# Plantilla de `revision-codigo.md` y cómo escribir cada comentario

El verificador (`scripts/verificar_revision.py`) lee este formato exacto. Respeta los títulos `##`, el `**Veredicto:**` y el encabezado de cada comentario `### [Nivel] archivo:línea`.

## Plantilla

```markdown
# Revisión de código: <qué hace el cambio, en una frase>

**Veredicto:** Necesita cambios
**Cambio revisado:** rama `<rama>` contra `<base>` · <N> archivos · <M> líneas
**En una línea:** <lo más importante que debe saber quien escribió el código>

## Resultado de pruebas y revisores
| Herramienta | Resultado | Detalle |
|---|---|---|
| unittest | FALLA | 1 de 6 pruebas falla: `test_promedio_vacio` (ZeroDivisionError) |
| compilación de Python | PASA | sin errores de sintaxis |
| ruff / flake8 | NO EJECUTADO | no está instalado |

## Comentarios que bloquean

### [Bloquea] app/consultas.py:14
**Qué veo:** La consulta se arma pegando el nombre que escribe el usuario dentro del texto SQL.
**Por qué importa:** Alguien puede escribir `' OR '1'='1` y leer todos los clientes; se llama inyección SQL.
**Propuesta:** Usa un parámetro: `conexion.execute("SELECT ... WHERE nombre = ?", (nombre,))`.

## Sugerencias

### [Sugerencia] app/precios.py:30-34
**Qué veo:** ...
**Por qué importa:** ...
**Propuesta:** ...

## Detalles

### [Detalle] app/precios.py:8
**Qué veo:** ...
**Por qué importa:** ...
**Propuesta:** ...

## Lo que está bien hecho

### [Bien hecho] tests/test_precios.py:12
**Qué veo:** La prueba cubre el caso de propina negativa además del caso normal.
**Por qué importa:** Así, si alguien rompe esa validación en el futuro, la prueba lo avisa antes de que llegue a producción.

## Lo que aprendes de este cambio
1. <lección general, conectada con un comentario>
2. <lección>
3. <opcional>

## Siguiente paso
<qué hacer ahora, en orden: primero lo que bloquea>
```

Reglas del formato:
- **Números de línea del archivo nuevo** (el lado derecho del diff, el de `+`). Para un rango: `archivo:30-34`. Si comentas código que se borró, cita la línea más cercana del archivo nuevo.
- Rutas relativas a la raíz del proyecto y con `/` (también en Windows).
- Si una sección no tiene comentarios, escribe «Ninguno.» debajo del título; no la borres.
- «Bien hecho» lleva **Qué veo** y **Por qué importa**; los demás niveles llevan además **Propuesta**.

## Cómo escribir un comentario de mentor (tono de editor, no de juez)
Un editor de libros no reescribe tu libro: te señala qué confunde al lector y te propone cómo arreglarlo. Así se escribe cada comentario.

1. **Habla del código, no de la persona.** «Esta función no revisa si la lista viene vacía», no «no revisaste la lista».
2. **Explica el porqué**, con la consecuencia concreta (qué se rompe, quién se ve afectado). Un «cámbialo» sin porqué no enseña nada.
3. **Propón algo concreto**: el cambio, un ejemplo de código corto o la función de la biblioteca que lo resuelve. Si hay varias opciones, da la que recomiendas.
4. **Pregunta cuando no estés seguro**: «¿Este valor puede llegar vacío? Si sí, …». Tal vez la persona sabe algo que tú no.
5. **Marca el nivel con honestidad**: no infles un detalle a «Bloquea» ni escondas un riesgo de seguridad como «Sugerencia».
6. **Reconoce lo bueno con la misma precisión** que lo malo: línea exacta y por qué está bien.
7. **Un tema por comentario.** Si el mismo problema se repite en cinco lugares, un comentario con todas las líneas en «Qué veo» basta.

### Frases que el verificador rechaza (y cómo decirlo mejor)
| Evita (FALLA) | Mejor |
|---|---|
| «Esto está mal» | «Esta línea da un resultado distinto al esperado cuando…» |
| «Obvio» / «obviamente» | Explica el motivo; si fuera obvio, no habría que comentarlo. |
| «Cualquiera sabe que…», «es básico» | «Una práctica común es… porque…» |
| «Hiciste mal», «te equivocaste» | «Este código…», «esta función…» |
| «Horrible», «basura», «ridículo», «pésimo» | Describe el problema concreto. |

Frases que solo generan AVISO porque minimizan el esfuerzo de la otra persona: «simplemente», «solo tienes que», «es fácil», «es trivial». Casi siempre puedes borrarlas y la frase queda mejor.

## Formato JSON (opcional, para publicar comentarios en un pull request)
```json
{
  "veredicto": "Necesita cambios",
  "pruebas": "unittest FALLA (1 de 6); compilación de Python PASA; ruff / flake8 NO EJECUTADO",
  "comentarios": [
    {"archivo": "app/consultas.py", "linea": "14", "nivel": "Bloquea",
     "que_veo": "…", "porque": "…", "propuesta": "…"}
  ],
  "lecciones": ["…", "…"]
}
```

## Publicar en el pull request (solo si el usuario lo pide y tiene `gh`)
Publicar es una acción hacia otras personas: **antes, muestra exactamente qué se va a publicar y pide un «sí» explícito.** Nunca apruebes ni pidas cambios en nombre del usuario: publica siempre como comentario.

- **Toda la revisión como un solo comentario**: `gh pr review <número> --comment --body-file revision-codigo/revision-codigo.md`
- **Comentarios en la línea exacta**: GitHub solo acepta comentarios en líneas que aparecen en el diff; por eso el verificador separa «dentro del cambio» de «contexto». Los de contexto van en el cuerpo general. Arma un `revision-codigo/comentarios-pr.json` así:
  ```json
  {"event": "COMMENT", "body": "<veredicto, pruebas y lecciones>",
   "comments": [{"path": "app/consultas.py", "line": 14, "side": "RIGHT", "body": "**Bloquea.** Qué veo… Por qué importa… Propuesta…"}]}
  ```
  y publícalo con `gh api repos/{owner}/{repo}/pulls/<número>/reviews --method POST --input revision-codigo/comentarios-pr.json`.
