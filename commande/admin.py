from django.contrib import admin, messages
from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models import QuerySet
from django.forms import modelformset_factory
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import path, reverse_lazy
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from imagekit.admin import AdminThumbnail
from import_export.admin import ExportMixin
from import_export.resources import ModelResource
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectMultipleFilter,
    BooleanRadioFilter,
    ChoicesDropdownFilter,
    ChoicesRadioFilter,
    MultipleRelatedDropdownFilter,
    SliderNumericFilter,
)
from unfold.decorators import action
from unfold.enums import ActionVariant
from unfold.views import UnfoldModelAdminViewMixin

from .forms import (
    CustomOrderProductExportForm,
    PrecreateUserForm,
    PrecreateUsersFormHelper,
    bulkCreateDeliveriesForm,
)
from .models import (
    Delivery,
    HelloAssoCheckout,
    Order,
    OrderProduct,
    Product,
    ProductCategory,
    Transaction,
    User,
)
from .utils import PrecreateUserFunction, PrecreateUsersFunction, append_unique_in_order


class CustomModelAdmin(ModelAdmin):
    """A custom admin class that allows superusers to see and edit everything,"""

    STAFF_EDITABLE_FIELDS = None  # Fields that staff can edit. If empty, can edit everything. If not empty, can only edit what is specified.
    STAFF_HIDDEN_FIELDS = ["id"]  # Fields that staff won't be able to see
    STAFF_CREATION_HIDDEN_FIELDS = (
        None  # Fields that staff won't be able to see in the creation page
    )
    STAFF_CAN_CREATE = None  # Whether staff can create a new object. If not set uses the default permissions using group permissions.
    sorted_fields: list[
        str
    ] = []  # Sort order of fields (fields not specified will be shown after them)
    additional_fields: list[
        str
    ] = []  # Fields that would not otherwise be shown to superusers because they are not direct fields of the model
    compressed_fields = True  # For Django Unfold display style
    warn_unsaved_form = True
    list_filter_submit = True

    def get_fields(self, request, obj=None):
        """
        Hook for specifying fields based on roles.
        """
        # Show fields not explicitly hidden to staff members (to allow ordering using self.fields)
        if request.user.is_staff:
            return [
                f
                for f in append_unique_in_order(
                    self.sorted_fields,
                    super().get_fields(request, obj=obj),
                    self.additional_fields,
                )
                if (f not in self.STAFF_HIDDEN_FIELDS)
                and (
                    (self.STAFF_CREATION_HIDDEN_FIELDS is None)
                    or (obj is not None)
                    or (f not in self.STAFF_CREATION_HIDDEN_FIELDS)
                )
            ]

        return super().get_fields(request, obj=obj)

    def get_fieldsets(self, request, obj=None):
        """
        Hook for specifying "advanced" fieldsets for superuser, showing all.
        """
        # Show everything to superusers
        if request.user.is_superuser:
            existant_fields = self.get_fields(request, obj)
            return [
                (None, {"fields": existant_fields}),
                (
                    "Superuser",
                    {
                        "classes": ["collapse"],
                        "fields": [
                            field
                            for field in append_unique_in_order(
                                self.sorted_fields,
                                [f.name for f in self.model._meta.fields],
                                self.additional_fields,
                            )
                            if field not in existant_fields
                        ],
                    },
                ),
            ]

        return super().get_fieldsets(request, obj=obj)

    def get_readonly_fields(self, request, obj=None):
        """
        Logic to restrict field editing for staff members.
        """
        # Superusers can edit anything
        if request.user.is_superuser:
            return (
                list(super().get_readonly_fields(request, obj)) + ["id"]
            )  # Else we get an error, because we are showing it but the field cannot be edited.

        # Staff (is_staff=True but not superuser)
        if (self.STAFF_EDITABLE_FIELDS is not None) and request.user.is_staff:
            # Return list of fields that are NOT in the allowed list
            # This effectively makes everything else read-only
            return append_unique_in_order(
                super().get_readonly_fields(request, obj),
                [
                    f.name
                    for f in self.model._meta.fields
                    if (
                        f.name not in self.STAFF_EDITABLE_FIELDS
                        and f.name not in self.STAFF_HIDDEN_FIELDS
                    )
                ],
            ) + ["id"]

        return super().get_readonly_fields(request, obj)

    def has_add_permission(self, request):
        if (
            (self.STAFF_CAN_CREATE is not None)
            and request.user.is_staff
            and (not request.user.is_superuser)
        ):
            return self.STAFF_CAN_CREATE

        return super().has_add_permission(request)


