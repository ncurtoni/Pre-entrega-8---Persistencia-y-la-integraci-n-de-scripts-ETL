"""
Extracción: lee las ventas de la base de origen.

Une las cuatro tablas del sistema transaccional en una sola tabla plana,
con una fila por línea de pedido.
"""

import sqlite3
from pathlib import Path

import pandas as pd

CONSULTA_VENTAS = """
SELECT d.detalle_id,
       d.pedido_id,
       p.fecha,
       p.estado,
       c.cliente_id,
       c.pais,
       pr.categoria,
       d.cantidad,
       d.precio_unitario
FROM detalle_pedido d
JOIN pedidos   p  ON d.pedido_id   = p.pedido_id
JOIN clientes  c  ON p.cliente_id  = c.cliente_id
JOIN productos pr ON d.producto_id = pr.producto_id
"""


def extraer_ventas(ruta_origen):
    """
    Devuelve un DataFrame con todas las líneas de pedido del origen.

    Errores que levanta (los captura main.py y muestra un mensaje claro):
    - FileNotFoundError: la base de origen no existe.
    - sqlite3.Error: la base está dañada o le falta alguna tabla.
    - ValueError: la consulta no devolvió ninguna fila.
    """
    ruta = Path(ruta_origen)
    if not ruta.exists():
        raise FileNotFoundError(f"No existe la base de origen: {ruta}")

    # modo solo lectura: el ETL nunca debe modificar el sistema transaccional
    conn = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True)
    try:
        df = pd.read_sql_query(CONSULTA_VENTAS, conn)
    except pd.errors.DatabaseError as e:
        # pandas envuelve los errores de SQL en su propio tipo; se vuelve a
        # sqlite3.Error para manejar todos los errores de base de la misma forma
        causa = e.__cause__ or e  # el error original de sqlite, sin repetir todo el SQL
        raise sqlite3.DatabaseError(f"No se pudo leer la base de origen {ruta}: {causa}") from e
    finally:
        conn.close()

    if df.empty:
        raise ValueError("La base de origen no tiene ventas para extraer")
    return df
