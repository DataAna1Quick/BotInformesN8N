"""Deterministic indicator narrative used when LLM is unavailable.

Same shape as `llm_indicators.propose()` so callers don't care which one ran.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal

from .eda import EdaReport
from .metrics import Kpis, fmt_int


@dataclass
class Indicator:
    name: str
    question: str
    formula: str
    columns: list[str]
    granularity: str
    frequency: str
    confidence: Literal["alta", "media", "baja"]
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class IndicatorBundle:
    """What the LLM (or this template) returns. Consumed by ppt_builder + indicators_propuestos.md."""
    executive_summary: str
    indicators: list[Indicator]
    fortalezas: list[tuple[str, str]]
    oportunidades: list[tuple[str, str]]
    bullets: dict[str, list[str]]  # one list per slide id


def _resumen_text(k: Kpis, client: str) -> str:
    return (
        f"Operación recurrente y trazable. Pico en {k['peak_month']} ({fmt_int(k['peak_val'])} servicios) "
        f"y valle en {k['valley_month']} ({fmt_int(k['valley_val'])}) muestran fuerte estacionalidad. "
        f"{k['top_cli']} es la sede ancla con {k['top_cli_pct']:.1f}% del volumen, atendida por "
        f"{k['n_drivers']} conductores y {k['n_keepers']} tenedores con {k['n_vehicle_types']} tipos "
        f"de vehículo. Cumplimiento de manifiestos en {k['terminal_rate']:.1f}% — operación cercana al "
        f"objetivo de 95%."
    )


def _bullets(k: Kpis) -> dict[str, list[str]]:
    avg = sum(k["vol_values"]) // max(len(k["vol_values"]), 1) if k["vol_values"] else 0
    return {
        "volume_month": [
            f"Promedio mensual: {fmt_int(avg)}",
            f"Pico: {k['peak_month']} — {fmt_int(k['peak_val'])}.",
            f"Valle: {k['valley_month']} — {fmt_int(k['valley_val'])}.",
            "Operación recurrente y sostenida en el período analizado.",
        ],
        "service_mix": [
            f"{k['st_top']} concentra {k['st_top_pct']:.1f}% del total de servicios.",
            f"Tipos de servicio activos: {k['n_service_types']}.",
            "El mix permite ajustar capacidad de flota a la modalidad dominante.",
        ],
        "by_client": [
            f"{k['n_clients']} sedes activas en el período.",
            f"Sede líder: {k['top_cli']} ({k['top_cli_pct']:.1f}% del volumen).",
            "Recomendación: alinear planeación de capacidad con la sede de mayor volumen.",
        ],
        "top_routes": [
            f"{k['n_routes']} rutas distintas atendidas.",
            f"Ruta líder: {k['top_route']} ({k['top_route_pct']:.1f}%).",
            f"El Top 10 concentra el {k['top10_route_pct']:.1f}% de la operación.",
        ],
        "top_drivers": [
            f"{k['n_drivers']} conductores únicos.",
            f"Conductor líder: {k['top_drv']} ({k['top_drv_pct']:.1f}%).",
            f"Top 10 concentra {k['top10_drv_pct']:.1f}% del volumen.",
        ],
        "vehicle_types": [
            f"{k['n_vehicle_types']} tipos de vehículo en operación.",
            f"Tipo dominante: {k['top_veh']} ({k['top_veh_pct']:.1f}%).",
            "La mezcla refleja el mix de servicio dominante.",
        ],
        "keepers": [
            f"{k['n_keepers']} tenedores aportan flota.",
            f"Tenedor líder: {k['top_kee']} ({k['top_kee_pct']:.1f}%).",
            f"Top 5 tenedores: {k['top5_kee_pct']:.1f}% — concentración relevante.",
        ],
        "manifests": [
            f"Tasa terminal global: {k['terminal_rate']:.1f}%.",
            "Línea de referencia: 95% — la operación se mantiene cercana al objetivo.",
        ],
        "cargo_types": [
            f"Categoría dominante: {k['top_merc']} ({k['top_merc_pct']:.1f}%).",
            "Recomendación: estandarizar el catálogo (eliminar duplicados por tildes/mayúsculas).",
        ],
    }


def _fortalezas(k: Kpis) -> list[tuple[str, str]]:
    return [
        ("Volumen sostenido", f"{fmt_int(k['total'])} servicios efectivos en {k['n_months']} meses · operación estable"),
        ("Cobertura amplia", f"{k['n_routes']} rutas únicas y {k['n_clients']} sedes atendidas"),
        ("Trazabilidad sólida", f"{k['terminal_rate']:.1f}% de manifiestos en estado terminal"),
        ("Red de aliados robusta", f"{k['n_drivers']} conductores y {k['n_keepers']} tenedores activos"),
        ("Mix de servicio claro", "Permite planeación de flota dirigida por modalidad"),
    ]


def _oportunidades(k: Kpis) -> list[tuple[str, str]]:
    return [
        ("Diversificar tenedores", f"Top 5 aporta {k['top5_kee_pct']:.1f}% — formalizar respaldos contractuales"),
        ("Banca de conductores", f"Top 10 cubre {k['top10_drv_pct']:.1f}% del volumen — ampliar y rotar"),
        ("Estandarizar catálogo", "Eliminar duplicados por tildes y mayúsculas en condiciones de transporte"),
        ("Reducir cola de Activos", "Seguimiento diario para cerrar manifiestos abiertos"),
        ("Capturar peso transportado", "Habilita KPIs de productividad y costo unitario por kg"),
    ]


def _ten_indicators(k: Kpis) -> list[Indicator]:
    """The 10 KPIs validated with Fleischmann (no financial info)."""
    return [
        Indicator(
            name="Volumen mensual de servicios",
            question="¿Cuál es la cadencia operativa del período?",
            formula="Conteo de filas agrupado por archivo_origen.",
            columns=["archivo_origen"],
            granularity="mensual",
            frequency="mensual",
            confidence="alta",
            reason="archivo_origen sin nulos y particiona el período naturalmente.",
        ),
        Indicator(
            name="Mix de tipo de servicio",
            question="¿Qué proporción ocupa cada modalidad de servicio?",
            formula="Conteo de filas por service_type, expresado como porcentaje del total.",
            columns=["service_type"],
            granularity="categórica",
            frequency="mensual",
            confidence="alta",
            reason="service_type con baja cardinalidad y 0% nulos.",
        ),
        Indicator(
            name="Distribución por sede cliente",
            question="¿Cómo se reparte la operación entre las sedes del cliente?",
            formula="Conteo de filas por client_name.",
            columns=["client_name"],
            granularity="por sede",
            frequency="mensual",
            confidence="alta",
            reason="client_name sin nulos.",
        ),
        Indicator(
            name="Top rutas origen → destino",
            question="¿Qué corredores concentran la operación?",
            formula="Concatenar origin_city + destiny_city y contar.",
            columns=["origin_city", "destiny_city"],
            granularity="por par O-D",
            frequency="mensual",
            confidence="alta",
            reason="Ambas columnas sin nulos.",
        ),
        Indicator(
            name="Top conductores por volumen (Pareto)",
            question="¿Qué conductores concentran la operación?",
            formula="Conteo por worker_name con acumulado para identificar el 80%.",
            columns=["worker_name"],
            granularity="por conductor",
            frequency="mensual",
            confidence="alta",
            reason="worker_name sin nulos.",
        ),
        Indicator(
            name="Distribución por tipo de vehículo",
            question="¿Qué tipos de vehículo se están utilizando?",
            formula="Conteo por worker_vehicle_type.",
            columns=["worker_vehicle_type"],
            granularity="por tipo",
            frequency="mensual",
            confidence="alta",
            reason="worker_vehicle_type con baja nulidad y 6 categorías.",
        ),
        Indicator(
            name="Concentración por tenedor (Pareto)",
            question="¿Qué tenedores concentran la flota?",
            formula="Conteo por keeper, acumulado para detectar el 80%.",
            columns=["keeper"],
            granularity="por tenedor",
            frequency="mensual",
            confidence="alta",
            reason="keeper sin nulos.",
        ),
        Indicator(
            name="Tasa de manifiestos en estado terminal",
            question="¿Qué proporción de manifiestos cierra correctamente?",
            formula="(Manifiestos en {Cumplido, Liquidado y Cerrado}) / total, segmentado por mes.",
            columns=["estado_manifiesto", "archivo_origen"],
            granularity="mensual",
            frequency="semanal",
            confidence="alta",
            reason="estado_manifiesto sin nulos y 4 categorías limpias.",
        ),
        Indicator(
            name="Tipos de mercancía transportada",
            question="¿Qué condiciones de transporte predominan?",
            formula="Conteo por transport_conditions normalizado.",
            columns=["transport_conditions"],
            granularity="por categoría",
            frequency="mensual",
            confidence="media",
            reason="Hay duplicados por tildes/mayúsculas; la normalización los unifica.",
        ),
        Indicator(
            name="Cobertura geográfica",
            question="¿Cuántas rutas y sedes cubre la operación?",
            formula="n_unique de la combinación origin_city + destiny_city y de client_name.",
            columns=["origin_city", "destiny_city", "client_name"],
            granularity="acumulada",
            frequency="mensual",
            confidence="alta",
            reason="Las tres columnas son viables.",
        ),
    ]


def derive(report: EdaReport, kpis: Kpis, client_name: str = "") -> IndicatorBundle:
    """Produce the deterministic narrative bundle. Mirrors the LLM contract."""
    return IndicatorBundle(
        executive_summary=_resumen_text(kpis, client_name),
        indicators=_ten_indicators(kpis),
        fortalezas=_fortalezas(kpis),
        oportunidades=_oportunidades(kpis),
        bullets=_bullets(kpis),
    )
