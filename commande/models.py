from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.auth.models import UserManager
from django.utils.translation import gettext_lazy as _

from datetime import datetime, time
from django.utils import timezone

import json

# Create your models here.

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True, null=True)

    # Taken from AbstractBaseUser
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    # End of taken from AbstractUser

    isLivreur = models.BooleanField(default = False)
    isPermis = models.BooleanField(default= False)
    getOrderMail = models.BooleanField(default=True)
    chambre = models.CharField(max_length=10)
    tel = models.CharField(max_length=20)
    last_login = models.DateTimeField(default=datetime.now)
    last_order = models.DateTimeField(default=datetime.now)
    created_at = models.DateTimeField(default=datetime.now)
    credit = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

class CategorieProduit(models.Model):
    nom = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.nom

class Produit(models.Model):
    nom = models.CharField(max_length=100)
    image = models.FileField(upload_to="images")
    prix = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    prix_achat = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    isQuota = models.BooleanField(default=False, verbose_name="Présence de quota pour le produit")
    quota = models.IntegerField(default=0)
    categorie = models.ForeignKey(CategorieProduit, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return self.nom

def defaultJson():
    return ["None"]

class LivraisonQuerySet(models.QuerySet):
    def modifiable(self):
        current_time = timezone.now()
        today = current_time.date()

        if current_time.time() < time(6, 30):
            qs = self.filter(date__gte=today).order_by("date")
        else:
            qs = self.filter(date__gt=today).order_by("date")
        
        return qs

class Livraison(models.Model):
    date = models.DateField(default=datetime.now, unique=True)
    produit = models.JSONField(default=defaultJson)

    objects = LivraisonQuerySet.as_manager()

    @property
    def est_modifiable(self):
        return Livraison.objects.filter(id=self.id).modifiable().exists()

    def __str__(self) -> str:
        return str(self.date)

class Commande(models.Model):
    client = models.CharField(max_length=100)
    date = models.DateField()
    produit = models.JSONField(default=defaultJson)
    chambre = models.CharField(max_length=10)
    total_commande = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    @property
    def est_modifiable(self):
        return Livraison.objects.filter(date=self.date).modifiable().exists()

    def __str__(self) -> str:
        return "Commande de " + str(self.client) + " pour le " + str(self.date)
