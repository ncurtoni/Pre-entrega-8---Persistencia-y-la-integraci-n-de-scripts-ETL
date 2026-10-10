"""
Punto de entrada del ETL: origen transaccional (SQLite) -> base analítica (SQLite).

Uso:
    python main.py                      # usa la base de origen simulada (la crea si no existe)
    python main.py --recrear-origen     # vuelve a generar la base simulada
    python main.py --origen mi_base.db --destino data/analitica.db   # usa una base propia
"""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

from src.crear_origen import crear_origen
from src.extract import extraer_ventas
from src.load import cargar_ventas
from src.transform import transformar_ventas

RAIZ = Path(__file__).resolve().parent
RUTA_ORIGEN = RAIZ / "data" / "origen.db"
RUTA_DESTINO = RAIZ / "data" / "analitica.db"
RUTA_DDL_DESTINO = RAIZ / "sql" / "schema_analitica.sql"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def ejecutar_etl(ruta_origen, ruta_destino):
    """Corre las tres etapas en orden y devuelve la cantidad de filas cargadas."""
    logging.info("Extrayendo ventas desde %s", ruta_origen)
    ventas = extraer_ventas(ruta_origen)
    logging.info("Filas extraídas: %d", len(ventas))

    resumen = transformar_ventas(ventas)
    logging.info("Filas después de limpiar y agregar: %d", len(resumen))

    cargadas = cargar_ventas(resumen, ruta_destino, RUTA_DDL_DESTINO, filas_origen=len(ventas))
    logging.info("Filas en ventas_mensuales (destino): %d", cargadas)
    return cargadas


def main():
    parser = argparse.ArgumentParser(description="ETL de ventas: origen transaccional a base analítica")
    parser.add_argument("--origen", default=None,
                        help="ruta de una base de origen propia (si no se indica, se usa la simulada en data/origen.db)")
    parser.add_argument("--destino", default=str(RUTA_DESTINO), help="ruta de la base analítica")
    parser.add_argument("--recrear-origen", action="store_true",
                        help="vuelve a generar la base de origen simulada (solo la de por defecto)")
    args = parser.parse_args()

    try:
        if args.origen:
            # Base propia: se usa tal cual. Nunca se crea ni se borra, solo se lee.
            if args.recrear_origen:
                parser.error("--recrear-origen solo se puede usar con la base simulada por defecto")
            origen = Path(args.origen)
        else:
            origen = RUTA_ORIGEN
            if args.recrear_origen or not origen.exists():
                n = crear_origen(origen)
                logging.info("Base de origen simulada creada en %s (%d pedidos)", origen, n)

        ejecutar_etl(origen, args.destino)
        logging.info("ETL finalizado correctamente")
    except (FileNotFoundError, ValueError, KeyError, sqlite3.Error) as e:
        logging.error("El ETL falló: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
