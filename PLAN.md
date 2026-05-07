# PLAN — BotInformesN8N

**Repo:** `BotInformesN8N` · **Hosting Streamlit:** Streamlit Community Cloud (no GitHub Pages — Pages es estático)
**Carpeta de trabajo:** `C:\Users\Quick\OneDrive\OneDrive - Quick Help SAS\Documentos\Proyecto_Informes_Automaticos`
**Origen del pipeline:** se reutilizan los módulos ya validados en el proyecto Fleischmann (`eda_fleischmann.py` + `build_ppt_v2.py` + sub-agente `indicator-analyst`).

---

## 1. Objetivo

Aplicación web (Streamlit) que cualquier usuario interno pueda usar para:

1. Iniciar sesión con un único password (`QuickHelp2026`).
2. Subir un Excel con la **estructura n8n estándar** (la misma que tiene la operación Fleischmann hoy: 108 columnas, 1 hoja).
3. Subir el **logo del cliente** que recibirá el reporte.
4. Generar y descargar una presentación PowerPoint gerencial con la identidad visual:
   - **Quick Help** (proveedor — logos y colores ya integrados al repo).
   - **Cliente** (logo subido + paleta automática derivada del logo, o color custom).
5. La narrativa de indicadores se genera con **Claude Sonnet 4.6** vía Anthropic API; si la API falla o se queda sin créditos, se usa la **plantilla determinística por defecto**.

Adicionalmente, una **consola de desarrollo en PyQt6** (lanzada desde un `.bat`) permite al equipo de Quick Help ajustar parámetros de la app Streamlit sin tocar código: prompts del LLM, paleta default, slides activos, ver consumo de API, correr pruebas locales.

---

## 2. Componentes del sistema

```
┌──────────────────────────────────────────────────────────────┐
│  STREAMLIT APP (cara al usuario, deploy en Streamlit Cloud)  │
│  ├─ Login (password gate, hash bcrypt)                       │
│  ├─ Upload Excel + Upload logo cliente                       │
│  ├─ Pipeline: schema → eda → indicators(LLM/template) → ppt  │
│  └─ Descarga .pptx                                           │
└──────────────────────────────────────────────────────────────┘
                              ▲
                              │ comparten mismos módulos core/
                              │
┌──────────────────────────────────────────────────────────────┐
│  PYQT6 DEV CONSOLE (interna, lanzada por .bat)               │
│  ├─ Editor de prompts del LLM                                │
│  ├─ Editor de paleta y slides default                        │
│  ├─ Monitor de consumo Anthropic API                         │
│  └─ Test runner: ejecuta pipeline local con un Excel mock    │
└──────────────────────────────────────────────────────────────┘
```

**Una sola fuente de verdad** para la lógica: `streamlit_app/core/`. La consola PyQt importa esos mismos módulos — no se duplica nada.

---

## 3. Estructura del repo

```
BotInformesN8N/                          ← repo GitHub
├── streamlit_app/
│   ├── app.py                           ← entry point
│   ├── pages/
│   │   ├── 1_Iniciar_sesion.py
│   │   └── 2_Generar_informe.py
│   ├── core/
│   │   ├── auth.py                      ← password gate + bcrypt
│   │   ├── schema.py                    ← valida estructura n8n
│   │   ├── eda.py                       ← refactor de eda_fleischmann.py
│   │   ├── indicators.py                ← plantilla determinística
│   │   ├── llm_indicators.py            ← Anthropic SDK + cache + fallback
│   │   ├── ppt_builder.py               ← refactor de build_ppt_v2.py
│   │   ├── pipeline.py                  ← orquestador
│   │   ├── color_extractor.py           ← extrae paleta del logo cliente
│   │   └── prompts/
│   │       └── indicator_analyst.md     ← prompt editable desde dev console
│   ├── assets/
│   │   ├── logo_quick.png
│   │   └── default_palette.json
│   ├── requirements.txt
│   └── .streamlit/
│       ├── config.toml
│       └── secrets.toml.example         ← plantilla, NO se commitea el real
├── dev_console/
│   ├── console.py                       ← PyQt6 main window
│   ├── modules/
│   │   ├── prompt_editor.py
│   │   ├── palette_editor.py
│   │   ├── api_monitor.py
│   │   ├── test_runner.py
│   │   └── slides_toggle.py
│   └── requirements.txt
├── tests/
│   ├── conftest.py
│   ├── fixtures/                        ← Excel mock pequeño
│   ├── test_eda.py
│   ├── test_indicators.py
│   └── test_ppt_builder.py
├── docs/
│   ├── PLAN.md                          ← este archivo (vive aquí en local)
│   ├── api_usage_plan.md
│   ├── architecture.md
│   ├── deployment.md
│   └── prompts.md
├── .github/
│   └── workflows/
│       └── tests.yml                    ← pytest en push
├── run_dev_console.bat                  ← lanza la consola PyQt
├── run_streamlit_local.bat              ← prueba local de Streamlit
├── .gitignore                           ← incluye secrets.toml, .venv, output/
├── README.md
└── pyproject.toml
```

