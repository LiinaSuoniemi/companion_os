"""
Companion OS — URL configuration.
Every request enters here. Routes are added as apps are built.
"""
from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path, include
from two_factor.admin import AdminSiteOTPRequired
from two_factor.urls import urlpatterns as tf_urls
from apps.accounts.views import _get_lang

# Require TOTP for every admin login. Anyone who reaches /admin/ must
# have a verified OTP device. Set up a device first via /account/two_factor/setup/
# while logged in as a regular user, then /admin/ will accept the TOTP code.
admin.site.__class__ = AdminSiteOTPRequired


def home(request):
    if request.user.is_authenticated:
        return redirect("chat:conversation_list")
    return render(request, "landing.html", {"lang": _get_lang(request)})


urlpatterns = [
    # Django admin — protected by TOTP via AdminSiteOTPRequired above
    path("admin/", admin.site.urls),

    # Two-factor auth — login and TOTP device setup/management pages.
    # Sits at /account/ (singular) — does not conflict with /accounts/ (plural).
    # Liina must visit /account/two_factor/setup/ to register her TOTP device
    # before the admin will accept her login.
    path("", include(tf_urls)),

    path("", home, name="home"),
    path("privacy/", lambda request: render(request, "privacy.html"), name="privacy"),

    # Accounts — login, logout, register
    path("accounts/", include("apps.accounts.urls")),

    # Chat — the main product
    path("chat/", include("apps.chat.urls")),
]
