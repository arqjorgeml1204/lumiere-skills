# Checklist fijo: 8 criterios, 0–2 puntos cada uno (máximo 16)

| # | Criterio | 0 | 1 | 2 |
|---|---|---|---|---|
| 1 | **Rol** | No dice quién responde | Rol genérico («eres un asistente») | Rol con experiencia y para quién escribe («eres contador; le escribes a un cliente sin formación contable») |
| 2 | **Tarea** | Ambigua o con varias tareas mezcladas | Clara pero sin verbo de acción concreto | Un verbo concreto y un resultado medible («clasifica en Queja, Elogio o Duda») |
| 3 | **Contexto** | Ninguno | Parcial | Todo lo que la IA no puede saber: negocio, público, restricciones, fecha si importa |
| 4 | **Formato de salida** | No se pide | Se menciona («en tabla») | Formato exacto: columnas, claves JSON, largo máximo, idioma |
| 5 | **Ejemplos (few-shot)** | Ninguno | Uno, o ejemplos que no se parecen a los casos reales | 1–3 ejemplos de entrada → salida parecidos a los casos reales |
| 6 | **Datos delimitados** | Los datos se mezclan con las instrucciones | Separados por un salto de línea | Entre delimitadores claros (`<datos>…</datos>`, `"""…"""`) |
| 7 | **Permiso para decir «no sé»** | No existe | Implícito | Explícito: qué responder si falta el dato |
| 8 | **Límites** | Ninguno | Algunos | Lo que nunca debe hacer (inventar precios, prometer plazos, dar consejo legal…) |

Lectura: 0–6 débil · 7–11 mejorable · 12–16 sólido. La puntuación orienta; lo que decide son las pruebas con los casos.

## Criterios automáticos al calificar salidas
- **formato**: la salida respeta el formato pedido (si es JSON, `comparar.py` lo comprueba solo con `"formato": "json"` y `"claves"`).
- **no_inventa**: no afirma datos que no estaban en el prompt ni en la entrada. En el caso trampa, pasa solo si dice que no lo sabe o pide el dato.
