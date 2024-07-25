from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.models import UserManager

from datetime import datetime

# Create your models here.

class Utilisateur(AbstractUser):
    username = models.EmailField(unique=True, null=True)
    isLivreur = models.BooleanField(default = False)
    isPermis = models.BooleanField(default= False)
    chambre = models.CharField(max_length=10)
    tel = models.CharField(max_length=20)
    last_login = models.DateTimeField(default=datetime.now)
    last_order = models.DateTimeField(default=datetime.now)
    created_at = models.DateTimeField(default=datetime.now)
    credit = models.FloatField(default=0)
    
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

class CategorieProduit(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.nom

class Produit(models.Model):
    nom = models.CharField(max_length=100)
    image = models.FileField(upload_to="images")
    prix = models.FloatField(default=0)
    isQuota = models.BooleanField(default=False, verbose_name="Présence de quota pour le produit")
    quota = models.IntegerField(default=0)
    categorie = models.ForeignKey(CategorieProduit, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.nom
    
class Livraison(models.Model):
    date = models.DateField(default=datetime.now)
    produit = models.JSONField(default=dict)

class Commande(models.Model):
    client = models.ForeignKey(Utilisateur, on_delete = models.CASCADE)
    date = models.ForeignKey(Livraison, on_delete=models.CASCADE)
    produit = models.ManyToManyField(Produit)
    total_commande = models.FloatField(default=0)

    def __str__(self) -> str:
        return "Commande de " + str(self.client) + " pour le " + str(self.date)
