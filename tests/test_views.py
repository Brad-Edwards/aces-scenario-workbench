from __future__ import annotations

from django.test import Client
from django.urls import reverse


def test_healthz_ok():
    response = Client().get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_landing_renders():
    response = Client().get(reverse("landing"))
    assert response.status_code == 200
    assert b"ACES Scenario Workbench" in response.content
    assert reverse("login").encode() in response.content
    assert b"Administration" not in response.content