@admin.register(User)
class UserAdmin(CustomModelAdmin):
    list_display = (
        "__str__",
        "email",
        "is_delivery_man",
        "has_drivers_licence",
        "balance_cache",
        "calculated_last_order_date",
        "last_login",
    )  # Pour choisir ce qui s'affiche dans la liste des utilisateurs
    search_fields = (
        "last_name",
        "first_name",
        "email",
        "room",
    )  # Pour faciliter la recherche
    list_filter = (
        "is_delivery_man",
        "has_drivers_licence",
        "is_staff",
        "is_superuser",
    )  # Pour ajouter des filtres sur les colonnes booléennes

    STAFF_EDITABLE_FIELDS = [
        "is_delivery_man",
        "has_drivers_licence",
        "verified_genuine_user",
        "is_staff",
    ]
    STAFF_HIDDEN_FIELDS = ["id", "groups", "user_permissions"]
    STAFF_CAN_CREATE = False
    sorted_fields = [
        "first_name",
        "last_name",
        "email",
        "email_verified",
        "get_order_email",
        "password",
        "balance_cache",
        "phone",
        "room",
        "is_delivery_man",
        "has_drivers_licence",
        "verified_genuine_user",
        "is_staff",
        "is_superuser",
        "last_login",
        "calculated_last_order_date",
        "date_joined",
        "created_at",
        "is_active",
    ]
    readonly_fields = [
        "calculated_last_order_date"
    ]  # because it is a calculated field, or else we have an error
    additional_fields = ["groups", "user_permissions"]
    actions_list = ["verify_balance_action"]

    @action(description=_("Vérifier les soldes"))
    def verify_balance_action(self, request: HttpRequest):
        with transaction.atomic():
            n, users = User.sync_all_user_balances()
            if n:
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=users,
                    action_flag=CHANGE,
                    change_message="Synchronisation du solde en cache",
                )
        if n:
            if n == 1:
                error_msg = "1 solde a du être mis à jour."
            else:
                error_msg = f"{n} soldes ont du être mis à jour."
            messages.error(request, error_msg)
        else:
            messages.success(request, "Tous les soldes sont déjà à jour.")
        return redirect(reverse_lazy("admin:commande_user_changelist"))


@admin.register(Product)
class ProductAdmin(CustomModelAdmin):
    list_display = (
        "name",
        "category",
        "purchase_price",
        "resell_price",
        "_image_thumbnail",
        "is_active",
    )
    sorted_fields = [
        "name",
        "category",
        "image",
        "_image",
        "resell_price",
        "purchase_price",
        "updated_at",
        "created_at",
    ]
    readonly_fields = ["_image", "created_at", "updated_at"]
    STAFF_HIDDEN_FIELDS = ["sort"]
    STAFF_CREATION_HIDDEN_FIELDS = ["created_at", "updated_at", "is_active", "_image"]
    STAFF_CAN_CREATE = True
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "category__name",
    )
    _image_thumbnail = AdminThumbnail(image_field="image_thumbnail")
    _image = AdminThumbnail(image_field="image")


class ProductInline(TabularInline):
    model = Product
    max_num = 0
    can_delete = False
    show_change_link = True
    ordering_field = "sort"
    fields = [
        "sort",
        "_image_thumbnail",
        "purchase_price",
        "resell_price",
        "updated_at",
        "created_at",
        "is_active",
    ]
    readonly_fields = fields[1:]
    _image_thumbnail = AdminThumbnail(image_field="image_thumbnail")


@admin.register(ProductCategory)
class ProductCategoryAdmin(CustomModelAdmin):
    ordering_field = "sort"
    list_display = ["name"]
    inlines = [ProductInline]
    STAFF_HIDDEN_FIELDS = ["sort"]
    STAFF_CAN_CREATE = True


