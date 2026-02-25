from html2text import HTML2Text
from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.mail import get_connection, EmailMultiAlternatives
from datetime import time, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.core.validators import EmailValidator
from django.utils.deconstruct import deconstructible

# Configuration of html2text
text_maker = HTML2Text()
text_maker.ignore_tables = True
text_maker.images_to_alt = True
text_maker.body_width = 1000
text_maker_translation = str.maketrans("[]", "  ")


def html_to_text(html_content):
    return (
        text_maker.handle(html_content)
        .translate(text_maker_translation)
        .replace("**", "*")
    )


# Login required with ability to set custom login message
def login_required_with_message(
    message="Tu dois être connecté pour accéder à cette page.",
):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                request.session["login_message"] = message
                request.session["login_next"] = (
                    None  # Stored to be able to invalidate message in case the querystring changes and not this session variable. Will be set in the view.
                )
            # apply normal login_required check
            return login_required(view_func)(request, *args, **kwargs)

        return _wrapped_view

    return decorator


def send_mass_html_mail(
    datatuple, fail_silently=False, user=None, password=None, connection=None
):
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    """
    connection = connection or get_connection(
        username=user, password=password, fail_silently=fail_silently
    )
    messages = []
    for subject, text, html, from_email, recipient in datatuple:
        message = EmailMultiAlternatives(subject, text, from_email, recipient)
        message.attach_alternative(html, "text/html")
        messages.append(message)
    return connection.send_messages(messages)


def append_unique_in_order(list1, list2, *lists):
    # 1. Create a set from list_a for fast O(1) lookups.
    # We use a set for efficiency, and it contains all elements already in list_a.
    existing_elements = set(list1)
    new_list = list(list1[:])  # to not modify original list

    # 2. Iterate through list_b, maintaining the original order.
    for l in (list2,) + lists:
        for item in l:
            # Check if the item is NOT already in our set of existing elements
            if item not in existing_elements:
                # 3. If it's new, append it to list_a and ADD it to the set.
                new_list.append(item)
                existing_elements.add(item)

    return new_list


def first_editable_day():
    current_time_local = timezone.localtime(timezone.now())
    today = current_time_local.date()
    cutoff = getattr(settings, "DELIVERY_CUTOFF_TIME", time(6, 30))

    if current_time_local.time() < cutoff:
        return today
    else:
        return today + timedelta(1)


def SendMailVerification(user, new_email, request):
    from .models import User

    # Temporarily set the email to generate the token
    current_email = user.email
    user.email = new_email
    user_pk_bytes = force_bytes(User._meta.pk.value_to_string(user))
    token = PasswordResetTokenGenerator().make_token(user)

    receiver_email = new_email
    template_name = "mail/verify_email_mail.html"
    convert_to_html_content = render_to_string(
        template_name=template_name,
        context={
            "request": request,
            "uid": urlsafe_base64_encode(user_pk_bytes),
            "email64": urlsafe_base64_encode(force_bytes(new_email)),
            "token": token,
            "user": user,
        },
    )

    send_mail(
        subject="Vérification de l'email",
        message=html_to_text(convert_to_html_content),
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[
            receiver_email,
        ],
        html_message=convert_to_html_content,
        fail_silently=True,
    )

    # Reset user email
    user.email = current_email


def PrecreateUserFunction(user, request):
    return PrecreateUsersFunction([user], request)


def SendPrecreationMailFunction(user, request):
    return SendPrecreationMailsFunction([user], request)


def PrecreateUsersFunction(users, request):
    # Create users in DB
    for user in users:
        user.date_joined = None  # To indicate that the user hasn't yet joined
        user.is_active = False
        user.save()

    SendPrecreationMailsFunction(users, request)


def SendPrecreationMailsFunction(users, request):
    from .models import User

    # Send pre-creation emails
    emails = []
    template_name = "mail/precreation_mail.html"
    for user in users:
        user_pk_bytes = force_bytes(User._meta.pk.value_to_string(user))
        token = PasswordResetTokenGenerator().make_token(user)
        convert_to_html_content = render_to_string(
            template_name=template_name,
            context={
                "request": request,
                "uid": urlsafe_base64_encode(user_pk_bytes),
                "token": token,
                "user": user,
            },
        )
        emails.append(
            (
                "Création de ton compte Pain'Gouin",
                html_to_text(convert_to_html_content),
                convert_to_html_content,
                settings.EMAIL_HOST_USER,
                [
                    user.email,
                ],
            )
        )

    send_mass_html_mail(emails, fail_silently=True)


@deconstructible
class WhitelistEmailValidator(EmailValidator):
    def validate_domain_part(self, domain_part):
        if domain_part in self.whitelist:
            return True
        return False

    def __eq__(self, other):
        return isinstance(other, WhitelistEmailValidator) and super().__eq__(other)

    def __init__(self, whitelist, message=None, code=None):
        self.whitelist = set(whitelist)
        super().__init__(message, code)
