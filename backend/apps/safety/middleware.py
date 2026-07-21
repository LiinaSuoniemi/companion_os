"""
Kill switch middleware.

Checks SystemConfig.maintenance_mode on every request. If True, returns
a 503 maintenance page (with crisis helplines visible) instead of routing
to the normal view. If False, the request proceeds normally.

Design decisions:

1. /admin/ is exempt
   So the operator can always reach the kill switch to turn it off,
   without needing a redeploy.

2. /static/ is exempt
   Static assets should still serve so admin tools render correctly
   during maintenance.

3. Fail-open on database error
   If the SystemConfig query throws (DB outage, connection timeout),
   we let the request through. Reasoning: the kill switch is one of
   three kill paths (Anthropic API key revoke and Railway service stop
   are the others). Fail-closed would lock the operator out of /admin
   during any DB blip with no way back in. Vulnerable users mid-
   conversation should not be locked out by a transient hiccup.

4. Inline HTML, no template dependency
   The maintenance page is rendered from a hardcoded string. If
   templates break, the kill switch still works.

5. Crisis helplines always visible
   "The AI never pastes a hotline number and goes quiet" — even when
   the AI itself is paused, helplines remain reachable.
"""

import logging

from django.core.cache import cache
from django.db import Error as DatabaseError
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class MaintenanceModeMiddleware:
    """Halts all non-admin requests when SystemConfig.maintenance_mode is True."""

    EXEMPT_PREFIXES = ("/admin/", "/static/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            from apps.safety.models import SystemConfig
            config = SystemConfig.get()
        except DatabaseError:
            # Fail-open on a database error: a DB outage must not lock the
            # operator out (the kill switch is not the only kill path). But
            # make the failure visible instead of silent, so a real DB problem
            # is not mistaken for normal operation.
            logger.error(
                "MaintenanceModeMiddleware: could not read SystemConfig "
                "(database error). Failing open and serving the request."
            )
            return self.get_response(request)

        if config.maintenance_mode:
            return HttpResponse(
                _maintenance_html(config.maintenance_message),
                status=503,
                content_type="text/html; charset=utf-8",
            )

        return self.get_response(request)


class DailySecurityLogPurgeMiddleware:
    """Runs the 30-day security-log purge at most once per day, in-process.

    django-axes login records are only removed by an explicit purge. Instead of
    depending on an external scheduler (a Railway cron that must be set up by
    hand and is easy to forget, which is exactly how these logs were piling up),
    this fires the purge in the app itself, gated by a 24h cache lock so it runs
    at most once a day. It travels with the app to any host.

    cache.add() sets the lock only if it is absent and returns True, so the first
    request after the lock expires runs the purge and every other request in the
    window is one cheap cache read that skips it. The purge runs after the
    response is produced.

    Fail-open by design: a purge error is logged loudly and swallowed. A cleanup
    task must never break a page for a user. The broad except is deliberate for
    that reason, and logger.exception keeps any real failure visible.
    """

    LOCK_KEY = "security_log_purge_ran"
    LOCK_TTL = 60 * 60 * 24  # 24 hours

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if cache.add(self.LOCK_KEY, "1", self.LOCK_TTL):
                from apps.safety.purge import purge_old_security_logs
                purge_old_security_logs()
        except Exception:
            logger.exception(
                "DailySecurityLogPurgeMiddleware: purge failed; ignored so the "
                "request is unaffected."
            )
        return response


def _maintenance_html(message: str) -> str:
    """Inline maintenance page. No template dependency."""
    safe_message = (
        (message or "Companion OS is temporarily unavailable.")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Companion OS — Temporarily unavailable</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
      background: #f5efe6;
      color: #3a2e22;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 1rem;
    }}
    .box {{
      max-width: 32rem;
      text-align: center;
      background: #fffaf2;
      padding: 2rem;
      border-radius: 0.5rem;
      border: 1px solid #d6c9b3;
    }}
    h1 {{ margin-top: 0; font-size: 1.5rem; color: #5a4a36; }}
    p {{ line-height: 1.6; }}
    .helplines {{
      margin-top: 1.5rem;
      padding-top: 1.5rem;
      border-top: 1px solid #e6dcc8;
      font-size: 0.95rem;
      color: #5a4a36;
      text-align: left;
    }}
    .helplines strong {{ display: block; margin-bottom: 0.5rem; text-align: center; }}
    .helplines a {{ color: #5a4a36; }}
  </style>
</head>
<body>
  <div class="box">
    <h1>Companion OS</h1>
    <p>{safe_message}</p>
    <div class="helplines">
      <strong>If you need immediate help</strong>
      Finland: 116 123 (MIELI) &middot; 112 (emergency)<br>
      Estonia: 116 006 &middot; 112<br>
      International: <a href="https://findahelpline.com">findahelpline.com</a>
    </div>
  </div>
</body>
</html>"""
