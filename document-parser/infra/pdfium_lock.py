"""The one lock every pdfium caller in the process takes.

pdfium is not thread-safe. Docling drives it from its own threads and guards
each call with a lock: when Docling is installed we share that lock, otherwise
(remote mode) the adapters share this module's own.
"""

from __future__ import annotations

import threading

try:  # pragma: no cover - which branch runs depends on the image
    from docling.utils.locks import pypdfium2_lock as pdfium_lock
except ImportError:  # pragma: no cover
    pdfium_lock = threading.Lock()

__all__ = ["pdfium_lock"]
