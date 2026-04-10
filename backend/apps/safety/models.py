from django.conf import settings
from django.db import models


class SafetyEvent(models.Model):
    """
    Records when a safety tier was triggered.

    CRITICAL DESIGN DECISION: We store NO conversation content here.
    Only the tier, the timestamp, and a hashed signal.

    Why hashed signal and not the original text?
    Because if this database were subpoenaed or breached,
    there is nothing here that identifies what the person said.
    The hash tells us a signal matched. It does not tell us what the signal was.
    This is GDPR-safe by design.

    This is enough for:
    - Auditing that the safety system is working
    - Providing aggregate statistics to parents (if minor)
    - Investigating if something went wrong
    """

    TIER_CHOICES = [
        (1, "General distress"),
        (2, "Warning signs"),
        (3, "Immediate danger"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # keep the event record even if user deletes account
        null=True,
        related_name="safety_events",
    )
    tier = models.IntegerField(choices=TIER_CHOICES)
    signal_hash = models.CharField(max_length=64)  # SHA-256 hash of the triggering signal
    triggered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self):
        return f"Tier {self.tier} — {self.triggered_at:%Y-%m-%d %H:%M}"


class SystemConfig(models.Model):
    """
    The kill switch.

    One row. One field that matters: maintenance_mode.
    If maintenance_mode is True, the app halts before processing any request.
    Accessible from the admin panel via phone on a secret URL.
    Flip it in under 60 seconds from anywhere.

    Why a database row instead of an environment variable?
    Because changing an env variable requires a redeploy (minutes).
    Flipping a database row is instant.
    """

    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        default="Companion OS is temporarily unavailable. Please check back shortly."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "System Configuration"
        verbose_name_plural = "System Configuration"

    def __str__(self):
        status = "MAINTENANCE MODE ON" if self.maintenance_mode else "Running normally"
        return f"System Config — {status}"

    def save(self, *args, **kwargs):
        # Enforce single row — there should only ever be one SystemConfig
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        """Get the single config row, creating it if it doesn't exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
