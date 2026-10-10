"""
Crea la base de datos de ORIGEN con datos simulados de una tienda online.

Los datos son inventados (no son reales) y se generan con una semilla fija,
así que siempre salen iguales. Eso permite que cualquiera ejecute el ETL sin
descargar nada ni depender de internet.
"""

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

RUTA_DDL = Path(__file__).resolve().parent.parent / "sql" / "schema_origen.sql"

PAISES = ["Argentina", "Chile", "Uruguay", "Brasil"]
PRODUCTOS = [
    ("Auriculares", "Electronica", 45.0),
    ("Teclado", "Electronica", 30.0),
    ("Monitor", "Electronica", 220.0),
    ("Lampara", "Hogar", 18.5),
    ("Juego de sabanas", "Hogar", 35.0),
    ("Cafetera", "Hogar", 60.0),
    ("Remera", "Ropa", 12.0),
    ("Campera", "Ropa", 80.0),
    ("Zapatillas", "Ropa", 95.0),
    ("Pelota", "Deportes", 20.0),
    ("Bicicleta", "Deportes", 350.0),
    ("Mancuernas", "Deportes", 40.0),
]


def crear_origen(ruta_db, semilla=42, n_clientes=40, n_pedidos=400):
    """Crea (o recrea) la base de origen y devuelve la cantidad de pedidos generados."""
    ruta_db = Path(ruta_db)
    ruta_db.parent.mkdir(parents=True, exist_ok=True)
    if ruta_db.exists():
        ruta_db.unlink()  # se parte siempre de una base vacía

    rng = random.Random(semilla)
    ddl = RUTA_DDL.read_text(encoding="utf-8")

    clientes = []
    for i in range(1, n_clientes + 1):
        # ~10% de clientes sin país, para tener un nulo real que limpiar
        pais = None if rng.random() < 0.10 else rng.choice(PAISES)
        clientes.append((i, f"Cliente {i}", pais))

    productos = [(i, nombre, cat, precio) for i, (nombre, cat, precio) in enumerate(PRODUCTOS, start=1)]

    pedidos = []
    detalles = []
    detalle_id = 1
    inicio = date(2025, 1, 1)
    for pedido_id in range(1, n_pedidos + 1):
        fecha = inicio + timedelta(days=rng.randint(0, 364))
        estado = rng.choices(["entregado", "cancelado", "pendiente"], weights=[80, 12, 8])[0]
        pedidos.append((pedido_id, rng.randint(1, n_clientes), fecha.isoformat(), estado))

        for producto in rng.sample(productos, k=rng.randint(1, 4)):
            precio_unitario = round(producto[3] * rng.choice([1.0, 1.0, 0.9]), 2)  # a veces con descuento
            detalles.append((detalle_id, pedido_id, producto[0], rng.randint(1, 5), precio_unitario))
            detalle_id += 1

    conn = sqlite3.connect(ruta_db)
    try:
        conn.executescript(ddl)
        with conn:  # una sola transacción para toda la carga inicial
            conn.executemany("INSERT INTO clientes VALUES (?, ?, ?)", clientes)
            conn.executemany("INSERT INTO productos VALUES (?, ?, ?, ?)", productos)
            conn.executemany("INSERT INTO pedidos VALUES (?, ?, ?, ?)", pedidos)
            conn.executemany("INSERT INTO detalle_pedido VALUES (?, ?, ?, ?, ?)", detalles)
    finally:
        conn.close()

    return len(pedidos)
