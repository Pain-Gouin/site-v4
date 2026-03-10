from celery import shared_task
from django.db import transaction

from .models import HelloAssoCheckout


@shared_task
def refresh_transactions():
    checkouts = HelloAssoCheckout.objects.filter(
        status__in=[
            HelloAssoCheckout.HelloAssoCheckoutStatusChoices.INITIATED,
            HelloAssoCheckout.HelloAssoCheckoutStatusChoices.PENDING,
        ]
    )
    for checkout in checkouts:
        checkout.refresh_from_api()


@shared_task
def helloasso_payment_notification(payement, metadata=None):
    with transaction.atomic():
        if HelloAssoCheckout.objects.filter(payement_id=payement["id"]).exists():
            checkout = HelloAssoCheckout.objects.get(payement_id=payement["id"])
            if (
                checkout.status
                == HelloAssoCheckout.HelloAssoCheckoutStatusChoices.AUTHORIZED
                and payement["state"] == "authorized"
            ):
                return False  # No new data, prevent useless api call
        elif metadata and metadata.get("website_tracked"):
            checkout = HelloAssoCheckout.objects.get(id=metadata["HelloAssoCheckoutPK"])
        else:
            return False
        checkout.refresh_from_api()
        return True


@shared_task
def helloasso_order_notification(order, metadata=None):
    with transaction.atomic():
        if HelloAssoCheckout.objects.filter(order_id=order["id"]).exists():
            return False  # Data from order is already present, prevent useless api call
        if metadata and metadata.get("website_tracked"):
            checkout = HelloAssoCheckout.objects.get(id=metadata["HelloAssoCheckoutPK"])
        else:
            return False
        checkout.refresh_from_api()
        return True
