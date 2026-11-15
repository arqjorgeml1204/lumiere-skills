---
name: publica-con-claude
description: Revisa en español lo que vas a publicar en Instagram antes de subirlo, con scripts que miden en lugar de opinar. Revisa el guion de un reel (gancho, datos, cierre, pedidos), el caption (spanglish, muletillas de IA, primera línea y palabra clave), los mensajes automáticos de WhatsApp (si Meta te los cobraría como publicidad y si traen baja visible), ordena los comentarios para contestarlos y califica tu perfil sobre 100. Úsala cuando digas «revisa mi guion», «revisa este caption», «¿está bien este reel?», «antes de publicar…», «ayúdame a contestar estos comentarios», «califica mi perfil» o «revisa este mensaje de WhatsApp».
---

# Publica con Claude: revisa antes de publicar, en español

Hecha por Lumière Autómata (reel «No publiques con Claude en Instagram sin saber esto»). Es lo que sí funcionó de tres skills famosas de GitHub después de probarlas con texto real en español, más lo que aprendimos midiendo 41 guiones y 29 reels propios.

**La idea en una frase:** las herramientas pensadas en inglés se equivocan en español. Una calificó de «débil» el gancho de nuestro mejor reel, que llegó a 17 veces más gente que los demás, y otra cambió «es crucial» por «es important». Esta skill revisa con reglas hechas para el español y medidas con resultados reales.

## Qué hace que un chat normal no hace
1. **Mide con scripts, no con opinión.** Cada revisión sale de un script que da PASA, FALLA o AVISO, con el número que lo justifica. Si le preguntas dos veces, responde lo mismo.
2. **Está pensada para el español.** Entiende acentos y números dichos con letra («treinta y una»), detecta spanglish y las muletillas de la IA en español.
3. **Nunca reescribe por su cuenta.** Te dice qué falla y te propone el cambio; el texto final lo decides tú.

## Qué puedes revisar (elige lo que necesites)

| Pides | Script o referencia | Qué entrega |
|---|---|---|
| El **guion** de un reel | `scripts/analiza_guion.py` | Revisión de la voz: gancho, datos, cierre, pedidos, bucles y huecos sin terminar, con PASA/FALLA/AVISO |
| El **caption** | `scripts/revisa_caption.py` | Primera línea visible, palabra clave arriba, spanglish, muletillas de IA, rayas, caracteres invisibles, pedidos y hashtags |
| Un **mensaje automático de WhatsApp** | `scripts/revisa_whatsapp.py` + `referencia/plantillas_whatsapp.md` | Si suena a utilidad, a marketing o queda en duda; riesgo de que Meta te lo cobre como publicidad; si trae baja visible (un botón «Ahora no» pospone, no da de baja) |
| Los **comentarios** de un post | `referencia/comentarios_y_perfil.md` §1 | Los comentarios ordenados en 6 grupos y las respuestas listas para copiar |
| Tu **perfil** | `referencia/comentarios_y_perfil.md` §2 | Calificación sobre 100 con 12 puntos y qué cambiar primero |

## Proceso (siempre este orden)

**1. Reunir.** Pide **solo lo que falte**, en un solo mensaje numerado; lo que ya te dieron no se vuelve a preguntar:
1. El texto: el guion o teleprompter (un tramo de voz por línea), el caption, el mensaje de WhatsApp o los comentarios pegados.
2. Para captions: la **palabra clave** de la pieza, como la buscaría alguien que no sabe del tema («base de datos», no «MongoDB Atlas»). En guiones no se pide: el script de guion no la usa.
3. Para guiones: la velocidad de la voz, si no es la normal. El script supone ~3 palabras por segundo (voz ágil y continua). Con voz más lenta se usa `--pps 2.5`.
4. Para WhatsApp: con qué categoría registraste la plantilla en Meta (utilidad o marketing) y el texto de sus botones.

**2. Guardar el texto en un archivo** dentro de una carpeta de trabajo (`revision/`), con el mismo texto que pegó la persona y sin corregir nada todavía: `guion.txt`, `caption.txt` o `mensaje.txt`. En un guion, cada tramo de voz va en su línea y **la primera línea es el gancho** (lo primero que se dice; el título de la portada no va). Si el guion viene en una tabla `.md`, el script lee la columna «Voz»; si un archivo trae varios guiones, se elige uno con `--seccion "<texto del encabezado>"`.

**3. Correr el script que toque:**
```bash
python <carpeta de esta skill>/scripts/analiza_guion.py guion.txt
python <carpeta de esta skill>/scripts/revisa_caption.py caption.txt --clave "base de datos"
python <carpeta de esta skill>/scripts/revisa_whatsapp.py mensaje.txt --categoria utilidad --botones "Sí, agendar|No, gracias"
```
- Opciones útiles: `--resumen` (una línea por guion, para una carpeta), `--json` (salida para otra herramienta) y `--pps 2.5` (voz más lenta).
- Los nombres propios en inglés con mayúscula a media frase (Netflix, The Verge) no cuentan como spanglish. Si un término en minúscula es correcto (el nombre de tu herramienta), pásalo con `--permitidas remotion,github` y vuelve a correr.
- Comentarios y perfil no llevan script: se usa la referencia y se muestra la tabla completa.

