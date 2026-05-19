"""Tests for the FernetBox secrets-at-rest wrapper (#279)."""

from __future__ import annotations

import pytest

from infra.secrets import (
    FernetBox,
    SealedValueTamperedError,
    StoreSecretKeyInvalidError,
    StoreSecretKeyMissingError,
    generate_key,
    get_fernet_box,
    reset_fernet_box,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Each test starts with a clean module-level singleton — otherwise
    a previous test's key would leak through `get_fernet_box()`.
    """
    reset_fernet_box()
    yield
    reset_fernet_box()


class TestFernetBoxRoundtrip:
    def test_seal_then_open_recovers_plaintext(self) -> None:
        box = FernetBox(generate_key())
        assert box.open(box.seal("hello")) == "hello"

    def test_unicode_roundtrip(self) -> None:
        box = FernetBox(generate_key())
        assert box.open(box.seal("éàü中文🔐")) == "éàü中文🔐"

    def test_empty_string_is_allowed(self) -> None:
        # Defensible — sealing an empty password produces a valid token
        # and lets the caller distinguish "no password" (NULL column)
        # from "explicitly empty" (sealed empty string).
        box = FernetBox(generate_key())
        assert box.open(box.seal("")) == ""

    def test_each_seal_produces_distinct_ciphertext(self) -> None:
        # Fernet uses a random IV per call. Two seals of the same
        # plaintext must differ — otherwise the column would leak
        # equality of secrets across stores.
        box = FernetBox(generate_key())
        a = box.seal("same-password")
        b = box.seal("same-password")
        assert a != b
        assert box.open(a) == "same-password"
        assert box.open(b) == "same-password"


class TestFernetBoxFailureModes:
    def test_invalid_key_raises_typed_error(self) -> None:
        with pytest.raises(StoreSecretKeyInvalidError):
            FernetBox("not-a-real-fernet-key")

    def test_wrong_key_cannot_open_ciphertext(self) -> None:
        # Seal with one key, try to open with another — the box must
        # refuse rather than return garbage.
        box_a = FernetBox(generate_key())
        box_b = FernetBox(generate_key())
        sealed = box_a.seal("secret")
        with pytest.raises(SealedValueTamperedError):
            box_b.open(sealed)

    def test_tampered_ciphertext_raises(self) -> None:
        box = FernetBox(generate_key())
        sealed = box.seal("secret")
        # Flip one character of the ciphertext body.
        tampered = sealed[:-2] + ("A" if sealed[-2] != "A" else "B") + sealed[-1]
        with pytest.raises(SealedValueTamperedError):
            box.open(tampered)

    def test_seal_rejects_non_str(self) -> None:
        box = FernetBox(generate_key())
        with pytest.raises(TypeError):
            box.seal(b"bytes-not-allowed")  # type: ignore[arg-type]

    def test_open_rejects_non_str(self) -> None:
        box = FernetBox(generate_key())
        with pytest.raises(TypeError):
            box.open(b"bytes-not-allowed")  # type: ignore[arg-type]


class TestModuleSingleton:
    def test_get_fernet_box_caches_the_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_SECRET_KEY", generate_key())
        a = get_fernet_box()
        b = get_fernet_box()
        assert a is b

    def test_missing_env_var_raises_typed_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("STORE_SECRET_KEY", raising=False)
        with pytest.raises(StoreSecretKeyMissingError) as excinfo:
            get_fernet_box()
        # The message must point the operator at the fix — it ends up
        # in boot logs and on-call eyes. Pin the contract.
        msg = str(excinfo.value)
        assert "STORE_SECRET_KEY" in msg
        assert "Fernet.generate_key" in msg

    def test_invalid_env_var_raises_typed_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_SECRET_KEY", "not-a-key")
        with pytest.raises(StoreSecretKeyInvalidError):
            get_fernet_box()

    def test_reset_lets_tests_rotate_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STORE_SECRET_KEY", generate_key())
        first = get_fernet_box()
        # A second `get_fernet_box()` would return the cached instance —
        # rotating the env var has no effect until `reset_fernet_box()`.
        new_key = generate_key()
        monkeypatch.setenv("STORE_SECRET_KEY", new_key)
        assert get_fernet_box() is first
        reset_fernet_box()
        second = get_fernet_box()
        assert second is not first


class TestGenerateKey:
    def test_generates_valid_fernet_key(self) -> None:
        # A freshly-generated key must roundtrip through a FernetBox
        # without the constructor complaining.
        key = generate_key()
        box = FernetBox(key)
        assert box.open(box.seal("k")) == "k"

    def test_two_calls_produce_distinct_keys(self) -> None:
        assert generate_key() != generate_key()
