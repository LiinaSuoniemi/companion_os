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
from .models import ImpactSurvey, PartnershipInquiry, PilotApplication


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
            login(request, user)
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

        survey = ImpactSurvey(
            user=request.user,
            survey_type=survey_type,
            handle_difficult_moments=int(request.POST.get("q1", 3)),
            notice_stress_building=int(request.POST.get("q2", 3)),
            have_something_to_try=int(request.POST.get("q3", 3)),
            get_through_daily_tasks=int(request.POST.get("q4", 3)),
            age_range=request.POST.get("age_range", ""),
            situation=situation,
            country=request.POST.get("country_other", "").strip() or request.POST.get("country", ""),
            what_brought_you=request.POST.get("what_brought_you", ""),
        )

        if survey_type == "followup":
            survey.feel_more_grounded = int(request.POST.get("q5", 3))
            survey.what_changed = request.POST.get("what_changed", "")

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


class PilotApplicationView(View):
    def post(self, request):
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        what_brings_you = request.POST.get("what_brings_you", "").strip()

        if not name or not email or not what_brings_you:
            return render(request, "landing.html", {"error": "Please fill in all fields.", "scroll_to_form": True})

        if PilotApplication.objects.filter(email=email).exists():
            return render(request, "landing.html", {"error": "This email has already applied. I'll be in touch.", "scroll_to_form": True})

        PilotApplication.objects.create(name=name, email=email, what_brings_you=what_brings_you)
        return render(request, "landing.html", {"success": True})


class PartnershipInquiryView(View):
    """
    B2B partnership inquiries from organizations.

    GET  → show the partnership inquiry page with form
    POST → validate, save inquiry, show confirmation

    For organizations interested in offering Companion OS to the people
    they already serve. Different from PilotApplication (individuals).
    """

    template_name = "accounts/partnership.html"

    def get(self, request):
        return render(request, self.template_name, {})

    def post(self, request):
        organization_name = request.POST.get("organization_name", "").strip()
        contact_person = request.POST.get("contact_person", "").strip()
        role = request.POST.get("role", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        organization_type = request.POST.get("organization_type", "other").strip()
        country = request.POST.get("country", "fi").strip()
        target_population = request.POST.get("target_population", "").strip()
        what_brings_you = request.POST.get("what_brings_you", "").strip()

        # Required fields validation
        if not organization_name or not contact_person or not email or not what_brings_you:
            return render(
                request,
                self.template_name,
                {
                    "error": "Please fill in the required fields (organization, contact person, email, and what brings you).",
                    "form_data": {
                        "organization_name": organization_name,
                        "contact_person": contact_person,
                        "role": role,
                        "email": email,
                        "phone": phone,
                        "organization_type": organization_type,
                        "country": country,
                        "target_population": target_population,
                        "what_brings_you": what_brings_you,
                    },
                },
            )

        # Validate organization_type and country are in choices (defensive — strict
        # against POST tampering even though the form has a select element).
        valid_org_types = {choice[0] for choice in PartnershipInquiry.ORG_TYPE_CHOICES}
        valid_countries = {choice[0] for choice in PartnershipInquiry.COUNTRY_CHOICES}
        if organization_type not in valid_org_types:
            organization_type = "other"
        if country not in valid_countries:
            country = "other"

        PartnershipInquiry.objects.create(
            organization_name=organization_name,
            contact_person=contact_person,
            role=role,
            email=email,
            phone=phone,
            organization_type=organization_type,
            country=country,
            target_population=target_population,
            what_brings_you=what_brings_you,
        )
        return render(request, self.template_name, {"success": True})


@method_decorator(login_required, name="dispatch")
class DeleteAccountView(View):
    """
    Permanently deletes the user's account and all associated data.
    POST only. Requires the user to confirm by typing their username.

    What gets deleted (CASCADE):
    - All conversations and their messages
    - SafetyEvent records: user FK set to NULL (audit trail preserved, user unlinked)
    - The user account itself

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

        # Delete the user. CASCADE handles conversations and messages.
        # SafetyEvent.user is SET_NULL so audit records survive.
        request.user.delete()
        logout(request)
        return redirect("accounts:login")
