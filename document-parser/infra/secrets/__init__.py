"""Secrets-at-rest adapter — Fernet box keyed by STORE_SECRET_KEY.

Used by the persistence layer to seal user-managed store passwords
(#279) before they touch SQLite. The Fernet algorithm bundles
AES-128-CBC encryption with HMAC-SHA256 authentication, so corrupted
ciphertext is detected at decrypt time rather than producing garbage.

Public surface:

  - `FernetBox` — explicit-key constructor, used in tests.
  - `get_fernet_box()` — module-level singleton lazy-loaded from
    `STORE_SECRET_KEY`. Raises `StoreSecretKeyMissingError` when
    needed and absent.
  - `StoreSecretKeyMissingError`, `StoreSecretKeyInvalidError`,
    `SealedValueTamperedError` — typed exceptions callers catch.
  - `generate_key()` — emits a fresh Fernet key. Used by `.env.example`
    bootstrapping and the test suite; not called at runtime.

Why a thin wrapper instead of using Fernet directly: the rest of the
codebase deals in str (Pydantic, aiosqlite TEXT columns), and the
boot-check error story for the missing key needs to be specific
enough that operators can self-serve. Centralising both here keeps
the call sites trivial — `box.seal(password)` / `box.open(sealed)`.
"""

from infra.secrets.fernet_box import (
    FernetBox,
    SealedValueTamperedError,
    StoreSecretKeyInvalidError,
    StoreSecretKeyMissingError,
    generate_key,
    get_fernet_box,
    reset_fernet_box,
)

__all__ = [
    "FernetBox",
    "SealedValueTamperedError",
    "StoreSecretKeyInvalidError",
    "StoreSecretKeyMissingError",
    "generate_key",
    "get_fernet_box",
    "reset_fernet_box",
]
