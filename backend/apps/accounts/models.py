from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom User model for Companion OS.

    Why extend AbstractUser instead of using Django's default?
    Because we need fields Django doesn't have by default:
    - language preference (Finnish, Estonian, English)
    - voice preference (Warm, Sharp, Steady, Spark, Coach)
    - age verification status (for under-18 parental consent flow)

    If we used Django's default User and later needed these fields,
    we'd have to do a complex migration. Setting this on day one costs nothing.
    """

    LANGUAGE_CHOICES = [
        ("fi", "Finnish"),
        ("et", "Estonian"),
        ("en", "English"),
    ]

    VOICE_CHOICES = [
        ("steady", "Steady"),  # default — calm, no drama
        ("warm", "Warm"),
        ("sharp", "Sharp"),
        ("spark", "Spark"),
        ("coach", "Coach"),
    ]

    language_preference = models.CharField(
        max_length=2,
        choices=LANGUAGE_CHOICES,
        default="en",
    )
    voice_preference = models.CharField(
        max_length=10,
        choices=VOICE_CHOICES,
        default="steady",
    )
    is_age_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username
