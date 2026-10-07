# Errores comunes al empezar con FastAPI (y su arreglo)

Antes de aplicar un arreglo de «no se reconoce» (salvo `python`) o «No module named»: carpeta correcta (`cd`), `(.venv)` visible y `python -m pip install -r requirements.txt` hecho. Ver «Si algo falla» en SKILL.md.

| Mensaje (o parte) | Qué pasó | Arreglo |
|---|---|---|
| `'python' no se reconoce` / `command not found: python` | Python no está instalado o no está en el PATH. | Instalar desde python.org marcando «Add python.exe to PATH» (Windows) y abrir una terminal **nueva**. En Mac/Linux probar `python3`. |
| `'pip' no se reconoce` | El ejecutable de pip no está en el PATH. | Usar siempre `python -m pip install …`. |
| `'uvicorn' no se reconoce` | Igual que pip. | `python -m uvicorn main:app --reload`. |
| `ModuleNotFoundError: No module named 'fastapi'` | Se instaló en otro Python, o el entorno virtual no está activado. | Activar `.venv` y repetir `python -m pip install -r requirements.txt`. |
| `Error loading ASGI app. Could not import module "main"` | Uvicorn se corrió fuera de la carpeta del proyecto, o el archivo no se llama `main.py`. | Ir a la carpeta (`cd`) donde está `main.py` o cambiar `main:app` por `nombre_archivo:app`. |
| `Attribute "app" not found in module "main"` | La variable no se llama `app`. | En `main.py` debe existir `app = FastAPI(...)`. |
| `[Errno 10048]` / `address already in use` | El puerto 8000 ya está ocupado (otro uvicorn abierto). | Cerrar la otra terminal o usar `--port 8001`. |
| `IndentationError` | Espacios mal puestos en Python. | Las líneas dentro de una función van con 4 espacios; no mezclar tabuladores y espacios. |
| `SyntaxError` en una línea con comillas | Comillas «tipográficas» copiadas de un documento. | Reescribir las comillas a mano en el editor (`"`). |
| `{"detail":"Not Found"}` con código 404 | La dirección no existe en la API. | Revisar mayúsculas y la barra: `/saludo`, no `/Saludo` ni `/saludo/`. |
| `422 Unprocessable Entity` | Falta un dato o tiene el tipo equivocado. | Leer `detail`: dice qué campo y qué esperaba. |
| `cannot be loaded because running scripts is disabled` (PowerShell al activar `.venv`) | Windows bloquea scripts por política. | Usar `cmd` en lugar de PowerShell, o en PowerShell: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (explicar antes qué hace y que es decisión del usuario). |
| La página `/docs` no carga pero `/saludo` sí | Sin internet: /docs descarga su diseño de una CDN. | Conectarse a internet; la API funciona igual. |
| `pytest` dice `0 passed` o no encuentra pruebas | El archivo no empieza por `test_` o se corrió en otra carpeta. | Correr `python -m pytest -q` en la carpeta del proyecto. |
