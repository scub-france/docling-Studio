"""Composition root — builds the application's typed state container.

`AppStateBuilder` is the entry point (`main.lifespan`); the factories are
re-exported because the wiring tests patch settings and assert on the adapter
each engine selects.
"""

from bootstrap.builder import AppStateBuilder
from bootstrap.factories import (
    build_chunker,
    build_converter,
    build_reasoning_runner,
    env_reasoning_config,
)

__all__ = [
    "AppStateBuilder",
    "build_chunker",
    "build_converter",
    "build_reasoning_runner",
    "env_reasoning_config",
]
