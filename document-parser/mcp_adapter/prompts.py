"""The user-invoked procedure — the Chunkless RAG loop as a slash command.

A tool description is read on every call and pays for itself in tokens each
time; a prompt is a slash command the *user* chooses. That is the right home
for a protocol that is thorough on purpose: reading a document under a budget,
citing every claim, and verifying each quote before it is published costs
several extra calls, which is worth it when someone asks for a sourced answer
and wasteful when they ask a passing question.

One prompt (#363), named after what it does: no chunks, no embeddings — the
model reads the map, opens only what the question needs, and every quote it
publishes is checked by the server. It replaces `cite_answer` and
`investigate`, which split the same loop in two.

The loop is docling-agent's, run by the client model: one section per round,
each with the reason for going there and what it gave, at most `MAX_ROUNDS`
rounds — the same cap as Studio's own Ask loop. Bounded, so the model does not
wander; explained, so the card can show the reasoning round by round.

Nothing here is a second implementation of the tools. The prompt returns text
that the model then executes with the same tools; keeping the procedure
declarative is what stops it from drifting away from what the server does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

from services.navigation_config import MAX_ROUNDS

if TYPE_CHECKING:
    from mcp.server.mcpserver import MCPServer

# Only when the cards are published: naming a tool this server did not publish
# spends a turn on a failure. One card ends the answer — show_sources shows
# each round's page with the passages boxed; show_citation is off by default.
_CARD_STEPS = """
5. `show_sources(question, read, cited)` to end. `read`: your rounds in order, each \
`{uri, why, found}` with the `uri` its read_element returned. `cited`: each quote you \
verified, as `{uri, quote}`."""

_TEXT_STEP = """
5. Give the reader each verified quote with its `deep_link`, when there is one."""


def register_prompts(server: MCPServer, *, apps: bool = True) -> None:
    """Register `chunkless_rag`."""

    @server.prompt(
        name="chunkless_rag",
        title="Chunkless RAG — answer with verified citations",
        description=(
            "Answer a question from one document by reading its map, then only the "
            "sections the question needs, and backing every claim with a quote the "
            "server has verified."
        ),
    )
    def chunkless_rag(
        document: Annotated[str, Field(description="Filename, or a fragment of one.")],
        question: Annotated[str, Field(description="What to answer from that document.")],
    ) -> str:
        return f"""\
Answer this from "{document}" only:

{question}

1. `find_documents(query="{document}")`: its document_id. If several match, ask which. A \
null version_id means it was never parsed: say so and stop.
2. `get_outline(document_id)`: the map, each entry with its `est_tokens`.
3. Then at most {MAX_ROUNDS} rounds. Each round: pick ONE entry, say in one line why, \
`read_element(document_id, ref)`, and say in one line what it gave. When `truncated`, \
continue with `cursor=next_cursor`: same round, not a new one. Stop as soon as you can \
answer.
4. Back every claim with a quote and the `citations[].uri` of the element quoted, and \
`verify_citation(uri, quote)` each one. On `quote_drift`, fix the quote or drop the \
claim.{_CARD_STEPS if apps else _TEXT_STEP}

If {MAX_ROUNDS} rounds did not find the answer, or the document does not answer, say what \
is missing. Do not complete the answer from what you already know."""
