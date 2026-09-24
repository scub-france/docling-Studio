"""Tests for persistence repositories using a temporary SQLite database."""

from datetime import UTC, datetime

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Document
from domain.value_objects import DocumentLifecycleState
from persistence.analysis_repo import SqliteAnalysisRepository
from persistence.database import init_db
from persistence.document_repo import SqliteDocumentRepository


@pytest.fixture(autouse=True)
async def setup_db(monkeypatch, tmp_path):
    """Use a temp file SQLite database for all repo tests."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("persistence.database.DB_PATH", db_path)
    await init_db()
    yield


@pytest.fixture
def document_repo():
    return SqliteDocumentRepository()


@pytest.fixture
def analysis_repo():
    return SqliteAnalysisRepository()


class TestDocumentRepo:
    async def test_insert_and_find_by_id(self, document_repo):
        doc = Document(
            id="doc-1",
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024,
            storage_path="/tmp/test.pdf",
        )
        await document_repo.insert(doc)

        found = await document_repo.find_by_id("doc-1")
        assert found is not None
        assert found.id == "doc-1"
        assert found.filename == "test.pdf"
        assert found.file_size == 1024

    async def test_find_by_id_not_found(self, document_repo):
        found = await document_repo.find_by_id("nonexistent")
        assert found is None

    async def test_find_all(self, document_repo):
        for i in range(3):
            doc = Document(id=f"doc-{i}", filename=f"file{i}.pdf", storage_path=f"/tmp/{i}")
            await document_repo.insert(doc)

        all_docs = await document_repo.find_all()
        assert len(all_docs) == 3

    async def test_update_page_count(self, document_repo):
        doc = Document(id="doc-1", filename="test.pdf", storage_path="/tmp/test.pdf")
        await document_repo.insert(doc)

        await document_repo.update_page_count("doc-1", 10)

        updated = await document_repo.find_by_id("doc-1")
        assert updated.page_count == 10

    async def test_delete(self, document_repo):
        doc = Document(id="doc-1", filename="test.pdf", storage_path="/tmp/test.pdf")
        await document_repo.insert(doc)

        deleted = await document_repo.delete("doc-1")
        assert deleted is True

        found = await document_repo.find_by_id("doc-1")
        assert found is None

    async def test_delete_nonexistent(self, document_repo):
        deleted = await document_repo.delete("nonexistent")
        assert deleted is False

    async def test_default_lifecycle_state_is_uploaded(self, document_repo):
        """Fresh document round-trip preserves the default Uploaded state."""
        doc = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
        await document_repo.insert(doc)

        found = await document_repo.find_by_id("doc-1")
        assert found is not None
        assert found.lifecycle_state == DocumentLifecycleState.UPLOADED
        assert found.lifecycle_state_at is None

    async def test_update_lifecycle_persists_state_and_timestamp(self, document_repo):
        doc = Document(id="doc-1", filename="t.pdf", storage_path="/tmp/t.pdf")
        await document_repo.insert(doc)

        when = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
        await document_repo.update_lifecycle("doc-1", DocumentLifecycleState.PARSED, when)

        found = await document_repo.find_by_id("doc-1")
        assert found is not None
        assert found.lifecycle_state == DocumentLifecycleState.PARSED
        assert found.lifecycle_state_at is not None
        assert found.lifecycle_state_at == when

    async def test_lifecycle_state_round_trips_for_each_value(self, document_repo):
        """Every enum value must serialize cleanly into and out of SQLite."""
        when = datetime(2026, 4, 29, 12, 0, tzinfo=UTC)
        for value in DocumentLifecycleState:
            doc = Document(
                id=f"doc-{value.value}",
                filename="t.pdf",
                storage_path="/tmp/t.pdf",
                lifecycle_state=value,
                lifecycle_state_at=when,
            )
            await document_repo.insert(doc)

            found = await document_repo.find_by_id(f"doc-{value.value}")
            assert found is not None
            assert found.lifecycle_state == value

    async def test_find_all_filters_on_the_filename_case_insensitively(self, document_repo):
        for i, name in enumerate(["Contrat.PDF", "facture.pdf", "contrat-annexe.pdf"]):
            await document_repo.insert(Document(id=f"doc-{i}", filename=name, storage_path="/x"))
        found = await document_repo.find_all(filename_like="CONTRAT")
        assert sorted(d.filename for d in found) == ["Contrat.PDF", "contrat-annexe.pdf"]

    async def test_find_all_matches_like_wildcards_literally(self, document_repo):
        for i, name in enumerate(
            ["taux_2024.pdf", "taux-2024.pdf", "remise 50%.pdf", "remise 505.pdf"]
        ):
            await document_repo.insert(Document(id=f"doc-{i}", filename=name, storage_path="/x"))
        assert [d.filename for d in await document_repo.find_all(filename_like="_2024")] == [
            "taux_2024.pdf"
        ]
        assert [d.filename for d in await document_repo.find_all(filename_like="50%")] == [
            "remise 50%.pdf"
        ]


class TestParseLookups:
    """The reads that never load a whole analysis row."""

    async def _parsed(self, analysis_repo, job_id: str, doc_id: str, *, json: str | None):
        job = AnalysisJob(id=job_id, document_id=doc_id)
        await analysis_repo.insert(job)
        job.mark_running()
        job.mark_completed(markdown="", html="", pages_json="[]", document_json=json)
        await analysis_repo.update_status(job)

    async def _docs(self, document_repo, *ids: str):
        for doc_id in ids:
            await document_repo.insert(
                Document(id=doc_id, filename=f"{doc_id}.pdf", storage_path="/x")
            )

    async def test_latest_parsed_ids_takes_each_documents_newest_parse(
        self, document_repo, analysis_repo
    ):
        await self._docs(document_repo, "doc-1", "doc-2", "doc-3")
        await self._parsed(analysis_repo, "a-old", "doc-1", json="{}")
        await self._parsed(analysis_repo, "a-new", "doc-1", json="{}")
        await self._parsed(analysis_repo, "b-only", "doc-2", json="{}")
        await self._parsed(analysis_repo, "c-empty", "doc-3", json=None)
        latest = await analysis_repo.latest_parsed_ids(["doc-1", "doc-2", "doc-3"])
        assert latest == {"doc-1": "a-new", "doc-2": "b-only"}

    async def test_parsed_document_id_is_none_without_a_parse(self, document_repo, analysis_repo):
        await self._docs(document_repo, "doc-1")
        await self._parsed(analysis_repo, "parsed", "doc-1", json="{}")
        await self._parsed(analysis_repo, "empty", "doc-1", json=None)
        assert await analysis_repo.parsed_document_id("parsed") == "doc-1"
        assert await analysis_repo.parsed_document_id("empty") is None
        assert await analysis_repo.parsed_document_id("missing") is None

    async def test_parse_json_reads_the_stored_parse(self, document_repo, analysis_repo):
        await self._docs(document_repo, "doc-1")
        await self._parsed(analysis_repo, "parsed", "doc-1", json='{"texts": []}')
        assert await analysis_repo.parse_json("parsed") == '{"texts": []}'
        assert await analysis_repo.parse_json("missing") is None


class TestAnalysisRepo:
    async def _insert_doc(self, document_repo):
        doc = Document(id="doc-1", filename="test.pdf", storage_path="/tmp/test.pdf")
        await document_repo.insert(doc)
        return doc

    async def test_insert_and_find_by_id(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        job = AnalysisJob(id="job-1", document_id="doc-1")
        await analysis_repo.insert(job)

        found = await analysis_repo.find_by_id("job-1")
        assert found is not None
        assert found.id == "job-1"
        assert found.document_id == "doc-1"
        assert found.status == AnalysisStatus.PENDING
        assert found.document_filename == "test.pdf"

    async def test_find_by_id_not_found(self, analysis_repo):
        found = await analysis_repo.find_by_id("nonexistent")
        assert found is None

    async def test_find_all(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        for i in range(3):
            job = AnalysisJob(id=f"job-{i}", document_id="doc-1")
            await analysis_repo.insert(job)

        all_jobs = await analysis_repo.find_all()
        assert len(all_jobs) == 3

    async def test_update_status(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        job = AnalysisJob(id="job-1", document_id="doc-1")
        await analysis_repo.insert(job)

        job.mark_running()
        await analysis_repo.update_status(job)

        found = await analysis_repo.find_by_id("job-1")
        assert found.status == AnalysisStatus.RUNNING
        assert isinstance(found.started_at, datetime)

    async def test_update_status_completed(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        job = AnalysisJob(id="job-1", document_id="doc-1")
        await analysis_repo.insert(job)

        job.mark_running()
        job.mark_completed(markdown="# Test", html="<h1>Test</h1>", pages_json="[]")
        await analysis_repo.update_status(job)

        found = await analysis_repo.find_by_id("job-1")
        assert found.status == AnalysisStatus.COMPLETED
        assert found.content_markdown == "# Test"
        assert found.content_html == "<h1>Test</h1>"
        assert found.pages_json == "[]"

    async def test_delete(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        job = AnalysisJob(id="job-1", document_id="doc-1")
        await analysis_repo.insert(job)

        deleted = await analysis_repo.delete("job-1")
        assert deleted is True

        found = await analysis_repo.find_by_id("job-1")
        assert found is None

    async def test_delete_nonexistent(self, analysis_repo):
        deleted = await analysis_repo.delete("nonexistent")
        assert deleted is False

    async def test_find_latest_completed_by_document(self, document_repo, analysis_repo):
        """Reasoning tunnel helper: latest COMPLETED analysis with document_json."""
        await self._insert_doc(document_repo)

        # Each job must be insert()'d before update_status can touch it.
        # Scenarios: pending (excluded — not COMPLETED), old completed without
        # document_json (excluded — NULL json), recent completed with
        # document_json (the one we want), running (excluded).
        pending = AnalysisJob(id="job-pending", document_id="doc-1")
        await analysis_repo.insert(pending)

        old_completed = AnalysisJob(id="job-old", document_id="doc-1")
        await analysis_repo.insert(old_completed)
        old_completed.mark_running()
        old_completed.mark_completed(markdown="", html="", pages_json="[]")
        await analysis_repo.update_status(old_completed)

        latest = AnalysisJob(id="job-latest", document_id="doc-1")
        await analysis_repo.insert(latest)
        latest.mark_running()
        latest.mark_completed(
            markdown="md",
            html="<p/>",
            pages_json="[]",
            document_json='{"body":{"children":[]},"texts":[]}',
        )
        await analysis_repo.update_status(latest)

        running = AnalysisJob(id="job-running", document_id="doc-1")
        await analysis_repo.insert(running)
        running.mark_running()
        await analysis_repo.update_status(running)

        found = await analysis_repo.find_latest_completed_by_document("doc-1")
        assert found is not None
        assert found.id == "job-latest"
        assert found.document_json == '{"body":{"children":[]},"texts":[]}'

    async def test_find_latest_completed_by_document_none(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        found = await analysis_repo.find_latest_completed_by_document("doc-1")
        assert found is None

    async def test_find_latest_completed_prefers_newest_completed_even_without_json(
        self, document_repo, analysis_repo
    ):
        await self._insert_doc(document_repo)

        older_with_json = AnalysisJob(id="job-json", document_id="doc-1")
        await analysis_repo.insert(older_with_json)
        older_with_json.mark_running()
        older_with_json.mark_completed(
            markdown="old",
            html="<p>old</p>",
            pages_json="[]",
            document_json='{"v":1}',
        )
        await analysis_repo.update_status(older_with_json)

        latest_no_json = AnalysisJob(id="job-latest", document_id="doc-1")
        await analysis_repo.insert(latest_no_json)
        latest_no_json.mark_running()
        latest_no_json.mark_completed(
            markdown="latest",
            html="<p>latest</p>",
            pages_json="[]",
        )
        await analysis_repo.update_status(latest_no_json)

        found = await analysis_repo.find_latest_completed("doc-1")

        assert found is not None
        assert found.id == "job-latest"
        assert found.content_markdown == "latest"

    async def test_delete_by_document(self, document_repo, analysis_repo):
        await self._insert_doc(document_repo)
        for i in range(3):
            job = AnalysisJob(id=f"job-{i}", document_id="doc-1")
            await analysis_repo.insert(job)

        count = await analysis_repo.delete_by_document("doc-1")
        assert count == 3

        all_jobs = await analysis_repo.find_all()
        assert len(all_jobs) == 0
