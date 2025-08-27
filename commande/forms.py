# authentication/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model

from django.forms import ModelForm

from .models import Produit, Livraison

import datetime
import re

from django.forms.widgets import Widget, Select
from django.utils.dates import MONTHS
from django.utils.safestring import mark_safe

class LoginForm(forms.Form):
    username = forms.CharField(max_length=63, label='Email')
    password = forms.CharField(max_length=63, widget=forms.PasswordInput, label='Mot de passe')

class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'chambre', 'tel','isPermis')
        

class UpdateForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('username', 'first_name', 'last_name', 'chambre', 'tel', 'isPermis', 'getOrderMail')


class ProductOrderForm(forms.Form):
    quantity = forms.IntegerField(widget=forms.TextInput(attrs={'placeholder': '69',  'aria-describedby':'helper-text-explanation', 'value':"0", 'data-input-counter-min':"0", 'data-input-counter-max':"20", 'data-input-counter':None}))

class LivraisonForm(forms.ModelForm):
    class Meta:
        model = Livraison
        exclude = ["produit"]



class ExportForm(forms.Form):
    mois = forms.DateField(
        required=True,
        widget=forms.DateInput(attrs={'type': 'date'})
    )