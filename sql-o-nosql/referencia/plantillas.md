# Plantillas del primer diseño

## Si sale SQL (PostgreSQL por defecto; SQLite si es pequeño y sin servidor)

```sql
-- Una tabla por entidad. Nombres en plural y en minúsculas.
CREATE TABLE clientes (
  id          BIGSERIAL PRIMARY KEY,             -- SQLite: INTEGER PRIMARY KEY
  nombre      TEXT NOT NULL,
  correo      TEXT NOT NULL UNIQUE,
  creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()  -- SQLite: TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pedidos (
  id          BIGSERIAL PRIMARY KEY,
  cliente_id  BIGINT NOT NULL REFERENCES clientes(id),  -- clave foránea: la relación
  total       NUMERIC(12,2) NOT NULL CHECK (total >= 0), -- dinero: NUMERIC, nunca FLOAT
  estado      TEXT NOT NULL DEFAULT 'pendiente',
  creado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Un índice por consulta frecuente que mencionó el usuario.
CREATE INDEX pedidos_por_cliente ON pedidos (cliente_id, creado_en DESC);
```

Reglas: dinero en `NUMERIC`; fechas con zona horaria; toda relación con `REFERENCES`; restricciones (`NOT NULL`, `UNIQUE`, `CHECK`) para que la base rechace datos inválidos; atributos variables en una columna `jsonb` en lugar de muchas columnas vacías. En SQLite, recordar `PRAGMA foreign_keys = ON;`.

## Si sale NoSQL documental (MongoDB o Firestore)

```json
// colección: chats  (un documento por conversación)
{ "_id": "chat_8812", "miembros": ["ana", "luis"], "creado_en": "2026-10-08T09:00:00Z", "ultimo_mensaje": { "de": "luis", "texto": "¡Sí!", "en": "2026-10-08T09:16:00Z" } }

// colección: mensajes  (referencian al chat: crecen sin límite, por eso no se embeben)
{ "_id": "m1", "chat_id": "chat_8812", "de": "ana", "tipo": "texto", "texto": "¿Ya viste el partido?", "en": "2026-10-08T09:15:00Z" }
{ "_id": "m2", "chat_id": "chat_8812", "de": "luis", "tipo": "foto", "foto": { "url": "fotos/estadio.jpg", "ancho": 1080 }, "en": "2026-10-08T09:16:00Z" }
```

Reglas: **embeber** lo que se lee junto y tiene tamaño acotado (último mensaje, dirección de envío); **referenciar** lo que crece sin límite o se comparte (mensajes, comentarios); duplicar a propósito los datos que se muestran en listas (`ultimo_mensaje`) para leer en una sola consulta; índice compuesto por el patrón de acceso (`{ chat_id: 1, en: -1 }`); validar la forma con reglas de esquema de la colección (MongoDB `$jsonSchema`) o reglas de seguridad (Firestore).

## Si son series de tiempo (sensores, métricas)

```sql
-- PostgreSQL + TimescaleDB: tabla normal convertida en hipertabla (particionada por tiempo).
CREATE TABLE lecturas (
  sensor_id  TEXT        NOT NULL,
  en         TIMESTAMPTZ NOT NULL,
  temperatura DOUBLE PRECISION,
  extras     JSONB                  -- humedad, luz… solo en los sensores que las miden
);
SELECT create_hypertable('lecturas', 'en');
CREATE INDEX lecturas_sensor_tiempo ON lecturas (sensor_id, en DESC);
-- Retención: borrar lecturas viejas automáticamente
SELECT add_retention_policy('lecturas', INTERVAL '90 days');
```

```js
// MongoDB: colección de series de tiempo con caducidad.
db.createCollection("lecturas", {
  timeseries: { timeField: "en", metaField: "sensor", granularity: "seconds" },
  expireAfterSeconds: 60 * 60 * 24 * 90
});
// documento: { en: ISODate(...), sensor: { id: "inv-07" }, temperatura: 24.1, humedad: 61 }
```

Reglas: la «última lectura por sensor» se guarda aparte (tabla o documento `ultima_lectura` actualizado en cada escritura, o caché en Redis) para no recorrer la serie completa; las alertas se calculan al escribir, no al consultar.
