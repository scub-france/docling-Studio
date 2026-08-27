"""Reading elements out of an indexed parse.

Resolution (`ref` -> text, page, provenance), the span a ref covers when read
as a section, and the markdown an excerpt is rendered as. Table payloads are
handled here too: a table is the element most worth citing verbatim and the
one whose shape varies most between docling versions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from domain.navigation import BoundingBox, ResolvedElement, is_heading, is_readable
from domain.parse_index import heading_level, label_of, parse_page_ref
from domain.spans import parse_span, span_members, span_ref

if TYPE_CHECKING:
    from domain.parse_index import DocumentIndex


def resolve(index: DocumentIndex, ref: str) -> ResolvedElement | None:
    """Resolve a `ref` to an element: a docling self_ref, a virtual page ref,
    or a span covering several elements (`#/texts/91..#/texts/94`)."""
    span = parse_span(ref)
    if span is not None:
        return _resolve_span(index, *span)

    page = parse_page_ref(ref)
    if page is not None:
        if index.page_numbers and page not in index.page_numbers:
            return None
        return ResolvedElement(ref=ref, label="page", text="", level=1, page=page)

    item = index.by_ref.get(ref)
    if item is None:
        return None
    label = label_of(item)
    return ResolvedElement(
        ref=ref,
        label=label,
        text=element_text(index, ref),
        level=heading_level(item) if is_heading(label) else 0,
        page=index.page_of.get(ref),
        bbox=index.bbox_of.get(ref),
        headings=list(index.heading_path.get(ref, [])),
    )


def section_refs(index: DocumentIndex, ref: str) -> list[str]:
    """Refs covered by `ref` when read as a section, in reading order.

    - a **page** ref covers every element whose first provenance is on it;
    - a **heading** covers everything until the next heading of the same or a
      higher level — nested subsections included, which is what "read
      Article 12" means to a reader;
    - anything else covers itself plus its docling descendants (a list and
      its items, a group and its rows).
    """
    span = parse_span(ref)
    if span is not None:
        return span_members(index, *span)

    page = parse_page_ref(ref)
    if page is not None:
        return [r for r in index.order if page in index.pages_of.get(r, frozenset())]

    if ref not in index.position:
        return []
    start = index.position[ref]
    item = index.by_ref[ref]
    if is_heading(label_of(item)):
        return index.order[start : index.section_end.get(ref, start + 1)]

    descendants = _descendant_refs(index, ref)
    return [ref] + [r for r in index.order[start + 1 :] if r in descendants]


def _descendant_refs(index: DocumentIndex, ref: str) -> set[str]:
    seen: set[str] = set()
    stack = [ref]
    while stack:
        current = index.by_ref.get(stack.pop())
        if current is None:
            continue
        for child in current.get("children") or []:
            child_ref = child.get("$ref") or child.get("cref")
            if not child_ref or child_ref in seen or child_ref not in index.by_ref:
                continue
            seen.add(child_ref)
            stack.append(child_ref)
    return seen


# What a span's citation is labelled. Not the label of its first element: a
# range of paragraphs is not a paragraph, and calling it one would colour the
# card and drive the reader's expectations off a member that happens to sort
# first.
SPAN_LABEL = "span"


def _resolve_span(index: DocumentIndex, start: str, end: str) -> ResolvedElement | None:
    """Resolve a span into one element carrying the whole passage.

    The text is the members' own text joined by blank lines — *not* rendered
    markdown. A quote crossing a heading must still verify, and prefixing that
    heading with `##` would put characters in the citation that are nowhere in
    the document.
    """
    members = [(ref, element_text(index, ref)) for ref in span_members(index, start, end)]
    readable = [(ref, text) for ref, text in members if text.strip()]
    if not readable:
        return None

    first = readable[0][0]
    page = next((index.page_of[ref] for ref, _ in readable if ref in index.page_of), None)
    boxes = [
        index.bbox_of[ref]
        for ref, _ in readable
        if ref in index.bbox_of and index.page_of.get(ref) == page
    ]
    return ResolvedElement(
        ref=span_ref(start, end),
        label=SPAN_LABEL,
        text="\n\n".join(text for _, text in readable),
        page=page,
        bbox=BoundingBox.union(boxes),
        headings=list(index.heading_path.get(first, [])),
    )


def element_text(index: DocumentIndex, ref: str) -> str:
    """The readable text of one element — inline runs joined, tables rendered."""
    meta = index.inline_meta.get(ref)
    if meta and meta.get("text"):
        return str(meta["text"])

    item = index.by_ref.get(ref)
    if item is None:
        return ""
    label = label_of(item)
    if not is_readable(label):
        return ""
    if label in {"table", "document_index"}:
        return _render_table(item) or _caption_text(index, item)
    text = (item.get("text") or "").strip()
    if text:
        return text
    if label in {"picture", "chart"}:
        caption = _caption_text(index, item)
        return f"[figure] {caption}".strip() if caption else "[figure]"
    return ""


def _caption_text(index: DocumentIndex, item: dict[str, Any]) -> str:
    parts: list[str] = []
    for caption in item.get("captions") or []:
        caption_ref = caption.get("$ref") or caption.get("cref")
        target = index.by_ref.get(caption_ref or "")
        if target and target.get("text"):
            parts.append(str(target["text"]).strip())
    return " ".join(parts).strip()


# What an unreadable table reads as. Not "": an empty string makes the element
# look textless, and a textless element is skipped by the reader — so a parse
# whose table payload changed shape would tell an agent the table is empty
# rather than that it could not be read. A marker survives the skip, and still
# verifies (verification is a substring match).
UNREADABLE_TABLE = "[table: unreadable payload]"


def _render_table(item: dict[str, Any]) -> str:
    """Render a docling table as markdown.

    Defensive by design: table payloads vary across docling versions, and a
    citation on a table is worth more than a perfectly formatted one. A shape
    this cannot read is reported, not swallowed.
    """
    data = item.get("data") or {}
    try:
        rows = _table_rows(data)
    except Exception:
        return UNREADABLE_TABLE
    if not rows:
        return UNREADABLE_TABLE if data else ""
    width = max(len(row) for row in rows)
    padded = [[*row, *([""] * (width - len(row)))] for row in rows]
    header, *body = padded
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in body]
    return "\n".join(lines)


def _table_rows(data: dict[str, Any]) -> list[list[str]]:
    grid = data.get("grid")
    if isinstance(grid, list) and grid:
        return [[_cell_text(cell) for cell in row] for row in grid]

    cells = data.get("table_cells") or []
    if not cells:
        return []
    num_rows = int(data.get("num_rows") or 0) or (
        max(int(c.get("start_row_offset_idx", 0)) for c in cells) + 1
    )
    num_cols = int(data.get("num_cols") or 0) or (
        max(int(c.get("start_col_offset_idx", 0)) for c in cells) + 1
    )
    rows = [[""] * num_cols for _ in range(num_rows)]
    for cell in cells:
        row = int(cell.get("start_row_offset_idx", 0))
        col = int(cell.get("start_col_offset_idx", 0))
        if 0 <= row < num_rows and 0 <= col < num_cols:
            rows[row][col] = _cell_text(cell)
    return rows


def _cell_text(cell: Any) -> str:
    if isinstance(cell, dict):
        return str(cell.get("text") or "").replace("|", "\\|").replace("\n", " ").strip()
    return str(cell or "").strip()


def render_markdown(elements: list[ResolvedElement]) -> str:
    """Render resolved elements as markdown, preserving heading structure."""
    blocks: list[str] = []
    for element in elements:
        text = element.text.strip()
        if not text:
            continue
        label = element.label
        if is_heading(label):
            blocks.append("#" * min(element.level + 1, 6) + " " + text)
        elif label == "list_item":
            blocks.append("- " + text)
        else:
            blocks.append(text)
    return "\n\n".join(blocks)
