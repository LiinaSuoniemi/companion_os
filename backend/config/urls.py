"""
Companion OS — URL configuration.
Every request enters here. Routes are added as apps are built.
"""
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include


def home(request):
    # Home redirects to conversation list — the entry point to the product
    return redirect("chat:conversation_list")


urlpatterns = [
    # Django admin — for you to manage the app from a browser
    path("admin/", admin.site.urls),

    path("", home, name="home"),

    # Accounts — login, logout, register
    path("accounts/", include("apps.accounts.urls")),

    # Chat — the main product
    path("chat/", include("apps.chat.urls")),
]