class OrderProductInline(TabularInline):
    model = OrderProduct
    extra = 0
    show_change_link = True
    fields = [
        "product_preview",
        "product",
        "quantity",
        "total_price_sold",
        "total_price_bought",
        "delivery_status",
    ]
    readonly_fields = ["product_preview"]
    _product_thumbnail = AdminThumbnail(image_field="image_thumbnail")

    def product_preview(self, obj):
        if obj.product:
            return self._product_thumbnail(obj.product)
        return ""

    # Optimization to avoid N+1 queries for the product images
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")


class TransactionInline(TabularInline):
    model = Transaction
    show_change_link = True
    extra = 0


@admin.register(Order)
class OrderAdmin(CustomModelAdmin):
    list_display = ("client", "delivery", "room", "is_cancelled", "created_at")
    list_filter = (
        ("is_cancelled", BooleanRadioFilter),
        ("delivery", AutocompleteSelectMultipleFilter),
    )
    inlines = [OrderProductInline, TransactionInline]
    actions_list = ["update_transactions_action"]
    readonly_fields = ["updated_at", "created_at"]
    list_filter = (
        ("delivery", AutocompleteSelectMultipleFilter),
        ("client", AutocompleteSelectMultipleFilter),
        "is_cancelled",
        "created_at",  # RangeDateTimeFilter does not work due to localisation : https://github.com/unfoldadmin/django-unfold/issues/1438
    )
    search_fields = ["delivery__date", "client__first_name", "client__last_name"]
    autocomplete_fields = ["delivery"]

    @action(description=_("Mettre à jour les transactions"))
    def update_transactions_action(self, request: HttpRequest):
        with transaction.atomic():
            n = 0
            orders = []
            for order in Order.objects.all():
                if order.update_transactions(
                    request,
                    reason="Mise à jour des transactions via le panel administrateur",
                ):
                    n += 1
                    orders.append(order)
            if n:
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=orders,
                    action_flag=CHANGE,
                    change_message="Mise à jour des transactions",
                )
        if n:
            if n == 1:
                error_msg = "1 transaction a du être créée."
            else:
                error_msg = f"{n} transactions ont du être créées."
            messages.error(request, error_msg)
        else:
            messages.success(request, "Toutes les transactions sont déjà à jour.")
        return redirect(reverse_lazy("admin:commande_order_changelist"))


class OrderProductResource(ModelResource):
    def __init__(self, **kwargs):
        super().__init__()
        self.start_date = kwargs.get("start_date")
        self.end_date = kwargs.get("end_date")

    def filter_export(self, queryset, **kwargs):
        return queryset.filter(
            order__delivery__date__range=(self.start_date, self.end_date),
            delivery_status__in=[
                OrderProduct.OrderProductStatusChoices.VALID,
                OrderProduct.OrderProductStatusChoices.NOT_DELIVERED,
            ],
        )

    class Meta:
        model = OrderProduct
        fields = [
            "order__delivery__date",
            "order__client__email",
            "product__name",
            "quantity",
            "total_price_bought",
            "total_price_sold",
            "delivery_status",
        ]


@admin.register(OrderProduct)
class OrderProductAdmin(ExportMixin, CustomModelAdmin):
    list_display = (
        "product",
        "product_preview",
        "quantity",
        "total_price_sold",
        "total_price_bought",
        "delivery_status",
        "order",
    )
    list_filter = (
        ("product", AutocompleteSelectMultipleFilter),
        ("delivery_status", ChoicesDropdownFilter),
        ("order__client", AutocompleteSelectMultipleFilter),
    )
    readonly_fields = ["updated_at"]
    autocomplete_fields = ["order"]

    _product_thumbnail = AdminThumbnail(image_field="image_thumbnail")

    def product_preview(self, obj):
        if obj.product:
            return self._product_thumbnail(obj.product)
        return ""

    # Optimization to avoid N+1 queries for the product images
    def get_queryset(self, request):
        return super().get_queryset(request).select_related("product")

    export_form_class = CustomOrderProductExportForm
    resource_classes = [OrderProductResource]

    def get_export_resource_kwargs(self, request, **kwargs):
        export_form = kwargs.get("export_form")
        if export_form:
            start_date, end_date = export_form.cleaned_data["date_range"]
            kwargs.update(start_date=start_date, end_date=end_date)
        return kwargs


class AmountSliderNumericFilter(SliderNumericFilter):
    MAX_DECIMALS = 2


