from core.eda import run as run_eda
from core.indicators import IndicatorBundle, derive
from core.metrics import compute


def test_derive_returns_bundle(excel_bytes):
    report = run_eda(excel_bytes)
    kpis = compute(report)
    bundle = derive(report, kpis, "Fleischmann")
    assert isinstance(bundle, IndicatorBundle)
    assert len(bundle.indicators) == 10
    assert bundle.executive_summary
    assert len(bundle.fortalezas) >= 3
    assert len(bundle.oportunidades) >= 3
    assert "volume_month" in bundle.bullets
    assert "manifests" in bundle.bullets


def test_indicators_use_only_viable_columns(excel_bytes):
    report = run_eda(excel_bytes)
    kpis = compute(report)
    bundle = derive(report, kpis, "Fleischmann")
    # No indicador debería referenciar una columna marcada como 'descartar'.
    descartadas = {name for name, info in report.columns.items() if info.verdict == "descartar"}
    for ind in bundle.indicators:
        for col in ind.columns:
            assert col not in descartadas, f"{ind.name} referencia columna descartada: {col}"
