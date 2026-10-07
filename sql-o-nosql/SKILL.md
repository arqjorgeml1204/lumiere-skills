---
name: sql-o-nosql
description: Te ayuda a decidir si tu proyecto necesita una base de datos SQL (relacional) o NoSQL, y te entrega el primer diseño listo para usar. Úsala cuando el usuario pregunte qué base de datos usar, si le conviene SQL o NoSQL, PostgreSQL o MongoDB, Firebase o Supabase, o cómo empezar a guardar los datos de su app.
---

# SQL o NoSQL — la decisión, razonada y con el primer diseño

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 3: «Bases de datos: SQL y NoSQL»).

## Qué entrega siempre (el diferenciador)
1. **Seis preguntas** sobre el proyecto (no más).
2. **Matriz de decisión** con la puntuación de `referencia/criterios.md`: cada criterio, la respuesta del usuario y hacia dónde inclina.
3. **Recomendación** en una frase, con el motor concreto sugerido y por qué.
4. **Primer diseño** listo para copiar: sentencias `CREATE TABLE` (si sale SQL) o colecciones con 2 documentos de ejemplo cada una (si sale NoSQL), siguiendo `referencia/plantillas.md`.
5. **Riesgos de la elección** y cuándo convendría replantearla.

## Cómo guiar

**1. Entrevista.** Haz las seis preguntas en un solo mensaje, numeradas, con ejemplos para que un principiante sepa qué contestar. Si el usuario ya contestó alguna en su mensaje, no la repitas.
1. ¿Qué hace tu app, en una frase?
2. ¿Qué «cosas» guardas y cómo se relacionan? (ej.: clientes que hacen pedidos que tienen productos)
3. ¿Hay dinero, inventario o reservas, donde un dato a medias sea grave?
4. ¿La forma de tus datos es fija o cambia seguido / cada registro es distinto?
5. ¿Cuántos datos esperas? (cientos, miles, millones de registros; cuántas escrituras por segundo)
6. ¿Qué preguntas le harás a tus datos (ej.: «ventas por mes», «últimos 20 mensajes de un chat») y necesitas que varios dispositivos vean los cambios en vivo sin tener servidor propio?

**2. Matriz.** Puntúa con `referencia/criterios.md` y muestra la tabla `criterio | lo que dijiste | inclina hacia | puntos`. Suma y muestra el total.

**3. Recomendación.** Una frase con el modelo y el motor. Reglas:
- Empate o duda → **PostgreSQL** (relacional). Es la opción segura por defecto: maneja JSON si después lo necesitas.
- Proyecto pequeño, una sola persona, sin servidor → **SQLite**.
- App móvil/web que necesita sincronización en tiempo real y no quiere servidor propio → **Firestore** (NoSQL documental) o **Supabase** (PostgreSQL); explica la diferencia en una línea.
- Caché, sesiones o contadores → **Redis**, además de la base principal (nunca en lugar de ella).
- **Series de tiempo** (lecturas de sensores, métricas, eventos con fecha que solo se agregan) → menciona siempre las dos vías: **PostgreSQL + TimescaleDB** (si ya hay o habrá datos relacionales, o el total salió en la franja de empate) o una **colección de series de tiempo de MongoDB** (si el total salió NoSQL); usa la plantilla de series de tiempo.
- NoSQL documental: **Firestore** si el criterio 6 (tiempo real sin servidor) suma; **MongoDB** si habrá servidor propio o consultas más ricas.

**4. Primer diseño.** Con los datos del usuario (sus entidades, no un ejemplo genérico), siguiendo `referencia/plantillas.md`. Incluye claves primarias, claves foráneas y un índice por cada consulta frecuente que mencionó.

**5. Riesgos.** Dos o tres viñetas: qué podría obligar a cambiar de decisión y qué hacer desde ya para no quedar atrapado.

## Palabras nuevas (en español la primera vez)
Database · base de datos · Table · tabla · Primary key · clave primaria · Foreign key · clave foránea · Document · documento · Collection · colección · Index · índice · Transaction · transacción · Schema · esquema.

## Reglas
- Español claro y profesional; explica cada término técnico la primera vez.
- No recomiendes por moda: cada recomendación cita qué respuesta del usuario la justifica.
- Precios y límites de planes gratuitos cambian: no los afirmes; di «revisa el plan vigente en su sitio».
- Si el usuario ya eligió una base y solo pide el diseño, salta la entrevista y entrega el paso 4.
