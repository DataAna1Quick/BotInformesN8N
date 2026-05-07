# Deployment — BotInformesN8N

## 1. Streamlit Community Cloud (recomendado)

### Requisitos previos
- Repo público o privado en GitHub: `BotInformesN8N`.
- Cuenta en https://streamlit.io/cloud (gratis, login con GitHub).
- Anthropic API key activa.

### Pasos
1. **Push del repo** a GitHub:
   ```bash
   git remote add origin git@github.com:<org>/BotInformesN8N.git
   git push -u origin main
   ```

2. **Crear app en Streamlit Cloud**:
   - "New app" → seleccionar repo `BotInformesN8N`
   - Branch: `main`
   - Main file: `streamlit_app/app.py`
   - App URL: `quickhelp-botinformes` → resulta en `https://quickhelp-botinformes.streamlit.app`

3. **Configurar secrets** (panel "Secrets" en Streamlit Cloud):
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-api03-..."
   APP_PASSWORD_HASH = "$2b$12$abcdef..."  # bcrypt de QuickHelp2026
   DEFAULT_MODEL = "claude-haiku-4-5-20251001"
   PREMIUM_MODEL = "claude-sonnet-4-6"
   ENABLE_LLM = true
   ```

   El hash bcrypt se genera una sola vez:
   ```python
   import bcrypt
   bcrypt.hashpw(b"QuickHelp2026", bcrypt.gensalt(rounds=12))
   ```

4. **Deploy**: el primer build instala `streamlit_app/requirements.txt` automáticamente. Aprox. 2-3 min.

5. **Smoke test**: abrir la URL pública, login con `QuickHelp2026`, subir el Excel de Fleischmann + un logo de prueba, verificar que descarga `.pptx`.

### Limitaciones del plan free de Streamlit Cloud
- Apps públicas; si el cliente no debe ser visible al mundo, usar password gate (ya planificado).
- Recursos limitados: 1 GB RAM, 1 CPU. Para el dataset Fleischmann (2.4K filas) sobra; para 100K+ filas habría que pasar a Streamlit for Teams o autohospedar.
- Hibernación tras 7 días sin uso (la primera carga después tarda ~30s).

---

## 2. Alternativas de hosting

### Hugging Face Spaces (Streamlit SDK)
- Igual de simple, push a un repo HF en vez de GitHub.
- Free tier: 16 GB RAM, 2 vCPU (más generoso).
- URL: `https://<user>-botinformesn8n.hf.space`.

### Render / Railway / Fly.io
- Más control, soporta Docker.
- Costo: ~$5-10/mes mínimo.
- Mejor opción si se quiere dominio custom (`informes.quickhelp.com.co`).

### Self-hosted (VPS Quick Help)
- Si Quick Help tiene un servidor propio:
  ```
  streamlit run streamlit_app/app.py --server.port 8501 --server.address 0.0.0.0
  ```
  Detrás de Nginx con TLS.

---

## 3. Repo y rama

- **Branch protegida**: `main` (sólo se mergea con PR).
- **Branches de trabajo**: `feature/<descripcion>`, `fix/<descripcion>`.
- **CI**: `.github/workflows/tests.yml` corre `pytest` en cada push y PR.
- **Nunca commitear**:
  - `.streamlit/secrets.toml`
  - `.env`
  - `dev_console/.api_log.jsonl`
  - `output/*.pptx` (PPTs generadas)
  - Logos de clientes externos (no compartir sin permiso).

`.gitignore` debe incluir:
```
# secrets
.streamlit/secrets.toml
.env

# logs y outputs
dev_console/.api_log.jsonl
output/

# python
.venv/
__pycache__/
*.pyc
.pytest_cache/

# OS
.DS_Store
Thumbs.db
```

---

## 4. Versionado del paquete

`pyproject.toml`:
```toml
[project]
name = "bot_informes_n8n"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "streamlit>=1.36",
    "pandas>=2.2",
    "openpyxl>=3.1",
    "python-pptx>=1.0",
    "anthropic>=0.40",
    "Pillow>=10.4",
    "scikit-learn>=1.5",
    "bcrypt>=4.2",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["PyQt6>=6.7", "pytest>=8.3", "ruff>=0.6"]
```

Bump de versión cuando cambie la lógica de PPT (puede romper PPTs reproducibles). Tag de git por release.

---

## 5. Smoke test post-deploy (checklist)

- [ ] La URL pública carga el login.
- [ ] Password incorrecto rebota con mensaje claro.
- [ ] Password correcto avanza a la página de generación.
- [ ] Health check de la API muestra el badge correcto.
- [ ] Subir el Excel de Fleischmann (2.4K filas) genera PPT en <90s.
- [ ] La PPT generada coincide visualmente con la versión local de referencia.
- [ ] Subir un Excel inválido (sin columnas n8n) muestra error sin traceback.
- [ ] Forzar fallback (key inválida temporal) genera PPT con plantilla y badge "Modo plantilla".
- [ ] El logo del cliente aparece en portada y cierre.
- [ ] La paleta de la PPT respeta el color extraído del logo.

---

## 6. Mantenimiento

- **Rotar API key** cada 90 días.
- **Revisar `.api_log.jsonl`** mensual desde la consola PyQt; si el costo > USD 30/mes, considerar pasar default a Haiku.
- **Tests verdes** antes de cada deploy.
- **Bump del modelo** cuando salgan versiones nuevas (Sonnet 4.7, etc.) — actualizar `DEFAULT_MODEL` en secrets, probar en staging primero.
