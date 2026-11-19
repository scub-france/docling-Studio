"""Tests for `LocalDocumentFileStore`, the `DocumentFileStore` adapter.

The delete guard is security-relevant: a stored path comes from the database,
and only a file inside the upload directory may ever be removed.
"""

from __future__ import annotations

import logging
import os
from unittest.mock import patch

import pytest

from domain.ports import DocumentFileStore
from infra.document_file_store import LocalDocumentFileStore

_LOGGER = "infra.document_file_store"


def _logged(caplog) -> list[tuple[str, str]]:
    return [(r.levelname, r.getMessage()) for r in caplog.records if r.name == _LOGGER]


def test_adapter_satisfies_its_port(tmp_path):
    assert isinstance(LocalDocumentFileStore(str(tmp_path)), DocumentFileStore)


class TestSave:
    def test_writes_the_content_and_returns_its_absolute_path(self, tmp_path):
        uploads = tmp_path / "uploads"  # not created yet: `save` makes it
        content = b"%PDF-1.4 " + os.urandom(200 * 1024)  # several write chunks

        stored = LocalDocumentFileStore(str(uploads)).save("abc.pdf", content)

        assert stored == os.path.abspath(uploads / "abc.pdf")
        with open(stored, "rb") as f:
            assert f.read() == content

    def test_a_relative_upload_dir_still_gives_an_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        stored = LocalDocumentFileStore("uploads").save("abc.pdf", b"%PDF")

        assert stored == str(tmp_path / "uploads" / "abc.pdf")


