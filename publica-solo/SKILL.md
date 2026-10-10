---
name: publica-solo
description: Prepara la publicación automática de tu proyecto y la prueba. Analiza tu código (lenguaje, pruebas, hacia dónde se despliega), escribe el workflow de GitHub Actions (pruebas automáticas y, si aplica, despliegue), lo valida y corre aquí los mismos comandos de pruebas, y te entrega un informe con lo que tienes que hacer tú. Úsala cuando el usuario diga "quiero que mi proyecto se publique solo", "configura GitHub Actions", "haz el CI/CD", "que se corran las pruebas cada vez que subo código" o "despliegue automático".
---

# Publica solo — tu proyecto se prueba y se publica sin que lo hagas a mano

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 7: «CI/CD: publicar sin hacerlo a mano»).

**La idea en una frase:** es como una *línea de ensamblaje con inspector*: cada vez que subes cambios, un robot de GitHub ejecuta tus pruebas (el inspector) y, solo si todo pasa, publica tu proyecto (el empaque y envío).

- **CI** (*Continuous Integration*, integración continua) = revisar automáticamente cada cambio.
- **CD** (*Continuous Delivery/Deployment*, entrega/despliegue continuo) = publicar automáticamente lo que pasó la revisión.

## Qué hace que un chat normal no hace
1. **Lee tu proyecto real**: lenguaje, versión, comando de pruebas, forma de construirlo y señales de dónde lo publicas (`vercel.json`, `netlify.toml`, `Dockerfile`…).
2. **Entrega archivos**: `.github/workflows/publicar.yml` e `informe-publicacion.md`.
3. **Los prueba antes de entregártelos** con `scripts/validar_workflow.py`: YAML y estructura, reglas de seguridad, `actionlint` si está instalado, y **ejecuta aquí los mismos comandos de pruebas/construcción** que luego correrá GitHub.
4. **Es honesta**: no puede ejecutar GitHub por ti. Te dice exactamente qué comprobó y qué solo se verá la primera vez que subas el código.

## Proceso (siempre estos 7 pasos, en este orden)

**1. Reunir evidencia.** Busca antes de preguntar:
- Lenguaje y gestor: `package.json` (+ lockfile), `requirements*.txt`/`pyproject.toml`, `go.mod`, `pom.xml`…
- **Comando de pruebas real**: `scripts.test` en `package.json`; `pytest`/`unittest` en dependencias y carpeta `tests/`. Si el proyecto **no tiene pruebas**, dilo: el CI solo podrá instalar y construir, y recomienda escribir al menos una (no inventes pruebas dentro de esta tarea sin permiso).
- Versión del runtime: `.nvmrc`, `engines`, `.python-version`, `python_requires`.
- Cómo se construye: `scripts.build`, `Dockerfile`.
- **Destino de despliegue** por señales: `vercel.json`/`.vercel/` (Vercel), `netlify.toml` (Netlify), `Dockerfile` (imagen), `dist/` o HTML plano (Pages), `app.json`/`eas.json` (app móvil → fuera de alcance). Pregunta si hay varias o ninguna.
- Rama principal y remoto: `git branch --show-current`, `git remote get-url origin`. `.github/workflows/` existente: **léelo y no lo sobrescribas**.
Si falta algo que cambie el resultado, haz **una sola pregunta numerada**; lo demás, supuesto marcado (S1, S2…).

**2. Ficha del proyecto.** Tabla `dato | valor | evidencia (archivo) | ¿supuesto?`: lenguaje, versión, instalación, comando de pruebas, comando de construcción, rama principal, destino de despliegue.

**3. Diseñar el flujo** con una tabla `cuándo | qué corre | qué pasa si falla`. Siempre: en `pull_request` y `push` a la rama principal corren las **pruebas**; el **despliegue** solo en `push` a la rama principal y solo si las pruebas pasaron. Si el destino no está claro, **solo CI**.

**4. Escribir el workflow** `.github/workflows/publicar.yml` desde `referencia/plantillas.md` (respeta sus reglas: acciones con versión, `permissions` mínimos, mismas versiones que el proyecto, secretos solo como `${{ secrets.NOMBRE }}`). Si hay despliegue con secretos, incluye el paso «Verificar secretos», que falla con un mensaje claro en español si falta alguno. No toques el código del proyecto, no hagas `git push`, no crees secretos ni actives servicios.

