from django.contrib import admin
from django.views.generic import TemplateView
from unfold.admin import ModelAdmin
from unfold.views import UnfoldModelAdminViewMixin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.urls import path
from django.contrib.auth.models import Group
from .models import Utilisateur, Produit, CategorieProduit, Commande, Livraison
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt



# Enregistrer les autres modèles
admin.site.register(Utilisateur)
admin.site.register(Produit)
admin.site.register(CategorieProduit)
admin.site.register(Commande)
admin.site.register(Livraison)

class SoldeView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Gestion des soldes"
    permission_required = ("auth.view_group",)
    template_name = "admin/solde.html"

def autocomplete_user(request):
    if 'term' in request.GET:
        qs = Utilisateur.objects.filter(
            first_name__icontains=request.GET.get('term'),
        )
        names = list()
        for user in qs:
            names.append(user.first_name + ' ' + user.last_name)
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
            user.credit = new_credit
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

class CustomAdmin(BaseGroupAdmin, ModelAdmin):
    def get_urls(self):
        custom_urls = [
            path("solde/", SoldeView.as_view(model_admin=self), name="solde"),
            path('solde/autocomplete_user/', autocomplete_user, name='autocomplete_user'),
            path('solde/get_user_solde/', get_user_solde, name='get_user_solde'),
            path("solde/update_credit/", update_credit, name="update_credit"),
            path("solde/add_credit/", add_credit, name="add_credit"),
        ]
        return custom_urls + super().get_urls()

admin.site.unregister(Group)
admin.site.register(Group, CustomAdmin)
