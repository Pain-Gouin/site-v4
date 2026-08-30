from decimal import Decimal

import factory
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from factory.django import DjangoModelFactory, ImageField

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

articles_boulangerie = [
    # Pains et baguettes
    "Baguette tradition",
    "Baguette moulée",
    "Baguette aux graines",
    "Pain de campagne",
    "Pain complet",
    "Pain au levain",
    "Pain de seigle",
    "Pain de mie",
    "Pain aux noix",
    "Pain aux figues",
    "Pain ciabatta",
    "Focaccia au romarin",
    "Pain marguerite",
    "Pain paillasse",
    "Bâtard",
    # Viennoiseries
    "Croissant au beurre",
    "Pain au chocolat",
    "Pain aux raisins",
    "Brioche tressée",
    "Brioche vendéenne",
    "Chausson aux pommes",
    "Chouquette",
    "Oranaise aux abricots",
    "Suisse au chocolat",
    "Kouign-amann",
    "Cramique",
    "Pétri de chocolat",
    "Pain au lait",
    "Kanelbulle",
    "Croissant aux amandes",
    # Pâtisseries individuelles
    "Éclair au chocolat",
    "Éclair au café",
    "Tartelette aux fraises",
    "Tartelette aux framboises",
    "Tartelette au citron meringuée",
    "Mille-feuille",
    "Paris-Brest",
    "Religieuse au chocolat",
    "Flan pâtissier",
    "Opéra",
    "Grand-mère aux pommes",
    "Baba au rhum",
    "Canelé de Bordeaux",
    "Macaron à la vanille",
    "Tartelette chocolat-caramel",
    # Tartes et grands gâteaux
    "Tarte aux pommes rustique",
    "Tarte aux poires et amandes",
    "Tarte aux myrtilles",
    "Saint-Honoré",
    "Tropezienne",
    # Traiteur et salé
    "Quiche lorraine",
    "Quiche au saumon et épinards",
    "Croque-monsieur",
    "Feuilleté au jambon",
    "Friand à la viande",
    "Fougasse aux olives et lardons",
    "Sandwich jambon-beurre",
    "Sandwich poulet crudités",
    "Sandwich thon mayonnaise",
    "Wrap au saumon fumé",
]


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.LazyAttribute(
        lambda o: (
            f"{o.first_name.lower()}.{o.last_name.lower()}@"
            f"{'centralelille.fr' if o.verified_genuine_user else 'example.com'}"
        )
    )
    password = factory.LazyFunction(lambda: make_password("testpass123"))
    first_name = factory.Faker("first_name", locale="fr_FR")
    last_name = factory.Faker("last_name", locale="fr_FR")
    room = factory.Sequence(lambda n: f"R{n:03d}")
    phone = factory.Faker("numerify", text="06########")
    email_verified = True
    is_staff = factory.Faker("boolean", chance_of_getting_true=10)
    verified_genuine_user = factory.LazyAttribute(
        lambda o: (
            o.is_staff or factory.Faker._get_faker().boolean(chance_of_getting_true=70)  # noqa: SLF001
        )
    )
    has_drivers_licence = factory.Faker("boolean", chance_of_getting_true=50)
    is_delivery_man = factory.Faker("boolean", chance_of_getting_true=33)

    class Params:
        # mirrors real signup(): get_or_create(email=...) with no password set yet
        unactivated = factory.Trait(
            password=factory.LazyFunction(
                lambda: make_password(None)
            ),  # unusable password
            email_verified=False,
            verified_genuine_user=False,
        )


class ProductCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ProductCategory
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Catégorie {n}")
    sort = factory.Sequence(lambda n: n)


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Iterator(articles_boulangerie, cycle=True)
    image = ImageField(color=factory.Faker("color"))
    resell_price = factory.Faker(
        "pydecimal", left_digits=1, right_digits=2, positive=True
    )
    purchase_price = factory.LazyAttribute(lambda o: o.resell_price * Decimal("0.6"))
    category = factory.SubFactory(ProductCategoryFactory)
    sort = factory.Sequence(lambda n: n)


class DeliveryFactory(DjangoModelFactory):
    class Meta:
        model = Delivery
        django_get_or_create = ("date",)

    # unique date per instance; offset by sequence so create_batch doesn't collide
    date = factory.Sequence(
        lambda n: timezone.now().date() + timezone.timedelta(days=n)
    )
    is_active = True


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order
        skip_postgeneration_save = (
            True  # avoid a redundant save before we set original_price
        )

    client = factory.SubFactory(UserFactory)
    delivery = factory.SubFactory(DeliveryFactory)
    room = factory.SelfAttribute("client.room")
    original_price = 0  # placeholder — overwritten by the `products` hook below

    @factory.post_generation
    def products(self, create, extracted, **kwargs):
        if not create:
            return

        # extracted lets callers pass explicit products:
        #   OrderFactory(products=[product_a, product_b]) # noqa: ERA001
        # default: one random product at a random quantity
        products = extracted or [ProductFactory()]

        total = Decimal("0")
        for product in products:
            order_product = OrderProductFactory(order=self, product=product)
            total += (
                order_product.total_price_sold
            )  # price at time of order, per your model's save()

        self.original_price = total
        self.save(update_fields=["original_price"])


class OrderProductFactory(DjangoModelFactory):
    class Meta:
        model = OrderProduct

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = factory.Faker("pyint", min_value=1, max_value=5)
    # leave total_price_sold / total_price_bought as None —
    # OrderProduct.save() auto-calculates them from product price * quantity
    total_price_sold = None
    total_price_bought = None


class HelloAssoCheckoutFactory(DjangoModelFactory):
    class Meta:
        model = HelloAssoCheckout

    checkout_intent_id = factory.Sequence(lambda n: n + 1000)
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    user = factory.SubFactory(UserFactory)
    status = HelloAssoCheckout.HelloAssoCheckoutStatusChoices.AUTHORIZED


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    user = factory.SubFactory(UserFactory)
    initiator = factory.SelfAttribute("user")
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2, positive=True)
    type = Transaction.TransactionTypeChoices.CASH_TOPUP
    note = factory.Faker("sentence")
