# CLAUDE.md — BotInformesN8N

Contexto que Claude Code carga automáticamente al abrir este repo.
**Léelo siempre antes de actuar. No lo dupliques en respuestas.**

---

## Qué es este proyecto

App **Streamlit** + consola **PyQt6** que toma un Excel n8n estándar (108 columnas) y
genera un PPT gerencial personalizado por cliente. Usado por **Quick Help SAS** para
todos sus clientes (Fleischmann, Éxito, etc.).

- **App pública** desplegada en Streamlit Community Cloud · login con password
  `QuickHelp2026` (hash bcrypt en `core/auth.py`).
- **Consola interna** (PyQt6, lanzada por `.bat`) edita prompts, paleta, slides
  y monitorea consumo de Anthropic API.
- **Repo:** https://github.com/DataAna1Quick/BotInformesN8N
- **Versión actual:** 0.1.0 · main protegida

---

## Estructura

```
streamlit_app/
  app.py                ← entrada Streamlit
  core/                 ← lógica de negocio, sin UI (importable desde PyQt también)
    schema.py           valida Excel n8n
    eda.py              análisis exploratorio puro
    metrics.py          KPIs determinísticos
    indicators.py       plantilla 10 KPIs
    llm_indicators.py   wrapper Anthropic (Haiku default)
    color_extractor.py  k-means sobre logo cliente
    ppt_builder.py      PPTBuilder parametrizado
    pipeline.py         orquestador
    auth.py             bcrypt password gate
    errors.py           jerarquía de errores del pipeline
    prompts/            prompts editables
  assets/               logo Quick Help, paleta, slides config
  .streamlit/           config + secrets (secrets.toml NO se commitea)

dev_console/            ← PyQt6 admin
  console.py            QMainWindow con 5 tabs
  modules/              prompt_editor, palette_editor, slides_editor,
                        api_monitor, test_runner

tests/                  ← pytest (37 verdes)
docs/                   ← PLAN, architecture, api_usage_plan, deployment,
                        decisions, manual_usuario, contributing, first_commit
.github/workflows/      ← CI (pytest)
```

---

## Sub-agentes especializados (en `.claude/agents/`)

**Delega tareas complejas a un sub-agente** para no quemar contexto. Mapa:

| Tarea | Sub-agente | Tools |
|---|---|---|
| Cambios en `streamlit_app/core/*.py` | `bot-core-engineer` | Read, Write, Edit, Bash, Grep, Glob |
| Cambios en `streamlit_app/app.py` o UI Streamlit | `bot-streamlit-ui` | Read, Write, Edit, Bash |
| Cambios en `dev_console/` | `bot-pyqt-console` | Read, Write, Edit, Bash |
| Tunear prompt LLM, modelo, costo | `bot-llm-tuner` | Read, Write, Edit |
| Agregar / correr tests pytest | `bot-test-engineer` | Read, Write, Edit, Bash |
| Documentación (markdown) | `bot-docs-writer` | Read, Write, Edit |
| Deploy, CI/CD, secrets | `bot-deploy-ops` | Read, Write, Edit, Bash |

El **agente orquestador** principal (`bot-informes-builder`) coordina cuando una
tarea cruza áreas (ej. "agregar nuevo slide" toca core + tests + docs).

---

## Decisiones inviolables

1. **Solo español** en UI, prompts y output.
2. **Modelo Anthropic default**: `claude-haiku-4-5-20251001`. Sonnet 4.6 solo
   como toggle puntual.
3. **Una sola llamada al LLM** por generación, con prompt caching del system
   prompt.
4. **Fallback a plantilla** en cualquier error LLM (auth, quota, network) —
   nunca dejar al usuario sin PPT.
5. **No información financiera** en la PPT (sin `total_billing`, sin tarifas,
   sin pagos al transportador).
6. **App solo genera** PPTs nuevas — no edita existentes.
7. **Cliente sin perfiles persistidos** — cada uso pide logo + nombre.
8. **Una sola fuente de verdad**: la lógica vive en `streamlit_app/core/`.
   Streamlit y PyQt importan los mismos módulos.
9. **No commitear secrets**: API key, hash override, logos cliente, Excels reales.
10. **Tests verdes** antes de cada PR. Paridad con baseline v2 antes de tocar
    `ppt_builder.py`.

---

## Comandos comunes

```cmd
# correr todos los tests (37)
pytest -q

# validar paridad visual con baseline v2
python tests/compare_baseline.py

# levantar Streamlit local
run_streamlit_local.bat
# → http://localhost:8501  ·  pass: QuickHelp2026

# levantar consola PyQt
run_dev_console.bat
```

---

## Convenciones de código

- Python 3.11+, **type hints obligatorios** en `core/`.
- Strings y output al usuario en **español**, código en **inglés**.
- Comentarios solo cuando el "por qué" no es obvio del nombre.
- Sin emojis salvo que el usuario los pida.
- `ruff check` antes de PR (config en `pyproject.toml`).

---

## Contratos clave

```python
# core/color_extractor.py
@dataclass
class ClientConfig:
    name: str
    subtitle: str = "Visión integral del servicio logístico"
    logo_bytes: bytes | None = None
    palette: Palette = field(default_factory=Palette)

# core/eda.py
@dataclass
class EdaReport:
    sheet_name: str
    n_rows_original: int
    n_rows_filtered: int
    period_label: str
    months: list[str]
    columns: dict[str, ColumnInfo]
    df_filtered: pd.DataFrame

# core/indicators.py
@dataclass
class IndicatorBundle:
    executive_summary: str
    indicators: list[Indicator]
    fortalezas: list[tuple[str, str]]
    oportunidades: list[tuple[str, str]]
    bullets: dict[str, list[str]]

# core/errors.py
PipelineError
├── SchemaInvalidError
├── EmptyAfterFilterError
├── LogoInvalidError
└── ClientNameMissingError
```

---

## Documentación canónica

Antes de implementar algo no trivial:

- `PLAN.md` — plan maestro y fases.
- `docs/architecture.md` — diagrama de capas y contratos.
- `docs/api_usage_plan.md` — reglas de uso de Anthropic.
- `docs/decisions.md` — registro ADR-style de decisiones.
- `docs/manual_usuario.md` — flujo de usuario (útil para entender UX esperada).

---

## Anti-patrones a evitar

- ❌ Lógica de negocio en `app.py` o `console.py` → debe ir a `core/`.
- ❌ Llamar al LLM más de una vez por generación.
- ❌ Mostrar tracebacks al usuario; siempre mensaje en español accionable.
- ❌ Hardcodear colores Fleischmann en código nuevo (usa `client_config.palette`).
- ❌ Agregar dependencias pesadas sin justificación (ya tenemos pandas + sklearn
  + python-pptx + Pillow + Streamlit + Anthropic + bcrypt).
- ❌ Modificar `ppt_builder.py` sin correr `tests/compare_baseline.py` después.
