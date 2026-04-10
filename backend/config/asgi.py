"""
ASGI config for Companion OS.

ASGI = Asynchronous Server Gateway Interface.
Why ASGI and not WSGI? Claude's API streams responses — it sends tokens one by one
as they are generated. ASGI handles long-lived async connections. WSGI cannot.
Without ASGI, the user would wait for the entire response before seeing anything.
With ASGI, the response appears word by word in real time, like the Streamlit version does now.
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_asgi_application()
