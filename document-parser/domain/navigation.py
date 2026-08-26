"""Navigation & citation value objects — the agent-facing contract.

Introduced by the MCP document server (lot 1). Everything here is pure data:
no I/O, no framework, no docling import. The projections that produce these
types live in `domain.navigation_builder`; the orchestration lives in
`services.navigation_service`.

The anchor grammar is the load-bearing piece::

    dstudio://doc/{document_id}@{version_id}#{ref}
    dstudio://doc/8f2a91c4@a71f0c33#/texts/91

- `document_id` — `Document.id`.
- `version_id`  — an **opaque** version token. Today it is the id of the
  analysis run that produced the tree, because a docling `self_ref` is stable
  *inside* one parse and meaningless across two: re-parsing the same PDF
  renumbers `#/texts/91`. Pinning the version is what keeps a citation true
  after a re-parse instead of silently pointing at another paragraph.
- `ref` — the docling `self_ref`, verbatim (`#/texts/91`, `#/tables/3`), or
  one of the virtual page refs (`#/pages/7`) the navigator synthesises for
  documents without section headings.

An agent never builds an anchor by hand: every read returns the anchors of
what it just read. `NavigationService.verify_citation` re-resolves an anchor
server-side and compares the quote, so a fabricated or drifted citation is
detectable rather than merely implausible.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from enum import StrEnum

# `dstudio://doc/<id>@<version>#<ref>` — ids are uuid4 strings today, but the
# grammar only forbids the separators themselves so opaque ids stay opaque.
_URI_RE = re.compile(r"^dstudio://doc/(?P<doc>[^@/#]+)@(?P<version>[^@/#]+)(?P<ref>#.+)$")

URI_SCHEME = "dstudio"


class AnchorParseError(ValueError):
    """Raised when a string is not a well-formed `dstudio://` anchor."""


@dataclass(frozen=True)
class DocumentAnchor:
    """A resolvable pointer to one element of one parse of one document."""

    document_id: str
    version_id: str
    ref: str

    @property
    def uri(self) -> str:
        return f"{URI_SCHEME}://doc/{self.document_id}@{self.version_id}{self.ref}"

    @classmethod
    def parse(cls, uri: str) -> DocumentAnchor:
        """Parse a `dstudio://` anchor.

        Raises:
            AnchorParseError: on any malformed input. The message is written
                for an LLM reader — it states the expected shape.
        """
        match = _URI_RE.match((uri or "").strip())
        if match is None:
            raise AnchorParseError(
                f"Malformed anchor {uri!r}. Expected "
                "'dstudio://doc/{document_id}@{version_id}#{self_ref}', "
                "for example 'dstudio://doc/8f2a91c4@a71f0c33#/texts/91'. "
                "Anchors are returned by get_outline and read_element — never build one by hand."
            )
        return cls(
            document_id=match.group("doc"),
            version_id=match.group("version"),
            ref=match.group("ref"),
        )


def quote_hash(text: str) -> str:
    """Return the `sha256:…` digest that binds a quote to a version.

    Computed on the *normalised* text (see `normalise_quote`) so that a quote
    round-tripped through an LLM — which reflows whitespace — still verifies.
    """
    digest = hashlib.sha256(normalise_quote(text).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def normalise_quote(text: str) -> str:
    """Collapse whitespace runs and strip — the comparison form for quotes.

    Verification must survive the trip through a model: line wrapping, a
    trailing newline or a non-breaking space are not textual drift. Anything
    else (a changed word, a dropped clause) is.
    """
    # The wire defuses `</document-content>` to `<\\/document-content>` before
    # handing document text to a model, so a quote coming back carries the
    # escaped form. Undo it here: an escape we applied ourselves is not drift.
    text = (text or "").replace("<\\/", "</")
    # `\s` also matches NBSP and friends in Unicode mode, so one pass is enough.
    return re.sub(r"\s+", " ", text).strip()


class CitationStatus(StrEnum):
    """Outcome of `verify_citation` — the enum the wire contract publishes.

    - VERIFIED       the quote appears in the cited element (or, for a section
                     anchor, in one of the elements it covers)
    - QUOTE_DRIFT    the anchor resolves but the quote is not in its text
    - UNKNOWN_REF    the ref does not exist in that parse
    - UNKNOWN_VERSION the version token names no parse of that document
    - STALE_VERSION  the quote checks out, but the anchor pins a parse that
                     has since been superseded by a newer analysis
    """

    VERIFIED = "verified"
    QUOTE_DRIFT = "quote_drift"
    UNKNOWN_REF = "unknown_ref"
    UNKNOWN_VERSION = "unknown_version"
    STALE_VERSION = "stale_version"


@dataclass(frozen=True)
class BoundingBox:
    """One element's rectangle on one page, in the parse's own coordinates.

    `coord_origin` is load-bearing and must be read before the numbers are:
    docling emits BOTTOMLEFT for PDF-native parses, where `top` is
    numerically **greater** than `bottom` (see `infra/bbox.py` and
    `docs/bbox-pipeline.md`), and TOPLEFT elsewhere, where it is smaller.
    The values are passed through unconverted — converting them here would
    silently lose the information a consumer needs to overlay them.

    `page_width` / `page_height` are the page's own dimensions when the parse
    records them, so a consumer can flip the origin without a second call.
    """

    page: int
    left: float
    top: float
    right: float
    bottom: float
    coord_origin: str = "TOPLEFT"
    page_width: float | None = None
    page_height: float | None = None

    def pixel_box(self, *, dpi: int = 150, padding: int = 8) -> tuple[int, int, int, int]:
        """Project the box onto a page rendered at `dpi`, origin-normalised.

        Docling reports points (1/72 inch) from whichever corner the parse
        used; a raster crop needs pixels from the top-left. The `page_height`
        flip is what turns a BOTTOMLEFT box into one, and the final swap
        catches a box whose corners are inverted for any other reason — a
        crop with a negative height would raise deep inside the imaging
        library instead of just being wrong.
        """
        scale = dpi / 72.0
        left, right = self.left * scale, self.right * scale
        if self.coord_origin.upper() == "BOTTOMLEFT" and self.page_height:
            top = (self.page_height - self.top) * scale
            bottom = (self.page_height - self.bottom) * scale
        else:
            top, bottom = self.top * scale, self.bottom * scale
        if top > bottom:
            top, bottom = bottom, top
        if left > right:
            left, right = right, left
        return (
            max(0, int(left - padding)),
            max(0, int(top - padding)),
            int(right + padding),
            int(bottom + padding),
        )


@dataclass(frozen=True)
class Citation:
    """A verifiable pointer to a passage: anchor + verbatim + provenance."""

    uri: str
    document_id: str
    version_id: str
    ref: str
    label: str
    quote: str
    quote_hash: str
    page: int | None = None
    bbox: BoundingBox | None = None
    headings: list[str] = field(default_factory=list)
    deep_link: str | None = None


@dataclass(frozen=True)
class CitationCheck:
    """Result of re-resolving an anchor and comparing the claimed quote."""

    valid: bool
    status: CitationStatus
    detail: str
    citation: Citation | None = None
    actual_quote: str | None = None


@dataclass(frozen=True)
class DocumentSummary:
    """One row of `find_documents` — enough to pick a document, nothing more."""

    document_id: str
    filename: str
    lifecycle_state: str
    page_count: int | None = None
    version_id: str | None = None
    created_at: str | None = None


@dataclass(frozen=True)
class DocumentSearch:
    """What `find_documents` answers.

    `scanned` / `scan_limit` are part of the answer, not diagnostics: the
    filter runs over the most recent `scan_limit` documents, so an empty
    `documents` list with `truncated=True` means "not in the window I looked
    at", which is a different fact from "no such document".
    """

    documents: list[DocumentSummary]
    scanned: int
    scan_limit: int
    truncated: bool


@dataclass(frozen=True)
class CitationImage:
    """A raster crop of the page region a citation points at.

    `png` is the image itself; `data_uri` is what an HTML view embeds. Kept
    together so a caller never has to re-derive one from the other.
    """

    png: bytes
    data_uri: str
    width: int
    height: int
    page: int
    dpi: int


@dataclass(frozen=True)
class OutlineNode:
    """One entry of the document map.

    `est_tokens` is what makes the outline actionable: the agent decides what
    to read *before* paying for it. It counts the section's own text plus
    everything under it, including deeper levels the outline itself elided.
    """

    ref: str
    uri: str
    title: str
    kind: str  # "section" | "page"
    level: int
    page: int | None = None
    est_tokens: int = 0
    child_count: int = 0
    children: list[OutlineNode] = field(default_factory=list)


@dataclass(frozen=True)
class DocumentOutline:
    """The map. Two truncations are reported apart because they recover
    differently: `depth_limited` is fixed by asking for more depth,
    `node_limited` cannot be — those nodes carry no anchor anywhere."""

    document_id: str
    version_id: str
    filename: str
    page_count: int | None
    total_est_tokens: int
    mode: str  # "sections" | "pages" — how the map was derived
    nodes: list[OutlineNode] = field(default_factory=list)
    depth_limited: bool = False
    node_limited: bool = False


@dataclass(frozen=True)
class ResolvedElement:
    """One docling element, resolved against a parse: text + provenance."""

    ref: str
    label: str
    text: str
    level: int = 0
    page: int | None = None
    bbox: BoundingBox | None = None
    headings: list[str] = field(default_factory=list)

    @property
    def est_tokens(self) -> int:
        return estimate_tokens(self.text)


@dataclass(frozen=True)
class Excerpt:
    """What `read_element` returns: markdown + one citation per element read.

    `next_cursor` is a `ref`: pass it back as `cursor` to continue exactly
    where the budget cut the read. `None` means the section is exhausted.
    """

    document_id: str
    version_id: str
    ref: str
    uri: str
    title: str
    markdown: str
    citations: list[Citation] = field(default_factory=list)
    est_tokens: int = 0
    truncated: bool = False
    next_cursor: str | None = None
    page_range: tuple[int, int] | None = None


# Docling labels that open a section in the outline. `title` is level 0 so a
# document title contains the chapters that follow it.
HEADING_LABELS = frozenset({"title", "section_header"})

# Labels carrying no readable text of their own — skipped by the reader so an
# excerpt is not padded with empty lines.
_EMPTY_LABELS = frozenset({"page_header", "page_footer"})

# Characters per token. A rough, tokenizer-free estimate: the numbers are a
# budgeting aid shown to the agent, not an accounting figure, and pulling a
# real tokenizer in for them would add a heavyweight dependency to `domain`.
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Estimate the token cost of `text` (≈ 4 characters per token)."""
    if not text:
        return 0
    return max(1, (len(text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)


def chars_for_tokens(tokens: int) -> int:
    """Inverse of `estimate_tokens` — the character budget for `tokens`."""
    return max(1, tokens) * _CHARS_PER_TOKEN


def is_heading(label: str) -> bool:
    return (label or "").lower() in HEADING_LABELS


def is_readable(label: str) -> bool:
    return (label or "").lower() not in _EMPTY_LABELS
