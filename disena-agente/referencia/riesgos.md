# Niveles de riesgo de cada acción (método fijo)

| Nivel | Tipo de acción | Ejemplos | Regla |
|---|---|---|---|
| **0** | Solo lectura dentro de la carpeta de trabajo | Leer archivos, buscar texto, listar una carpeta | Libre |
| **1** | Escritura reversible y local | Crear un borrador, escribir un informe nuevo, copiar a una carpeta de salida | Libre, con registro en el informe de entrega |
| **2** | Cambia algo existente o sale de la carpeta | Sobrescribir o mover archivos, ejecutar comandos, consultar internet | Solo si el mapa lo exige; la primera vez de cada ejecución, avisa qué va a hacer |
| **3** | Irreversible o hacia terceros | Borrar, enviar correos o mensajes, pagar, publicar, cambiar permisos o configuración | **Siempre** se detiene y pide aprobación humana, mostrando exactamente qué va a hacer |

## Herramientas de Claude Code y su nivel habitual
| Herramienta | Nivel |
|---|---|
| `Read`, `Glob`, `Grep` | 0 |
| `Write` (archivos nuevos en una carpeta de salida) | 1 |
| `Edit`, `Write` sobre archivos existentes | 2 |
| `Bash`, `PowerShell` | 2 (3 si el comando borra, envía o instala) |
| `WebFetch`, `WebSearch` | 2 |
| Conectores que envían o publican (correo, chat, redes, pagos) | 3 |

Un agente cuyo mapa solo tiene pasos de nivel 0–1 no necesita sección de aprobación más allá de «no hace nada de nivel 2–3».
