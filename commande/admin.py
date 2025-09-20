from django.contrib import admin, messages
from django.views.generic import TemplateView, FormView
from unfold.admin import ModelAdmin
from unfold.views import UnfoldModelAdminViewMixin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.urls import path, reverse_lazy
from django.contrib.auth.models import Group
from .models import Utilisateur, Produit, CategorieProduit, Commande, Livraison
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from io import BytesIO
import xlsxwriter
from django.http import HttpResponse
from django.shortcuts import render
import json
from django.db.models import Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.db.models import F
from datetime import datetime
from decimal import Decimal
from .utils import html_to_text, send_mass_html_mail
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.forms import modelformset_factory

from django.db.models import Q


from .forms import (
    LivraisonForm,
    ExportForm,
    PrecreateUserForm,
    PrecreateUsersFormHelper,
)


# Enregistrer les autres modèles


@admin.register(Produit)
class ProduitAdmin(ModelAdmin):
    pass


@admin.register(CategorieProduit)
class CategorieProduitAdmin(ModelAdmin):
    pass


@admin.register(Commande)
class CommandeAdmin(ModelAdmin):
    pass


class UtilisateurAdmin(ModelAdmin):
    list_display = (
        "last_name",
        "first_name",
        "email",
        "isLivreur",
        "isPermis",
        "credit",
        "last_login",
        "last_order",
        "created_at",
    )
    search_fields = (
        "last_name",
        "first_name",
        "email",
    )  # Pour faciliter la recherche par nom ou email
    list_filter = (
        "isLivreur",
        "isPermis",
    )  # Pour ajouter des filtres sur les colonnes booléennes


admin.site.register(Utilisateur, UtilisateurAdmin)


class LivraisonAdmin(ModelAdmin):
    exclude = ["produit"]
    form = LivraisonForm


class SoldeView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Gestion des soldes"
    permission_required = ("auth.view_group",)
    template_name = "admin/solde.html"


def autocomplete_user(request):
    if "term" in request.GET:
        term = request.GET.get("term")
        # Splitter le terme en mots pour gérer les prénoms et noms multiples
        terms = term.split()

        if len(terms) == 1:
            # Si un seul terme est saisi, chercher dans les prénoms ou les noms de famille
            qs = Utilisateur.objects.filter(
                Q(first_name__icontains=terms[0]) | Q(last_name__icontains=terms[0])
            )
        else:
            # Si plusieurs termes sont saisis, chercher par prénom et nom
            qs = Utilisateur.objects.filter(
                Q(first_name__icontains=terms[0], last_name__icontains=terms[-1])
                | Q(first_name__icontains=terms[-1], last_name__icontains=terms[0])
            )

        names = [f"{user.first_name} {user.last_name}" for user in qs]
        return JsonResponse(names, safe=False)


def get_user_solde(request):
    if "first_name" in request.GET and "last_name" in request.GET:
        first_name = request.GET.get("first_name")
        last_name = request.GET.get("last_name")
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            return JsonResponse({"solde": user.credit})
        except Utilisateur.DoesNotExist:
            return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def update_credit(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        new_credit = request.POST.get("new_credit")
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            user.credit = Decimal(new_credit)
            user.save()
            return JsonResponse({"message": "Crédit mis à jour avec succès."})
        except Utilisateur.DoesNotExist:
            return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)


