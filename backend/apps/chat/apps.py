import os
import sys
import threading

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.chat"

    def ready(self):
        # Pre-warm the voice models at startup so the FIRST mic click and first
        # "speak" aren't slow — the heavy model load happens now, in the background,
        # instead of on the user's first click.
        # Guarded: only in the running dev server (runserver) and only in the process
        # that actually serves requests (RUN_MAIN), so migrate / collectstatic / shell
        # never trigger a heavy model load or download.
        if "runserver" not in sys.argv or os.environ.get("RUN_MAIN") != "true":
            return

        def _warm():
            try:
                from . import voice
                voice.get_whisper()
                voice.get_synth()
            except Exception:
                # Warming must never crash the server; the models fall back to
                # loading lazily on first use.
                pass

        threading.Thread(target=_warm, daemon=True).start()
