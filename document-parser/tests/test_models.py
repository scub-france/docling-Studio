"""Tests for domain models."""

from datetime import datetime

import pytest

from domain.models import AnalysisJob, AnalysisStatus, Document


class TestDocument:
    def test_default_values(self):
        doc = Document()
        assert doc.id  # auto-generated UUID
        assert doc.filename == ""
        assert doc.content_type is None
        assert doc.file_size is None
        assert doc.page_count is None
        assert doc.storage_path == ""
        assert isinstance(doc.created_at, datetime)

    def test_custom_values(self):
        doc = Document(
            id="doc-1",
            filename="test.pdf",
            content_type="application/pdf",
            file_size=1024,
            page_count=5,
            storage_path="/tmp/test.pdf",
        )
        assert doc.id == "doc-1"
        assert doc.filename == "test.pdf"
        assert doc.file_size == 1024
        assert doc.page_count == 5

    def test_unique_ids(self):
        d1 = Document()
        d2 = Document()
        assert d1.id != d2.id


class TestAnalysisJob:
    def test_default_values(self):
        job = AnalysisJob()
        assert job.id
        assert job.document_id == ""
        assert job.status == AnalysisStatus.PENDING
        assert job.content_markdown is None
        assert job.content_html is None
        assert job.pages_json is None
        assert job.error_message is None
        assert job.started_at is None
        assert job.completed_at is None

    def test_mark_running(self):
        job = AnalysisJob()
        assert job.started_at is None

        job.mark_running()

        assert job.status == AnalysisStatus.RUNNING
        assert isinstance(job.started_at, datetime)

    def test_mark_completed(self):
        job = AnalysisJob()
        job.mark_running()

        job.mark_completed(
            markdown="# Title",
            html="<h1>Title</h1>",
            pages_json='[{"page": 1}]',
        )

        assert job.status == AnalysisStatus.COMPLETED
        assert job.content_markdown == "# Title"
        assert job.content_html == "<h1>Title</h1>"
        assert job.pages_json == '[{"page": 1}]'
        assert isinstance(job.completed_at, datetime)
        assert job.completed_at >= job.started_at

    def test_mark_failed(self):
        job = AnalysisJob()
        job.mark_running()

        job.mark_failed("Something went wrong")

        assert job.status == AnalysisStatus.FAILED
        assert job.error_message == "Something went wrong"
        assert isinstance(job.completed_at, datetime)
        assert job.completed_at >= job.started_at

    def test_status_transitions(self):
        """Test full lifecycle: PENDING -> RUNNING -> COMPLETED."""
        job = AnalysisJob()
        assert job.status == AnalysisStatus.PENDING

        job.mark_running()
        assert job.status == AnalysisStatus.RUNNING

        job.mark_completed(markdown="md", html="html", pages_json="[]")
        assert job.status == AnalysisStatus.COMPLETED


class TestAnalysisJobGuardClauses:
    """Guard clauses prevent invalid state transitions."""

    def test_mark_running_from_running_raises(self):
        job = AnalysisJob()
        job.mark_running()
        with pytest.raises(ValueError, match="Cannot mark as RUNNING"):
            job.mark_running()

    def test_mark_running_from_completed_raises(self):
        job = AnalysisJob()
        job.mark_running()
        job.mark_completed(markdown="", html="", pages_json="[]")
        with pytest.raises(ValueError, match="Cannot mark as RUNNING"):
            job.mark_running()

    def test_mark_running_from_failed_raises(self):
        job = AnalysisJob()
        job.mark_failed("err")
        with pytest.raises(ValueError, match="Cannot mark as RUNNING"):
            job.mark_running()

    def test_mark_completed_from_pending_raises(self):
        job = AnalysisJob()
        with pytest.raises(ValueError, match="Cannot mark as COMPLETED"):
            job.mark_completed(markdown="", html="", pages_json="[]")

    def test_mark_completed_from_failed_raises(self):
        job = AnalysisJob()
        job.mark_failed("err")
        with pytest.raises(ValueError, match="Cannot mark as COMPLETED"):
            job.mark_completed(markdown="", html="", pages_json="[]")

    def test_mark_failed_from_completed_raises(self):
        job = AnalysisJob()
        job.mark_running()
        job.mark_completed(markdown="", html="", pages_json="[]")
        with pytest.raises(ValueError, match="Cannot mark as FAILED"):
            job.mark_failed("err")

    def test_mark_failed_from_pending_allowed(self):
        job = AnalysisJob()
        job.mark_failed("err")
        assert job.status == AnalysisStatus.FAILED

    def test_mark_failed_from_running_allowed(self):
        job = AnalysisJob()
        job.mark_running()
        job.mark_failed("err")
        assert job.status == AnalysisStatus.FAILED

    def test_update_progress_from_pending_raises(self):
        job = AnalysisJob()
        with pytest.raises(ValueError, match="Cannot update progress"):
            job.update_progress(1, 10)

    def test_update_progress_from_running_allowed(self):
        job = AnalysisJob()
        job.mark_running()
        job.update_progress(5, 10)
        assert job.progress_current == 5
        assert job.progress_total == 10


class TestAnalysisStatus:
    def test_values(self):
        assert AnalysisStatus.PENDING == "PENDING"
        assert AnalysisStatus.RUNNING == "RUNNING"
        assert AnalysisStatus.COMPLETED == "COMPLETED"
        assert AnalysisStatus.FAILED == "FAILED"

    def test_from_string(self):
        assert AnalysisStatus("PENDING") == AnalysisStatus.PENDING
        assert AnalysisStatus("COMPLETED") == AnalysisStatus.COMPLETED


class TestCurrentAnalysisRules:
    """One predicate per rule on which analysis can be a document's current one."""

    @pytest.mark.parametrize("status", list(AnalysisStatus))
    def test_only_a_completed_analysis_can_be_current(self, status):
        job = AnalysisJob(document_id="d1", status=status)
        assert job.can_be_current() is (status is AnalysisStatus.COMPLETED)

    def test_it_must_also_belong_to_the_document(self):
        job = AnalysisJob(document_id="d1", status=AnalysisStatus.COMPLETED)
        assert job.can_be_current_of("d1")
        assert not job.can_be_current_of("d2")

    def test_a_docling_document_is_a_separate_rule(self):
        completed = AnalysisJob(status=AnalysisStatus.COMPLETED)
        assert not completed.has_docling_document()
        completed.document_json = "{}"
        assert completed.has_docling_document()
        running = AnalysisJob(status=AnalysisStatus.RUNNING, document_json="{}")
        assert not running.has_docling_document()
