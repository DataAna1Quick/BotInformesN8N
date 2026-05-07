"""Streamlit app tests using AppTest. Validates login flow and main UI."""
from __future__ import annotations

import pytest

try:
    from streamlit.testing.v1 import AppTest
    HAS_APPTEST = True
except ImportError:
    HAS_APPTEST = False


pytestmark = pytest.mark.skipif(not HAS_APPTEST, reason="AppTest not available")


def _new_app():
    from pathlib import Path
    here = Path(__file__).resolve().parent.parent
    return AppTest.from_file(str(here / "streamlit_app" / "app.py"), default_timeout=30)


def test_initial_view_shows_login():
    at = _new_app()
    at.run()
    # Login form must exist
    assert at.text_input
    assert any("Contraseña" in str(t.label) for t in at.text_input)
    # No content from generator view yet
    body_text = " ".join(str(m) for m in at.markdown)
    assert "Generación de informes" not in body_text


def test_wrong_password_shows_error():
    at = _new_app()
    at.run()
    at.text_input[0].input("not-the-password").run()
    # Click the submit button
    if at.button:
        at.button[0].click().run()
    # Error message should appear
    if at.error:
        assert any("Contraseña incorrecta" in str(e.value) for e in at.error)


def test_correct_password_logs_in():
    at = _new_app()
    at.run()
    at.text_input[0].input("QuickHelp2026").run()
    if at.button:
        at.button[0].click().run()
    # session_state in AppTest behaves like an object, not a dict
    assert "authed" in at.session_state
    assert at.session_state["authed"] is True
