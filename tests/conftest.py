from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _relax_ssl_redirect(settings):
    """Outside DEBUG the app enforces an HTTPS redirect (DEBUG is off under the
    test runner); disable it so the test client can exercise views over HTTP."""
    settings.SECURE_SSL_REDIRECT = False


@pytest.fixture(autouse=True)
def _isolate_rate_limit_cache():
    """Rate limits are cache-backed; clear counters between tests so one test's
    requests cannot exhaust another test's limit."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
