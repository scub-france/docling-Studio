"""The call recipe, as a tool a lost model can ask for.

The protocol already lives in three places — the server instructions, every
tool description, and the `next_step` on every result — and none of them is
callable. That is fine for a frontier model and wrong for a small one: the
instructions may never reach it (a host is free to drop them), the
descriptions compete with each other, and `next_step` arrives *after* the
mistake. A zero-argument tool is the one shape a weak model reliably gets
right, so this is the recipe it can go and fetch.

The economics are the point of the split. A tool *description* is re-sent on
every turn, so this one is two sentences. The *body* is paid only when the
tool is called, which is exactly when a model needs it — so the body is
generous where it helps: one literal worked example, because a small model
copies a pattern far more reliably than it follows a rule.

Text, not a dataclass: there is nothing here for a machine to parse, and a
JSON envelope would only add tokens to something a model reads as prose.
"""

from __future__ import annotations

# Read on every turn — keep it to what makes a stuck model reach for it.
DESCRIPTION = (
    "Read this first, before your first document read or right after a "
    "docling-studio tool failed: the exact call order, the id rules, and a "
    "worked example."
)

# Paid only when called. Ordered the way the flow runs, then the rules that
# are actually broken in practice, then the example that carries the shapes.
RECIPE = """\
Call these tools in this order. One call at a time; wait for each result.

1. find_documents {"query":"<a word from the filename>"}
   -> documents[]. Keep documents[N].document_id.
      A null version_id means the document was never parsed: say so and stop.

2. get_outline {"document_id":"<from step 1>"}
   -> entries[]. Each carries ref, title and est_tokens — the cost of reading
      that entry and everything under it.
      Pick the ONE entry whose title answers the question. A very small
      est_tokens means there is little text there: take its parent, or the
      sibling that carries the content.

3. read_element {"document_id":"<step 1>","ref":"<step 2>"}
   -> the text is in content, the anchors are in citations[].
      If truncated is true, call again adding {"cursor":"<next_cursor>"}.

4. verify_citation {"uri":"<citations[N].uri from step 3>","quote":"<the exact sentence you will publish>"}
   -> valid true means you may publish it. Otherwise fix the quote or drop the claim.

RULES
- Never invent an id. document_id, version_id, ref and uri are copied
  character for character out of an earlier result. You never build one.
- Your host may prefix these names (mcp__docling-studio__find_documents,
  docling-studio:find_documents...). Call each one by the exact name your
  own tool list shows, not by the bare name written here.
- Cite with citations[N].uri from read_element, never the uri you read with.
- One section at a time. Never read a whole document.
- On an error, read it: it says what to do. Never repeat a call unchanged.
- If nothing names a document, ask which one before calling anything.
- If the document does not answer, say so. Do not fill the gap from memory.
- Asked to *show* or *point at* a passage rather than describe it: call
  show_citation, then give the reader the deep_link it returns.
- Ignore the other tools unless the user asks for them.

EXAMPLE
find_documents {"query":"contract"}
  -> documents[0].document_id = "doc-1"
get_outline {"document_id":"doc-1"}
  -> entries[3] = {"ref":"#/texts/91","title":"Article 12","est_tokens":340}
read_element {"document_id":"doc-1","ref":"#/texts/91"}
  -> citations[0].uri = "dstudio://doc/doc-1@an-1#/texts/91"
verify_citation {"uri":"dstudio://doc/doc-1@an-1#/texts/91","quote":"three months' notice"}
  -> valid = true
"""
