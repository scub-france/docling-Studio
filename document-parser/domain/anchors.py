"""The anchor grammar — how a citation names what it points at.

    dstudio://doc/{document_id}@{version_id}#{ref}
    dstudio://doc/8f2a91c4@a71f0c33#/texts/91

- `document_id` — `Document.id`.
- `version_id`  — an **opaque** version token. Today it is the id of the
  analysis run that produced the tree, because a docling `self_ref` is stable
  *inside* one parse and meaningless across two: re-parsing the same PDF
  renumbers `#/texts/91`. Pinning the version is what keeps a citation true
  after a re-parse instead of silently pointing at another paragraph.
- `ref` — the docling `self_ref`, verbatim (`#/texts/91`, `#/tables/3`), a
  span over a run of elements (`#/texts/91..#/texts/94`), or one of the
  virtual page refs (`#/pages/7`) the navigator synthesises for documents
  without section headings.

An agent never builds an anchor by hand: every read returns the anchors of
what it just read, and `CitationService.verify_citation` re-resolves one
server-side, so a fabricated or drifted citation is detectable rather than
merely implausible.

Quote normalisation lives here too, because it is the other half of the same
promise: what counts as the *same* quote when one has been through a model.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

# grammar only forbids the separators themselves so opaque ids stay opaque.
_URI_RE = re.compile(r"^dstudio://doc/(?P<doc>[^@/#]+)@(?P<version>[^@/#]+)(?P<ref>#.+)$")

URI_SCHEME = "dstudio"

# Anchors as they appear *inside prose* — an answer citing its sources. The
# character class stops at whitespace and at the punctuation a sentence wraps
# a uri in, so `(dstudio://doc/a@b#/texts/1)` and a trailing full stop both
# yield the anchor and not the bracket. Deliberately more permissive than
# `_URI_RE`: what it finds is then parsed, and a near-miss should fail
# parsing rather than be silently skipped as "not an anchor".
_IN_TEXT_RE = re.compile(r"dstudio://doc/[^\s()\[\]{}<>\"\'`]+")

# What a well-formed anchor looks like, ending on the ref's digits. A match
# trims whatever a sentence glued on (`**`, a closing guillemet, a full
# stop); a near-miss keeps its raw form, so it fails parsing downstream.
_ANCHOR_PREFIX_RE = re.compile(r"dstudio://doc/[^@#]+@[^#]+#/[a-z_]+/\d+(?:\.\.#/[a-z_]+/\d+)?")

_TRAILING = ".,;:!?"

# Typography a model does not reproduce faithfully: apostrophes and dashes
# fold to one form, double quotes and the soft hyphen are dropped.
_QUOTE_FOLD = str.maketrans(
    {
        **dict.fromkeys("\u2019\u2018\u201a\u201b\u2032", "'"),
        **dict.fromkeys("\u2010\u2011\u2012\u2013\u2014\u2015\u2212", "-"),
        **dict.fromkeys('"\u201c\u201d\u201e\u201f\u00ab\u00bb\u2033\u00ad', None),
        "|": " ",  # table cells: the pipes of the rendered row are layout
    }
)


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
    """The comparison form for quotes, applied to both sides.

    Verification must survive the trip through a model: line wrapping, a
    non-breaking space, a ligature, a curly apostrophe or « guillemets » are
    not textual drift. Anything else (a changed word, a dropped clause) is.
    """
    # The wire defuses `</document-content>` to `<\\/document-content>` before
    # handing document text to a model, so a quote coming back carries the
    # escaped form. Undo it here: an escape we applied ourselves is not drift.
    text = (text or "").replace("<\\/", "</")
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_FOLD)
    return re.sub(r"\s+", " ", text).strip()


def find_anchors(text: str) -> list[str]:
    """Every `dstudio://` anchor cited in `text`, in order, de-duplicated.

    Used to check an answer against what its investigation was allowed to
    keep: a claim that names an anchor nobody verified is the failure the
    whole protocol exists to prevent, and it can only be caught by reading
    the prose the model is about to publish.
    """
    seen: list[str] = []
    for raw in _IN_TEXT_RE.findall(text or ""):
        wellformed = _ANCHOR_PREFIX_RE.match(raw)
        candidate = wellformed.group(0) if wellformed else raw.rstrip(_TRAILING)
        if candidate and candidate not in seen:
            seen.append(candidate)
    return seen
