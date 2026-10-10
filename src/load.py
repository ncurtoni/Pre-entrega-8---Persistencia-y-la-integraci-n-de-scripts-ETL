"""
Carga: guarda el resultado en la base de datos analítica (SQLite).

Para evitar duplicados se usa "limpieza previa": dentro de una misma transacción
se vacía la tabla y se vuelve a insertar todo. Así, ejecutar el ETL dos veces
deja exactamente el mismo resultado que ejecutarlo una vez.
"""

import sqlite3
from datetime import datetime
from pathlib import Path


def cargar_ventas(resumen, ruta_destino, ruta_ddl, filas_origen):
    """
    Crea las tablas si no existen (DDL) y carga el resumen.
    Devuelve la cantidad de filas que quedaron en ventas_mensuales.
    """
    ruta_destino = Path(ruta_destino)
    ruta_destino.parent.mkdir(parents=True, exist_ok=True)
    ddl = Path(ruta_ddl).read_text(encoding="utf-8")

    # Se pasan a tipos nativos de Python: sqlite3 no acepta int64/float64 de numpy
    filas = [
        (str(r.mes), str(r.categoria), str(r.pais), int(r.cant_pedidos),
         int(r.unidades), float(r.ingresos), float(r.ticket_promedio))
        for r in resumen.itertuples(index=False)
    ]

    conn = sqlite3.connect(ruta_destino)
    try:
        conn.executescript(ddl)

        # "with conn" hace un único commit al final, o rollback si algo falla:
        # nunca queda la tabla a medio cargar.
        with conn:
            conn.execute("DELETE FROM ventas_mensuales")
            conn.executemany(
                """INSERT INTO ventas_mensuales
                   (mes, categoria, pais, cant_pedidos, unidades, ingresos, ticket_promedio)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                filas,
            )
            conn.execute(
                "INSERT INTO etl_log (fecha_ejecucion, filas_origen, filas_cargadas) VALUES (?, ?, ?)",
                (datetime.now().isoformat(timespec="seconds"), int(filas_origen), len(filas)),
            )

        return conn.execute("SELECT COUNT(*) FROM ventas_mensuales").fetchone()[0]
    finally:
        conn.close()
