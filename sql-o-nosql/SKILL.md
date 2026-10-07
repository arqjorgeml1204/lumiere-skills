---
name: sql-o-nosql
description: Analiza tu proyecto o idea (una descripción, tu código, tus modelos o tus exportaciones de datos) y te entrega la arquitectura de datos completa — qué base de datos te conviene y por qué, punto por punto, el mapa de entidades, el esquema, los índices, las consultas clave y una base de datos prototipo que ya funciona en tu computadora. Úsala cuando el usuario pregunte qué base de datos usar, SQL o NoSQL, PostgreSQL o MongoDB, Firebase o Supabase, cómo diseñar las tablas de su app o cómo organizar sus datos.
---

# SQL o NoSQL — análisis de tu proyecto y arquitectura de datos lista para usar

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 3: «Bases de datos: SQL y NoSQL»).

## Qué hace que un chat normal no hace
1. **Lee tu proyecto real**, no uno genérico: tu descripción, y si hay archivos, tus modelos, migraciones, esquemas, dependencias o exportaciones (CSV/Excel/JSON). De ahí saca entidades, relaciones y patrones de acceso.
2. **Decide con un método fijo y visible** (`referencia/criterios.md`): cada criterio con la evidencia de *tu* proyecto que lo justifica.
3. **Entrega archivos, no solo texto**: un informe completo y una **base de datos prototipo que se ejecuta** con datos de ejemplo y tus consultas clave, comprobada antes de entregarla.

## Proceso

**1. Reunir evidencia.**
- Si hay acceso a archivos del proyecto, búscalos antes de preguntar nada: modelos u ORM (`models.py`, `schema.prisma`, `*.entity.ts`, `models/`), migraciones (`migrations/`, `*.sql`), esquemas de Firebase (`firestore.rules`, `*.json`), dependencias (`package.json`, `requirements.txt`, `pubspec.yaml`) y exportaciones de datos. Cita los archivos que usaste.
- Si solo hay una descripción, haz **solo las preguntas cuya respuesta falte** de estas seis (en un mensaje, numeradas, con ejemplos): qué hace la app; qué «cosas» guarda y cómo se relacionan; si hay dinero, inventario o reservas; si la forma de los datos es fija o variable; volumen esperado (registros y escrituras por segundo); qué preguntas se le harán a los datos y si varios dispositivos deben ver cambios en vivo sin servidor propio.

**2. Mapa de entidades.** Lista de entidades con sus atributos clave y cardinalidad de cada relación (1:1, 1:N, N:M), más un diagrama Mermaid `erDiagram`.

**3. Patrones de acceso.** Tabla `consulta | quién la hace | frecuencia estimada | latencia esperada | cómo se resuelve (índice, tabla, documento embebido)`. Mínimo las 5 consultas más importantes.

**4. Matriz de decisión** con `referencia/criterios.md`: `criterio | evidencia de tu proyecto | inclina hacia | puntos`, total y umbral aplicado.

**5. Recomendación razonada.** Modelo y motor concretos, y **por qué** en 3–5 puntos ligados a la evidencia. Incluye: alternativa descartada y por qué; dónde alojarla (servidor propio, servicio administrado: Supabase, Neon, Amazon RDS, MongoDB Atlas, Firestore — sin afirmar precios: «revisa el plan vigente») según el tamaño del equipo. Reglas de desempate en `referencia/criterios.md`.

**6. Diseño completo** (plantillas en `referencia/plantillas.md`):
- SQL: DDL de PostgreSQL con claves, restricciones, tipos correctos (dinero en `NUMERIC`), índices justificados por los patrones del paso 3.
- NoSQL documental: colecciones, un documento de ejemplo por colección, decisión embeber/referenciar razonada, validación de esquema e índices.
- Series de tiempo: hipertabla de TimescaleDB o colección de series de tiempo de MongoDB, con retención.

**7. Prototipo ejecutable** (el entregable diferenciador):
- Escribe `prototipo/prototipo.sql` en el dialecto de **SQLite** (equivalente al diseño; anota las diferencias con PostgreSQL), con: `PRAGMA foreign_keys = ON;`, el esquema, **datos de ejemplo realistas del dominio del usuario** (10–30 filas por tabla principal) y las consultas clave del paso 3, cada una precedida por una línea `-- consulta: <nombre>`.
- Agrega **al menos 3 reglas de negocio que la base debe rechazar**, cada una precedida por `-- debe-fallar: <nombre>` (ej.: monto negativo, referencia inexistente, cupo lleno, duplicado). El script comprueba que se rechazan; así el prototipo demuestra sus reglas, no solo su sintaxis.
- Usa **fechas fijas** en datos y consultas (no `date('now')`), para que los resultados sean reproducibles.
- Si una regla depende de concurrencia (cupos, inventario), el prototipo de SQLite la muestra con un trigger y el informe da la versión segura para PostgreSQL (`SELECT … FOR UPDATE` o restricción equivalente).
- Copia `scripts/probar_prototipo.py` junto a él y ejecútalo (`python probar_prototipo.py`): crea `prototipo.db`, carga todo y ejecuta cada consulta mostrando sus resultados. **Si algo falla, corrígelo antes de entregar.** Para NoSQL, además del prototipo relacional de las entidades estables, entrega `prototipo/mongo.js` (colecciones, validación, índices e inserciones) para `mongosh`.
- Dile al usuario cómo abrir `prototipo.db` en DB Browser for SQLite para explorarlo.

**8. Plan de crecimiento y riesgos.** Qué cambiar a 10× y a 100× de datos o usuarios; dos o tres riesgos de la decisión y cómo mitigarlos desde ya.

**9. Informe.** Si hay acceso a archivos, guarda todo lo anterior en `informe-datos.md` (estructura en `referencia/plantillas.md`) además de mostrar el resumen en el chat. Si no hay acceso a archivos, entrega el informe completo en el chat y los archivos del prototipo como bloques listos para copiar, con la instrucción para ejecutarlos.

## Palabras nuevas (en español la primera vez)
Database · base de datos · Table · tabla · Primary key · clave primaria · Foreign key · clave foránea · Document · documento · Collection · colección · Index · índice · Transaction · transacción · Schema · esquema · Seed · datos de ejemplo.

## Reglas
- Profesional y claro; explica cada término técnico la primera vez.
- Nada de recomendaciones por moda: cada afirmación se apoya en evidencia del proyecto o en un criterio de la matriz.
- No inventes archivos que no viste ni datos del usuario que no dio: si supones algo (volumen, frecuencia, tiempo real), márcalo como **supuesto** (S1, S2…) en el informe. Si un dato faltante **no cambiaría la recomendación** (el total de la matriz quedaría del mismo lado del umbral con cualquier respuesta), no lo preguntes: anótalo como supuesto y sigue.
- Nunca pidas ni muestres contraseñas o cadenas de conexión reales.
