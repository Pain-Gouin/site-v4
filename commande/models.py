from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.contrib.auth.models import UserManager

from datetime import datetime

import json

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

def defaultJson():
    return ["None"]

class Livraison(models.Model):
    date = models.DateField(default=datetime.now)
    produit = models.JSONField(default=defaultJson)

    def __str__(self) -> str:
        return str(self.date)

class Commande(models.Model):
    client = models.CharField(max_length=100)
    date = models.DateField()
    produit = models.JSONField(default=defaultJson)
    chambre = models.CharField(max_length=10)
    total_commande = models.FloatField(default=0)

    def __str__(self) -> str:
        return "Commande de " + str(self.client) + " pour le " + str(self.date)
