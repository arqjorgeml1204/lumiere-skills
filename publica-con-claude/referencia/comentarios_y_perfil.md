# Comentarios por grupos y rúbrica de perfil

Traducido y adaptado de `instagram-agent-skill` (skills `ig-reply` e `ig-profile`, archivo `rubric.json`).
Copyright (c) Jake Schincariol, licencia MIT: https://github.com/Jakeschincariol/instagram-agent-skill

## 1. Comentarios: primero se ordenan, luego se contestan

Nada de envíos masivos: solo se escribe por DM a quien comentó.

Cuando la persona pegue los comentarios de un post, se ordenan en 6 grupos. Se dice cuántos hay en cada uno y se contesta en este orden:

| Grupo | Qué es | Qué recibe |
|---|---|---|
| **PALABRA** | Comentó la palabra del CTA | Lo prometido por DM (el mensaje de la ficha). En público, una línea distinta para cada uno, nunca la misma copiada. |
| **CLIENTE** | Describe un problema que resolvemos | Respuesta completa en público y, al final, una frase que ofrece ayuda, sin vender. Se le avisa a la persona. |
| **APORTE** | Da un dato, no está de acuerdo o amplía | La respuesta más larga del hilo. Primero se le da la razón en lo que sí la tiene, con sus palabras. |
| **PREGUNTA** | Una duda que tendrían muchos | Se contesta **y se marca como idea de reel**: Instagram permite responder un comentario con un reel (sale como sticker y le llega aviso a quien preguntó). Va a la cola de ideas con el comentario literal como gancho (fórmula «pregunta textual»). |
| **APOYO** | «🔥», «buenísimo», una etiqueta | Un like y de 3 a 8 palabras como mucho. |
| **RUIDO** | Spam, venta, mala fe | Nada. Si es abusivo, se oculta. Contestar le da alcance. |

**Cómo se contesta:**
- Se responde lo que preguntó, ahí mismo; no se le manda al DM para darle algo que cabía en la respuesta.
- Su nombre una vez, al inicio, sin signos de admiración.
- El largo de la respuesta se parece al del comentario.
- A un crítico: se le reconoce lo cierto y se sostiene el punto, una sola vez. Nunca se borra.
- Las respuestas pasan por `scripts/revisa_caption.py` (sin spanglish ni muletillas) y las publica la persona: nada sale sin su sí.

**Salida:** un bloque por grupo, listo para copiar, con el conteo arriba.

## 2. Rúbrica de perfil (100 puntos)

Se corre cuando la persona lo pida o una vez al mes. Se califica sin regalar puntos (un primer perfil suele quedar entre 30 y 49), se reescribe lo que perdió puntos en orden de mayor a menor.

| Punto | Pts | Puntuación completa | Falla típica |
|---|---|---|---|
| Campo «Nombre» | 12 | Nombre + lo que hace, con palabras que se buscan (Instagram indexa este campo, no la bio) | Solo el nombre, o el nombre con un emoji |
| 1.ª línea de la bio | 12 | Para quién es y qué cambia para esa persona, con sus palabras | «Emprendedor · café · perros» |
| Resto de la bio | 8 | Una prueba o una oferta concreta, en frases | Palabras clave sueltas o espacio vacío |
| 3 fijados | 10 | Tres trabajos distintos: la mejor prueba, la oferta más clara y la mejor presentación | Nada fijado |
| Enlace | 8 | Un destino que cumple lo que la bio promete; más de 2 enlaces es un menú | Árbol de 11 enlaces, o ninguno |
| Destacadas | 8 | De 4 a 6, con el nombre de las preguntas reales (Cómo funciona, Resultados, Guías…) y portadas iguales | «Random», o 14 sin orden |
| Cuadrícula | 8 | Las 9 primeras portadas se leen en miniatura y dicen de qué es la cuenta | Caras a media palabra sin texto |
| Foto | 6 | La cara llena ~60 % del círculo; los ojos se ven | Cuerpo entero, o un logo en una marca personal |
| @usuario | 6 | Se lee, se dice en voz alta y es el mismo en todas las redes | Guiones bajos y números en lugar de letras |
| Categoría y contacto | 6 | Cuenta profesional, categoría correcta y botones que funcionan | Cuenta personal |
| Actividad | 10 | Publicó en los últimos 7 días y contestó la última pieza | 5 semanas sin publicar |
| Historias | 6 | Hay historia hoy, o casi todos los días | Nunca hay anillo |

Anota la fecha y los puntos: vuelve a calificar en un mes y compáralo con los seguidores ganados.
