from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.contrib.auth.views import PasswordResetView
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy, reverse
from django.http import HttpResponseServerError
from django.utils.http import urlsafe_base64_decode
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from datetime import datetime
from .utils import html_to_text, login_required_with_message

from . import forms

import json

from .models import Produit, CategorieProduit, Commande, Livraison, Utilisateur

# Create your views here.
def index(request):
    return render(request, "commande/main.html")

def mentions(request):
    return render(request, "commande/mentions.html")

def contact(request):
    return render(request, "commande/contact.html")

@login_required_with_message("Authentifie toi avant d’accéder au rechargement")
def recharge(request):
    return render(request, "commande/recharge.html")

def login_page(request):
    invalidCredential=False
    form = forms.LoginForm()
    if request.method == 'POST':
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                username = form.cleaned_data["email"],
                password = form.cleaned_data["password"],
            )
            request.user.last_login = datetime.now
            if user is not None :
                login(request,user)
                request.session.pop('login_message', None)
                request.session.pop('login_next', None)
                return redirect(request.GET.get('next', index))
            else:
                invalidCredential = True
    
    login_redirect_msg = None
    if 'login_message' in request.session:
        if request.session.get('login_next') is None: # Il faut set car c'est la première fois.
            request.session['login_next'] = request.GET.get('next')
        if request.GET.get('next') is None or request.GET.get('next') != request.session.get('login_next'): # Le msg n'est plus valide
            request.session.pop('login_message', None)
            request.session.pop('login_next', None)
        else:
            login_redirect_msg = request.session['login_message']
        
    return render(request, 'commande/login.html', context={'form': form, "invalidCredential":invalidCredential, 'msg':login_redirect_msg})

class ResetPasswordView(SuccessMessageMixin, PasswordResetView):
    template_name = 'commande/password_reset.html'
    html_email_template_name = 'mail/password_reset_mail.html'
    subject_template_name = 'mail/password_reset_subject.txt'
    search_field = ['email']
    from_email = settings.EMAIL_HOST_USER
    success_message = """Si un compte est associé à cette adresse e-mail, un message contenant les instructions pour réinitialiser ton mot de passe vient de t’être envoyé.
Si tu ne le reçois pas, vérifie que l’adresse saisie est correcte et consulte également tes spams.
En cas de difficulté persistante, contacte l’association."""
    success_url = reverse_lazy("password_reset")


def logout_user(request):
    logout(request)
    return redirect(index)

def finish_signup_page(request, uidb64, token):

    # Decode de l'uid
    try:
        # urlsafe_base64_decode() decodes to bytestring
        uid = urlsafe_base64_decode(uidb64).decode()
        pk = Utilisateur._meta.pk.to_python(uid)
        user = Utilisateur._default_manager.get(pk=pk)
    except (
        TypeError,
        ValueError,
        OverflowError,
        Utilisateur.DoesNotExist,
        ValidationError,
    ):
        user = None
    
    if user is None:
        messages.error(request, "uid utilisateur non valide")
        return redirect(settings.LOGIN_URL)

    # Vérification du token
    if not PasswordResetTokenGenerator().check_token(user, token):
        messages.error(request, "lien non valide")
        return redirect(settings.LOGIN_URL)
    
    # Lien valide
    if request.method == 'POST':
        original_email = user.email
        form = forms.FinishSignupForm(user, data=request.POST, instance=user)
        if form.is_valid():
            updated_user = form.save(commit=False)
            updated_user.email_verified = (original_email == updated_user.email)
            updated_user.date_joined = datetime.now()
            updated_user.save()
            login(request, user)
            receiver_email = updated_user.email
            template_name = "mail/signup_mail.html"
            convert_to_html_content =  render_to_string(
                template_name=template_name,
                context = {
                    'prenom':updated_user.first_name,
                    'request':request,
                }
            )
            plain_message = html_to_text(convert_to_html_content)

            send_mail(
                subject="Inscription confirmée",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[receiver_email,],
                html_message=convert_to_html_content,
                fail_silently=True
            )
            messages.success(request, "Ton compte a bien été créé !")
            return redirect(settings.LOGIN_REDIRECT_URL)
        else:
            for key, value in form.errors.items():
                messages.error(request, value)
    else:
        form = forms.FinishSignupForm(user, instance=user)

    return render(request, 'commande/finish_signup.html', context={'form': form})

