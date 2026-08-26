"""The anchor grammar — how a citation names what it points at.

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
what it just read, and `CitationService.verify_citation` re-resolves one
server-side, so a fabricated or drifted citation is detectable rather than
merely implausible.

Quote normalisation lives here too, because it is the other half of the same
promise: what counts as the *same* quote when one has been through a model.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

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
