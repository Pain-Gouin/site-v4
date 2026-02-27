from decimal import Decimal

import helloasso_python
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    Group,
    PermissionsMixin,
    UserManager,
)
from django.core.exceptions import PermissionDenied
from django.db import models, transaction
from django.db.models import F
from django.db.models.functions import Coalesce
from django.utils import formats, timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit

from .utils.helloasso import get_api_client, log_api_exception
from .utils.utils import first_editable_day

# Create your models here.


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True, null=False, blank=False)

    # Taken from AbstractBaseUser
    last_login = models.DateTimeField(
        _("last login"),
        blank=True,
        null=True,
        help_text=_(
            "Date de la dernière connexion de l'utilisateur. Si vide, alors le compte n'a pas encore été activé."
        ),
    )
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
            "Designates whether this user should be treated as active. Unselect this instead of deleting accounts."
        ),
    )
    email_verified = models.BooleanField(
        "E-mail vérifié",
        default=False,
        help_text="Désigne si l'utilisateur a bien vérifié son e-mail",
    )
    verified_genuine_user = models.BooleanField(
        "Centralien vérifié",
        default=False,
        help_text="Désigne si l'utilisateur a été vérifié comme étant un Centralien, autorisé à utiliser le site",
    )
    date_joined = models.DateTimeField(
        _("date joined"), default=timezone.now, null=True
    )
    # End of taken from AbstractUser

    is_delivery_man = models.BooleanField(
        "Livreur",
        default=False,
        help_text="Désigne si l'utilisateur a accepté de faire des livraisons",
    )
    has_drivers_licence = models.BooleanField(
        "Permis",
        default=False,
        help_text="Désigne si l'utilisateur a le permis de conduire",
    )
    get_order_email = models.BooleanField(
        "Confirmation de commande",
        default=True,
        help_text="Désigne si l'utilisateur souhaite recevoir des mails de confirmation de commande",
    )
    room = models.CharField(
        "Chambre",
        max_length=10,
        blank=False,
        default="",
        help_text="Désigne la chambre de l'utilisateur. "
        "Permet de préremplir la chambre de livraison lors d'une commande",
    )
    phone = models.CharField(
        "Numéro de téléphone", max_length=20, blank=False, default=""
    )
    created_at = models.DateTimeField(default=timezone.now, verbose_name=_("Créé le"))
    balance_cache = models.DecimalField(
        "Dernier solde calculé",
        max_digits=8,
        decimal_places=2,
        default=0,
        help_text="Cache pour stocker le potentiel solde actuel de l'utilisateur. "
        "La table des transactions fait foix !",
    )

    @cached_property
    def calculated_last_order_date(self):
        """
        Returns the created_at date of the most recent order made by this user.
        """
        return self.order_set.aggregate(max_date=models.Max("created_at"))["max_date"]

    def sync_balance_cache(self):
        with transaction.atomic():
            old_balance_cache = self.balance_cache
            self.balance_cache = self.transaction_set.aggregate(
                total_sum=models.Sum("amount")
            )["total_sum"]
            if old_balance_cache != self.balance_cache:
                self.save(update_fields=["balance_cache"])
                return True
            return False

    def can_be_verified_genuine_user(self):
        if self.verified_genuine_user:  # Why have you called this function ?
            return True
        if self.transaction_set.exists() or (
            self.email_verified
            and self.email.split("@")[-1] in settings.VERIFIED_USER_EMAIL_DOMAINS
        ):
            self.verified_genuine_user = True
            self.save(update_fields=["verified_genuine_user"])
            return True
        return False

    @staticmethod
    def sync_all_user_balances():
        """
        Recalculates balance_cache for all users in one database query.
        """
        # 1. Create a subquery that sums transactions for a specific user
        # We use Round to ensure the sum matches the 2-decimal precision of the cache
        transactions_sum = (
            Transaction.objects.filter(user=models.OuterRef("pk"))
            .values("user")
            .annotate(total=models.Sum("amount"))
            .values("total")
        )

        # 2. Wrap it in Coalesce to handle users with zero transactions
        new_balance_expr = Coalesce(models.Subquery(transactions_sum), Decimal("0.00"))

        # 3. Update only the users whose current cache doesn't match the sum
        # This generates a single 'UPDATE ... WHERE NOT (balance_cache = ...)' query
        q = User.objects.annotate(calc=new_balance_expr).exclude(
            balance_cache=models.F("calc")
        )
        with transaction.atomic():
            users = list(q)
            updated_count = q.update(balance_cache=new_balance_expr)

        return updated_count, users

    calculated_last_order_date.short_description = "Dernière Commande"

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def save(self, *args, **kwargs):
        add_default_group = self._state.adding

        super().save(*args, **kwargs)

        if add_default_group:
            group, _ = Group.objects.get_or_create(name="default")
            self.groups.add(group)

    def __str__(self):
        return f"{self.first_name} {self.last_name.upper()}"

    class Meta:
        verbose_name = _("Utilisateur")


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    sort = models.PositiveIntegerField(
        _("Ordre d'apparition"),
        default=0,
        db_index=True,
        help_text="Numéro indiquant l'ordre d'apparition de la catégorie.",
    )

    class Meta:
        verbose_name = _("Catégorie produit")
        verbose_name_plural = _("Catégories produit")
        ordering = ["sort"]

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom du produit")
    image = models.ImageField(upload_to="images")
    image_resized = ImageSpecField(
        source="image",
        processors=[ResizeToFit(500, 500)],
        format="WEBP",
        options={"quality": 85},
    )
    image_thumbnail = ImageSpecField(
        source="image",
        processors=[ResizeToFit(50, 50)],
        format="WEBP",
        options={"quality": 85},
    )
    resell_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Prix de revente",
        help_text="Prix de revente aux centraliens sur le site.",
    )
    purchase_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        verbose_name="Prix d'achat",
        help_text="Prix d'achat à la boulangerie.",
    )
    category = models.ForeignKey(
        ProductCategory, on_delete=models.CASCADE, verbose_name="Catégorie"
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Ajouté le"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Mise à jour le"))

    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this product is still available to order. "
            "Unselect this instead of deleting the product."
        ),
    )

    sort = models.PositiveIntegerField(
        _("Ordre d'apparition"),
        default=0,
        db_index=True,
        help_text="Numéro indiquant l'ordre d'apparition du produit.",
    )

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Produit")

    def __str__(self) -> str:
        return self.name


