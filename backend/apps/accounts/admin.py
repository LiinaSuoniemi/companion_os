"""
Accounts app — Admin configuration.

Registers InviteCode in Django admin so you can generate and manage
invite codes from the admin panel on your phone.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import InviteCode, ImpactSurvey, PilotApplication, User


@admin.register(User)
class CompanionUserAdmin(UserAdmin):
    list_display = ("username", "language_preference", "is_age_verified", "created_at")


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "max_uses", "times_used", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("code", "label")
    readonly_fields = ("times_used", "created_at")


@admin.register(ImpactSurvey)
class ImpactSurveyAdmin(admin.ModelAdmin):
    list_display = ("user", "survey_type", "handle_difficult_moments", "notice_stress_building", "have_something_to_try", "get_through_daily_tasks", "created_at")
    list_filter = ("survey_type",)
    readonly_fields = ("created_at",)


@admin.register(PilotApplication)
class PilotApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email")
    readonly_fields = ("created_at",)
