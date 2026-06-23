# Introduccion
Una importante empresa representrante de las Sociedad Musicales de la comunidad valenciana en España nos elige para ejecutar un proyecto para solucion un problema

Todos los años, todas las bandas de musica pertenecientes  realizan un ( O varioss) pago a sus musicos debido a los 
actos musicales callejeros que realizan en distintos pueblos por los cuales los musicos cobran

Se desea genera una aplicacion que analice los datos de asistencia perteneciente a dichos actos de una sociedad musical y automatize el cobro de cada uno de los musicos
dependiendo de su asistencia con el objetivo de mejorar los procesos de cobro de todas las bandas de musica.

# Datos

El dataset está en la carpeta data, en un archivo excel. Analiza los datos para saber la estructura.

En principio no hace falta limpiar los datos

# Aplicacion a generar
Genera una aplicación que:

Leer hojas del archivo Excel.

Analizar los datos

montar un cuadro de mandos con diversas paginas donde puedas hacer lo siguiente:
*Editar la ponderacion por acto 
*Obtener en tiempo real la diferencia entre A Repartir - total repartido para saber de que margen contamos
*Obtener la cantidad y nombre de musicos por categoria de cada acto

Posteriormente a tener las ponderaciones editadas tiene que hacer lo siguiente:
*Procesar y descargar un excel para su facil visualizacion detallada. Dicho excel descargado tiene contener la siguiente información:

Transformar tabla de asistencia a formato largo.

Normalizar nombres y valores de columnas.

Unir asistencia con presupuesto.

Unir asistencia con ponderaciones.

Filtrar asistentes.

Calcular total de asistentes por acto.

Calcular importe ponderado por músico.

Generar resumen total por músico.

Crear pivote de importes por acto.

Crear pivote de asistencia por acto.

Detectar actos oficiales.

Contar actos oficiales no asistidos por músico.

Añadir conteo de actos no asistidos al resumen.

Filtrar músicos con ganancia > 0.

Calcular total repartido real por acto.

Comparar presupuesto vs reparto real.

Contar músicos por categoría y acto.

Enriquecer tabla de ganancias por acto.

Exportar resultados a Excel.


# Tecnologias

backend: Python
frontend: streamlit
base de datos: si consideras que es necesario sqlite