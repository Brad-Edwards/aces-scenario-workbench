"""Scenario-scoped authorization helpers.

Access is enforced server-side: a user only sees or acts on a scenario they are
a member of. Hiding navigation is never treated as authorization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Membership, Role, Scenario

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    UserOrAnon = AbstractBaseUser | AnonymousUser

CONTRIBUTOR_ROLES = frozenset({Role.AUTHOR, Role.REVIEWER, Role.ADMINISTRATOR})


def user_membership(user: UserOrAnon, scenario: Scenario) -> Membership | None:
    if not user.is_authenticated:
        return None
    return Membership.objects.filter(scenario=scenario, user=user).first()


def user_role(user: UserOrAnon, scenario: Scenario) -> str | None:
    membership = user_membership(user, scenario)
    return membership.role if membership is not None else None


def is_member(user: UserOrAnon, scenario: Scenario) -> bool:
    return user_membership(user, scenario) is not None


def can_contribute(user: UserOrAnon, scenario: Scenario) -> bool:
    """Whether the user may comment, set review state, or record decisions."""
    return user_role(user, scenario) in CONTRIBUTOR_ROLES
