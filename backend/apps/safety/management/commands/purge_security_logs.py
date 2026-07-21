"""
purge_security_logs management command.

Deletes django-axes login attempt records older than 30 days.
Axes does not auto-expire records — this command is the cleanup mechanism.

Usage
-----
Railway production:
    railway run python manage.py purge_security_logs

Local Docker:
    docker compose exec web python manage.py purge_security_logs

This is the manual entry point. The same purge also runs automatically once a
day via DailySecurityLogPurgeMiddleware, so the 30-day retention holds without
any external scheduler. Run this command any time you want to purge on demand.
"""
from django.core.management.base import BaseCommand

from apps.safety.purge import purge_old_security_logs


class Command(BaseCommand):
    help = "Delete axes login attempt records older than 30 days."

    def handle(self, *args, **options):
        total = purge_old_security_logs()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {total} security log records older than 30 days."
        ))
