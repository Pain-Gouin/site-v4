import json
from datetime import datetime, time, timedelta
from decimal import Decimal
from pprint import pformat

import helloasso_python
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Case, CharField, Prefetch, Sum, Value, When
from django.db.models.functions import Lower, Substr
from django.forms import Select, modelformset_factory
from django.http import HttpResponseBadRequest, HttpResponseServerError, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from commande.tokens import VerifiedUserTokenGenerator

from . import forms, tasks
from .helloasso import get_api_client, log_api_exception
from .models import (
    Delivery,
    HelloAssoCheckout,
    Order,
    OrderProduct,
    ProductCategory,
    Transaction,
    User,
)
from .utils import (
    PrecreateUserFunction,
    SendMailVerification,
    SendPrecreationMailFunction,
    html_to_text,
    login_required_with_message,
)


# Create your views here.
def index(request):
    return render(
        request,
        "commande/main.html",
        context={
            "DELIVERY_CUTOFF_TIME": settings.DELIVERY_CUTOFF_TIME,
            "GIT_COMMIT": settings.GIT_COMMIT,
        },
    )


def mentions(request):
    return render(request, "commande/mentions.html")


def contact(request):
    return render(request, "commande/contact.html")


@login_required_with_message("Authentifie toi avant d’accéder au rechargement")
def recharge(request):
    # Vérification que l'utilisateur est bien vérifié
    if (
        not request.user.verified_genuine_user
        and not request.user.can_be_verified_genuine_user()
    ):
        messages.warning(
            request, "Tu dois valider ton compte avant de pouvoir le recharger !"
        )
        return redirect(account_verification)

    if "error" in request.GET:
        messages.error(request, f"Erreur HelloAsso: {request.GET['error']}")
    elif "checkoutIntentId" in request.GET:
        messages.success(
            request,
            "Transaction effectuée avec succès, ton compte devrait être crédité d'ici quelques secondes",
        )
        checkout = HelloAssoCheckout.objects.get(
            checkout_intent_id=request.GET["checkoutIntentId"]
        )
        checkout.refresh_from_api()
        return redirect("recharge")

    amount = request.GET.get("amount")
    min_amount = Decimal(0.5)
    max_amount = min(
        settings.MAX_TOPUP_AMOUNT,
        settings.MAX_BALANCE_ALLOWED - request.user.balance_cache,
    )
    if request.method == "POST":
        form = forms.TopupForm(min_amount, max_amount, data=request.POST)
        if form.is_valid():
            if request.is_secure():
                new_checkout = HelloAssoCheckout.objects.create(
                    user=request.user, amount=form.cleaned_data["amount"]
                )

                with get_api_client() as api_client:
                    api_instance = helloasso_python.CheckoutApi(api_client)
                    organization_slug = settings.HELLOASSO_ORG_SLUG
                    payer = helloasso_python.HelloAssoApiV5ModelsCartsCheckoutPayer(
                        firstName=request.user.first_name,
                        lastName=request.user.last_name,
                        email=request.user.email,
                    )
                    amount_int = int(new_checkout.amount * 100)
                    body = helloasso_python.HelloAssoApiV5ModelsCartsInitCheckoutBody(
                        total_amount=amount_int,
                        initial_amount=amount_int,
                        item_name=f"Rechargement du compte paingouin de {new_checkout.amount}€",
                        back_url=request.build_absolute_uri(
                            reverse("recharge", query={"amount": new_checkout.amount})
                        ),
                        error_url=request.build_absolute_uri(
                            reverse("recharge", query={"amount": new_checkout.amount})
                        ),
                        return_url=request.build_absolute_uri(reverse("recharge")),
                        contains_donation=False,
                        payer=payer,
                        metadata={
                            "website_tracked": True,
                            "HelloAssoCheckoutPK": new_checkout.pk,
                        },
                    )

                    try:
                        api_response = api_instance.organizations_organization_slug_checkout_intents_post(
                            organization_slug, body
                        )

                        new_checkout.checkout_intent_id = api_response.id
                        new_checkout.save()
                        tasks.check_checkout_status.apply_async_on_commit(
                            (api_response.id,), countdown=60 * 60
                        )

                        return redirect(api_response.redirect_url)
                    except helloasso_python.ApiException as e:
                        messages.error(
                            request, f"Erreur lors de l'appel API: {pformat(e)}"
                        )
                        log_api_exception(
                            e,
                            api_instance.organizations_organization_slug_checkout_intents_post,
                        )

            else:
                messages.warning(
                    request,
                    "Formulaire correct, mais il n'est pas possible d'utiliser l'API en HTTP.",
                )

        else:
            messages.error(
                request,
                f"Saisie invalide. La somme doit être comprise entre {min_amount}€ et {max_amount}€.",
            )
    else:
        form = forms.TopupForm(min_amount, max_amount, data={"amount": amount})

    topup_types = [
        Transaction.TransactionTypeChoices.LYF_TOPUP,
        Transaction.TransactionTypeChoices.POS_TERMINAL_TOPUP,
        Transaction.TransactionTypeChoices.CASH_TOPUP,
    ]
    transaction_type_cases = [
        When(type=choice[0], then=Value(choice[1]))
        for choice in Transaction.TransactionTypeChoices.choices
    ]
    helloasso_status_cases = [
        When(status=choice[0], then=Value(choice[1]))
        for choice in HelloAssoCheckout.HelloAssoCheckoutStatusChoices.choices
    ]
    transactions = (
        Transaction.objects.filter(user=request.user, type__in=topup_types)
        .annotate(
            statusL=Value("Validé", output_field=CharField()),
            typeL=Case(*transaction_type_cases, output_field=CharField()),
        )
        .values("amount", "typeL", "statusL", "created_at")
    )

    checkouts = (
        HelloAssoCheckout.objects.filter(user=request.user)
        .annotate(
            typeL=Value(
                Transaction.TransactionTypeChoices.HELLOASSO_CHECKOUT.label,
                output_field=CharField(),
            ),
            statusL=Case(*helloasso_status_cases, output_field=CharField()),
        )
        .values("amount", "typeL", "statusL", "created_at")
    )

    combined_topup_list = transactions.union(checkouts).order_by("-created_at")

    return render(
        request,
        "commande/recharge.html",
        context={
            "form": form,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "combined_topup_list": combined_topup_list,
        },
    )


