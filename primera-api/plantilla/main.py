# main.py — tu primera API con FastAPI.
# Cocina = este programa · Ventanilla = FastAPI · Menú = la página /docs que se crea sola.
from fastapi import FastAPI

# Abres el negocio: creas la aplicación (el título aparece en /docs).
app = FastAPI(title="Mi primera API")


# GET = leer. Cuando alguien pida la dirección /saludo, responde con este mensaje en JSON.
@app.get("/saludo")
def saludo():
    return {"mensaje": "Hola, soy tu primera API"}


# Una dirección con un dato variable: /saludo/Ana responde «Hola, Ana».
@app.get("/saludo/{nombre}")
def saludo_personal(nombre: str):
    return {"mensaje": f"Hola, {nombre}"}
