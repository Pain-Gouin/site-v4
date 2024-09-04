from django.contrib import admin
from django.views.generic import TemplateView, FormView
from unfold.admin import ModelAdmin
from unfold.views import UnfoldModelAdminViewMixin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.urls import path
from django.contrib.auth.models import Group
from .models import Utilisateur, Produit, CategorieProduit, Commande, Livraison
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from io import BytesIO
import xlsxwriter
from django.http import HttpResponse
from django.shortcuts import render
import json

from django.db.models import Q


from .forms import LivraisonForm, ExportForm



# Enregistrer les autres modèles
admin.site.register(Produit)
admin.site.register(CategorieProduit)
admin.site.register(Commande)
admin.site.register(Livraison)

class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'email', 'isLivreur', 'isPermis', 'credit', 'last_login', 'last_order', 'created_at')
    search_fields = ('last_name', 'first_name', 'email')  # Pour faciliter la recherche par nom ou email
    list_filter = ('isLivreur', 'isPermis')  # Pour ajouter des filtres sur les colonnes booléennes

admin.site.register(Utilisateur, UtilisateurAdmin)


class LivraisonAdmin(admin.ModelAdmin):
    exclude = ["produit"]
    form = LivraisonForm

class SoldeView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Gestion des soldes"
    permission_required = ("auth.view_group",)
    template_name = "admin/solde.html"

def autocomplete_user(request):
    if 'term' in request.GET:
        term = request.GET.get('term')
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
                Q(first_name__icontains=terms[0], last_name__icontains=terms[-1]) |
                Q(first_name__icontains=terms[-1], last_name__icontains=terms[0])
            )

        names = [f"{user.first_name} {user.last_name}" for user in qs]
        return JsonResponse(names, safe=False)
    