@csrf_exempt
def add_credit(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        add_credit = request.POST.get("add_credit")
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            user.credit += Decimal(add_credit)
            user.save()
            return JsonResponse(
                {"message": "Crédit ajouté avec succès.", "new_solde": user.credit}
            )
        except Utilisateur.DoesNotExist:
            return JsonResponse({"error": "Utilisateur non trouvé"}, status=404)
    return JsonResponse({"error": "Invalid request"}, status=400)


class TableurView(UnfoldModelAdminViewMixin, FormView):
    title = "Export d'un tableur"
    permission_required = ("auth.view_group",)
    template_name = "admin/tableur.html"
    form_class = ExportForm

    def form_valid(self, form):
        month = form.cleaned_data["mois"]
        year = month.year
        month = month.month

        solde_total = 0

        solde_query = list(Utilisateur.objects.all())
        for i in solde_query:
            solde_total += i.credit

        try:
            livraison_query = Livraison.objects.filter(
                date__year=year, date__month=month
            )
            commande_query = Commande.objects.filter(date__year=year, date__month=month)
            user_solde = Utilisateur.objects.aggregate(Sum("credit"))["credit__sum"]
            nbre_commande = len(commande_query)
            produit = []
            for liv in livraison_query:
                if (
                    liv.produit != ["None"]
                    and liv.produit != "[]"
                    and liv.produit != "[None]"
                ):
                    produit.append(json.loads(liv.produit))

        except Exception as e:
            print(f"Error: {e}")
            livraison_query = None
            produit = "Pas de produit commandé"

        liv_mois = add_livraison_mois(produit)

        # Création du tableur
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})

        # Création des styles du tableur
        header_format = workbook.add_format(
            {
                "bold": True,
                "align": "center",
                "valign": "vcenter",
                "bg_color": "#f4dcdc",
                "border": 1,
            }
        )

        produit_format = workbook.add_format(
            {"bg_color": "#f9e8e8", "align": "center", "valign": "vcenter", "border": 1}
        )

        table = workbook.add_format(
            {
                "border": 1,
                "align": "center",
                "valign": "vcenter",
            }
        )

        table_with_wrap = workbook.add_format(
            {
                "border": 1,
                "align": "center",
                "valign": "vcenter",
                "text_wrap": True,  # Active le retour à la ligne dans la cellule
            }
        )

        info_format = workbook.add_format(
            {
                "italic": True,
            }
        )

        date_format = workbook.add_format({"num_format": "mm-yyyy"})

        worksheet = workbook.add_worksheet("Bilan général")
        worksheet2 = workbook.add_worksheet("Détail des commandes")

        worksheet.write("A1", "Mois", header_format)
        worksheet.write("A2", f"{year}-{month:02}", date_format)
        worksheet.write("A4", "Produit", header_format)
        worksheet.write("B4", "Quantité", header_format)
        worksheet.write("C4", "Prix de vente", header_format)
        worksheet.write("D4", "Prix d'achat", header_format)
        worksheet.write("E4", "Chiffre d'affaire du produit", header_format)
        worksheet.write("F4", "Dépense sur le produit", header_format)

        col_widths = [
            len("Produit"),
            len("Quantité"),
            len("Prix de vente"),
            len("Prix d'achat"),
            len("Chiffre d'affaire du produit"),
            len("Dépense sur le produit"),
        ]

        for i in range(len(liv_mois) - 1):
            worksheet.write(f"A{5+i}", str(liv_mois[i][0]), produit_format)
            worksheet.write(f"B{5+i}", str(liv_mois[i][1]), table)
            worksheet.write(f"C{5+i}", str(liv_mois[i][2]).replace(".", ","), table)
            worksheet.write(f"D{5+i}", str(liv_mois[i][3]).replace(".", ","), table)
            worksheet.write(
                f"E{5+i}", str("{:.2f}".format(liv_mois[i][4]).replace(".", ",")), table
            )
            worksheet.write(
                f"F{5+i}", str("{:.2f}".format(liv_mois[i][5]).replace(".", ",")), table
            )

            col_widths[0] = max(col_widths[0], len(str(liv_mois[i][0])))
            col_widths[1] = max(col_widths[1], len(str(liv_mois[i][1])))
            col_widths[2] = max(col_widths[2], len(str(liv_mois[i][2])))
            col_widths[3] = max(col_widths[3], len(str(liv_mois[i][3])))
            col_widths[4] = max(
                col_widths[4],
                len(str("{:.2f}".format(liv_mois[i][4])).replace(".", ",")),
            )
            col_widths[5] = max(
                col_widths[5],
                len(str("{:.2f}".format(liv_mois[i][5])).replace(".", ",")),
            )

        worksheet.write(
            "A3",
            "Tout étant automatisé, veuillez vérifier la cohérence des résultats et contacter le responsable web en cas de problème",
            info_format,
        )

        worksheet.write(f"E{len(liv_mois)+5}", "Total dépense", header_format)
        worksheet.write(
            f"F{len(liv_mois)+5}",
            str("{:.2f}".format(liv_mois[-1][2])).replace(".", ",") + "€",
            header_format,
        )

        worksheet.write(f"E{len(liv_mois)+6}", "Chiffre d'affaire", header_format)
        worksheet.write(
            f"F{len(liv_mois)+6}",
            str("{:.2f}".format(liv_mois[-1][1])).replace(".", ",") + "€",
            header_format,
        )

        worksheet.write(f"E{len(liv_mois)+8}", "Nombre de commande", header_format)
        worksheet.write(f"F{len(liv_mois)+8}", str(nbre_commande), header_format)

        worksheet.write(f"E{len(liv_mois)+9}", "Solde utilisateur", header_format)
        worksheet.write(
            f"F{len(liv_mois)+9}",
            str("{:.2f}".format(user_solde)).replace(".", ",") + "€",
            header_format,
        )

        worksheet.write(
            f"G{len(liv_mois)+9}",
            "NB : Le solde utilisateur est calculé au moment de la génération du Excel",
            info_format,
        )

        worksheet.set_column(
            "A:A", col_widths[0] + 2
        )  # Ajout d'une marge pour rendre le texte plus aéré
        worksheet.set_column("B:B", col_widths[1] + 2)
        worksheet.set_column("C:C", col_widths[2] + 2)
        worksheet.set_column("D:D", col_widths[3] + 2)
        worksheet.set_column("E:E", col_widths[4] + 2)
        worksheet.set_column("F:F", col_widths[5] + 2)
        worksheet.set_column(
            "G:G",
            len(
                "NB : Le solde utilisateur est calculé au moment de la génération du Excel"
            )
            + 2,
        )

        worksheet2.write("A1", "Détail des commandes du mois", header_format)
        worksheet2.write("A2", f"{year}-{month:02}", date_format)
        worksheet2.write("A4", "Utilisateur", header_format)
        worksheet2.write("B4", "Date de la commande", header_format)
        worksheet2.write("C4", "Contenu de la commande", header_format)
        worksheet2.write("D4", "Total de la commande", header_format)

        col_widths = [
            len("Utilisateur"),
            len("Date de la commande"),
            len("Contenu de la commande"),
            len("Total de la commande"),
        ]

        compteur = 0
        for i in commande_query:
            worksheet2.write(f"A{5+compteur}", str(i.client), table)
            worksheet2.write(f"B{5+compteur}", str(i.date), table)

            produits = json.loads(i.produit)
            produits_text = "\n".join(
                str(produit[1]) + " " + str(produit[0]) for produit in produits
            )
            worksheet2.write(f"C{5+compteur}", str(produits_text), table_with_wrap)

            worksheet2.write(
                f"D{5+compteur}",
                str("{:.2f}".format(i.total_commande)).replace(".", ","),
                table,
            )

            col_widths[0] = max(col_widths[0], len(str(i.client)))
            col_widths[1] = max(col_widths[1], len(str(i.date)))
            col_widths[2] = max(col_widths[2], len(str(i.produit)))
            col_widths[3] = max(col_widths[3], len(f"{i.total_commande:.2f}"))

            compteur += 1

        worksheet2.set_column(
            "A:A", col_widths[0] + 2
        )  # Ajout d'une marge pour un affichage aéré
        worksheet2.set_column("B:B", col_widths[1] + 2)
        worksheet2.set_column("C:C", col_widths[2] + 2)
        worksheet2.set_column("D:D", col_widths[3] + 2)

        workbook.close()

        # Mise du tableur dans la réponse
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = f"BilanCommande_{month:02}_{year}.xlsx"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    def form_invalid(self, form):
        # Gérer les erreurs du formulaire
        return self.render_to_response(self.get_context_data(form=form))


