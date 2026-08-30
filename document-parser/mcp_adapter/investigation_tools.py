"""The investigation journal's tools — the first ones on this surface that write.

They write to the journal's own tables and to nothing else: no document, no
analysis, no chunk is touched, so the read-only promise of #327 holds where it
was made. What changes is that the surface now remembers, which is what lets
the server count attempts and refuse an answer the investigation did not earn.

Mapping only, like every other tool module here. The sequencing lives in
`InvestigationService`, the verdicts in `investigation_adjudicator`, the
shapes in `investigation_wire`. A tool that starts deciding something is a
service that has not been written yet.

Registered behind `MCP_INVESTIGATION_ENABLED`: five extra tool descriptions
are read on every call, including in the conversations that never
investigate, and this surface has already paid once for sending text nobody
asked for twice.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp.types import ToolAnnotations

from domain.anchors import find_anchors
from mcp_adapter.investigation_wire import (
    AttemptSettled,
    InvestigationClosed,
    InvestigationOpened,
    InvestigationView,
    PlanAccepted,
    attempt_result,
    closed_result,
    opened_result,
    plan_result,
    view_result,
)
from mcp_adapter.tool_errors import ToolErrors
from mcp_adapter.wire import UNTRUSTED_NOTE

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.mcpserver import MCPServer

    from mcp_adapter.ledger import Ledger
    from services.document_tools import DocumentTools

# These tools change server state. `open_world_hint` stays false: the state
# they touch is this server's own, not the wider world.
_WRITES = ToolAnnotations(read_only_hint=False, idempotent_hint=False, open_world_hint=False)
_READS = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

INSTRUCTIONS = """\

For a question that needs more than one passage, run the `investigate` prompt rather than \
reading ad hoc: the server then keeps the plan, checks every ref you try, bounds the \
retries, and leaves a navigation tree behind.
"""


def register_investigation_tools(
    server: MCPServer,
    tools: Callable[[], DocumentTools],
    ledger: Ledger,
) -> None:
    """Publish the journal's five tools on `server`."""

    @server.tool(
        annotations=_WRITES,
        description=(
            "Start a recorded investigation of one document and return its map. Use it "
            "when a question needs several passages: the server then remembers what you "
            "tried, checks each ref, and bounds how many times a step may be retried. "
            "Resolves `document` to exactly one document — it refuses when several match, "
            "so ask which before starting. The parse is pinned for the whole "
            "investigation, so every ref stays comparable. Returns the outline too: plan "
            "against it rather than paying a second call to see it."
        ),
    )
    async def open_investigation(document: str, question: str) -> InvestigationOpened:
        async with ToolErrors():
            service = tools().investigations
            investigation, outline = await service.open(document=document, question=question)
        return ledger.record(
            opened_result(
                investigation,
                outline,
                max_steps=service.config.max_steps_per_investigation,
                max_attempts=service.config.max_attempts_per_step,
            )
        )

    @server.tool(
        annotations=_WRITES,
        description=(
            "Record the decomposition of the question into steps. `steps` is a list of "
            '{"question": "...", "why": "..."} — the sub-question, and why answering it '
            "moves the main question forward; a bare string is taken as the question. "
            "Callable once per investigation: a plan "
            "that grows while it is being executed is not a plan, and it would make the "
            "attempt budget meaningless. Returns the step ids to use with record_attempt."
        ),
    )
    async def plan_steps(
        investigation_id: str,
        # The union is not decoration: the SDK validates against this schema
        # before the tool body runs, so a plan sent as bare strings would be
        # refused at the boundary and `_drafts` would never see it.
        steps: list[dict[str, str] | str],
    ) -> PlanAccepted:
        async with ToolErrors():
            service = tools().investigations
            investigation = await service.plan(investigation_id, _drafts(steps))
        return plan_result(investigation, attempts_per_step=service.config.max_attempts_per_step)

    @server.tool(
        annotations=_WRITES,
        description=(
            "Try one ref against one step, and be told whether it held up. `thought` is "
            "what you were thinking when you chose it — recorded as written, never "
            "checked. `uri` is an anchor you were given, never one you built. `quote` is "
            "the passage you would publish: pass it and the server verifies it, omit it "
            "and the ref is kept on resolution alone. The outcome is the SERVER's: "
            "kept / quote_drift / unknown_ref / empty_element / bad_anchor / "
            "foreign_document. `attempts_left` says whether to try again; at zero the "
            "step closes as unanswered, and that is a finding to state in the answer, not "
            "an error to work around."
        ),
    )
    async def record_attempt(
        investigation_id: str,
        step_id: str,
        thought: str,
        uri: str,
        quote: str | None = None,
    ) -> AttemptSettled:
        async with ToolErrors():
            verdict = await tools().investigations.record_attempt(
                investigation_id=investigation_id,
                step_id=step_id,
                thought=thought,
                uri=uri,
                quote=quote,
            )
        return ledger.record(attempt_result(verdict, investigation_id=investigation_id))

    @server.tool(
        annotations=_WRITES,
        description=(
            "Publish the answer and close the investigation. Every dstudio:// anchor in "
            "`answer` must be one this investigation kept — the server refuses an answer "
            "resting on a ref nobody verified, which is verify_citation applied to the "
            "whole claim rather than to one quote. An answer citing nothing is accepted "
            "only when no step was answered: that is the honest 'the document does not "
            "say' case."
        ),
    )
    async def close_investigation(investigation_id: str, answer: str) -> InvestigationClosed:
        async with ToolErrors():
            investigation = await tools().investigations.close(investigation_id, answer)
        return ledger.record(closed_result(investigation, find_anchors(answer)))

    @server.tool(
        annotations=_READS,
        description=(
            "Read an investigation back: `reasoning` is the plan and every attempt with "
            "its verdict, `map` is those verdicts placed on the document outline in "
            "document order — the navigation tree. Use it to resume after losing context, "
            "or to show where an answer came from. Thoughts in `reasoning` are what the "
            "agent said it was doing and are not verified; each attempt's `outcome` is. "
            f"{UNTRUSTED_NOTE}"
        ),
    )
    async def get_investigation(investigation_id: str) -> InvestigationView:
        async with ToolErrors():
            investigation, nodes = await tools().investigations.view(investigation_id)
        return ledger.record(view_result(investigation, nodes))


def _drafts(steps: list[Any]) -> list[tuple[str, str]]:
    """Normalise the plan a model sent.

    A bare list of strings is accepted alongside the documented
    `{question, why}` objects: models produce it often enough that rejecting
    it would spend an attempt on a schema quibble rather than on the
    document, and the missing `why` costs nothing but a blank field.
    """
    drafts: list[tuple[str, str]] = []
    for entry in steps or []:
        if isinstance(entry, str):
            drafts.append((entry, ""))
        elif isinstance(entry, dict):
            drafts.append((str(entry.get("question") or ""), str(entry.get("why") or "")))
    return drafts
