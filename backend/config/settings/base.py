"""
Base settings for Companion OS.
These settings apply in all environments (development and production).
Environment-specific settings live in development.py and production.py.
"""
import os
from pathlib import Path

# Base directory is the backend/ folder
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY: Secret key must be set in environment variables.
# Never hardcode this. Never commit this.
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY")

# Apps built into Django
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

# Our apps
LOCAL_APPS = [
    "apps.accounts",
    "apps.chat",
    "apps.safety",
    "apps.admin_panel",
]

INSTALLED_APPS = DJANGO_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Our security middleware — prompt injection protection (Layer 1)
    # Will be built in apps/safety/middleware.py
    # "apps.safety.middleware.SecurityMiddleware",  # uncomment when built
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ASGI for async streaming (Claude API responses stream in real time)
ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# Password validation rules
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Use our custom User model (defined in apps/accounts/models.py)
# We set this now so we never have to migrate away from Django's default User later
# Changing this after the first migration is a nightmare — set it on day one
AUTH_USER_MODEL = "accounts.User"

# Internationalisation — Finnish, Estonian, English from day one
# Retrofitting i18n later is painful. Cost of including it now: near zero.
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Europe/Helsinki"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("fi", "Finnish"),
    ("et", "Estonian"),
    ("en", "English"),
]

LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Where to send users after login / logout
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "chat:chat"
LOGOUT_REDIRECT_URL = "accounts:login"

# Anthropic API key — from environment, never hardcoded
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

# Redis — for session tracking and security attempt counters
REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
