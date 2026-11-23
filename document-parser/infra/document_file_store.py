"""Uploaded document files on the local disk — the `DocumentFileStore` port's adapter.

Every filesystem call the document use cases need lives here, so the services
above it only handle the `storage_path` strings a `Document` persists.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_WRITE_CHUNK_SIZE = 64 * 1024  # 64 KB chunks for streaming writes


class LocalDocumentFileStore:
    """Adapter for the `DocumentFileStore` port, rooted at one upload directory."""

    def __init__(self, upload_dir: str) -> None:
        self._upload_dir = upload_dir

    def save(self, file_name: str, content: bytes) -> str:
        # Fixed-size chunks keep the write's peak memory low on large uploads.
        file_path = os.path.join(self._upload_dir, file_name)
        os.makedirs(self._upload_dir, exist_ok=True)
        with open(file_path, "wb") as f:
            for offset in range(0, len(content), _WRITE_CHUNK_SIZE):
                f.write(content[offset : offset + _WRITE_CHUNK_SIZE])
        return os.path.abspath(file_path)

    def discard(self, storage_path: str) -> None:
        os.unlink(storage_path)

    def delete(self, storage_path: str) -> None:
        # The path comes from the database: only ever delete inside the
        # upload directory, after resolving symlinks and `..` segments.
        try:
            real_path = os.path.realpath(storage_path)
            real_upload_dir = os.path.realpath(self._upload_dir)
            if real_path.startswith(real_upload_dir + os.sep) and os.path.exists(real_path):
                os.unlink(real_path)
            elif os.path.exists(storage_path):
                logger.warning("Refused to delete file outside upload dir: %s", storage_path)
        except FileNotFoundError:
            logger.info("File already removed: %s", storage_path)
        except PermissionError:
            logger.error("Permission denied deleting file: %s", storage_path)
        except OSError:
            logger.warning("Could not delete file: %s", storage_path, exc_info=True)

    def has_file(self, storage_path: str) -> bool:
        return Path(storage_path).is_file()

    def resolve(self, storage_path: str) -> str:
        # Docker records `/app/uploads/...`, while a worktree started directly
        # on the host stores the copied files under its configured upload dir.
        # Keep the original path when it exists; otherwise only fall back to
        # its basename inside that directory.
        path = Path(storage_path)
        if path.is_file():
            return str(path)
        fallback = Path(self._upload_dir).resolve() / path.name
        return str(fallback if fallback.is_file() else path)

    def read_fingerprint(self, storage_path: str) -> tuple[int, int]:
        stat = Path(storage_path).stat()
        return stat.st_size, stat.st_mtime_ns