**4. Proponer arreglos.** Por cada FALLA:
- el texto exacto que falla;
- por qué importa (una línea);
- **tu propuesta de reescritura**, en español natural, sin muletillas.

Después, los AVISOS en una lista corta. No inventes datos: si un arreglo necesita un número que no tienes («llegó a 17 veces más gente»), pídelo.

**5. Guardar la versión corregida** como `<archivo>_v2.txt` (sin pisar el original) y **volver a correr** el script sobre ella hasta que no quede ninguna FALLA. Entrega esa versión.

## Formato de la respuesta (siempre igual)
1. **Veredicto en una línea**, una de estas tres:
   - «PASA»;
   - «PASA, con N avisos: …» (los avisos no impiden publicar);
   - «FALLA en N puntos: …» (y, si hay, «+ N avisos»).
2. **La salida del script, tal cual** (bloque de código).
3. **Arreglos propuestos**, uno por FALLA, con el antes y el después. Después, los **avisos** en una lista corta, cada uno con su sugerencia. Si el veredicto es PASA sin avisos, este punto dice «Nada que corregir».
4. **Versión final** lista para copiar, solo si hubo arreglos y la persona los aceptó. Si un arreglo cambia el gancho o la idea, pregunta antes de reescribir.
5. **Palabras nuevas**, máximo 5: *hook* = gancho; *caption* = texto del post; *CTA* = la acción que pides al final; *engagement* = interacción; *opt-out* = darse de baja.

## Comentarios y perfil: qué pedir y cómo entregar
- **Comentarios:** pide que pegue los comentarios tal cual (con el @ de cada persona) y que diga cuál fue la palabra del CTA. Entrega:
  - una línea con el conteo por grupo (`84 comentarios · 41 PALABRA, 2 CLIENTE, 3 APORTE, 2 PREGUNTA, 34 APOYO, 2 RUIDO`);
  - un bloque por grupo, en este orden, con la respuesta lista para copiar debajo de cada comentario;
  - en PREGUNTA, la idea de reel que sale de cada una.
- **Perfil:** pide una captura del perfil completo (nombre, bio, enlace, destacadas, primeras 9 publicaciones), cuántas publicaciones fijadas tiene y la fecha de la última publicación. Entrega la tabla de 12 puntos con los puntos ganados, el total sobre 100 y los 3 cambios que más suben la calificación, en orden.

## Lo que aprendimos midiendo (para explicar los arreglos)
- **El primer segundo decide.** En nuestras cuentas, los dos reels que funcionaron pasaron del 41 % de gente que se queda después de 3 segundos; ninguno de los demás pasó de 35 %. Los dos abren con **una escena o comparación que todos conocen**, en una frase corta: «Millones de personas abren Netflix a la misma hora, y no se cae. ¿Cómo lo logran?» y «Antes de construir una casa se hacen planos. Antes de programar, también.»
- **La portada dice la escena, no el término.** «RAG: IA que lee tus documentos» no frena a nadie; «Tu IA leyó el contrato equivocado» sí.
- **Un dato cada 3 tramos.** Un número o una marca conocida sostiene la atención; tres frases seguidas explicando sin datos aburren.
- **Pide una cosa al final.** Cuatro pedidos seguidos («comenta, guarda, comparte, sígueme») se sienten como anuncio.
- **El bucle nombra lo que viene.** «Y la que más se nota, la sientes con los dedos» engancha; «¿Y si…?» suelto no.

## Reglas
- Español claro, frases cortas, tutea.
- Nunca publiques nada ni mandes mensajes: esta skill revisa, la persona publica.
- No inventes métricas ni datos de clientes. Si en un mensaje de WhatsApp hay datos personales, trabaja con `{nombre}` en su lugar.
- Los límites del analizador vienen de cuentas pequeñas de tecnología en español. Si tus métricas dicen otra cosa, mandan tus métricas: dilo y ajusta con `--pps` o en el script.

## Créditos
Ideas tomadas de dos proyectos con licencia MIT, adaptadas al español y reescritas:
- [`instagram-agent-skill`](https://github.com/Jakeschincariol/instagram-agent-skill) (Jake Schincariol): la forma de ordenar los comentarios y la rúbrica de perfil (traducidas y adaptadas), y la idea de puntuar ganchos y tiempos con scripts.
- [`marketingskills`](https://github.com/coreyhaines31/marketingskills) (Corey Haines): el criterio de categorías de plantillas de WhatsApp.
