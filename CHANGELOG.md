# Changelog

Todos los cambios relevantes del proyecto se documentan acá. Formato basado en
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [0.1.0] — 2026-05-06

### Agregado
- **Pipeline core** (`streamlit_app/core/`) que convierte un Excel n8n en PPT:
  - `schema.py` valida estructura de 108 columnas con mensaje accionable.
  - `eda.py` análisis exploratorio puro con veredicto de viabilidad por columna.
  - `metrics.py` cálculo determinístico de KPIs.
  - `indicators.py` plantilla con 10 KPIs validados (sin información financiera).
  - `llm_indicators.py` wrapper Anthropic Claude con prompt caching, tool use,
    health check y fallback robusto.
  - `color_extractor.py` extracción de paleta vía k-means con filtro de neutrales.
  - `ppt_builder.py` constructor parametrizado por `ClientConfig`.
  - `pipeline.py` orquestador end-to-end.
- **App Streamlit** (`streamlit_app/app.py`) con login bcrypt (`QuickHelp2026`),
  upload de Excel + logo + nombre, preview de paleta extraída del logo en vivo,
  badge de estado de IA, log de progreso en tiempo real, descarga de `.pptx`.
- **Consola PyQt6** (`dev_console/`) con 5 pestañas: prompts, paleta, slides,
  monitor de API y test runner.
- **CI** con GitHub Actions corriendo pytest en cada push/PR.
- **37 tests** verdes cubriendo schema, EDA, metrics, indicators, color extractor,
  ppt builder, LLM (mockeado), auth, errors, e2e y AppTest de Streamlit.
- **Validación de paridad visual** con la baseline Fleischmann v2 (13/13 slides
  estructuralmente equivalentes).
- **Documentación**: PLAN.md, architecture.md, api_usage_plan.md, deployment.md,
  decisions.md, manual_usuario.md, first_commit.md.

### Seguridad
- Hash bcrypt del password embebido en `core/auth.py`; nunca en plain text.
- API key Anthropic se carga de `st.secrets` o env var, nunca del repo.
- `.gitignore` cubre secrets, logs, fixtures con datos reales y outputs.
- Logos de clientes no se persisten más allá de la sesión.

### Decisiones (ver `docs/decisions.md`)
- Hosting: Streamlit Community Cloud (free).
- Modelo Claude default: Haiku 4.5 (~USD 0,003 por PPT).
- Color del cliente: extracción automática del logo, sin override manual.
- Idioma: solo español.
- App **solo genera** PPTs nuevas; no modifica PPTs existentes.

---

## [Unreleased]

Ideas para versiones futuras:

- Conversor de seriales Excel → fechas reales (`date_time2`, `created_at`),
  habilitando series diarias y lead-time entre creación y manifiesto.
- Indicadores monetarios opcionales con bandera "uso interno Quick Help"
  (no se mostraría a clientes).
- Soporte multi-idioma (i18n) si llega un cliente internacional.
- Cache de generaciones idénticas (mismo Excel + cliente) → reusar PPT.
- Plantillas de slides industry-specific (logística, retail, manufactura).
