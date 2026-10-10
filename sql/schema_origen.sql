-- Esquema de la base de ORIGEN (sistema transaccional de una tienda online).
-- Es la fuente de datos del ETL: normalizada, pensada para registrar ventas.

CREATE TABLE clientes (
    cliente_id INTEGER PRIMARY KEY,
    nombre     TEXT NOT NULL,
    pais       TEXT              -- puede ser NULL: algunos clientes no cargaron el país
);

CREATE TABLE productos (
    producto_id INTEGER PRIMARY KEY,
    nombre      TEXT NOT NULL,
    categoria   TEXT NOT NULL,
    precio      REAL NOT NULL CHECK (precio > 0)
);

CREATE TABLE pedidos (
    pedido_id  INTEGER PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes (cliente_id),
    fecha      TEXT NOT NULL,    -- formato YYYY-MM-DD
    estado     TEXT NOT NULL CHECK (estado IN ('entregado', 'pendiente', 'cancelado'))
);

CREATE TABLE detalle_pedido (
    detalle_id      INTEGER PRIMARY KEY,
    pedido_id       INTEGER NOT NULL REFERENCES pedidos (pedido_id),
    producto_id     INTEGER NOT NULL REFERENCES productos (producto_id),
    cantidad        INTEGER NOT NULL CHECK (cantidad > 0),
    precio_unitario REAL NOT NULL CHECK (precio_unitario > 0)
);
