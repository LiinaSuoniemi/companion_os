"""
Usage app — Models.

Two models:
- UsageQuota:  Per-user conversation limits (daily and monthly).
               Admin can override limits for individual users.
- UsageEvent:  Timestamped log of conversation creation events.
               Only recorded if the user consented to usage tracking.
               This is the data that feeds the Anthropic application
               and Business Finland reporting.

Design decisions:
- Counter increments on conversation CREATE, not on message send.
  A person in crisis might need 20 turns in one sitting. Counting
  turns would cut them off mid-crisis. That cannot happen.
- Daily reset happens automatically when the date changes.
  Monthly reset happens when the month changes.
  No cron job needed. The check runs on every create_for_user call.
- Defaults: 2 conversations/day, 30/month. With 10 pilot users
  at 2/day, cost stays around 60-100 EUR/month.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone


class UsageQuota(models.Model):
    """
    Per-user conversation quota.

    One row per user. Created automatically when a user registers
    (via post_save signal). Admin can adjust limits per user from
    the Django admin panel.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_quota",
    )

    # Limits — admin can bump these for individual users
    daily_limit = models.PositiveIntegerField(
        default=2,
        help_text="Max new conversations per day. 0 = unlimited.",
    )
    monthly_limit = models.PositiveIntegerField(
        default=30,
        help_text="Max new conversations per month. 0 = unlimited.",
    )

    # Counters — reset automatically when date/month changes
    daily_used = models.PositiveIntegerField(default=0)
    monthly_used = models.PositiveIntegerField(default=0)
    last_daily_reset = models.DateField(default=timezone.now)
    last_monthly_reset = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Usage Quota"
        verbose_name_plural = "Usage Quotas"

    def __str__(self):
        return f"{self.user.username} — {self.daily_used}/{self.daily_limit} today, {self.monthly_used}/{self.monthly_limit} this month"

    def _reset_if_needed(self):
        """
        Reset counters if the date or month has rolled over.
        Called internally before every quota check.
        """
        today = timezone.now().date()
        changed = False

        if self.last_daily_reset < today:
            self.daily_used = 0
            self.last_daily_reset = today
            changed = True

        if (self.last_monthly_reset.year < today.year
                or self.last_monthly_reset.month < today.month):
            self.monthly_used = 0
            self.last_monthly_reset = today
            changed = True

        if changed:
            self.save(update_fields=[
                "daily_used", "monthly_used",
                "last_daily_reset", "last_monthly_reset",
            ])

    def can_create_conversation(self):
        """
        Check if the user can create a new conversation right now.
        Returns (allowed: bool, reason: str).
        """
        self._reset_if_needed()

        if self.daily_limit > 0 and self.daily_used >= self.daily_limit:
            return False, (
                f"You have used your {self.daily_limit} conversations for today. "
                "Your limit resets tomorrow. If you need to talk now, "
                "you can continue an existing conversation."
            )

        if self.monthly_limit > 0 and self.monthly_used >= self.monthly_limit:
            return False, (
                f"You have used your {self.monthly_limit} conversations for this month. "
                "Your limit resets next month. You can still continue "
                "any existing conversation."
            )

        return True, ""

    def increment(self):
        """
        Increment both daily and monthly counters.
        Called after a conversation is successfully created.
        """
        self._reset_if_needed()
        self.daily_used += 1
        self.monthly_used += 1
        self.save(update_fields=["daily_used", "monthly_used"])

    @property
    def daily_remaining(self):
        self._reset_if_needed()
        if self.daily_limit == 0:
            return None  # unlimited
        return max(0, self.daily_limit - self.daily_used)

    @property
    def monthly_remaining(self):
        self._reset_if_needed()
        if self.monthly_limit == 0:
            return None  # unlimited
        return max(0, self.monthly_limit - self.monthly_used)


class UsageEvent(models.Model):
    """
    Timestamped usage event for analytics.

    Only created if the user has consent_usage_tracking = True.
    This is the data that shows Anthropic and Business Finland
    how the product is actually used.

    No conversation content is stored here. Just the event type
    and timestamp.
    """

    EVENT_CHOICES = [
        ("conversation_created", "Conversation created"),
        ("conversation_deleted", "Conversation deleted"),
        ("mode_used", "Mode used"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="usage_events",
    )
    event_type = models.CharField(max_length=30, choices=EVENT_CHOICES)
    mode = models.CharField(max_length=50, blank=True, default="")
    token_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.event_type} ({self.created_at:%Y-%m-%d %H:%M})"