class DeliveryQuerySet(models.QuerySet):
    def editable(self):
        qs = self.filter(date__gte=first_editable_day())

        return qs.filter(is_active=True)


class Delivery(models.Model):
    date = models.DateField(_("Jour"), default=timezone.now, unique=True)
    is_active = models.BooleanField(
        _("Actif"),
        default=True,
        help_text=_(
            "Permet de désactiver une livraison sans casser les liens d'éventuelles commandes faites pour ce jour"
        ),
    )
    objects = DeliveryQuerySet.as_manager()

    class Meta:
        ordering = ["-date"]
        verbose_name = _("Livraison")

    def __str__(self) -> str:
        return str(self.date)

    @property
    def is_editable(self):
        return self.is_active and self.date >= first_editable_day()

    def deactivate(self, request, *, cancel_orders=True):
        if not self.is_active:
            return False  # delivery already deactivated
        with transaction.atomic():
            for order in self.order_set.all():
                if cancel_orders:
                    order.cancel(request, from_user=False)
                elif not order.is_cancelled:
                    return False

            self.is_active = False
            self.save()
        return True


class Order(models.Model):
    original_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Prix originel de la commande",
        help_text="Prix originel de la commande, sans prendre en compte d'éventuels remboursements",
    )
    client = models.ForeignKey(User, on_delete=models.PROTECT)
    delivery = models.ForeignKey(
        Delivery, on_delete=models.PROTECT, verbose_name="Livraison associée"
    )
    room = models.CharField("Chambre à livrer", max_length=10)
    is_cancelled = models.BooleanField(
        default=False,
        verbose_name="Annulée",
        help_text="Désigne si la transaction a été annulé par l'utilisateur",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Commande")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"Commande de {self.client} pour le {formats.date_format(self.delivery.date, 'D j M Y')} "
            f"({formats.date_format(self.created_at, 'd/m/Y H:i:s')})"
        )

    @property
    def is_editable(self):
        return self.delivery.is_editable

    def update_transactions(self, request, *, save=True, reason="Annulation"):
        with transaction.atomic():
            current_price_paid = -self.transactions.aggregate(
                models.Sum("amount", default=0)
            )["amount__sum"]
            price_to_pay = self.orderproduct_set.filter(
                delivery_status=OrderProduct.OrderProductStatusChoices.VALID
            ).aggregate(models.Sum("total_price_sold", default=0))[
                "total_price_sold__sum"
            ]
            diff = current_price_paid - price_to_pay
            if diff:
                refund_transaction = Transaction.objects.create(
                    user=self.client,
                    amount=diff,
                    type=Transaction.TransactionTypeChoices.REFUND,
                    note=f"{reason} par {request.user} de la commande #{self.pk} passée le {self.created_at}",
                    initiator=request.user,
                )
                self.transactions.add(refund_transaction)
                if save:
                    self.save()
                return True
            return False

    def cancel(self, request, *, from_user=True):
        if self.is_cancelled:
            return  # already cancelled
        with transaction.atomic():
            self.orderproduct_set.update(
                delivery_status=OrderProduct.OrderProductStatusChoices.CANCELLED,
                updated_at=timezone.now(),  # Manually update timestamp, as auto_now=True is bypassed by update()
            )
            self.is_cancelled = from_user  # If not from the user, than should not be marked cancelled by the user.
            self.update_transactions(request, save=False)
            self.save()


