"""The sources card's wire contract — what `show_sources` returns (#363).

A published contract, like `wire.py`: the SDK derives the tool's JSON output
schema from these dataclasses, so a rename here is a breaking change for every
connected agent. The boxes travel as fractions of the page, so the card lays
them over a page raster of any size.

Kept apart from the mapping that fills them (`sources_mapping.py`) and the
text a host without a UI reads (`sources_text.py`), as `wire.py` is from
`wire_mapping.py`.

The card calls a round of the loop a *hop* (`hops`, `hop_id`, `hop_ids`,
`SourceHopOut`); the domain says round (`domain.source_map.SourceRound`).
The wire keeps its names, class names included since they title the output
schema, until the contract is versioned. The class docstrings are published
too, as the schema's descriptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RegionOut:
    """A block of a page: `box` is `[left, top, right, bottom]`, fractions of
    the page from its top-left corner."""

    page: int
    box: list[float]


@dataclass(frozen=True)
class PassageOut:
    """One cited passage. `status` is the server's word on `quote` (a
    `verify_citation` status), absent when no quote came with the anchor.
    `marks` are the lines the quote covers, found in the PDF's text layer;
    `regions` the blocks of its element, drawn when `marks` is empty."""

    uri: str
    ref: str
    quote: str
    status: str | None
    regions: list[RegionOut]
    hop_id: str | None = None
    page: int | None = None
    deep_link: str | None = None
    section: str = ""
    marks: list[RegionOut] = field(default_factory=list)


@dataclass(frozen=True)
class SourceHopOut:
    hop_id: str
    ordinal: int
    ref: str
    uri: str
    title: str
    why: str
    est_tokens: int
    found: str = ""
    node_ref: str | None = None
    page: int | None = None
    cited: list[str] = field(default_factory=list)
    deep_link: str | None = None
    regions: list[RegionOut] = field(default_factory=list)


@dataclass(frozen=True)
class SourceNodeOut:
    ref: str
    uri: str
    title: str
    kind: str
    level: int
    status: str
    est_tokens: int = 0
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)
    deep_link: str | None = None


@dataclass(frozen=True)
class SourceSegmentOut:
    ref: str
    title: str
    level: int
    tokens: int
    status: str
    page: int | None = None
    hop_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceTotalsOut:
    mode: str
    rounds: int
    max_rounds: int
    over_cap: bool
    sections_read: int
    sections_total: int
    tokens_read: int
    tokens_total: int
    percent: float


@dataclass(frozen=True)
class SourcesCard:
    """Where an answer came from, for the card and for a host without one.

    `hops` is the reading order — one per round of the loop, each with its
    `why`, what it `found` and where it sits on its pages — `passages` the
    quotes cited, `map` the same reads placed on the outline (status `cited`,
    `read`, or `path` for an ancestor), `summary` the one line a reader
    quotes. `unknown` lists every anchor that resolved to nothing — shown,
    never silently dropped.
    """

    document_id: str
    version_id: str
    filename: str
    question: str
    summary: str
    totals: SourceTotalsOut
    hops: list[SourceHopOut]
    map: list[SourceNodeOut]
    segments: list[SourceSegmentOut] = field(default_factory=list)
    passages: list[PassageOut] = field(default_factory=list)
    page_count: int | None = None
    unknown: list[str] = field(default_factory=list)
    next_step: str = ""
    # The document's title as the parse found it, else its filename.
    title: str = ""
