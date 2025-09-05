# authentication/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from django.forms import ModelForm

from .models import Produit, Livraison

import datetime
import re

from django.forms.widgets import Widget, Select
from django.utils.dates import MONTHS
from django.utils.safestring import mark_safe

from unfold.widgets import (
    UnfoldAdminCheckboxSelectMultiple,
    UnfoldAdminDateWidget,
    UnfoldAdminEmailInputWidget,
    UnfoldAdminExpandableTextareaWidget,
    UnfoldAdminFileFieldWidget,
    UnfoldAdminImageFieldWidget,
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminMoneyWidget,
    UnfoldAdminRadioSelectWidget,
    UnfoldAdminSelect2Widget,
    UnfoldAdminSplitDateTimeWidget,
    UnfoldAdminTextareaWidget,
    UnfoldAdminTextInputWidget,
    UnfoldAdminTimeWidget,
    UnfoldAdminURLInputWidget,
    UnfoldBooleanSwitchWidget,
)

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset
from unfold.layout import Submit


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=63, label='Email')
    password = forms.CharField(max_length=63, widget=forms.PasswordInput, label='Mot de passe')

class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', 'chambre', 'tel','isPermis')


class UpdateForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', 'chambre', 'tel', 'isPermis', 'getOrderMail')


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

class PrecreateUserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('email', 'isPermis', 'isLivreur')
        widgets = {
            'email': UnfoldAdminEmailInputWidget(),
            'isPermis': UnfoldBooleanSwitchWidget(),
            'isLivreur': UnfoldBooleanSwitchWidget(),
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Pré-créer un utilisateur',
                'email',
                'isPermis', 
                'isLivreur',
                css_class="mb-8"
            ),
        )
        self.helper.add_input(Submit("Pré-créer", "Pré-créer"))