**5. Validar y probar.** Desde la carpeta de la skill (o con su ruta):
`python scripts/validar_workflow.py "<carpeta-del-proyecto>" --ejecutar pruebas`
Hace, en este orden: (a) YAML y estructura; (b) reglas de seguridad; (c) `actionlint` si existe; (d) **ejecuta aquí los comandos `run:` del job `pruebas`** y muestra el resultado real de cada uno. Si algo falla: corrige el workflow (si el error es del workflow) o dile al usuario que el proyecto falla sus propias pruebas (si es del proyecto) y por qué **no** se puede entregar como «listo». Repite hasta pasar. Si falta una herramienta (Node, Python, PyYAML, actionlint), el script lo dice: conserva esa frase en el informe como «NO verificado: …».
En Windows, si `python`/`pip` no están en el PATH, el script usa el intérprete que lo ejecuta (o el que indiques con `--python RUTA`) y lo avisa. Nunca ejecutes el job de despliegue en local.

**6. Checklist de verificación.** Marca ✅ (comprobado, con la salida que lo prueba), ⚠️ (aviso) o ⛔ (no comprobado, con motivo):
- [ ] YAML válido (¿con parser real o solo estructura?)
- [ ] `on`, `jobs`, `runs-on`, `steps` presentes
- [ ] Acciones con versión fija
- [ ] `permissions` mínimos
- [ ] Ningún secreto escrito en el archivo
- [ ] Despliegue solo en la rama principal y con `needs: pruebas`
- [ ] Comandos de instalación y pruebas **ejecutados aquí con éxito**
- [ ] Versión de Node/Python del workflow vs. la de tu computadora (la salida del script las compara)
- [ ] `actionlint` (✅ o ⛔ «no instalado»)
- [ ] ⛔ **Ejecución real en GitHub: NO verificada** (solo ocurre al subir el código; siempre va en la lista)

**7. Entrega (formato fijo, en este orden).** Guárdalo también en `informe-publicacion.md`:
1. **Resultado en una línea**: «Workflow listo y validado; falta que lo subas y configures los secretos» (o lo que corresponda).
2. **Archivos entregados** (rutas).
3. **Ficha del proyecto** (paso 2).
4. **Cómo funciona**, con la analogía y la tabla del paso 3, en palabras sencillas.
5. **Qué se ejecutó y qué salió**: comandos reales y su resultado (copia la salida del script, no la resumas).
6. **Qué NO se pudo verificar** (siempre incluye la ejecución real en GitHub).
7. **Lo que tienes que hacer tú**, numerado y con los nombres exactos: `git push` de la rama; crear cada secreto en *Settings → Secrets and variables → Actions* (nombre exacto, de dónde sale el valor, **nunca pegarlo en el chat**); activar Pages si aplica.
8. **Cómo comprobar que funcionó**: pestaña *Actions*, qué verás en verde, y la tabla de errores típicos (`referencia/errores.md`).
9. **Palabras nuevas** (máximo 5).

## Palabras nuevas (en español la primera vez)
Workflow · flujo de trabajo automático · Job · tarea · Step · paso · Runner · máquina de GitHub que ejecuta tu flujo · Secret · secreto (valor privado guardado en GitHub) · Trigger · disparador · Pipeline · tubería (el conjunto CI + CD) · Deploy · desplegar/publicar · Artifact · artefacto (archivo que produce un job).

## Reglas
- Español claro, frases cortas, tutea. Explica cada término técnico la primera vez.
- **Nunca** escribas, copies ni repitas secretos (tokens, llaves, contraseñas). En los archivos solo van nombres de secretos. Si el usuario pega uno en el chat, dile que lo revoque y cree otro.
- **Nunca** hagas push, crees secretos, actives GitHub Pages, ni contrates o suscribas servicios; eso lo decide y lo hace el usuario. Si el destino cuesta dinero o exige una cuenta, dilo sin afirmar precios: «revisa el plan vigente».
- No inventes: comandos, versiones o destinos que no estén en el proyecto se preguntan o se marcan **supuesto**. Nunca digas «probado» para algo que no se ejecutó; lo que solo ocurre en GitHub se declara **no verificado**.
- No sobrescribas un workflow existente sin decirlo.
