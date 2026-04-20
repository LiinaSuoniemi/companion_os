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
            return redirect("home")
        # Form invalid — re-render with error messages attached to the form
        return render(request, self.template_name, {"form": form})


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
