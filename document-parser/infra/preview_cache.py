"""Bounded, process-local cache for rendered PDF page images.

The server render is the fallback behind PDF.js, and the browser keeps each
image (`Cache-Control: immutable`): the cache only spares re-rendering the
few pages several viewers ask for. Read and written from the event loop
only, so it needs no lock.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.ports import PreviewImageKey


class PreviewCache:
    """Bounded in-memory implementation of the PreviewImageCache port."""

    def __init__(self, max_bytes: int = 16 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes
        self._bytes = 0
        self._images: OrderedDict[PreviewImageKey, bytes] = OrderedDict()

    def get(self, key: PreviewImageKey) -> bytes | None:
        image = self._images.get(key)
        if image is not None:
            self._images.move_to_end(key)
        return image

    def put(self, key: PreviewImageKey, image: bytes) -> None:
        if len(image) > self._max_bytes:
            return
        previous = self._images.pop(key, None)
        if previous is not None:
            self._bytes -= len(previous)
        self._images[key] = image
        self._bytes += len(image)
        while self._bytes > self._max_bytes:
            _, evicted = self._images.popitem(last=False)
            self._bytes -= len(evicted)
