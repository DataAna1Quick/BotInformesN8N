"""Pure EDA pipeline. No disk writes, no argv. Returns an EdaReport ready to consume."""
from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd

from .schema import pick_sheet, _open_excel  # noqa: F401  (private helpers reused)


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
PHONE_RE = re.compile(r"^[+\d][\d\s().\-]{6,}$")
DATE_LIKE_RE = re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}")

DEFAULT_FILTERS = {
    "service_state_exclude": ["5 - Cancelado", "7 - Finalizado Cancelado"],
}

MONTH_ORDER = ("Ene", "Feb", "Mar", "Abr", "May", "Jun",
               "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")


@dataclass
class ColumnInfo:
    name: str
    dtype: str
    n_total: int
    n_non_null: int
    pct_null: float
    n_unique: int
    pct_unique: float
    top_values: list[dict]
    verdict: str
    reason: str
    numeric_stats: dict | None = None
    text_stats: dict | None = None
    date_stats: dict | None = None


@dataclass
class EdaReport:
    sheet_name: str
    n_rows_original: int
    n_rows_filtered: int
    n_cols: int
    period_label: str
    months: list[str]
    columns: dict[str, ColumnInfo]
    df_filtered: pd.DataFrame = field(repr=False)
    filters_applied: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Column-level helpers
# ---------------------------------------------------------------------------

def _safe_pct(n: int, total: int) -> float:
    return round(100.0 * n / total, 2) if total else 0.0


def _detect_text_pattern(series: pd.Series) -> str:
    sample = series.dropna().astype(str).head(200)
    if sample.empty:
        return "vacio"
    counts = {"email": 0, "url": 0, "phone": 0, "date_like": 0}
    for v in sample:
        s = v.strip()
        if EMAIL_RE.match(s):
            counts["email"] += 1
        if URL_RE.match(s):
            counts["url"] += 1
        if PHONE_RE.match(s):
            counts["phone"] += 1
        if DATE_LIKE_RE.match(s):
            counts["date_like"] += 1
    n = len(sample)
    dominant = max(counts.items(), key=lambda kv: kv[1])
    return dominant[0] if dominant[1] / n >= 0.7 else "texto_generico"


def _numeric_stats(series: pd.Series) -> dict:
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return {}
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    return {
        "min": float(s.min()), "p25": float(q1), "p50": float(s.median()),
        "p75": float(q3), "max": float(s.max()),
        "mean": float(s.mean()), "std": float(s.std() or 0),
        "n_zeros": int((s == 0).sum()),
        "n_negatives": int((s < 0).sum()),
    }


def _text_stats(series: pd.Series) -> dict:
    s = series.dropna().astype(str)
    if s.empty:
        return {}
    lengths = s.str.len()
    return {
        "len_min": int(lengths.min()),
        "len_max": int(lengths.max()),
        "len_mean": round(float(lengths.mean()), 2),
        "pattern": _detect_text_pattern(series),
    }


def _top_values(series: pd.Series, n: int = 10) -> list[dict]:
    vc = series.dropna().value_counts().head(n)
    return [{"value": _to_jsonable(idx), "count": int(cnt)} for idx, cnt in vc.items()]


def _to_jsonable(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return None if math.isnan(f) else f
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, pd.Timestamp):
        return v.isoformat()
    if isinstance(v, (list, tuple)):
        return [_to_jsonable(x) for x in v]
    return str(v) if not isinstance(v, (str, int, float, bool)) else v


def _column_verdict(info: dict) -> tuple[str, str]:
    pct_null = info["pct_null"]
    n_unique = info["n_unique"]
    n_non_null = info["n_non_null"]
    dtype_kind = info["dtype_kind"]
    top = info.get("top_values", [])

    if info["n_total"] == 0:
        return "descartar", "hoja vacía"
    if n_unique <= 1 and n_non_null > 0:
        return "descartar", "columna constante"
    if top and n_non_null > 0 and top[0]["count"] / n_non_null >= 0.95:
        return "descartar", f"cuasi-constante ({top[0]['count']}/{n_non_null})"
    if pct_null >= 95:
        return "descartar", f"{pct_null}% nulos"
    if dtype_kind in ("i", "u", "f") and not info.get("looks_like_id"):
        stats = info.get("numeric_stats") or {}
        if pct_null < 20 and stats.get("std") not in (None, 0):
            return "viable_métrica", f"numérica, {pct_null}% nulos, std={stats.get('std')}"
        if pct_null < 60:
            return "revisar", f"numérica con {pct_null}% nulos o varianza baja"
        return "descartar", f"numérica con {pct_null}% nulos"

    pct_unique_nn = (n_unique / n_non_null * 100) if n_non_null else 0
    if pct_unique_nn >= 95 and n_non_null >= 20:
        return "descartar", f"identificador único ({pct_unique_nn:.1f}%)"
    if pct_null >= 60:
        return "revisar", f"{pct_null}% nulos"

    text_pat = (info.get("text_stats") or {}).get("pattern")
    len_mean = (info.get("text_stats") or {}).get("len_mean", 0) or 0
    if text_pat in ("email", "url", "phone"):
        return "revisar", f"patrón {text_pat}"
    if 2 <= n_unique <= 50:
        return "viable_dimensión", f"categórica baja card ({n_unique})"
    if 50 < n_unique <= 500:
        return "viable_dimensión_alta_card", f"categórica alta card ({n_unique})"
    if n_unique > 500 and len_mean >= 25:
        return "viable_texto_libre", f"texto largo (len medio {len_mean})"
    return "revisar", f"sin regla clara — n_unique={n_unique}"


