# Manual de usuario — BotInformesN8N

Aplicación web para generar presentaciones gerenciales de operaciones logísticas
a partir de los exportes n8n de Quick Help SAS.

---

## Requisitos previos

- Tener el archivo Excel **exportado desde n8n** (estructura estándar de 108 columnas,
  hoja única con los servicios del período).
- Tener el **logo del cliente** en formato PNG o JPG (idealmente con fondo
  transparente o blanco).
- Conocer el **nombre comercial del cliente** tal y como debe aparecer en la portada.

---

## Paso a paso

### 1. Acceder a la app

Abrir la URL pública (ej. `https://<app-name>.streamlit.app`).
Ingresar la contraseña: **`QuickHelp2026`**.

> Si la contraseña cambia, el equipo Quick Help generará un nuevo hash bcrypt
> y lo configurará en los secrets de Streamlit Cloud.

### 2. Cargar los datos del cliente

- **Nombre del cliente**: ej. "Fleischmann", "Acme Foods". Aparecerá en portada y cierre.
- **Logo del cliente**: arrastrar el archivo o usar el botón "Browse files".
  - Formato: PNG o JPG.
  - **Vista previa**: tan pronto como subas el logo, la app extrae el color
    principal y te lo muestra. Ese color se usará como acento del cliente en el PPT.
  - Si subes un SVG o PDF, la app rechaza el archivo con un mensaje claro.

### 3. Cargar el Excel de la operación

- Arrastrar el `.xlsx` exportado desde n8n.
- Si el archivo no tiene la estructura correcta, la app indica exactamente qué
  columna falta. Pedir al equipo n8n que regenere el export con todas las columnas.

### 4. Activar / desactivar análisis con IA

El **toggle "Análisis con IA (Claude)"** controla cómo se redacta la narrativa:

| Modo | Cuándo se usa | Descripción de los textos |
|---|---|---|
| **Modo IA** | API Anthropic activa con créditos | Narrativa contextual generada por Claude Haiku 4.5 con base en los datos reales del cliente. |
| **Modo plantilla** | API sin créditos / sin clave / error de red | Plantilla determinística — frases estándar con los números reales insertados. |

> El badge en la parte superior indica el estado actual.
> En modo plantilla la PPT es totalmente válida; sólo cambia que las frases
> son genéricas en vez de adaptadas al contexto.

### 5. Generar la PPT

- Presionar **"🚀 Generar presentación"**.
- En el log se ve el progreso por etapas (validación, EDA, KPIs, indicadores, PPT).
- Tiempo aproximado: **20–60 segundos** según tamaño del Excel.
- Cuando termina, aparece:
  - 4 KPI cards con resumen.
  - Botón **"⬇ Descargar presentación"** con el archivo nombrado
    `Informe_<Cliente>_<Fecha>.pptx`.

### 6. Revisar la PPT generada

La presentación tiene **13 diapositivas** organizadas en 5 secciones:

1. **Portada** con logos Quick Help + cliente, KPIs principales del período.
2. **Resumen ejecutivo** con 8 KPI cards y una lectura ejecutiva.
3. **Sección 1 · Ritmo operativo** — volumen mensual, mix de servicio.
4. **Sección 2 · Cliente** — distribución por sede, top rutas.
5. **Sección 3 · Equipo Quick Help** — top conductores, vehículos, tenedores.
6. **Sección 4 · Calidad y trazabilidad** — manifiestos, mercancía.
7. **Sección 5 · Conclusiones** — fortalezas y oportunidades.
8. **Cierre** con logos y mensaje de despedida.

> **Importante**: la PPT no contiene información financiera. Está pensada para
> ser entregada al cliente sin necesidad de censura adicional.

### 7. Si necesitas editar algo manualmente

La app **no edita** PPTs existentes. Si necesitas cambios puntuales (mover un
texto, corregir un nombre, añadir un slide especial), abre el `.pptx` en
PowerPoint y modifícalo allí. La próxima generación volverá a partir desde cero.

---

## Errores comunes y solución

| Mensaje | Causa | Solución |
|---|---|---|
| "Faltan columnas obligatorias: …" | El Excel no es un export n8n estándar. | Pedir al equipo n8n el archivo con la estructura completa. |
| "El logo está en formato vectorial (SVG/PDF)…" | Subiste un SVG o PDF. | Convertir a PNG (puedes usar https://cloudconvert.com). |
| "No se pudo leer el logo como imagen…" | El archivo está corrupto o en un formato exótico. | Re-exportar el logo como PNG. |
| "El Excel no tiene filas analizables…" | Todos los servicios fueron filtrados (cancelados). | Revisar el período del export; pedir uno con servicios efectivos. |
| Badge "Modo plantilla · sin créditos" | API Anthropic agotada. | El admin debe recargar créditos en console.anthropic.com. La app sigue funcional con plantilla. |

---

## Para administradores Quick Help

### Cambiar el prompt de la narrativa IA

1. Abrir la consola PyQt local (`run_dev_console.bat`).
2. Pestaña **Prompts** → editar el texto.
3. Botón **"Probar prompt"** para validar contra Claude antes de guardar.
4. **"Guardar"** y commitear el cambio en git.

### Cambiar la paleta default

1. Consola PyQt → pestaña **Paleta**.
2. Editar colores con los pickers.
3. Guardar.

### Cambiar el orden o títulos de los slides

1. Consola PyQt → pestaña **Slides**.
2. Toggle ON/OFF para activar/desactivar.
3. Arrastrar filas para reordenar.
4. Doble click en la columna "Título" para renombrar.
5. Guardar.

### Monitorear consumo de API

1. Consola PyQt → pestaña **API Monitor**.
2. Ver costo acumulado, llamadas con IA vs fallback, tabla detallada.
3. Si los fallbacks aumentan súbitamente, revisar el saldo en console.anthropic.com.

### Probar localmente antes de publicar cambios

1. Consola PyQt → pestaña **Test runner**.
2. Seleccionar un Excel y un logo de prueba.
3. **"▶ Generar PPT de prueba"** corre el pipeline completo en la máquina local.
4. Validar que el PPT resultante quedó bien antes de mergear cambios.

---

## Soporte

- Equipo de Operaciones y Analítica · Quick Help SAS
- Email: datos.quick8@gmail.com
