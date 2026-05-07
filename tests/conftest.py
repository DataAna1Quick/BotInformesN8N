"""Pytest fixtures shared across tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make `streamlit_app/core` importable as `core`.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "streamlit_app"))

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def excel_path() -> Path:
    p = FIXTURES / "n8n_sample.xlsx"
    if not p.exists():
        pytest.skip(f"Falta fixture {p} (no commiteado, copiar manualmente)")
    return p


@pytest.fixture(scope="session")
def excel_bytes(excel_path) -> bytes:
    return excel_path.read_bytes()


@pytest.fixture(scope="session")
def client_logo_bytes() -> bytes:
    p = FIXTURES / "client_logo_sample.png"
    return p.read_bytes() if p.exists() else b""


@pytest.fixture(scope="session")
def provider_logo_bytes() -> bytes:
    p = ROOT / "streamlit_app" / "assets" / "logo_quick.png"
    return p.read_bytes() if p.exists() else b""
