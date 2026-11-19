"""The sources card as text, for a host without MCP Apps (#363).

Such a host gets the same record as a short text tree, built here rather
than left to the SDK's pretty-printed JSON: that text is what a model reads
on such a host, and a tree is what a reader asks it to relay.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_adapter.sources_card import PassageOut, SourcesCard


def render_sources_text(card: SourcesCard) -> str:
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
            lines.append(f"   cited {passage.ref}{_format_quote_verdict(passage)}")
        if hop.deep_link:
            lines.append(f"   open in Studio: {hop.deep_link}")
    outside = [p for p in card.passages if not p.hop_id]
    if outside:
        lines += ["", "Cited outside the rounds:"]
        lines += [f"- {p.ref}{_format_quote_verdict(p)}" for p in outside]
    lines += ["", "On the map:"]
    lines += [f"{'  ' * max(0, n.level - 1)}- {n.title} [{n.status}]" for n in card.map]
    if card.unknown:
        lines += ["", "Unknown anchors (not shown): " + ", ".join(card.unknown)]
    return "\n".join(lines)


def _format_quote_verdict(passage: PassageOut) -> str:
    """A cited quote, and the server's word on it, for the text tree."""
    if not passage.quote:
        return ""
    return f" — “{passage.quote}” ({passage.status or 'not checked'})"
