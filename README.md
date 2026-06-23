# Sistema de Cobro Musical

Aplicación web para automatizar el cálculo de pagos a músicos de sociedades
musicales valencianas basado en datos de asistencia a actos.

Migrada de Streamlit a una arquitectura moderna **FastAPI + HTML/CSS/JS**,
manteniendo **exactamente la misma lógica de cálculo** (verificada con un test de
paridad byte a byte contra la versión original).

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python run.py
```

Esto arranca el servidor en `http://127.0.0.1:8000` y abre el navegador
automáticamente. En Windows también puedes hacer doble clic en `start_web.bat`.

Para desarrollo con recarga automática:

```bash
uvicorn backend.server:app --reload
```

## Funcionalidades

- **Dashboard Principal**: métricas clave y visualizaciones (Plotly).
- **Editar Ponderaciones**: pesos por categoría en tiempo real, con herramientas
  automáticas (ponderación A automática e igualar presupuestos) y vista previa.
- **Configurar Retención Banda**: porcentaje que retiene la banda por acto.
- **Análisis por Actos**: detalle de asistencia y presupuesto por evento.
- **Procesar y Descargar**: cálculo completo, penalizaciones y export a Excel
  (completo o básico).

## Estructura del proyecto

```
backend/                 Paquete Python (servidor + lógica)
  core.py                Motor de cálculo (MusicianPaymentSystem), sin UI
  pricing.py             Ponderaciones automáticas e igualar presupuestos
  excel_export.py        Generación de los ficheros Excel de resultados
  server.py              API REST (FastAPI) + servido del frontend
frontend/                Cliente web
  index.html
  assets/                Logo y favicon (escudo de la sociedad)
  css/styles.css
  js/api.js              Cliente HTTP
  js/ui.js               Helpers de presentación (tablas, toasts, tabs, iconos)
  js/app.js              Controlador de páginas + router
run.py                   Lanzador (uvicorn + abre el navegador)
start_web.bat            Lanzador para Windows
Data/                    Archivos Excel de ejemplo
docs/                    Documentación de usuario (INSTRUCCIONES, prompt)
legacy/                  App Streamlit original (referencia de paridad)
  streamlit_app.py
tests/parity_check.py    Verifica paridad con la lógica original de Streamlit
```

## Estructura de Datos

La aplicación procesa un archivo Excel con tres hojas:

- **Asistencia**: datos de asistencia de músicos por evento (valores 1/0).
- **Presupuesto**: información presupuestaria por acto (`ACTES`, `A REPARTIR`…).
- **Configuracion_Precios**: ponderaciones por categoría (`ACTES`, A, B, C, D, E).

## Fórmula de reparto

```
Importe individual = (A_REPARTIR_NETO / total_asistentes) × ponderación
```

donde `A_REPARTIR_NETO` aplica la retención de banda configurada para el acto.

## Verificar la paridad de la lógica

```bash
python tests/parity_check.py
```

Compara, sobre los mismos datos, el motor nuevo (`backend.core`) con la lógica
original de Streamlit (`legacy/streamlit_app.py`) y confirma que los resultados
son idénticos.

## Tecnologías

- **Backend**: Python, FastAPI, Pandas, NumPy, XlsxWriter / OpenPyXL
- **Frontend**: HTML, CSS, JavaScript (vanilla) + Plotly
