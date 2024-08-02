from django.contrib import admin
from django.views.generic import TemplateView
from unfold.admin import ModelAdmin
from unfold.views import UnfoldModelAdminViewMixin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.urls import path
from django.contrib.auth.models import Group
from .models import Utilisateur, Produit, CategorieProduit, Commande, Livraison

# Enregistrer les autres modèles
admin.site.register(Utilisateur)
admin.site.register(Produit)
admin.site.register(CategorieProduit)
admin.site.register(Commande)
admin.site.register(Livraison)

class MyClassBasedView(UnfoldModelAdminViewMixin, TemplateView):
    title = "Gestion des soldes"  # required: custom page header title
    permission_required = ("auth.view_group",)  # required: tuple of permissions
    template_name = "admin/solde.html"

class CustomAdmin(BaseGroupAdmin, ModelAdmin):
    def get_urls(self):
        custom_urls = [
            path("solde/", MyClassBasedView.as_view(model_admin=self), name="solde"),
        ]
        return custom_urls + super().get_urls()

admin.site.unregister(Group)
admin.site.register(Group, CustomAdmin)
