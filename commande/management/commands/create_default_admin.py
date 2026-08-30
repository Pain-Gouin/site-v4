from decimal import Decimal

from django.core.management.base import BaseCommand

from commande.models import Transaction, User


class Command(BaseCommand):
    help = "Create (or reset) a default admin/superuser for local dev — NEVER run in production"

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@admin.com")
        parser.add_argument("--password", default="admin")

    def handle(self, *args, **options):
        email = options["email"]
        password = options["password"]

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "first_name": "Admin",
                "last_name": "Local",
                "is_staff": True,
                "is_superuser": True,
                "email_verified": True,
                "verified_genuine_user": True,
                "is_delivery_man": True,
                "room": "000",
                "phone": "0123456789",
            },
        )

        # idempotent: if the user already existed (e.g. re-running after a reseed),
        # still make sure it's a usable staff/superuser with the known password
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        topup_note = "Solde initial admin (dev)"
        if not user.transaction_set.filter(note=topup_note).exists():
            Transaction.objects.create(
                user=user,
                initiator=user,
                amount=Decimal("999999.42"),
                type=Transaction.TransactionTypeChoices.OTHER,
                note=topup_note,
            )

        verb = "Created" if created else "Reset"
        self.stdout.write(
            self.style.SUCCESS(f"{verb} admin user: {email} / {password}")
        )
