from __future__ import annotations

from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "display_name")
    ordering = ("email",)