> **Nota local:** durante el desarrollo, el repo vive en
> `C:\Users\Quick\OneDrive\OneDrive - Quick Help SAS\Documentos\Proyecto_Informes_Automaticos`.
> El `.git` apuntará al remoto `github.com/<org>/BotInformesN8N`.

---

## 4. Flujo del usuario en la app Streamlit

1. **Login**
   - Input password único.
   - Comparación contra hash bcrypt (`QuickHelp2026` → hash hardcoded en `auth.py`, no en plain text).
   - Sesión persistida en `st.session_state`. Logout disponible.

2. **Generar informe** (página principal post-login)
   - **Paso 1**: Drag & drop del Excel (validación instantánea de estructura n8n; mensaje claro si faltan columnas).
   - **Paso 2**: Drag & drop del logo del cliente (PNG/JPG/SVG → convertido a PNG si hace falta).
   - **Paso 3**: Inputs:
     - Nombre del cliente (autocompletado del nombre del archivo Excel si aplica).
     - Subtítulo (default: "Visión integral del servicio logístico").
     - Color primario del cliente (color picker; default = color dominante extraído del logo).
     - Toggle "Análisis con IA" (ON por defecto si la API tiene créditos; se valida con un health check al cargar la página).
   - **Paso 4**: Botón **Generar PPT** → progress bar con etapas:
     - `Validando Excel…`
     - `Ejecutando análisis exploratorio…`
     - `Derivando indicadores (IA / plantilla)…`
     - `Construyendo presentación…`
     - `Listo`
   - **Paso 5**: Botón **Descargar `.pptx`** + preview de portada.

3. **Errores manejados sin traceback:**
   - Excel sin estructura n8n → mensaje específico ("falta la columna `total_billing`, etc.").
   - Logo demasiado pequeño → warning.
   - API key inválida o sin créditos → fallback automático a plantilla + badge "Modo plantilla".
   - Excel con 0 filas tras filtros → error claro.

---

## 5. Pipeline (lógica central, compartida)

```python
def run_pipeline(excel_bytes, client_logo_bytes, client_name, client_color,
                 use_llm: bool, progress_cb) -> bytes:
    progress_cb("Validando estructura...")
    schema.validate(excel_bytes)

    progress_cb("Análisis exploratorio...")
    report = eda.run(excel_bytes, filters=DEFAULT_FILTERS)

    progress_cb("Derivando indicadores...")
    if use_llm:
        try:
            kpis = llm_indicators.propose(report, client_name)
        except (LLMQuotaError, LLMUnavailableError) as e:
            progress_cb(f"⚠ IA no disponible ({e}). Usando plantilla.")
            kpis = indicators.derive(report)
    else:
        kpis = indicators.derive(report)

    progress_cb("Construyendo PPT...")
    palette = color_extractor.from_logo(client_logo_bytes, primary=client_color)
    pptx_bytes = ppt_builder.build(report, kpis, client_name,
                                    client_logo_bytes, palette)
    progress_cb("Listo")
    return pptx_bytes
```

