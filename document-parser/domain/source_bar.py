"""The whole document as one bar: every section, sized by its own text (#363).

The sources card draws it to show what an answer did not need. Each outline
section is one segment, as wide as the text it holds itself — its
`est_tokens` minus its published subsections' — so the segments add up to the
document once. A section a round read is lit; so are the subsections of a
section read whole, since reading a section reads what it contains.

Pure: it takes the flattened outline and the trail's marks, nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.navigation import OutlineNode

STATUS_UNREAD = "unread"
_INHERITED = "read"
_UNMARKED = {None, "path"}


@dataclass(frozen=True)
class SourceSegment:
    """One outline section on the bar."""

    ref: str
    title: str
    level: int
    tokens: int
    status: str
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)


def build_segments(
    flat: list[tuple[OutlineNode, list[str]]],
    status: dict[str, str],
    reached: dict[str, list[str]],
) -> list[SourceSegment]:
    """Every published section, in document order, with what happened to it."""
    segments: list[SourceSegment] = []
    for node, ancestors in flat:
        own = node.est_tokens - sum(child.est_tokens for child in node.children)
        state = status.get(node.ref)
        if state in _UNMARKED:
            read_above = any(reached.get(ancestor) for ancestor in ancestors)
            state = _INHERITED if read_above else STATUS_UNREAD
        segments.append(
            SourceSegment(
                ref=node.ref,
                title=node.title,
                level=node.level,
                tokens=max(0, own),
                status=state,
                page=node.page,
                hop_ids=list(reached.get(node.ref, [])),
            )
        )
    return segments
