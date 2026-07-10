"""
Accounts app — Views.

Why class-based views (CBV) instead of function-based views (FBV)?
For register, either would work. We use CBV here to stay consistent
with Django's built-in auth views (LoginView, LogoutView) and because
CBVs are easier to extend later (e.g. adding OAuth on top).
"""
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.decorators import method_decorator
from django.views import View

from .forms import RegisterForm
from .models import ImpactSurvey


SUPPORTED_LANGS = {"en", "fi", "et"}


def set_language_pref(request):
    lang = request.GET.get("lang", "en")
    if lang in SUPPORTED_LANGS:
        request.session["ui_lang"] = lang
    next_url = request.GET.get("next", "/")
    # Prevent open redirects — only allow same-origin relative paths
    if not next_url.startswith("/") or next_url.startswith("//"):
        next_url = "/"
    return redirect(next_url)


class RegisterView(View):
    """
    Handles GET and POST for the registration page.

    GET  → show empty form
    POST → validate form, create user, log them in, redirect to home
    """

    template_name = "accounts/register.html"

    def get(self, request):
        # If already logged in, no point showing register page
        if request.user.is_authenticated:
            return redirect("home")
        form = RegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Mark the invite code as used
            form._invite.use()
            # Log the user in immediately after registering
            # so they don't have to log in again right away
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            # If user consented to impact survey, show it first
            if user.consent_impact_survey:
                return redirect("accounts:impact_survey")
            return redirect("home")
        # Form invalid — re-render with error messages attached to the form
        return render(request, self.template_name, {"form": form})


@method_decorator(login_required, name="dispatch")
class ImpactSurveyView(View):
    """
    Impact survey page. Shows automatically on first login if user consented.
    Shows again after 4 weeks for the follow-up.

    This is product impact research, not clinical assessment.
    Scores are never shown back to the user.
    """
    template_name = "accounts/impact_survey.html"

    def get(self, request):
        survey_type = self._get_survey_type(request.user)
        if not survey_type:
            return redirect("chat:conversation_list")
        return render(request, self.template_name, {
            "survey_type": survey_type,
            "is_followup": survey_type == "followup",
        })

    def post(self, request):
        survey_type = request.POST.get("survey_type", "baseline")

        # Parse situation checkboxes (multiple select)
        situation = []
        for option in ["working_ft", "working_pt", "studying_ft", "studying_pt", "parent"]:
            if request.POST.get(f"situation_{option}"):
                situation.append(option)

        def _scale(val):
            try:
                return max(1, min(5, int(val)))
            except (TypeError, ValueError):
                return 3

        survey = ImpactSurvey(
            user=request.user,
            survey_type=survey_type,
            handle_difficult_moments=_scale(request.POST.get("q1")),
            notice_stress_building=_scale(request.POST.get("q2")),
            have_something_to_try=_scale(request.POST.get("q3")),
            get_through_daily_tasks=_scale(request.POST.get("q4")),
            age_range=request.POST.get("age_range", ""),
            situation=situation,
            country=request.POST.get("country_other", "").strip() or request.POST.get("country", ""),
            what_brought_you=request.POST.get("what_brought_you", "")[:2000],
        )

        if survey_type == "followup":
            survey.feel_more_grounded = _scale(request.POST.get("q5"))
            survey.what_changed = request.POST.get("what_changed", "")[:2000]

        survey.save()
        return redirect("chat:conversation_list")

    def _get_survey_type(self, user):
        """Determine which survey to show, or None if no survey needed."""
        if not user.consent_impact_survey:
            return None

        has_baseline = ImpactSurvey.objects.filter(
            user=user, survey_type="baseline"
        ).exists()

        if not has_baseline:
            return "baseline"

        # Check if follow-up is due (4+ weeks since account creation)
        from django.utils import timezone
        import datetime
        weeks_since_signup = (timezone.now() - user.created_at).days // 7
        if weeks_since_signup >= 4:
            has_followup = ImpactSurvey.objects.filter(
                user=user, survey_type="followup"
            ).exists()
            if not has_followup:
                return "followup"

        return None


@method_decorator(login_required, name="dispatch")
class DeleteAccountView(View):
    """
    Permanently deletes the user's account and all associated data.
    POST only. Requires the user to confirm by typing their username.

    What gets deleted (CASCADE):
    - All conversations and their messages
    - The user account itself

    What is kept with user FK set to NULL:
    - SafetyEvent records (audit trail preserved, user unlinked)
    - ImpactSurvey responses (anonymised research data, user unlinked)
    - UsageEvent records (anonymised aggregate data, user unlinked)

    Why permanent?
    GDPR Article 17 — right to erasure. When a user deletes their account,
    their data is gone. Not archived. Not recoverable.
    """
    template_name = "accounts/delete_account.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        confirmation = request.POST.get("confirmation", "").strip()
        if confirmation != request.user.username:
            return render(request, self.template_name, {
                "error": "The username you entered does not match. Your account was not deleted.",
            })

        # Save username before deletion — needed to clean up axes records after.
        username = request.user.username

        # Delete the user. CASCADE handles conversations and messages.
        # SafetyEvent.user is SET_NULL so audit records survive.
        request.user.delete()

        # Clean up axes login attempt records for this username.
        # Axes stores these by username string (no FK), so CASCADE does not reach them.
        from axes.models import AccessAttempt, AccessLog
        AccessAttempt.objects.filter(username=username).delete()
        AccessLog.objects.filter(username=username).delete()

        logout(request)
        return redirect("accounts:login")
