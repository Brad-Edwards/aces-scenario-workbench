from __future__ import annotations

from django.contrib import admin

from .models import Invitation, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "display_name")
    ordering = ("email",)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "project", "role", "invited_by", "created_at", "accepted_at")
    list_filter = ("role", "project")
    search_fields = ("email", "project__name")
    readonly_fields = ("token", "created_at", "accepted_at")
