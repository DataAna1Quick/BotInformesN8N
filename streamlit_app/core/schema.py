"""Schema validation for the n8n consolidated workbook."""
from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import pandas as pd

# Columns expected to drive the analysis. Missing any → hard error.
REQUIRED_COLUMNS = (
    "service_id",
    "service_type",
    "service_state",
    "client_name",
    "worker_name",
    "worker_vehicle_type",
    "keeper",
    "origin_city",
    "destiny_city",
    "estado_manifiesto",
    "transport_conditions",
    "archivo_origen",
)

# Columns expected by the n8n schema (108). Used only as a soft check.
EXPECTED_COLUMNS = (
    "its_paid", "pay_number", "its_billed", "bill_number", "service_id", "order_no",
    "service_type", "line", "date_time2", "created_at", "service_state",
    "total_billing", "total_pay_quicker", "base_rate", "base_freigth",
    "reference_rate", "reference_freigth", "reference_ica", "reference_retefuente",
    "reference_rate_discounts", "reference_freigth_discounts",
    "reference_rate_additional", "reference_freigth_additional", "manifest_base",
    "client_nid", "client_name", "worker_nid", "worker_name", "worker_email",
    "worker_mobile_phone", "company_name", "company_nid", "transport_conditions",
    "worker_car_plate", "worker_vehicle_type", "stop_evidence_links",
    "advances_value", "proyect", "ministry_weight", "product_description",
    "service_city_code", "keeper", "vehicle_keeper_nid", "owner",
    "vehicle_owner_nid", "origin_city", "destiny_city",
    "payment_advances_numbers_value", "balance_payment_advances_numbers_value",
    "manifiesto", "estado_manifiesto", "radicado_manifiesto",
    "created_at_manifiesto", "created_time_at_manifiesto", "consignment_summary",
    "remesa1", "estado1", "radicado1", "factura_remesa1", "fecha_factura1",
    "fecha_creacion_remesa1", "anticipo1", "valor1",
    "remesa2", "estado2", "radicado2", "factura_remesa2", "fecha_factura2",
    "fecha_creacion_remesa2", "archivo_origen", "anticipo2", "valor2",
    "remesa3", "estado3", "radicado3", "factura_remesa3", "fecha_factura3",
    "fecha_creacion_remesa3", "anticipo3", "valor3",
    "anticipo4", "valor4", "remesa4", "estado4", "radicado4", "factura_remesa4",
    "fecha_factura4", "fecha_creacion_remesa4",
    "remesa5", "estado5", "radicado5", "factura_remesa5", "fecha_factura5",
    "fecha_creacion_remesa5",
    "remesa6", "estado6", "radicado6", "factura_remesa6", "fecha_factura6",
    "fecha_creacion_remesa6",
    "remesa7", "estado7", "radicado7", "factura_remesa7", "fecha_factura7",
    "fecha_creacion_remesa7",
    "pbv", "BDT",
)

DEFAULT_SHEET_CANDIDATES = ("FLEISCHMANN", "Sheet1", "Hoja1")


class SchemaError(ValueError):
    """Raised when the uploaded Excel does not match the expected n8n shape."""


@dataclass
class SchemaCheck:
    sheet_name: str
    n_rows: int
    n_cols: int
    missing_required: list[str] = field(default_factory=list)
    missing_expected: list[str] = field(default_factory=list)
    extra_columns: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing_required


def _open_excel(source: bytes | str | Path | BytesIO) -> pd.ExcelFile:
    if isinstance(source, (str, Path)):
        return pd.ExcelFile(source, engine="openpyxl")
    if isinstance(source, bytes):
        return pd.ExcelFile(BytesIO(source), engine="openpyxl")
    return pd.ExcelFile(source, engine="openpyxl")


def pick_sheet(xls: pd.ExcelFile) -> str:
    """Pick the largest data sheet, preferring known names."""
    for name in DEFAULT_SHEET_CANDIDATES:
        if name in xls.sheet_names:
            return name
    # Fall back to whichever sheet has the most rows.
    sizes = {n: pd.read_excel(xls, sheet_name=n, nrows=1).shape[1] for n in xls.sheet_names}
    return max(sizes, key=sizes.get)


def validate(source: bytes | str | Path | BytesIO) -> SchemaCheck:
    """Validate that `source` is a readable Excel with the n8n structure.

    Raises SchemaError with an actionable message if a required column is missing.
    """
    try:
        xls = _open_excel(source)
    except Exception as e:
        raise SchemaError(f"No se pudo abrir el archivo Excel: {type(e).__name__}: {e}") from e

    if not xls.sheet_names:
        raise SchemaError("El archivo Excel no contiene hojas.")

    sheet = pick_sheet(xls)
    df = pd.read_excel(xls, sheet_name=sheet, nrows=0)
    cols = list(df.columns)

    missing_required = [c for c in REQUIRED_COLUMNS if c not in cols]
    missing_expected = [c for c in EXPECTED_COLUMNS if c not in cols]
    extras = [c for c in cols if c not in EXPECTED_COLUMNS]

    if missing_required:
        raise SchemaError(
            "El Excel no tiene la estructura n8n esperada. "
            f"Faltan columnas obligatorias: {', '.join(missing_required)}."
        )

    # Read full sheet just for row count (cheap because only column count was peeked above).
    full = pd.read_excel(xls, sheet_name=sheet)
    return SchemaCheck(
        sheet_name=sheet,
        n_rows=int(len(full)),
        n_cols=int(len(cols)),
        missing_required=missing_required,
        missing_expected=missing_expected,
        extra_columns=extras,
    )
