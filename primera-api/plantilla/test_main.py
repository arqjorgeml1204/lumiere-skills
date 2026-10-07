# test_main.py — comprueba que tu API responde bien sin abrir el navegador.
# Córrelo con:  python -m pytest -q
from fastapi.testclient import TestClient

from main import app

cliente = TestClient(app)


def test_saludo():
    r = cliente.get("/saludo")
    assert r.status_code == 200  # 200 = todo bien
    assert r.json() == {"mensaje": "Hola, soy tu primera API"}


def test_saludo_personal():
    r = cliente.get("/saludo/Ana")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Hola, Ana"


def test_direccion_que_no_existe():
    assert cliente.get("/no-existe").status_code == 404  # 404 = eso no existe