`DEFAULT_FILTERS` incluye `service_state ∉ {5 - Cancelado, 7 - Finalizado Cancelado}` y se puede editar desde la consola PyQt.

---

## 6. Consola PyQt6 de desarrollo

Lanzada por `run_dev_console.bat`:

```bat
@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe python -m venv .venv
call .venv\Scripts\activate
pip install -q -r dev_console\requirements.txt
python dev_console\console.py
```

### Pestañas

| Pestaña | Funcionalidad |
|---|---|
| **Prompts** | Editor de texto sobre `core/prompts/indicator_analyst.md`. Botón "Probar prompt" ejecuta una llamada a Claude con un EDA de fixture y muestra la respuesta. |
| **Paleta** | Editor de `assets/default_palette.json`: primary, accent, dark, success, alert. Color pickers + preview de KPI card. |
| **Slides** | Lista de los 13 slides actuales con toggle ON/OFF y reorden por drag. Se persiste en `assets/slides_config.json`. |
| **API Monitor** | Lee `dev_console/.api_log.jsonl`. Tabla con: fecha, modelo, input/output tokens, costo estimado, fallback sí/no. Total acumulado. |
| **Test runner** | Selector de Excel de prueba → corre pipeline completo local → muestra logs y abre el `.pptx` resultante. Equivalente al flujo Streamlit pero offline. |

Todos los cambios son archivos de configuración versionables; no toca código fuente.

---

## 7. Plan de uso de Anthropic API (resumen — detalle en `docs/api_usage_plan.md`)

- **Modelo default**: `claude-haiku-4-5-20251001` (~$0,003 por PPT). Toggle a `claude-sonnet-4-6` desde la consola PyQt si se quiere mejor calidad puntual.
- **Una sola llamada por generación**: input = EDA JSON resumido + prompt del sub-agente, output = JSON con los 10 indicadores.
- **Prompt caching** del system prompt + esquema (estable entre llamadas) → ahorra ~70% del costo de input.
- **Pre-flight health check** al cargar la página Streamlit: 1-token completion para verificar que la key funciona y hay créditos. Resultado cacheado por sesión.
- **Fallback automático** si la API responde 401 / 429 / `insufficient_quota` → plantilla determinística (idéntica a la actual). El usuario ve un badge claro "Modo plantilla".
- **Logging local** (`dev_console/.api_log.jsonl`) con tokens y costo por llamada para que la consola PyQt grafique consumo.
- **Costo estimado** por generación: ~USD 0,02–0,05 con Sonnet + caching; ~USD 0,002–0,005 con Haiku.

La key se guarda **únicamente** en `streamlit_app/.streamlit/secrets.toml` (no commiteado) y, en local, en variable de entorno `ANTHROPIC_API_KEY` o en QSettings de la consola PyQt (cifrado vía `keyring`).

---

## 8. Seguridad — checklist obligatorio

- [ ] **Rotar la API key compartida** en console.anthropic.com en cuanto el setup esté listo. La actual quedó en historial de chat.
- [ ] `secrets.toml` en `.gitignore`. Solo `secrets.toml.example` se commitea.
- [ ] Password `QuickHelp2026` se hashea con `bcrypt` antes de hardcodear en `auth.py`. Nunca se compara en texto plano.
- [ ] Los logos subidos por el usuario **no se persisten** en el servidor más allá de la sesión (`st.session_state` + descarga directa, sin escritura a disco compartido).
- [ ] El `.streamlit/secrets.toml` se sube manualmente a Streamlit Cloud (panel "Secrets"), no por git.
- [ ] Si el repo se hace público, NO subir el log con tokens consumidos (`.api_log.jsonl` en `.gitignore`).

---

## 9. Plan de implementación por fases

