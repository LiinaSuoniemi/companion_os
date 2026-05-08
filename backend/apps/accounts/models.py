import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class InviteCode(models.Model):
    """
    Access control for Companion OS registration.

    Why invite codes?
    This app serves vulnerable people. Open registration means anyone can
    sign up, including bad actors. Invite codes let Liina control who gets
    access during early testing and beyond.

    Each code can be single-use or multi-use (max_uses).
    Once used up, it cannot be reused.
    """

    code = models.CharField(
        max_length=40,
        unique=True,
        default=uuid.uuid4,
        help_text="The invite code users enter during registration.",
    )
    label = models.CharField(
        max_length=100,
        blank=True,
        help_text="Who is this code for? e.g. 'Niina testing', 'Jon demo'",
    )
    max_uses = models.PositiveIntegerField(
        default=1,
        help_text="How many times this code can be used. 0 = unlimited.",
    )
    times_used = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        status = "active" if self.is_active and not self.is_exhausted else "used up"
        return f"{self.label or self.code} ({status})"

    @property
    def is_exhausted(self):
        """True if the code has been used up (max_uses > 0 and reached)."""
        if self.max_uses == 0:
            return False  # unlimited
        return self.times_used >= self.max_uses

    @property
    def is_valid(self):
        """True if this code can still be used."""
        return self.is_active and not self.is_exhausted

    def use(self):
        """Mark one use of this code."""
        self.times_used += 1
        self.save(update_fields=["times_used"])


class User(AbstractUser):
    """
    Custom User model for Companion OS.

    Why extend AbstractUser instead of using Django's default?
    Because we need fields Django doesn't have by default:
    - language preference (Finnish, Estonian, English)
    - age verification status (for under-18 parental consent flow)

    If we used Django's default User and later needed these fields,
    we'd have to do a complex migration. Setting this on day one costs nothing.
    """

    LANGUAGE_CHOICES = [
        ("fi", "Finnish"),
        ("et", "Estonian"),
        ("en", "English"),
    ]

    language_preference = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    is_age_verified = models.BooleanField(default=False)
    consent_conversations = models.BooleanField(
        default=False,
        help_text="User consented to conversation storage and processing.",
    )
    consent_usage_tracking = models.BooleanField(
        default=False,
        help_text="User consented to anonymised usage data collection.",
    )
    consent_impact_survey = models.BooleanField(
        default=False,
        help_text="User consented to optional impact survey.",
    )
    consent_given_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class ImpactSurvey(models.Model):
    """
    Anonymised impact survey response.

    Collected at signup (baseline) and after 4 weeks (follow-up).
    Measures whether Companion OS makes a difference in daily life.
    This is product impact research, not clinical assessment.

    Scores are NEVER shown back to the user.
    Responses are anonymised: stored with user FK for timing logic
    but reported only in aggregate.
    """

    SURVEY_TYPE_CHOICES = [
        ("baseline", "Baseline (signup)"),
        ("followup", "Follow-up (4 weeks)"),
    ]

    SITUATION_CHOICES = [
        ("working_ft", "Working full time"),
        ("working_pt", "Working part time"),
        ("studying_ft", "Studying full time"),
        ("studying_pt", "Studying part time"),
        ("parent", "Parent or caregiver"),
    ]

    AGE_RANGE_CHOICES = [
        ("under_18", "Under 18"),
        ("18_25", "18-25"),
        ("26_35", "26-35"),
        ("36_50", "36-50"),
        ("51_65", "51-65"),
        ("over_65", "Over 65"),
    ]

    COUNTRY_CHOICES = [
        ("fi", "Finland"),
        ("ee", "Estonia"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="impact_surveys",
    )
    survey_type = models.CharField(max_length=10, choices=SURVEY_TYPE_CHOICES)

    # Scaled questions (1-5)
    handle_difficult_moments = models.PositiveSmallIntegerField(
        help_text="In the past week, I felt able to handle difficult moments in my day.",
    )
    notice_stress_building = models.PositiveSmallIntegerField(
        help_text="I notice when my stress or emotions are building up before they become overwhelming.",
    )
    have_something_to_try = models.PositiveSmallIntegerField(
        help_text="When I feel stuck or overwhelmed, I have something I can try that helps.",
    )
    get_through_daily_tasks = models.PositiveSmallIntegerField(
        help_text="I have been able to get through my daily tasks and responsibilities.",
    )
    # Follow-up only
    feel_more_grounded = models.PositiveSmallIntegerField(
        null=True, blank=True,
        help_text="Overall, I feel more steady and grounded in my daily life than I did a month ago.",
    )

    # Background (all optional)
    age_range = models.CharField(max_length=10, choices=AGE_RANGE_CHOICES, blank=True)
    situation = models.JSONField(
        default=list, blank=True,
        help_text="Multiple select: working_ft, working_pt, studying_ft, studying_pt, parent",
    )
    country = models.CharField(max_length=50, blank=True)

    # Open text
    what_brought_you = models.TextField(
        blank=True,
        help_text="What brought you to Companion OS? (baseline)",
    )
    what_changed = models.TextField(
        blank=True,
        help_text="Is there anything that has changed in your daily life? (follow-up)",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.username} — {self.survey_type} ({self.created_at:%Y-%m-%d})"


class PilotApplication(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("waitlisted", "Waitlisted"),
    ]

    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    what_brings_you = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.email}) — {self.status}"
