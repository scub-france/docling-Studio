# Analysis Editor: Path To Alpha

## Goal

Ship an alpha that makes the existing text and structural editing workflow
reliable, understandable, and recoverable. The alpha is not a general-purpose
document authoring tool.

## Implementation Status

Completed:

- Durable command replay, preview/save consistency, working-copy recovery, and
  realistic nested/provenance projection regressions.
- Selection feedback, save feedback, explicit move destinations, pending-edit
  recovery, conflict recovery, and keyboard-accessible tree/move controls.
- Safe structured logs for editor projection failures without document text.
- Axe accessibility audit for the mounted editor, plus keyboard selection and
  move controls.
- Karate UI workflows for replace, merge, move, range delete, discard,
  save/reload, refresh/restore, and stale-draft rejection using generated
  fixtures.

Deferred or external validation:

- Expand browser tests to cover undo/redo, save conflicts, PDF provenance
  selection, and read-only element feedback.
- Final alpha validation still requires representative production-like documents.

## Alpha Scope

The editor supports durable, replayable operations for:

- Replacing text.
- Converting text and headings between title, body text, and heading levels.
- Merging compatible selected paragraphs, including cross-parent selections.
- Moving elements and subtrees in reading order.
- Deleting individual elements or a selected range.
- Previewing, saving, discarding, and locally undoing or redoing pending edits.

## Phase 1: Prove Core Workflows

### End-to-End Coverage

Add browser-level tests for the critical paths:

- Select an element, edit text, preview, save, reload, and confirm persistence.
- Cmd/Ctrl-select text, merge it, preview, save, and reload.
- Reorder an element within and across parents, then save and reload.
- Delete one element and a range containing a parent and child.
- Undo and redo pending text and structural edits.
- Discard pending edits and verify the saved document is restored.

Acceptance criteria:

- Tests run in CI against the local development stack.
- Each durable command is covered by save/reload replay verification.
- The test corpus includes representative headings, nested sections, and pages
  with provenance.

### Replay and Projection Checks

- Verify preview and save produce equivalent normalized Docling documents.
- Verify saved streams rebuild correctly after deleting the working-copy cache.
- Verify generated Markdown, HTML, page overlays, and tree projections remain
  internally consistent after every command type.

Acceptance criteria:

- A focused backend regression suite covers every command and Docling tree
  validation path.
- Replay failures include command sequence and command type in structured logs
  without logging document text.

## Phase 2: Make Editing Understandable

### Selection and Operation Feedback

- Display a clear selected-element count and multi-select keyboard guidance.
- Keep selection focused on the merge target or move target after an operation.
- Show inline success feedback after a save.
- Explain invalid or unsupported operations before the user attempts them.
- Confirm range deletion with the selected-element count and affected subtree
  count.

Acceptance criteria:

- No disabled operation appears without an explanation.
- Every destructive operation requires a deliberate confirmation or has a
  clearly reversible pending undo action.
- The selected state is visually distinguishable in both PDF and reading-order
  tree views.

### Explicit Move Destinations

- Replace ambiguous tree drop behavior with visible destinations: before, after,
  and inside a section.
- Preserve cycle prevention and Docling tree validation.
- Retain the existing behavior that moving a parent moves its subtree.

Acceptance criteria:

- A user can predict the destination parent and relative position before drop.
- Unsupported nodes cannot be used as drag sources or destinations.
- Cross-parent moves have browser and backend regression coverage.

## Phase 3: Make Pending Work Recoverable

### Navigation and Refresh Protection

- Warn before leaving the editor with pending edits.
- Store pending commands in session-scoped browser storage, keyed by document
  and base analysis.
- Restore pending edits only after confirming their expected saved sequence is
  still current.
- Provide explicit restore and discard choices when pending work is found.

Acceptance criteria:

- Refreshing the page does not silently lose pending edits.
- Stale pending edits are never replayed onto a changed saved stream without
  user confirmation.
- Discard clears both the in-memory and session-scoped pending state.

### Conflict Recovery

- Replace raw optimistic-concurrency errors with a conflict state.
- Offer reload saved result, copy pending edit details, or discard pending
  changes.
- Do not attempt automatic command rebasing in alpha.

Acceptance criteria:

- A sequence conflict does not leave the editor in an ambiguous state.
- The user can return to a usable saved document without manually refreshing.

## Phase 4: Accessibility and Operational Readiness

### Accessibility

- Add keyboard navigation for the reading-order tree and properties panel.
- Ensure visible focus states and accessible labels for operation controls.
- Announce selection-count and save/error status changes to assistive
  technology.

Acceptance criteria:

- Core text edit, merge, move, delete, save, undo, and redo workflows are
  keyboard-operable.
- Automated accessibility checks cover the editor toolbar and tree.

### Observability and Support

- Emit structured events for command replay, validation, projection, save, and
  Docling compatibility failures.
- Include document ID, base analysis ID, command sequence, and command type;
  exclude document text and sensitive payload content.
- Surface a supportable error reference in the UI for unexpected failures.

Acceptance criteria:

- Failures can be correlated from the UI report to backend logs.
- Private Docling API compatibility errors identify the required remediation.

## Explicitly Deferred

- General paragraph, heading, title, list, table, caption, image, and footnote
  insertion.
- Table-cell and rich-table editing.
- List creation, nesting, and indentation controls.
- Saved-history undo/redo through compensating durable commands.
- Automatic conflict rebasing.
- LLM-generated edits.

## Alpha Exit Criteria

- All Phase 1 browser and backend regressions pass in CI.
- Pending edits survive refresh and have a clear conflict path.
- Text, merge, move, and delete operations are understandable and accessible.
- Replay and Docling validation failures are observable and actionable.
- The team has exercised the workflow on representative real documents and
  recorded known unsupported element types.
