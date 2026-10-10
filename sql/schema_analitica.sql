-- DDL de la base de DESTINO (analítica).
-- Se ejecuta en cada corrida del ETL: como usa IF NOT EXISTS, es seguro repetirlo.

-- Tabla de hechos agregada: una fila por mes, categoría y país.
-- La clave primaria compuesta impide que se guarde dos veces la misma combinación.
CREATE TABLE IF NOT EXISTS ventas_mensuales (
    mes             TEXT    NOT NULL,                          -- formato YYYY-MM
    categoria       TEXT    NOT NULL,
    pais            TEXT    NOT NULL,
    cant_pedidos    INTEGER NOT NULL CHECK (cant_pedidos > 0),
    unidades        INTEGER NOT NULL CHECK (unidades > 0),
    ingresos        REAL    NOT NULL CHECK (ingresos >= 0),
    ticket_promedio REAL    NOT NULL,                          -- ingresos / cant_pedidos
    PRIMARY KEY (mes, categoria, pais)
);

-- Registro de cada ejecución del ETL, para poder auditar qué se cargó y cuándo.
CREATE TABLE IF NOT EXISTS etl_log (
    ejecucion_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha_ejecucion TEXT    NOT NULL,
    filas_origen    INTEGER NOT NULL,                          -- filas extraídas del origen
    filas_cargadas  INTEGER NOT NULL                           -- filas que quedaron en ventas_mensuales
);

-- Índice para consultas por categoría (las más comunes en los reportes)
CREATE INDEX IF NOT EXISTS idx_ventas_categoria ON ventas_mensuales (categoria);
