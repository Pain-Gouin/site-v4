import random

from django.core.management.base import BaseCommand

from commande.factories import (
    DeliveryFactory,
    OrderFactory,
    ProductCategoryFactory,
    ProductFactory,
    TransactionFactory,
    UserFactory,
)


class Command(BaseCommand):
    help = "Seed local DB with fake data"

    def handle(self, *args, **options):
        users = UserFactory.create_batch(50)
        categories = ProductCategoryFactory.create_batch(4)
        products = [ProductFactory(category=c) for c in categories for _ in range(3)]
        deliveries = DeliveryFactory.create_batch(10)

        for user in users:
            TransactionFactory(user=user, initiator=user, amount=25)

        for delivery in deliveries:
            for _ in range(5):
                client = random.choice(users)  # noqa: S311
                order_products = random.sample(products, k=random.randint(1, 5))  # noqa: S311
                OrderFactory(
                    delivery=delivery,
                    client=client,
                    room=client.room,
                    products=order_products,
                )

        self.stdout.write(self.style.SUCCESS("Seeded paingouin dev DB"))
