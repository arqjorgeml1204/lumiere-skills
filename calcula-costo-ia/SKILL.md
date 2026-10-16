---
name: calcula-costo-ia
description: Mide cuánto cuesta y cuánto tarda la IA dentro de la app del usuario (Claude, OpenAI o Gemini) a partir de su código y sus registros de uso, simula cinco optimizaciones (caché de prompts, modelo más barato para tareas simples, recortar el prompt, streaming y caché de respuestas) con un script y entrega un informe antes/después con los 3 cambios que más ahorran y el archivo y la línea donde aplicarlos. Úsala cuando el usuario diga que su app de IA le sale cara o lenta, quiera saber cuánto le va a costar al mes, pregunte si le conviene la caché de prompts o un modelo más barato, o quiera optimizar latencia o tokens.
---

# Calcula el costo de tu IA — mide, simula y decide con números

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 15: «Velocidad y costo de una app de IA»).

## Qué hace que un chat normal no hace
1. **Trabaja con lo tuyo**: busca en tu código dónde llamas a la IA (archivo y línea), qué modelo usa cada función, cuánto mide tu prompt de sistema y si ya usas streaming o caché; luego lee tus registros de uso reales (CSV o JSONL). Si no tienes registros, usa tus volúmenes estimados y te deja listo cómo empezar a registrar.
2. **Mide antes de optimizar**: `scripts/costo_ia.py` calcula el costo por llamada, por día y al mes, por modelo y por función, y la latencia p50/p95, con los precios oficiales fechados de `referencia/precios.json`. Con tus propios tiempos calcula de dónde sale la espera (entrada contra salida).
3. **Simula con un método fijo**: las mismas cinco optimizaciones, con los mismos supuestos escritos en el informe, sin importar cómo preguntes. Entrega `informe-costo-ia.md` y `uso_normalizado.csv`, generados y ejecutados aquí antes de dártelos. **No toca tu código sin tu permiso.**

Dato de referencia: Anthropic reporta que la caché de prompts reduce hasta 90 % el costo y hasta 85 % la latencia en prompts largos (https://claude.com/blog/prompt-caching); Notion la usa en Notion AI. El informe te dice cuánto de eso aplica **a tu app**: a veces nada, porque el prompt es muy corto o las llamadas están muy separadas.

## Proceso (siempre este orden)

**1. Reunir.** Ejecuta primero:
`python <carpeta de esta skill>/scripts/costo_ia.py buscar <carpeta del proyecto>`
Te da las llamadas a la IA (archivo:línea, modelo, ¿streaming?, ¿caché?), los prompts largos con su tamaño aproximado y los archivos de registro que encontró. Abre cada llamada y llena esta tabla:
`función | archivo:línea de la llamada | archivo:línea del prompt | modelo | tokens fijos (sistema + herramientas + documentos fijos) | ¿lo variable va antes que lo fijo? | ¿streaming? | ¿tarea simple?`
- «Tarea simple» = clasificar, etiquetar, extraer campos, sí/no, respuestas de una línea. Redactar, razonar o hablar con clientes no es simple.
- Marca si algo variable (fecha, nombre, pregunta) va **antes** de la parte fija: eso rompe la caché.
- Pide solo lo que falte, en un mensaje numerado: (1) la ruta de los registros de uso, o (2) si no hay, llamadas al día por función y tamaños típicos de entrada y salida. Con estimados, escribe `estimado.csv` (formato en `referencia/formato_uso.md`, «Sin registros») y marca el informe como **estimado, no medido**.

**2. Precios.** Revisa la fecha de `referencia/precios.json`. Si tiene más de 60 días o falta un modelo del usuario, abre la URL «fuente» del proveedor, confirma los precios y actualiza el archivo con la fecha de hoy. Nunca pongas un precio que no confirmaste en la página oficial.

**3. Medir.** Ejecuta:
`python <carpeta de esta skill>/scripts/costo_ia.py medir <registro> --salida costo-ia --fijos f1=N,f2=M --simples f3 --ubicaciones costo-ia/ubicaciones.json`
- `--fijos`: tokens de la parte fija por función, de tu tabla del paso 1. Sin este dato el script lo deduce de la caché o de la entrada más pequeña y lo marca como estimado.
- `--simples`: las funciones que marcaste como simples. Sin este dato usa una heurística (salida promedio de 100 tokens o menos) y lo dice.
- `--ubicaciones`: JSON `{"función": {"llamada": "app/x.py:35", "prompt": "app/prompts.py:3"}}` con tu tabla. Así el top 3 dice dónde cambiar.
- `--ya-streaming f1,f2` si alguna función ya transmite la respuesta.
- Si el script reporta filas ignoradas o columnas no reconocidas, revísalas con `referencia/formato_uso.md` y vuelve a correrlo.

**4. Revisar supuestos.** Lee la sección 6 del informe. El recorte del prompt (25 % por defecto) es un supuesto: léelo de verdad, identifica qué sobra (instrucciones repetidas, ejemplos de más, texto que nunca aplica) y ajusta `recorte_prompt` en un JSON de supuestos (`--supuestos`). Los demás supuestos y por qué existen están en `referencia/optimizaciones.md`. Si cambias alguno, vuelve a correr el paso 3.

**5. Verificar a mano.** Rehaz con calculadora el «Cálculo de ejemplo» de la sección 7 (tokens × precio ÷ 1,000,000) y confirma que el total del archivo ÷ días × 30 da el costo al mes. Si algo no cuadra, no entregues: busca la causa.

**6. Entregar.** Carpeta `costo-ia/` con `informe-costo-ia.md`, `uso_normalizado.csv` y `ubicaciones.json`. En el chat: costo al mes hoy, los 3 cambios con su ahorro y su riesgo, la espera que se ahorra con streaming y qué es medido contra qué es supuesto. Ofrece aplicar **un** cambio, el primero, solo si el usuario lo aprueba; después pide un día de registros nuevos y vuelve a medir para comprobar el ahorro real. Si la app no registra el uso, ofrece agregar el registro de `referencia/formato_uso.md` («Empieza a registrar»), también con permiso.

## Palabras nuevas (en español la primera vez)
Token · pedazo de texto que cobra la IA (unas ¾ de palabra) · Latency · latencia (lo que tarda) · p50 / p95 · percentil 50 y 95 · Prompt caching · caché de prompts (guardar la parte fija) · Cache hit · acierto de caché · Streaming · respuesta en flujo · TTFT (time to first token) · tiempo al primer token · Routing · enrutar (mandar cada tarea al modelo adecuado) · Batch · procesamiento por lotes.

## Reglas
- Español claro; tutea y explica cada término la primera vez.
- Medir antes de optimizar: nada de recomendaciones sin el informe del script.
- Los precios cambian: cita siempre la fecha y la URL de `precios.json`, y verifícalos si tienen más de 60 días.
- Di siempre qué número es **medido** y cuál es **supuesto**. No prometas el ahorro: es una estimación hasta que se mida con registros nuevos.
- Streaming no baja el costo ni el tiempo total: baja la espera que siente el usuario. Dilo así.
- Cambiar a un modelo más barato puede bajar la calidad: antes de aplicarlo, pruébalo con casos reales (skill `mejora-prompt`).
- Nunca pidas, muestres ni guardes llaves de API. Los registros no deben guardar textos personales: usa un hash de la pregunta.
- No cambies el código del usuario sin su permiso explícito, cambio por cambio.
