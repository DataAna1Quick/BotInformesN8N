# Fixtures de tests

**Importante:** los archivos `.xlsx` con datos reales de clientes están en `.gitignore` y **no se commitean**.
Para correr los tests localmente, copiar manualmente:

- `n8n_sample.xlsx` — un Excel n8n con la estructura estándar (108 columnas).
- `client_logo_sample.png` — cualquier logo de cliente para tests visuales.

Para CI público, hay que generar un Excel sintético en `conftest.py` que reproduzca la estructura sin datos sensibles.
