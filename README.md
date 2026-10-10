# ETL de ventas: de una base transaccional a una base analítica

Pre-entrega de Data Science II (Coderhouse, comisión 90545): Persistencia y la integración de scripts ETL.

El script toma las ventas de una base transaccional de una tienda online (origen), las limpia y las agrega por mes, categoría y país, y las guarda en una base analítica SQLite (destino). Se puede ejecutar todas las veces que haga falta: el resultado es siempre el mismo y no se duplican datos.

## Requisitos

- Python 3.9 o superior
- Las dependencias de `requirements.txt` (pandas y pytest). El resto de las librerías (`sqlite3`, `argparse`, `logging`) vienen con Python.
- No hace falta instalar ninguna base de datos ni tener conexión a internet: SQLite funciona con archivos locales.

## Pasos para ejecutar

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone <url-del-repositorio>
cd <nombre-del-repositorio>

# 2. (Opcional) crear un entorno virtual
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar el ETL
python main.py

# 5. (Opcional) correr los tests
pytest
```

En Windows con VS Code, si `python` o `pip` no se reconocen, usar `py main.py` y `py -m pip install -r requirements.txt`.

La primera vez, `main.py` genera solo la base de origen simulada en `data/origen.db` (datos inventados, con semilla fija, siempre iguales) y después corre el ETL. El resultado queda en `data/analitica.db`.

Opciones:

| Comando | Qué hace |
|---|---|
| `python main.py` | Corre el ETL con la base simulada (la crea si no existe). |
| `python main.py --recrear-origen` | Vuelve a generar la base de origen simulada y corre el ETL. |
| `python main.py --origen mi_base.db --destino otra.db` | Usa una base de origen propia (solo se lee, nunca se modifica) y otro destino. |

## Patrón de datos utilizado

Es un ETL clásico **OLTP a base analítica**, con carga completa (truncate and load):

1. **Extract** (`src/extract.py`): une las cuatro tablas del sistema transaccional (`clientes`, `productos`, `pedidos`, `detalle_pedido`) en una tabla plana con una fila por línea de pedido. La base de origen se abre en modo solo lectura.
2. **Transform** (`src/transform.py`):
   - quita líneas duplicadas (mismo `detalle_id`);
   - descarta los pedidos cancelados, porque no son ventas;
   - completa el país faltante con `'Sin dato'` en vez de borrar la fila, para no perder ingresos reales;
   - descarta filas con fecha, cantidad o precio inválidos;
   - agrega por mes, categoría y país: cantidad de pedidos, unidades, ingresos y ticket promedio.
3. **Load** (`src/load.py`): ejecuta el DDL del destino y carga el resultado en `ventas_mensuales`.

Por qué se agrega antes de cargar: el destino está pensado para reportes por mes, categoría y país. Guardar ya el resumen evita recalcularlo en cada consulta.

## Esquema de la base de destino

El DDL completo está en [`sql/schema_analitica.sql`](sql/schema_analitica.sql) (el del origen, en `sql/schema_origen.sql`).

| Tabla | Para qué sirve |
|---|---|
| `ventas_mensuales` | Una fila por `(mes, categoria, pais)`. Clave primaria compuesta, con restricciones `CHECK` para que no entren cantidades o ingresos inválidos. |
| `etl_log` | Una fila por ejecución del ETL (fecha, filas extraídas y filas cargadas), para auditar las corridas. |

## Cómo se evitan los duplicados

Se usa **limpieza previa dentro de una transacción**: `DELETE FROM ventas_mensuales` y los `INSERT` ocurren juntos, con un único `commit` al final (`with conn:`). Esto da tres garantías:

- Ejecutar el ETL dos veces deja la tabla igual que ejecutarlo una vez.
- Si algo falla a mitad de la carga, se hace rollback y la tabla queda como estaba (hay un test que lo comprueba).
- La clave primaria `(mes, categoria, pais)` impide guardar la misma combinación dos veces, aunque el código tuviera un error.

Los `CREATE TABLE IF NOT EXISTS` del DDL hacen que el script se pueda correr sobre una base que ya existe sin romper nada.

## Manejo de errores

`main.py` atrapa los errores esperados, los muestra con un mensaje claro y termina con código de salida 1 (útil si el script se automatiza):

| Situación | Resultado |
|---|---|
| La base de origen indicada no existe | `No existe la base de origen: ...` |
| La base de origen no tiene las tablas esperadas | `No se pudo leer la base de origen ...: no such table: ...` |
| El origen no tiene ventas | `La base de origen no tiene ventas para extraer` |
| Falla la carga | Rollback: el destino no queda a medias |

## Estructura del repositorio

```
main.py                      # punto de entrada: orquesta extract, transform y load
sql/
    schema_origen.sql        # DDL de la base transaccional (origen)
    schema_analitica.sql     # DDL de la base analítica (destino)
src/
    crear_origen.py          # genera la base de origen simulada
    extract.py
    transform.py
    load.py
tests/
    test_etl.py              # tests con pytest
data/                        # acá se generan las bases .db (no se suben al repo)
requirements.txt
pytest.ini
.gitignore
```

## Tests

`pytest` corre 10 tests que cubren: limpieza (duplicados, cancelados, país nulo), que `transform` no modifique el DataFrame original, errores de extracción (origen inexistente o sin tablas), creación del DDL, **idempotencia de la carga** (dos corridas no duplican filas) y rollback ante una falla.

## Salida de ejemplo

```
INFO Extrayendo ventas desde data/origen.db
INFO Filas extraídas: 974
INFO Filas después de limpiar y agregar: 224
INFO Filas en ventas_mensuales (destino): 224
INFO ETL finalizado correctamente
```

Una segunda ejecución imprime los mismos números y `ventas_mensuales` sigue con 224 filas. Además, el total de ingresos del destino coincide con el del origen sin pedidos cancelados (234200.40).

Los números exactos dependen de la semilla del generador de datos simulados, y podrían variar levemente con otra versión de Python.

Para consultar el resultado sin instalar nada extra:

```bash
python -c "import sqlite3; c = sqlite3.connect('data/analitica.db'); print(c.execute('SELECT mes, categoria, pais, ingresos FROM ventas_mensuales ORDER BY ingresos DESC LIMIT 5').fetchall())"
```
