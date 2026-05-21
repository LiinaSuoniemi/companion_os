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

Run this once a month to honour the 30-day retention period stated
in the privacy policy. Add to a Railway cron job if you want it automated.
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Delete axes login attempt records older than 30 days."

    def handle(self, *args, **options):
        from axes.models import AccessAttempt, AccessLog

        cutoff = timezone.now() - timedelta(days=30)

        attempts_deleted, _ = AccessAttempt.objects.filter(attempt_time__lt=cutoff).delete()
        logs_deleted, _ = AccessLog.objects.filter(attempt_time__lt=cutoff).delete()

        total = attempts_deleted + logs_deleted
        logger.info("purge_security_logs: deleted %d records older than 30 days.", total)
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {total} security log records older than 30 days."
        ))
