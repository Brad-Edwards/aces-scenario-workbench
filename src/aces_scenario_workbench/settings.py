"""Django settings for the ACES Scenario Workbench.

All deployment-specific values are read from the environment so the same code
runs unchanged locally (SQLite, zero config) and in a hosted deployment
(PostgreSQL via ``DATABASE_URL``).
"""

from __future__ import annotations

import os
from pathlib import Path

import dj_database_url
import django_cache_url
from csp.constants import NONCE, SELF
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _env_list(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.environ.get(name, default).split(",") if item.strip()]


def _env_relative_path(name: str, default: str) -> str:
    value = os.environ.get(name, default).strip().strip("/")
    if (
        not value
        or value.startswith(("http:", "https:"))
        or "\\" in value
        or "?" in value
        or "#" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise ImproperlyConfigured(f"{name} must be a relative URL path such as 'control'.")
    return f"{value}/"


# A stable key must be provided in any non-local deployment; the random fallback
# keeps local use zero-config without committing a secret.
SECRET_KEY = os.environ.get("ACES_WORKBENCH_SECRET_KEY") or get_random_secret_key()
# True when no stable key was supplied (sessions reset on restart) — surfaced by
# `aces-workbench doctor`.
SECRET_KEY_IS_EPHEMERAL = "ACES_WORKBENCH_SECRET_KEY" not in os.environ

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
    "axes",
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
    "csp.middleware.CSPMiddleware",
    "django_ratelimit.middleware.RatelimitMiddleware",
    # AxesMiddleware must be last so it can convert lockouts into responses.
    "axes.middleware.AxesMiddleware",
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

# Cache backend, used by the request rate limiter. The in-memory default needs no
# setup and is correct for a single worker; point ACES_WORKBENCH_CACHE_URL at a
# shared cache (e.g. redis://…) so limits hold across multiple worker processes.
CACHES = {
    "default": django_cache_url.config(
        env="ACES_WORKBENCH_CACHE_URL", default="locmem://aces-workbench"
    )
}

AUTH_USER_MODEL = "accounts.User"

# django-axes brute-force protection sits in front of the model backend. Its
# database handler records attempts in the database, so lockouts are consistent
# across worker processes without a shared cache.
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

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

ADMIN_PATH = _env_relative_path("ACES_WORKBENCH_ADMIN_PATH", "control")

# Email. The console backend (prints messages) is the default so local use needs
# no mail server; set the SMTP host to deliver for real. Credentials are read
# from the environment, never source.
EMAIL_HOST = os.environ.get("ACES_WORKBENCH_EMAIL_HOST", "")
if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_PORT = int(os.environ.get("ACES_WORKBENCH_EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("ACES_WORKBENCH_EMAIL_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("ACES_WORKBENCH_EMAIL_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("ACES_WORKBENCH_EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = os.environ.get("ACES_WORKBENCH_DEFAULT_FROM_EMAIL", "aces-workbench@localhost")

# Baseline security posture. Cookie/redirect hardening defaults follow DEBUG and
# can be overridden per deployment.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = _env_bool("ACES_WORKBENCH_SECURE_COOKIES", not DEBUG)
CSRF_COOKIE_SECURE = _env_bool("ACES_WORKBENCH_SECURE_COOKIES", not DEBUG)
# HTTPS enforcement is on by default outside DEBUG. The proxy header lets the app
# recognise TLS terminated upstream, so the redirect does not loop behind a
# correctly configured reverse proxy. Each value stays overridable per deployment.
SECURE_SSL_REDIRECT = _env_bool("ACES_WORKBENCH_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = _env_int("ACES_WORKBENCH_HSTS_SECONDS", 0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("ACES_WORKBENCH_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = _env_bool("ACES_WORKBENCH_HSTS_PRELOAD", False)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Brute-force protection for authentication (django-axes). Failures are counted
# per client IP address, so repeated password attempts from one source are locked
# out after the limit for the cool-off window, and the counter clears on success.
AXES_FAILURE_LIMIT = _env_int("ACES_WORKBENCH_AXES_FAILURE_LIMIT", 5)
AXES_COOLOFF_TIME = _env_int("ACES_WORKBENCH_AXES_COOLOFF_HOURS", 1)
AXES_LOCKOUT_PARAMETERS = ["ip_address"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "429.html"

# Rate limiting (django-ratelimit) for unauthenticated abuse-prone endpoints.
# Exceeding a limit raises Ratelimited, which RatelimitMiddleware renders here.
RATELIMIT_VIEW = "aces_scenario_workbench.workbench.views.ratelimited"

# Content Security Policy. Scripts are restricted to same-origin plus a per-request
# nonce (the one inline script carries {{ request.csp_nonce }}); there is no
# unsafe-inline. The Django admin ships inline scripts it does not nonce, so it is
# excluded from the policy — keep the admin access-restricted in any deployment.
CONTENT_SECURITY_POLICY = {
    "EXCLUDE_URL_PREFIXES": (f"/{ADMIN_PATH}",),
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF, NONCE],
        "style-src": [SELF],
        "img-src": [SELF, "data:"],
        "font-src": [SELF],
        "connect-src": [SELF],
        "form-action": [SELF],
        "frame-ancestors": ["'none'"],
        "base-uri": [SELF],
        "object-src": ["'none'"],
    },
}