def get_user_solde(request):
    if 'first_name' in request.GET and 'last_name' in request.GET:
        first_name = request.GET.get('first_name')
        last_name = request.GET.get('last_name')
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            return JsonResponse({'solde': user.credit})
        except Utilisateur.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def update_credit(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        new_credit = request.POST.get('new_credit')
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            user.credit = float(new_credit)
            user.save()
            return JsonResponse({'message': 'Crédit mis à jour avec succès.'})
        except Utilisateur.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def add_credit(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        add_credit = request.POST.get('add_credit')
        try:
            user = Utilisateur.objects.get(first_name=first_name, last_name=last_name)
            user.credit += float(add_credit)
            user.save()
            return JsonResponse({'message': 'Crédit ajouté avec succès.', 'new_solde': user.credit})
        except Utilisateur.DoesNotExist:
            return JsonResponse({'error': 'Utilisateur non trouvé'}, status=404)
    return JsonResponse({'error': 'Invalid request'}, status=400)


class TableurView(UnfoldModelAdminViewMixin, FormView):
    title = "Export d'un tableur"
    permission_required = ("auth.view_group",)
    template_name = "admin/tableur.html"
    form_class = ExportForm

    def form_valid(self, form):
        month = form.cleaned_data['mois']
        year = month.year
        month = month.month

        try:
            livraison_query = Livraison.objects.filter(date__year=year, date__month=month)
            produit = []
            for liv in livraison_query:
                if liv.produit != ['None'] and liv.produit !='[]':
                    produit.append(json.loads(liv.produit))
        except Exception as e:
            print(f"Error: {e}")
            livraison_query = None
            produit = "Pas de produit commandé"
        
        liv_mois = add_livraison_mois(produit)

        # Création du tableur
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Création des styles du tableur
        header_format = workbook.add_format({
            'bold': True,
            'align':'center',
            'valign': 'vcenter',
            'bg_color': '#f4dcdc',
            'border': 1
        })

        produit_format = workbook.add_format({
            'bg_color':'#f9e8e8',
            'align':'center',
            'valign': 'vcenter',
            'border':1
        })

        table = workbook.add_format({
            'border':1,
            'align':'center',
            'valign': 'vcenter',
        })

        info_format = workbook.add_format({
            'italic':True,
        })

        date_format = workbook.add_format({'num_format': 'mm-yyyy'})

        worksheet = workbook.add_worksheet()
        worksheet.write('A1', 'Mois', header_format)
        worksheet.write('A2', f'{year}-{month:02}', date_format)
        worksheet.write('A4', 'Produit', header_format)
        worksheet.write('B4', 'Quantité', header_format)
        worksheet.write('C4', 'Prix de vente', header_format)
        worksheet.write('D4', 'Prix d\'achat', header_format)
        worksheet.write('E4', 'Chiffre d\'affaire du produit', header_format)
        worksheet.write('F4', 'Dépense sur le produit', header_format)

        col_widths = [len('Produit'), len('Quantité'), len('Prix de vente'), len('Prix d\'achat'), len('Chiffre d\'affaire du produit'), len('Dépense sur le produit')]

        for i in range(len(liv_mois)-1):
            worksheet.write(f'A{5+i}', str(liv_mois[i][0]), produit_format)
            worksheet.write(f'B{5+i}', str(liv_mois[i][1]), table)
            worksheet.write(f'C{5+i}', str(liv_mois[i][2]), table)
            worksheet.write(f'D{5+i}', str(liv_mois[i][3]), table)
            worksheet.write(f'E{5+i}', str("{:.2f}".format(liv_mois[i][4])), table)
            worksheet.write(f'F{5+i}', str("{:.2f}".format(liv_mois[i][5])), table)

            col_widths[0] = max(col_widths[0], len(str(liv_mois[i][0])))
            col_widths[1] = max(col_widths[1], len(str(liv_mois[i][1])))
            col_widths[2] = max(col_widths[2], len(str(liv_mois[i][2])))
            col_widths[3] = max(col_widths[3], len(str(liv_mois[i][3])))
            col_widths[4] = max(col_widths[4], len(str("{:.2f}".format(liv_mois[i][4]))))
            col_widths[5] = max(col_widths[5], len(str("{:.2f}".format(liv_mois[i][5]))))

        
        worksheet.write('A3', 'Tout étant automatisé, veuillez vérifier la cohérence des résultats et contacter le responsable web en cas de problème',info_format)

        
        worksheet.write(f'E{len(liv_mois)+5}', 'Total dépense', header_format)
        worksheet.write(f'F{len(liv_mois)+5}', str("{:.2f}".format(liv_mois[-1][2])), header_format)


        worksheet.set_column('A:A', col_widths[0] + 2)  # Ajout d'une marge pour rendre le texte plus aéré
        worksheet.set_column('B:B', col_widths[1] + 2)
        worksheet.set_column('C:C', col_widths[2] + 2)
        worksheet.set_column('D:D', col_widths[3] + 2)
        worksheet.set_column('E:E', col_widths[4] + 2)
        worksheet.set_column('F:F', col_widths[5] + 2)

        workbook.close()

        # Mise du tableur dans la réponse
        output.seek(0)
        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'BilanCommande_{month:02}_{year}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response


    
    def form_invalid(self, form):
        # Gérer les erreurs du formulaire
        return self.render_to_response(self.get_context_data(form=form))


def add_livraison_mois(livraison):
    liv_mois = []
    temp = []

    for i in livraison :
        for j in i :
            temp.append(j)

    liv_mois = [temp[0]]
    
    for i in temp[1:]:
        compteur = 0
        for j in liv_mois:
            if i[0] == j[0]:
                a = int(j[1]) + int(i[1])
                j[1] = str(a)
                break
            compteur +=1

        if compteur == len(liv_mois):
            liv_mois.append(i.copy())

    total_depense = 0
    for i in liv_mois:
        produit = Produit.objects.get(nom = i[0])
        prix_achat = produit.prix_achat
        prix_vente = produit.prix

        chiffre_affaire = int(i[1]) * prix_vente
        depense = -1*(int(i[1])*prix_achat)

        benefice = chiffre_affaire - depense

        i.append(prix_vente)
        i.append(prix_achat)
        i.append(chiffre_affaire)
        i.append(depense)
        i.append(benefice)

        total_depense += depense

    liv_mois.append(["Total", "", total_depense,"","","",""])

    return liv_mois




class CustomAdmin(BaseGroupAdmin, ModelAdmin):
    def get_urls(self):
        custom_urls = [
            path("solde/", SoldeView.as_view(model_admin=self), name="solde"),
            path('solde/autocomplete_user/', autocomplete_user, name='autocomplete_user'),
            path('solde/get_user_solde/', get_user_solde, name='get_user_solde'),
            path("solde/update_credit/", update_credit, name="update_credit"),
            path("solde/add_credit/", add_credit, name="add_credit"),
            path("tableur/", TableurView.as_view(model_admin=self), name="tableur"),
        ]
        return custom_urls + super().get_urls()

admin.site.unregister(Group)
admin.site.register(Group, CustomAdmin)

admin.site.unregister(Livraison)
admin.site.register(Livraison, LivraisonAdmin)