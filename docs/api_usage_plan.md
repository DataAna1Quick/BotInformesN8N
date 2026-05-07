# Plan de uso — Anthropic API (Claude) en BotInformesN8N

Objetivo: usar Claude para generar la narrativa de indicadores (sub-agente `indicator-analyst`) **sin quemar créditos innecesarios**, con fallback determinístico cuando la API no esté disponible.

---

## 1. Modelo y formato

| Aspecto | Decisión |
|---|---|
| **Modelo default** | `claude-haiku-4-5-20251001` (~$0,003 por PPT) |
| **Modelo premium** | `claude-sonnet-4-6` (toggle puntual desde consola PyQt) |
| **Max output tokens** | `4000` (suficiente para 10 indicadores + resumen) |
| **Temperature** | `0.3` (consistencia entre PPTs del mismo cliente) |
| **Formato salida** | JSON estructurado vía `response_format` o tool use con un schema definido |
| **Llamadas por PPT** | **Una sola** — no multi-turn |

---

## 2. Prompt caching (clave para bajar costo)

El system prompt del `indicator-analyst` (~3.500 tokens) es **estable entre todas las generaciones**. Usar Anthropic prompt caching:

```python
client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4000,
    system=[
        {
            "type": "text",
            "text": INDICATOR_ANALYST_SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"}  # ← cacheado
        }
    ],
    messages=[
        {"role": "user", "content": user_input_with_eda_json}
    ]
)
```

**Beneficio:** Tras el primer request, el system prompt cuesta ~10% del precio normal por las siguientes 5 minutos. Para un usuario que genere 3 PPTs seguidas: ~70% de ahorro en input.

---

## 3. Token budget esperado por generación

Asumiendo dataset tipo Fleischmann (2.464 filas, 108 columnas, EDA JSON ~30K tokens crudo):

| Componente | Tokens | Estrategia |
|---|---|---|
| System prompt (cacheado) | ~3.500 | `cache_control` |
| EDA JSON resumido (no la versión cruda) | ~6.000 | Pre-filtrar a sólo columnas viables + top 10 por sección |
| Instrucción del turno | ~200 | mínimo |
| **Total input** | **~9.700** | |
| Output (10 indicadores + lectura ejecutiva) | ~3.500 | `max_tokens=4000` |

**Costo Sonnet 4.6** (precios de referencia, validar con la consola en tiempo real):
- Input non-cached: ~$3 / 1M tokens → 9.700 × $3/1M = **$0,029**
- Con caching tras primera llamada: input efectivo ~3.000 tokens → **$0,009**
- Output: ~$15 / 1M tokens → 3.500 × $15/1M = **$0,053**
- **Total por PPT: ~$0,06 sin cache, ~$0,06 primera vez, ~$0,06 → $0,02–0,03 cacheado**

**Costo Haiku 4.5** equivalente: ~10× más barato → **$0,003–0,006 por PPT**.

---

## 4. Pre-flight health check

Al cargar la página de generación en Streamlit, ejecutar:

```python
@st.cache_data(ttl=3600)  # 1h
def api_health_check() -> dict:
    """Returns {ok: bool, reason: str, model: str}."""
    try:
        client.messages.create(
            model="claude-haiku-4-5-20251001",  # haiku para barato
            max_tokens=1,
            messages=[{"role": "user", "content": "ok"}]
        )
        return {"ok": True, "reason": "healthy", "model": "sonnet"}
    except anthropic.AuthenticationError:
        return {"ok": False, "reason": "api_key_invalid"}
    except anthropic.RateLimitError:
        return {"ok": False, "reason": "rate_limited"}
    except anthropic.APIStatusError as e:
        if "credit" in str(e).lower() or "quota" in str(e).lower():
            return {"ok": False, "reason": "no_credit"}
        return {"ok": False, "reason": f"api_error_{e.status_code}"}
    except Exception as e:
        return {"ok": False, "reason": f"network_error"}
```

El resultado se cachea por sesión y se muestra en UI:
- ✅ **Modo IA activo** (badge verde)
- ⚠ **Modo plantilla** (badge amarillo) — con tooltip "API sin créditos / no disponible"

Costo del health check: ~$0,000001 con Haiku (despreciable).

---

## 5. Fallback chain — política

```python
def derive_indicators(report, client_name, *, force_template=False):
    if force_template:
        return template.derive(report, client_name)

    health = api_health_check()
    if not health["ok"]:
        log.info(f"LLM unavailable ({health['reason']}), using template")
        return template.derive(report, client_name)

    try:
        return llm.propose(report, client_name)
    except anthropic.APIStatusError as e:
        log.warning(f"LLM call failed ({e.status_code}), falling back to template")
        return template.derive(report, client_name)
    except Exception as e:
        log.exception("Unexpected LLM failure, falling back")
        return template.derive(report, client_name)
```

