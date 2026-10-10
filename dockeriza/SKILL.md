---
name: dockeriza
description: Analiza tu proyecto (su código, sus dependencias y cómo arranca), le escribe su Dockerfile, su .dockerignore y su docker-compose, y los prueba construyendo y arrancando el contenedor antes de entregártelos. Úsala cuando el usuario diga "dockeriza mi proyecto", "quiero usar Docker", "cómo meto mi app en un contenedor", "hazme un Dockerfile" o "cómo despliego mi app igual que en mi computadora".
---

# Dockeriza — tu proyecto en un contenedor, probado

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 5: «Docker y contenedores»).

**La idea en una frase:** un contenedor es como una *lonchera sellada*: lleva tu programa y todo lo que necesita (versión de Python o Node, librerías, configuración), así funciona igual en tu computadora, en la de tu socio y en el servidor.

## Qué hace que un chat normal no hace
1. **Lee tu proyecto real**: lenguaje, dependencias, comando de arranque, puerto, variables de entorno y servicios que usa. No te da un ejemplo genérico.
2. **Entrega archivos**, no solo explicación: `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `.env.example` (si falta) e `informe-docker.md`.
3. **Los prueba antes de entregártelos** con `scripts/verificar_docker.py`: revisión de seguridad y buenas prácticas, y —si Docker está disponible— construye la imagen, arranca el contenedor y comprueba que responde.
4. **Es honesta**: si en tu computadora no hay Docker, entrega los archivos marcados `SIN PROBAR` y te dice cómo probarlos. Nunca dice que probó algo que no ejecutó.

## Proceso (siempre estos 7 pasos, en este orden)

**1. Reunir evidencia.** Busca en la carpeta del proyecto antes de preguntar: `requirements.txt`/`pyproject.toml`/`Pipfile`, `package.json` (+ `package-lock.json`), `go.mod`, `pom.xml`, `Gemfile`, `composer.json`; el archivo de arranque (`main.py`, `app.py`, `manage.py`, `server.js`, `scripts.start`); `.env.example`/`.env` (**lee solo los nombres de las variables, nunca los valores ni los repitas**); `.python-version`/`.nvmrc`/`engines`; `.gitignore`; un `Dockerfile` o compose previo (si existe, **no lo sobrescribas**: léelo, dilo y propón cambios aparte). Detecta servicios externos por evidencia (`psycopg`, `pg`, `DATABASE_URL`, `redis`, `mongodb`…). Cita los archivos que usaste.
Solo si falta algo que cambie el resultado, haz **una sola pregunta numerada** (ej.: ¿cómo arrancas la app hoy?, ¿qué puerto usa?, ¿usa base de datos?). Lo demás, supuesto marcado.

**2. Ficha del proyecto.** Tabla `dato | valor | evidencia (archivo) | ¿supuesto?`: lenguaje y versión, gestor de dependencias, comando de arranque, puerto, ruta de salud, variables de entorno (solo nombres), servicios externos, carpetas con datos que deben sobrevivir, tamaño aproximado de lo que no debe entrar (`node_modules`, `.venv`).

**3. Escribir los archivos** con `referencia/plantillas.md` (respeta sus reglas: versión fija, dependencias antes del código, usuario sin privilegios, `0.0.0.0`, healthcheck, cero secretos):
- `Dockerfile`
- `.dockerignore`
- `docker-compose.yml` (la app; con base de datos y volumen solo si la evidencia lo pide)
- `.env.example` si el proyecto lee variables y no lo tiene
Escríbelos **en la carpeta del proyecto** (no en la skill). Si la app no tiene ruta de salud, propón añadir una mínima (`/salud` → `{"estado":"ok"}`) y pide permiso antes de tocar su código; sin permiso, usa `/` en el healthcheck.

**4. Probar.** Ejecuta, desde la carpeta de la skill o con su ruta:
`python scripts/verificar_docker.py "<carpeta-del-proyecto>" --puerto <puerto> --ruta-salud <ruta>`
- **Con Docker encendido** hace todo: revisión estática, `docker build`, `docker run`, pide la ruta de salud, comprueba que no corre como root, y si hay compose: `docker compose config`, `up --build`, salud y `down`.
- **Sin Docker** (o apagado) hace la revisión estática y termina con `ESTADO: SIN PROBAR (motivo)`.
- Si sale `FALLÓ`, corrige y repite hasta que pase o hasta explicar honestamente qué no se pudo resolver. No entregues archivos con fallas sin decirlo.
- Si Docker no existe, **no lo instales tú** (instala servicios del sistema: WSL2, Docker Desktop). Dile al usuario cómo hacerlo (`referencia/errores.md`) y que vuelva a correr el comando del paso 4.

**5. Checklist de verificación.** Marca cada punto como ✅ (comprobado, con la salida que lo prueba), ⚠️ (aviso) o ⛔ (no comprobado, con motivo):
- [ ] Imagen base con versión fija
- [ ] Dependencias antes del código (caché de capas)
- [ ] Usuario sin privilegios
- [ ] `.dockerignore` excluye `.git`, `.env` y carpetas pesadas
- [ ] Ningún secreto en Dockerfile, compose ni imagen (variables por `env_file`/`${VAR}`)
- [ ] Escucha en `0.0.0.0` y el puerto coincide en Dockerfile, compose y app
- [ ] Healthcheck definido
- [ ] Datos persistentes en un volumen (si la app escribe)
- [ ] **Build y arranque ejecutados** → `PROBADO`; si no → `SIN PROBAR`

**6. Marcar los archivos con su estado** (primera línea, como comentario `#`, de `Dockerfile`, `.dockerignore` y `docker-compose.yml`; `.env.example` no lleva marca):
- `# Estado: PROBADO el AAAA-MM-DD (docker build + arranque + salud OK)`
- `# Estado: SIN PROBAR — Docker no estaba disponible; solo se validó la sintaxis y las reglas (ver informe-docker.md)`
Usa exactamente lo que dijo `ESTADO:` del paso 4. En un Dockerfile la primera línea puede ser un comentario, así que es válido.

