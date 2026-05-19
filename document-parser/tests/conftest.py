"""Shared pytest fixtures for the backend test suite.

Currently centralises one cross-cutting concern: the in-memory rate
limiter (`infra.rate_limiter.RateLimiterMiddleware`) is wired at
module load (`main.py`) with `RATE_LIMIT_RPM=100`, and its `_buckets`
dict is shared across every test that uses `TestClient(app, ...)`.
Once the suite drives more than 100 HTTP calls in a minute (which a
moderately large suite does easily), later tests hit 429 in random
places — looks like a real failure but is just test crosstalk.

The autouse fixture below flushes the middleware's buckets before
every test, so each test starts with a fresh quota.
"""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limiter_buckets() -> None:
    """Clear the rate-limiter middleware buckets between tests.

    No-op if the middleware isn't wired (e.g. modules that don't
    import `main` at all). Reaches into FastAPI's middleware stack
    by class match — the rate limiter is added once at startup, so
    only one entry matches.
    """
    try:
        from infra.rate_limiter import RateLimiterMiddleware
        from main import app
    except Exception:
        return

    for middleware in app.user_middleware:
        if middleware.cls is RateLimiterMiddleware:
            # The instance is built inside Starlette's middleware
            # stack on first request, so we patch the kwargs that
            # become its constructor arg. The `_buckets` dict is
            # owned by the instance — but the instance is recreated
            # per `Starlette.middleware_stack`, which is rebuilt
            # lazily. Easier path: clear any cached middleware stack
            # so the next request rebuilds a fresh middleware chain
            # with empty buckets.
            app.middleware_stack = None
            break
