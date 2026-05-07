from io import BytesIO

import pandas as pd
import pytest

from core.schema import REQUIRED_COLUMNS, SchemaError, validate


def test_validate_real_sample(excel_bytes):
    check = validate(excel_bytes)
    assert check.ok
    assert check.sheet_name == "FLEISCHMANN"
    assert check.n_rows > 1000
    assert check.n_cols >= 100
    assert not check.missing_required


def test_validate_rejects_missing_columns():
    df = pd.DataFrame({"foo": [1, 2], "bar": [3, 4]})
    buf = BytesIO()
    df.to_excel(buf, index=False)
    with pytest.raises(SchemaError) as exc:
        validate(buf.getvalue())
    msg = str(exc.value)
    # Mensaje debe nombrar columnas obligatorias faltantes.
    assert "Faltan columnas obligatorias" in msg
    for col in REQUIRED_COLUMNS[:3]:
        assert col in msg


def test_validate_rejects_garbage_bytes():
    with pytest.raises(SchemaError):
        validate(b"not an excel")
