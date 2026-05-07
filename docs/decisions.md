# Decisiones del proyecto — registro

Documento de referencia rápida con las decisiones confirmadas por el usuario.
Cualquier cambio de scope o de stack se anota aquí con fecha.

---

## D-001 · Hosting
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Streamlit Community Cloud (plan free).
- Repo en GitHub: `BotInformesN8N`.
- URL prevista: `https://quickhelp-botinformes.streamlit.app`.

## D-002 · Modelo Claude default
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Default: `claude-haiku-4-5-20251001` (~USD 0,003 por PPT).
- Premium: `claude-sonnet-4-6` (toggle desde consola PyQt para casos puntuales).
- Razón: minimizar gasto de créditos en un escenario de uso recurrente.

## D-003 · Color del cliente
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Extracción **automática** del logo del cliente vía k-means sobre pixeles (PIL + scikit-learn).
- Sin color picker manual.
- La paleta complementaria se deriva con reglas de contraste sobre el color dominante.

## D-004 · Datos del cliente por sesión
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Cada generación pide al usuario:
  - Excel n8n
  - Logo del cliente
  - Nombre del cliente
- Nada se persiste entre sesiones. No hay perfiles de cliente.
- Quick Help (proveedor) sí está fijo en el repo: logo + colores corporativos.

## D-005 · Idioma
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Solo español. No hay variante en inglés.
- Aplica a UI, prompts del LLM y contenido del PPT.

## D-006 · Slides editables
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- Desde la consola PyQt:
  - Toggle ON/OFF por slide.
  - Reorden por drag & drop.
  - Edición de textos default (subtítulos, footers, lecturas ejecutivas alternas).
- Persistido en `assets/slides_config.json` (versionable).

## D-007 · Scope de la app
**Fecha:** 2026-05-06 · **Estado:** ✅ confirmada
- La app **solo genera** PPTs nuevas a partir de un Excel.
- **No** modifica PPTs existentes. No hay flujo de re-import de `.pptx`.
- No hay edición online del PPT generado: el usuario lo descarga y lo edita en PowerPoint si quiere cambiar algo manualmente.

---

## Implícitas pero importantes (no requirieron pregunta)

- **Auth**: una sola password global (`QuickHelp2026`), hasheada con bcrypt antes de hardcodearse en secrets.
- **Pipeline single-source**: tanto Streamlit como la consola PyQt importan los mismos módulos `core/`. Ningún código duplicado.
- **Fallback obligatorio**: si la API Anthropic falla o no tiene créditos, la app entrega PPT con plantilla determinística + badge visible.
- **Reutilización**: los módulos del proyecto Fleischmann (`build_ppt_v2.py`, `eda_fleischmann.py`) se refactorizan, no se copian. Los hardcodes (Fleischmann, colores, paths) se parametrizan vía `ClientConfig`.

---

## Decisiones diferidas (revisar en F7 o post-MVP)

- Migración a Streamlit for Teams si el plan free queda corto en RAM/CPU.
- Dominio custom (`informes.quickhelp.com.co`) — requiere salir de Streamlit free.
- Multi-idioma — no en scope inicial.
- Plantillas de slides adicionales (industry-specific) — postponer hasta tener 3+ clientes en producción.
