---
name: explica-api
description: Explica en español sencillo qué pasó con una petición a una API. Úsala cuando el usuario pegue una respuesta, un error, un código de estado (200, 401, 404, 500…), un mensaje de consola o un comando curl y quiera saber qué significa, por qué falló y cómo arreglarlo. Pensada para personas que están empezando.
---

# Explica API — diagnóstico en español para principiantes

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 1: «¿Qué es una API?»).

## Cuándo usarla
El usuario pega cualquiera de estas cosas y quiere entenderla:
- Una respuesta de API (JSON, HTML, texto) con o sin su código de estado.
- Un error de consola, de Postman, Hoppscotch, curl, fetch, axios o requests.
- Solo un número de código («me sale 403»).

## Cómo responder (este formato, en este orden; ver «Cómo adaptar el formato»)

**1. Veredicto en una línea.** Empieza con un ícono y una frase: `✅ Funcionó`, `⚠️ Funcionó a medias`, `❌ Falló por tu lado (cliente)` o `🔥 Falló por el lado del servidor`. Los códigos 1xx/2xx/3xx no son errores; 4xx es del cliente; 5xx es del servidor. Detalle de cada código en `referencia/codigos.md`: léelo antes de diagnosticar cualquier código que no sea 200.

**2. Qué pasó, con la analogía del restaurante.** Dos o tres frases. Tú eres el cliente, la API es el mesero y el servidor es la cocina. Ejemplo para 404: «Pediste un platillo que no está en el menú: la dirección a la que llamaste no existe».

**3. Causa más probable.** Lista de 1 a 3 causas, de la más a la menos probable, basadas en lo que pegó el usuario (cita el dato que te hace pensarlo: un encabezado, una palabra del mensaje, la URL). Nunca inventes datos que no estén en lo pegado; si falta información, dilo.

**4. Cómo arreglarlo.** Pasos numerados, concretos y cortos. Si el arreglo implica cambiar la petición, muestra la petición corregida en el mismo formato que usó el usuario (curl, fetch, Python). No pongas claves reales: usa `TU_CLAVE`.

**5. Lo que dice la respuesta.** Si hay JSON, tradúcelo campo por campo en una tabla `campo | qué significa` (máximo 8 filas; si hay más, las más importantes).

**6. Palabras nuevas.** Glosario inglés → español solo de los términos que aparecieron en esta respuesta (por ejemplo `Unauthorized · no autorizado`, `Header · encabezado`, `Token · llave de acceso temporal`). Máximo 5.

## Cómo adaptar el formato
- **Respuesta 2xx sin problemas:** solo las partes 1, 2, 5 y 6 (sin causa ni arreglo), numeradas 1 a 4. Texto breve: unas 12 líneas sin contar la tabla, y la tabla con los 5 campos más útiles.
- **Glosario:** si no aparece ningún término nuevo de verdad, omite la parte 6.
- **Sin cuerpo** (vacío, cortado o `Content-Length: 0`): en la parte 5 dilo en una frase y traduce solo los 3–4 encabezados que ayudan al diagnóstico (`Content-Type`, `Retry-After`, `Location`, límites de peticiones); omite el resto.
- **Falta información para la causa:** la parte 3 da las causas generales del código y termina con una sola pregunta por lo que falta (URL, método o cuerpo). No inventes la URL.
- **⚠️ «Funcionó a medias»** se usa cuando el código es 2xx pero el cuerpo trae un error, viene vacío cuando debía traer datos, o está incompleto (paginado, recortado). Una respuesta servida desde caché (`Age`, `cf-cache-status: HIT`) sigue siendo ✅; solo menciónalo si importa.

## Reglas
- Español claro, sin jerga sin explicar. Frases cortas. Tutea.
- Si el usuario pegó una clave, token o contraseña real, avísale al inicio que la cambie (rótala), porque ya quedó expuesta, y no la repitas.
- Si el código y el cuerpo se contradicen (por ejemplo, código 200 con `"error"` dentro del JSON), dilo: muchas APIs mal hechas responden 200 aunque fallen.
- Si no hay código ni mensaje suficiente, pide exactamente lo que falta (la URL, el método, el código o el cuerpo), en una sola pregunta.
- No escribas más de lo necesario.