| Fase | Entregable | Tiempo |
|---|---|---|
| **F0 — Bootstrap** | Carpeta del proyecto, `git init`, `pyproject.toml`, `.gitignore`, requirements.txt, README skeleton. Migrar logos Quick desde la carpeta Fleischmann. | 0.25 d |
| **F1 — Core modules** | Refactor `eda_fleischmann.py` → `core/eda.py`. Refactor `build_ppt_v2.py` → `core/ppt_builder.py` parametrizado. `core/indicators.py` con plantilla. `core/schema.py` con las 108 columnas. Tests pytest. | 0.75 d |
| **F2 — LLM layer** | `core/llm_indicators.py` con Anthropic SDK, prompt caching, fallback robusto, health check, logging. `core/prompts/indicator_analyst.md` editable. | 0.5 d |
| **F3 — Streamlit app** | `app.py`, login con bcrypt, página de generación, integración pipeline, descarga del .pptx, manejo de errores, badge IA/plantilla. | 1.0 d |
| **F4 — Color extractor** | `core/color_extractor.py`: dominante via k-means de pixeles (PIL + sklearn) → genera paleta complementaria. | 0.25 d |
| **F5 — Dev console PyQt** | `console.py` con las 5 pestañas. `.bat` lanzador. Persistencia de configs en JSON. | 1.0 d |
| **F6 — Deployment** | Push a GitHub, conectar Streamlit Cloud, configurar secrets, smoke test en producción, README final. | 0.5 d |
| **F7 — Endurecimiento** | CI con pytest, manejo de PPT con Office 2013/2016/365 (fallback PNG), accesibilidad de UI. | 0.5 d |

**Total estimado: ~5 días de trabajo enfocado.**

---

## 10. Criterios de aceptación

- ✅ Usuario externo abre la URL pública, ingresa `QuickHelp2026`, sube Excel + logo, recibe `.pptx` en <90 s.
- ✅ La PPT generada para Fleischmann es **visualmente equivalente** a `Presentacion_Operacion_Fleischmann_v2.pptx`.
- ✅ Si la API key no tiene créditos, la app funciona y entrega plantilla en vez de fallar.
- ✅ Equipo Quick Help puede cambiar el prompt del LLM o la paleta default desde la consola PyQt sin editar código.
- ✅ Tests pytest verdes en CI.
- ✅ Ningún secreto en el repo público.

---

## 11. Decisiones tomadas (✅ confirmadas)

| # | Decisión | Detalle |
|---|---|---|
| 1 | **Hosting** | Streamlit Community Cloud (plan free) |
| 2 | **Modelo Claude default** | `claude-haiku-4-5-20251001` (~USD 0,003 por PPT). Toggle a Sonnet desde consola PyQt si se requiere narrativa más rica para un caso puntual. |
| 3 | **Color del cliente** | Extracción **automática** del logo (k-means). No hay color picker manual ni perfiles persistidos. |
| 4 | **Datos del cliente** | Cada generación pide al usuario **logo + nombre del cliente**. Nada se guarda entre sesiones. |
| 5 | **Idioma** | Solo español. |
| 6 | **Slides editables** | Desde consola PyQt: toggle ON/OFF, reorden, y edición de textos default. |
| 7 | **Scope** | La app **solo genera** PPTs nuevas. **No edita** PPTs existentes — no hay flujo de re-importar `.pptx`. |

## 12. Próximo paso

Implementación inmediata en este orden:

- **F0 — Bootstrap**: estructura del repo, `git init`, `pyproject.toml`, `requirements.txt`, `.gitignore`, README, copiar logo Quick Help y un Excel de prueba.
- **F1 — Core modules**: refactor `eda_fleischmann.py` → `core/eda.py` puro · refactor `build_ppt_v2.py` → `core/ppt_builder.py` parametrizado por `ClientConfig` · `core/indicators.py` con plantilla determinística · `core/schema.py` con validación de las 108 columnas n8n · `core/color_extractor.py` con k-means · tests pytest verdes.

Tras F1 entrego un punto de control donde verifiquemos que la PPT sale **idéntica** a la actual de Fleischmann antes de continuar con la capa LLM, Streamlit y la consola PyQt.
