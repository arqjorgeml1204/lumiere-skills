#!/usr/bin/env python3
"""Reúne el cambio que vas a revisar y corre las pruebas y revisores que tu proyecto ya tiene.

Hecho por Lumière Autómata (skill «revisa-mi-codigo»). Solo biblioteca estándar, Python 3.10+.

Uso:
    python preparar_revision.py CARPETA_DEL_PROYECTO                    # tu rama contra la rama base (la detecta)
    python preparar_revision.py CARPETA --base main                     # rama base indicada (o un commit: HEAD~1)
    python preparar_revision.py CARPETA --pr 12                         # un pull request de GitHub (necesita gh)
    python preparar_revision.py CARPETA --carpeta                       # sin git: revisa todos los archivos
    python preparar_revision.py CARPETA --rutas app/,tests/             # solo una parte del cambio
    python preparar_revision.py CARPETA --sin-ejecutar                  # no corre pruebas ni revisores

Qué hace, siempre en este orden:
  1. Obtiene el diff: desde el punto donde tu rama salió de la base hasta tus archivos de hoy
     (incluye lo que aún no has guardado en un commit y los archivos nuevos que git todavía no sigue).
  2. Lista los archivos tocados con sus líneas agregadas y quitadas. Si el cambio pasa de 400 líneas,
     propone cómo partirlo.
  3. Detecta y ejecuta lo que el proyecto ya tiene: pruebas (pytest, unittest, npm test, go test, cargo test),
     revisores de estilo (ruff, flake8, eslint) y de tipos (mypy, tsc). No instala nada.
  4. Escribe en CARPETA/revision-codigo/: cambio.diff, contexto.json, herramientas.json y herramientas.log.
     Esa carpeta trae su propio .gitignore, así que git la ignora y no se cuela en tus commits.
"""
import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

LIMITE_LINEAS = 400
CARPETA_SALIDA = "revision-codigo"
IGNORAR_DIRS = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".next",
                ".pytest_cache", ".mypy_cache", ".ruff_cache", "coverage", CARPETA_SALIDA}
EXT_TEXTO = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".json", ".md", ".txt", ".html", ".css", ".scss",
             ".sql", ".yml", ".yaml", ".toml", ".ini", ".cfg", ".go", ".rs", ".java", ".kt", ".rb", ".php", ".cs",
             ".c", ".h", ".cpp", ".hpp", ".sh", ".ps1", ".vue", ".svelte", ".env", ".example"}


def git(carpeta, *args, permitir_error=False):
    p = subprocess.run(["git", "-c", "core.quotepath=off", *args], cwd=carpeta, capture_output=True)
    salida = p.stdout.decode("utf-8", errors="replace")
    if p.returncode != 0 and not permitir_error:
        raise RuntimeError(f"git {' '.join(args)} falló: {p.stderr.decode('utf-8', errors='replace').strip()}")
    return salida if p.returncode == 0 else None


def es_repo(carpeta):
    return git(carpeta, "rev-parse", "--is-inside-work-tree", permitir_error=True) is not None


