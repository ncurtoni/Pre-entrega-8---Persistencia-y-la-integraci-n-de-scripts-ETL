"""
Transformación: limpia las ventas y las agrega por mes, categoría y país.
"""

import pandas as pd

COLUMNAS_REQUERIDAS = ["detalle_id", "pedido_id", "fecha", "estado", "pais",
                       "categoria", "cantidad", "precio_unitario"]


def transformar_ventas(df):
    """
    Limpieza:
    - Quita líneas duplicadas (mismo detalle_id).
    - Descarta los pedidos cancelados: no son ventas.
    - Completa el país faltante con 'Sin dato' (en vez de borrar la fila, para no
      perder ingresos reales en el análisis).
    - Descarta filas con fecha inválida o sin cantidad/precio.

    Agregación: una fila por (mes, categoria, pais) con cantidad de pedidos,
    unidades, ingresos y ticket promedio.
    """
    faltantes = [c for c in COLUMNAS_REQUERIDAS if c not in df.columns]
    if faltantes:
        raise KeyError(f"Faltan columnas para transformar: {faltantes}")

    df = df.copy()  # no se modifica el DataFrame que llega de extract

    df = df.drop_duplicates(subset="detalle_id")
    df = df[df["estado"] != "cancelado"]
    df["pais"] = df["pais"].fillna("Sin dato")

    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha", "categoria", "cantidad", "precio_unitario"])

    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    df["importe"] = df["cantidad"] * df["precio_unitario"]

    resumen = df.groupby(["mes", "categoria", "pais"], as_index=False).agg(
        cant_pedidos=("pedido_id", "nunique"),
        unidades=("cantidad", "sum"),
        ingresos=("importe", "sum"),
    )
    resumen["ingresos"] = resumen["ingresos"].round(2)
    resumen["ticket_promedio"] = (resumen["ingresos"] / resumen["cant_pedidos"]).round(2)

    return resumen.sort_values(["mes", "categoria", "pais"]).reset_index(drop=True)
