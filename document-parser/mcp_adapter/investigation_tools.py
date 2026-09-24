"""The investigation journal's tools — the first ones on this surface that write.

They write to the journal's own tables and to nothing else: no document, no
analysis, no chunk is touched, so the read-only promise of #327 holds where it
was made. What changes is that the surface now remembers, which is what lets
the server count attempts and refuse an answer the investigation did not earn.

Mapping only, like every other tool module here. The sequencing lives in
`InvestigationService`, the verdicts in `investigation_adjudicator`, the
shapes in `investigation_wire`. A tool that starts deciding something is a
service that has not been written yet.

Registered behind `MCP_INVESTIGATION_ENABLED`: six extra tool descriptions
are read on every call, including in the conversations that never
investigate.
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
    StepAbandoned,
    abandoned_result,
    attempt_result,
    closed_result,
    opened_result,
    plan_result,
    view_result,
)
from mcp_adapter.tool_errors import ToolErrors

if TYPE_CHECKING:
    from collections.abc import Callable

    from mcp.server.mcpserver import MCPServer

    from services.document_tools import DocumentTools

# These tools change server state. `open_world_hint` stays false: the state
# they touch is this server's own, not the wider world.
_WRITES = ToolAnnotations(read_only_hint=False, idempotent_hint=False, open_world_hint=False)
_READS = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)

INSTRUCTIONS = "For a question needing several passages, run the `investigate` prompt.\n"


def register_investigation_tools(
    server: MCPServer,
    tools: Callable[[], DocumentTools],
    *,
    viewer: bool = False,
) -> None:
    """Publish the journal's six tools on `server`.

    `viewer` says whether `show_investigation` exists on this surface, so the
    close result can steer to it — pointing a model at a tool this server did
    not publish would spend a turn on a failure.
    """

    @server.tool(
        annotations=_WRITES,
        description=(
            "Start a recorded investigation of one document (`document_id`) for a question "
            "that needs several passages. Pins the parse and returns its outline to plan from."
        ),
    )
    async def open_investigation(document_id: str, question: str) -> InvestigationOpened:
        async with ToolErrors():
            service = tools().investigations
            investigation, outline = await service.open(document_id=document_id, question=question)
        return opened_result(
            investigation,
            outline,
            max_steps=service.config.max_steps_per_investigation,
            max_attempts=service.config.max_attempts_per_step,
        )

    @server.tool(
        annotations=_WRITES,
        description=(
            "Record the plan, once: `steps` is a list of {question, why}, sub-questions the "
            "document can each answer. Returns the step ids."
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
            "Try an anchor (`uri`) for a step. `thought`: why you chose it. `quote`: what you "
            "would publish; the server verifies it. When `outcome` is kept, cite `kept_uri`. "
            "At `attempts_left` 0 the step is unanswered: a finding to state."
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
        return attempt_result(verdict, investigation_id=investigation_id)

    @server.tool(
        annotations=_WRITES,
        description=(
            "Drop a planned step you will not work; `thought` says why. Closing needs every "
            "step worked or abandoned."
        ),
    )
    async def abandon_step(
        investigation_id: str,
        step_id: str,
        thought: str,
    ) -> StepAbandoned:
        async with ToolErrors():
            investigation = await tools().investigations.abandon_step(
                investigation_id, step_id, thought
            )
        return abandoned_result(investigation, step_id)

    @server.tool(
        annotations=_WRITES,
        description=(
            "Publish `answer` and close. Every dstudio:// anchor in it must be one this "
            "investigation kept; citing none is allowed only when no step was answered."
        ),
    )
    async def close_investigation(investigation_id: str, answer: str) -> InvestigationClosed:
        async with ToolErrors():
            investigation = await tools().investigations.close(investigation_id, answer)
        return closed_result(investigation, find_anchors(answer), viewer=viewer)

    @server.tool(
        annotations=_READS,
        description=(
            "Read an investigation back, to resume it: `reasoning` has its steps and attempts "
            "with the server's verdicts, `map` where they landed in the document."
        ),
    )
    async def get_investigation(investigation_id: str) -> InvestigationView:
        async with ToolErrors():
            report = await tools().investigations.view(investigation_id)
        return view_result(report)


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
