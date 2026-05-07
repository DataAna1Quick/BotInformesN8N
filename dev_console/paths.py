"""Centralised paths used by the dev console."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STREAMLIT_DIR = ROOT / "streamlit_app"
CORE_DIR = STREAMLIT_DIR / "core"
ASSETS_DIR = STREAMLIT_DIR / "assets"
PROMPTS_DIR = CORE_DIR / "prompts"

PROMPT_FILE = PROMPTS_DIR / "indicator_analyst.md"
PALETTE_FILE = ASSETS_DIR / "default_palette.json"
SLIDES_FILE = ASSETS_DIR / "slides_config.json"
API_LOG_FILE = ROOT / "dev_console" / ".api_log.jsonl"

FIXTURES_DIR = ROOT / "tests" / "fixtures"
