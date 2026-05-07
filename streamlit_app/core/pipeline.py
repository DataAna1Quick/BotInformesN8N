"""End-to-end orchestrator: Excel + logo + name → PPT bytes.

Streamlit and the PyQt console both call `run_pipeline`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

from .color_extractor import ClientConfig, Palette, extract_palette
from .eda import run as run_eda
from .errors import (
    ClientNameMissingError,
    EmptyAfterFilterError,
    PipelineError,
)
from .indicators import IndicatorBundle, derive as derive_indicators_template
from .metrics import compute as compute_metrics
from .ppt_builder import PPTBuilder
from .schema import validate as validate_schema


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _load_provider_logo() -> bytes:
    path = ASSETS_DIR / "logo_quick.png"
    return path.read_bytes() if path.exists() else b""


def _load_slides_config() -> dict:
    path = ASSETS_DIR / "slides_config.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def run_pipeline(
    excel_bytes: bytes,
    client_logo_bytes: bytes | None,
    client_name: str,
    *,
    use_llm: bool = False,
    api_key: str | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> bytes:
    """Run the full Excel → PPT pipeline. Returns .pptx bytes."""
    log = progress_cb or (lambda msg: None)

    log("Validando estructura del Excel...")
    schema_check = validate_schema(excel_bytes)
    log(f"  hoja '{schema_check.sheet_name}' · {schema_check.n_rows} filas")

    log("Ejecutando análisis exploratorio...")
    report = run_eda(excel_bytes)
    log(f"  {report.n_rows_filtered} filas tras filtros · período {report.period_label}")

    log("Calculando KPIs...")
    kpis = compute_metrics(report)

    log("Derivando indicadores...")
    bundle: IndicatorBundle
    used_llm = False
    if use_llm and api_key:
        from .llm_indicators import LLMError, log_fallback, propose as llm_propose
        try:
            bundle = llm_propose(report, kpis, client_name, api_key=api_key)
            used_llm = True
            log("  modo IA · Claude")
        except LLMError as e:
            log(f"  ⚠ IA no disponible ({type(e).__name__}); usando plantilla")
            log_fallback(client_name, type(e).__name__)
            bundle = derive_indicators_template(report, kpis, client_name)
    else:
        bundle = derive_indicators_template(report, kpis, client_name)
        log("  modo plantilla determinística")

    log("Extrayendo paleta del logo cliente...")
    palette = extract_palette(client_logo_bytes)
    config = ClientConfig(
        name=client_name or "Cliente",
        logo_bytes=client_logo_bytes,
        palette=palette,
    )

    log("Construyendo PPT...")
    builder = PPTBuilder(config, slides_config=_load_slides_config())
    pptx_bytes = builder.build(kpis, bundle, _load_provider_logo())
    log(f"  PPT generado · {len(pptx_bytes):,} bytes".replace(",", "."))

    log("Listo.")
    return pptx_bytes


def run_pipeline_full(
    excel_bytes: bytes,
    client_logo_bytes: bytes | None,
    client_name: str,
    *,
    use_llm: bool = False,
    api_key: str | None = None,
    progress_cb: Callable[[str], None] | None = None,
) -> dict:
    """Same as run_pipeline but returns metadata + bytes for the UI.

    Raises subclasses of PipelineError on validation failures.
    """
    log = progress_cb or (lambda msg: None)

    if not client_name or not client_name.strip():
        raise ClientNameMissingError(
            "Falta el nombre del cliente. No se puede generar la presentación sin él."
        )

    log("Validando estructura del Excel...")
    schema_check = validate_schema(excel_bytes)

    log("Análisis exploratorio...")
    report = run_eda(excel_bytes)
    if report.n_rows_filtered == 0:
        raise EmptyAfterFilterError(
            "El Excel no tiene filas analizables después de aplicar los filtros "
            f"(estado de servicio excluidos: {report.filters_applied.get('service_state_exclude', [])}). "
            "Verifica el archivo."
        )

    log("Calculando KPIs...")
    kpis = compute_metrics(report)

    used_llm = False
    log("Derivando indicadores...")
    if use_llm and api_key:
        from .llm_indicators import LLMError, log_fallback, propose as llm_propose
        try:
            bundle = llm_propose(report, kpis, client_name, api_key=api_key)
            used_llm = True
            log("  modo IA · Claude")
        except LLMError as e:
            log(f"  ⚠ IA falló ({type(e).__name__}); usando plantilla")
            log_fallback(client_name, type(e).__name__)
            bundle = derive_indicators_template(report, kpis, client_name)
    else:
        bundle = derive_indicators_template(report, kpis, client_name)
        log("  modo plantilla")

    log("Extrayendo paleta del logo...")
    palette = extract_palette(client_logo_bytes, strict=True)
    config = ClientConfig(
        name=client_name.strip(),
        logo_bytes=client_logo_bytes,
        palette=palette,
    )

    log("Construyendo PPT...")
    builder = PPTBuilder(config, slides_config=_load_slides_config())
    pptx_bytes = builder.build(kpis, bundle, _load_provider_logo())
    log("Listo.")

    return {
        "pptx_bytes": pptx_bytes,
        "used_llm": used_llm,
        "rows_original": schema_check.n_rows,
        "rows_filtered": report.n_rows_filtered,
        "period": report.period_label,
        "client_name": config.name,
        "palette_primary": palette.primary,
        "n_indicators": len(bundle.indicators),
    }


def preview_palette(client_logo_bytes: bytes | None) -> Palette:
    """Public helper used by the UI to preview the palette before generating."""
    return extract_palette(client_logo_bytes, strict=False)
