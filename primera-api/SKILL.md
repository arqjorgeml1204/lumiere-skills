---
name: primera-api
description: Arma contigo tu primera API con Python y FastAPI, paso a paso y en español, para principiantes. Úsala cuando el usuario quiera crear una API, empezar con FastAPI, «hacer que mi programa reciba pedidos», o cuando algo de FastAPI/uvicorn/pip no le funcione al primer intento.
---

# Primera API — de cero a una API funcionando, en español

Hecha por Lumière Autómata para la serie Learning (lumiereautomata.com/learning, día 2: «Cómo se construye una API»).

## Qué entrega siempre (el diferenciador)
Un proyecto que **funciona a la primera**, no un fragmento suelto: los tres archivos de `plantilla/` (`main.py` comentado en español, `test_main.py` con 3 pruebas, `requirements.txt`), los pasos exactos para el sistema del usuario y la comprobación de que quedó bien. Si algo falla, el diagnóstico sale de `referencia/errores.md`.

## Cómo guiar (en este orden; una etapa por mensaje si el usuario es principiante)

**1. Situación.** Pregunta **solo lo que falte** de: sistema (Windows, Mac, Linux), si ya tiene Python (`python --version`) y si ha usado una terminal. Si dice que nunca programó, empieza por el paso 1b.

**1b. Lo básico (solo si nunca usó una terminal).**
- Abrir la terminal: Windows → tecla Windows, escribir `cmd`, Enter (usar **cmd**, no PowerShell: evita el bloqueo de scripts al activar el entorno). Mac → Cmd+Espacio, «Terminal».
- Editor: **VS Code** (code.visualstudio.com). No usar el Bloc de notas: guarda `.txt` y comillas raras.
- Carpeta: crear `mi-primera-api` en Documentos y entrar con `cd` (Windows: `cd %USERPROFILE%\Documents\mi-primera-api`; si Documentos está en OneDrive, escribe `cd ` y arrastra la carpeta a la terminal, luego Enter; Mac: `cd ~/Documents/mi-primera-api`). Explica: «la terminal siempre trabaja dentro de una carpeta; todos los comandos van en esta».

**2. Preparar.** Comandos exactos para su sistema, en bloques separados, explicando cada uno en una línea:
- Python ≥ 3.10. Si falta, python.org; en Windows marcar «Add python.exe to PATH». Trampa de Windows: si `python --version` abre la Microsoft Store o no responde, es el atajo de la Store, no Python; instalar desde python.org y abrir una terminal nueva. Si `python` no existe pero `py` sí, usar `py` en todos los comandos.
- Entorno virtual en la carpeta del proyecto: `python -m venv .venv`; activar: Windows (cmd) `.venv\Scripts\activate`, Mac/Linux `source .venv/bin/activate`. Explica: «una caja aparte para las herramientas de este proyecto»; debe aparecer `(.venv)` al inicio de la línea. Cada terminal nueva se activa otra vez.
- `python -m pip install -r requirements.txt` (usa siempre `python -m pip`: evita el error de «pip no se reconoce»).

**3. Crear los archivos.** Si tienes acceso al sistema de archivos, crea los tres de `plantilla/` tal cual. Si no, muéstralos completos y di **dónde guardarlos**: en VS Code, Archivo → Abrir carpeta → `mi-primera-api`, luego Nuevo archivo con el nombre exacto (`main.py`, `test_main.py`, `requirements.txt`). No los acortes ni cambies los comentarios.

**4. Encender.** `python -m uvicorn main:app --reload` (con `python -m`, nunca `uvicorn` solo). Explica: «tu computadora ahora es un servidor; mientras esta terminal esté abierta, la ventanilla está abierta». Qué debe verse: `Uvicorn running on http://127.0.0.1:8000`.

**5. Probar en el menú.** `http://127.0.0.1:8000/docs` → desplegar **GET /saludo** → **Try it out** (pruébalo) → **Execute** (ejecutar) → código **200** y el mensaje. Luego `/saludo/{nombre}` con su propio nombre.

**6. Comprobar con las pruebas.** En **otra** terminal (el servidor sigue en la primera; para apagarlo: Ctrl+C), en la carpeta del proyecto y con el entorno activado: `python -m pytest -q` → debe decir `3 passed`. Explica: «esto revisa tu API sola, sin abrir el navegador; así sabrás si un cambio la rompe».

**7. Primer cambio propio.** Propón uno pequeño (cambiar el mensaje o agregar `/hora` que responda la hora) y que vuelva a correr las pruebas.

## Si algo falla
Pide el **mensaje de error completo** y búscalo en `referencia/errores.md`; responde con: qué pasó (una frase), por qué, y el comando exacto que lo arregla. Si el error es `'python' no se reconoce`, es la instalación (paso 2). Si es de `uvicorn`, `pip`, `pytest` o «No module named», **antes** de aplicar el arreglo de la tabla confirma tres cosas en este orden: está en la carpeta del proyecto (`cd`), ve `(.venv)` al inicio de la línea, y corrió `python -m pip install -r requirements.txt`.

## Palabras nuevas (dales en español la primera vez)
Framework · marco de trabajo · Server · servidor · Endpoint · punto de acceso · Virtual environment · entorno virtual · Request · petición · Response · respuesta · Test · prueba · Reload · recarga automática.

## Reglas
- Español claro, frases cortas, tutea. Nada de jerga sin traducir.
- No inventes salidas de comandos; si el usuario no pegó lo que vio, pregúntalo.
- Nunca pidas ni repitas claves o contraseñas.
- No avances de etapa si la anterior no funcionó.
