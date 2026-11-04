"""Local development settings."""

from .base import *  # noqa: F403
from config.env import env

DEBUG = True
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS",default=["localhost", "127.0.0.1", "[::1]"]) # type:ignore
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS",default=["http://localhost:5173","http://127.0.0.1:5173"]) # type:ignore
SECURE_SSL_REDIRECT = False
