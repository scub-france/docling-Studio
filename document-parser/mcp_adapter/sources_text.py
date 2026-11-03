"""The sources card as a text tree, for a host without MCP Apps (#363).

Built here rather than left to the SDK's pretty-printed JSON: that text is
what a model reads on such a host, and a tree is what a reader asks it to
relay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_adapter.sources_wire import PassageOut, SourcesCard


def sources_text(card: SourcesCard) -> str:
    """The card as a tree a text-only host can relay as is."""
    lines = [f"Sources — {card.question}", f"{card.filename}: {card.summary}", ""]
    lines.append("Rounds:")
    cap = card.totals.max_rounds
    for hop in card.hops:
        page = f", p.{hop.page}" if hop.page else ""
        why = f" — {hop.why}" if hop.why else ""
        lines.append(f"{hop.ordinal}/{cap}. {hop.title}{page} (~{hop.est_tokens:,} t){why}")
        if hop.found:
            lines.append(f"   found: {hop.found}")
        # Every quote, each with its own words: several can share one anchor.
        for passage in (p for p in card.passages if p.hop_id == hop.hop_id):
            lines.append(f"   cited {passage.ref}{_said(passage)}")
        if hop.deep_link:
            lines.append(f"   open in Studio: {hop.deep_link}")
    outside = [p for p in card.passages if not p.hop_id]
    if outside:
        lines += ["", "Cited outside the rounds:"]
        lines += [f"- {p.ref}{_said(p)}" for p in outside]
    lines += ["", "On the map:"]
    lines += [f"{'  ' * max(0, n.level - 1)}- {n.title} [{n.status}]" for n in card.map]
    if card.unknown:
        lines += ["", "Unknown anchors (not shown): " + ", ".join(card.unknown)]
    return "\n".join(lines)


def _said(passage: PassageOut) -> str:
    """A cited quote, and the server's word on it, for the text tree."""
    if not passage.quote:
        return ""
    return f" — “{passage.quote}” ({passage.status or 'not checked'})"