def signup_page(request):
    if request.method == 'POST':
        form = forms.SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            receiver_email = request.user.email
            request.user.save()
            template_name = "mail/signup_mail.html"
            convert_to_html_content =  render_to_string(
                template_name=template_name,
                context = {
                    'prenom':request.user.first_name,
                    'request':request,
                }
            )
            plain_message = html_to_text(convert_to_html_content)

            send_mail(
                subject="Inscription confirmée",
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[receiver_email,],
                html_message=convert_to_html_content,
                fail_silently=True
            )
            messages.success(request, "Ton compte a bien été créé !")
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = forms.SignupForm()

    return render(request, 'commande/signup.html', context={'form': form})

@login_required
def update_user_page(request):
    if request.method == 'POST':
        form = forms.UpdateForm(data=request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile mise à jour.")
        else:
            for key, value in form.errors.items():
                messages.error(request, value)
            
        return redirect('update')
    
    form = forms.UpdateForm(instance=request.user)

    return render(request, "commande/update.html", context={"form":form})


@login_required_with_message("Authentifie toi avant de pouvoir commander")
def commande(request):
    order = []

    livraison_query = Livraison.objects.modifiable()

    categorie_query = CategorieProduit.objects.prefetch_related('produit_set').all()

    category_dict = {}
    for cat in categorie_query:
        category_dict[cat] = list(cat.produit_set.all())
    
    if request.user.is_authenticated and request.method == 'POST':

        total_commande = 0

        bought_prod = []
        for product_list in category_dict.values():
            for prod in product_list:
                quantity = request.POST["quantity" + str(prod.id)]

                total_commande += int(quantity)*prod.prix
                if int(quantity) > 0:
                    bought_prod.append({"object": prod, "quantity": quantity, "price": int(quantity)*prod.prix})
                    order.append([prod.nom, quantity])
        order = json.dumps(order)

        if total_commande > request.user.credit:
            messages.error(request, mark_safe(f'Fonds insuffisant, il faut que tu <a href="{reverse("recharge")}" class="font-semibold underline hover:no-underline">recharges ton compte</a> !'))
        elif len(bought_prod) == 0: # Avec la vérification javascript côté client, ce n'est pas sensé être possible
            messages.error(request, "Sélectionne au moins un article !")
        else:
            chambre = request.POST["chambre"]
            date = list(Livraison.objects.filter(id = request.POST["date"]))[0].date
            request.user.credit -= total_commande
            request.user.last_order = datetime.now
            request.user.save()

            comm = Commande(client = request.user.get_username(), date = date, produit = order, chambre = chambre, total_commande = total_commande)
            comm.save()

            add_to_livraison(date,order)

            if request.user.getOrderMail:
                receiver_email = request.user.email
                template_name = "mail/order_mail.html"
                convert_to_html_content =  render_to_string(
                    template_name=template_name,
                    context = {
                        'prenom': request.user.first_name,
                        'date': date,
                        'commande': bought_prod,
                        'total': total_commande,
                        'chambre': chambre,
                        "request": request,
                        "media_url": settings.MEDIA_URL
                    }
                )
                plain_message = html_to_text(convert_to_html_content)

                send_mail(
                    subject="Confirmation de commande",
                    message=plain_message,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[receiver_email,],
                    html_message=convert_to_html_content,
                    fail_silently=True
                )
            
            messages.success(request, mark_safe(f'Commande bien prise en compte, <b>pense à mettre un sac devant ta porte !</b>  <a href="{reverse("historique")}" class="font-semibold underline hover:no-underline">Annuler la commande</a>'))
            return redirect('commande')

    if request.user.credit == 0:
        messages.warning(request, mark_safe(f'Avant de pouvoir passer commande, tu dois d\'abord <a href="{reverse('recharge')}" class="font-semibold underline hover:no-underline">alimenter ton compte</a>.'))
    elif request.user.credit <= 2:
        messages.warning(request, mark_safe(f'Ton solde commence à être bas, n\'oublie pas de <a href="{reverse("recharge")}" class="font-semibold underline hover:no-underline">recharger ton compte</a>.'))

    context = {'category_dict': category_dict, 'livraison':livraison_query, 'solde_vide':request.user.credit==0}
    return render(request, 'commande/order.html', context)

def add_to_livraison(date, commande):
    livraison = Livraison.objects.get(date = date).produit
    liste_commande = json.loads(commande)

    if livraison == ['None']:
        livraison.pop()
    else:
        livraison = json.loads(livraison)

    for produit in liste_commande:
        compteur = 0
        for liv in livraison:
            if produit[0] == liv[0]:
                a = int(liv[1]) + int(produit[1])
                liv[1] = str(a)
                break
            compteur +=1
        if compteur == len(livraison) and int(produit[1])!=0:
            livraison.append(produit.copy()) 

    update =  Livraison.objects.filter(date=date).update(produit = json.dumps(livraison))
    return

def add_livraison_batiment(batiment, commande_batiment, produit_client):
    if commande_batiment[batiment]['commande'] == []:
        commande_batiment[batiment]['commande'] = produit_client.copy()
    else:
        for comm_client in produit_client:
            trouve = False
            for prod in commande_batiment[batiment]['commande']:
                if prod[0] == comm_client[0]:
                    a = str(int(prod[1]) + int(comm_client[1]))
                    prod[1] = a
                    trouve = True
                    break

            if not trouve:
                commande_batiment[batiment]['commande'].append(comm_client.copy())
    return commande_batiment

@login_required
def livreur(request):
    produit = ['None']
    date = datetime.today().strftime('%Y-%m-%d')
    try:
        livraison_query = Livraison.objects.get(date=date)
    except Livraison.DoesNotExist: # la date de livraison n'existe pas
        return render(request, "commande/livreur.html", {'livraison':None})
    except Exception:
        # Not supposed to happen, another exception happened
        return HttpResponseServerError()
    
    produit = livraison_query.produit

    commande = list(Commande.objects.filter(date = date).order_by("chambre"))
    commande_list = []
    commande_batiment = [{'nom': "Bâtiment A", 'commande': []},{'nom': "Bâtiment B", 'commande': []},{'nom': "Bâtiment C", 'commande': []},{'nom': "Bâtiment D", 'commande': []},{'nom': "Bâtiment E", 'commande': []},{'nom': "Bâtiment F", 'commande': []},{'nom': "Autre (indeterminé)", 'commande': []}]

    for comm in commande :
        produit_client = json.loads(comm.produit)
        produit_client2 = json.loads(comm.produit)
        commande_list.append([comm.chambre, produit_client])
        match comm.chambre[0].upper():
            case 'A':
                commande_batiment = add_livraison_batiment(0, commande_batiment, produit_client2)
            case 'B':
                commande_batiment = add_livraison_batiment(1, commande_batiment, produit_client2)
            case 'C':
                commande_batiment = add_livraison_batiment(2, commande_batiment, produit_client2)
            case 'D':
                commande_batiment = add_livraison_batiment(3, commande_batiment, produit_client2)
            case 'E':
                commande_batiment = add_livraison_batiment(4, commande_batiment, produit_client2)
            case 'F':
                commande_batiment = add_livraison_batiment(5, commande_batiment, produit_client2)
            case _:
                commande_batiment = add_livraison_batiment(6, commande_batiment, produit_client2)

    if produit == ['None']:
        produit = False
    else :
        produit = json.loads(produit)

    context = {'livraison':livraison_query, 'produit':produit, 'commande':commande_list, 'commande_batiment':commande_batiment}
    return render(request, "commande/livreur.html", context)


@login_required
def historique(request):
    user_order = Commande.objects.filter(client=request.user.get_username()).order_by("-date")
    historique = []

    for commande in user_order:
        passe = commande.est_modifiable
        historique.append({"date":commande.date, "produits":json.loads(commande.produit), "total":commande.total_commande, "passe":passe, "id":commande.id})

    context = {"historique":historique}
    return render(request, "commande/historique.html", context)

@login_required
def del_order(request, order):
    query_order = Commande.objects.get(id = order)
    if query_order.client != request.user.get_username():
        messages.error(request, "Tu dois être connecté pour faire cela !")
        return redirect(settings.LOGIN_REDIRECT_URL)
    elif query_order.date <= datetime.today().date():
        messages.error(request, "La commande est déjà passée, il n'est plus possible de la supprimer.")
    else:
        request.user.credit += query_order.total_commande
        request.user.save()
        
        del_to_livraison(query_order.date,query_order.produit)
        messages.success(request, "Commande bien annulée.")

        query_order.delete()

    return redirect("historique")

def del_to_livraison(date, commande):
    livraison = Livraison.objects.get(date = date).produit
    liste_commande = json.loads(commande)

    if livraison == ['None']:
        livraison.pop()
    else:
        livraison = json.loads(livraison)

    for produit in liste_commande:
        for liv in livraison:
            if produit[0] == liv[0]:
                a = int(liv[1]) - int(produit[1])
                if a == 0:
                    livraison.remove(liv)
                else:
                    liv[1] = str(a)
                break
    
    update =  Livraison.objects.filter(date=date).update(produit = json.dumps(livraison))
    return
