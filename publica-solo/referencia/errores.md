# Errores típicos de GitHub Actions y qué hacer

Dónde ver el resultado: tu repositorio en GitHub → pestaña **Actions** → la ejecución más reciente → el job en rojo → el paso en rojo (ahí está el mensaje).

| Lo que ves | Qué significa | Qué hacer |
|---|---|---|
| El workflow no aparece en Actions | El archivo no está en `.github/workflows/` de la rama que subiste, o la extensión no es `.yml`/`.yaml`. | Revisa la ruta exacta y haz `git push`. |
| `Invalid workflow file … line N` | Error de sintaxis YAML (sangría, tabulador, comillas). | Corrige la línea N; solo espacios para sangrar. Corre de nuevo el validador. |
| `npm ci` falla: `package.json and package-lock.json are not in sync` | El `package-lock.json` está desactualizado. | En tu computadora: `npm install`, y sube el `package-lock.json` nuevo. |
| `ModuleNotFoundError` solo en Actions | La dependencia está instalada en tu PC pero no en `requirements*.txt`. | Agrégala al archivo de dependencias que instala el workflow. |
| Las pruebas pasan en tu PC y fallan en Actions | GitHub usa Linux: distingue mayúsculas en nombres de archivo, no tiene tus variables ni tu `.env`, y puede tener otra versión de Python/Node. | Revisa el nombre exacto de los archivos importados, define las variables de prueba en `env:` (valores falsos), y alinea la versión. |
| `Process completed with exit code 1` | Un comando devolvió error; el motivo está unas líneas antes. | Lee el paso en rojo; reproduce ese comando en tu terminal. |
| `Resource not accessible by integration` | Al token del workflow le faltan permisos. | Añade el permiso mínimo necesario en `permissions:` del job (p. ej. `pages: write`). |
| `Falta el secreto X` (mensaje de la skill) | No creaste el secreto en GitHub. | *Settings → Secrets and variables → Actions → New repository secret*. Nombre **exacto**, valor desde la fuente indicada en el informe. Nunca lo pegues en el chat ni en un archivo. |
| El job de despliegue no corre | Sus condiciones no se cumplen: no es `push` a la rama principal, o las pruebas fallaron (`needs`). | Es lo esperado en pull requests. Mezcla a la rama principal y revisa. |
| Los secretos llegan vacíos en un pull request | GitHub no entrega secretos a pull requests de forks. | Es una protección; el despliegue solo debe correr en `push` a la rama principal. |
| `Get Pages site failed` / `Not Found` en deploy-pages | Pages aún no está activado. | *Settings → Pages → Source: GitHub Actions* y vuelve a correr el workflow. |
| La página de Pages carga sin estilos | Ruta base incorrecta (`/repo/`). | Configura la base del sitio (en Vite: `base: '/nombre-del-repo/'`). |
| `unauthorized` al subir la imagen a ghcr.io | Falta `packages: write` o el nombre tiene mayúsculas. | Añade el permiso y escribe `ghcr.io/usuario/repo` en minúsculas. |
| Una ejecución se canceló sola | `concurrency` canceló una ejecución vieja porque llegó una nueva. | Es lo esperado. |

Para repetir una ejecución sin cambiar nada: Actions → la ejecución → *Re-run all jobs*.