@admin.register(Transaction)
class TransactionAdmin(CustomModelAdmin):
    list_display = (
        "amount_",
        "user",
        "type",
        "note",
        "initiator",
        "created_at",
    )
    list_filter = (
        ("type", ChoicesDropdownFilter),
        ("amount", AmountSliderNumericFilter),
        ("user", AutocompleteSelectMultipleFilter),
        ("initiator", AutocompleteSelectMultipleFilter),
        "created_at",  # RangeDateTimeFilter does not work due to localisation : https://github.com/unfoldadmin/django-unfold/issues/1438
    )
    STAFF_EDITABLE_FIELDS = ["user", "amount", "type", "note"]
    STAFF_CREATION_HIDDEN_FIELDS = ["initiator", "order", "created_at"]
    autocomplete_fields = ["user", "initiator", "order"]

    def amount_(self, obj):
        return mark_safe(
            f'<div style="text-align: right; color:{"red" if obj.amount < 0 else "green"}; font-weight: bold;">{obj.amount}€</div>'
        )

    amount_.admin_order_field = "amount"
    amount_.short_description = "Quantité"

    allowed_codes = [
        Transaction.TransactionTypeChoices.LYF_TOPUP,
        Transaction.TransactionTypeChoices.POS_TERMINAL_TOPUP,
        Transaction.TransactionTypeChoices.CASH_TOPUP,
        Transaction.TransactionTypeChoices.OTHER,
    ]

    # To limit the manual types allowed when creating a transaction (only UI enforcement)
    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "type":
            # Filter the choices
            kwargs["choices"] = [
                choice
                for choice in Transaction.TransactionTypeChoices.choices
                if choice[0] in self.allowed_codes
            ]

        return super().formfield_for_choice_field(db_field, request, **kwargs)

    # To inject the initiator in the creation form when adding (UI enforcement)
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if request.user.is_superuser:
            form.base_fields["initiator"].initial = request.user.id
        return form

    def save_model(self, request, obj, form, change):
        # To inject the initiator when creating a new transaction (Actual enforcement, even superusers)
        if not obj.pk:  # Only set on creation
            obj.initiator = request.user

        if obj.type not in self.allowed_codes:
            raise PermissionDenied(
                "You cannot manually create this type of transaction."
            )

        super().save_model(request, obj, form, change)


class OrderInline(TabularInline):
    model = Order
    extra = 0
    show_change_link = True
    fields = [
        "client",
        "room",
        "original_price",
        "is_cancelled",
        "created_at",
    ]