@login_required_with_message("Authentifie toi avant d’accéder au rechargement")
def recharge_lyf(request):
    messages.info(
        request,
        mark_safe(
            f"Vous pouvez également recharger directement en ligne, en <a href='{reverse('recharge')}' class='underline'>payant par carte bancaire</a>"
        ),
    )
    return render(request, "commande/recharge_lyf.html")


@login_required
def account_verification(request):
    if (
        request.user.verified_genuine_user
        or request.user.can_be_verified_genuine_user()
    ):
        messages.success(request, "Ton compte est déjà validé")
        return redirect(index)

    if request.method == "POST":
        form = forms.CheckGenuineUserForm(request.POST)

        if form.is_valid():
            user_pk_bytes = force_bytes(User._meta.pk.value_to_string(request.user))
            token = VerifiedUserTokenGenerator().make_token(request.user)

            email_html = render_to_string(
                template_name="mail/verify_account_mail.html",
                context={
                    "request": request,
                    "uid": urlsafe_base64_encode(user_pk_bytes),
                    "token": token,
                    "user": request.user,
                },
            )
            send_mail(
                subject="Vérification de ton compte Pain'Gouin",
                message=html_to_text(email_html),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[form.cleaned_data["email"]],
                html_message=email_html,
                fail_silently=True,
            )
            messages.success(
                request,
                "Un lien pour vérifier ton compte vient d'être envoyé à ta boîte mail Centrale",
            )

        else:
            messages.error(
                request,
                "E-mail non valide. Celui-ci doit se finir par: @centrale.centralelille.fr",
            )
    else:
        form = forms.CheckGenuineUserForm()
    return render(request, "commande/verify_user.html", context={"form": form})


