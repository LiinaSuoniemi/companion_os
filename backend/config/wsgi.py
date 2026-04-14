"""
WSGI config for Companion OS.
Used for non-async parts of the app (admin, static files).
ASGI handles the chat. WSGI handles everything else.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

application = get_wsgi_application()
