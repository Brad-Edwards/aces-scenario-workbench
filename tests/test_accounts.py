from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_create_user_defaults():
    user = User.objects.create_user(email="author@example.com", password="review-pass-1")
    assert user.email == "author@example.com"
    assert user.is_active is True
    assert user.is_staff is False
    assert user.is_superuser is False
    assert str(user) == "author@example.com"


@pytest.mark.django_db
def test_create_superuser():
    admin = User.objects.create_superuser(email="admin@example.com", password="review-pass-1")
    assert admin.is_staff is True
    assert admin.is_superuser is True


@pytest.mark.django_db
def test_create_user_requires_email():
    with pytest.raises(ValueError, match="email"):
        User.objects.create_user(email="", password="review-pass-1")


@pytest.mark.django_db
def test_create_superuser_requires_staff_flag():
    with pytest.raises(ValueError, match="is_staff"):
        User.objects.create_superuser(
            email="admin@example.com", password="review-pass-1", is_staff=False
        )


@pytest.mark.django_db
def test_create_superuser_requires_superuser_flag():
    with pytest.raises(ValueError, match="is_superuser"):
        User.objects.create_superuser(
            email="admin@example.com", password="review-pass-1", is_superuser=False
        )


@pytest.mark.django_db
def test_short_name_prefers_display_name():
    user = User.objects.create_user(
        email="author@example.com", password="review-pass-1", display_name="Author One"
    )
    assert user.get_short_name() == "Author One"