@login_required_with_message("Authentifie toi pour vérifier ton compte")
def verify_account(request, uidb64, token):
    # Decode de l'uid
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = urlsafe_base64_decode(uidb64).decode()
        pk = User._meta.pk.to_python(uid)
        user = User._default_manager.get(pk=pk)
    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
        ValidationError,
    ):
        user = None

    if user is None:
        messages.error(request, "Lien non valide.")
        return redirect(index)
    if user != request.user:
        messages.error(
            request, "Ce lien n'est pas pour le compte actuellement connecté."
        )
        return redirect(index)

    if not VerifiedUserTokenGenerator().check_token(user, token):
        if user.verified_genuine_user:
            messages.warning(request, "Ce compte a déjà été validé.")
            return redirect(index)
        messages.error(
            request, "Ce lien n'est plus valide. Tu peux faire une nouvelle demande."
        )
        return redirect(account_verification)

    # Lien valide
    user.verified_genuine_user = True
    user.save(update_fields=["verified_genuine_user"])
    messages.success(request, "Compte vérifié avec succès.")

    return redirect(recharge)


def login_page(request):
    if request.user.is_authenticated:
        return redirect("update")

    invalidCredential = False
    if request.method == "POST":
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            if user is not None:
                # Check if the email is verified
                if user.email_verified:
                    login(request, user)
                    request.session.pop("login_message", None)
                    request.session.pop("login_next", None)
                    return redirect(request.GET.get("next", index))
                SendMailVerification(user, user.email, request)
                messages.success(
                    request,
                    "Un lien vient de t'être envoyé afin de vérifier ton email.\nSi tu ne réussis pas à le vérifer, contact l'administrateur web.",
                )

            else:
                invalidCredential = True
    else:
        form = forms.LoginForm()

    login_redirect_msg = None
    if "login_message" in request.session:
        if (
            request.session.get("login_next") is None
        ):  # Il faut set car c'est la première fois.
            request.session["login_next"] = request.GET.get("next")
        if request.GET.get("next") is None or request.GET.get(
            "next"
        ) != request.session.get("login_next"):  # Le msg n'est plus valide
            request.session.pop("login_message", None)
            request.session.pop("login_next", None)
        else:
            login_redirect_msg = request.session["login_message"]

    return render(
        request,
        "commande/login.html",
        context={
            "form": form,
            "invalidCredential": invalidCredential,
            "msg": login_redirect_msg,
        },
    )


@require_POST
def check_email(request):
    email = request.POST.get("email")
    exists = User.objects.filter(email=email, is_active=True).exists()
    return JsonResponse({"exists": exists})


@require_POST
def signup(request):
    email = request.POST.get("email")
    user, created = User.objects.get_or_create(email=email)

    if not created and user.is_active:
        return JsonResponse(
            {"success": False, "error": "User already exists"}, status=400
        )

    PrecreateUserFunction(user, request)
    messages.success(
        request,
        f"Un email avec un lien pour créer ton compte vient d'être envoyé à l'adresse {email}",
    )

    msg = render_to_string("commande/messages.html", request=request)
    return JsonResponse({"success": True, "msg": msg})


@require_POST
def reset_password_ajax(request):
    form = PasswordResetForm(request.POST)

    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            subject_template_name="mail/password_reset_subject.txt",
            html_email_template_name="mail/password_reset_mail.html",
            from_email=settings.EMAIL_HOST_USER,
        )

        messages.success(request, "Un lien de réinitialisation a été envoyé.")
        msg_html = render_to_string("commande/messages.html", request=request)

        return JsonResponse({"success": True, "msg": msg_html})

    # If the form is invalid (e.g. bad email format)
    return JsonResponse(
        {"success": False, "error": "Adresse e-mail invalide."}, status=400
    )


