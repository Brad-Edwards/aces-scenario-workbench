"""Project-scoped authorization helpers.

Access is enforced server-side: a user only sees or acts on a project they are a
member of. Hiding navigation is never treated as authorization.
"""

from __future__ import annotations

from .models import Membership, Project


def user_membership(user, project: Project) -> Membership | None:
    if not user.is_authenticated:
        return None
    return Membership.objects.filter(project=project, user=user).first()


def user_role(user, project: Project) -> str | None:
    membership = user_membership(user, project)
    return membership.role if membership is not None else None


def is_member(user, project: Project) -> bool:
    return user_membership(user, project) is not None
