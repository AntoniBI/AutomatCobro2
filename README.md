# Sistema de Cobro Musical 🎵

Aplicación web para automatizar el cálculo de pagos a músicos de sociedades musicales valencianas basado en datos de asistencia a actos.

## Instalación

1. Instalar dependencias:
```bash
pip install -r requirements.txt
```

2. Ejecutar la aplicación:
```bash
streamlit run app.py
```

## Funcionalidades

- **Dashboard Principal**: Métricas clave y visualizaciones
- **Editor de Ponderaciones**: Modificar pesos por categoría de músico
- **Análisis por Actos**: Información detallada por evento
- **Procesamiento y Descarga**: Cálculos completos y exportación a Excel

## Estructura de Datos

La aplicación procesa un archivo Excel con tres hojas:
- **Asistencia**: Datos de asistencia de músicos por evento
- **Presupuesto**: Información presupuestaria por acto
- **Configuracion_Precios**: Ponderaciones por categoría

## Tecnologías

- Python + Pandas
- Streamlit
- Plotly
- OpenPyXL