@admin.register(Delivery)
class DeliveryAdmin(CustomModelAdmin):
    search_fields = ("date",)
    list_display = (
        "date",
        "is_active",
    )
    list_filter = (
        "date",  # RangeDateFilter does not work due to localization issues
        ("is_active", BooleanRadioFilter),
    )
    STAFF_CAN_CREATE = True
    STAFF_CREATION_HIDDEN_FIELDS = ["is_active"]
    actions = [
        "cancel_deliveries_action",
        "uncancel_deliveries_action",
        "activate_deliveries_action",
    ]
    actions_list = ["bulk_edit_action"]
    actions_row = [
        "cancel_delivery_action_row",
        "uncancel_delivery_action_row",
        "activate_delivery_action_row",
    ]
    actions_detail = actions_row
    inlines = [OrderInline]

    @admin.action(description=_("Annuler les dates"))
    def cancel_deliveries_action(self, request: HttpRequest, queryset: QuerySet):
        n = 0
        for delivery in queryset:
            n += self.cancel_delivery_action_row(request, delivery.id, alone=False)
        tot = len(queryset)
        if n == tot:
            messages.success(request, f"{n} livraisons bien annulées.")
        elif n > 0:
            messages.warning(
                request,
                f"{n}/{tot} livraison(s) annulée(s). Les autres étaient déjà annulées.",
            )
        else:
            messages.error(
                request, f"Ce(s) {tot} livraison(s) est(sont) déjà désactivée(s) !"
            )

    @admin.action(description=_("Désannuler les dates"))
    def uncancel_deliveries_action(self, request: HttpRequest, queryset: QuerySet):
        return self.activate_deliveries_action(request, queryset, True)

    @admin.action(
        description=_(
            "Réactiver les dates (cette opération n'impacte pas les commandes déjà annulées)"
        )
    )
    def activate_deliveries_action(
        self, request: HttpRequest, queryset: QuerySet, uncancel=False
    ):
        n = 0
        uncanceled_n = 0
        for delivery in queryset:
            cn, cuncanceled = self.activate_delivery_action_row(
                request, delivery.id, uncancel, False
            )
            n += cn
            uncanceled_n += cuncanceled
        tot = len(queryset)
        if n == tot:
            messages.success(
                request,
                f"{n} livraison(s) bien réactivée(s)"
                + (
                    f" et {uncanceled_n} commande(s) désannulée(s)."
                    if uncancel
                    else " (cette opération n'impacte pas les commandes déjà annulées)."
                ),
            )
        elif n > 0:
            messages.warning(
                request,
                f"{n}/{tot} livraison(s) réactivée(s)"
                + (
                    f" et {uncanceled_n} commande(s) désannulée(s)."
                    if uncancel
                    else " (cette opération n'impacte pas les commandes déjà annulées)."
                ),
            )
        else:
            messages.error(
                request, f"Ce(s) {tot} livraison(s) est(sont) déjà activée(s) !"
            )

    @action(
        description=_("Annuler la date"),
        variant=ActionVariant.DANGER,
        permissions=["cancel_delivery_action_row"],
    )
    def cancel_delivery_action_row(
        self, request: HttpRequest, object_id: int, alone=True
    ):
        with transaction.atomic():
            deliv = Delivery.objects.get(id=object_id)
            if deliv.deactivate(request):
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=[deliv],
                    action_flag=CHANGE,
                    change_message="Annulation de la livraison",
                )
                if alone:
                    messages.success(request, "Livraison annulée avec succés.")
                else:
                    return 1
            elif alone:
                messages.error(request, "La livraison était déjà annulée !")
            else:
                return 0
        return redirect(
            request.headers.get("referer")
            or reverse_lazy("admin:commande_delivery_changelist")
        )

    def has_cancel_delivery_action_row_permission(
        self, request: HttpRequest, object_id=None
    ):
        return object_id is None or Delivery.objects.get(id=object_id).is_active

    @action(
        description=_("Désannuler la date"),
        variant=ActionVariant.SUCCESS,
        permissions=["activate_delivery_action_row"],
    )
    def uncancel_delivery_action_row(
        self, request: HttpRequest, object_id: int, alone=True
    ):
        return self.activate_delivery_action_row(request, object_id, True)

    @action(
        description=_(
            "Réactiver la date (cette opération n'impacte pas les commandes déjà annulées)"
        ),
        variant=ActionVariant.SUCCESS,
        permissions=["activate_delivery_action_row"],
    )
    def activate_delivery_action_row(
        self, request: HttpRequest, object_id: int, uncancel=False, alone=True
    ):
        deliv = Delivery.objects.get(id=object_id)
        if not deliv.is_active:
            with transaction.atomic():
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=[deliv],
                    action_flag=CHANGE,
                    change_message="Activation de la livraison",
                )
                deliv.is_active = True
                deliv.save()
                uncanceled = 0
                if uncancel:
                    for order in deliv.order_set.all():
                        if not order.is_cancelled:
                            for orderproduct in order.orderproduct_set.all():
                                orderproduct.delivery_status = (
                                    OrderProduct.OrderProductStatusChoices.VALID
                                )
                                orderproduct.save()
                                uncanceled += 1
                            order.update_transactions(
                                request, save=True, reason="Désannulation"
                            )
            if alone:
                messages.success(
                    request,
                    "Livraison réactivée"
                    + (
                        f" et {uncanceled} commande(s) désannulée(s)."
                        if uncancel
                        else " (cette opération n'impacte pas les commandes déjà annulées)."
                    ),
                )
            else:
                return 1, uncanceled
        elif alone:
            messages.error(request, "La livraison était déjà active !")
        else:
            return 0, 0
        return redirect(
            request.headers.get("referer")
            or reverse_lazy("admin:commande_delivery_changelist")
        )

    def has_activate_delivery_action_row_permission(
        self, request: HttpRequest, object_id=None
    ):
        return object_id is None or not Delivery.objects.get(id=object_id).is_active

    @action(
        description=_("Édition en masse"),
        variant=ActionVariant.PRIMARY,
        url_path="bulk-edit-action",
    )
    def bulk_edit_action(self, request: HttpRequest):
        form = bulkCreateDeliveriesForm(request.POST or None)

        if request.method == "POST" and form.is_valid():
            form_dates = form.cleaned_data["dates"]
            cancel_orders = form.cleaned_data["cancel_orders"]
            all_dates = append_unique_in_order(form_dates, form.old_dates)
            with transaction.atomic():
                failed = []
                succesful_creation = []
                succesful_activation = []
                succesful_deactivation = []
                succesful_deactivation_e = 0
                for date in all_dates:
                    if date in form_dates:
                        deliv, created = Delivery.objects.get_or_create(date=date)
                        if created:
                            deliv.save()
                            succesful_creation.append(deliv)
                        elif not deliv.is_active:
                            deliv.is_active = True
                            deliv.save()
                            succesful_activation.append(deliv)
                    else:
                        try:
                            deliv = Delivery.objects.get(date=date)
                            if (
                                deliv.deactivate(request, cancel_orders)
                                or cancel_orders
                            ):
                                succesful_deactivation.append(deliv)
                            elif cancel_orders:
                                succesful_deactivation_e += 1
                            else:
                                failed.append(deliv)
                        except ObjectDoesNotExist:
                            succesful_deactivation_e += 1
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=succesful_creation,
                    action_flag=CHANGE,
                    change_message="Création de la livraison",
                )
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=succesful_activation,
                    action_flag=CHANGE,
                    change_message="Activation de la livraison",
                )
                LogEntry.objects.log_actions(
                    user_id=request.user.id,
                    queryset=succesful_deactivation,
                    action_flag=CHANGE,
                    change_message="Désactivation de la livraison",
                )

            messages.success(
                request,
                f"{len(succesful_creation) + len(succesful_activation)} dates ont bien été créées/activées (cette opération n'impacte pas les commandes déjà annulées), et {len(succesful_deactivation) + succesful_deactivation_e} dates ont bien été désactivées.",
            )
            if len(failed) > 0:
                messages.error(
                    request,
                    f"{len(failed)} dates n'ont pas été désactivés, car auraient nécessité d'annuler des commandes clients {(*[deliv.date.strftime('%d/%m/%y') for deliv in failed],)}.",
                )
            else:
                return redirect(reverse_lazy("admin:commande_delivery_changelist"))

        return render(
            request,
            "admin/bulk_create_deliveries.html",
            {
                "form": form,
                "title": _("Création en masse de dates de livraisons"),
                **self.admin_site.each_context(request),
            },
        )


