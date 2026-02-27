from pprint import pformat

from authlib.integrations.requests_client import OAuth2Session
from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from helloasso_python import ApiClient, Configuration

TOKEN_CACHE_KEY = "helloasso_token"  # noqa: S105


def update_token(token, refresh_token=None, access_token=None):
    """Callback function: Authlib calls this when it gets a new token."""
    # Store the entire token dictionary (includes access, refresh, and expires_at)
    cache.set(TOKEN_CACHE_KEY, token)


def get_oauth_session():
    # 1. Try to get the existing token from cache
    token = cache.get(TOKEN_CACHE_KEY)

    # 2. Initialize the session with the 'update_token' callback
    client = OAuth2Session(
        settings.HELLOASSO_CLIENT_ID,
        settings.HELLOASSO_CLIENT_SECRET,
        token=token,
        token_endpoint=settings.HELLOASSO_TOKEN_URL,
        update_token=update_token,
    )

    # 3. If no token exists at all, perform the initial fetch
    if not token:
        token = client.fetch_token(grant_type="client_credentials")
        update_token(token)

    return client


def get_fresh_token():
    oauth = get_oauth_session()
    oauth.ensure_active_token()

    return oauth.token["access_token"]


def get_api_client():
    config = Configuration(host=settings.HELLOASSO_API_URL)
    config.access_token = get_fresh_token()
    return ApiClient(configuration=config)


def log_api_exception(e, fnct):
    mail_admins(
        "Erreur API HelloAsso",
        f"Erreur suivante lors de l'appel de {fnct.__name__} :\n\n{pformat(e)}",
    )
