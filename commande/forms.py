# authentication/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, SetPasswordForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError

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

    def clean_email(self):
        """Check if user had been precreated, and reject usernames that differ only in case."""
        email = self.cleaned_data.get("email")
        if (
            email
            and self._meta.model.objects.filter(email__iexact=email).exists()
        ):
            existing_user = self._meta.model.objects.get(email__iexact=email)
            if existing_user.date_joined is None:
                # The user had been precreated, but it has not yet been finally created.
                self.instance = existing_user
                return email
            else:
                self._update_errors(
                    ValidationError(
                        {
                            "email": self.instance.unique_error_message(
                                self._meta.model, ["email"]
                            )
                        }
                    )
                )
        else:
            return email
    
    def save(self, commit = True):
        if self.instance.date_joined is None:
            self.instance.date_joined = datetime.datetime.now()
        return super().save(commit)


class FinishSignupForm(SetPasswordForm, forms.ModelForm):
    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = ('email', 'first_name', 'last_name', 'chambre', 'tel', 'isPermis')
    
    def save(self, commit = True):
        user = super().save(commit=False)
        for field in self.Meta.fields:
            setattr(user, field, self.cleaned_data[field])
        
        if not user.is_active:
            user.is_active = True
        
        if commit:
            user.save()

        return user


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
        fields = ('first_name', 'last_name', 'email', 'isLivreur', 'isPermis')
        widgets = {
            'email': UnfoldAdminEmailInputWidget(),
            'isPermis': UnfoldBooleanSwitchWidget(),
            'isLivreur': UnfoldBooleanSwitchWidget(),
            'first_name': UnfoldAdminTextInputWidget(),
            'last_name': UnfoldAdminTextInputWidget(),
            }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['first_name'].required = False
        self.fields['last_name'].required = False

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Pré-créer un utilisateur',
                'email',
                'first_name',
                'last_name',
                'isPermis', 
                'isLivreur',
                css_class="mb-8"
            ),
        )
        self.helper.add_input(Submit("Pré-créer", "Pré-créer"))

class PrecreateUsersFormHelper(FormHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = "unfold_crispy/layout/table_inline_formset.html"
        self.form_id = "driver-formset"
        self.form_add = True
        self.form_show_labels = False
        self.attrs = {
            "novalidate": "novalidate",
        }
        self.add_input(Submit("submit", _("Pré-créer")))
