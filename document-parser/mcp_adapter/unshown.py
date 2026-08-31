"""Anchors kept by a closed investigation nobody has shown yet.

The `investigate` prompt asks for `show_investigation`, the close's
`next_step` asks again, and `show_citation`'s description yields — and three
runs against a live host showed what advisory text is worth at the moment a
model chooses a display: two of them ended in a card per kept anchor anyway.
This is the same lesson the journal itself was built on. The server does not
advise a model to verify its quotes; it refuses the unverified ones. So the
display follows the same rule: a citation kept by an investigation the reader
has never seen is refused, with the call to make instead, until the record
has been shown once.

In-process state, on purpose. Whether a record has been *shown* is a fact
about this serving process's conversation with its hosts, not about the
investigation — the journal in SQLite stays the domain's, and a restart
merely means one investigation may be asked to show its record again, which
is never wrong. Keyed by anchor, not by time, so a client working an
unrelated document is never caught in another conversation's redirect.
"""

from __future__ import annotations


class UnshownInvestigations:
    """The map from a kept anchor to the closed investigation that owes a showing."""

    def __init__(self) -> None:
        self._by_anchor: dict[str, str] = {}

    def closed(self, investigation_id: str, anchors: list[str]) -> None:
        """A close published these anchors; the record they rest on is unshown."""
        for anchor in anchors:
            self._by_anchor[anchor] = investigation_id

    def shown(self, investigation_id: str) -> None:
        """The record was read back — as a card or as text — and owes nothing."""
        self._by_anchor = {
            anchor: keeper
            for anchor, keeper in self._by_anchor.items()
            if keeper != investigation_id
        }

    def keeper_of(self, uri: str) -> str | None:
        """The unshown investigation this anchor belongs to, if any."""
        return self._by_anchor.get(uri)
