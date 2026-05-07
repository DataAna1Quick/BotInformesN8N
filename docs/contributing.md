# Contribuir al proyecto

Guía rápida para el equipo Quick Help.

## Setup local

```cmd
git clone https://github.com/<org>/BotInformesN8N.git
cd BotInformesN8N
python -m venv .venv
.venv\Scripts\activate
pip install -r streamlit_app/requirements.txt
pip install -r dev_console/requirements.txt
pip install pytest pytest-cov
```

## Antes de cada cambio

1. Crear branch: `git checkout -b feature/mi-cambio`.
2. Ejecutar tests verdes: `pytest -q`.
3. Hacer cambios pequeños y enfocados.
4. Volver a ejecutar tests.
5. Commit con mensaje convencional.

## Convenciones

### Mensajes de commit

```
feat(<area>): <qué se agregó>
fix(<area>):  <qué se arregló>
docs(<area>): <docs editados>
test(<area>): <tests agregados>
refactor:     <reorg sin cambio funcional>
```

Ejemplo: `feat(ppt): add stop-evidence slide`

### Estilo de código

- Python 3.11+
- Type hints obligatorios en `core/`.
- Docstrings: una línea para funciones simples, multilínea sólo si hay
  invariantes no obvias.
- Nada de comentarios narrativos (`# this function does X`); el nombre debe
  bastar.
- Strings al usuario en español, código en inglés.
- `ruff check` antes de PR (configurado en `pyproject.toml`).

### Tests

- Cualquier feature nueva en `core/` necesita test.
- Tests rápidos (<2s cada uno) salvo el e2e que vale la pena.
- Mockear servicios externos (Anthropic, FS write, redes).
- Usar `excel_bytes` y `client_logo_bytes` como fixtures (definidos en
  `conftest.py`).

## Pull requests

- Asegurar que CI esté verde antes de pedir review.
- Auto-asignar revisor del equipo de Operaciones.
- Si el cambio impacta UI: incluir screenshots.
- Si el cambio impacta la PPT generada: correr `python tests/compare_baseline.py`
  y verificar resultado.
- No mergear sin al menos un approve.

## Liberar una nueva versión

1. Bump en `pyproject.toml` (`version = "0.X.Y"`).
2. Actualizar `CHANGELOG.md` con los cambios bajo el nuevo número.
3. Tag git: `git tag v0.X.Y && git push --tags`.
4. Streamlit Cloud auto-deploya el branch `main`.

## Estructura de carpetas

```
streamlit_app/      ← cara al usuario
  core/             ← lógica reutilizable, sin UI
  assets/           ← logos default, configs
dev_console/        ← herramientas internas (PyQt)
tests/              ← pytest
docs/               ← markdown
.github/workflows/  ← CI
```

**Regla:** la lógica vive en `streamlit_app/core/`. Streamlit y la consola PyQt
solo orquestan llamadas a esos módulos. Si te encuentras escribiendo lógica de
negocio en `app.py` o en `console.py`, sácala a `core/`.
