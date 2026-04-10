"""
Production settings for Companion OS.
Used on Railway. Never used locally.
DEBUG is False — errors never shown to users, logged internally only.
"""
from .base import *

DEBUG = False

# Only allow the real domain — set this when Railway gives you the URL
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

# Production database — Railway injects DATABASE_URL automatically
import dj_database_url
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        conn_max_age=600,
        ssl_require=True,
    )
}

# Security headers — these protect against common web attacks
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files served by WhiteNoise (no separate file server needed on Railway)
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
