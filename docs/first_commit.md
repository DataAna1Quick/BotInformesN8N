# Cómo cerrar el commit inicial

Git no tiene identidad configurada en esta máquina y por política no la modifico
automáticamente. Tres líneas y ya queda listo:

```cmd
cd "C:\Users\Quick\OneDrive\OneDrive - Quick Help SAS\Documentos\Proyecto_Informes_Automaticos"

git config user.email "datos.quick8@gmail.com"
git config user.name  "Quick Help SAS"

git commit -m "feat: bootstrap BotInformesN8N with full pipeline + Streamlit + PyQt console"
```

> Importante: usar `git config` **sin** `--global` para que la identidad quede sólo
> en este repo (no afecta los demás).

Todos los archivos ya están staged. Verifica con `git status` antes de commitear si quieres confirmar.

---

## Push al remoto

Una vez creado el repo `BotInformesN8N` en GitHub:

```cmd
git remote add origin git@github.com:<org>/BotInformesN8N.git
git branch -M main
git push -u origin main
```

Reemplaza `<org>` por tu organización o usuario de GitHub.

---

## Después del push

1. Entrar a https://share.streamlit.io
2. "New app" → seleccionar repo `BotInformesN8N` → branch `main` → main file `streamlit_app/app.py`
3. En "Advanced settings" → "Secrets":
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."   # tu key
   APP_PASSWORD_HASH = "$2b$12$8dXy0y25fv8uaTEJN4CkguAndDN5ZncaPLDLnIK4I0sEhoXnVmRS2"
   ENABLE_LLM = true
   ```
4. Deploy. La primera build tarda ~3 min.
5. URL pública: `https://<app-name>.streamlit.app`.
6. Smoke test con `tests/fixtures/n8n_sample.xlsx` y un logo de prueba.
