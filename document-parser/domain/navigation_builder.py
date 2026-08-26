"""Pure projections over a serialized `DoclingDocument` — map, resolve, render.

Sibling of `domain.trace_builder`: no I/O, no dates, no randomness, and no
docling import. Every docling-shaped access goes through the injected
`DocumentTreeReader` port, so this module knows the *structure* of a parsed
document without knowing the library that produced it.

Three projections, one index:

- `build_index` walks the parse once and pre-computes what every read needs:
  reading order, heading breadcrumbs, section boundaries and page provenance.
- `build_outline` turns that index into the agent's map — headings when the
  document has them, pages when it doesn't. A PDF with no `section_header`
  is the common case, not the edge case, and a map is what makes the rest of
  the surface usable, so the page fallback is part of the contract.
- `resolve` / `section_refs` / `render_markdown` turn a `ref` back into text,
  provenance and markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from domain.navigation import (
    BoundingBox,
    OutlineNode,
    ResolvedElement,
    estimate_tokens,
    is_heading,
    is_readable,
)

if TYPE_CHECKING:
    from domain.ports import DocumentTreeReader

# Virtual refs for the page fallback. They are not docling `self_ref`s — the
# navigator synthesises them — but they round-trip through the same anchor
# grammar, so an agent handles both kinds without a special case.
PAGE_REF_PREFIX = "#/pages/"

# Docling containers whose children are structure, not prose: the reader
# walks into them rather than treating them as leaves.
_CONTAINER_LABELS = frozenset({"list", "group", "form_area", "key_value_area", "inline"})

_MAX_TITLE_LEN = 96


def page_ref(page: int) -> str:
    return f"{PAGE_REF_PREFIX}{page}"


def parse_page_ref(ref: str) -> int | None:
    """Return the page number of a virtual page ref, or None if it isn't one."""
    if not ref.startswith(PAGE_REF_PREFIX):
        return None
    try:
        return int(ref[len(PAGE_REF_PREFIX) :])
    except ValueError:
        return None


@dataclass(frozen=True)
class DocumentIndex:
    """Everything one walk of the parse can pre-compute.

    Built once per (document, version) read. Callers treat it as opaque and
    go through the module's functions.
    """

    by_ref: dict[str, dict[str, Any]]
    order: list[str]
    position: dict[str, int]
    heading_path: dict[str, list[str]]
    section_end: dict[str, int]
    # The page an element *starts* on — what a citation reports.
    page_of: dict[str, int]
    # Every page an element touches. An element that straddles a page break is
    # on both, and a "read page N" that only knew about starting pages would
    # silently drop the half of the paragraph the reader can actually see.
    pages_of: dict[str, frozenset[int]]
    bbox_of: dict[str, BoundingBox]
    inline_meta: dict[str, dict[str, Any]]
    page_numbers: list[int] = field(default_factory=list)
    page_sizes: dict[int, tuple[float, float]] = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return max(self.page_numbers) if self.page_numbers else 0


