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
