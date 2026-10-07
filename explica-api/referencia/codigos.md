# Códigos de estado HTTP — guía para principiantes

Formato: código · nombre en inglés · en español · analogía del restaurante · causas típicas · qué hacer.

## 2xx — salió bien
- **200 · OK · correcto.** Te trajeron tu platillo. Revisa igual el cuerpo: algunas APIs responden 200 con un error adentro.
- **201 · Created · creado.** Tu pedido quedó registrado (se creó algo nuevo, típico tras POST).
- **204 · No Content · sin contenido.** Lo hicieron, pero no hay nada que traerte (típico tras DELETE).

## 3xx — te mandan a otro lado
- **301 / 308 · Moved Permanently · se mudó para siempre.** El restaurante cambió de dirección. Usa la nueva URL del encabezado `Location`.
- **302 / 307 · Found / Temporary Redirect · redirección temporal.** Por ahora atienden en otra sucursal. Sigue el `Location`.
- **304 · Not Modified · sin cambios.** Ya tienes la versión más reciente guardada (caché).

## 4xx — el problema está en tu pedido
- **400 · Bad Request · petición mal hecha.** Pediste algo que el mesero no entiende. Causas: JSON mal escrito (comas, comillas), campo obligatorio faltante, tipo de dato equivocado. Qué hacer: valida el JSON y compara con la documentación.
- **401 · Unauthorized · no autenticado.** No dijiste quién eres. Causas: falta la llave (`Authorization`), llave vencida o mal copiada (espacios). Qué hacer: revisa el encabezado y el formato exacto (`Bearer TU_CLAVE`).
- **403 · Forbidden · prohibido.** Sabemos quién eres, pero no puedes pedir eso. Causas: tu llave no tiene ese permiso, plan gratuito limitado, IP bloqueada. Qué hacer: revisa los permisos o el plan de tu cuenta.
- **404 · Not Found · no encontrado.** Ese platillo no está en el menú. Causas: URL mal escrita, versión equivocada (`/v1` vs `/v2`), el recurso fue borrado, ID inexistente. Qué hacer: copia la URL exacta de la documentación.
- **405 · Method Not Allowed · método no permitido.** Pediste bien el platillo pero de la forma equivocada (GET en lugar de POST). Qué hacer: cambia el verbo.
- **408 · Request Timeout · se tardó tu pedido.** Tardaste demasiado en terminar de pedir. Qué hacer: reintenta; revisa tu conexión.
- **409 · Conflict · conflicto.** Choca con algo que ya existe (usuario duplicado, versión desactualizada). Qué hacer: consulta el estado actual y vuelve a intentar.
- **415 · Unsupported Media Type · formato no aceptado.** Mandaste el pedido en un idioma que no leen. Qué hacer: agrega `Content-Type: application/json`.
- **422 · Unprocessable Content · datos inválidos.** Se entiende el pedido pero los datos no cumplen las reglas (correo inválido, número negativo). Qué hacer: lee el detalle del error, suele decir qué campo.
- **429 · Too Many Requests · demasiadas peticiones.** Pediste demasiado rápido. Qué hacer: espera (mira `Retry-After`) y reduce la frecuencia.

## 5xx — el problema está en el servidor
- **500 · Internal Server Error · error interno.** Se descompuso algo en la cocina. No es tu culpa en la mayoría de los casos. Qué hacer: reintenta más tarde; si la API es tuya, revisa los registros (logs) del servidor.
- **502 · Bad Gateway · puerta de enlace con problemas.** El mesero no pudo hablar con la cocina. Qué hacer: reintenta; suele ser temporal.
- **503 · Service Unavailable · servicio no disponible.** Cerrado por mantenimiento o saturado. Qué hacer: espera y reintenta.
- **504 · Gateway Timeout · tiempo de espera agotado.** La cocina tardó demasiado. Qué hacer: reintenta; si la API es tuya, la consulta es muy lenta.

## Errores sin código (la petición ni siquiera llegó)
- **CORS / «blocked by CORS policy».** El navegador no deja que una página hable con esa API. Es configuración del servidor, no de tu código; desde el servidor o con curl sí funciona.
- **ENOTFOUND / «Could not resolve host».** La dirección no existe o no hay internet. Revisa el dominio.
- **ECONNREFUSED.** Llegaste a la dirección pero nadie atiende (el servidor está apagado o en otro puerto).
- **certificate / SSL.** Problema con el certificado de seguridad del sitio: no lo ignores en producción.