def build_index(doc_data: dict[str, Any], tree_reader: DocumentTreeReader) -> DocumentIndex:
    """Walk a parse once and pre-compute order, breadcrumbs and provenance."""
    skip_refs, inline_meta = tree_reader.build_collapse_index(doc_data)

    by_ref: dict[str, dict[str, Any]] = {}
    for _, item in tree_reader.iter_items(doc_data):
        ref = item.get("self_ref")
        if ref:
            by_ref[ref] = item

    order = [ref for ref in tree_reader.dfs_order(doc_data, skip_refs) if ref in by_ref]
    position = {ref: idx for idx, ref in enumerate(order)}

    heading_path: dict[str, list[str]] = {}
    section_end: dict[str, int] = {}
    stack: list[tuple[int, str, str]] = []  # (level, ref, title)

    for idx, ref in enumerate(order):
        item = by_ref[ref]
        label = _label_of(item)
        if is_heading(label):
            level = heading_level(item)
            while stack and stack[-1][0] >= level:
                _, closed, _ = stack.pop()
                section_end[closed] = idx
            heading_path[ref] = [title for _, _, title in stack]
            stack.append((level, ref, _title_of(item, inline_meta)))
        else:
            heading_path[ref] = [title for _, _, title in stack]
    while stack:
        _, closed, _ = stack.pop()
        section_end[closed] = len(order)

    page_sizes: dict[int, tuple[float, float]] = {}
    for page in tree_reader.iter_pages(doc_data):
        number = page.get("page_no")
        if number is None:
            continue
        width, height = page.get("width"), page.get("height")
        if width and height:
            page_sizes[int(number)] = (float(width), float(height))

    page_of: dict[str, int] = {}
    pages_of: dict[str, frozenset[int]] = {}
    bbox_of: dict[str, BoundingBox] = {}
    for ref, item in by_ref.items():
        provs = tree_reader.iter_provs(item)
        if not provs and ref in inline_meta:
            provs = inline_meta[ref].get("provs") or []
        located = [p for p in provs if p.get("page_no") is not None]
        if not located:
            continue
        first = located[0]
        page = int(first["page_no"])
        page_of[ref] = page
        pages_of[ref] = frozenset(int(p["page_no"]) for p in located)
        width, height = page_sizes.get(page, (None, None))
        bbox_of[ref] = BoundingBox(
            page=page,
            left=float(first.get("bbox_l", 0.0)),
            top=float(first.get("bbox_t", 0.0)),
            right=float(first.get("bbox_r", 0.0)),
            bottom=float(first.get("bbox_b", 0.0)),
            coord_origin=str(first.get("coord_origin") or "TOPLEFT"),
            page_width=width,
            page_height=height,
        )

    page_numbers = sorted(page_sizes) or sorted({p for pages in pages_of.values() for p in pages})

    return DocumentIndex(
        by_ref=by_ref,
        order=order,
        position=position,
        heading_path=heading_path,
        section_end=section_end,
        page_of=page_of,
        pages_of=pages_of,
        bbox_of=bbox_of,
        inline_meta=inline_meta,
        page_numbers=page_numbers,
        page_sizes=page_sizes,
    )


def heading_level(item: dict[str, Any]) -> int:
    """0 for the document title, >=1 for section headers (docling `level`)."""
    if _label_of(item) == "title":
        return 0
    try:
        return max(int(item.get("level") or 1), 1)
    except (TypeError, ValueError):
        return 1


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve(index: DocumentIndex, ref: str) -> ResolvedElement | None:
    """Resolve a `ref` (docling self_ref or virtual page ref) to an element."""
    page = parse_page_ref(ref)
    if page is not None:
        if index.page_numbers and page not in index.page_numbers:
            return None
        return ResolvedElement(ref=ref, label="page", text="", level=1, page=page)

    item = index.by_ref.get(ref)
    if item is None:
        return None
    label = _label_of(item)
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
    page = parse_page_ref(ref)
    if page is not None:
        return [r for r in index.order if page in index.pages_of.get(r, frozenset())]

    if ref not in index.position:
        return []
    start = index.position[ref]
    item = index.by_ref[ref]
    if is_heading(_label_of(item)):
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


def element_text(index: DocumentIndex, ref: str) -> str:
    """The readable text of one element — inline runs joined, tables rendered."""
    meta = index.inline_meta.get(ref)
    if meta and meta.get("text"):
        return str(meta["text"])

    item = index.by_ref.get(ref)
    if item is None:
        return ""
    label = _label_of(item)
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


def _render_table(item: dict[str, Any]) -> str:
    """Render a docling table as markdown; empty string when unreadable.

    Defensive by design: table payloads vary across docling versions, and a
    citation on a table is worth more than a perfectly formatted one.
    """
    try:
        rows = _table_rows(item.get("data") or {})
    except Exception:
        return ""
    if not rows:
        return ""
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


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OutlineDraft:
    """`build_outline`'s answer: the nodes plus how the map was cut."""

    nodes: list[OutlineNode]
    mode: str  # "sections" | "pages"
    total_est_tokens: int
    depth_limited: bool = False
    node_limited: bool = False


def build_outline(
    index: DocumentIndex,
    *,
    depth: int = 2,
    max_nodes: int = 200,
) -> OutlineDraft:
    """Project the index into a map.

    `mode` is `"sections"` when the parse carries headings, `"pages"` when it
    doesn't — a scanned PDF still gets a usable map.
    """
    total = sum(estimate_tokens(element_text(index, ref)) for ref in index.order)
    headings = [ref for ref in index.order if is_heading(_label_of(index.by_ref[ref]))]
    if not headings:
        nodes, node_limited = _page_nodes(index, max_nodes=max_nodes)
        return OutlineDraft(
            nodes=nodes, mode="pages", total_est_tokens=total, node_limited=node_limited
        )

    nodes, depth_limited, node_limited = _section_nodes(
        index, headings, depth=depth, max_nodes=max_nodes
    )
    return OutlineDraft(
        nodes=nodes,
        mode="sections",
        total_est_tokens=total,
        depth_limited=depth_limited,
        node_limited=node_limited,
    )


