#!/usr/bin/env python3
"""Verifica el Dockerfile, el .dockerignore y el docker-compose de un proyecto.

Hecho por Lumière Autómata (skill «dockeriza»). Solo usa la biblioteca estándar de Python.

Uso:
    python verificar_docker.py CARPETA_DEL_PROYECTO [--puerto 8000] [--ruta-salud /salud]
                               [--imagen nombre] [--sin-docker] [--espera 40]

Qué hace:
  1. Revisión estática (siempre): reglas de buenas prácticas y de seguridad.
  2. Si Docker está instalado y encendido: construye la imagen, arranca el contenedor,
     pide la ruta de salud y lo apaga; si hay docker-compose.yml también lo levanta.
  3. Si Docker NO está disponible, lo dice y termina con  ESTADO: SIN PROBAR.
     Nunca declara «probado» algo que no se ejecutó.

Código de salida: 0 = sin fallas (probado o sin probar), 1 = hay fallas.
La última línea es siempre  ESTADO: PROBADO | SIN PROBAR (motivo) | FALLÓ (motivo).
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SECRETOS = r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL)"
resultados = []  # (nivel, mensaje)


def anota(nivel, msg):
    resultados.append((nivel, msg))
    print(f"[{nivel}] {msg}")


def lee(ruta):
    return ruta.read_text(encoding="utf-8", errors="replace")


# ---------------------------------------------------------------- estática
def revisa_dockerfile(carpeta):
    df = carpeta / "Dockerfile"
    if not df.exists():
        anota("FALLA", "No existe Dockerfile")
        return
    anota("OK", "Existe Dockerfile")
    # une líneas partidas con «\» y quita comentarios
    texto = re.sub(r"\\\r?\n", " ", lee(df))
    lineas = [l.strip() for l in texto.splitlines() if l.strip() and not l.strip().startswith("#")]
    froms = [l for l in lineas if l.upper().startswith("FROM ")]
    if not froms:
        anota("FALLA", "El Dockerfile no tiene FROM")
        return
    for f in froms:
        img = f.split()[1]
        if img.lower() == "scratch" or img.startswith("$"):
            continue
        if ":" not in img.split("/")[-1] and "@" not in img:
            anota("FALLA", f"FROM sin versión (usa :latest implícito): {img}")
        elif img.endswith(":latest"):
            anota("FALLA", f"FROM con :latest, fija una versión: {img}")
        else:
            anota("OK", f"Imagen base con versión fija: {img}")
    users = [l.split(None, 1)[1].strip() for l in lineas if l.upper().startswith("USER ")]
    if users and users[-1].split(":")[0] not in ("root", "0"):
        anota("OK", f"Corre sin privilegios (USER {users[-1]})")
    else:
        anota("FALLA", "El contenedor corre como root: agrega un USER sin privilegios")
    if any(l.upper().startswith("EXPOSE ") for l in lineas):
        anota("OK", "Declara EXPOSE")
    else:
        anota("AVISO", "Falta EXPOSE (documenta el puerto)")
    if any(l.upper().startswith(("CMD ", "ENTRYPOINT ")) for l in lineas):
        anota("OK", "Define CMD/ENTRYPOINT (comando de arranque)")
    else:
        anota("FALLA", "Falta CMD o ENTRYPOINT: el contenedor no sabría qué ejecutar")
    if any(l.upper().startswith("HEALTHCHECK ") for l in lineas):
        anota("OK", "Tiene HEALTHCHECK")
    else:
        anota("AVISO", "Sin HEALTHCHECK: Docker no sabrá si tu app está sana")
    malos = [l for l in lineas if re.match(r"(COPY|ADD)\s+(--\S+\s+)*\.env(\s|$)", l, re.I)]
    if malos:
        anota("FALLA", f"Copia .env dentro de la imagen: {malos[0]}")
    else:
        anota("OK", "No copia .env a la imagen")
    sec = [l for l in lineas
           if re.match(rf"(ENV|ARG)\s+\w*{SECRETOS}\w*\s*(=|\s)\s*[^\s$]+", l, re.I)]
    if sec:
        anota("FALLA", f"Secreto escrito en el Dockerfile (queda en la imagen): variable {sec[0].split()[1].split('=')[0]} (valor oculto)")
    else:
        anota("OK", "Ningún secreto escrito en ENV/ARG")
    # orden de capas: dependencias antes que el código
    idx_copia = next((i for i, l in enumerate(lineas)
                      if re.match(r"COPY\s+(--\S+\s+)*\.\s+\S+", l, re.I)), None)
    idx_inst = next((i for i, l in enumerate(lineas)
                     if re.search(r"(pip install|npm (ci|install)|yarn install|pnpm install|go mod download|cargo build)", l)), None)
    if idx_copia is not None and idx_inst is not None and idx_copia < idx_inst:
        anota("AVISO", "Copias todo el código ANTES de instalar dependencias: cada cambio reinstalará todo "
                       "(copia primero requirements.txt / package.json)")
    elif idx_inst is not None:
        anota("OK", "Las dependencias se instalan antes de copiar todo el código (aprovecha la caché)")
    if any("pip install" in l and "--no-cache-dir" not in l for l in lineas) and \
            not any("PIP_NO_CACHE_DIR" in l for l in lineas):
        anota("AVISO", "pip install sin --no-cache-dir: la imagen pesará más")


def revisa_dockerignore(carpeta):
    di = carpeta / ".dockerignore"
    if not di.exists():
        anota("FALLA", "No existe .dockerignore (se colarían .git, .env y carpetas pesadas)")
        return
    anota("OK", "Existe .dockerignore")
    reglas = [l.strip().rstrip("/") for l in lee(di).splitlines() if l.strip() and not l.startswith("#")]

    def tiene(*nombres):
        return any(r in nombres or r.lstrip("*/") in nombres for r in reglas)

    if tiene(".git"):
        anota("OK", ".git excluido")
    else:
        anota("FALLA", ".git NO está excluido en .dockerignore")
    if tiene(".env", ".env*", "*.env"):
        anota("OK", ".env excluido")
    else:
        anota("FALLA", ".env NO está excluido en .dockerignore (tus secretos podrían entrar a la imagen)")
    if (carpeta / "package.json").exists():
        if tiene("node_modules"):
            anota("OK", "node_modules excluido")
        else:
            anota("AVISO", "Falta excluir node_modules")
    if (carpeta / "requirements.txt").exists() or (carpeta / "pyproject.toml").exists():
        if tiene("__pycache__", "**/__pycache__") and tiene(".venv", "venv", "env"):
            anota("OK", "__pycache__ y entorno virtual excluidos")
        else:
            anota("AVISO", "Falta excluir __pycache__ y/o el entorno virtual (.venv)")


def revisa_compose(carpeta):
    cf = next((carpeta / n for n in ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml")
               if (carpeta / n).exists()), None)
    if cf is None:
        anota("FALLA", "No existe docker-compose.yml")
        return None
    anota("OK", f"Existe {cf.name}")
    texto = lee(cf)
    if "\t" in texto:
        anota("FALLA", "El YAML contiene tabuladores (YAML solo admite espacios)")
    try:
        import yaml  # opcional
        datos = yaml.safe_load(texto)
        if not isinstance(datos, dict) or "services" not in datos:
            anota("FALLA", "El compose no tiene la sección «services»")
        else:
            anota("OK", f"YAML válido (PyYAML); servicios: {', '.join(datos['services'])}")
    except ImportError:
        if re.search(r"^services:\s*$", texto, re.M):
            anota("AVISO", "PyYAML no está instalado: el YAML NO se analizó con un parser (solo revisión de texto). "
                           "Con Docker usa «docker compose config»")
        else:
            anota("FALLA", "No se encontró la sección «services:»")
    except Exception as e:  # YAML mal formado
        anota("FALLA", f"YAML inválido: {e}")
    lit = [l.strip() for l in texto.splitlines()
           if re.match(rf"\s*-?\s*\w*{SECRETOS}\w*\s*[:=]\s*[^\s$#]", l, re.I)]
    lit = [l for l in lit if "${" not in l]
    if lit:
        anota("FALLA", f"Secreto escrito en el compose: variable {re.split(r'[:=]', lit[0].lstrip('- '))[0].strip()} (valor oculto; usa env_file o ${{VARIABLE}})")
    else:
        anota("OK", "Ningún secreto escrito en el compose")
    if re.search(r"image:\s*\S+:latest\b", texto):
        anota("FALLA", "Una imagen del compose usa :latest")
    if re.search(r"^version:", texto, re.M):
        anota("AVISO", "«version:» está obsoleto en Docker Compose v2; puedes quitarlo")
    if re.search(r"healthcheck:", texto):
        anota("OK", "El compose define healthcheck")
    else:
        anota("AVISO", "El compose no define healthcheck (se hereda el del Dockerfile)")
    return cf


# ---------------------------------------------------------------- ejecución
def corre(cmd, cwd, tiempo=600):
    print("   $ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=tiempo)
    return p.returncode, (p.stdout + p.stderr)


def espera_salud(url, segundos):
    fin = time.time() + segundos
    ultimo = "sin respuesta"
    while time.time() < fin:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                return r.status, r.read(300).decode("utf-8", "replace")
        except Exception as e:
            ultimo = str(e)
            time.sleep(1.5)
    return None, ultimo


def prueba_docker(carpeta, imagen, puerto, ruta, espera, hay_compose):
    """Devuelve (estado, motivo)."""
    docker = shutil.which("docker")
    if not docker:
        return "SIN PROBAR", "Docker no está instalado en esta computadora"
    try:
        rc, _ = corre([docker, "info"], carpeta, 60)
    except Exception as e:
        return "SIN PROBAR", f"no se pudo consultar Docker ({e})"
    if rc != 0:
        return "SIN PROBAR", "Docker está instalado pero apagado (abre Docker Desktop y espera a que diga «running»)"
    nombre = f"{imagen}-prueba"
    url = f"http://localhost:{puerto}{ruta}"
    try:
        rc, salida = corre([docker, "build", "-t", imagen, "."], carpeta)
        print(salida[-1500:])
        if rc != 0:
            return "FALLÓ", "docker build falló (ver salida arriba)"
        anota("OK", "docker build terminó sin errores")
        corre([docker, "rm", "-f", nombre], carpeta, 60)
        rc, salida = corre([docker, "run", "-d", "--name", nombre, "-p", f"{puerto}:{puerto}", imagen], carpeta, 120)
        if rc != 0:
            return "FALLÓ", f"docker run falló: {salida.strip()[-300:]}"
        codigo, cuerpo = espera_salud(url, espera)
        if codigo is None:
            _, logs = corre([docker, "logs", "--tail", "30", nombre], carpeta, 60)
            print(logs)
            return "FALLÓ", f"el contenedor no respondió en {url} ({cuerpo})"
        anota("OK", f"El contenedor responde: GET {url} -> {codigo} {cuerpo[:80]!r}")
        _, usuario = corre([docker, "exec", nombre, "id", "-u"], carpeta, 60)
        if usuario.strip() in ("0", ""):
            anota("FALLA", f"El proceso corre como root dentro del contenedor (UID {usuario.strip() or '?'})")
        else:
            anota("OK", f"UID dentro del contenedor: {usuario.strip()} (no es root)")
    finally:
        corre([docker, "rm", "-f", nombre], carpeta, 60)
    if hay_compose:
        # proyecto con nombre propio: «down -v» solo borra lo que esta prueba creó, nunca tus datos reales
        try:
            rc, salida = corre([docker, "compose", "-p", nombre, "config", "-q"], carpeta, 60)
            if rc != 0:
                return "FALLÓ", f"docker compose config rechazó el archivo: {salida.strip()[-300:]}"
            anota("OK", "docker compose config: el archivo es válido")
            rc, salida = corre([docker, "compose", "-p", nombre, "up", "-d", "--build"], carpeta)
            if rc != 0:
                return "FALLÓ", f"docker compose up falló: {salida.strip()[-400:]}"
            codigo, cuerpo = espera_salud(url, espera)
            if codigo is None:
                return "FALLÓ", f"compose arrancó pero {url} no respondió ({cuerpo})"
            anota("OK", f"compose levantado y responde: {url} -> {codigo}")
        finally:
            corre([docker, "compose", "-p", nombre, "down", "-v"], carpeta, 120)
    return "PROBADO", "build, arranque y ruta de salud comprobados"


def main():
    for flujo in (sys.stdout, sys.stderr):  # que las tildes salgan bien también si la salida se redirige
        if hasattr(flujo, "reconfigure") and not flujo.isatty():
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--ruta-salud", default="/")
    ap.add_argument("--imagen", default=None)
    ap.add_argument("--sin-docker", action="store_true", help="solo revisión estática")
    ap.add_argument("--espera", type=int, default=40, help="segundos máximos esperando a la app")
    a = ap.parse_args()
    carpeta = Path(a.carpeta).resolve()
    # Git Bash convierte «/salud» en «C:/Program Files/Git/salud»: lo deshacemos
    ruta = a.ruta_salud.replace("\\", "/")
    if "/Git/" in ruta:
        ruta = "/" + ruta.split("/Git/", 1)[1]
    a.ruta_salud = ruta if ruta.startswith("/") else "/" + ruta
    imagen = a.imagen or re.sub(r"[^a-z0-9_.-]", "-", carpeta.name.lower()) or "app"
    print(f"== Revisión estática de {carpeta}\n")
    revisa_dockerfile(carpeta)
    revisa_dockerignore(carpeta)
    cf = revisa_compose(carpeta)
    fallas = [m for n, m in resultados if n == "FALLA"]
    avisos = [m for n, m in resultados if n == "AVISO"]
    oks = [m for n, m in resultados if n == "OK"]
    print(f"\n== Estática: {len(oks)} OK, {len(avisos)} avisos, {len(fallas)} fallas")
    if fallas:
        print("ESTADO: FALLÓ (corrige las fallas de la revisión estática antes de probar con Docker)")
        return 1
    if a.sin_docker:
        estado, motivo = "SIN PROBAR", "se pidió solo la revisión estática"
    else:
        print("\n== Prueba con Docker")
        estado, motivo = prueba_docker(carpeta, imagen, a.puerto, a.ruta_salud, a.espera, cf is not None)
    if estado == "PROBADO" and any(n == "FALLA" for n, _ in resultados):
        estado, motivo = "FALLÓ", "la prueba dentro del contenedor encontró fallas"
    print(f"\nESTADO: {estado} ({motivo})")
    return 1 if estado == "FALLÓ" else 0


if __name__ == "__main__":
    sys.exit(main())
