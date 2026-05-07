# BotInformesN8N

Generador automático de presentaciones gerenciales a partir de exportes n8n.
**Quick Help SAS** · 2026.

[![tests](https://github.com/<org>/BotInformesN8N/actions/workflows/tests.yml/badge.svg)](https://github.com/<org>/BotInformesN8N/actions/workflows/tests.yml)

---

## ¿Qué es esto?

Una app web (Streamlit) que el equipo Quick Help puede usar para generar un PPT
gerencial personalizado por cliente, partiendo del Excel n8n estándar (108 columnas).
Cada generación toma ~30 segundos y produce un `.pptx` con la identidad visual
del cliente extraída automáticamente de su logo.

Adicionalmente, una **consola PyQt6** permite al equipo ajustar prompts, paleta,
slides activos y monitorear el consumo de la API de Anthropic — sin tocar código.

---

## Arquitectura

```
streamlit_app/        ← cara al usuario (deploy en Streamlit Cloud)
  app.py
  core/               ← single source of truth: lógica reutilizable
    schema.py         valida estructura del Excel n8n
    eda.py            análisis exploratorio puro
    metrics.py        cálculo de KPIs
    indicators.py     plantilla determinística (10 KPIs)
    llm_indicators.py wrapper Claude con caching + fallback
    color_extractor.py k-means sobre el logo cliente
    ppt_builder.py    PPTBuilder parametrizado por ClientConfig
    pipeline.py       orquestador
  assets/             logo Quick Help, paleta default, config slides

dev_console/          ← consola interna (PyQt6, lanzada por .bat)
  console.py
  modules/
    prompt_editor.py
    palette_editor.py
    slides_editor.py
    api_monitor.py
    test_runner.py

tests/                ← pytest (24 tests verdes)
docs/                 ← PLAN.md, architecture, API usage, deployment, decisions
```

---

## Uso local

### Streamlit (la app)

```cmd
run_streamlit_local.bat
```

- Crea venv si no existe, instala dependencias.
- Abre `http://localhost:8501`.
- Login: `QuickHelp2026`.
- Cargar Excel n8n + logo cliente + nombre → descarga `.pptx`.

Para activar análisis con IA, crear `streamlit_app/.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

### Dev console (interna)

```cmd
run_dev_console.bat
```

5 pestañas:
1. **Prompts** — editor del system prompt + botón "Probar prompt".
2. **Paleta** — color pickers para los defaults.
3. **Slides** — toggle ON/OFF, reorden, edición de títulos.
4. **API Monitor** — consumo acumulado, tabla de llamadas, fallbacks.
5. **Test runner** — corre el pipeline local con un Excel de prueba.

---

## Estructura del Excel n8n esperada

108 columnas. Las **obligatorias** para que el pipeline funcione:

```
service_id, service_type, service_state, client_name, worker_name,
worker_vehicle_type, keeper, origin_city, destiny_city,
estado_manifiesto, transport_conditions, archivo_origen
```

Si falta alguna, la app muestra un mensaje específico (sin traceback).

---

## Tests

```cmd
pytest -q
```

24 tests:
- `test_auth` (3) · `test_color_extractor` (2) · `test_eda` (3)
- `test_indicators` (2) · `test_llm_indicators` (8 con SDK mockeado)
- `test_metrics` (1) · `test_ppt_builder` (1) · `test_schema` (3)

Validación de paridad visual con la presentación baseline:

```cmd
python tests/compare_baseline.py
```

---

## Deploy a Streamlit Community Cloud

Ver [`docs/deployment.md`](./docs/deployment.md). Resumen:

1. Push del repo a GitHub.
2. Crear app en streamlit.io/cloud, apuntando a `streamlit_app/app.py`.
3. Configurar secrets en el panel de Streamlit (no en el repo):
   - `ANTHROPIC_API_KEY`
   - `APP_PASSWORD_HASH` (opcional — el hash default ya está en `core/auth.py`)

---

## Documentación

| Archivo | Contenido |
|---|---|
| [`PLAN.md`](./PLAN.md) | Plan maestro, fases, criterios de aceptación |
| [`docs/architecture.md`](./docs/architecture.md) | Diagrama de capas, contratos, flujo de datos |
| [`docs/api_usage_plan.md`](./docs/api_usage_plan.md) | Estrategia de uso de Anthropic API + fallback |
| [`docs/deployment.md`](./docs/deployment.md) | Pasos de deploy a Streamlit Cloud |
| [`docs/decisions.md`](./docs/decisions.md) | Registro de decisiones tomadas |

---

## Seguridad

- ⚠ Nunca commitear `secrets.toml`, `.env`, ni `dev_console/.api_log.jsonl`.
- ⚠ Rotar la API key de Anthropic cada 90 días.
- ⚠ El password `QuickHelp2026` está hasheado con bcrypt; cambiar requiere generar
  nuevo hash y reemplazarlo en `core/auth.py` o en `secrets.toml`.

---

## Estado

✅ **F0** Bootstrap · ✅ **F1** Core modules + paridad visual con baseline
✅ **F2** LLM layer · ✅ **F3** Streamlit app · ✅ **F4** Color extractor
✅ **F5** Dev console PyQt · ⏳ **F6** Deploy a Streamlit Cloud

---

Quick Help SAS · Equipo de Operaciones y Analítica · 2026
