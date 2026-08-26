"""User-invoked procedures — the protocols nobody wants always-on.

A tool description is read on every call and pays for itself in tokens each
time; a prompt is a slash command the *user* chooses. That is the right home
for a protocol that is thorough on purpose: reading a document under a budget,
citing every claim, and verifying each quote before it is published costs
several extra calls, which is worth it when someone asks for a sourced answer
and wasteful when they ask a passing question.

Nothing here is a second implementation of the tools. A prompt returns text
that the model then executes with the same four tools; keeping the procedure
declarative is what stops it from drifting away from what the server actually
does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

if TYPE_CHECKING:
    from mcp.server.mcpserver import MCPServer

EVIDENCE_MODES = ("text", "images")


def register_prompts(server: MCPServer) -> None:
    """Register the server's user-invoked procedures."""

    @server.prompt(
        name="cite_answer",
        title="Answer with verified citations",
        description=(
            "Answer a question about one document, reading under a budget and "
            "backing every claim with a citation the server has verified."
        ),
    )
    def cite_answer(
        document: Annotated[str, Field(description="Filename, or a fragment of one.")],
        question: Annotated[str, Field(description="What to answer from that document.")],
        evidence: Annotated[
            str,
            Field(description="'text' for quoted citations, 'images' to also show each passage."),
        ] = "text",
    ) -> str:
        show = evidence.strip().lower() == "images"
        step_six = (
            "\n6. `show_citation(uri)` on each verified citation, so the reader sees the "
            "passage on the page it came from."
            if show
            else ""
        )
        return f"""\
Answer this question about "{document}", using only what that document says:

{question}

Follow this protocol:

1. `find_documents(query="{document}")` — resolve it to one document_id. If several match, \
ask which before reading anything. A null version_id means the document has never been \
parsed and cannot be read.
2. `get_outline(document_id)` — the map before any text. Every entry carries `est_tokens`, \
so choose what to read instead of paying to find out. Reading a whole document is \
typically one to two orders of magnitude more expensive than reading the section that \
answers the question.
3. `read_element(uri)` on those entries only. When `truncated` is true, continue with \
`cursor=next_cursor` — do not re-read the same section with a bigger budget.
4. Every claim you make carries a citation, and the citation is `citations[].uri`: the uri \
of the element you are quoting, not the uri you passed to `read_element`.
5. `verify_citation(uri, quote)` on each quote before you write it down. `quote_drift` \
means the quote is not there — fix it or drop the claim, never publish it. \
`stale_version` means it is real but pins a superseded parse.{step_six}

If the document does not answer the question, say so plainly and stop. Do not complete \
the answer from what you already know: one unsourced sentence inside a sourced answer is \
the failure this whole protocol exists to prevent."""

    @server.prompt(
        name="extract_table",
        title="Extract a table verbatim",
        description=(
            "Return one table as markdown, unaltered, with the citation needed to "
            "check it against the page."
        ),
    )
    def extract_table(
        uri: Annotated[str, Field(description="Anchor uri of the table, from get_outline.")],
    ) -> str:
        return f"""\
Read the table at `{uri}` and give it back as markdown.

1. `read_element(uri="{uri}", include="self")` — a table is one element, and reading its \
section would pull in the surrounding prose for nothing.
2. Return the markdown exactly as the server rendered it. Do not re-align columns, \
re-order rows, round numbers, or repair a cell that looks wrong: a table is evidence, and \
a corrected table is no longer evidence. An empty cell in the source stays empty.
3. Close with the citation — `citations[0].uri` and its page. If a number matters enough \
that someone will want to check it, `show_citation` on that uri puts the original in front \
of them.

If the uri does not point at a table, say what it does point at and stop."""
