"""Production settings with explicit deployment safety checks."""

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from config.env import env

DEBUG = False

if not SECRET_KEY or SECRET_KEY.startswith("django-insecure-change-this"):  # noqa: F405
    raise ImproperlyConfigured(
        "Set a unique SECRET_KEY environment variable before using production settings."
    )

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "Set ALLOWED_HOSTS to the production hostnames before using production settings."
    )

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