class OrderProduct(models.Model):
    class OrderProductStatusChoices(models.TextChoices):
        VALID = "NA", "Rien à signaler"
        NOT_DELIVERED = "NDELIV", "Échec de livraison, mais récupéré à la boulangerie"
        NOT_BOUGHT = "NBOUGHT", "Échec de récupération à la boulangerie"
        CANCELLED = "CANCEL", "Produit annulé"

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, verbose_name="Commande associée"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, verbose_name="Produit"
    )
    quantity = models.PositiveIntegerField(verbose_name="Quantité commandée")
    total_price_sold = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Coût payé par le client pour l'article",
        help_text="Au moment de l'achat. Prend en compte la quantité",
    )
    total_price_bought = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="Coût payé à la boulangerie pour l'article",
        help_text="Au moment de l'achat. Prend en compte la quantité",
    )
    delivery_status = models.CharField(
        choices=OrderProductStatusChoices,
        max_length=7,
        verbose_name="État de livraison du produit",
        help_text="Permet d'identifier si le produit n'a pas été récupéré à la boulangerie, "
        "ou a été récupéré mais pas livré à l'utilisateur",
        default=OrderProductStatusChoices.VALID,
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Produit commandé")
        verbose_name_plural = _("Produits commandés")

    def __str__(self) -> str:
        return f"{self.product.name} x{self.quantity}"

    def save(self, *args, **kwargs):
        # automatically calculate the price at time of saving
        if self.total_price_sold is None:
            self.total_price_sold = self.product.resell_price * self.quantity
        if self.total_price_bought is None:
            self.total_price_bought = self.product.purchase_price * self.quantity
        super().save(*args, **kwargs)


class HelloAssoCheckout(models.Model):
    class HelloAssoCheckoutStatusChoices(models.TextChoices):
        INITIATED = "INIT", "Checkout initié"
        PENDING = "PEND", "Checkout effectué, en attente de validation du paiement"
        AUTHORIZED = "DONE", "Paiement valide, autorisé, et effectué"
        CONTESTED = "CONT", "Paiement contesté par la banque"
        REFUNDED = "REIM", "Paiement remboursé"
        REFUSED = "REFU", "Paiement refusé par la banque"
        OTHER = "OTHE", "Paiement dans un état incertain"

    checkout_intent_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    order_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    payement_id = models.PositiveIntegerField(unique=True, null=True, blank=True)
    amount = models.DecimalField(
        _("Somme"), max_digits=5, decimal_places=2, help_text="en euros"
    )
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    status = models.CharField(
        choices=HelloAssoCheckoutStatusChoices,
        max_length=4,
        verbose_name="État du paiement",
        default=HelloAssoCheckoutStatusChoices.INITIATED,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "HelloAsso Checkout"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"#{self.checkout_intent_id} pour {self.amount}€"

    def refresh_from_api(self):
        from .tasks import (  # noqa: PLC0415 (To prevent circular import)
            check_checkout_status,
        )

        with transaction.atomic(), get_api_client() as api_client:
            api_instance = helloasso_python.CheckoutApi(api_client)
            organization_slug = settings.HELLOASSO_ORG_SLUG
            checkout_intent_id = self.checkout_intent_id
            try:
                api_response = api_instance.organizations_organization_slug_checkout_intents_checkout_intent_id_get(
                    organization_slug, checkout_intent_id
                )
                if not api_response.order:
                    if timezone.now() - self.created_at > timezone.timedelta(
                        minutes=45
                    ):  # checkout intent can be considered cancelled
                        self.delete()
                        # Maybe we should verify that no transactions are attached,
                        # but it is not supposed to be possible, and this would prevent deletion anyway
                    else:
                        self.status = (
                            HelloAssoCheckout.HelloAssoCheckoutStatusChoices.INITIATED
                        )
                        self.save()
                        check_checkout_status.apply_async_on_commit(
                            (self.checkout_intent_id,), countdown=60 * 60
                        )
                else:
                    self.parse_order(api_response.order, save=False)
                    self.parse_payment(api_response.order.payments[0], save=False)
                    self.update_transactions(save=False)
                    self.save()
            except helloasso_python.ApiException as e:
                log_api_exception(
                    e,
                    api_instance.organizations_organization_slug_checkout_intents_checkout_intent_id_get,
                )
                return False
            else:
                return True

    def update_transactions(self, *, save=True):
        with transaction.atomic():
            current_transaction_amount = self.transactions.aggregate(
                models.Sum("amount", default=0)
            )["amount__sum"]
            current_amount = (
                self.amount
                if self.status
                == HelloAssoCheckout.HelloAssoCheckoutStatusChoices.AUTHORIZED
                else 0
            )
            diff = current_amount - current_transaction_amount

            if diff:
                new_transaction = Transaction.objects.create(
                    user=self.user,
                    amount=diff,
                    type=Transaction.TransactionTypeChoices.HELLOASSO_CHECKOUT,
                    note=self.status.label
                    if self.status
                    in (
                        HelloAssoCheckout.HelloAssoCheckoutStatusChoices.AUTHORIZED,
                        HelloAssoCheckout.HelloAssoCheckoutStatusChoices.REFUNDED,
                        HelloAssoCheckout.HelloAssoCheckoutStatusChoices.CONTESTED,
                    )
                    else "Régularisation d'une anomalie",
                    initiator=self.user,
                )
                self.transactions.add(new_transaction)
                if save:
                    self.save()
                return True
            return False

    def parse_order(
        self,
        order: helloasso_python.HelloAssoApiV5ModelsStatisticsOrderDetail,
        *,
        save=True,
    ):
        if (
            order.checkout_intent_id
            and order.checkout_intent_id != self.checkout_intent_id
        ):
            error_msg = (
                f"CRITICAL: Checkout Intent ID mismatch! "
                f"Expected {self.checkout_intent_id}, but received {order.checkout_intent_id}. "
                f"This could indicate a logic error or a spoofing attempt."
            )
            raise ValueError(error_msg)

        if not self.order_id:
            self.order_id = order.id
        elif self.order_id != order.id:
            error_msg = (
                f"CRITICAL: Order ID mismatch! "
                f"Expected {self.order_id}, but received {order.id}. "
                f"This could indicate a logic error or a spoofing attempt."
            )
            raise ValueError(error_msg)

        if save:
            self.save()

    def parse_payment(
        self,
        payment: helloasso_python.HelloAssoApiV5ModelsStatisticsOrderPayment,
        *,
        save=True,
    ):
        if not self.payement_id:
            self.payement_id = payment.id
        elif self.payement_id != payment.id:
            error_msg = (
                f"CRITICAL: Payment ID mismatch! "
                f"Expected {self.payement_id}, but received {payment.id}. "
                f"This could indicate a logic error or a spoofing attempt."
            )
            raise ValueError(error_msg)

        match payment.state:
            case helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.PENDING:
                self.status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.PENDING
            case (
                helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.AUTHORIZED
                | helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.REFUNDING
            ):
                self.status = (
                    HelloAssoCheckout.HelloAssoCheckoutStatusChoices.AUTHORIZED
                )
            case helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.REFUSED:
                self.status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.REFUSED
            case helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.REFUNDED:
                self.status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.REFUNDED
            case helloasso_python.HelloAssoApiV5ModelsEnumsPaymentState.CONTESTED:
                self.status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.CONTESTED
            case _:
                self.status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.OTHER

        if save:
            self.save()


class ImmutableQuerySet(models.QuerySet):
    def delete(self):
        msg = "Bulk deletion of transactions is protected."
        raise PermissionDenied(msg)

    def update(self, **kwargs):
        msg = "Bulk updating of transactions is protected."
        raise PermissionDenied(msg)


class Transaction(models.Model):
    class TransactionTypeChoices(models.TextChoices):
        ORDER_CHARGE = "ORDER", "Paiement d'une commande"
        REFUND = "REFUND", "Remboursement d'une commande"
        LYF_TOPUP = "LYF", "Rechargement via LYF"
        POS_TERMINAL_TOPUP = "POS", "Rechargement via TPE"
        CASH_TOPUP = "CASH", "Rechargement via Cash"
        HELLOASSO_CHECKOUT = "HAC", "Rechargement via HelloAsso Checkout"
        OTHER = "OTHER", "Autre (à préciser !)"

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Utilisateur")
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Commande associée",
    )
    helloasso_checkout = models.ForeignKey(
        HelloAssoCheckout,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name="Rechargement associé",
    )
    amount = models.DecimalField(
        max_digits=8, decimal_places=2, verbose_name="Quantité"
    )
    type = models.CharField(max_length=6, choices=TransactionTypeChoices)
    note = models.TextField(blank=True)
    initiator = models.ForeignKey(
        User,
        verbose_name="Initiateur de la transaction",
        related_name="initiated_transactions",
        on_delete=models.PROTECT,
        help_text="Désigne la personne à l'origine de la transaction. Peut être l'utilisateur "
        "lui-même, par exemple lors d'une commande, ou bien un administrateur.",
    )
    created_at = models.DateTimeField(
        default=timezone.now, verbose_name=_("Effectuée le")
    )

    objects = ImmutableQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.amount}€ pour {self.initiator}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            msg = "Transactions cannot be modified once created."
            raise PermissionDenied(msg)

        # To keep user's balance cache in sync
        with transaction.atomic():
            super().save(*args, **kwargs)
            User.objects.filter(id=self.user.id).update(
                balance_cache=F("balance_cache") + self.amount
            )

    def delete(self, *args, **kwargs):
        msg = "Transactions cannot be deleted."
        raise PermissionDenied(msg)
