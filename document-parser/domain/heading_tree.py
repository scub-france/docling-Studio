"""Nesting items under headings: the one walk every outline view shares.

Items are walked in reading order with a stack of open headings. A heading
first closes every open heading at its level or deeper, then opens its own
section; any other item belongs to the deepest open heading. Level jumps
nest (an H3 right after an H1 sits under the H1), and items before the first
heading sit at the root.

What counts as a heading and the level it gets are the caller's choice,
through `level_of`: the outline, the parse index, the chunk tree and the
editor tree each read them their own way, on purpose. An empty stack is the
root; the views that used a sentinel level -1 for it behave the same, since
no heading level is below 0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


@dataclass(frozen=True)
class NestStep:
    """Where one item sits. Items are named by their position in the walk.

    `ancestors` are the open headings above the item, outermost first, after
    it closed what it closes; `parent` is the last of them, None at the root.
    `closed` lists the headings the item closed, innermost first.
    """

    position: int
    level: int | None
    opened: bool
    parent: int | None
    ancestors: tuple[int, ...]
    closed: tuple[int, ...]


@dataclass(frozen=True)
class HeadingNesting:
    """Every item's step, and the headings still open after the last item
    (outermost first)."""

    steps: tuple[NestStep, ...]
    still_open: tuple[int, ...]


def nest_by_heading[T](
    items: Iterable[T],
    *,
    level_of: Callable[[T], int | None],
    may_open: Callable[[tuple[int, ...]], bool] | None = None,
) -> HeadingNesting:
    """Walk `items` in order and say where each one nests.

    `level_of` returns an item's heading level, or None when it is not a
    heading. `may_open`, when given, receives the levels of the open
    headings (outermost first) once a heading has closed what it closes, and
    decides whether that heading opens a section; a heading it refuses
    still closes, but nothing nests under it.
    """
    stack: list[tuple[int, int]] = []  # (level, position)
    steps: list[NestStep] = []
    for position, item in enumerate(items):
        level = level_of(item)
        closed: list[int] = []
        opened = False
        if level is not None:
            while stack and stack[-1][0] >= level:
                closed.append(stack.pop()[1])
            opened = may_open is None or may_open(tuple(open_level for open_level, _ in stack))
        ancestors = tuple(open_position for _, open_position in stack)
        steps.append(
            NestStep(
                position=position,
                level=level,
                opened=opened,
                parent=ancestors[-1] if ancestors else None,
                ancestors=ancestors,
                closed=tuple(closed),
            )
        )
        if opened:
            stack.append((level, position))
    return HeadingNesting(
        steps=tuple(steps),
        still_open=tuple(open_position for _, open_position in stack),
    )
