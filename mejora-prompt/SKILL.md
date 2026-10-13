---
name: mejora-prompt
description: Toma un prompt que el usuario ya usa (para ChatGPT, Claude, Gemini o su propia app), lo prueba con sus casos reales, lo reescribe con las cuatro piezas de un buen prompt, lo vuelve a probar con los mismos casos más un caso trampa y entrega el prompt final con un informe antes/después generado por un script. Úsala cuando el usuario diga que la IA le responde mal, que quiere mejorar un prompt, que la IA inventa datos o no respeta un formato.
---

# Mejora prompt — prueba tu prompt, mejóralo y demuestra la diferencia

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 10: «Prompts: cómo hablarle a una IA»).

## Qué hace que un chat normal no hace
1. **Trabaja con tu prompt y tus casos reales**, no con un ejemplo inventado: el texto que ya usas y 3–5 entradas de verdad (correos, comentarios, documentos, preguntas de clientes).
2. **Prueba antes de cambiar nada**: corre tu prompt tal cual con cada caso y califica las salidas con criterios fijos. Así se ve qué falla, no se adivina.
3. **Entrega archivos verificables**: el prompt final, los casos, las salidas de las dos versiones y un informe antes/después que produce `scripts/comparar.py` (no se escribe a mano).

## Proceso (siempre este orden)

**1. Reunir.** Pide solo lo que falte, en un mensaje numerado:
1. El prompt actual, completo (y el «mensaje de sistema» si tu app lo usa).
2. Para qué lo usas y quién lee la respuesta.
3. De 3 a 5 casos reales de entrada. Si el usuario tiene archivos, búscalos antes de preguntar.
4. Cómo es una respuesta buena: formato, largo, tono y qué nunca debe hacer.
Nunca pidas ni repitas contraseñas, llaves de API ni datos personales de terceros: si aparecen en un caso, reemplázalos por `[DATO]` y avísale.

**2. Diagnóstico** con el checklist fijo de `referencia/checklist.md` (8 criterios, 0–2 puntos cada uno). Muestra la tabla con la evidencia de cada puntuación, citando el texto del prompt.

**3. Probar el original.** Ejecuta el prompt con cada caso **en un contexto limpio**, sin lo que se habló en esta conversación:
- En Claude Code: lanza un subagente por caso con un encargo que contenga **solo** el prompt y la entrada, y que termine con «Devuelve únicamente el texto de la respuesta, sin comentarios». Guarda la salida tal cual en `prompt-mejorado/salidas/<caso>_original.txt`. Si un subagente no devuelve texto, relánzalo una vez; si vuelve a fallar, márcalo en el informe. El subagente hereda reglas del entorno, así que la prueba es «casi limpia»: anota en el informe qué modelo usaste y que el del usuario puede responder distinto.
- Si no hay subagentes: responde cada caso como si fuera la primera vez que ves el prompt, y márcalo en el informe como «prueba en el mismo chat (menos estricta)».
- Si el usuario usa otra IA (ChatGPT, Gemini o la API de su app), dale los casos listos para pegar y pídele las salidas; si no puede, sigue con la prueba local y dilo en el informe.

**4. Calificar** cada salida con una rúbrica escrita **antes** de ver las salidas: un criterio por cada regla del usuario (paso 1.4: largo, tono, lo que debe incluir, lo que nunca debe hacer) más los automáticos `formato` y `no_inventa`. Cada criterio es `true` o `false` con una razón de una línea. Si un criterio es subjetivo («tono cálido»), escribe en la rúbrica qué cuenta como sí y qué como no.

**5. Reescribir** con la plantilla de `referencia/plantilla.md`: rol, tarea, contexto, formato de salida, 1–3 ejemplos (*few-shot*) tomados de los casos, datos entre delimitadores y permiso explícito para decir «no lo sé». Conserva todo lo que el usuario pidió; no agregues requisitos que no dio. Si tuviste que decidir algo que el usuario no dijo (cómo tratar una entrada ambigua), escríbelo en el informe como **interpretación** para que lo confirme.

**6. Probar el nuevo** con los mismos casos **más un caso trampa** escrito por ti: una entrada a la que le falta el dato clave. Corre el caso trampa **también con el prompt original** (el informe compara los dos en todos los casos). Pasa si responde que no lo sabe o pide el dato, en lugar de inventarlo.

**7. Comparar con el script.** Escribe `resultados.json` (formato en `referencia/plantilla.md`) y ejecuta:
`python <carpeta de esta skill>/scripts/comparar.py prompt-mejorado/resultados.json prompt-mejorado/informe.md` (usa la ruta completa del script). Sale con código 0 si el prompt final mejora y con 1 si no.
El script valida el JSON, comprueba el formato de las salidas que deban ser JSON y genera la tabla antes/después con el porcentaje de criterios cumplidos. **Si el prompt nuevo no supera al original, vuelve al paso 5** (máximo dos vueltas) y dilo en el informe.

**8. Entregar.** Carpeta `prompt-mejorado/` con `prompt_original.md`, `prompt_final.md` (listo para copiar), `casos.md`, `salidas/`, `resultados.json` e `informe.md` (con el modelo usado en las pruebas y tus interpretaciones). En el chat: el prompt final, el resumen del informe (aciertos antes → después) y qué cambiar si su caso de uso crece. Si no hay acceso a archivos, entrega lo mismo como bloques para copiar y el script para que lo corra en su computadora.

## Palabras nuevas (en español la primera vez)
Prompt · instrucción · System prompt · instrucciones del sistema · Few-shot · dar ejemplos · Hallucination · alucinación · Output format · formato de salida · Delimiter · delimitador.

## Reglas
- Español claro; tutea y explica cada término la primera vez.
- No prometas que un prompt elimina las alucinaciones: las reduce. Lo que se afirma sale de las pruebas.
- No inventes casos «reales»: si el usuario no da casos, escribe ejemplos, márcalos como **casos de ejemplo** y pídele los suyos para una segunda vuelta.
- Si el problema no es el prompt (falta un dato que la IA no puede saber, el modelo no tiene acceso a sus archivos), dilo y recomienda la solución: darle los datos, RAG (día 11) o una herramienta (día 13).
