# Sistema de Cobro Musical

Aplicación web para automatizar el cálculo de pagos a músicos de sociedades
musicales valencianas a partir de los datos de asistencia a los actos. Subes un
Excel, ajustas ponderaciones y retenciones, y descargas el reparto calculado.

Migrada de Streamlit a una arquitectura **FastAPI + HTML/CSS/JS (vanilla)**,
manteniendo **exactamente la misma lógica de cálculo** (verificada con un test de
paridad contra la versión original).

## Requisitos

- **Python 3.10 o superior**.
- Un navegador web moderno (Chrome, Firefox, Edge…).

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

## Cómo usarla

1. **Carga**: arrastra tu archivo Excel a la barra lateral (o haz clic para
   seleccionarlo) y pulsa **Cargar y Procesar**.
2. **Dashboard**: revisa las métricas clave y las visualizaciones.
3. **Ponderaciones**: ajusta los pesos por categoría, con las herramientas
   automáticas (ponderación A automática e igualar presupuestos) y vista previa.
4. **Retención Banda**: configura el porcentaje que retiene la banda por acto.
5. **Análisis por Actos**: consulta el detalle de asistencia y presupuesto por
   evento.
6. **Procesar y Descargar**: ejecuta el cálculo completo y descarga el Excel de
   resultados (completo o básico).

## Estructura de datos (Excel de entrada)

El archivo debe tener tres hojas. El número de actos es dinámico: la app se
adapta a las columnas presentes.

| Hoja                    | Contenido                                                                 |
| ----------------------- | ------------------------------------------------------------------------- |
| **Asistencia**          | `Nombre`, `Apellidos`, `Instrumento`, `Categoria` + una columna por acto (1/0). |
| **Presupuesto**         | `ACTES` + columnas de presupuesto (incluida `A REPARTIR`, COBRAT, LLOGATS, TRANSPORT…). |
| **Configuracion_Precios** | `ACTES`, `A`, `B`, `C`, `D`, `E` (ponderaciones por categoría).          |

## Fórmula de reparto

```
Importe individual = (A_REPARTIR_NETO / total_asistentes) × ponderación
```

donde `A_REPARTIR_NETO` aplica la retención de banda configurada para el acto.

## API REST

El frontend consume una API JSON servida por FastAPI. El estado se guarda por
usuario en sesiones en memoria identificadas por la cookie `cobro_session`.

| Método | Endpoint                       | Descripción                                |
| ------ | ------------------------------ | ------------------------------------------ |
| GET    | `/api/session`                 | Estado de la sesión y resumen de datos.    |
| POST   | `/api/upload`                  | Sube y procesa el Excel.                   |
| GET    | `/api/dashboard`               | Datos y métricas del dashboard.            |
| GET/PUT| `/api/weights`                 | Lee / actualiza ponderaciones.             |
| POST   | `/api/weights/save`            | Guarda los cambios de ponderaciones.       |
| POST   | `/api/weights/restore`         | Restaura las ponderaciones guardadas.      |
| POST   | `/api/weights/auto-a`          | Calcula la ponderación A automática.       |
| POST   | `/api/weights/default-budget`  | Aplica el presupuesto por defecto.         |
| POST   | `/api/weights/equalize`        | Iguala presupuestos.                       |
| GET/PUT| `/api/retention`               | Lee / actualiza la retención de banda.     |
| POST   | `/api/retention/save`          | Guarda la retención.                       |
| POST   | `/api/retention/reset`         | Restablece la retención.                   |
| POST   | `/api/retention/template`      | Aplica una plantilla de retención.         |
| GET    | `/api/events`                  | Lista de actos.                            |
| GET    | `/api/events/analysis`         | Análisis por acto.                         |
| POST   | `/api/process`                 | Ejecuta el cálculo completo.               |
| GET    | `/api/export/{kind}`           | Descarga el Excel de resultados.           |

## Estructura del proyecto

```
backend/                 Paquete Python (servidor + lógica)
  core.py                Motor de cálculo (MusicianPaymentSystem), sin UI
  pricing.py             Ponderaciones automáticas e igualar presupuestos
  excel_export.py        Generación de los ficheros Excel de resultados
  server.py              API REST (FastAPI) + servido del frontend
frontend/                Cliente web
  index.html             SPA + sprite de iconos SVG
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

## Verificar la paridad de la lógica

Si modificas `backend/core.py` o `backend/pricing.py`, ejecuta:

```bash
python tests/parity_check.py
```

Compara, sobre los mismos datos, el motor nuevo (`backend.core`) con la lógica
original de Streamlit (`legacy/streamlit_app.py`) y confirma que los resultados
son idénticos (**PARIDAD TOTAL**). `legacy/` es solo referencia; no se añade
funcionalidad nueva ahí.

## Tecnologías

- **Backend**: Python, FastAPI, Uvicorn, Pandas, NumPy, XlsxWriter, OpenPyXL.
- **Frontend**: HTML, CSS, JavaScript (vanilla) + Plotly.

## Solución de problemas

Si tienes problemas, verifica que:

1. Python 3.10+ esté instalado correctamente.
2. Las dependencias estén instaladas (`pip install -r requirements.txt`).
3. El archivo Excel tenga las tres hojas con las columnas requeridas.
