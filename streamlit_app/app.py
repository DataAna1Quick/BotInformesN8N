"""BotInformesN8N · Streamlit entry point.

Single-page app with two states:
  1. Login (password gate).
  2. Generador (upload Excel + logo + nombre cliente → PPT).
"""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

import streamlit as st

from core.auth import verify_password
from core.errors import (
    ClientNameMissingError,
    EmptyAfterFilterError,
    LogoInvalidError,
    PipelineError,
)
from core.llm_indicators import health_check
from core.pipeline import preview_palette, run_pipeline_full
from core.schema import SchemaError


APP_TITLE = "BotInformesN8N"
PROVIDER = "Quick Help SAS"
ASSETS = Path(__file__).parent / "assets"
LOGO_PROVIDER = ASSETS / "logo_quick.png"

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=str(LOGO_PROVIDER) if LOGO_PROVIDER.exists() else "📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _secret(key: str, default=None):
    try:
        return st.secrets.get(key, default)  # type: ignore[attr-defined]
    except Exception:
        return default


def _api_key() -> str | None:
    import os
    return _secret("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")


def _enable_llm_default() -> bool:
    return bool(_secret("ENABLE_LLM", True))


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { max-width: 880px; padding-top: 2rem; }
        .quick-card {
            background: #FFFFFF;
            border: 1px solid #E6E8EE;
            border-left: 4px solid #F4B400;
            border-radius: 6px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
        }
        .quick-card-title {
            font-size: 0.75rem;
            font-weight: 700;
            color: #7A7F8C;
            letter-spacing: 0.05em;
            margin-bottom: 0.4rem;
        }
        .quick-card-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #1B3D7A;
            line-height: 1.1;
        }
        .quick-card-footer {
            font-size: 0.85rem;
            color: #3F4452;
            margin-top: 0.4rem;
        }
        .badge { display: inline-block; padding: 0.15rem 0.6rem; border-radius: 999px;
                 font-size: 0.75rem; font-weight: 700; }
        .badge-ai      { background: #E8F5EF; color: #2C7A4E; }
        .badge-tpl     { background: #FFF8E1; color: #B07900; }
        .badge-error   { background: #FCE7E9; color: #C8102E; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _login_view() -> None:
    cols = st.columns([1, 2, 1])
    with cols[1]:
        if LOGO_PROVIDER.exists():
            st.image(str(LOGO_PROVIDER), width=140)
        st.markdown(f"### {APP_TITLE}")
        st.caption(f"{PROVIDER} · Generador automático de informes gerenciales")
        st.write("")
        with st.form("login", clear_on_submit=False):
            password = st.text_input("Contraseña", type="password",
                                     placeholder="Ingrese la contraseña")
            submitted = st.form_submit_button("Ingresar", use_container_width=True,
                                              type="primary")
        if submitted:
            if verify_password(password):
                st.session_state["authed"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")


def _badge_for_mode(used_llm: bool) -> str:
    if used_llm:
        return '<span class="badge badge-ai">Modo IA · Claude</span>'
    return '<span class="badge badge-tpl">Modo plantilla</span>'


def _generator_view() -> None:
    # Header
    cols = st.columns([6, 1])
    with cols[0]:
        st.markdown(f"### {APP_TITLE}")
        st.caption(f"{PROVIDER} · Generación de informes")
    with cols[1]:
        if st.button("Salir", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    st.divider()

    # API health badge
    api_key = _api_key()
    enable_llm_default = _enable_llm_default()
    health = st.session_state.get("api_health")
    if health is None:
        health = health_check(api_key) if api_key else {"ok": False, "reason": "no_key"}
        st.session_state["api_health"] = health

    if health["ok"]:
        st.markdown(
            f'<span class="badge badge-ai">✓ IA disponible · {health.get("model", "")}</span>',
            unsafe_allow_html=True,
        )
    else:
        reason = {
            "no_key": "no se configuró API key",
            "missing_api_key": "no se configuró API key",
            "api_key_invalid": "API key inválida",
            "no_credit": "sin créditos",
            "rate_limited": "rate limit",
        }.get(health["reason"], f"no disponible ({health['reason']})")
        st.markdown(
            f'<span class="badge badge-tpl">⚠ Modo plantilla · {reason}</span>',
            unsafe_allow_html=True,
        )

    st.write("")

    # Inputs
    with st.container(border=True):
        st.markdown("**1 · Datos del cliente**")
        client_name = st.text_input("Nombre del cliente",
                                    placeholder="Ej. Fleischmann")
        client_logo = st.file_uploader("Logo del cliente (PNG / JPG)",
                                       type=["png", "jpg", "jpeg"],
                                       accept_multiple_files=False)
        # Live palette preview
        if client_logo is not None:
            logo_bytes_preview = client_logo.getvalue()
            try:
                pal = preview_palette(logo_bytes_preview)
                pcols = st.columns([1, 4])
                with pcols[0]:
                    st.image(logo_bytes_preview, width=80)
                with pcols[1]:
                    st.markdown(
                        f'<div style="display:flex; gap:0.5rem; align-items:center;">'
                        f'<div style="width:32px; height:32px; border-radius:4px; '
                        f'background:{pal.primary}; border:1px solid #E6E8EE;"></div>'
                        f'<div><strong>Color principal detectado:</strong> '
                        f'<code>{pal.primary}</code></div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    st.caption("Este color se usará como acento del cliente en la PPT.")
            except Exception:
                st.warning("No se pudo procesar el logo para extraer color. Se usará el color default.")

    with st.container(border=True):
        st.markdown("**2 · Datos de la operación**")
        excel_file = st.file_uploader(
            "Excel con la estructura n8n estándar",
            type=["xlsx"], accept_multiple_files=False,
            help="El archivo debe tener las 108 columnas n8n. Si falta alguna, se indicará.",
        )

    with st.container(border=True):
        st.markdown("**3 · Opciones**")
        use_llm = st.toggle("Análisis con IA (Claude)",
                            value=health["ok"] and enable_llm_default,
                            disabled=not health["ok"],
                            help="Si está desactivado, se usa la plantilla determinística.")

    st.write("")
    can_generate = bool(client_name and excel_file)
    if not can_generate:
        st.info("Completa el nombre del cliente y carga el Excel para habilitar la generación.")

    if st.button("🚀 Generar presentación", type="primary",
                 use_container_width=True, disabled=not can_generate):
        _run_generation(
            excel_bytes=excel_file.read(),
            logo_bytes=client_logo.read() if client_logo else None,
            client_name=client_name.strip(),
            use_llm=use_llm and health["ok"],
            api_key=api_key,
        )


def _run_generation(*, excel_bytes: bytes, logo_bytes: bytes | None,
                    client_name: str, use_llm: bool, api_key: str | None) -> None:
    progress_box = st.empty()
    log_lines: list[str] = []

    def progress(msg: str) -> None:
        log_lines.append(msg)
        progress_box.markdown(
            "```\n" + "\n".join(log_lines[-12:]) + "\n```"
        )

    try:
        with st.spinner("Generando presentación..."):
            result = run_pipeline_full(
                excel_bytes,
                logo_bytes,
                client_name,
                use_llm=use_llm,
                api_key=api_key,
                progress_cb=progress,
            )
    except ClientNameMissingError as e:
        st.error(f"❌ {e}")
        return
    except SchemaError as e:
        st.error(f"❌ {e}")
        st.info("Revisa que el archivo provenga de la exportación n8n estándar.")
        return
    except EmptyAfterFilterError as e:
        st.error(f"❌ {e}")
        return
    except LogoInvalidError as e:
        st.error(f"❌ {e}")
        return
    except PipelineError as e:
        st.error(f"❌ {e}")
        return
    except Exception as e:
        st.error(f"❌ Falló la generación: {type(e).__name__}: {e}")
        return

    # Success view
    progress_box.empty()
    st.success("Presentación generada correctamente.")
    st.markdown(_badge_for_mode(result["used_llm"]), unsafe_allow_html=True)

    cols = st.columns(4)
    metrics = [
        ("Filas analizadas", f"{result['rows_filtered']:,}".replace(",", ".")),
        ("Período", result["period"]),
        ("Indicadores", result["n_indicators"]),
        ("Color cliente", result["palette_primary"]),
    ]
    for c, (label, val) in zip(cols, metrics):
        with c:
            st.markdown(
                f'<div class="quick-card">'
                f'<div class="quick-card-title">{label.upper()}</div>'
                f'<div class="quick-card-value">{val}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    today = datetime.now().strftime("%Y%m%d")
    safe_name = "".join(c if c.isalnum() else "_" for c in client_name)
    fname = f"Informe_{safe_name}_{today}.pptx"
    st.download_button(
        "⬇ Descargar presentación",
        data=result["pptx_bytes"],
        file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        use_container_width=True,
        type="primary",
    )


# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------

def main() -> None:
    _inject_css()
    if not st.session_state.get("authed"):
        _login_view()
    else:
        _generator_view()


if __name__ == "__main__":
    main()