def _section_nodes(
    index: DocumentIndex,
    headings: list[str],
    *,
    depth: int,
    max_nodes: int,
) -> tuple[list[OutlineNode], bool, bool]:
    roots: list[OutlineNode] = []
    # Stack of (level, mutable children list) — the root sentinel is level -1
    # so any heading nests inside it, mirroring `ChunkService`'s doc tree.
    stack: list[tuple[int, list[OutlineNode]]] = [(-1, roots)]
    emitted = 0
    depth_limited = False
    node_limited = False

    for ref in headings:
        item = index.by_ref[ref]
        level = heading_level(item)
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()
        # A document `title` wraps everything without being a level a reader
        # thinks about, so it does not consume depth budget: `depth=2` means
        # chapters and their subsections, title or no title.
        nesting = sum(1 for open_level, _ in stack[1:] if open_level > 0)
        if nesting >= depth:
            # Deeper than requested: its tokens still count towards the
            # nearest emitted ancestor, so nothing is hidden from the budget.
            depth_limited = True
            continue
        if emitted >= max_nodes:
            node_limited = True
            break
        children: list[OutlineNode] = []
        node = OutlineNode(
            ref=ref,
            uri="",  # stamped by the service, which owns the version token
            title=_title_of(item, index.inline_meta),
            kind="section",
            level=level,
            page=index.page_of.get(ref),
            est_tokens=section_est_tokens(index, ref),
            child_count=_direct_child_headings(index, ref, level),
            children=children,
        )
        stack[-1][1].append(node)
        stack.append((level, children))
        emitted += 1

    return roots, depth_limited, node_limited


def _page_nodes(index: DocumentIndex, *, max_nodes: int) -> tuple[list[OutlineNode], bool]:
    pages = index.page_numbers or sorted({p for pages in index.pages_of.values() for p in pages})
    truncated = len(pages) > max_nodes
    nodes: list[OutlineNode] = []
    for page in pages[:max_nodes]:
        refs = [ref for ref in index.order if page in index.pages_of.get(ref, frozenset())]
        text = " ".join(element_text(index, ref) for ref in refs).strip()
        nodes.append(
            OutlineNode(
                ref=page_ref(page),
                uri="",
                title=_truncate(text) if text else f"Page {page}",
                kind="page",
                level=1,
                page=page,
                est_tokens=estimate_tokens(text),
                child_count=len(refs),
            )
        )
    return nodes, truncated


def section_est_tokens(index: DocumentIndex, ref: str) -> int:
    return sum(estimate_tokens(element_text(index, r)) for r in section_refs(index, ref))


def _direct_child_headings(index: DocumentIndex, ref: str, level: int) -> int:
    """Count the subsections that nest *directly* under `ref`.

    Not `level + 1`: docling derives heading levels from the document's visual
    hierarchy and routinely skips numbers (an h1 followed by h3s). The outline
    nests by relative depth — pop until the top of the stack is shallower — so
    counting by absolute level would publish `child_count: 0` next to a
    non-empty `children` list. The direct children are the headings at the
    *shallowest level present* inside the section.
    """
    start = index.position.get(ref)
    if start is None:
        return 0
    end = index.section_end.get(ref, start + 1)
    levels = [
        heading_level(index.by_ref[candidate])
        for candidate in index.order[start + 1 : end]
        if is_heading(_label_of(index.by_ref[candidate]))
    ]
    inner = [value for value in levels if value > level]
    if not inner:
        return 0
    shallowest = min(inner)
    return sum(1 for value in inner if value == shallowest)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


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


def _label_of(item: dict[str, Any]) -> str:
    return (item.get("label") or "text").lower()


def _title_of(item: dict[str, Any], inline_meta: dict[str, dict[str, Any]]) -> str:
    ref = item.get("self_ref") or ""
    meta = inline_meta.get(ref)
    raw = (meta or {}).get("text") or item.get("text") or ""
    title = str(raw).strip()
    if title:
        return _truncate(title)
    label = _label_of(item)
    return {"table": "Table", "picture": "Figure", "list": "List"}.get(label, label or "node")


def _truncate(text: str, max_len: int = _MAX_TITLE_LEN) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"
