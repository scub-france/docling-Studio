"""Deterministic hashing for chunksets — substrate for auto-stale detection (#204).

A `chunkset_hash` summarises the content of a list of chunks for a
document. The hash is recorded on each `DocumentStoreLink` at push time
(#203 ships the column slot). When chunks change, recomputing the hash
and comparing against the stored value tells us whether the link has
gone stale.

Why a hash and not, say, an updated_at?
  - Idempotent re-pipelines on identical input bump `updated_at` without
    semantic change. A content hash is the only signal that survives
    that.
  - It is also content-addressed: two different docs that happen to have
    the same chunkset get the same hash. Useful for de-duplication
    further down the road.

Inputs and exclusions are pinned. Any change to the canonical inputs
re-flips every existing link to Stale once — that is a deliberate
release-note event, not a silent migration.

This module is pure: in / out. No I/O. No randomness. No dates.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from domain.value_objects import ChunkResult


# Byte separator inserted between chunks so concatenating two chunks does
# not yield the same hash as a single chunk with the joined text. \x1f is
# the Unicode "Information Separator One" — semantically appropriate and
# safe inside arbitrary text.
_CHUNK_SEPARATOR = b"\x1f"


def hash_chunkset(chunks: Iterable[ChunkResult]) -> str:
    """Return a deterministic SHA-256 hex digest over a chunkset.

    Hashed inputs (per chunk, in order):
      - text             (str)
      - source_page      (int | None)
      - headings         (list[str], order preserved)

    Excluded:
      - bboxes / doc_items   (rendering artefacts; do not affect retrieval)
      - token_count          (derived; unstable across tokenizers)

    The exclusion list is intentional. Bumping it changes every link's
    hash and triggers a one-time corpus-wide flip to `Stale`.
    """
    h = hashlib.sha256()
    for chunk in chunks:
        payload = {
            "t": chunk.text,
            "p": chunk.source_page,
            "h": list(chunk.headings or []),
        }
        h.update(_CHUNK_SEPARATOR)
        h.update(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    return h.hexdigest()
