"""
Accounts app — Forms.

Why UserCreationForm as the base?
Django's UserCreationForm already handles:
- password confirmation (type it twice, must match)
- password strength validation
- duplicate username check

We extend it to add our custom fields (language, voice preference, consent).
Writing this from scratch would mean reimplementing all of that.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import InviteCode, User


class RegisterForm(UserCreationForm):
    """
    Registration form for new Companion OS users.

    Requires a valid invite code. No code = no account.
    Requires explicit consent for conversation processing (GDPR Article 9).
    Optional consent for usage tracking and impact survey.
    """

    invite_code = forms.CharField(
        max_length=40,
        label="Invite code",
        help_text="You need an invite code to create an account.",
    )

    class Meta:
        model = User
        fields = [
            "invite_code",
            "username",
            "password1",
            "password2",
        ]

    def clean(self):
        """Validate that conversation consent is given. Required by GDPR Article 9."""
        cleaned_data = super().clean()
        if self.data.get("consent_conversations") != "on":
            raise forms.ValidationError(
                "You must consent to conversation processing to create an account. "
                "Without this consent, Companion OS cannot function."
            )
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # Read consent checkboxes from POST data
        user.consent_conversations = self.data.get("consent_conversations") == "on"
        user.consent_usage_tracking = self.data.get("consent_usage_tracking") == "on"
        user.consent_impact_survey = self.data.get("consent_impact_survey") == "on"
        if user.consent_conversations:
            user.consent_given_at = timezone.now()
        if commit:
            user.save()
        return user

    def clean_invite_code(self):
        """Validate the invite code exists and is still usable."""
        code = self.cleaned_data.get("invite_code", "").strip()
        try:
            invite = InviteCode.objects.get(code=code)
        except InviteCode.DoesNotExist:
            raise forms.ValidationError("This invite code is not valid.")

        if not invite.is_valid:
            raise forms.ValidationError("This invite code has already been used.")

        # Store the invite object so the view can mark it as used after save
        self._invite = invite
        return code
