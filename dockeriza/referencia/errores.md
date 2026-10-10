# Errores típicos al usar Docker (sobre todo en Windows) y qué hacer

| Lo que ves | Qué significa | Qué hacer |
|---|---|---|
| `'docker' no se reconoce como un comando` | Docker no está instalado (o la terminal se abrió antes de instalarlo). | Instala **Docker Desktop** (docker.com, tú lo descargas y lo instalas), reinicia la terminal. |
| `error during connect … the system cannot find the file specified` / `Cannot connect to the Docker daemon` | Docker está instalado pero **apagado**. | Abre Docker Desktop y espera a que diga «Engine running». |
| Docker Desktop pide WSL 2 / «virtualization not enabled» | Windows necesita la función de virtualización. | Activa «Virtualización» en la BIOS y ejecuta `wsl --install` en PowerShell como administrador (cambia el sistema: hazlo tú, no Claude). |
| `port is already allocated` / `address already in use` | Otro programa usa ese puerto. | Cambia la parte de **afuera** del puerto: `"8001:8000"` (en el compose, variable `PUERTO=8001`). |
| El contenedor arranca y se apaga solo (`Exited (1)`) | La app falló al iniciar. | `docker logs NOMBRE` muestra la causa (casi siempre falta una variable de entorno o un archivo). |
| Abres `http://localhost:8000` y no carga, pero el contenedor está «Up» | La app escucha en `127.0.0.1` dentro del contenedor. | Arráncala con `--host 0.0.0.0` (uvicorn) o `host: '0.0.0.0'` (Node). |
| `COPY failed: file not found in build context` | El archivo no existe, o lo excluye `.dockerignore`. | Revisa el nombre y quita la regla que lo excluye. |
| `ModuleNotFoundError` / `Cannot find module` solo dentro del contenedor | Falta una dependencia en `requirements.txt` / `package.json` (en tu PC la tenías instalada global). | Agrégala al archivo de dependencias y reconstruye (`docker compose build`). |
| `PermissionError` / `EACCES` al escribir un archivo o la base | Corres sin privilegios y la carpeta es de root. | Crea la carpeta en el Dockerfile y dale dueño: `mkdir /data && chown appuser /data`. |
| `exec ./script.sh: no such file or directory` o `bad interpreter` | El script se guardó con finales de línea de Windows (CRLF). | Guárdalo con finales `LF` (en VS Code: barra inferior → CRLF → LF). |
| Cambié el código y no se nota | La imagen vieja sigue en uso. | `docker compose up -d --build`. |
| La base de datos «se borró» al reiniciar | No hay volumen: los datos vivían dentro del contenedor. | Declara un `volumes:` con nombre (como en la plantilla). Ojo: `docker compose down -v` **sí** borra los volúmenes. |
| `no matching manifest for linux/arm64` (Mac con chip M) | La imagen no existe para tu procesador. | Añade `platform: linux/amd64` al servicio o usa otra imagen. |
| `env file .env not found` | El compose pide un `.env` que aún no existe. | `copy .env.example .env` (PowerShell) y rellena los valores. |

Comandos de diario:
```
docker compose up -d --build     # construir y arrancar en segundo plano
docker compose ps                # ver qué está corriendo y si está «healthy»
docker compose logs -f           # ver lo que dice la app
docker compose down              # apagar (conserva los datos)
```
