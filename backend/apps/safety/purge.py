"""
Shared security-log purge logic.

django-axes does not auto-expire login attempt records. This deletes records
older than the retention window (30 days), matching the privacy notice. The
same function backs both the manual `purge_security_logs` management command
and the automatic once-a-day middleware, so there is one source of truth.
"""
import logging
from datetime import timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


def purge_old_security_logs(days: int = RETENTION_DAYS) -> int:
    """Delete axes login records older than `days`. Returns the number deleted."""
    from axes.models import AccessAttempt, AccessLog

    cutoff = timezone.now() - timedelta(days=days)
    attempts_deleted, _ = AccessAttempt.objects.filter(attempt_time__lt=cutoff).delete()
    logs_deleted, _ = AccessLog.objects.filter(attempt_time__lt=cutoff).delete()
    total = attempts_deleted + logs_deleted
    logger.info("purge_old_security_logs: deleted %d records older than %d days.", total, days)
    return total
