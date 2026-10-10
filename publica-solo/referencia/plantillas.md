# Plantillas de workflow

Archivo: `.github/workflows/publicar.yml` (si ya existe un workflow, **no lo sobrescribas**: lee el existente, dilo y escribe el nuevo con otro nombre o propón cambios).

Reglas comunes:
- **Disparadores**: `push` a la rama principal (la que detectaste: `main`/`master`) y `pull_request`. El despliegue **solo** en `push` a esa rama.
- **`permissions: contents: read`** arriba; cada job de despliegue añade solo lo que necesita.
- **Acciones con versión** (`actions/checkout@v4`), nunca `@main`/`@master`. Prefiere acciones de `actions/*` y `github/*`.
- **Mismas versiones que en tu computadora**: el runtime sale de `.nvmrc` / `engines` / `.python-version` / `python_requires`; si no hay, la que usaste para probar y márcalo **supuesto**.
- **Los mismos comandos que corre el proyecto**: `npm test` si hay `scripts.test`; `python -m pytest -q` si hay pruebas de pytest. No inventes un comando que el proyecto no tenga.
- **Secretos solo como `${{ secrets.NOMBRE }}`**, pasados por `env:` (no pegados dentro del comando).
- `concurrency` para cancelar ejecuciones viejas de la misma rama y `timeout-minutes` para que un job colgado no gaste minutos.

## CI de Python (pruebas)
```yaml
name: Pruebas y publicación

on:
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  pruebas:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Instalar dependencias
        run: pip install -r requirements-dev.txt   # o requirements.txt si no hay separación
      - name: Correr las pruebas
        run: python -m pytest -q
```
Notas: con `pyproject.toml` usa `pip install -e ".[dev]"` según lo que declare. Si el proyecto no tiene archivo de dependencias, dilo: la CI no puede adivinarlas.

## CI de Node (pruebas)
```yaml
jobs:
  pruebas:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - name: Instalar dependencias
        run: npm ci
      - name: Correr las pruebas
        run: npm test
      - name: Construir
        run: npm run build --if-present
```
(Encabezado `name/on/permissions/concurrency` como arriba.) `npm ci` exige `package-lock.json`; sin él usa `npm install` y avísalo. Con yarn/pnpm cambia `cache` y los comandos según el lockfile que exista.

## Despliegue (CD): elige UNO según la evidencia del paso 1

Añade un segundo job a continuación de `pruebas`. Todos tienen la misma forma:
```yaml
  desplegar:
    needs: pruebas                                         # solo si las pruebas pasaron
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      ...
```

### GitHub Pages (sitio estático: HTML, o `dist/` de Vite/React)
Evidencia: no hay `vercel.json`/`netlify.toml`, el proyecto se construye a `dist/` o es HTML plano. Sin secretos; el usuario activa Pages una vez.
```yaml
  desplegar:
    needs: pruebas
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.despliegue.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: dist
      - id: despliegue
        uses: actions/deploy-pages@v4
```
Usuario: *Settings → Pages → Source: GitHub Actions*. Si el sitio vive en `usuario.github.io/repo/`, Vite necesita `base: '/repo/'`.

### Vercel
Evidencia: `vercel.json` o carpeta `.vercel`. Secretos: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (los dos IDs están en `.vercel/project.json` tras `vercel link`; el token se crea en vercel.com → Account Settings → Tokens).
```yaml
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22 }
      - name: Verificar secretos
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          for v in VERCEL_TOKEN VERCEL_ORG_ID VERCEL_PROJECT_ID; do
            if [ -z "$(printenv $v)" ]; then echo "::error::Falta el secreto $v en Settings > Secrets and variables > Actions"; exit 1; fi
          done
      - name: Desplegar a producción
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
          VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
          VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
        run: |
          npx --yes vercel@latest pull --yes --environment=production --token="$VERCEL_TOKEN"
          npx --yes vercel@latest build --prod --token="$VERCEL_TOKEN"
          npx --yes vercel@latest deploy --prebuilt --prod --token="$VERCEL_TOKEN"
```
(Alternativa sin Actions: conectar el repo desde el panel de Vercel; si el usuario ya lo hizo, **no necesita CD**: dilo y deja solo CI.)

### Netlify
Evidencia: `netlify.toml`. Secretos: `NETLIFY_AUTH_TOKEN` (User settings → Applications → Personal access tokens) y `NETLIFY_SITE_ID` (Site configuration → Site ID).
```yaml
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npm run build
      - name: Desplegar a producción
        env:
          NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}
          NETLIFY_SITE_ID: ${{ secrets.NETLIFY_SITE_ID }}
        run: npx --yes netlify-cli@latest deploy --dir=dist --prod
```
Antepón el mismo paso «Verificar secretos» (con sus dos nombres). Siempre `--dir` con la carpeta ya construida, nunca la raíz del proyecto.

### Imagen Docker en GitHub Container Registry (si hay `Dockerfile` y no hay otro destino)
Sin secretos propios: usa el `GITHUB_TOKEN` automático.
```yaml
  desplegar:
    needs: pruebas
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 20
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
```
(El nombre de la imagen debe ir en minúsculas; los usuarios de GitHub con mayúsculas necesitan escribirlo a mano.) Esto **publica la imagen**, no la ejecuta en un servidor: dile al usuario que alojarla es otro paso.

### Sin destino claro
Entrega **solo CI** y pregunta en una línea dónde quiere publicar. No inventes un destino ni pidas secretos «por si acaso».

## Fuera de alcance (dilo si el proyecto lo necesita)
Apps móviles (Expo/EAS, tiendas), bases de datos y migraciones automáticas, servidores propios por SSH: requieren secretos y decisiones que esta skill no toma sola; ofrece CI y señala el siguiente paso.
