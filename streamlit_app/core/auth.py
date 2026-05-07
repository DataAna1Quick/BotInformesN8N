"""Password gate using bcrypt.

The hash for "QuickHelp2026" is generated once and stored in
`.streamlit/secrets.toml` as `APP_PASSWORD_HASH`. There is also a
fallback hash hardcoded here so the app works locally without secrets.

Generate a fresh hash:
    python -c "import bcrypt; print(bcrypt.hashpw(b'QuickHelp2026', bcrypt.gensalt(12)).decode())"
"""
from __future__ import annotations

import os

import bcrypt


# Bcrypt hash of "QuickHelp2026" - generated with bcrypt.gensalt(12).
# Used as fallback when secrets.toml is not configured (local dev).
DEFAULT_PASSWORD_HASH = "$2b$12$8dXy0y25fv8uaTEJN4CkguAndDN5ZncaPLDLnIK4I0sEhoXnVmRS2"


def _resolve_hash() -> str:
    # Streamlit secrets when available
    try:
        import streamlit as st  # noqa: F401
        h = st.secrets.get("APP_PASSWORD_HASH")  # type: ignore[attr-defined]
        if h:
            return h
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD_HASH") or DEFAULT_PASSWORD_HASH


def verify_password(password: str) -> bool:
    """True if `password` matches the configured hash."""
    if not isinstance(password, str) or not password:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), _resolve_hash().encode("utf-8"))
    except Exception:
        return False


def hash_password(password: str) -> str:
    """Helper to generate a fresh hash. Not called by the app at runtime."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(12)).decode()