def add_livraison_mois(livraison):
    liv_mois = []
    temp = []

    for i in livraison:
        for j in i:
            temp.append(j)

    liv_mois = [temp[0]]

    for i in temp[1:]:
        compteur = 0
        for j in liv_mois:
            if i[0] == j[0]:
                a = int(j[1]) + int(i[1])
                j[1] = str(a)
                break
            compteur += 1

        if compteur == len(liv_mois):
            liv_mois.append(i.copy())

    total_depense = 0
    total_ca = 0
    for i in liv_mois:
        produit = Produit.objects.get(nom=i[0])
        prix_achat = produit.prix_achat
        prix_vente = produit.prix

        chiffre_affaire = int(i[1]) * prix_vente
        depense = -1 * (int(i[1]) * prix_achat)

        benefice = chiffre_affaire - depense
        total_ca += chiffre_affaire

        i.append(prix_vente)
        i.append(prix_achat)
        i.append(chiffre_affaire)
        i.append(depense)
        i.append(benefice)

        total_depense += depense

    liv_mois.append(["Total", total_ca, total_depense, "", "", "", ""])

    return liv_mois


class ModificationCommandeView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Modification d'une commande"
    permission_required = ("auth.view_group",)  # Ajout de la permission
    template_name = "admin/modification.html"


