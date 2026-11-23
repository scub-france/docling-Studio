"""Edit-stream hashes, the sequence check and the plain-value edit rules.

The hashes are persisted (`analysis_edit_commands.command_hash`,
`edited_analysis_cache.command_stream_hash`): the tests pin them against the
formula written out by hand, so a change to the serialisation fails here
before it invalidates stored rows.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import pytest

from domain.analysis_editing import (
    EDITOR_SEQUENCE_CONFLICT,
    STORED_SEQUENCE_CONFLICT,
    AnalysisEditConflictError,
    AnalysisEditError,
    EditCommand,
    StoredEditCommand,
    check_command_version,
    check_delete_request,
    check_expected_sequence,
    check_heading_level,
    check_merge_request,
    check_mergeable_labels,
    check_move_target,
    hash_command,
    hash_command_stream,
    serialize_command_payload,
)

_COMMANDS = [
    EditCommand("replaceText", {"text": "Résumé", "elementId": "base:#/texts/0"}),
    EditCommand("mergeText", {"elementIds": ["a", "b"], "separator": " "}),
    EditCommand("setCommandActive", {"targetSequence": 1, "active": False}),
]


def _expected_command_hash(previous: str, sequence: int, command: EditCommand) -> str:
    payload = json.dumps(command.payload, sort_keys=True, separators=(",", ":"))
    raw = f"{previous}|{sequence}|{command.command_type}|{command.command_version}|{payload}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _store(commands: list[EditCommand]) -> list[StoredEditCommand]:
    """The rows the repository writes for `commands` on an empty stream."""
    stored: list[StoredEditCommand] = []
    previous = ""
    for sequence, command in enumerate(commands, start=1):
        previous = hash_command(previous, sequence, command)
        stored.append(
            StoredEditCommand(f"id-{sequence}", "an-1", sequence, command, previous, _NOW)
        )
    return stored


class TestCommandHash:
    def test_payload_json_is_sorted_compact_and_ascii(self):
        payload = serialize_command_payload({"b": 1, "a": "é", "c": [1, 2]})
        assert payload == '{"a":"\\u00e9","b":1,"c":[1,2]}'

    def test_matches_the_persisted_formula(self):
        previous = ""
        for sequence, command in enumerate(_COMMANDS, start=1):
            expected = _expected_command_hash(previous, sequence, command)
            assert hash_command(previous, sequence, command) == expected
            previous = expected

    def test_depends_on_the_previous_link(self):
        command = _COMMANDS[0]
        assert hash_command("", 1, command) != hash_command("x", 1, command)


class TestStreamHash:
    def test_an_empty_stream_is_the_hash_of_nothing(self):
        assert hash_command_stream([], []) == hashlib.sha256(b"").hexdigest()

    def test_digests_the_chain_hashes_in_order(self):
        stored = _store(_COMMANDS)
        digest = hashlib.sha256()
        for record in stored:
            digest.update(record.command_hash.encode())
        assert hash_command_stream(stored, []) == digest.hexdigest()

    def test_the_hash_saved_with_pending_commands_matches_the_one_loaded_later(self):
        # `save` writes the cache with the pending commands; `load_editor`
        # checks it against the stored rows. Both must agree or every load
        # replays the stream.
        stored = _store(_COMMANDS)
        expected = hash_command_stream(stored, [])
        for split_at in range(len(_COMMANDS) + 1):
            assert hash_command_stream(stored[:split_at], _COMMANDS[split_at:]) == expected


class TestExpectedSequence:
    def test_accepts_the_current_sequence(self):
        check_expected_sequence(3, 3)

    def test_the_service_wording(self):
        with pytest.raises(AnalysisEditConflictError) as caught:
            check_expected_sequence(1, 2)
        assert str(caught.value) == "The editor stream changed: expected 1, actual 2"
        assert EDITOR_SEQUENCE_CONFLICT.format(expected=1, actual=2) == str(caught.value)

    def test_the_repository_wording(self):
        with pytest.raises(AnalysisEditConflictError) as caught:
            check_expected_sequence(0, 4, STORED_SEQUENCE_CONFLICT)
        assert str(caught.value) == "Edit stream changed: expected sequence 0, actual sequence 4"


class TestPlainValueEditRules:
    def test_command_version(self):
        check_command_version(1)
        with pytest.raises(AnalysisEditError, match=r"^Unsupported command version: 2$"):
            check_command_version(2)

    @pytest.mark.parametrize("level", [-1, 0, 1, 6])
    def test_heading_levels_in_bounds(self, level):
        check_heading_level(level, title_exists=False)

    @pytest.mark.parametrize("level", [-2, 7])
    def test_heading_levels_out_of_bounds(self, level):
        with pytest.raises(AnalysisEditError, match=r"^Heading level must be -1, 0, or between"):
            check_heading_level(level, title_exists=False)

    def test_only_one_title(self):
        check_heading_level(1, title_exists=True)
        with pytest.raises(AnalysisEditError, match=r"^A document can contain only one title$"):
            check_heading_level(0, title_exists=True)

    @pytest.mark.parametrize(
        ("ids", "separator"),
        [(["a"], " "), ("ab", " "), (None, " "), (["a", "b"], None)],
    )
    def test_merge_request_shape(self, ids, separator):
        with pytest.raises(AnalysisEditError, match=r"^mergeText requires at least two element"):
            check_merge_request(ids, separator)

    def test_merge_request_accepts_two_ids(self):
        check_merge_request(["a", "b"], "")

    @pytest.mark.parametrize("labels", [{"text"}, {"paragraph"}, {"Text"}])
    def test_mergeable_labels(self, labels):
        check_mergeable_labels(labels)

    @pytest.mark.parametrize("labels", [{"text", "paragraph"}, {"section_header"}, set()])
    def test_unmergeable_labels(self, labels):
        with pytest.raises(AnalysisEditError, match=r"^Only compatible paragraph text items"):
            check_mergeable_labels(labels)

    @pytest.mark.parametrize("ids", [[], None, "a"])
    def test_delete_request_shape(self, ids):
        with pytest.raises(AnalysisEditError, match=r"^deleteElements requires at least one"):
            check_delete_request(ids)

    @pytest.mark.parametrize("placement", ["before", "after", "inside"])
    def test_move_target_accepts_known_placements(self, placement):
        check_move_target("base:#/texts/1", placement)

    @pytest.mark.parametrize(
        ("target_id", "placement"),
        [(None, "before"), (1, "after"), ("base:#/texts/1", "below"), ("x", None)],
    )
    def test_move_target_rejects(self, target_id, placement):
        with pytest.raises(AnalysisEditError, match=r"^moveElement requires a target"):
            check_move_target(target_id, placement)
