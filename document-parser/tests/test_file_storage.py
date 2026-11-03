"""The local `FileStorage` adapter: where an upload is written, how a recorded
path is found again, and what a removal may touch.

Real files under `tmp_path`: the adapter is the disk, so there is nothing to
fake. The service-level policy (what a failed removal means) is tested in
`test_document_service.py`.
"""

from __future__ import annotations

import logging
import os

import pytest

from domain.ports import FileStorage
from infra.file_storage import LocalFileStorage


@pytest.fixture
def uploads(tmp_path):
    return tmp_path / "uploads"


@pytest.fixture
def storage(uploads):
    return LocalFileStorage(str(uploads))


def test_implements_the_port(storage):
    assert isinstance(storage, FileStorage)


class TestSave:
    def test_writes_the_content_under_a_fresh_name_in_the_storage(self, storage, uploads):
        content = b"%PDF-1.4 " + os.urandom(200_000)  # several write slices

        first = storage.save(content, suffix=".pdf")
        second = storage.save(content, suffix=".pdf")

        assert first != second
        for path in (first, second):
            assert os.path.isabs(path)
            assert os.path.dirname(path) == str(uploads)
            assert path.endswith(".pdf")
            with open(path, "rb") as f:
                assert f.read() == content

    def test_creates_the_storage_directory(self, storage, uploads):
        assert not uploads.exists()

        storage.save(b"x", suffix=".pdf")

        assert uploads.is_dir()

    def test_a_relative_root_gives_an_absolute_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        path = LocalFileStorage("./uploads").save(b"x", suffix=".pdf")

        assert path == os.path.join(str(tmp_path), "uploads", os.path.basename(path))


class TestExists:
    def test_reads_the_path_as_recorded(self, storage, uploads):
        stored = storage.save(b"x", suffix=".pdf")

        assert storage.exists(stored)
        assert not storage.exists(str(uploads / "gone.pdf"))
        # The fallback by name is for reading, not for this check.
        assert not storage.exists("/app/uploads/" + os.path.basename(stored))

    def test_a_directory_is_not_a_stored_file(self, storage, tmp_path):
        assert not storage.exists(str(tmp_path))


class TestResolve:
    def test_keeps_a_recorded_path_that_holds_a_file(self, storage, tmp_path):
        elsewhere = tmp_path / "elsewhere.pdf"
        elsewhere.write_bytes(b"x")

        assert storage.resolve(str(elsewhere)) == str(elsewhere)

    def test_finds_a_docker_path_in_the_local_storage_by_its_name(self, storage, uploads):
        uploads.mkdir()
        (uploads / "stored.pdf").write_bytes(b"x")

        assert storage.resolve("/app/uploads/stored.pdf") == str(uploads / "stored.pdf")

    def test_leaves_a_path_found_nowhere_unchanged(self, storage):
        assert storage.resolve("/app/uploads/gone.pdf") == "/app/uploads/gone.pdf"

    def test_the_fallback_looks_up_the_name_only(self, storage, uploads, tmp_path):
        """The directories of the recorded path never lead the lookup out."""
        uploads.mkdir()
        (tmp_path / "secret.pdf").write_bytes(b"x")

        assert storage.resolve("/app/uploads/../secret.pdf") == "/app/uploads/../secret.pdf"


class TestDelete:
    def test_removes_a_stored_file(self, storage):
        stored = storage.save(b"x", suffix=".pdf")

        storage.delete(stored)

        assert not os.path.exists(stored)

    def test_a_file_already_gone_is_not_an_error(self, storage, uploads):
        uploads.mkdir()

        storage.delete(str(uploads / "gone.pdf"))

    def test_refuses_a_file_outside_the_storage(self, storage, uploads, tmp_path, caplog):
        uploads.mkdir()
        outside = tmp_path / "secret.txt"
        outside.write_bytes(b"secret")

        with caplog.at_level(logging.WARNING, logger="infra.file_storage"):
            storage.delete(str(outside))

        assert outside.exists()
        assert "Refused to delete file outside upload dir" in caplog.text

    def test_refuses_a_path_that_climbs_out_with_dot_dot(self, storage, uploads, tmp_path):
        uploads.mkdir()
        outside = tmp_path / "secret.txt"
        outside.write_bytes(b"secret")

        storage.delete(str(uploads / ".." / "secret.txt"))

        assert outside.exists()

    def test_refuses_a_symlink_that_leads_out(self, storage, uploads, tmp_path):
        uploads.mkdir()
        outside = tmp_path / "secret.txt"
        outside.write_bytes(b"secret")
        link = uploads / "link.pdf"
        link.symlink_to(outside)

        storage.delete(str(link))

        assert outside.exists()

    def test_refuses_a_sibling_whose_name_extends_the_storage(self, storage, uploads, tmp_path):
        """`/x/uploads-old/f` starts with `/x/uploads` but is not inside it."""
        uploads.mkdir()
        sibling = tmp_path / "uploads-old"
        sibling.mkdir()
        (sibling / "f.pdf").write_bytes(b"x")

        storage.delete(str(sibling / "f.pdf"))

        assert (sibling / "f.pdf").exists()

    def test_a_failed_removal_raises(self, storage, monkeypatch):
        stored = storage.save(b"x", suffix=".pdf")

        def denied(path):
            raise PermissionError(path)

        monkeypatch.setattr(os, "unlink", denied)

        with pytest.raises(PermissionError):
            storage.delete(stored)


def test_the_composition_root_stores_under_upload_dir(monkeypatch, tmp_path):
    """Upload, preview, deletion and the PDF export share one storage, over
    `UPLOAD_DIR`."""
    from dataclasses import replace
    from unittest.mock import AsyncMock

    from bootstrap import factories

    monkeypatch.setattr(
        factories, "settings", replace(factories.settings, upload_dir=str(tmp_path))
    )

    storage = factories.build_file_storage()
    service = factories.build_document_service(AsyncMock(), AsyncMock())

    assert isinstance(storage, LocalFileStorage)
    assert os.path.dirname(storage.save(b"x", suffix=".pdf")) == str(tmp_path)
    assert isinstance(service._files, LocalFileStorage)
