# authentication/forms.py
import datetime
from datetime import date

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError
from django.forms import BooleanField
from django.utils.translation import gettext_lazy as _
from unfold.contrib.import_export.forms import ExportForm
from unfold.layout import Submit
from unfold.widgets import (
    UnfoldAdminEmailInputWidget,
    UnfoldAdminTextInputWidget,
    UnfoldBooleanSwitchWidget,
)

from commande.utils import (
    SendMailVerification,
    WhitelistEmailValidator,
    first_editable_day,
)
from commande.widgets import DateRangeField, MultiDateField

from .models import Delivery


class LoginForm(forms.Form):
    email = forms.EmailField(max_length=63, label="Email")
    password = forms.CharField(
        max_length=63, widget=forms.PasswordInput, label="Mot de passe"
    )


class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = (
            "email",
            "first_name",
            "last_name",
            "room",
            "phone",
            "has_drivers_licence",
        )

    def clean_email(self):
        """Check if user had been precreated, and reject usernames that differ only in case."""
        email = self.cleaned_data.get("email")
        if email and self._meta.model.objects.filter(email__iexact=email).exists():
            existing_user = self._meta.model.objects.get(email__iexact=email)
            if existing_user.date_joined is None:
                # The user had been precreated, but it has not yet been finally created.
                self.instance = existing_user
                return email
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

    def save(self, commit=True):
        if self.instance.date_joined is None:
            self.instance.date_joined = datetime.datetime.now()

        if not self.instance.is_active:
            # The user was precreated, but eventually ended-up signing up normally
            self.instance.is_active = True

        return super().save(commit)


class FinishSignupForm(SetPasswordForm, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevents modification in the UI and ignores POST data for this field
        if "email" in self.fields:
            self.fields["email"].disabled = True

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = (
            "email",
            "first_name",
            "last_name",
            "room",
            "phone",
            "has_drivers_licence",
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        for field in self.Meta.fields:
            setattr(user, field, self.cleaned_data[field])

        if not user.is_active:
            user.is_active = True

        if commit:
            user.save()

        return user


class UpdateForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        # Pop 'request' so it doesn't get passed to the parent UserChangeForm
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    class Meta(UserChangeForm.Meta):
        model = get_user_model()
        fields = (
            "email",
            "first_name",
            "last_name",
            "room",
            "phone",
            "has_drivers_licence",
            "get_order_email",
        )

    def save(self, commit=True):
        user = super().save(commit=False)

        # Check if the email field is in changed_data
        if "email" in self.changed_data:
            new_email = self.cleaned_data.get("email")

            # Revert the email on the instance so it doesn't save to the DB yet
            old_email = (
                self.instance.pk
                and get_user_model().objects.get(pk=self.instance.pk).email
            )  # The instance still has the old email until we save it
            user.email = old_email

            SendMailVerification(user, new_email, self.request)
            messages.success(
                self.request,
                "Un lien vient de t'être envoyé afin de finaliser le changement d'email.",
            )

        if commit:
            user.save()
        return user


class ProductOrderForm(forms.Form):
    quantity = forms.IntegerField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "69",
                "aria-describedby": "helper-text-explanation",
                "value": "0",
                "data-input-counter-min": "0",
                "data-input-counter-max": "20",
                "data-input-counter": None,
            }
        )
    )


class PrecreateUserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = (
            "first_name",
            "last_name",
            "email",
            "is_delivery_man",
            "has_drivers_licence",
            "verified_genuine_user",
        )
        widgets = {
            "email": UnfoldAdminEmailInputWidget(),
            "has_drivers_licence": UnfoldBooleanSwitchWidget(),
            "is_delivery_man": UnfoldBooleanSwitchWidget(),
            "first_name": UnfoldAdminTextInputWidget(),
            "last_name": UnfoldAdminTextInputWidget(),
            "verified_genuine_user": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["verified_genuine_user"].initial = True

        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                "Pré-créer un utilisateur",
                "email",
                "first_name",
                "last_name",
                "has_drivers_licence",
                "is_delivery_man",
                css_class="mb-8",
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


class bulkCreateDeliveriesForm(forms.Form):
    dates = MultiDateField(required=False, min_date=first_editable_day)
    cancel_orders = BooleanField(
        initial=False,
        widget=UnfoldBooleanSwitchWidget(),
        label=_("Annuler les commandes clients si nécessaire ?"),
        help_text=_("En cas de suppression d'une date existante."),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Update the initial value dynamically
        self.old_dates = list(
            Delivery.objects.editable().values_list("date", flat=True)
        )
        self.fields["dates"].initial = self.old_dates


class CustomOrderProductExportForm(ExportForm):
    date_range = DateRangeField(
        label="Période",
        required=True,
        min_date=lambda: Delivery.objects.order_by("date").first().date,
        max_date=date.today,
    )


class CheckGenuineUserForm(forms.Form):
    email = forms.EmailField(
        validators=[
            WhitelistEmailValidator(whitelist=settings.VERIFIED_USER_EMAIL_DOMAINS)
        ]
    )


class TopupForm(forms.Form):
    amount = forms.DecimalField()  # Redefined in __init__

    def __init__(self, min_amount=0.5, max_amount=99, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount"] = forms.DecimalField(
            min_value=min_amount, max_value=max_amount, decimal_places=2, max_digits=4
        )