def verify_email(request, uidb64, email64, token):
    # Decode de l'uid et de l'email
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = urlsafe_base64_decode(uidb64).decode()
        pk = User._meta.pk.to_python(uid)
        user = User._default_manager.get(pk=pk)
        new_email = urlsafe_base64_decode(email64).decode()
    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
        ValidationError,
    ):
        user = None

    if user is None:
        messages.error(request, "Lien non valide.")
        return redirect(settings.LOGIN_URL)

    # On modifie temporairement l'email pour vérifier que le token est bien associé à ce nouvel email
    user.email = new_email
    # Vérification du token
    if not PasswordResetTokenGenerator().check_token(user, token):
        # Le token n'est pas valide car expiré ou modifié/inventé
        messages.error(
            request,
            mark_safe("Ce lien a expiré ou n'est plus valide."),
        )
    else:
        # Lien valide
        user.email_verified = True
        user.save()
        messages.success(request, f"L'email '{user.email}' a bien été vérifié.")
    return redirect(settings.LOGIN_URL)


def logout_user(request):
    logout(request)
    return redirect(index)


def finish_signup_page(request, uidb64, token):
    # Decode de l'uid
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = urlsafe_base64_decode(uidb64).decode()
        pk = User._meta.pk.to_python(uid)
        user = User._default_manager.get(pk=pk)
    except (
        TypeError,
        ValueError,
        OverflowError,
        User.DoesNotExist,
        ValidationError,
    ):
        user = None

    if user is None:
        messages.error(request, "Lien non valide.")
        return redirect(settings.LOGIN_URL)

    # Vérification du token
    if not PasswordResetTokenGenerator().check_token(user, token):
        if user.last_login is not None:
            messages.warning(
                request,
                "Ce compte a déjà été activé, connecte-toi pour continuer.",
            )
        else:
            # On suppose que le token n'est pas valide car expiré (ça pourrait également être un token modifié/inventé)
            SendPrecreationMailFunction(user, request)
            messages.warning(
                request,
                "Ce lien a expiré, un nouveau lien de création de compte vient de t'être envoyé par email.",
            )
        return redirect(settings.LOGIN_URL)

    # Lien valide
    if request.method == "POST":
        original_email = user.email
        form = forms.FinishSignupForm(user, data=request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            updated_user.email_verified = original_email == updated_user.email
            updated_user.date_joined = timezone.now()
            updated_user.save()
            login(request, user)
            receiver_email = updated_user.email
            template_name = "mail/signup_mail.html"
            convert_to_html_content = render_to_string(
                template_name=template_name,
                context={
                    "prenom": updated_user.first_name,
                    "request": request,
                },
            )
            plain_message = html_to_text(convert_to_html_content)

            send_mail(
                subject="Inscription confirmée",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[
                    receiver_email,
                ],
                html_message=convert_to_html_content,
                fail_silently=True,
            )
            messages.success(request, "Ton compte a bien été créé !")
            return redirect(settings.LOGIN_REDIRECT_URL)
        for key, value in form.errors.items():
            messages.error(request, value)
    else:
        form = forms.FinishSignupForm(user, instance=user)

    return render(request, "commande/finish_signup.html", context={"form": form})


@login_required
def update_user_page(request):
    if request.method == "POST":
        form = forms.UpdateForm(
            data=request.POST, instance=request.user, request=request
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Profile mise à jour.")
        else:
            for key, value in form.errors.items():
                messages.error(request, value)

        return redirect("update")

    form = forms.UpdateForm(instance=request.user, request=request)

    return render(request, "commande/update.html", context={"form": form})


@login_required_with_message("Authentifie toi avant de pouvoir commander")
def commande(request):
    livraison_query = Delivery.objects.editable().order_by("date")

    category_query = ProductCategory.objects.prefetch_related("product_set").all()

    category_dict = {}
    for cat in category_query:
        queryset = cat.product_set.filter(is_active=True)
        if queryset.exists():
            category_dict[cat] = list(queryset)

    if request.user.is_authenticated and request.method == "POST":
        order_list = []
        total_commande = 0

        for product_list in category_dict.values():
            for prod in product_list:
                quantity = int(request.POST["quantity" + str(prod.id)])

                if quantity > 0:
                    order_list.append([prod, quantity, quantity * prod.resell_price])
                    total_commande += order_list[-1][2]

        delivery = Delivery.objects.get(id=request.POST["date"])
        if total_commande > request.user.balance_cache:
            messages.error(
                request,
                mark_safe(
                    f'Fonds insuffisant, il faut que tu <a href="{reverse("recharge")}" class="font-semibold underline hover:no-underline">recharges ton compte</a> !'
                ),
            )
        elif (
            len(order_list) == 0
        ):  # Avec la vérification javascript côté client, ce n'est pas sensé être possible
            messages.error(request, "Sélectionne au moins un article !")
        elif not delivery.is_editable:
            messages.error(
                request,
                "Il n'est plus possible de passer une commande pour cette date, la livraison est peut-être déjà en cours.",
            )
        else:
            room = request.POST["room"]
            with transaction.atomic():
                order = Order.objects.create(
                    original_price=total_commande,
                    client=request.user,
                    delivery=delivery,
                    room=room,
                )
                order_transaction = Transaction.objects.create(
                    user=request.user,
                    order=order,
                    amount=-total_commande,
                    type=Transaction.TransactionTypeChoices.ORDER_CHARGE,
                    initiator=request.user,
                )

                order_product_instances = []
                for item in order_list:
                    op = OrderProduct(
                        order=order,  # The crucial step: link the saved Order object
                        product=item[0],
                        quantity=item[1],
                        total_price_sold=item[2],
                        total_price_bought=item[1] * item[0].purchase_price,
                    )
                    order_product_instances.append(op)
                OrderProduct.objects.bulk_create(order_product_instances)

            if request.user.get_order_email:
                receiver_email = request.user.email
                template_name = "mail/order_mail.html"
                convert_to_html_content = render_to_string(
                    template_name=template_name,
                    context={
                        "prenom": request.user.first_name,
                        "date": order.delivery.date,
                        "order": order,
                        "total": total_commande,
                        "room": room,
                        "request": request,
                        "media_url": settings.MEDIA_URL,
                    },
                )
                plain_message = html_to_text(convert_to_html_content)

                send_mail(
                    subject="Confirmation de commande",
                    message=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[
                        receiver_email,
                    ],
                    html_message=convert_to_html_content,
                    fail_silently=True,
                )

            messages.success(
                request,
                mark_safe(
                    f'Commande bien prise en compte, <b>pense à mettre un sac devant ta porte !</b>  <a href="{reverse("historique")}" class="font-semibold underline hover:no-underline">Annuler la commande</a>'
                ),
            )
            return redirect("commande")

    if request.user.balance_cache == 0:
        messages.warning(
            request,
            mark_safe(
                f'Avant de pouvoir passer commande, tu dois d\'abord <a href="{reverse("recharge")}" class="font-semibold underline hover:no-underline">alimenter ton compte</a>.'
            ),
        )
    elif request.user.balance_cache <= 2:
        messages.warning(
            request,
            mark_safe(
                f'Ton solde commence à être bas, n\'oublie pas de <a href="{reverse("recharge")}" class="font-semibold underline hover:no-underline">recharger ton compte</a>.'
            ),
        )

    context = {
        "category_dict": category_dict,
        "livraison": livraison_query,
        "solde_vide": request.user.balance_cache == 0,
    }
    return render(request, "commande/order.html", context)


def add_livraison_batiment(batiment, commande_batiment, produit_client):
    if commande_batiment[batiment]["commande"] == []:
        commande_batiment[batiment]["commande"] = produit_client.copy()
    else:
        for comm_client in produit_client:
            trouve = False
            for prod in commande_batiment[batiment]["commande"]:
                if prod[0] == comm_client[0]:
                    a = str(int(prod[1]) + int(comm_client[1]))
                    prod[1] = a
                    trouve = True
                    break

            if not trouve:
                commande_batiment[batiment]["commande"].append(comm_client.copy())
    return commande_batiment


@login_required
def livreur(request):
    if not (
        request.user.is_delivery_man
        or request.user.is_staff
        or request.user.is_superuser
    ):
        messages.warning(
            request,
            "Tu dois être un livreur ou un administrateur pour accéder à la page de livraison.",
        )
        return redirect("/")

    context = {}
    context["show_calendar"] = request.user.is_staff
    if context["show_calendar"]:
        if request.user.is_staff:
            context["allowed_dates"] = list(
                Delivery.objects.filter(is_active=True).values_list("date", flat=True)
            )
    if "date" in request.GET:
        if context["show_calendar"]:
            querystring = request.GET.get("date")
            target_date = datetime.strptime(querystring, "%Y-%m-%d").date()
        else:
            messages.warning(request, "Tu n'as pas le droit d'accéder à cette date !")
            return redirect("livreur")
        context["target_date"] = target_date

        try:
            delivery = Delivery.objects.filter(is_active=True).get(date=target_date)
        except Delivery.DoesNotExist:  # la date de livraison n'existe pas
            delivery = False
        except Exception:
            # Not supposed to happen, another exception happened
            return HttpResponseServerError()
    else:
        CUTOFF_TIME = time(14, 0)  # Time at wich to show tomorrow's delivery
        now = timezone.now()
        if now.time() >= CUTOFF_TIME:
            target_date = now.date() + timedelta(days=1)
        else:
            target_date = now.date()
        delivery = (
            Delivery.objects.filter(date__gte=target_date, is_active=True)
            .order_by("date")
            .first()
        )
        if delivery is None:
            delivery = False
        else:
            context["target_date"] = delivery.date

    context["delivery"] = delivery
    if delivery:
        current_orderproducts = OrderProduct.objects.filter(
            order__delivery=delivery,  # Filter backwards to the specific Delivery instance
            order__is_cancelled=False,  # Filter the related Order's status
            delivery_status=OrderProduct.OrderProductStatusChoices.VALID,  # Filter the item status
        )

        order_items = current_orderproducts.select_related("product").order_by(
            "product__category", "product__sort"
        )
        # I had issues with the group_by while keeping the model instances, so I group them manually.
        grouped_data = {}
        for item in order_items:
            prod_id = item.product.id
            if prod_id not in grouped_data:
                grouped_data[prod_id] = item
            else:
                grouped_data[prod_id].quantity += item.quantity

        context["products"] = grouped_data.values()

        current_orderproducts_bybuildings = (
            current_orderproducts.annotate(bat_id=Lower(Substr("order__room", 1, 1)))
            .values("bat_id", "product_id", "product__name")
            .annotate(total_quantity=Sum("quantity"))
            .order_by("product__category", "product__sort")
        )
        context["buildings"] = [
            {
                "nom": "Bâtiment A",
                "commande": current_orderproducts_bybuildings.filter(bat_id="a"),
            },
            {
                "nom": "Bâtiment B",
                "commande": current_orderproducts_bybuildings.filter(bat_id="b"),
            },
            {
                "nom": "Bâtiment C",
                "commande": current_orderproducts_bybuildings.filter(bat_id="c"),
            },
            {
                "nom": "Bâtiment D",
                "commande": current_orderproducts_bybuildings.filter(bat_id="d"),
            },
            {
                "nom": "Bâtiment E",
                "commande": current_orderproducts_bybuildings.filter(bat_id="e"),
            },
            {
                "nom": "Bâtiment F",
                "commande": current_orderproducts_bybuildings.filter(bat_id="f"),
            },
            {
                "nom": "Autre (indeterminé)",
                "commande": current_orderproducts_bybuildings.exclude(
                    bat_id__in=["a", "b", "c", "d", "e", "f"]
                ),
            },
        ]

        context["orders"] = list(
            Order.objects.filter(delivery=delivery, is_cancelled=False)
            .prefetch_related(
                Prefetch(
                    "orderproduct_set",
                    queryset=OrderProduct.objects.order_by(
                        "product", "product__category", "product__sort"
                    ).select_related("product"),
                )
            )
            .order_by("room")
        )

        if request.user.is_staff or request.user.is_superuser:
            ProductOrderFormSet = modelformset_factory(
                OrderProduct,
                fields=("delivery_status",),
                extra=0,
                widgets={
                    "delivery_status": Select(
                        attrs={
                            "class": "font-montserrat p-1 text-gray-900 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:ring-secondary focus:border-secondary"
                        },
                    )
                },
            )

            formset_qs = (
                OrderProduct.objects.filter(order__in=context["orders"])
                .select_related("product", "order")
                .order_by(
                    "order__room", "product", "product__category", "product__sort"
                )
            )

            if request.method == "POST":
                formset = ProductOrderFormSet(request.POST, queryset=formset_qs)
                if formset.is_valid():
                    with transaction.atomic():
                        # Initialize the set to track unique orders
                        modified_orders = set()

                        for form in formset.initial_forms:
                            if form.has_changed():
                                instance = form.save()

                                # Log the change:
                                field = form.changed_data[0]  # We have only one field
                                LogEntry.objects.log_actions(
                                    user_id=request.user.id,
                                    queryset=(instance,),
                                    action_flag=CHANGE,
                                    change_message=f"Statut changé de {form.initial.get(field)} à {form.cleaned_data.get(field)}",
                                )

                                modified_orders.add(instance.order)

                        # Mettre à jour les transactions liées aux produits
                        for order in modified_orders:
                            order.update_transactions(
                                request,
                                reason="Modification du statut de livraison d'articles",
                            )

                        messages.success(
                            request,
                            "Mise à jour des statuts de livraison effectuée avec succés.",
                        )
                    return redirect(request.get_full_path())
            else:
                formset = ProductOrderFormSet(queryset=formset_qs)

            form_map = {form.instance.id: form for form in formset}
            for order in context["orders"]:
                for op in order.orderproduct_set.all():
                    op.form = form_map.get(op.id)
            context["formset"] = formset

    return render(request, "commande/livreur.html", context)


@login_required
def historique(request):
    user_orders = (
        Order.objects.filter(client=request.user)
        .annotate(current_price=-Sum("transactions__amount"))
        .select_related("delivery")
        .prefetch_related("orderproduct_set__product")
        .order_by("-created_at")
    )

    return render(request, "commande/historique.html", {"user_orders": user_orders})


@login_required
def del_order(request, order):
    query_order = Order.objects.get(id=order)
    if query_order.client != request.user:
        messages.error(request, "Tu dois être connecté pour faire cela !")
        return redirect(settings.LOGIN_REDIRECT_URL)
    if not query_order.is_editable:
        messages.error(
            request,
            "La livraison est déjà en cours ou passée, il n'est plus possible de supprimer la commande.",
        )
    else:
        query_order.cancel(request)

        messages.success(request, "Commande bien annulée.")

    return redirect("historique")


@csrf_exempt
@require_POST
def helloasso_webhook_handler(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON payload.")

    event_type = body["eventType"]
    data = body["data"]
    metadata = body.get("metadata")

    match event_type:
        case "Order":
            tasks.helloasso_order_notification.delay(data, metadata)
        case "Payment":
            tasks.helloasso_payment_notification.delay(data, metadata)
        case _:
            # Not implemented/not usefull
            pass

    return JsonResponse({"status": "success"})
