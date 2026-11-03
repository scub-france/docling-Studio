"""The chunkset hash recorded when a document's chunks are pushed to a store.

Pushing a chunkset (`push_to_store`) writes it on the `chunk_pushes` row and on
the (document, store) `DocumentStoreLink`, and `GET
/api/documents/{id}/chunks/pushes` returns it (`chunksetHash`). It answers
"is the store in sync with the chunkset as it is now" without listing the
store's chunks.

The rule hashes, per chunk and in order: the id, the text and
`str(updated_at)`. Any edit therefore changes it, even one that leaves the
text as it was: a stored hash can only err towards "changed", never towards
"in sync".

Why this rule and not a content-only one. This module used to hold a
content-only `chunkset_hash` (text, page, headings; no ids, no dates) that
nothing called, while the service wrote the rule above. The hashes already
stored were all written by the service's rule, so that is the one kept when
the rule moved here (audit 0.7.4, 01 MAJ-1): switching rules would make every
stored hash differ from a fresh one on unchanged chunks, so the day a
comparison reads them, every existing link would look stale at once. Change
the inputs only as a deliberate, release-noted event.

Pure: in, out. No I/O, no randomness.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from domain.models import Chunk

# Between the fields of one chunk, and after each chunk: concatenating two
# chunks never hashes like one chunk with the joined text.
_FIELD_SEPARATOR = b"\x00"
_CHUNK_TERMINATOR = b"\x01"


def chunkset_hash(chunks: Iterable[Chunk]) -> str:
    """SHA-256 hex digest over (id, text, `str(updated_at)`) of each chunk, in order."""
    h = hashlib.sha256()
    for chunk in chunks:
        h.update(chunk.id.encode("utf-8"))
        h.update(_FIELD_SEPARATOR)
        h.update(chunk.text.encode("utf-8"))
        h.update(_FIELD_SEPARATOR)
        h.update(str(chunk.updated_at).encode("utf-8"))
        h.update(_CHUNK_TERMINATOR)
    return h.hexdigest()
