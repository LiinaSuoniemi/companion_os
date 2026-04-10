"""
Companion OS — URL configuration.
Every request enters here. Routes are added as apps are built.
"""
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    # Django admin — for you to manage the app from a browser
    path("admin/", admin.site.urls),

    # App routes — uncomment as each app is built
    # path("accounts/", include("apps.accounts.urls")),
    # path("chat/", include("apps.chat.urls")),
]
