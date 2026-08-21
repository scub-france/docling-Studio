"""Test helpers for the typed `AppState` container (#306 review).

The API layer resolves its services from `app.state.container`, so tests wire
or swap a whole container rather than poking individual `app.state`
attributes. Kept out of `conftest.py` because the backend already has a
root-level `conftest` that shadows the package one on import.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace

from api.state import AppState


def wire_state(app, **fields) -> None:
    """Publish a container carrying only `fields` — for the standalone
    single-router apps tests build; every other slot stays None."""
    app.state.container = AppState(**fields)


@contextmanager
def state_override(app, **fields):
    """Temporarily publish a container with `fields` applied, then restore.

    Restoring on exit keeps tests that share the module-level `main.app`
    isolated from one another.
    """
    original = getattr(app.state, "container", AppState())
    app.state.container = replace(original, **fields)
    try:
        yield
    finally:
        app.state.container = original
