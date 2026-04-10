import pandas as pd

def calcular_presupuestos_iguales(
    df_asistencia,
    df_ponderaciones,
    eventos,
    categorias,
    presupuesto_total_max,
    categoria_col="Categoria"
):
    """
    Calcula los presupuestos por evento para que el valor unitario ponderado sea igual en todos,
    respetando un presupuesto total máximo.

    Parámetros:
    - df_asistencia: DataFrame con asistencia (1/0) y columna 'Categoria'
    - df_ponderaciones: DataFrame con eventos como índice y categorías como columnas
    - eventos: lista de nombres de eventos (columnas en df_asistencia)
    - categorias: lista de nombres de categorías (ej: ['A','B','C','D','E'])
    - presupuesto_total_max: presupuesto total máximo a repartir (ej: 1800)
    - categoria_col: nombre de la columna con la categoría en df_asistencia

    Retorna:
    - dict: {evento: presupuesto_calculado}
    - float: valor unitario común
    """
    # Asegurar que ponderaciones y categorías coincidan
    df_ponderaciones = df_ponderaciones[categorias].copy()
    
    # Calcular la "masa ponderada" de cada evento
    masas = {}
    for evento in eventos:
        masa = 0.0
        for _, row in df_asistencia.iterrows():
            if row[evento] == 1:  # si asistió
                cat = row[categoria_col]
                if cat in categorias:
                    masa += df_ponderaciones.loc[evento, cat]
        masas[evento] = masa

    # Calcular factor común
    masa_total = sum(masas.values())
    if masa_total == 0:
        raise ValueError("No hay asistencia en ningún evento. Masa total = 0.")

    valor_unitario = presupuesto_total_max / masa_total

    # Calcular presupuestos finales
    presupuestos = {evento: valor_unitario * masas[evento] for evento in eventos}

    return presupuestos, valor_unitario

# ---------------------------
# Ejemplo de uso con tu archivo
# ---------------------------
if __name__ == "__main__":
    # Cargar hojas
    file_path = "Configuración Xecs.xlsx"
    df_asistencia = pd.read_excel(file_path, sheet_name="Asistencia")
    df_pond = pd.read_excel(file_path, sheet_name="Configuración Precios", index_col=0)

    # Definir eventos y categorías
    eventos = ["Processó La Milagrosa", "FIlles de Maria"]
    categorias = ["A", "B", "C", "D", "E"]
    PRESUPUESTO_MAX = 1800  # €

    # Ejecutar cálculo
    presupuestos, valor_unitario = calcular_presupuestos_iguales(
        df_asistencia=df_asistencia,
        df_ponderaciones=df_pond,
        eventos=eventos,
        categorias=categorias,
        presupuesto_total_max=PRESUPUESTO_MAX
    )

    # Mostrar resultados
    print("Valor unitario común: {:.4f} € por unidad ponderada".format(valor_unitario))
    print("\nPresupuestos ajustados:")
    for ev, pres in presupuestos.items():
        print(f"  {ev}: {pres:.2f} €")
    print(f"\nSuma total: {sum(presupuestos.values()):.2f} €")