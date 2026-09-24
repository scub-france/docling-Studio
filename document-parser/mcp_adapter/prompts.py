"""User-invoked procedures — the protocols nobody wants always-on.

A tool description is read on every call and pays for itself in tokens each
time; a prompt is a slash command the *user* chooses. That is the right home
for a protocol that is thorough on purpose: reading a document under a budget,
citing every claim, and verifying each quote before it is published costs
several extra calls, which is worth it when someone asks for a sourced answer
and wasteful when they ask a passing question.

Nothing here is a second implementation of the tools. A prompt returns text
that the model then executes with the same tools; keeping the procedure
declarative is what stops it from drifting away from what the server does.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from pydantic import Field

if TYPE_CHECKING:
    from mcp.server.mcpserver import MCPServer

EVIDENCE_MODES = ("text", "images")


def register_prompts(
    server: MCPServer,
    *,
    investigations: bool = True,
    apps: bool = True,
) -> None:
    """Register the server's user-invoked procedures.

    `investigations` follows `MCP_INVESTIGATION_ENABLED`: a prompt that
    drives five tools the server did not publish would be a procedure the
    agent cannot execute, which is worse than one it never sees.
    """
    if investigations:
        _register_investigate(server, apps=apps)

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
        # Only when the viewer is published: naming a tool this server did not
        # publish spends a turn on a failure.
        show = apps and evidence.strip().lower() == "images"
        step_five = (
            "\n5. `show_citation(uri)` on each verified citation, to show the reader its page."
            if show
            else ""
        )
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
claim.{step_five}

If the document does not answer, say so. Do not complete the answer from what you already \
know."""


def _register_investigate(server: MCPServer, *, apps: bool = True) -> None:
    """The decomposed question — the protocol the journal exists to hold.

    `cite_answer` stays for the question one passage settles. This is for the
    one that does not: the server keeps the plan, grades every ref, bounds
    the retries, and leaves a navigation tree behind.
    """

    @server.prompt(
        name="investigate",
        title="Investigate a document, step by step",
        description=(
            "Answer a question that needs several passages, recording the reasoning: "
            "the server keeps the plan, checks every ref, and bounds the retries."
        ),
    )
    def investigate(
        document: Annotated[str, Field(description="Filename, or a fragment of one.")],
        question: Annotated[str, Field(description="What to answer from that document.")],
    ) -> str:
        step_seven = (
            "\n7. Finish with `show_investigation(investigation_id)`: one card for the whole "
            "record. Not a `show_citation` per passage; keep that for a passage in dispute."
            if apps
            else ""
        )
        return f"""\
Investigate "{document}" to answer this, recording as you go:

{question}

1. `find_documents(query="{document}")`, then `open_investigation(document_id, question)`. \
If several documents match, ask which first.
2. `plan_steps`: split the question into steps a section of the outline can each answer, \
each with its `why`.
3. For each step, `read_element` the likely entry, then `record_attempt(investigation_id, \
step_id, thought, uri, quote)`: `thought` is why you chose it, `quote` what you would publish.
4. The verdict is the server's. `kept`: cite `kept_uri`. `quote_drift`: `actual_quote` is \
the real text. `unknown_ref`: use a uri a read returned. At 0 `attempts_left` the step is \
`unanswered`: a finding, not a failure.
5. A step you will not work: `abandon_step` with the reason. Closing is refused while a \
step is pending.
6. `close_investigation(investigation_id, answer)`: cite only kept anchors, and say which \
steps the document did not answer.{step_seven}

`thought` is recorded verbatim and never checked: write what you actually reasoned."""
