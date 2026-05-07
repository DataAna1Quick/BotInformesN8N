"""Computes the KPI dictionary consumed by `ppt_builder` from an EdaReport."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .eda import EdaReport, normalize_text, order_months


TERMINAL_STATES = {"Cumplido", "Liquidado y Cerrado"}


def _fmt_int(n) -> str:
    if pd.isna(n):
        return "—"
    return f"{int(n):,}".replace(",", ".")


def _shorten(name: str, n: int = 22) -> str:
    if not isinstance(name, str):
        return str(name)
    s = name.strip().title()
    return s if len(s) <= n else s[: n - 1] + "…"


def _title_case(s: str) -> str:
    if not isinstance(s, str):
        return str(s)
    return " ".join(w.capitalize() for w in s.lower().split())


@dataclass
class Kpis:
    raw: dict  # full dict consumed by ppt_builder

    def __getitem__(self, key):
        return self.raw[key]

    def __contains__(self, key):
        return key in self.raw

    def get(self, key, default=None):
        return self.raw.get(key, default)


def compute(report: EdaReport) -> Kpis:
    """Aggregate all numeric/textual KPIs needed by the PPT builder."""
    df = report.df_filtered
    months = report.months
    periodo = report.period_label
    total = len(df)

    n_clients = df["client_name"].nunique()
    n_drivers = df["worker_name"].nunique()
    n_keepers = df["keeper"].nunique()
    n_vehicle_types = df["worker_vehicle_type"].dropna().nunique()
    n_routes = df["ruta"].nunique()
    n_months = len(months)

    terminal_rate = df["estado_manifiesto"].isin(TERMINAL_STATES).sum() / total * 100

    # Volumen por mes
    vol = df.groupby("mes").size().reindex(months).fillna(0).astype(int)
    peak_month = vol.idxmax(); peak_val = int(vol.max())
    valley_month = vol.idxmin(); valley_val = int(vol.min())
    avg_month = float(vol.mean())
    peak_x = peak_val / avg_month if avg_month else 0

    # Service type
    st = df["service_type"].value_counts()
    st_top = str(st.index[0])
    st_top_pct = st.iloc[0] / st.sum() * 100

    # Clientes
    cli = df["client_name"].value_counts()
    top_cli = str(cli.index[0])
    top_cli_pct = cli.iloc[0] / cli.sum() * 100

    # Rutas (top 10 ya que el PPT muestra 10)
    rutas = df["ruta"].value_counts().head(10)
    top_route = str(rutas.index[0])
    top_route_pct = rutas.iloc[0] / total * 100
    top10_route_pct = rutas.sum() / total * 100

    # Conductores top 10
    drv = df["worker_name"].value_counts().head(10)
    drv_short = drv.copy()
    drv_short.index = [_shorten(n) for n in drv.index]
    top_drv = _shorten(str(drv.index[0]))
    top_drv_pct = drv.iloc[0] / total * 100
    top10_drv_pct = drv.sum() / total * 100

    # Vehículos
    veh = df["worker_vehicle_type"].dropna().value_counts()
    top_veh = str(veh.index[0])
    top_veh_pct = veh.iloc[0] / veh.sum() * 100

    # Keepers top 10
    kee = df["keeper"].value_counts().head(10)
    kee_short = kee.copy()
    kee_short.index = [_shorten(n) for n in kee.index]
    top_kee = _shorten(str(kee.index[0]))
    keeper_total = df["keeper"].notna().sum()
    top_kee_pct = kee.iloc[0] / keeper_total * 100
    top5_kee_pct = kee.head(5).sum() / keeper_total * 100

    # Manifiestos
    mfs = df["estado_manifiesto"].value_counts()
    state_order = ["Cumplido", "Liquidado y Cerrado", "Activo", "Anulado"]
    mfs_cats = [s for s in state_order if s in mfs.index]
    mfs_vals = [int(mfs[s]) for s in mfs_cats]

    # Tasa terminal por mes
    tmp = df.copy()
    tmp["terminal"] = tmp["estado_manifiesto"].isin(TERMINAL_STATES)
    by_m = tmp.groupby("mes")["terminal"].agg(["sum", "count"])
    by_m["rate"] = by_m["sum"] / by_m["count"] * 100
    by_m = by_m.reindex(months)

    # Mercancía
    merc = (
        df["transport_conditions"].dropna()
        .apply(normalize_text).value_counts().head(8)
    )
    merc_total = df["transport_conditions"].notna().sum()
    top_merc = _title_case(str(merc.index[0]))
    top_merc_pct = merc.iloc[0] / merc_total * 100

    return Kpis(raw=dict(
        periodo=periodo, total=total, n_clients=n_clients, n_drivers=n_drivers,
        n_keepers=n_keepers, n_vehicle_types=n_vehicle_types, n_routes=n_routes,
        n_months=n_months, terminal_rate=terminal_rate,

        vol_categories=list(vol.index), vol_values=[int(v) for v in vol.values],
        peak_month=peak_month, peak_val=peak_val, peak_x=peak_x,
        valley_month=valley_month, valley_val=valley_val,

        st_cats=list(st.index), st_vals=[int(v) for v in st.values],
        st_top=st_top, st_top_pct=st_top_pct, n_service_types=len(st),

        cli_cats=list(cli.index)[::-1],
        cli_vals=[int(v) for v in cli.values][::-1],
        top_cli=top_cli, top_cli_pct=top_cli_pct,

        route_cats=list(rutas.index)[::-1],
        route_vals=[int(v) for v in rutas.values][::-1],
        top_route=top_route, top_route_pct=top_route_pct, top10_route_pct=top10_route_pct,

        drv_cats=list(drv_short.index)[::-1],
        drv_vals=[int(v) for v in drv_short.values][::-1],
        top_drv=top_drv, top_drv_pct=top_drv_pct, top10_drv_pct=top10_drv_pct,

        veh_cats=list(veh.index), veh_vals=[int(v) for v in veh.values],
        top_veh=top_veh, top_veh_pct=top_veh_pct,

        kee_cats=list(kee_short.index), kee_vals=[int(v) for v in kee_short.values],
        top_kee=top_kee, top_kee_pct=top_kee_pct, top5_kee_pct=top5_kee_pct,

        mfs_cats=mfs_cats, mfs_vals=mfs_vals,
        term_months=list(by_m.index),
        term_rates=[round(float(r), 1) for r in by_m["rate"].fillna(0)],

        merc_cats=[_title_case(x) for x in merc.index][::-1],
        merc_vals=[int(v) for v in merc.values][::-1],
        top_merc=top_merc, top_merc_pct=top_merc_pct, n_merc=len(merc),
    ))


def fmt_int(n) -> str:
    """Public re-export for ppt_builder."""
    return _fmt_int(n)
