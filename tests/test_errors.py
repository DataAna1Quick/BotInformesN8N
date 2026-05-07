"""Edge-case tests for the hardened pipeline."""
from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from core.color_extractor import extract_palette
from core.errors import (
    ClientNameMissingError,
    EmptyAfterFilterError,
    LogoInvalidError,
    SchemaInvalidError,
)
from core.pipeline import run_pipeline_full, preview_palette


def test_logo_svg_strict_raises():
    svg_bytes = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
    with pytest.raises(LogoInvalidError):
        extract_palette(svg_bytes, strict=True)


def test_logo_svg_non_strict_returns_default():
    svg_bytes = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
    p = extract_palette(svg_bytes, strict=False)
    assert p.primary == "#1B3D7A"


def test_logo_garbage_strict_raises():
    with pytest.raises(LogoInvalidError):
        extract_palette(b"garbage bytes that are not an image", strict=True)


def test_logo_pdf_strict_raises():
    with pytest.raises(LogoInvalidError):
        extract_palette(b"%PDF-1.5\n...", strict=True)


def test_preview_palette_never_raises():
    # All inputs go through preview_palette with strict=False
    assert preview_palette(None).primary
    assert preview_palette(b"<svg>").primary
    assert preview_palette(b"junk").primary


def test_pipeline_missing_client_name(excel_bytes, client_logo_bytes):
    with pytest.raises(ClientNameMissingError):
        run_pipeline_full(excel_bytes, client_logo_bytes, "")
    with pytest.raises(ClientNameMissingError):
        run_pipeline_full(excel_bytes, client_logo_bytes, "   ")


def test_pipeline_invalid_excel():
    df = pd.DataFrame({"foo": [1, 2]})
    buf = BytesIO()
    df.to_excel(buf, index=False)
    with pytest.raises(SchemaInvalidError):
        run_pipeline_full(buf.getvalue(), None, "ClienteX")


def test_pipeline_empty_after_filter(excel_bytes, monkeypatch):
    """If filters drop all rows the pipeline must raise EmptyAfterFilterError."""
    from core import eda

    real_run = eda.run

    def empty_run(*args, **kwargs):
        report = real_run(*args, **kwargs)
        report.df_filtered = report.df_filtered.iloc[0:0]
        report.n_rows_filtered = 0
        return report

    monkeypatch.setattr("core.pipeline.run_eda", empty_run)
    with pytest.raises(EmptyAfterFilterError):
        run_pipeline_full(excel_bytes, None, "ClienteX")
