"""FernetBox — seal/open string secrets with a single symmetric key.

The implementation lives here so callers don't see the `cryptography`
imports and aren't tempted to roll their own crypto. Used by the
store repository to seal `connection_password_sealed` (#279).

Design choices:

- **Strings in, strings out.** Pydantic + aiosqlite both deal in str.
  Encoding happens behind the wall.
- **Lazy module singleton.** `get_fernet_box()` reads `STORE_SECRET_KEY`
  once and caches the box. Importing this module does **not** require
  the key — useful in tests and in boots that have no encrypted secrets
  yet.
- **Typed errors.** Callers want to discriminate between "key not set"
  (operator must act) and "ciphertext tampered" (data is corrupt or
  the key changed). `cryptography.fernet.InvalidToken` is wrapped so
  the dependency stays scoped.
- **Test affordance.** `reset_fernet_box()` lets tests swap the env
  var between cases without process restart.

Not in scope: key rotation, multi-key envelopes, KMS integration. The
`connection_key_id` reservation lives on the `stores` table for when
rotation becomes a thing — see follow-up issues from #279.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


class StoreSecretKeyMissingError(RuntimeError):
    """`STORE_SECRET_KEY` is not set and a sealed secret is being
    read or written. Callers should surface this to the operator as a
    boot-blocking error.
    """


class StoreSecretKeyInvalidError(RuntimeError):
    """`STORE_SECRET_KEY` is set but not a valid Fernet key.

    Fernet keys are URL-safe base64-encoded 32 random bytes. Generate
    a fresh one with `FernetBox.generate_key()` or
    `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    """


class SealedValueTamperedError(RuntimeError):
    """A sealed value failed to decrypt. The ciphertext is either
    corrupt or was sealed with a different key. Do NOT log the
    sealed value — it's still secret-bearing material.
    """


class FernetBox:
    """Stateless seal/open wrapper around a single Fernet key.

    Construct with an explicit key for tests. For runtime use, prefer
    `get_fernet_box()` — it caches the singleton and pulls the key
    from `STORE_SECRET_KEY`.
    """

    def __init__(self, key: str | bytes) -> None:
        if isinstance(key, str):
            key = key.encode()
        try:
            self._fernet = Fernet(key)
        except (ValueError, TypeError) as exc:
            raise StoreSecretKeyInvalidError(
                "STORE_SECRET_KEY is set but not a valid Fernet key "
                "(expected URL-safe base64-encoded 32 bytes). "
                "Generate a fresh key with FernetBox.generate_key()."
            ) from exc

    def seal(self, plaintext: str) -> str:
        """Encrypt + authenticate `plaintext`. Returns base64 ciphertext."""
        if not isinstance(plaintext, str):
            raise TypeError(f"seal() expects str, got {type(plaintext).__name__}")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def open(self, sealed: str) -> str:
        """Decrypt + verify `sealed`. Raises `SealedValueTamperedError`
        on a corrupt or key-mismatched payload.
        """
        if not isinstance(sealed, str):
            raise TypeError(f"open() expects str, got {type(sealed).__name__}")
        try:
            return self._fernet.decrypt(sealed.encode()).decode()
        except InvalidToken as exc:
            raise SealedValueTamperedError(
                "Sealed value failed to decrypt — ciphertext is corrupt "
                "or was sealed with a different STORE_SECRET_KEY."
            ) from exc


def generate_key() -> str:
    """Return a fresh Fernet key (URL-safe base64, 44 chars).

    Used by `.env.example` bootstrap and by tests; not called at
    runtime. Operators wanting a fresh key can also run the
    one-liner shown in `StoreSecretKeyInvalidError`'s docstring.
    """
    return Fernet.generate_key().decode()


# Module-level singleton. Lazy — importing this module does not read
# the env var. `reset_fernet_box()` exists for tests that need to
# rotate the key between cases without a process restart.
_box: FernetBox | None = None


def get_fernet_box() -> FernetBox:
    """Return the process-wide FernetBox, building it on first call.

    Raises `StoreSecretKeyMissingError` if the env var is unset, and
    `StoreSecretKeyInvalidError` if it's malformed. Callers that may
    operate without sealed secrets should check the env themselves
    before invoking this — the boot-time precondition check in
    `main.py` does exactly that.
    """
    global _box
    if _box is not None:
        return _box
    raw = os.environ.get("STORE_SECRET_KEY")
    if not raw:
        raise StoreSecretKeyMissingError(
            "STORE_SECRET_KEY is required to read or write encrypted "
            "store credentials. Set it in the backend environment "
            "before booting; generate a fresh key with "
            '`python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"` and keep it '
            "stable across restarts (rotating the key invalidates "
            "every existing sealed value)."
        )
    _box = FernetBox(raw)
    return _box


def reset_fernet_box() -> None:
    """Drop the cached singleton — only used by tests.

    Production code should never call this: a key change while the
    backend is running invalidates every in-memory plaintext that was
    derived from the old key.
    """
    global _box
    _box = None