@admin.register(HelloAssoCheckout)
class HelloAssoCheckoutAdmin(CustomModelAdmin):
    list_display = (
        "amount",
        "user",
        "status",
        "created_at",
    )
    list_filter = (
        ("status", ChoicesDropdownFilter),
        ("amount", AmountSliderNumericFilter),
        ("user", AutocompleteSelectMultipleFilter),
        "created_at",  # RangeDateTimeFilter does not work due to localisation : https://github.com/unfoldadmin/django-unfold/issues/1438
    )
    inlines = [TransactionInline]
    readonly_fields = ["updated_at"]
    autocomplete_fields = ["user"]
    STAFF_CAN_CREATE = False

    actions = ["refresh_data_action"]
    actions_row = ["refresh_data_action_row"]
    actions_detail = actions_row

    @action(
        description=_("Rafraichir les données"),
        variant=ActionVariant.PRIMARY,
    )
    def refresh_data_action_row(self, request: HttpRequest, object_id: int, alone=True):
        with transaction.atomic():
            checkout = HelloAssoCheckout.objects.get(id=object_id)
            checkout.refresh_from_api()
            if alone:
                messages.success(request, "Checkout bien rafraichit.")
            else:
                return 1
        return redirect(
            request.headers.get("referer")
            or reverse_lazy("admin:commande_helloassocheckout_changelist")
        )

    @admin.action(
        description=_("Rafraichir les données (attention au rate limit de l'API !)")
    )
    def refresh_data_action(self, request: HttpRequest, queryset: QuerySet):
        for checkout in queryset:
            checkout.refresh_from_api()
        tot = len(queryset)
        messages.success(request, f"{tot} checkout(s) bien rafraichit(s).")


