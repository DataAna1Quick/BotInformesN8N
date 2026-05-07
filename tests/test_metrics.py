from core.eda import run as run_eda
from core.metrics import compute


def test_metrics_match_v2_baseline(excel_bytes):
    """Numbers must match the validated v2 PPT baseline (Fleischmann fixture, post-filter)."""
    report = run_eda(excel_bytes)
    k = compute(report)

    assert k["total"] == 2414
    assert k["n_clients"] == 4
    assert k["n_drivers"] == 53
    assert k["n_keepers"] == 42
    assert k["n_vehicle_types"] == 6
    assert k["n_months"] == 5
    assert k["periodo"] == "Ene–May"

    # Cumplimiento ~96.85% with the filter applied.
    assert 96.5 <= k["terminal_rate"] <= 97.2

    # Pico debe ser uno de los meses cargados; valor positivo coherente.
    assert k["peak_month"] in ("Mar", "Feb", "Abr", "May")
    assert k["peak_val"] > k["valley_val"]

    # KPIs estructurales no vacíos.
    assert k["vol_categories"]
    assert k["st_cats"]
    assert k["mfs_cats"]
    assert k["term_rates"]
