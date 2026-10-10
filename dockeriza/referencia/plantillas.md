# Plantillas de partida

Adáptalas al proyecto real (puerto, comando de arranque, archivos). Cada decisión tiene su razón; si la cambias, anótalo en el informe.

Reglas comunes a todas:
- **Imagen base con versión fija** (`python:3.12-slim`, nunca `:latest`). Usa la versión que pide el proyecto (`.python-version`, `engines` de `package.json`, `.nvmrc`); si no dice, elige una versión estable vigente y márcala como **supuesto**.
- **Dependencias primero, código después**: copia solo `requirements.txt` / `package*.json`, instala, y luego copia el resto. Así Docker reutiliza la caché y reconstruir tarda segundos.
- **Usuario sin privilegios** (`USER`): si alguien vulnera la app, no es administrador del contenedor.
- **Cero secretos** en el Dockerfile, el compose y la imagen. Se pasan al arrancar (`env_file`, `${VARIABLE}` o secretos del servicio de alojamiento).
- **Escuchar en `0.0.0.0`**, no en `127.0.0.1`: dentro del contenedor `127.0.0.1` es «solo yo mismo» y nadie de afuera podría entrar.
- **HEALTHCHECK** con la ruta de salud de la app (si no existe, crea una `/salud` mínima y avísalo; o usa `/`).

## Python (FastAPI, Flask, Django con ASGI/WSGI)

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 1) Dependencias (esta capa se reutiliza mientras requirements.txt no cambie)
COPY requirements.txt .
RUN pip install -r requirements.txt

# 2) Usuario sin privilegios y carpeta de datos que pueda escribir
RUN useradd --create-home --uid 10001 appuser \
    && mkdir /data && chown appuser:appuser /data

# 3) Código
COPY --chown=appuser:appuser . .

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/salud', timeout=2)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Notas: si el proyecto mezcla dependencias de producción y de pruebas en un solo `requirements.txt`, sepáralas (`requirements-dev.txt`) y avísalo: la imagen de producción no necesita `pytest`. Django: `CMD ["gunicorn", "proyecto.wsgi:application", "--bind", "0.0.0.0:8000"]` y `gunicorn` en requirements. Si hay dependencias que compilan (psycopg2, cryptography antiguas), usa el paquete binario (`psycopg2-binary`, `psycopg[binary]`) en vez de añadir compiladores.

## Node (Express, Fastify, NestJS, Next.js en modo servidor)

```dockerfile
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --chown=node:node . .

USER node
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD node -e "fetch('http://localhost:3000/salud').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
```
Notas: `npm ci` exige `package-lock.json` (si no existe, avísalo y usa `npm install --omit=dev`). Si el proyecto necesita **compilar** (TypeScript, Next.js, Vite), usa dos etapas: una `AS build` con `npm ci` + `npm run build`, y una final que copia solo `dist/` (o `.next/`) y las dependencias de producción. El comando de arranque sale de `scripts.start` o `main` del `package.json`: no lo inventes.

## Sitio estático (HTML/CSS/JS ya hecho, o `dist/` de Vite/React)

```dockerfile
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY dist/ /usr/share/nginx/html/
EXPOSE 8080
HEALTHCHECK CMD wget -qO- http://localhost:8080/ >/dev/null || exit 1
```
Esa imagen ya corre sin privilegios y escucha en el 8080. Si el sitio se compila, usa dos etapas (`node` para construir, `nginx` para servir).

## `.dockerignore`

Lo que no está aquí **entra a la imagen**. Mínimo:
```
.git
.gitignore
.env
.env.*
!.env.example
Dockerfile
docker-compose*.yml
.dockerignore
*.md
# Python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
tests/
# Node
node_modules/
npm-debug.log
coverage/
# Editor / sistema
.vscode/
.idea/
.DS_Store
```
Ajusta por lenguaje: quita lo de Python en un proyecto Node y viceversa. Si el Dockerfile necesita un archivo que `*.md` o `tests/` excluyen, quita esa línea. Excluir `tests/` es opcional: hazlo si las pruebas no corren dentro de la imagen.

## `docker-compose.yml` (la app sola)

```yaml
services:
  app:
    build: .
    image: mi-proyecto:dev
    ports:
      - "${PUERTO:-8000}:8000"        # afuera:adentro; PUERTO sale de tu .env
    env_file:
      - path: .env                    # tus variables reales (NO se sube a Git)
        required: false               # que arranque aunque aún no lo tengas
    environment:
      DB_PATH: /data/app.db           # variables no secretas pueden ir aquí
    volumes:
      - datos:/data                   # lo que la app guarda sobrevive al reiniciar
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/salud', timeout=2)"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

volumes:
  datos:
```
Reglas: nada de `version:` (obsoleto); ninguna contraseña escrita; `env_file` con `required: false` necesita Docker Compose 2.24 o más nuevo (si el usuario tiene uno anterior, quita `required` y que cree el `.env` copiando `.env.example` antes de arrancar).

## Compose con base de datos (cuando el proyecto la usa)

Añade el servicio y haz que la app espere a que esté **sana**, no solo «encendida»:
```yaml
services:
  app:
    # ... como arriba ...
    environment:
      DATABASE_URL: postgresql://${DB_USUARIO:-app}:${DB_CLAVE}@db:5432/${DB_NOMBRE:-app}
    depends_on:
      db:
        condition: service_healthy
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USUARIO:-app}
      POSTGRES_PASSWORD: ${DB_CLAVE}      # viene del .env, jamás escrita aquí
      POSTGRES_DB: ${DB_NOMBRE:-app}
    volumes:
      - pgdatos:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USUARIO:-app}"]
      interval: 5s
      retries: 10
volumes:
  pgdatos:
```
No publiques el puerto de la base (`5432`) al exterior salvo que el usuario lo necesite: dentro de la red del compose la app la alcanza por el nombre `db`. Detecta el motor por evidencia (`psycopg`, `pg`, `DATABASE_URL`, `mysql`, `redis`…), no lo supongas.

## `.env.example` (si falta)

Lista **los nombres** de las variables que el código lee, sin valores reales:
```
PUERTO=8000
DB_PATH=/data/app.db
API_KEY=cambia-esto
```
Y recuerda al usuario: `.env` real nunca se sube a Git ni se pega en el chat.
