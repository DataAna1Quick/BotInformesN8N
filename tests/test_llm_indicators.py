"""Tests for the Anthropic wrapper. The SDK is mocked end-to-end."""
from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from core import llm_indicators as llm
from core.eda import run as run_eda
from core.indicators import IndicatorBundle
from core.metrics import compute


@pytest.fixture
def fake_tool_input() -> dict:
    return {
        "executive_summary": "Resumen de prueba.",
        "indicators": [
            {
                "name": f"KPI {i}", "question": "?", "formula": "x",
                "columns": ["service_type"], "granularity": "mensual",
                "frequency": "mensual", "confidence": "alta", "reason": "ok",
            }
            for i in range(5)
        ],
        "fortalezas": [["F1", "x"], ["F2", "y"], ["F3", "z"]],
        "oportunidades": [["O1", "x"], ["O2", "y"], ["O3", "z"]],
        "bullets": {
            "volume_month": ["a", "b"],
            "service_mix": ["c"],
            "by_client": ["d"],
            "top_routes": ["e"],
            "top_drivers": ["f"],
            "vehicle_types": ["g"],
            "keepers": ["h"],
            "manifests": ["i"],
            "cargo_types": ["j"],
        },
    }


def _install_fake_anthropic(monkeypatch, *, behavior: str, fake_input=None):
    """Install a fake `anthropic` module on sys.modules with the requested behavior."""
    fake = types.ModuleType("anthropic")

    class AuthenticationError(Exception):
        pass

    class RateLimitError(Exception):
        pass

    class APIStatusError(Exception):
        def __init__(self, msg, status_code=500):
            super().__init__(msg)
            self.status_code = status_code

    class FakeUsage:
        input_tokens = 1000
        output_tokens = 500
        cache_read_input_tokens = 200

    class FakeBlock:
        def __init__(self, name, input_):
            self.type = "tool_use"
            self.name = name
            self.input = input_

    class FakeMessage:
        def __init__(self, content):
            self.content = content
            self.usage = FakeUsage()

    class FakeMessages:
        def create(self, **kwargs):
            if behavior == "ok":
                return FakeMessage([FakeBlock("submit_report", fake_input)])
            if behavior == "auth":
                raise AuthenticationError("invalid api key")
            if behavior == "rate":
                raise RateLimitError("rate limited 429")
            if behavior == "quota":
                raise APIStatusError("insufficient_quota: out of credit", 400)
            if behavior == "network":
                raise APIStatusError("connection reset", 503)
            if behavior == "no_tool":
                return FakeMessage([])
            raise RuntimeError("unexpected behavior")

    class FakeClient:
        def __init__(self, *_, **__):
            self.messages = FakeMessages()

    fake.Anthropic = FakeClient
    fake.AuthenticationError = AuthenticationError
    fake.RateLimitError = RateLimitError
    fake.APIStatusError = APIStatusError
    monkeypatch.setitem(sys.modules, "anthropic", fake)


def test_propose_happy_path(monkeypatch, excel_bytes, fake_tool_input, tmp_path):
    monkeypatch.setattr(llm, "LOG_PATH", tmp_path / "api_log.jsonl")
    _install_fake_anthropic(monkeypatch, behavior="ok", fake_input=fake_tool_input)
    report = run_eda(excel_bytes)
    kpis = compute(report)
    bundle = llm.propose(report, kpis, "ClienteX", api_key="sk-ant-fake")
    assert isinstance(bundle, IndicatorBundle)
    assert len(bundle.indicators) == 5
    # Log file written
    log_text = (tmp_path / "api_log.jsonl").read_text(encoding="utf-8")
    assert "ClienteX" in log_text
    assert '"fallback": false' in log_text


@pytest.mark.parametrize("behavior,exc_cls", [
    ("auth", llm.LLMAuthError),
    ("rate", llm.LLMQuotaError),
    ("quota", llm.LLMQuotaError),
    ("network", llm.LLMUnavailable),
])
def test_propose_falls_back_correctly(monkeypatch, excel_bytes, behavior, exc_cls):
    _install_fake_anthropic(monkeypatch, behavior=behavior)
    report = run_eda(excel_bytes)
    kpis = compute(report)
    with pytest.raises(exc_cls):
        llm.propose(report, kpis, "ClienteX", api_key="sk-ant-fake")


def test_propose_no_tool_call_raises(monkeypatch, excel_bytes):
    _install_fake_anthropic(monkeypatch, behavior="no_tool")
    report = run_eda(excel_bytes)
    kpis = compute(report)
    with pytest.raises(llm.LLMError):
        llm.propose(report, kpis, "ClienteX", api_key="sk-ant-fake")


def test_propose_no_api_key_raises():
    # Don't install fake anthropic; just call without key
    import os
    old = os.environ.pop("ANTHROPIC_API_KEY", None)
    try:
        from core.eda import EdaReport
        from core.metrics import Kpis
        with pytest.raises(llm.LLMAuthError):
            llm.propose(MagicMock(spec=EdaReport), MagicMock(spec=Kpis), "C")
    finally:
        if old:
            os.environ["ANTHROPIC_API_KEY"] = old


def test_health_check_no_key():
    h = llm.health_check(None)
    assert h["ok"] is False
    assert h["reason"] == "missing_api_key"
