"""Project-scoped authorization helpers.

Access is enforced server-side: a user only sees or acts on a project they are a
member of. Hiding navigation is never treated as authorization.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import Membership, Project, Role

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

    UserOrAnon = AbstractBaseUser | AnonymousUser

CONTRIBUTOR_ROLES = frozenset({Role.AUTHOR, Role.REVIEWER, Role.ADMINISTRATOR})


def user_membership(user: UserOrAnon, project: Project) -> Membership | None:
    if not user.is_authenticated:
        return None
    return Membership.objects.filter(project=project, user=user).first()


def user_role(user: UserOrAnon, project: Project) -> str | None:
    membership = user_membership(user, project)
    return membership.role if membership is not None else None


def is_member(user: UserOrAnon, project: Project) -> bool:
    return user_membership(user, project) is not None


def can_contribute(user: UserOrAnon, project: Project) -> bool:
    """Whether the user may comment, set review state, or record decisions."""
    return user_role(user, project) in CONTRIBUTOR_ROLES
