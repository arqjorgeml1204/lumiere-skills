---
name: revisa-mi-codigo
description: Revisa tus cambios reales de código como lo haría un mentor (code review). Saca el diff de tu rama contra la rama base, de un pull request de GitHub o de una carpeta; corre las pruebas, el linter y el verificador de tipos que tu proyecto ya tiene; aplica un checklist fijo inspirado en la guía pública de Google (diseño, casos borde, pruebas, nombres, seguridad…); escribe comentarios con archivo:línea, nivel, porqué y propuesta, y comprueba con un script que cada cita exista en el cambio antes de entregarte revision-codigo.md. Úsala cuando el usuario diga "revisa mi código", "hazme un code review", "revisa mi pull request", "¿está bien mi cambio?", "revisa mi rama antes de subirla" o "quiero retroalimentación de mi código".
---

# Revisa mi código — una revisión de mentor sobre tus cambios reales, comprobada

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 18: «Code review y mentoría»).

**La idea en una frase:** es como un *editor de libros*: no reescribe tu libro, te señala qué confunde al lector, por qué, y cómo dejarlo mejor. En Google prácticamente todo cambio pasa por una revisión así antes de entrar al código (*Software Engineering at Google*, cap. 9; guía pública en google.github.io/eng-practices/review).

## Qué hace que un chat normal no hace
1. **Trabaja sobre tus cambios reales**, no sobre un pedazo de código pegado: saca el diff de tu rama contra la rama base (incluidos los cambios sin commit y los archivos nuevos), de un pull request con `gh pr diff`, o de una carpeta si no usas git (`scripts/preparar_revision.py`).
2. **Corre lo que tu proyecto ya tiene** (pruebas, linter, verificador de tipos) y anota el **resultado real**; si no hay pruebas o una herramienta no está instalada, lo dice en lugar de suponer.
3. **Método fijo y visible**: siempre el mismo checklist de 10 puntos (`referencia/checklist.md`) y el mismo formato de comentario (`referencia/plantilla-revision.md`), sin importar cómo le preguntes.
4. **Comprueba su propia revisión** con `scripts/verificar_revision.py`: cada `archivo:línea` citado existe y está dentro del cambio (o lo marca como contexto), cada comentario trae nivel, porqué y propuesta, hay al menos un «Bien hecho», el tono es de editor y el veredicto cuadra con lo que encontró y con las pruebas.

## Proceso (siempre este orden)

**1. Reunir el cambio.** Si el usuario no lo dijo, pregunta en una sola línea qué revisar: tu rama actual (lo normal), un pull request (número) o una carpeta. Luego, desde la carpeta de esta skill (o con su ruta):
`python scripts/preparar_revision.py "<carpeta del proyecto>"` (agrega `--base NOMBRE`, `--pr NÚMERO`, `--carpeta` o `--rutas a/,b/` según el caso; si `python` no está en el PATH, usa la ruta completa del intérprete).
El script detecta la rama base (`origin/HEAD`, `main`, `master`), guarda el diff en `revision-codigo/cambio.diff`, lista los archivos tocados con sus líneas y crea `revision-codigo/.gitignore` para que esa carpeta nunca se cuele en un commit.
- **No hay cambios**: dilo y ofrece `--base HEAD~1` para revisar el último commit.
- **Más de 400 líneas**: el script propone cómo partirlo. Muéstrale la propuesta al usuario y revisa por partes con `--rutas` (una revisión por parte: termina y verifica cada una antes de preparar la siguiente, porque `cambio.diff` se reemplaza; renombra la ya verificada a `revision-codigo-parte1.md`), salvo que él pida revisar todo junto; en ese caso dilo en la revisión.
- **Pull request de otra persona**: correr sus pruebas ejecuta su código en tu computadora. Si el PR no está en tu copia local, el script no lo ejecuta; para hacerlo, pide permiso antes de `gh pr checkout <número>`.

**2. Correr lo que el proyecto ya tiene.** El mismo script lo hace en el paso 1 (sin `--sin-ejecutar`): pruebas (pytest, o unittest si pytest no está; npm test; go test; cargo test), compilación de los archivos de Python cambiados, revisores de estilo (ruff, flake8, eslint, `npm run lint`) y de tipos (mypy, tsc). **No instala nada.** El resultado real queda en `revision-codigo/herramientas.json` y la salida completa en `herramientas.log`. Lee el log de lo que falló y di si lo rompe el cambio (la prueba o el código que falla está en el diff) o si parece que ya fallaba antes; no uses `git stash` ni cambies de rama para averiguarlo.