def _process_column(name: str, series: pd.Series) -> ColumnInfo:
    n_total = len(series)
    n_non_null = int(series.notna().sum())
    pct_null = _safe_pct(n_total - n_non_null, n_total)
    n_unique = int(series.nunique(dropna=True))

    info = {
        "name": name, "dtype": str(series.dtype), "dtype_kind": series.dtype.kind,
        "n_total": n_total, "n_non_null": n_non_null, "pct_null": pct_null,
        "n_unique": n_unique, "pct_unique": _safe_pct(n_unique, n_total),
        "top_values": _top_values(series, 10),
        "looks_like_id": (series.dtype.kind in ("i", "u", "f")
                          and n_non_null > 20 and (n_unique / max(n_non_null, 1)) >= 0.95),
    }
    if series.dtype.kind in ("i", "u", "f"):
        info["numeric_stats"] = _numeric_stats(series)
    if series.dtype.kind == "O":
        info["text_stats"] = _text_stats(series)
    verdict, reason = _column_verdict(info)
    return ColumnInfo(
        name=name, dtype=info["dtype"], n_total=n_total, n_non_null=n_non_null,
        pct_null=pct_null, n_unique=n_unique, pct_unique=info["pct_unique"],
        top_values=info["top_values"], verdict=verdict, reason=reason,
        numeric_stats=info.get("numeric_stats"),
        text_stats=info.get("text_stats"),
    )


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------

_MONTH_MAP = {
    "enero": "Ene", "febrero": "Feb", "marzo": "Mar", "abril": "Abr",
    "mayo": "May", "junio": "Jun", "julio": "Jul", "agosto": "Ago",
    "septiembre": "Sep", "octubre": "Oct", "noviembre": "Nov", "diciembre": "Dic",
}


def month_label(filename) -> str:
    if not isinstance(filename, str):
        return "Sin clasificar"
    s = filename.lower()
    for k, v in _MONTH_MAP.items():
        if k in s:
            return v
    return filename[:8]


def order_months(values) -> list[str]:
    seen = [m for m in MONTH_ORDER if m in set(values)]
    extras = [m for m in values if m not in MONTH_ORDER]
    return seen + sorted(set(extras))


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run(
    source: bytes | str | Path | BytesIO,
    *,
    filters: dict | None = None,
    sheet_name: str | None = None,
) -> EdaReport:
    """Run EDA on the n8n consolidated workbook.

    `filters` defaults to dropping service_state in {5 - Cancelado, 7 - Finalizado Cancelado}.
    """
    filters = {**DEFAULT_FILTERS, **(filters or {})}
    xls = _open_excel(source)
    sheet = sheet_name or pick_sheet(xls)
    df_raw = pd.read_excel(xls, sheet_name=sheet)
    n_rows_original = int(len(df_raw))

    excluded = filters.get("service_state_exclude", [])
    if excluded and "service_state" in df_raw.columns:
        df = df_raw[~df_raw["service_state"].isin(excluded)].copy()
    else:
        df = df_raw.copy()

    df["mes"] = df["archivo_origen"].apply(month_label)
    df["ruta"] = (
        df["origin_city"].astype(str).str.strip()
        + " → "
        + df["destiny_city"].astype(str).str.strip()
    )

    months = order_months(df["mes"].dropna().unique().tolist())
    period_label = f"{months[0]}–{months[-1]}" if months else "—"

    columns: dict[str, ColumnInfo] = {}
    for col in df_raw.columns:
        try:
            columns[str(col)] = _process_column(str(col), df_raw[col])
        except Exception as e:
            columns[str(col)] = ColumnInfo(
                name=str(col), dtype="?", n_total=len(df_raw), n_non_null=0,
                pct_null=100.0, n_unique=0, pct_unique=0.0, top_values=[],
                verdict="revisar", reason=f"fallo al analizar: {type(e).__name__}",
            )

    return EdaReport(
        sheet_name=sheet,
        n_rows_original=n_rows_original,
        n_rows_filtered=int(len(df)),
        n_cols=int(df_raw.shape[1]),
        period_label=period_label,
        months=months,
        columns=columns,
        df_filtered=df,
        filters_applied=filters,
    )


# ---------------------------------------------------------------------------
# Util for downstream modules
# ---------------------------------------------------------------------------

def normalize_text(s):
    if pd.isna(s):
        return s
    s = str(s).strip()
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()
