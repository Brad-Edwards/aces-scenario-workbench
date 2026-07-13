"""Email-based user model.

A custom user is defined from the first migration so identity is email-first and
future changes stay migration-safe.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from aces_scenario_workbench.workbench.models import Role

INVITATION_TTL_DAYS = 14


def _default_invitation_token() -> str:
    return secrets.token_urlsafe(32)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields) -> User:
        if not email:
            raise ValueError("Users must have an email address.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields) -> User:
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    is_staff = models.BooleanField(
        default=False,
        help_text="Whether the user can access the admin site.",
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    class Meta:
        ordering = ["email"]

    def __str__(self) -> str:
        return self.email

    def get_short_name(self) -> str:
        return self.display_name or self.email


class Invitation(models.Model):
    """A single-use, expiring invitation for a user to join a scenario."""

    email = models.EmailField()
    scenario = models.ForeignKey(
        "workbench.Scenario", on_delete=models.CASCADE, related_name="invitations"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.REVIEWER)
    token = models.CharField(max_length=64, unique=True, default=_default_invitation_token)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    created_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invitation for {self.email} to {self.scenario_id}"

    def is_expired(self) -> bool:
        return timezone.now() > self.created_at + timedelta(days=INVITATION_TTL_DAYS)

    def is_pending(self) -> bool:
        return self.accepted_at is None and not self.is_expired()

    def accept(self, user: User) -> None:
        from aces_scenario_workbench.workbench.models import Membership

        Membership.objects.get_or_create(
            scenario=self.scenario, user=user, defaults={"role": self.role}
        )
        self.accepted_at = timezone.now()
        self.save(update_fields=["accepted_at"])
