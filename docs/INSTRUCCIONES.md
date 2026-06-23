# INSTRUCCIONES DE USO

## Iniciar la aplicación
1. Haz doble clic en **`start_web.bat`** (Windows) o ejecuta `python run.py`.
2. Se abrirá automáticamente tu navegador en `http://127.0.0.1:8000`.
3. ¡La aplicación estará funcionando!

## Primera vez (instalar dependencias)
1. Instala Python 3.10 o superior.
2. Abre una terminal en esta carpeta y ejecuta:
   ```
   pip install -r requirements.txt
   ```

## Cómo usarla
1. Arrastra tu archivo Excel a la barra lateral (o haz clic para seleccionarlo)
   y pulsa **Cargar y Procesar**.
2. Navega entre las páginas: Dashboard, Ponderaciones, Retención Banda,
   Análisis por Actos y Procesar y Descargar.
3. En **Procesar y Descargar** genera el Excel con los resultados.

## Estructura del archivo Excel
El archivo debe tener tres hojas:
- **Asistencia**: Nombre, Apellidos, Instrumento, Categoria + una columna por acto.
- **Presupuesto**: ACTES + columnas de presupuesto (incluida `A REPARTIR`).
- **Configuracion_Precios**: ACTES, A, B, C, D, E.

## Requisitos
- Python 3.10 o superior.
- Navegador web (Chrome, Firefox, Edge, etc.).

## Soporte
Si tienes problemas, verifica que:
1. Python esté instalado correctamente.
2. Todas las dependencias estén instaladas (`pip install -r requirements.txt`).
3. El archivo Excel tenga las tres hojas con las columnas requeridas.
