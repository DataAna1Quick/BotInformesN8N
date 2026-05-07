"""Anthropic Claude wrapper that produces an IndicatorBundle.

Contract is identical to `indicators.derive` so callers can swap the two
without changes. On any failure (no key, quota, network), the caller is
expected to fall back to the deterministic template.
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from .eda import EdaReport
from .indicators import Indicator, IndicatorBundle
from .metrics import Kpis


log = logging.getLogger("botinformes.llm")

DEFAULT_MODEL = "claude-haiku-4-5-20251001"
PREMIUM_MODEL = "claude-sonnet-4-6"

# Approximate USD cost per 1M tokens (validate periodically against console.anthropic.com).
PRICE_TABLE = {
    "claude-haiku-4-5-20251001": {"input": 1.0, "cached_input": 0.10, "output": 5.0},
    "claude-sonnet-4-6":         {"input": 3.0, "cached_input": 0.30, "output": 15.0},
}

PROMPT_PATH = Path(__file__).parent / "prompts" / "indicator_analyst.md"
LOG_PATH = Path(__file__).resolve().parents[2] / "dev_console" / ".api_log.jsonl"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class LLMError(RuntimeError):
    """Generic LLM problem — fall back to template."""


class LLMUnavailable(LLMError):
    """Network / 5xx / timeout — fall back."""


class LLMAuthError(LLMError):
    """401, invalid key — fall back, surface to UI."""


class LLMQuotaError(LLMError):
    """429, insufficient_quota, rate limit — fall back, surface to UI."""


# ---------------------------------------------------------------------------
# Tool schema for structured output
# ---------------------------------------------------------------------------

SUBMIT_REPORT_TOOL = {
    "name": "submit_report",
    "description": "Devuelve el contenido textual del informe gerencial.",
    "input_schema": {
        "type": "object",
        "required": ["executive_summary", "indicators", "fortalezas",
                     "oportunidades", "bullets"],
        "properties": {
            "executive_summary": {"type": "string"},
            "indicators": {
                "type": "array", "minItems": 5, "maxItems": 12,
                "items": {
                    "type": "object",
                    "required": ["name", "question", "formula", "columns",
                                 "granularity", "frequency", "confidence", "reason"],
                    "properties": {
                        "name": {"type": "string"},
                        "question": {"type": "string"},
                        "formula": {"type": "string"},
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "granularity": {"type": "string"},
                        "frequency": {"type": "string"},
                        "confidence": {"enum": ["alta", "media", "baja"]},
                        "reason": {"type": "string"},
                    },
                },
            },
            "fortalezas": {
                "type": "array", "minItems": 3, "maxItems": 6,
                "items": {
                    "type": "array", "minItems": 2, "maxItems": 2,
                    "items": {"type": "string"},
                },
            },
            "oportunidades": {
                "type": "array", "minItems": 3, "maxItems": 6,
                "items": {
                    "type": "array", "minItems": 2, "maxItems": 2,
                    "items": {"type": "string"},
                },
            },
            "bullets": {
                "type": "object",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1, "maxItems": 5,
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _estimate_cost(model: str, input_tokens: int, cached_input_tokens: int,
                   output_tokens: int) -> float:
    table = PRICE_TABLE.get(model) or PRICE_TABLE[DEFAULT_MODEL]
    return round(
        (input_tokens - cached_input_tokens) / 1e6 * table["input"]
        + cached_input_tokens / 1e6 * table["cached_input"]
        + output_tokens / 1e6 * table["output"],
        6,
    )


def _log_call(record: dict) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        log.warning("Could not write api log: %s", e)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def health_check(api_key: str | None) -> dict:
    """Cheap one-token probe with Haiku. Returns {ok, reason, model}."""
    if not api_key:
        return {"ok": False, "reason": "missing_api_key", "model": None}
    try:
        import anthropic
    except ImportError:
        return {"ok": False, "reason": "anthropic_sdk_not_installed", "model": None}

    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=1,
            messages=[{"role": "user", "content": "ok"}],
        )
        return {"ok": True, "reason": "healthy", "model": DEFAULT_MODEL}
    except Exception as e:
        cls = type(e).__name__
        msg = str(e).lower()
        if "auth" in cls.lower() or "401" in msg:
            return {"ok": False, "reason": "api_key_invalid", "model": None}
        if "rate" in cls.lower() or "429" in msg:
            return {"ok": False, "reason": "rate_limited", "model": None}
        if "credit" in msg or "quota" in msg:
            return {"ok": False, "reason": "no_credit", "model": None}
        return {"ok": False, "reason": f"error_{cls}", "model": None}


# ---------------------------------------------------------------------------
# Building the prompt
# ---------------------------------------------------------------------------

def _read_system_prompt() -> str:
    if not PROMPT_PATH.exists():
        return "Eres un analista senior de operaciones logísticas."
    return PROMPT_PATH.read_text(encoding="utf-8")


def _summarize_eda_for_llm(report: EdaReport, kpis: Kpis,
                            client_name: str) -> str:
    """Compact textual summary of the EDA (≈3-6K tokens)."""
    viable = []
    revisar = []
    descartadas = []
    for col, info in report.columns.items():
        if info.verdict.startswith("viable"):
            viable.append({"col": col, "verdict": info.verdict,
                           "n_unique": info.n_unique, "pct_null": info.pct_null})
        elif info.verdict == "revisar":
            revisar.append(col)
        elif info.verdict == "descartar":
            descartadas.append(col)

    payload = {
        "client_name": client_name,
        "rows": kpis["total"],
        "rows_original": report.n_rows_original,
        "period": kpis["periodo"],
        "months": kpis["vol_categories"],
        "filters_applied": report.filters_applied,
        "kpis": {
            "n_clients": kpis["n_clients"],
            "n_drivers": kpis["n_drivers"],
            "n_keepers": kpis["n_keepers"],
            "n_vehicle_types": kpis["n_vehicle_types"],
            "n_routes": kpis["n_routes"],
            "n_months": kpis["n_months"],
            "terminal_rate": round(float(kpis["terminal_rate"]), 2),
            "peak_month": kpis["peak_month"],
            "peak_val": kpis["peak_val"],
            "valley_month": kpis["valley_month"],
            "valley_val": kpis["valley_val"],
            "service_type_top": kpis["st_top"],
            "service_type_top_pct": round(float(kpis["st_top_pct"]), 1),
            "client_top": kpis["top_cli"],
            "client_top_pct": round(float(kpis["top_cli_pct"]), 1),
            "route_top": kpis["top_route"],
            "route_top_pct": round(float(kpis["top_route_pct"]), 1),
            "top10_route_pct": round(float(kpis["top10_route_pct"]), 1),
            "driver_top": kpis["top_drv"],
            "driver_top_pct": round(float(kpis["top_drv_pct"]), 1),
            "top10_drv_pct": round(float(kpis["top10_drv_pct"]), 1),
            "vehicle_top": kpis["top_veh"],
            "vehicle_top_pct": round(float(kpis["top_veh_pct"]), 1),
            "keeper_top": kpis["top_kee"],
            "keeper_top_pct": round(float(kpis["top_kee_pct"]), 1),
            "top5_kee_pct": round(float(kpis["top5_kee_pct"]), 1),
            "manifest_states": dict(zip(kpis["mfs_cats"], kpis["mfs_vals"])),
            "term_by_month": dict(zip(kpis["term_months"], kpis["term_rates"])),
            "cargo_top": kpis["top_merc"],
            "cargo_top_pct": round(float(kpis["top_merc_pct"]), 1),
            "n_cargo_types": kpis["n_merc"],
        },
        "viable_columns": viable,
        "revisar_columns": revisar,
        "descartadas_columns_sample": descartadas[:30],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def propose(
    report: EdaReport,
    kpis: Kpis,
    client_name: str,
    *,
    api_key: str | None = None,
    model: str | None = None,
    timeout: float = 30.0,
) -> IndicatorBundle:
    """Build IndicatorBundle via Claude. Raises LLMError on failure."""
    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMAuthError("ANTHROPIC_API_KEY not set")

    try:
        import anthropic
    except ImportError as e:
        raise LLMUnavailable("anthropic SDK not installed") from e

    model = model or DEFAULT_MODEL
    system_prompt = _read_system_prompt()
    user_payload = _summarize_eda_for_llm(report, kpis, client_name)

    client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
    t0 = time.time()
    try:
        msg = client.messages.create(
            model=model,
            max_tokens=4000,
            temperature=0.3,
            system=[{
                "type": "text",
                "text": system_prompt,
                "cache_control": {"type": "ephemeral"},
            }],
            tools=[SUBMIT_REPORT_TOOL],
            tool_choice={"type": "tool", "name": "submit_report"},
            messages=[{
                "role": "user",
                "content": (
                    "Aquí está el contexto de la operación. Devuelve el informe "
                    "vía la herramienta submit_report.\n\n```json\n"
                    + user_payload + "\n```"
                ),
            }],
        )
    except Exception as e:
        cls = type(e).__name__
        msg_lower = str(e).lower()
        if "auth" in cls.lower() or "401" in msg_lower:
            raise LLMAuthError(str(e)) from e
        if "rate" in cls.lower() or "429" in msg_lower:
            raise LLMQuotaError(str(e)) from e
        if "credit" in msg_lower or "quota" in msg_lower:
            raise LLMQuotaError(str(e)) from e
        raise LLMUnavailable(f"{cls}: {e}") from e

    elapsed_ms = int((time.time() - t0) * 1000)

    # Extract tool input
    tool_input = None
    for block in msg.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_report":
            tool_input = block.input
            break
    if tool_input is None:
        raise LLMError("LLM did not return submit_report tool call")

    # Logging
    usage = getattr(msg, "usage", None)
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    cached_tok = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost = _estimate_cost(model, in_tok, cached_tok, out_tok)
    _log_call({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "client": client_name,
        "input_tokens": int(in_tok),
        "cached_input_tokens": int(cached_tok),
        "output_tokens": int(out_tok),
        "cost_usd": cost,
        "elapsed_ms": elapsed_ms,
        "fallback": False,
    })

    return _bundle_from_tool_input(tool_input)


def _bundle_from_tool_input(d: dict) -> IndicatorBundle:
    return IndicatorBundle(
        executive_summary=str(d["executive_summary"]),
        indicators=[
            Indicator(
                name=str(i["name"]),
                question=str(i["question"]),
                formula=str(i["formula"]),
                columns=list(i["columns"]),
                granularity=str(i["granularity"]),
                frequency=str(i["frequency"]),
                confidence=i["confidence"],
                reason=str(i["reason"]),
            )
            for i in d["indicators"]
        ],
        fortalezas=[(str(p[0]), str(p[1])) for p in d["fortalezas"]],
        oportunidades=[(str(p[0]), str(p[1])) for p in d["oportunidades"]],
        bullets={k: list(v) for k, v in d["bullets"].items()},
    )


def log_fallback(client_name: str, reason: str) -> None:
    """Public helper to register a fallback in the api log."""
    _log_call({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": None,
        "client": client_name,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "elapsed_ms": 0,
        "fallback": True,
        "fallback_reason": reason,
    })