**7. Entrega (formato fijo, en este orden).**
1. **Resultado en una línea** con el estado: «Tu proyecto quedó dockerizado y PROBADO» o «… SIN PROBAR (no hay Docker aquí)».
2. **Archivos entregados** (lista con rutas).
3. **Ficha del proyecto** (paso 2).
4. **Qué se ejecutó y qué salió** (comandos reales y su resultado, no resúmenes inventados) y **qué NO se pudo verificar**.
5. **Cómo usarlo**: `docker compose up -d --build`, abrir `http://localhost:<puerto>`, `docker compose logs -f`, `docker compose down`. Si faltan variables: `copy .env.example .env` y rellenar.
6. **Si salió SIN PROBAR**: los 3 comandos para probarlo (`docker compose config`, `docker compose up -d --build`, abrir la URL) y qué hacer con los errores típicos (`referencia/errores.md`).
7. **Palabras nuevas** (máximo 5).
Guarda 2–6 también en `informe-docker.md` junto a los archivos.

## Palabras nuevas (en español la primera vez)
Container · contenedor · Image · imagen · Dockerfile · receta de la imagen · Volume · volumen (disco que sobrevive) · Port mapping · puerto expuesto · Healthcheck · chequeo de salud · Build · construir · Compose · orquestador local · Layer · capa · Registry · registro (almacén de imágenes).

## Reglas
- Español claro, frases cortas, tutea. Explica cada término técnico la primera vez.
- **Nunca** escribas, copies ni repitas secretos (claves, contraseñas, tokens, cadenas de conexión). Si el usuario pega uno, avísale que lo cambie. En los archivos solo van nombres de variables.
- **Nunca** instales Docker, WSL ni nada del sistema; **nunca** subas imágenes a un registro ni despliegues: esta skill prepara y prueba en local.
- No inventes lo que no viste: puerto, comando de arranque o servicios que no aparezcan en el proyecto se preguntan o se marcan como **supuesto**.
- No borres imágenes, contenedores ni volúmenes del usuario; la prueba solo apaga lo que ella misma creó.
- Si ya existía un Dockerfile/compose, no lo sobrescribas sin decirlo.
