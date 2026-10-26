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

Nothing here is a second implementation of the tools. The prompt returns text
that the model then executes with the same tools; keeping the procedure
declarative is what stops it from drifting away from what the server does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

if TYPE_CHECKING:
    from mcp.server.mcpserver import MCPServer

# Only when the cards are published: naming a tool this server did not publish
# spends a turn on a failure.
_CARD_STEPS = """
5. `show_citation(uri)` on the one verified quote that carries the answer: the reader \
sees it on its page.
6. `show_sources(question, read, cited)` to end. `read`: the `uri` of each read_element \
result, in the order you read them, each with a one-line `why`. `cited`: the anchors you \
verified."""

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
2. `get_outline(document_id)`: pick the entries likely to answer, by title and `est_tokens`.
3. `read_element(document_id, ref)` on those only. When `truncated`, continue with \
`cursor=next_cursor` rather than re-reading with a bigger budget.
4. Back every claim with a quote and the `citations[].uri` of the element quoted, and \
`verify_citation(uri, quote)` each one. On `quote_drift`, fix the quote or drop the \
claim.{_CARD_STEPS if apps else _TEXT_STEP}

If the document does not answer, say so. Do not complete the answer from what you already \
know."""