@admin.register(LogEntry)
class LogEntryAdmin(CustomModelAdmin):
    # Display the most important information
    list_display = [
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "action_flag_",
        "change_message",
    ]
    list_filter = [
        "action_time",
        ("user", AutocompleteSelectMultipleFilter),
        ("content_type", MultipleRelatedDropdownFilter),
        ("action_flag", ChoicesRadioFilter),
    ]
    search_fields = ["object_repr", "change_message", "user"]

    # Prevent anyone from editing or deleting logs
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    # Make the action flag (Add/Change/Delete) readable with colors
    def action_flag_(self, obj):
        flags = {1: "Green", 2: "Blue", 3: "Red"}  # Add, Change, Deletion
        colors = {1: "green", 2: "#2471a3", 3: "red"}
        return mark_safe(
            f'<b style="color:{colors[obj.action_flag]}">{obj.get_action_flag_display()}</b>'
        )


class PrecreateUserView(UnfoldModelAdminViewMixin, FormView):
    title = "Précréation de compte utilisateur"
    form_class = PrecreateUserForm
    permission_required = ("commande.view_user",)
    template_name = "admin/precreate_user.html"
    success_url = reverse_lazy("admin:precreation_utilisateur")

    def form_valid(self, form):

        # Create user in DB
        user = form.save(commit=False)
        PrecreateUserFunction(user, self.request)

        messages.success(self.request, "Utilisateur bien pré-créé")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Erreur, utilisateur non créé.")
        return super().form_invalid(form)


class PrecreateUsersView(UnfoldModelAdminViewMixin, FormView):
    title = "Précréation de compte utilisateur"
    permission_required = ("commande.view_user",)
    template_name = "admin/precreate_users.html"
    success_url = reverse_lazy("admin:precreation_utilisateurs")

    def get_form_class(self, extra=3):
        return modelformset_factory(
            User,
            form=PrecreateUserForm,
            extra=extra,  # number of empty forms to display
            can_delete=False,
        )

    def get_form(self, form_class=None):
        form_class = self.get_form_class()
        return form_class(queryset=User.objects.none(), **self.get_form_kwargs())

    def form_valid(self, formset):

        valid_users = []
        invalid_forms_indices = []

        for i, form in enumerate(formset):
            if form.is_valid() and form.has_changed():
                valid_users.append(form.save(commit=False))
            elif form.has_changed():
                # keep invalid or empty forms for re-rendering
                invalid_forms_indices.append(i)

        PrecreateUsersFunction(valid_users, self.request)

        if valid_users:
            messages.success(
                self.request, f"{len(valid_users)} utilisateur(s) bien pré-créé(s)"
            )

        if invalid_forms_indices:
            messages.error(
                self.request,
                f"{len(invalid_forms_indices)} formulaire(s) contiennent des erreurs et doivent être corrigés.",
            )

            # Rebuild formset with only invalid forms
            Formset = self.get_form_class(extra=len(invalid_forms_indices))
            # Pass in data from the original request to preserve errors
            new_formset = Formset(
                data=self.request.POST,
                queryset=User.objects.none(),
            )
            # Delete all non invalid forms
            for i, form in reversed(list(enumerate(new_formset.forms))):
                if i not in invalid_forms_indices:
                    del new_formset.forms[i]

            return self.render_to_response(self.get_context_data(form=new_formset))

        return super().form_valid(formset)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context.update(
            {
                "precreateuser_formset_helper": PrecreateUsersFormHelper(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a form instance with the passed
        POST variables.
        """
        # I need the form to be passed even if not valid
        form = self.get_form()
        return self.form_valid(form)


class CustomAdmin(BaseGroupAdmin, ModelAdmin):
    actions = None

    def get_urls(self):
        custom_urls = [
            path(
                "precreation_utilisateur/",
                PrecreateUserView.as_view(model_admin=self),
                name="precreation_utilisateur",
            ),
            path(
                "precreation_utilisateurs/",
                PrecreateUsersView.as_view(model_admin=self),
                name="precreation_utilisateurs",
            ),
        ]
        return custom_urls + super().get_urls()


admin.site.unregister(Group)
admin.site.register(Group, CustomAdmin)
