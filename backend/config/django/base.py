"""Shared Django settings for all deployment environments."""

from pathlib import Path

from config.env import BASE_DIR, env

env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[]) # type:ignore
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[]) # type:ignore

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "accounts.apps.AccountsConfig",
    "requisitions.apps.RequisitionsConfig",
    "candidates.apps.CandidatesConfig",
    "llm.apps.LLMConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": Path(env("SQLITE_DB_PATH", default=str(BASE_DIR / "db.sqlite3"))), # type:ignore
    "CONN_MAX_AGE": 0,
}}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = env("LANGUAGE_CODE", default="en-us") # type:ignore
TIME_ZONE = env("TIME_ZONE", default="UTC") # type:ignore
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend") # type:ignore
EMAIL_HOST = env("EMAIL_HOST", default="") # type:ignore
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="") # type:ignore
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="") # type:ignore
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@example.invalid") # type:ignore
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "30/min", "user": "120/min"},
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": __import__("datetime").timedelta(days=10),
    "REFRESH_TOKEN_LIFETIME": __import__("datetime").timedelta(days=10),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "UPDATE_LAST_LOGIN": False,
}


# Azure OpenAI v1 client controls. Secrets remain in backend/.env only.
AZURE_OPENAI_ENDPOINT = env("AZURE_OPENAI_ENDPOINT", default="") # type:ignore
AZURE_OPENAI_API_KEY = env("AZURE_OPENAI_API_KEY", default="") # type:ignore
AZURE_OPENAI_CHAT_DEPLOYMENT = env("AZURE_OPENAI_CHAT_DEPLOYMENT", default="") # type:ignore
AZURE_OPENAI_TIMEOUT_SECONDS = env.int("AZURE_OPENAI_TIMEOUT_SECONDS", default=30)
AZURE_OPENAI_MAX_RETRIES = env.int("AZURE_OPENAI_MAX_RETRIES", default=2)
AZURE_OPENAI_REASONING_EFFORT = env("AZURE_OPENAI_REASONING_EFFORT", default="low") # type:ignore
AZURE_OPENAI_MAX_COMPLETION_TOKENS = env.int("AZURE_OPENAI_MAX_COMPLETION_TOKENS", default=2000)

# Private resume upload limits and Django multipart request limits.
RESUME_MAX_FILE_SIZE_MB = env.int("RESUME_MAX_FILE_SIZE_MB", default=10)
RESUME_MAX_FILE_SIZE_BYTES = RESUME_MAX_FILE_SIZE_MB * 1024 * 1024
RESUME_MAX_BATCH_FILES = env.int("RESUME_MAX_BATCH_FILES", default=20)
RESUME_MAX_BATCH_TOTAL_MB = env.int("RESUME_MAX_BATCH_TOTAL_MB", default=50)
RESUME_MAX_BATCH_TOTAL_BYTES = RESUME_MAX_BATCH_TOTAL_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = RESUME_MAX_BATCH_TOTAL_BYTES + (1024 * 1024)
FILE_UPLOAD_PERMISSIONS = 0o640

LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper() # type:ignore
LOGGING = {
    "version": 1, "disable_existing_loggers": False,
    "formatters": {"standard": {"format": "{asctime} {levelname} {name}: {message}", "style": "{"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "standard"}},
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {"django": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False}},
}