**3. Revisar con el checklist fijo.** Lee `referencia/checklist.md` y recorre los 10 puntos **en orden** sobre el diff completo: primero la vista general (¿la idea tiene sentido?), luego el archivo con más lógica, luego el resto. Lee los archivos completos cuando el diff no baste para entender el contexto. En seguridad (punto 8) revisa siempre las seis señales: secretos en el código, SQL armado con texto del usuario, entradas sin validar, comandos o rutas armados con texto, datos personales en registros, errores que se tragan. Busca activamente casos borde: lista vacía, cero, `None`/`null`, negativos, texto vacío.

**4. Escribir comentarios como mentor** en `revision-codigo/revision-codigo.md` con la plantilla de `referencia/plantilla-revision.md`. Cada comentario: `### [Nivel] archivo:línea`, **Qué veo**, **Por qué importa** y **Propuesta** (concreta, con código corto si ayuda). Niveles: `Bloquea` (se arregla antes de integrar), `Sugerencia` (mejora real; decide quien escribió el código), `Detalle` (pulido menor) y `Bien hecho` (al menos uno, con la línea exacta). Tono de editor: habla del código, no de la persona; explica el porqué; pregunta cuando dudes. No inventes problemas para llenar secciones: si no hay nada que bloquee, escribe «Ninguno.».

**5. Comprobar:** `python scripts/verificar_revision.py "<carpeta del proyecto>/revision-codigo"`. Debe decir `PASA`. Si dice `FALLA`, corrige la revisión (no el verificador) y repite. Lee también los `AVISO`: una línea marcada como **contexto** está bien solo si de verdad querías comentar código que no cambió; si no, corrige el número de línea. El script revisa la **forma y la evidencia**; el **fondo** lo revisas tú: que cada «Bloquea» sea real, que no falte ninguno de los 10 puntos y que las propuestas funcionen.

**6. Entregar** `revision-codigo/revision-codigo.md` (formato fijo de la plantilla): veredicto (Aprobar / Aprobar con cambios / Necesita cambios), resultado real de pruebas y revisores (copiado de `herramientas.json`, sin maquillar), comentarios agrupados por nivel, «Lo que está bien hecho», «Lo que aprendes de este cambio» (2–3 lecciones para quien empieza) y el siguiente paso. En el chat, resume en 5 líneas: veredicto, cuántos comentarios por nivel, lo que bloquea, el resultado de las pruebas y la salida final del verificador (PASA). **No cambies el código del usuario** salvo que te lo pida después de leer la revisión.

**Opcional — publicar en el pull request.** Solo si el usuario lo pide y tiene `gh`. Primero muéstrale exactamente qué se va a publicar y espera un «sí» explícito; publica siempre como comentario (nunca apruebes ni pidas cambios en su nombre). Comandos en `referencia/plantilla-revision.md`.

## Palabras nuevas (en español la primera vez)
Code review · revisión de código · Pull request · solicitud para integrar cambios · Feedback · retroalimentación · Mentoring · mentoría · Diff · diferencias entre dos versiones · Linter · revisor automático de estilo · Edge case · caso borde · Nit · detalle menor · LGTM (*looks good to me*) · «se ve bien», la forma corta de aprobar.

## Reglas
- Español claro, frases cortas, tutea. Explica cada término técnico la primera vez.
- **Evidencia antes que opinión**: cada comentario cita una línea real del cambio; nunca digas «las pruebas pasan» si no se ejecutaron (escribe «NO EJECUTADO» y el motivo).
- **No instales ni cambies nada** en el proyecto para revisarlo: ni dependencias, ni código, ni ramas. La única carpeta que escribes es `revision-codigo/`.
- **Nunca copies secretos** en la revisión: si encuentras uno, cita el archivo y la línea, escribe `<oculto>` en lugar del valor y recomienda revocarlo (si ya se subió a git, queda en el historial).
- Nada hacia otras personas sin un «sí» explícito: publicar comentarios, aprobar un PR o hacer checkout del código de alguien más.
- Tono de editor, no de juez: el verificador rechaza frases duras («esto está mal», «obvio»…) y la revisión siempre incluye lo que está bien hecho.
