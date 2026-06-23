"""Backend del Sistema de Cobro Musical.

Paquete que contiene:
  - core: motor de cálculo (lógica de negocio, sin dependencias de UI).
  - excel_export: generación de los ficheros Excel de resultados.
  - server: API REST (FastAPI) y servido del frontend estático.

La lógica de cálculo es idéntica a la versión original en Streamlit (`app.py`);
solo se ha separado de la capa de presentación.
"""
