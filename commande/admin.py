from django.contrib import admin

# Register your models here.
from .models import Utilisateur, Produit, CategorieProduit, Commande, Livraison

admin.site.register(Utilisateur)
admin.site.register(Produit)
admin.site.register(CategorieProduit)
admin.site.register(Commande)
admin.site.register(Livraison)