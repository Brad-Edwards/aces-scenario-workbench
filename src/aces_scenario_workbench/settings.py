"""Django settings for the ACES Scenario Workbench.

All deployment-specific values are read from the environment so the same code
runs unchanged locally (SQLite, zero config) and in a hosted deployment
(PostgreSQL via ``DATABASE_URL``).
"""

from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


# A stable key must be provided in any non-local deployment; the random fallback
# keeps local use zero-config without committing a secret.
SECRET_KEY = os.environ.get("ACES_WORKBENCH_SECRET_KEY") or get_random_secret_key()

DEBUG = _env_bool("ACES_WORKBENCH_DEBUG", False)

ALLOWED_HOSTS = _env_list("ACES_WORKBENCH_ALLOWED_HOSTS", "localhost,127.0.0.1,[::1]")

CSRF_TRUSTED_ORIGINS = _env_list("ACES_WORKBENCH_CSRF_TRUSTED_ORIGINS", "")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "aces_scenario_workbench.accounts",
    "aces_scenario_workbench.workbench",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aces_scenario_workbench.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aces_scenario_workbench.wsgi.application"
ASGI_APPLICATION = "aces_scenario_workbench.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=f"sqlite:///{os.environ.get('ACES_WORKBENCH_DB_PATH', 'db.sqlite3')}",
        conn_max_age=600,
    ),
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Serve static assets from app/finder locations so the app runs without a
# separate collectstatic step in local and development use.
WHITENOISE_USE_FINDERS = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "landing"

# Baseline security posture. Cookie/redirect hardening defaults follow DEBUG and
# can be overridden per deployment.
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _env_bool("ACES_WORKBENCH_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("ACES_WORKBENCH_SECURE_COOKIES", not DEBUG)
SECURE_SSL_REDIRECT = _env_bool("ACES_WORKBENCH_SSL_REDIRECT", False)
SECURE_HSTS_SECONDS = int(os.environ.get("ACES_WORKBENCH_HSTS_SECONDS", "0"))
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