def get_commandes_by_date(request):
    date_str = request.GET.get("date", None)
    commandes_data = []

    if date_str:
        try:
            # Convertir la chaîne de date en objet date
            selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            commandes = Commande.objects.filter(date=selected_date)
            # Préparer les données des commandes pour le JSON
            commandes_data = [
                {
                    "id": commande.id,
                    "client": str(commande.client),
                    "total": commande.total_commande,
                    # Ajoutez d'autres champs au besoin
                }
                for commande in commandes
            ]
        except ValueError:
            # Gérer le cas où la date n'est pas valide
            pass
    return JsonResponse(commandes_data, safe=False)


def get_commandes_details(request, commande_id):
    produit_data = []
    try:
        commande = Commande.objects.get(id=commande_id)
        commande_produit = json.loads(commande.produit)

        produit_data = [
            {"nom": produit[0], "quantite": produit[1]} for produit in commande_produit
        ]

    except Commande.DoesNotExist:
        return JsonResponse({"error": "Commande non trouvée."}, status=404)

    return JsonResponse(produit_data, safe=False)


@csrf_exempt
def delete_commandes(request, commande_id):
    try:
        commande = Commande.objects.get(id=commande_id)
        date_livraison = commande.date
        total = commande.total_commande
        produit_commande = json.loads(commande.produit)

        utilisateur = Utilisateur.objects.get(
            **{Utilisateur.USERNAME_FIELD: commande.client}
        )

        livraison = Livraison.objects.get(date=date_livraison)
        produit_livraison = json.loads(livraison.produit)

        for p in produit_commande:
            for m in produit_livraison:
                if p[0] == m[0]:
                    new = int(m[1]) - int(p[1])
                    m[1] = str(new)

        livraison.produit = json.dumps(produit_livraison)
        livraison.save()

        commande.delete()

        utilisateur.credit += total
        utilisateur.save()

        return JsonResponse({"success": True})
    except Commande.DoesNotExist:
        return JsonResponse({"error": "Commande non trouvée."}, status=404)
    except Livraison.DoesNotExist:
        return JsonResponse({"error": "Livraison non trouvée."}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def PrecreateUserFunction(user, request):
    return PrecreateUsersFunction([user], request)


def PrecreateUsersFunction(users, request):
    # Create users in DB
    for user in users:
        user.date_joined = None  # To indicate that the user hasn't yet joined
        user.is_active = False
        user.save()

    # Send pre-creation emails
    emails = []
    template_name = "mail/precreation_mail.html"
    for user in users:
        user_pk_bytes = force_bytes(Utilisateur._meta.pk.value_to_string(user))
        token = PasswordResetTokenGenerator().make_token(user)
        convert_to_html_content = render_to_string(
            template_name=template_name,
            context={
                "request": request,
                "uid": urlsafe_base64_encode(user_pk_bytes),
                "token": token,
                "user": user,
            },
        )
        emails.append(
            (
                "Création de ton compte Pain'Gouin",
                html_to_text(convert_to_html_content),
                convert_to_html_content,
                settings.EMAIL_HOST_USER,
                [
                    user.email,
                ],
            )
        )

    send_mass_html_mail(emails, fail_silently=True)


class PrecreateUserView(UnfoldModelAdminViewMixin, FormView):
    title = "Précréation de compte utilisateur"
    form_class = PrecreateUserForm
    permission_required = ("auth.view_group",)
    template_name = "admin/precreate_user.html"
    success_url = reverse_lazy("admin:precreation_utilisateur")

    def form_valid(self, form):

        # Create user in DB
        user = form.save(commit=False)
        PrecreateUserFunction(user, self.request)

        messages.success(self.request, "Utilisateur bien pré-créé")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur, utilisateur non créé.")
        return super().form_invalid(form)


class PrecreateUsersView(UnfoldModelAdminViewMixin, FormView):
    title = "Précréation de compte utilisateur"
    permission_required = ("auth.view_group",)
    template_name = "admin/precreate_users.html"
    success_url = reverse_lazy("admin:precreation_utilisateurs")

    def get_form_class(self, extra=3):
        return modelformset_factory(
            Utilisateur,
            form=PrecreateUserForm,
            extra=extra,  # number of empty forms to display
            can_delete=False,
        )

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(queryset=Utilisateur.objects.none(), **self.get_form_kwargs())

    def form_valid(self, formset):

        valid_users = []
        invalid_forms_indices = []

        for i, form in enumerate(formset):
            if form.is_valid() and form.has_changed():
                valid_users.append(form.save(commit=False))
            elif form.has_changed():
                # keep invalid or empty forms for re-rendering
                invalid_forms_indices.append(i)

        PrecreateUsersFunction(valid_users, self.request)

        if valid_users:
            messages.success(
                self.request, f"{len(valid_users)} utilisateur(s) bien pré-créés"
            )

        if invalid_forms_indices:
            messages.error(
                self.request,
                f"{len(invalid_forms_indices)} formulaire(s) contiennent des erreurs et doivent être corrigés.",
            )

            # Rebuild formset with only invalid forms
            Formset = self.get_form_class(extra=len(invalid_forms_indices))
            # Pass in data from the original request to preserve errors
            new_formset = Formset(
                data=self.request.POST,
                queryset=Utilisateur.objects.none(),
            )
            # Delete all non invalid forms
            for i, form in reversed(list(enumerate(new_formset.forms))):
                if i not in invalid_forms_indices:
                    del new_formset.forms[i]

            return self.render_to_response(self.get_context_data(form=new_formset))

        return super().form_valid(formset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "precreateuser_formset_helper": PrecreateUsersFormHelper(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables.
        """
        # I need the form to be passed even if not valid
        form = self.get_form()
        return self.form_valid(form)


class CustomAdmin(BaseGroupAdmin, ModelAdmin):
    actions = None

    def get_urls(self):
        custom_urls = [
            path("solde/", SoldeView.as_view(model_admin=self), name="solde"),
            path(
                "solde/autocomplete_user/", autocomplete_user, name="autocomplete_user"
            ),
            path("solde/get_user_solde/", get_user_solde, name="get_user_solde"),
            path("solde/update_credit/", update_credit, name="update_credit"),
            path("solde/add_credit/", add_credit, name="add_credit"),
            path("tableur/", TableurView.as_view(model_admin=self), name="tableur"),
            path(
                "modification_commande/",
                ModificationCommandeView.as_view(model_admin=self),
                name="modification_commande",
            ),
            path(
                "modification_commande/date/",
                get_commandes_by_date,
                name="get_commandes_by_date",
            ),
            path(
                "modification_commande/<int:commande_id>/details/",
                get_commandes_details,
                name="detailler_commande",
            ),
            path(
                "modification_commande/<int:commande_id>/supprimer/",
                delete_commandes,
                name="detailler_commande",
            ),
            path(
                "precreation_utilisateur/",
                PrecreateUserView.as_view(model_admin=self),
                name="precreation_utilisateur",
            ),
            path(
                "precreation_utilisateurs/",
                PrecreateUsersView.as_view(model_admin=self),
                name="precreation_utilisateurs",
            ),
        ]
        return custom_urls + super().get_urls()


admin.site.unregister(Group)
admin.site.register(Group, CustomAdmin)

admin.site.register(Livraison, LivraisonAdmin)
