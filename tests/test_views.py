from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

User = get_user_model()


def test_healthz_ok():
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_landing_redirects_anonymous_to_login():
    response = Client().get(reverse("landing"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_landing_redirects_authenticated_to_app(db):
    client = Client()
    user = User.objects.create_user(email="member@example.com", password="review-pass-42x")
    client.force_login(user)

    response = client.get(reverse("landing"))

    assert response.status_code == 302
    assert response.url == reverse("spa-app")


def test_spa_requires_login():
    response = Client().get(reverse("spa-app"))
    assert response.status_code == 302
    assert reverse("login") in response.url


def test_spa_renders_standalone_assets(db):
    client = Client()
    user = User.objects.create_user(email="member@example.com", password="review-pass-42x")
    client.force_login(user)

    response = client.get(reverse("spa-app"))

    assert response.status_code == 200
    assert b"workbench/spa/app.css" in response.content
    assert b"workbench/spa/app.js" in response.content
    assert b"data-theme-toggle" not in response.content
    assert b"data-cookie-notice" not in response.content