class TestDiscard:
    def test_removes_the_file(self, tmp_path):
        stored = tmp_path / "abc.pdf"
        stored.write_bytes(b"%PDF")

        LocalDocumentFileStore(str(tmp_path)).discard(str(stored))

        assert not stored.exists()

    def test_raises_when_it_cannot(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LocalDocumentFileStore(str(tmp_path)).discard(str(tmp_path / "gone.pdf"))


class TestDeleteConfinement:
    @pytest.fixture
    def uploads(self, tmp_path):
        path = tmp_path / "uploads"
        path.mkdir()
        return path

    def test_deletes_a_file_inside_the_upload_dir(self, uploads, caplog):
        stored = uploads / "doc.pdf"
        stored.write_bytes(b"%PDF")

        with caplog.at_level(logging.INFO, logger=_LOGGER):
            LocalDocumentFileStore(str(uploads)).delete(str(stored))

        assert not stored.exists()
        assert _logged(caplog) == []

    def test_refuses_a_file_outside_the_upload_dir_and_logs_it(self, uploads, tmp_path, caplog):
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")

        with caplog.at_level(logging.INFO, logger=_LOGGER):
            LocalDocumentFileStore(str(uploads)).delete(str(secret))

        assert secret.exists()
        assert _logged(caplog) == [
            ("WARNING", f"Refused to delete file outside upload dir: {secret}")
        ]

    def test_refuses_a_path_that_climbs_out_with_dot_dot(self, uploads, tmp_path, caplog):
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        climbing = f"{uploads}{os.sep}..{os.sep}secret.txt"

        with caplog.at_level(logging.INFO, logger=_LOGGER):
            LocalDocumentFileStore(str(uploads)).delete(climbing)

        assert secret.exists()
        assert _logged(caplog) == [
            ("WARNING", f"Refused to delete file outside upload dir: {climbing}")
        ]

    def test_refuses_a_sibling_dir_sharing_the_prefix(self, uploads, tmp_path):
        sibling = tmp_path / "uploads-other"
        sibling.mkdir()
        victim = sibling / "doc.pdf"
        victim.write_bytes(b"%PDF")

        LocalDocumentFileStore(str(uploads)).delete(str(victim))

        assert victim.exists()

    def test_refuses_a_symlink_inside_that_points_outside(self, uploads, tmp_path, caplog):
        secret = tmp_path / "secret.txt"
        secret.write_bytes(b"secret")
        link = uploads / "doc.pdf"
        link.symlink_to(secret)

        with caplog.at_level(logging.INFO, logger=_LOGGER):
            LocalDocumentFileStore(str(uploads)).delete(str(link))

        assert secret.exists()
        assert link.is_symlink()
        assert _logged(caplog) == [
            ("WARNING", f"Refused to delete file outside upload dir: {link}")
        ]

    def test_a_missing_file_is_no_error(self, uploads, caplog):
        with caplog.at_level(logging.INFO, logger=_LOGGER):
            LocalDocumentFileStore(str(uploads)).delete(str(uploads / "gone.pdf"))

        assert _logged(caplog) == []

    def test_a_file_removed_meanwhile_is_logged_as_info(self, uploads, caplog):
        stored = uploads / "doc.pdf"
        stored.write_bytes(b"%PDF")

        with (
            caplog.at_level(logging.INFO, logger=_LOGGER),
            patch("infra.document_file_store.os.unlink", side_effect=FileNotFoundError),
        ):
            LocalDocumentFileStore(str(uploads)).delete(str(stored))

        assert _logged(caplog) == [("INFO", f"File already removed: {stored}")]

    def test_permission_denied_is_logged_as_an_error(self, uploads, caplog):
        stored = uploads / "doc.pdf"
        stored.write_bytes(b"%PDF")

        with (
            caplog.at_level(logging.INFO, logger=_LOGGER),
            patch("infra.document_file_store.os.unlink", side_effect=PermissionError),
        ):
            LocalDocumentFileStore(str(uploads)).delete(str(stored))

        assert stored.exists()
        assert _logged(caplog) == [("ERROR", f"Permission denied deleting file: {stored}")]

    def test_another_os_error_is_logged_as_a_warning(self, uploads, caplog):
        stored = uploads / "doc.pdf"
        stored.write_bytes(b"%PDF")

        with (
            caplog.at_level(logging.INFO, logger=_LOGGER),
            patch("infra.document_file_store.os.unlink", side_effect=OSError("busy")),
        ):
            LocalDocumentFileStore(str(uploads)).delete(str(stored))

        assert stored.exists()
        assert _logged(caplog) == [("WARNING", f"Could not delete file: {stored}")]


class TestHasFile:
    def test_a_regular_file(self, tmp_path):
        stored = tmp_path / "doc.pdf"
        stored.write_bytes(b"%PDF")

        assert LocalDocumentFileStore(str(tmp_path)).has_file(str(stored)) is True

    def test_a_missing_file_or_a_directory(self, tmp_path):
        store = LocalDocumentFileStore(str(tmp_path))

        assert store.has_file(str(tmp_path / "gone.pdf")) is False
        assert store.has_file(str(tmp_path)) is False


class TestResolve:
    def test_keeps_a_path_that_exists(self, tmp_path):
        stored = tmp_path / "elsewhere" / "doc.pdf"
        stored.parent.mkdir()
        stored.write_bytes(b"%PDF")

        assert LocalDocumentFileStore(str(tmp_path)).resolve(str(stored)) == str(stored)

    def test_resolves_docker_upload_path_from_local_worktree(self, tmp_path):
        local_file = tmp_path / "stored.pdf"
        local_file.write_bytes(b"%PDF-1.4")

        resolved = LocalDocumentFileStore(str(tmp_path)).resolve("/app/uploads/stored.pdf")

        assert resolved == str(local_file.resolve())

    def test_keeps_the_original_path_when_neither_exists(self, tmp_path):
        resolved = LocalDocumentFileStore(str(tmp_path)).resolve("/app/uploads/gone.pdf")

        assert resolved == "/app/uploads/gone.pdf"


class TestReadFingerprint:
    def test_size_and_modification_time(self, tmp_path):
        stored = tmp_path / "doc.pdf"
        stored.write_bytes(b"%PDF-1.4")

        size, mtime_ns = LocalDocumentFileStore(str(tmp_path)).read_fingerprint(str(stored))

        assert (size, mtime_ns) == (8, stored.stat().st_mtime_ns)

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LocalDocumentFileStore(str(tmp_path)).read_fingerprint(str(tmp_path / "gone.pdf"))
