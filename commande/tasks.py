from celery import shared_task
from .models import HelloAssoCheckout
from django.db import transaction


@shared_task
def check_checkout_status(checkout_intent_id):
    checkout = HelloAssoCheckout.objects.filter(
        checkout_intent_id=checkout_intent_id
    ).first()
    if checkout is None:
        return

    if checkout.status in (
        HelloAssoCheckout.HelloAssoCheckoutStatusChoices.INITIATED,
        HelloAssoCheckout.HelloAssoCheckoutStatusChoices.PENDING,
    ):
        checkout.refresh_status()


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
        elif metadata and metadata.get("website_tracked"):
            checkout = HelloAssoCheckout.objects.get(id=metadata["HelloAssoCheckoutPK"])
        else:
            return False
        checkout.refresh_from_api()
        return True
