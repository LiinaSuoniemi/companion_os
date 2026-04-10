"""
Development settings for Companion OS.
Used locally. Never deployed to production.
DEBUG is True — full error pages visible, which you want when building.
"""
from .base import *

DEBUG = True

# Allow connections from localhost and Docker internal network
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# Local PostgreSQL running in Docker
# These values match what we set in docker-compose.yml
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "companion_os"),
        "USER": os.environ.get("POSTGRES_USER", "companion"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "companion_dev_password"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

# Print emails to terminal instead of sending them (useful during development)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
