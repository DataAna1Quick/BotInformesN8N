from core.eda import EdaReport, run as run_eda


def test_run_eda_filters_cancelled(excel_bytes):
    report = run_eda(excel_bytes)
    assert isinstance(report, EdaReport)
    # The fixture has 2464 raw rows; filter drops 50 (5- and 7-Cancelado).
    assert report.n_rows_original == 2464
    assert report.n_rows_filtered == 2414
    assert report.period_label == "Ene–May"
    assert report.months == ["Ene", "Feb", "Mar", "Abr", "May"]


def test_run_eda_marks_constants_as_descartar(excel_bytes):
    report = run_eda(excel_bytes)
    cols = report.columns
    # company_name / line / BDT / bill_number are constant or near-constant in the fixture.
    for c in ("company_name", "line", "BDT", "bill_number"):
        assert cols[c].verdict == "descartar"


def test_run_eda_marks_dimensions(excel_bytes):
    report = run_eda(excel_bytes)
    cols = report.columns
    # service_type has 4 unique values → viable_dimensión.
    assert cols["service_type"].verdict == "viable_dimensión"
    assert cols["client_name"].verdict == "viable_dimensión"
