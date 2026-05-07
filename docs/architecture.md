# Arquitectura — BotInformesN8N

## Diagrama de capas

```
┌─────────────────────────────────────────────────────────────────────┐
│  PRESENTATION                                                       │
│  ┌──────────────────────────┐  ┌──────────────────────────────┐    │
│  │ Streamlit App (público)  │  │ PyQt6 Dev Console (interna)  │    │
│  │  pages/, app.py          │  │  console.py, modules/        │    │
│  └────────────┬─────────────┘  └────────────┬─────────────────┘    │
│               └──────────────┬───────────────┘                      │
└───────────────────────────────┼─────────────────────────────────────┘
                                │  importan exactamente lo mismo
┌───────────────────────────────▼─────────────────────────────────────┐
│  CORE (lógica de negocio, sin dependencias UI)                      │
│  ┌────────┐ ┌────────┐ ┌────────────┐ ┌────────────────┐ ┌───────┐ │
│  │schema  │ │  eda   │ │ indicators │ │ llm_indicators │ │  ppt  │ │
│  └────────┘ └────────┘ └────────────┘ └────────────────┘ └───────┘ │
│       └────────────┬─────────┴────────────┬─────────────────┘       │
│                    │                      │                          │
│                ┌───▼─────┐         ┌──────▼──────────┐               │
│                │pipeline │         │ color_extractor │               │
│                └─────────┘         └─────────────────┘               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│  EXTERNALS                                                           │
│  ┌────────────────┐  ┌────────────────────┐  ┌──────────────────┐   │
│  │ Anthropic API  │  │ Local FS (configs) │  │  Excel del user  │   │
│  └────────────────┘  └────────────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## Responsabilidades por módulo

| Módulo | Responsabilidad | Dependencias clave |
|---|---|---|
| `core/schema.py` | Validar que el Excel cargado tenga la estructura n8n. Listar columnas obligatorias y opcionales. Mensajes accionables. | `pandas` |
| `core/eda.py` | Función pura `run(file_bytes, filters) → EdaReport`. Mismas reglas de viabilidad del agente `eda-fleischmann`. **No escribe a disco.** | `pandas`, `openpyxl`, `numpy` |
| `core/indicators.py` | Plantilla determinística que devuelve los 10 KPIs en `list[Indicator]` a partir de un `EdaReport`. Sin LLM. | sólo stdlib |
| `core/llm_indicators.py` | Wrapper sobre Anthropic SDK. Health check, prompt caching, tool use, fallback, logging. Misma interfaz de retorno que `indicators.py` para ser intercambiable. | `anthropic` |
| `core/ppt_builder.py` | Construye el `.pptx` recibiendo `EdaReport`, `list[Indicator]`, `ClientConfig` (logo bytes, colores). Devuelve `bytes`. **No depende de Streamlit ni PyQt.** | `python-pptx`, `Pillow` |
| `core/color_extractor.py` | Extrae color dominante del logo del cliente (k-means sobre pixeles de PIL). Genera paleta complementaria respetando contraste. | `Pillow`, `scikit-learn` |
| `core/pipeline.py` | Orquestador. Recibe inputs del usuario y un `progress_cb`, devuelve bytes del PPT. Es lo único que la UI invoca. | core/* |

## Contratos clave (data classes)

```python
# core/schema.py
@dataclass
class ClientConfig:
    name: str
    subtitle: str = "Visión integral del servicio logístico"
    logo_bytes: bytes | None = None
    primary_color: str = "#1B3D7A"   # default Fleischmann (override por logo)
    accent_color: str = "#F4B400"    # Quick Help shared yellow

# core/eda.py
@dataclass
class EdaReport:
    sheets: dict[str, SheetReport]
    rows_after_filter: int
    period_label: str
    df_filtered: pd.DataFrame  # para ppt_builder

# core/indicators.py
@dataclass
class Indicator:
    name: str
    question: str
    formula: str
    columns: list[str]
    granularity: str
    frequency: str
    confidence: Literal["alta", "media", "baja"]
    reason: str
```

## Flujo de datos en una generación

```
[user upload] excel.xlsx ──► schema.validate ──► eda.run ──► EdaReport
                                                                │
                                                                ▼
                                  [LLM ok?]──► llm_indicators.propose ──► list[Indicator]
                                       │                                      ▲
                                       └──fallback──► indicators.derive ──────┘
                                                                              │
[user upload] logo.png ──► color_extractor ──► ClientConfig                   │
                                                    │                         │
                                                    └──┐                      │
                                                       ▼                      │
                                       ppt_builder.build(report, indicators, config)
                                                       │
                                                       ▼
                                                   bytes (.pptx)
                                                       │
                                                       ▼
                                          [Streamlit] download button
```

## Configuración persistida

| Archivo | Propósito | Editable desde |
|---|---|---|
| `assets/default_palette.json` | Paleta default de Quick Help (azul Fleischmann como demo) | Consola PyQt → tab Paleta |
| `assets/slides_config.json` | Lista ordenada de slides activos | Consola PyQt → tab Slides |
| `core/prompts/indicator_analyst.md` | System prompt del LLM | Consola PyQt → tab Prompts |
| `.streamlit/secrets.toml` | API key + password hash + flags | Panel de Streamlit Cloud (manual) |

## Tests

- `tests/test_eda.py` — corre `eda.run` sobre un Excel mock de 50 filas; valida que `pct_null`, `n_unique`, veredictos sean los esperados.
- `tests/test_indicators.py` — valida que `indicators.derive(eda_report)` devuelva los 10 indicadores de la plantilla.
- `tests/test_ppt_builder.py` — corre `ppt_builder.build` y verifica que el `.pptx` resultante tiene 13 slides y que cada uno contiene los charts esperados (vía `python-pptx`).
- `tests/test_llm_indicators.py` — mockea Anthropic con `responses` o `vcrpy`. Verifica fallback en 401, 429, 5xx.

## Inyección de configuración en el PPT builder

El builder actual (`build_ppt_v2.py`) tiene constantes hardcoded (`BLUE = "#1B3D7A"`, paths a logos, "Quick Help SAS", "Fleischmann"). El refactor:

```python
# core/ppt_builder.py
class PPTBuilder:
    def __init__(self, client_config: ClientConfig, slides_config: SlidesConfig):
        self.client = client_config
        self.slides_config = slides_config
        self.palette = Palette(
            primary=client_config.primary_color,
            accent=client_config.accent_color,
            dark=DEFAULT_DARK,
            success=DEFAULT_SUCCESS,
            alert=DEFAULT_ALERT,
        )

    def build(self, report: EdaReport, indicators: list[Indicator]) -> bytes:
        ...
```

Quick Help logo se mantiene siempre fijo (es el proveedor); el logo cliente entra dinámico por `client_config.logo_bytes`.

## Convenciones

- **Encoding**: todo UTF-8.
- **Idioma**: código en inglés, strings y output al usuario en español.
- **Fechas**: el dataset n8n trae seriales Excel; convertirlos en `eda.run` antes de cualquier análisis temporal.
- **Naming**: `snake_case` en código, `PascalCase` para clases.
- **Type hints**: obligatorios en módulos `core/`.
- **Docstrings**: una línea para funciones; multilineas solo si hay invariantes no obvias.
