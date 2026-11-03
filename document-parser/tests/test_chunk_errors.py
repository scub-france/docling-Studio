"""`refusals_as_service_errors` — a refusal of the chunkset, answered with
the chunk error (and so the HTTP status) its reason calls for."""

from __future__ import annotations

import pytest

from domain import chunk_editing
from services.chunk_errors import (
    ChunkConflictError,
    ChunkNotFoundError,
    ChunkServiceError,
    ChunkValidationError,
    refusals_as_service_errors,
)


def _answer(refusal: Exception) -> ChunkServiceError:
    with pytest.raises(ChunkServiceError) as caught, refusals_as_service_errors():
        raise refusal
    return caught.value


class TestRefusals:
    @pytest.mark.parametrize(
        ("refusal", "error", "status"),
        [
            (chunk_editing.InvalidChunkEditError, ChunkValidationError, 400),
            (chunk_editing.UnknownChunkError, ChunkNotFoundError, 404),
            (chunk_editing.NonContiguousMergeError, ChunkConflictError, 409),
        ],
    )
    def test_each_reason_has_its_error(self, refusal, error, status):
        answer = _answer(refusal("nope"))
        assert type(answer) is error
        assert answer.http_status == status
        assert str(answer) == "nope"
        assert isinstance(answer.__cause__, refusal)

    def test_a_subclass_takes_its_parents_error(self):
        """A new reason the table does not name yet is still answered by its
        family: a lookup by exact type raised `KeyError`, a 500."""

        class StaleMergeError(chunk_editing.NonContiguousMergeError):
            pass

        answer = _answer(StaleMergeError("moved"))
        assert type(answer) is ChunkConflictError
        assert answer.http_status == 409

    def test_the_bare_base_is_a_bad_edit(self):
        answer = _answer(chunk_editing.ChunkEditingError("refused"))
        assert type(answer) is ChunkValidationError
        assert answer.http_status == 400

    def test_anything_else_goes_through_untouched(self):
        with pytest.raises(RuntimeError), refusals_as_service_errors():
            raise RuntimeError("boom")
