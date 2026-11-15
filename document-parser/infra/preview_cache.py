"""Bounded, process-local cache for rendered PDF page images."""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.ports import PreviewImageKey


class PreviewCache:
    """Bounded in-memory implementation of the PreviewImageCache port."""

    def __init__(self, max_bytes: int = 64 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes
        self._bytes = 0
        self._images: OrderedDict[PreviewImageKey, bytes] = OrderedDict()
        self._lock = Lock()

    def get(self, key: PreviewImageKey) -> bytes | None:
        with self._lock:
            image = self._images.get(key)
            if image is not None:
                self._images.move_to_end(key)
            return image

    def put(self, key: PreviewImageKey, image: bytes) -> None:
        if len(image) > self._max_bytes:
            return
        with self._lock:
            previous = self._images.pop(key, None)
            if previous is not None:
                self._bytes -= len(previous)
            self._images[key] = image
            self._bytes += len(image)
            while self._bytes > self._max_bytes:
                _, evicted = self._images.popitem(last=False)
                self._bytes -= len(evicted)
