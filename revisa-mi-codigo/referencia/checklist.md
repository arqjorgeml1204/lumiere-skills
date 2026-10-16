# Checklist fijo de revisión (siempre los 10 puntos, en este orden)

Inspirado en la guía pública de revisión de código de Google ([google.github.io/eng-practices/review](https://google.github.io/eng-practices/review/)) y en el capítulo 9 de *Software Engineering at Google* ([abseil.io/resources/swe-book/html/ch09.html](https://abseil.io/resources/swe-book/html/ch09.html)). Es una adaptación en español para quien empieza, no una copia.

## La regla de oro: ¿el código queda mejor que antes?
Un cambio se aprueba cuando **mejora la salud del código**, aunque no sea perfecto. Nadie escribe código perfecto; lo que se busca es que cada cambio deje las cosas un poco mejor. Por eso:
- Lo que rompe algo, abre un hueco de seguridad o deja lógica nueva sin probar **bloquea**.
- Lo que solo lo haría más bonito es **sugerencia** o **detalle**, y la decisión es de quien escribió el código.
- Los gustos personales no son reglas: si no hay una guía de estilo que lo diga, no bloquea.

## Cómo recorrer el cambio
1. **Vista general**: lee la descripción (o pregunta qué querían lograr) y la lista de archivos. ¿El cambio tiene sentido? Si la idea de fondo está mal, dilo primero, antes de comentar comas.
2. **La parte principal**: empieza por el archivo con más lógica nueva. Ahí suelen estar los problemas de diseño.
3. **El resto**, en orden lógico (primero las pruebas, porque te dicen qué se quería lograr).
4. **Cada línea que te toca revisar**, de verdad. Si no entiendes algo, eso ya es un comentario: el próximo que lo lea tampoco lo va a entender.

## Los 10 puntos

| # | Punto | Pregúntate | Nivel habitual |
|---|---|---|---|
| 1 | **Diseño** | ¿Las piezas encajan? ¿Esto va en este archivo o en otro? ¿Es el momento de agregarlo? | Bloquea si complica todo lo demás; si no, Sugerencia |
| 2 | **Funcionalidad y casos borde** | ¿Hace lo que se quería? ¿Qué pasa con una lista vacía, un cero, un texto vacío, un `None`/`null`, un número negativo, un archivo que no existe, dos personas a la vez? | Bloquea si truena o da un resultado equivocado |
| 3 | **Complejidad** | ¿Se entiende rápido? ¿Hay código «por si acaso» que nadie pidió? ¿Una función hace demasiadas cosas? | Sugerencia |
| 4 | **Pruebas** | ¿La lógica nueva tiene prueba? ¿La prueba fallaría si el código estuviera mal? ¿Prueba los casos borde del punto 2? | Bloquea si la lógica nueva no tiene ninguna prueba |
| 5 | **Nombres** | ¿El nombre dice qué es o qué hace, sin ser un párrafo? (`total_con_iva` y no `x2`) | Detalle o Sugerencia |
| 6 | **Comentarios** | ¿Explican el *porqué* (no el *qué*, que ya dice el código)? ¿Hay comentarios viejos que ya mienten o código comentado que sobra? | Detalle |
| 7 | **Estilo y consistencia** | ¿Sigue la guía de estilo del proyecto y se parece al código de alrededor? Lo que ya marca el linter no se repite a mano. | Detalle |
| 8 | **Seguridad** | Ver la lista de abajo. | Bloquea casi siempre |
| 9 | **Documentación** | Si cambia cómo se instala, se usa o se configura, ¿se actualizó el README o la documentación? | Sugerencia (Bloquea si sin eso nadie puede usarlo) |
| 10 | **Lo que está bien hecho** | ¿Qué aprendiste del cambio? ¿Qué decisión fue buena? Dilo con la línea exacta. | Bien hecho (mínimo uno) |

### Punto 8 — Seguridad (revisa siempre estas seis)
1. **Secretos en el código**: llaves de API, contraseñas, tokens, cadenas de conexión con usuario y contraseña. Van en variables de entorno o en un gestor de secretos, nunca en el repositorio. Si ya se subió a git, cambiarla de lugar no basta: **hay que revocarla y crear otra**, porque queda en el historial.
2. **Consultas SQL armadas con texto del usuario** (f-strings, `+`, `format`, plantillas de texto): permiten la *inyección SQL*. Se arreglan con parámetros (`?`, `%s`, `$1`) que la biblioteca de la base de datos escapa por ti.
3. **Entradas sin validar**: datos que llegan de un formulario, una URL, un archivo o una API se tratan como sospechosos. Revisa tipo, rango y tamaño antes de usarlos.
4. **Comandos o rutas armados con texto del usuario** (`os.system`, `subprocess(..., shell=True)`, `exec`, `eval`, rutas `../`): mismo problema que el SQL.
5. **Datos personales en los registros** (logs): contraseñas, correos, tarjetas o tokens impresos con `print` o `console.log`.
6. **Errores que se tragan**: un `except: pass` o un `catch {}` vacío esconde fallas y a veces deja pasar a quien no debería.

## Qué decide cada nivel
- **Bloquea**: hay que arreglarlo antes de integrar el cambio. Úsalo poco y siempre con el motivo concreto (qué se rompe o qué riesgo abre).
- **Sugerencia**: mejora real; quien escribió el código decide. Si no la toma, se acepta su explicación.
- **Detalle**: pulido menor (un nombre, un espacio, una coma). En Google le dicen *nit*. Nunca detiene el cambio.
- **Bien hecho**: algo que vale la pena repetir. Cuenta igual que los demás: también enseña.

## Veredicto
| Veredicto | Cuándo |
|---|---|
| **Aprobar** | Sin «Bloquea», las pruebas pasan y no hay sugerencias importantes pendientes. |
| **Aprobar con cambios** | Sin «Bloquea» y las pruebas pasan, pero hay sugerencias que conviene atender; se confía en que la persona las resuelva sin otra revisión. |
| **Necesita cambios** | Hay al menos un «Bloquea», o las pruebas o el revisor de tipos fallan por culpa del cambio. |

## Tamaño
Si el cambio pasa de **400 líneas**, la atención de quien revisa baja y se escapan errores. Propón partirlo (por carpeta o por tema) y revisa una parte a la vez. Los cambios pequeños se revisan más rápido y mejor; en Google se insiste en cambios chicos por la misma razón.
