#!/usr/bin/env python3
"""Valida los workflows de GitHub Actions de un proyecto y prueba sus comandos en tu computadora.

Hecho por Lumière Autómata (skill «publica-solo»). Solo usa la biblioteca estándar de Python.

Uso:
    python validar_workflow.py CARPETA_DEL_PROYECTO                 # validar
    python validar_workflow.py CARPETA_DEL_PROYECTO --ejecutar pruebas   # además, correr los comandos del job «pruebas»

Qué hace:
  1. Sintaxis: tabuladores, YAML (con PyYAML si está instalado) y estructura (on, jobs, runs-on, steps).
  2. Reglas de seguridad y buenas prácticas (acciones con versión, permisos, secretos, inyección).
  3. Lista los secretos de GitHub que el workflow necesita (solo nombres).
  4. actionlint, si está instalado (si no, lo dice).
  5. Con --ejecutar JOB: ejecuta aquí, uno por uno, los comandos «run:» de ese job y muestra su resultado real.
     Los pasos con expresiones ${{ }} no se pueden ejecutar fuera de GitHub: se listan como «no ejecutado».

La última línea es siempre  ESTADO: ... y dice con precisión qué se comprobó.
Código de salida: 0 = sin fallas, 1 = hay fallas.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

SECRETO_NOMBRE = r"(PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|PRIVATE_?KEY|CREDENTIAL)"
resultados = []


def anota(nivel, msg):
    resultados.append((nivel, msg))
    print(f"  [{nivel}] {msg}")


def sangria(linea):
    return len(linea) - len(linea.lstrip(" "))


# ------------------------------------------------------------ análisis de texto
def analiza(texto):
    """Extrae jobs, pasos, acciones y comandos con un recorrido por líneas (sin depender de PyYAML)."""
    lineas = texto.splitlines()
    info = {"on": False, "permissions": False, "jobs": {}, "uses": [], "secrets": set(), "lineas": lineas}
    en_jobs = False
    job = None
    i = 0
    while i < len(lineas):
        l = lineas[i]
        s = l.strip()
        if not s or s.startswith("#"):
            i += 1
            continue
        if sangria(l) == 0:
            en_jobs = s == "jobs:"
            if re.match(r"""^("?on"?|'on')\s*:""", s):
                info["on"] = True
            if s.startswith("permissions:"):
                info["permissions"] = True
            job = None
        elif en_jobs and sangria(l) == 2 and re.match(r"^[\w-]+:\s*$", s):
            job = s[:-1]
            info["jobs"][job] = {"runs-on": False, "steps": False, "needs": None, "if": None,
                                 "comandos": [], "versiones": {}, "linea": i + 1}
        elif job:
            j = info["jobs"][job]
            if re.match(r"runs-on:", s):
                j["runs-on"] = True
            if re.match(r"steps:\s*$", s):
                j["steps"] = True
            m = re.match(r"needs:\s*(.*)", s)
            if m:
                j["needs"] = m.group(1) or "(lista)"
            if re.match(r"if:", s) and sangria(l) == 4:
                j["if"] = s
            m = re.match(r"-?\s*uses:\s*(\S+)", s)
            if m:
                info["uses"].append((job, m.group(1).strip("'\""), i + 1))
            m = re.match(r"(node|python|go|java|ruby)-version:\s*(.+)", s)
            if m:
                j["versiones"][m.group(1)] = m.group(2).strip().strip("'\"")
            m = re.match(r"(-\s*)?run:\s*(.*)$", s)
            if m:
                base = l.index("run:")
                valor = m.group(2).strip()
                if valor in ("|", "|-", "|+", ">", ">-", ">+"):
                    bloque = []
                    i += 1
                    while i < len(lineas) and (not lineas[i].strip() or sangria(lineas[i]) > base):
                        bloque.append(lineas[i])
                        i += 1
                    quita = min([sangria(b) for b in bloque if b.strip()] or [0])
                    cmd = "\n".join(b[quita:] for b in bloque).strip("\n")
                    j["comandos"].append((cmd, i - len(bloque) + 1))
                    continue
                j["comandos"].append((valor.strip("'\""), i + 1))
        for sec in re.findall(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}", l):
            info["secrets"].add(sec)
        i += 1
    return info


# ------------------------------------------------------------ revisión de un archivo
def valida_archivo(ruta, carpeta):
    print(f"\n== {ruta.relative_to(carpeta)}")
    texto = ruta.read_text(encoding="utf-8", errors="replace")
    if "\t" in texto:
        anota("FALLA", "Hay tabuladores: YAML solo admite espacios para sangrar")
    try:
        import yaml  # opcional
        try:
            datos = yaml.safe_load(texto)
            if isinstance(datos, dict):
                anota("OK", "YAML válido (analizado con PyYAML)")
            else:
                anota("FALLA", "El YAML no es un diccionario (¿archivo vacío o mal sangrado?)")
        except Exception as e:
            anota("FALLA", f"YAML inválido: {str(e).splitlines()[0]}")
    except ImportError:
        anota("AVISO", "PyYAML no está instalado: el YAML no se analizó con un parser; solo con la revisión de estructura "
                       "de este script. (pip install pyyaml, o usa actionlint)")
    info = analiza(texto)
    anota("OK" if info["on"] else "FALLA", "Define cuándo corre (on:)" if info["on"] else "Falta «on:» (cuándo se ejecuta)")
    if not info["jobs"]:
        anota("FALLA", "No se encontraron jobs bajo «jobs:»")
    for nombre, j in info["jobs"].items():
        if not j["runs-on"]:
            anota("FALLA", f"El job «{nombre}» no tiene runs-on")
        if not j["steps"]:
            anota("FALLA", f"El job «{nombre}» no tiene steps")
        if j["runs-on"] and j["steps"]:
            anota("OK", f"Job «{nombre}»: runs-on y steps presentes ({len(j['comandos'])} comandos run)")
        if re.search(r"deploy|despl[ie]g|release|publish|publica", nombre, re.I):
            if not j["needs"]:
                anota("AVISO", f"El job de despliegue «{nombre}» no depende (needs) de las pruebas: se desplegaría aunque fallen")
            if not j["if"]:
                anota("AVISO", f"El job de despliegue «{nombre}» no tiene if: (¿solo en main?): se desplegaría desde ramas y pull requests")
    if info["permissions"]:
        anota("OK", "Declara permissions (principio de mínimo privilegio)")
    else:
        anota("AVISO", "Sin «permissions:»: el token del workflow tendría más permisos de los necesarios")
    for job, uso, n in info["uses"]:
        if uso.startswith("./") or uso.startswith("docker://"):
            continue
        if "@" not in uso:
            anota("FALLA", f"Línea {n}: la acción {uso} no fija versión (usa @vN)")
        elif uso.split("@", 1)[1] in ("main", "master", "latest"):
            anota("FALLA", f"Línea {n}: {uso} apunta a una rama móvil; fija una versión (@vN)")
        elif not uso.startswith(("actions/", "github/")):
            anota("AVISO", f"Línea {n}: {uso} es de un tercero; revisa que confíes en él")
    texto_sin_comentarios = "\n".join(l for l in info["lineas"] if not l.strip().startswith("#"))
    literales = [re.sub(r"[:=]\s*\S.*$", "", l.strip().lstrip("- ")) for l in info["lineas"]
                 if re.match(rf"\s*-?\s*[\w.-]*{SECRETO_NOMBRE}[\w.-]*\s*[:=]\s*[^\s$#{{]", l, re.I)
                 and not l.strip().startswith("#")]
    if literales:
        anota("FALLA", f"Posible secreto escrito en el workflow: variable {literales[0]} (valor oculto). Usa ${{{{ secrets.NOMBRE }}}}")
    patrones = [(r"ghp_[A-Za-z0-9]{20,}", "token de GitHub"), (r"AKIA[0-9A-Z]{16}", "clave de AWS"),
                (r"-----BEGIN [A-Z ]*PRIVATE KEY", "llave privada"), (r"\bsk-[A-Za-z0-9]{20,}", "clave de API"),
                (r"xox[baprs]-[A-Za-z0-9-]{10,}", "token de Slack")]
    hallados = [n for p, n in patrones if re.search(p, texto_sin_comentarios)]
    if hallados:
        anota("FALLA", f"El archivo contiene algo con forma de {', '.join(hallados)} (valor oculto)")
    if not literales and not hallados:
        anota("OK", "Ningún secreto escrito en el workflow")
    if re.search(r"echo[^\n]*\$\{\{\s*secrets\.", texto_sin_comentarios):
        anota("FALLA", "Un comando hace echo de un secreto (saldría en los registros)")
    if re.search(r"pull_request_target", texto_sin_comentarios):
        anota("AVISO", "Usa pull_request_target: corre con permisos de escritura sobre código ajeno; evítalo salvo que sepas por qué")
    for j in info["jobs"].values():
        for cmd, n in j["comandos"]:
            if re.search(r"\$\{\{\s*github\.event\.(issue|pull_request|comment|review|head_commit)[\w.]*"
                         r"(title|body|name|message|ref|label)", cmd):
                anota("FALLA", f"Línea {n}: inyección de comandos: un dato escrito por otras personas va directo a un comando "
                               "(pásalo por una variable env:)")
    if info["secrets"]:
        print(f"  Secretos de GitHub que usa (solo nombres): {', '.join(sorted(info['secrets']))}")
    return info


def actionlint(carpeta):
    exe = shutil.which("actionlint")
    if not exe:
        anota("AVISO", "actionlint no está instalado: no se corrió (es opcional; github.com/rhysd/actionlint)")
        return "no disponible"
    p = subprocess.run([exe], cwd=carpeta, capture_output=True, text=True)
    print((p.stdout + p.stderr).strip() or "  (sin hallazgos)")
    if p.returncode == 0:
        anota("OK", "actionlint: sin hallazgos")
        return "OK"
    anota("FALLA", "actionlint reportó problemas (ver arriba)")
    return "con hallazgos"


def versiones_locales(info):
    pedidas = {}
    for j in info["jobs"].values():
        pedidas.update(j["versiones"])
    cmds = {"node": ["node", "--version"], "python": [sys.executable, "--version"], "go": ["go", "version"]}
    for lang, v in pedidas.items():
        if lang in cmds:
            try:
                p = subprocess.run(cmds[lang], capture_output=True, text=True)
                print(f"  Versión de {lang}: el workflow pide {v}; aquí hay {(p.stdout + p.stderr).strip()}")
            except OSError:
                print(f"  Versión de {lang}: el workflow pide {v}; aquí no está instalado")


def adapta_python(cmd, interprete):
    """En Windows «python» y «pip» a veces no están en el PATH: usa el intérprete que sí existe."""
    if not interprete:
        return cmd
    ruta = '"' + interprete.replace("\\", "/") + '"'
    cmd = re.sub(r"(^|&&|\|\||;|\|)(\s*)(python3?|py)(?=\s|$)", lambda m: f"{m.group(1)}{m.group(2)}{ruta}", cmd, flags=re.M)
    cmd = re.sub(r"(^|&&|\|\||;|\|)(\s*)pip3?(?=\s|$)", lambda m: f"{m.group(1)}{m.group(2)}{ruta} -m pip", cmd, flags=re.M)
    return cmd


def ejecuta_job(info, job, carpeta, python=None):
    """Corre los comandos run: de un job. Devuelve (ejecutados, fallidos, no_ejecutados)."""
    if job not in info["jobs"]:
        anota("FALLA", f"No existe el job «{job}» (hay: {', '.join(info['jobs'])})")
        return 0, 1, 0
    bash = shutil.which("bash")
    ok = mal = salto = 0
    print(f"\n== Ejecutando en esta computadora los comandos del job «{job}»")
    versiones_locales(info)
    interprete = python or (None if shutil.which("python") and shutil.which("pip") else sys.executable)
    if interprete:
        print(f"  Nota: «python»/«pip» no están en el PATH (o se indicó --python); se usa {interprete}")
    for cmd, n in info["jobs"][job]["comandos"]:
        cmd = adapta_python(cmd, interprete)
        resumen = cmd.splitlines()[0] if cmd else ""
        if "${{" in cmd:
            print(f"  [NO EJECUTADO] línea {n}: «{resumen}» usa una expresión de GitHub (${{{{ }}}})")
            salto += 1
            continue
        print(f"  $ {resumen}{'  (+ más líneas)' if len(cmd.splitlines()) > 1 else ''}")
        try:
            if bash:
                p = subprocess.run([bash, "-e", "-c", cmd], cwd=carpeta, capture_output=True, text=True, timeout=900)
            else:
                p = subprocess.run(cmd, cwd=carpeta, capture_output=True, text=True, shell=True, timeout=900)
        except subprocess.TimeoutExpired:
            anota("FALLA", f"línea {n}: el comando tardó más de 15 minutos")
            mal += 1
            continue
        cola = (p.stdout + p.stderr).strip().splitlines()[-6:]
        for c in cola:
            print(f"      {c}")
        if p.returncode == 0:
            anota("OK", f"línea {n}: terminó con código 0")
            ok += 1
        else:
            anota("FALLA", f"línea {n}: terminó con código {p.returncode}")
            mal += 1
    return ok, mal, salto


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure") and not flujo.isatty():
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta")
    ap.add_argument("--ejecutar", metavar="JOB", help="corre aquí los comandos run: de ese job")
    ap.add_argument("--python", metavar="RUTA", help="intérprete de Python a usar para «python» y «pip» (por defecto, el que ejecuta este script si no hay otro en el PATH)")
    a = ap.parse_args()
    carpeta = Path(a.carpeta).resolve()
    archivos = sorted(list((carpeta / ".github" / "workflows").glob("*.yml")) +
                      list((carpeta / ".github" / "workflows").glob("*.yaml")))
    if not archivos:
        print("No hay archivos en .github/workflows/")
        print("ESTADO: FALLÓ (no hay workflow que validar)")
        return 1
    infos = {r: valida_archivo(r, carpeta) for r in archivos}
    print("\n== actionlint")
    al = actionlint(carpeta)
    ejecutados = None
    if a.ejecutar:
        objetivo = next((i for i in infos.values() if a.ejecutar in i["jobs"]), None)
        if objetivo is None:
            anota("FALLA", f"Ningún workflow tiene el job «{a.ejecutar}»")
        else:
            ejecutados = ejecuta_job(objetivo, a.ejecutar, carpeta, a.python)
    fallas = [m for n, m in resultados if n == "FALLA"]
    avisos = [m for n, m in resultados if n == "AVISO"]
    print(f"\n== Resumen: {len([1 for n, _ in resultados if n == 'OK'])} OK, {len(avisos)} avisos, {len(fallas)} fallas")
    hay_yaml = True
    try:
        import yaml  # noqa: F401
    except ImportError:
        hay_yaml = False
    partes = [f"YAML {'analizado con parser' if hay_yaml else 'NO analizado con parser (solo estructura)'}",
              f"actionlint {al}"]
    if ejecutados is not None:
        partes.append(f"comandos de «{a.ejecutar}»: {ejecutados[0]} OK, {ejecutados[1]} fallidos, {ejecutados[2]} no ejecutados")
    else:
        partes.append("comandos locales NO ejecutados")
    estado = "FALLÓ" if fallas else "VALIDADO"
    print("ESTADO: " + estado + " (" + "; ".join(partes) + "; el workflow NO se ha ejecutado en GitHub todavía)")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