**Sin retries** en errores de cuota o auth — fallback inmediato. Sí retry (1 vez, 2s delay) en errores 5xx transitorios.

La salida de `template.derive()` y `llm.propose()` debe respetar **el mismo schema** (lista de `Indicator` dataclass) para que el resto del pipeline no se entere de cuál se usó.

---

## 6. Schema de respuesta del LLM (tool use)

Para evitar "JSON malformado":

```python
INDICATOR_TOOL = {
    "name": "submit_indicators",
    "description": "Returns the prioritized list of operational KPIs.",
    "input_schema": {
        "type": "object",
        "properties": {
            "executive_summary": {"type": "string"},
            "indicators": {
                "type": "array",
                "minItems": 5, "maxItems": 10,
                "items": {
                    "type": "object",
                    "required": ["name", "question", "formula", "columns",
                                 "granularity", "frequency", "confidence", "reason"],
                    "properties": {
                        "name": {"type": "string"},
                        "question": {"type": "string"},
                        "formula": {"type": "string"},
                        "columns": {"type": "array", "items": {"type": "string"}},
                        "granularity": {"type": "string"},
                        "frequency": {"type": "string"},
                        "confidence": {"enum": ["alta", "media", "baja"]},
                        "reason": {"type": "string"},
                    }
                }
            },
            "limitations": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["executive_summary", "indicators", "limitations", "next_steps"]
    }
}
```

Forzar el uso del tool con `tool_choice={"type": "tool", "name": "submit_indicators"}`. Esto garantiza JSON parseable y rechaza respuestas en prosa.

---

## 7. Logging local de consumo

Cada llamada se registra en `dev_console/.api_log.jsonl`:

```jsonl
{"ts":"2026-05-06T10:42:11","model":"claude-sonnet-4-6","input_tokens":9712,"cached_input_tokens":3500,"output_tokens":3421,"cost_usd":0.025,"client":"Fleischmann","fallback":false}
{"ts":"2026-05-06T11:05:33","model":null,"input_tokens":0,"output_tokens":0,"cost_usd":0,"client":"Acme","fallback":true,"fallback_reason":"no_credit"}
```

La consola PyQt tiene una pestaña que lee este archivo y muestra:
- Total acumulado del mes (tokens + USD).
- Tabla por cliente con cantidad de generaciones.
- Gráfico de barras: usos por día.
- Alerta si en los últimos 5 usos el `fallback=true` ratio es >50% (señal de que se acabaron los créditos).

---

## 8. Configuración

**En Streamlit (producción):** `.streamlit/secrets.toml` (administrado por panel de Streamlit Cloud, no commiteado):
```toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
APP_PASSWORD_HASH = "$2b$12$..."  # bcrypt de QuickHelp2026
DEFAULT_MODEL = "claude-sonnet-4-6"
ECONOMY_MODEL = "claude-haiku-4-5-20251001"
ENABLE_LLM = true
```

**En desarrollo local:** archivo `.env` (también en `.gitignore`):
```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

`core/llm_indicators.py` lee primero `st.secrets`, luego `os.environ`, luego falla con mensaje claro.

---

## 9. Decisiones que minimizan gasto

1. ✅ **Una sola llamada** por generación (no multi-turn, no auto-reflexión).
2. ✅ **Caching del system prompt** (estable entre llamadas).
3. ✅ **EDA pre-resumido** (no enviar JSON crudo de 30K tokens, sólo lo viable + top-N).
4. ✅ **Health check con Haiku**, no con Sonnet.
5. ✅ **Toggle Sonnet/Haiku** en consola PyQt — Haiku para clientes recurrentes donde la calidad ya está validada.
6. ✅ **Sin retries en errores de cuota.**
7. ✅ **`max_tokens` ajustado** (4000, no 8000).
8. ✅ **Fallback inmediato** a plantilla determinística — el usuario nunca queda sin PPT.

---

## 10. Métricas a monitorear

Visibles en la pestaña API Monitor de la consola PyQt:

- Costo acumulado del mes (USD).
- # de generaciones con LLM vs # con plantilla.
- Tokens promedio por generación (input cacheado vs no cacheado).
- Tasa de fallback en los últimos 30 días.
- Latencia P50/P95 de la llamada al LLM.

Si el costo mensual proyectado excede USD 50, alertar al admin para considerar pasar el modelo default a Haiku.
