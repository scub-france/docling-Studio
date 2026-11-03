"""Local-disk adapter of the `FileStorage` port: the upload directory.

The uploaded PDFs live as files under one directory (`UPLOAD_DIR`). The
document records keep each file's absolute path; this adapter writes the
files, finds them again, and removes them only from inside that directory.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

# Written in fixed-size slices rather than handed to the OS in one piece.
_WRITE_CHUNK_SIZE = 64 * 1024


class LocalFileStorage:
    """`FileStorage` over a directory of the local filesystem."""

    def __init__(self, root: str) -> None:
        # Kept as configured (relative to the working directory when it is
        # relative) and resolved at each use, like the paths compared to it.
        self._root = root

    def save(self, content: bytes, *, suffix: str) -> str:
        os.makedirs(self._root, exist_ok=True)
        path = os.path.join(self._root, f"{uuid.uuid4()}{suffix}")
        with open(path, "wb") as f:
            for offset in range(0, len(content), _WRITE_CHUNK_SIZE):
                f.write(content[offset : offset + _WRITE_CHUNK_SIZE])
        return os.path.abspath(path)

    def exists(self, storage_path: str) -> bool:
        return Path(storage_path).is_file()

    def resolve(self, storage_path: str) -> str:
        """Docker records `/app/uploads/...`, while a worktree started on the
        host keeps the copied files under its own upload directory. Only the
        file's name is looked up there, so the rest of the recorded path
        cannot lead the lookup out of the storage."""
        path = Path(storage_path)
        if path.is_file():
            return str(path)
        fallback = Path(self._root).resolve() / path.name
        return str(fallback if fallback.is_file() else path)

    def delete(self, storage_path: str) -> None:
        # Both sides resolved, symlinks included: a recorded path that leads
        # out of the storage (`..`, a link) is judged by where it lands.
        real_path = os.path.realpath(storage_path)
        real_root = os.path.realpath(self._root)
        if real_path.startswith(real_root + os.sep) and os.path.exists(real_path):
            os.unlink(real_path)
        elif os.path.exists(storage_path):
            logger.warning("Refused to delete file outside upload dir: %s", storage_path)