def detectar_base(carpeta):
    ref = git(carpeta, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD", permitir_error=True)
    if ref:
        return ref.strip().replace("refs/remotes/", "")
    for candidata in ("main", "master", "develop", "origin/main", "origin/master"):
        if git(carpeta, "rev-parse", "--verify", "--quiet", candidata, permitir_error=True):
            return candidata
    return None


def diff_archivo_nuevo(ruta_rel, contenido):
    lineas = contenido.splitlines(keepends=True)
    if lineas and not lineas[-1].endswith("\n"):
        lineas[-1] += "\n"
    cuerpo = "".join(difflib.unified_diff([], lineas, "/dev/null", f"b/{ruta_rel}", n=3))
    return f"diff --git a/{ruta_rel} b/{ruta_rel}\nnew file mode 100644\n{cuerpo}" if cuerpo else ""


def leer_texto(ruta):
    try:
        datos = ruta.read_bytes()
    except OSError:
        return None
    if b"\0" in datos[:4096]:
        return None  # binario
    return datos.decode("utf-8", errors="replace")


def filtrar_rutas(rutas_rel, filtros):
    if not filtros:
        return rutas_rel
    return [r for r in rutas_rel if any(r == f or r.startswith(f.rstrip("/") + "/") for f in filtros)]


def diff_desde_git(carpeta, base, filtros):
    punto = git(carpeta, "merge-base", base, "HEAD", permitir_error=True)
    punto = punto.strip() if punto else base
    args = ["diff", "--no-color", "--no-ext-diff", "-U3", "-M", punto]
    if filtros:
        args += ["--", *filtros]
    texto = git(carpeta, *args)
    nuevos = [l for l in git(carpeta, "ls-files", "--others", "--exclude-standard").splitlines() if l.strip()]
    nuevos = [n for n in filtrar_rutas(nuevos, filtros) if not n.startswith(CARPETA_SALIDA + "/")]
    extra = []
    for n in nuevos:
        contenido = leer_texto(carpeta / n)
        if contenido is not None:
            extra.append(diff_archivo_nuevo(n, contenido))
    if extra:
        texto = texto + ("" if texto.endswith("\n") or not texto else "\n") + "".join(extra)
    return texto, punto, nuevos


def diff_desde_pr(carpeta, numero):
    if not shutil.which("gh"):
        raise RuntimeError("no encontré gh (GitHub CLI). Instálalo desde cli.github.com o usa el modo rama/carpeta")
    p = subprocess.run(["gh", "pr", "diff", str(numero), "--color", "never"], cwd=carpeta, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError("gh pr diff falló: " + p.stderr.decode("utf-8", errors="replace").strip())
    info = subprocess.run(["gh", "pr", "view", str(numero), "--json", "title,baseRefName,headRefName,url,author"],
                          cwd=carpeta, capture_output=True)
    datos = json.loads(info.stdout.decode("utf-8", errors="replace") or "{}") if info.returncode == 0 else {}
    return p.stdout.decode("utf-8", errors="replace"), datos


def diff_desde_carpeta(carpeta, filtros):
    partes = []
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = sorted(d for d in dirs if d not in IGNORAR_DIRS and not d.startswith("."))
        for a in sorted(archivos):
            ruta = Path(raiz) / a
            if ruta.suffix.lower() not in EXT_TEXTO and a not in ("Dockerfile", "Makefile"):
                continue
            rel = ruta.relative_to(carpeta).as_posix()
            if filtros and not filtrar_rutas([rel], filtros):
                continue
            contenido = leer_texto(ruta)
            if contenido:
                partes.append(diff_archivo_nuevo(rel, contenido))
    return "".join(partes)


def resumen_diff(texto):
    """Devuelve {ruta: [agregadas, quitadas]} contando líneas + y - de cada archivo."""
    archivos, actual = {}, None
    for linea in texto.splitlines():
        if linea.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", linea)
            actual = m.group(2) if m else None
            if actual:
                archivos.setdefault(actual, [0, 0])
        elif linea.startswith("+++ ") or linea.startswith("--- "):
            continue
        elif actual and linea.startswith("+"):
            archivos[actual][0] += 1
        elif actual and linea.startswith("-"):
            archivos[actual][1] += 1
    return archivos


def propuesta_particion(archivos):
    grupos = {}
    for ruta, (mas, menos) in archivos.items():
        clave = ruta.split("/")[0] if "/" in ruta else "(raíz)"
        grupos.setdefault(clave, [0, []])
        grupos[clave][0] += mas + menos
        grupos[clave][1].append(ruta)
    return sorted(grupos.items(), key=lambda g: -g[1][0])


# ------------------------------------------------------------------ herramientas del proyecto
def leer(carpeta, nombre):
    ruta = carpeta / nombre
    return ruta.read_text(encoding="utf-8", errors="replace") if ruta.is_file() else ""


def modulo_disponible(python, modulo):
    p = subprocess.run([python, "-c", f"import {modulo}"], capture_output=True)
    return p.returncode == 0


def detectar_herramientas(carpeta, python, archivos_cambiados):
    """Lista de (nombre, tipo, comando o None, motivo si no se puede ejecutar)."""
    plan = []
    config_py = leer(carpeta, "pyproject.toml") + leer(carpeta, "setup.cfg") + leer(carpeta, "tox.ini") + \
        leer(carpeta, "pytest.ini") + leer(carpeta, "requirements.txt") + leer(carpeta, "requirements-dev.txt")
    py_cambiados = [a for a in archivos_cambiados if a.endswith(".py") and (carpeta / a).is_file()]
    hay_python = bool(py_cambiados) or any((carpeta / n).exists() for n in ("pyproject.toml", "setup.py", "requirements.txt"))
    if hay_python:
        pruebas_py = [p for p in carpeta.rglob("test*.py") if not (set(p.relative_to(carpeta).parts) & IGNORAR_DIRS)]
        usa_pytest = "pytest" in config_py or (carpeta / "conftest.py").exists()
        if usa_pytest and modulo_disponible(python, "pytest"):
            plan.append(("pytest", "pruebas", [python, "-m", "pytest", "-q"], None))
        elif pruebas_py:
            inicio = "tests" if (carpeta / "tests").is_dir() else "."
            nota = "el proyecto usa pytest pero no está instalado; se corrió unittest" if usa_pytest else None
            plan.append(("unittest", "pruebas", [python, "-m", "unittest", "discover", "-s", inicio, "-v"], nota))
        else:
            plan.append(("pruebas de Python", "pruebas", None, "no encontré archivos test*.py: el proyecto no tiene pruebas"))
        if py_cambiados:
            revisa = "import sys; [compile(open(f, encoding='utf-8-sig').read(), f, 'exec') for f in sys.argv[1:]]"
            plan.append(("compilación de Python", "sintaxis", [python, "-c", revisa, *py_cambiados], None))
        if shutil.which("ruff") or modulo_disponible(python, "ruff"):
            cmd = ["ruff"] if shutil.which("ruff") else [python, "-m", "ruff"]
            plan.append(("ruff", "estilo", cmd + ["check", *(py_cambiados or ["."])], None))
        elif "flake8" in config_py and modulo_disponible(python, "flake8"):
            plan.append(("flake8", "estilo", [python, "-m", "flake8", *(py_cambiados or ["."])], None))
        else:
            plan.append(("ruff / flake8", "estilo", None, "no está instalado (no se instala nada sin tu permiso)"))
        if re.search(r"\[(tool\.)?mypy\]", config_py) or (carpeta / "mypy.ini").exists():
            if modulo_disponible(python, "mypy"):
                plan.append(("mypy", "tipos", [python, "-m", "mypy", *(py_cambiados or ["."])], None))
            else:
                plan.append(("mypy", "tipos", None, "está configurado pero no instalado"))
    pkg_txt = leer(carpeta, "package.json")
    if pkg_txt:
        try:
            scripts = json.loads(pkg_txt).get("scripts", {}) or {}
        except json.JSONDecodeError:
            scripts = {}
        npm = shutil.which("npm")
        sin_modulos = not (carpeta / "node_modules").is_dir()
        motivo_npm = "no encontré npm" if not npm else ("falta node_modules: corre «npm install» tú (no se instala nada sin permiso)" if sin_modulos else None)
        test = scripts.get("test", "")
        if test and "no test specified" not in test:
            plan.append(("npm test", "pruebas", None if motivo_npm else [npm, "test", "--silent"], motivo_npm))
        else:
            plan.append(("npm test", "pruebas", None, "package.json no tiene un script «test» real: el proyecto no tiene pruebas"))
        if "lint" in scripts:
            plan.append(("npm run lint", "estilo", None if motivo_npm else [npm, "run", "lint", "--silent"], motivo_npm))
        elif any((carpeta / n).exists() for n in ("eslint.config.js", "eslint.config.mjs", ".eslintrc.json", ".eslintrc.js", ".eslintrc.cjs")):
            js = [a for a in archivos_cambiados if re.search(r"\.(m?js|cjs|jsx|tsx?)$", a) and (carpeta / a).is_file()]
            local = carpeta / "node_modules" / ".bin" / ("eslint.cmd" if os.name == "nt" else "eslint")
            plan.append(("eslint", "estilo", [str(local), *(js or ["."])] if local.exists() else None,
                         None if local.exists() else "eslint no está instalado en node_modules"))
        tipo = next((s for s in ("typecheck", "type-check", "tsc") if s in scripts), None)
        if tipo:
            plan.append((f"npm run {tipo}", "tipos", None if motivo_npm else [npm, "run", tipo, "--silent"], motivo_npm))
        elif (carpeta / "tsconfig.json").exists():
            local = carpeta / "node_modules" / ".bin" / ("tsc.cmd" if os.name == "nt" else "tsc")
            plan.append(("tsc --noEmit", "tipos", [str(local), "--noEmit"] if local.exists() else None,
                         None if local.exists() else "typescript no está instalado en node_modules"))
    if (carpeta / "go.mod").exists():
        go = shutil.which("go")
        plan.append(("go test", "pruebas", [go, "test", "./..."] if go else None, None if go else "no encontré go"))
        plan.append(("go vet", "estilo", [go, "vet", "./..."] if go else None, None if go else "no encontré go"))
    if (carpeta / "Cargo.toml").exists():
        cargo = shutil.which("cargo")
        plan.append(("cargo test", "pruebas", [cargo, "test"] if cargo else None, None if cargo else "no encontré cargo"))
    return plan


def correr(plan, carpeta, bitacora):
    resultados = []
    for nombre, tipo, cmd, nota in plan:
        if cmd is None:
            estado, cola = "NO EJECUTADO", [nota]
            nota = None
        else:
            try:
                entorno = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}  # no dejar __pycache__ en tu proyecto
                p = subprocess.run(cmd, cwd=carpeta, capture_output=True, timeout=900, env=entorno)
                salida = (p.stdout + p.stderr).decode("utf-8", errors="replace")
                estado = "PASA" if p.returncode == 0 else "FALLA"
                cola = [l for l in salida.strip().splitlines() if l.strip()][-12:]
                bitacora.append(f"$ {' '.join(cmd)}\n(código {p.returncode})\n{salida}\n")
            except subprocess.TimeoutExpired:
                estado, cola = "FALLA", ["tardó más de 15 minutos"]
            except OSError as e:
                estado, cola = "NO EJECUTADO", [f"no se pudo ejecutar: {e}"]
        resultados.append({"herramienta": nombre, "tipo": tipo, "estado": estado,
                           "comando": " ".join(cmd) if cmd else None, "nota": nota, "salida_final": cola})
        print(f"  [{estado}] {nombre} ({tipo})" + (f": {cola[0]}" if estado == "NO EJECUTADO" else ""))
        if nota:
            print(f"      nota: {nota}")
        if estado == "FALLA":
            for c in cola[-6:]:
                print(f"      {c}")
    return resultados


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    modo = ap.add_mutually_exclusive_group()
    modo.add_argument("--base", help="rama o commit contra el que se compara (por defecto la rama principal)")
    modo.add_argument("--pr", help="número de pull request de GitHub (usa gh pr diff)")
    modo.add_argument("--carpeta", dest="sin_git", action="store_true", help="revisar todos los archivos, sin git")
    ap.add_argument("--rutas", help="solo estas rutas, separadas por coma (para revisar por partes)")
    ap.add_argument("--sin-ejecutar", action="store_true", help="no correr pruebas ni revisores")
    ap.add_argument("--python", default=sys.executable, help="intérprete de Python para las pruebas (por defecto, este)")
    a = ap.parse_args()

    carpeta = Path(a.carpeta).resolve()
    if not carpeta.is_dir():
        print(f"FALLA: no existe la carpeta {carpeta}")
        return 2
    filtros = [f.strip().replace("\\", "/") for f in (a.rutas or "").split(",") if f.strip()]
    contexto = {"proyecto": str(carpeta), "rutas": filtros or None}
    nuevos = []
    try:
        if a.pr:
            texto, datos = diff_desde_pr(carpeta, a.pr)
            contexto.update(modo="pull request", pr=a.pr, titulo=datos.get("title"), base=datos.get("baseRefName"),
                            rama=datos.get("headRefName"), url=datos.get("url"))
            actual = (git(carpeta, "branch", "--show-current", permitir_error=True) or "").strip()
            contexto["pr_en_copia_local"] = bool(actual) and actual == datos.get("headRefName")
        elif a.sin_git or not es_repo(carpeta):
            if not a.sin_git:
                print("Aviso: la carpeta no es un repositorio git; se revisan todos sus archivos (modo carpeta).")
            texto = diff_desde_carpeta(carpeta, filtros)
            contexto.update(modo="carpeta", base=None, rama=None)
        else:
            base = a.base or detectar_base(carpeta)
            if not base:
                print("FALLA: no pude detectar la rama base (main/master). Indícala con --base NOMBRE o --base HEAD~1")
                return 2
            rama = (git(carpeta, "branch", "--show-current", permitir_error=True) or "").strip() or "(sin rama)"
            texto, punto, nuevos = diff_desde_git(carpeta, base, filtros)
            contexto.update(modo="rama", base=base, rama=rama, desde_commit=punto, archivos_nuevos_sin_seguir=nuevos)
    except RuntimeError as e:
        print(f"FALLA: {e}")
        return 2

    archivos = resumen_diff(texto)
    if not archivos:
        print("No hay cambios que revisar.")
        if contexto.get("modo") == "rama":
            print(f"Tu rama «{contexto['rama']}» no tiene diferencias con «{contexto['base']}». "
                  "Si quieres revisar tu último commit, usa --base HEAD~1.")
        return 1

    salida = carpeta / CARPETA_SALIDA
    salida.mkdir(exist_ok=True)
    (salida / ".gitignore").write_text("# Carpeta de trabajo de la revisión: git la ignora.\n*\n", encoding="utf-8")
    (salida / "cambio.diff").write_text(texto, encoding="utf-8", newline="\n")

    total = sum(m + q for m, q in archivos.values())
    print(f"== Cambio a revisar ({contexto['modo']})")
    if contexto.get("base"):
        print(f"  Base: {contexto['base']}  ·  Rama: {contexto.get('rama')}")
    if contexto.get("titulo"):
        print(f"  Pull request #{a.pr}: {contexto['titulo']}")
    print(f"  {len(archivos)} archivos, {total} líneas cambiadas (+ agregadas / - quitadas):")
    for ruta, (mas, menos) in sorted(archivos.items()):
        marca = "  (nuevo, sin commit)" if ruta in nuevos else ""
        print(f"    {ruta}: +{mas} -{menos}{marca}")
    contexto.update(archivos={r: {"agregadas": m, "quitadas": q} for r, (m, q) in archivos.items()},
                    lineas_cambiadas=total, grande=total > LIMITE_LINEAS)
    if total > LIMITE_LINEAS:
        print(f"\n  AVISO: son más de {LIMITE_LINEAS} líneas. Una revisión pierde atención con cambios tan grandes.")
        print("  Propuesta para revisar por partes (vuelve a correr con --rutas):")
        for grupo, (lineas, rutas) in propuesta_particion(archivos):
            print(f"    --rutas {grupo + '/' if grupo != '(raíz)' else ','.join(rutas)}  ({lineas} líneas)")

    resultados = []
    if a.sin_ejecutar:
        print("\n== Pruebas y revisores: NO ejecutados (--sin-ejecutar)")
    elif contexto["modo"] == "pull request" and not contexto.get("pr_en_copia_local"):
        print("\n== Pruebas y revisores: NO ejecutados")
        print(f"  El pull request no está en tu copia local (rama «{contexto.get('rama')}»). Para correrlas,"
              f" primero «gh pr checkout {a.pr}» (con tu permiso) y repite.")
        resultados = [{"herramienta": "pruebas del proyecto", "tipo": "pruebas", "estado": "NO EJECUTADO",
                       "comando": None, "nota": None, "salida_final": ["el pull request no está en la copia local"]}]
    else:
        print("\n== Pruebas y revisores del proyecto (resultado real)")
        bitacora = []
        resultados = correr(detectar_herramientas(carpeta, a.python, list(archivos)), carpeta, bitacora)
        (salida / "herramientas.log").write_text("\n".join(bitacora) or "(no se ejecutó ningún comando)\n",
                                                 encoding="utf-8")
    (salida / "herramientas.json").write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    (salida / "contexto.json").write_text(json.dumps(contexto, ensure_ascii=False, indent=2), encoding="utf-8")

    fallan = [r["herramienta"] for r in resultados if r["estado"] == "FALLA"]
    sin = [r["herramienta"] for r in resultados if r["estado"] == "NO EJECUTADO"]
    print(f"\nArchivos en {salida}: cambio.diff, contexto.json, herramientas.json" +
          (", herramientas.log" if resultados and not a.sin_ejecutar else ""))
    print("ESTADO: LISTO PARA REVISAR (" + f"{len(archivos)} archivos, {total} líneas; " +
          (f"fallan: {', '.join(fallan)}; " if fallan else "") +
          (f"sin ejecutar: {', '.join(sin)}" if sin else "todo lo detectado se ejecutó") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
