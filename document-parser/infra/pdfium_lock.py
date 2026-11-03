"""The one lock every pdfium call in the process takes.

pdfium is not thread-safe. Docling drives it from its own threads during a
local analysis and guards it with one process-wide lock; the adapters here
take that same lock when Docling is installed, and a lock of their own when it
is not (the remote-engine image), so two requests never open a PDF at once.

Not re-entrant: hold it around one pdfium document, open to close, and never
call another adapter while holding it.
"""

from __future__ import annotations

import threading

try:  # pragma: no cover - which branch runs depends on the image
    from docling.utils.locks import pypdfium2_lock as pdfium_lock
except ImportError:  # pragma: no cover
    pdfium_lock = threading.Lock()

__all__ = ["pdfium_lock"]
