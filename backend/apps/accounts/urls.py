"""
Accounts app — URL routes.

Three routes:
- login/   → Django's built-in LoginView (we just give it a template)
- logout/  → Django's built-in LogoutView (redirects to login)
- register/ → our own RegisterView (Django has no built-in register)

Why use Django's built-in views for login/logout?
They handle: wrong password logic, session creation, CSRF protection, brute-force
rate limiting hooks. Writing this from scratch would be reinventing a well-tested wheel.
"""
from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="accounts/login.html"),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="accounts:login"),
        name="logout",
    ),
    path(
        "register/",
        views.RegisterView.as_view(),
        name="register",
    ),
    path(
        "delete-account/",
        views.DeleteAccountView.as_view(),
        name="delete_account",
    ),
]
