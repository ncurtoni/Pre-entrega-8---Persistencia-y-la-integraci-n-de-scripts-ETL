import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from src.crear_origen import crear_origen
from src.extract import extraer_ventas
from src.load import cargar_ventas
from src.transform import transformar_ventas

DDL_DESTINO = Path(__file__).resolve().parent.parent / "sql" / "schema_analitica.sql"


@pytest.fixture
def ventas_ejemplo():
    """Dataset chico armado a mano, con un duplicado, un cancelado y un país nulo."""
    return pd.DataFrame({
        "detalle_id": [1, 2, 2, 3, 4],
        "pedido_id": [10, 10, 10, 11, 12],
        "fecha": ["2025-01-05", "2025-01-05", "2025-01-05", "2025-01-20", "2025-02-01"],
        "estado": ["entregado", "entregado", "entregado", "cancelado", "pendiente"],
        "cliente_id": [1, 1, 1, 2, 3],
        "pais": ["Chile", "Chile", "Chile", "Chile", None],
        "categoria": ["Hogar", "Hogar", "Hogar", "Hogar", "Ropa"],
        "cantidad": [2, 1, 1, 5, 3],
        "precio_unitario": [10.0, 20.0, 20.0, 99.0, 5.0],
    })


@pytest.fixture
def origen_db(tmp_path):
    ruta = tmp_path / "origen.db"
    crear_origen(ruta, n_clientes=10, n_pedidos=50)
    return ruta


# ---------- transform ----------

def test_transform_quita_duplicados_y_cancelados(ventas_ejemplo):
    r = transformar_ventas(ventas_ejemplo)
    # enero/Hogar: solo el pedido 10 (2*10 + 1*20 = 40). El cancelado no cuenta
    fila = r[(r["mes"] == "2025-01") & (r["categoria"] == "Hogar")].iloc[0]
    assert fila["ingresos"] == 40.0
    assert fila["cant_pedidos"] == 1
    assert fila["unidades"] == 3


def test_transform_completa_pais_nulo(ventas_ejemplo):
    r = transformar_ventas(ventas_ejemplo)
    assert "Sin dato" in r["pais"].tolist()
    assert r["pais"].notna().all()


def test_transform_no_modifica_el_original(ventas_ejemplo):
    copia = ventas_ejemplo.copy()
    transformar_ventas(ventas_ejemplo)
    pd.testing.assert_frame_equal(ventas_ejemplo, copia)


def test_transform_columna_faltante_da_error(ventas_ejemplo):
    with pytest.raises(KeyError):
        transformar_ventas(ventas_ejemplo.drop(columns=["estado"]))


# ---------- extract ----------

def test_extract_origen_inexistente(tmp_path):
    with pytest.raises(FileNotFoundError):
        extraer_ventas(tmp_path / "no_existe.db")


def test_extract_base_sin_tablas(tmp_path):
    vacia = tmp_path / "vacia.db"
    sqlite3.connect(vacia).close()
    with pytest.raises(sqlite3.Error):  # faltan las tablas del sistema transaccional
        extraer_ventas(vacia)


def test_extract_devuelve_filas(origen_db):
    df = extraer_ventas(origen_db)
    assert len(df) > 0
    assert {"detalle_id", "categoria", "pais", "estado"} <= set(df.columns)


# ---------- load ----------

def test_load_crea_tablas_y_carga(tmp_path, ventas_ejemplo):
    destino = tmp_path / "analitica.db"
    resumen = transformar_ventas(ventas_ejemplo)
    cargadas = cargar_ventas(resumen, destino, DDL_DESTINO, filas_origen=len(ventas_ejemplo))
    assert cargadas == len(resumen)

    conn = sqlite3.connect(destino)
    tablas = {f[0] for f in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"ventas_mensuales", "etl_log"} <= tablas


def test_load_es_idempotente(tmp_path, ventas_ejemplo):
    """Correr la carga dos veces no debe duplicar filas."""
    destino = tmp_path / "analitica.db"
    resumen = transformar_ventas(ventas_ejemplo)
    primera = cargar_ventas(resumen, destino, DDL_DESTINO, filas_origen=5)
    segunda = cargar_ventas(resumen, destino, DDL_DESTINO, filas_origen=5)
    assert primera == segunda

    conn = sqlite3.connect(destino)
    corridas = conn.execute("SELECT COUNT(*) FROM etl_log").fetchone()[0]
    conn.close()
    assert corridas == 2  # el log sí registra las dos ejecuciones


def test_load_hace_rollback_si_falla(tmp_path, ventas_ejemplo):
    """Si la carga falla a mitad de camino, la tabla debe quedar como estaba."""
    destino = tmp_path / "analitica.db"
    resumen = transformar_ventas(ventas_ejemplo)
    cargar_ventas(resumen, destino, DDL_DESTINO, filas_origen=5)

    roto = pd.concat([resumen, resumen.iloc[[0]]], ignore_index=True)  # clave primaria repetida
    with pytest.raises(sqlite3.IntegrityError):
        cargar_ventas(roto, destino, DDL_DESTINO, filas_origen=5)

    conn = sqlite3.connect(destino)
    filas = conn.execute("SELECT COUNT(*) FROM ventas_mensuales").fetchone()[0]
    conn.close()
    assert filas == len(resumen)  # la carga anterior sigue intacta
