# Matriz de decisión SQL / NoSQL

Puntuación: valores negativos inclinan a **SQL**, positivos a **NoSQL**. Total ≤ −2 → SQL · total ≥ +3 → NoSQL · entre −1 y +2 → PostgreSQL (relacional con columnas JSON para lo variable).

| # | Criterio | Respuesta típica | Puntos |
|---|---|---|---|
| 1 | Relaciones entre entidades | Muchas entidades relacionadas y consultadas juntas (clientes–pedidos–productos) | −2 |
|   |  | Pocas relaciones; los datos se leen agrupados por un dueño (todos los mensajes de un chat) | +2 |
| 2 | Integridad crítica | Dinero, inventario, reservas, calificaciones oficiales | −3 |
|   |  | Un dato a medias no es grave (likes, vistas, lecturas de sensores) | +1 |
| 3 | Forma de los datos | Fija y conocida | −1 |
|   |  | Pocos campos opcionales sobre una base común | +1 |
|   |  | Cambia seguido o cada registro es distinto (catálogos con atributos variables, eventos) | +2 |
| 4 | Volumen y escrituras | Hasta millones de registros, escrituras moderadas | −1 |
|   |  | Escrituras sostenidas ≥ 1,000 por segundo, o más de 1,000 millones de registros al año | +2 |
|   |  | Entre ambos (decenas a cientos de escrituras por segundo) | +1 |
| 5 | Consultas | Preguntas nuevas e informes con agregaciones («ventas por ciudad y mes») | −2 |
|   |  | Patrones fijos y conocidos («últimos 20 mensajes del chat X») | +1 |
| 6 | Tiempo real sin servidor propio (se pregunta en la 6) | Necesita sincronización en vivo entre dispositivos y no quiere administrar servidor | +1 (y considerar Firestore o Supabase) |
|   |  | No lo necesita o tendrá servidor propio | 0 |

## Notas para explicar el resultado
- **Integridad** pesa más que cualquier otro criterio: si hay dinero, la recomendación base es relacional aunque otros criterios sumen hacia NoSQL; lo variable se guarda en columnas JSON (`jsonb` en PostgreSQL).
- **Volumen** casi nunca decide al empezar: millones de registros caben bien en PostgreSQL con índices. Solo pesa con escrituras masivas sostenidas.
- **Persistencia políglota**: si la matriz sale dividida por partes del sistema (pagos vs. mensajes), recomienda la base principal relacional y un componente NoSQL solo para la parte que lo justifica.
