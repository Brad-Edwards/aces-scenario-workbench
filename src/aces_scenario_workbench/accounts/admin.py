from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest

from .emails import send_invitation_email
from .forms import UserChangeForm, UserCreationForm
from .models import Invitation, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = User
    ordering = ("email",)
    list_display = ("email", "display_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("email", "display_name")
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("display_name",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {"classes": ("wide",), "fields": ("email", "display_name", "password1", "password2")},
        ),
    )


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "project", "role", "invited_by", "created_at", "accepted_at")
    list_filter = ("role", "project")
    search_fields = ("email", "project__name")
    readonly_fields = ("token", "created_at", "accepted_at")
    actions = ("resend_invitation_email",)

    def save_model(
        self, request: HttpRequest, obj: Invitation, form: ModelForm, change: bool
    ) -> None:
        if obj.invited_by_id is None:
            obj.invited_by = request.user
        super().save_model(request, obj, form, change)
        if not change:
            send_invitation_email(obj, request.build_absolute_uri("/"))

    @admin.action(description="Resend invitation email")
    def resend_invitation_email(self, request: HttpRequest, queryset: QuerySet[Invitation]) -> None:
        for invitation in queryset:
            send_invitation_email(invitation, request.build_absolute_uri("/"))
        self.message_user(request, "Invitation emails sent.")
