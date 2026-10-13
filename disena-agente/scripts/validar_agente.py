"""Valida el archivo de un agente de Claude Code antes de entregarlo.

Uso: python validar_agente.py <agente.md> --permitidas Read,Glob,Write
Comprueba: encabezado con name/description/tools, nombre válido, lista de herramientas explícita y
dentro de las permitidas por el mapa de la tarea, secciones obligatorias, barandales concretos y
aprobación humana que diga cuándo se detiene si hay herramientas de riesgo. Sale con código 0 si PASA
y 1 si FALLA. Solo biblioteca estándar.
"""
import re
import sys

SECCIONES = ["Objetivo", "Entradas", "Proceso", "Barandales", "Aprobación humana", "Entrega", "Terminado cuando"]
RIESGOSAS = {"Bash", "PowerShell", "Edit", "WebFetch", "WebSearch", "NotebookEdit", "Agent", "Task", "Skill"}
VERBOS_PAUSA = re.compile(r"\b(detiene|det[eé]n|pide|pregunta|espera|aprobaci[oó]n|aprueba|confirma)", re.I)


def campos_cabecera(cabecera: str) -> dict:
    """Lee `clave: valor`, listas YAML (`- Read`) y bloques plegados (`>` o `|`)."""
    campos, clave = {}, None
    for linea in cabecera.splitlines():
        m = re.match(r"^(\w+):\s*(.*)$", linea)
        if m:
            clave, valor = m.group(1), m.group(2).strip()
            campos[clave] = "" if valor in (">", "|", ">-", "|-") else valor
        elif clave and linea.strip():
            extra = linea.strip()
            sep = ", " if extra.startswith("- ") else " "
            campos[clave] = (campos[clave] + sep + extra.removeprefix("- ")).strip(", ")
    return campos


def validar(ruta: str, permitidas: set[str]) -> list[str]:
    texto = open(ruta, encoding="utf-8-sig").read()  # utf-8-sig: tolera el BOM de PowerShell
    errores = []
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", texto.replace("\r\n", "\n"), re.S)
    if not m:
        return ["falta el encabezado entre líneas --- (name, description, tools)"]
    campos, cuerpo = campos_cabecera(m.group(1)), m.group(2)
    cuerpo_sin_codigo = re.sub(r"```.*?```", "", cuerpo, flags=re.S)  # las secciones dentro de un bloque de código no cuentan
    for c in ("name", "description", "tools"):
        if not campos.get(c, "").strip():
            errores.append(f"falta «{c}» en el encabezado" + (" (sin lista, el agente hereda TODAS las herramientas)" if c == "tools" else ""))
    if campos.get("name") and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", campos["name"].strip()):
        errores.append("«name» debe ir en minúsculas con guiones (p. ej. resume-pedidos)")
    herramientas = {h.strip() for h in campos.get("tools", "").split(",") if h.strip()}
    if "*" in herramientas:
        errores.append("«tools: *» da TODAS las herramientas: lista solo las que exige el mapa")
    extra = herramientas - permitidas - {"*"}
    if extra:
        errores.append(f"herramientas fuera del mapa de la tarea: {', '.join(sorted(extra))}")
    titulos = {t.strip() for t in re.findall(r"^##\s+(.+)$", cuerpo_sin_codigo, re.M)}
    for s in SECCIONES:
        if s not in titulos:
            errores.append(f"falta la sección «## {s}»")
    seccion = lambda nombre: (re.search(rf"^##\s+{nombre}\s*\n(.*?)(?=^##\s|\Z)", cuerpo_sin_codigo, re.S | re.M) or [None, ""])[1]
    limites = [l for l in re.findall(r"^\s*(?:[-*]|\d+\.)\s+(.+)$", seccion("Barandales"), re.M) if len(l.split()) >= 4]
    if "Barandales" in titulos and len(limites) < 2:
        errores.append("«Barandales» necesita al menos 2 límites concretos (frases de 4 palabras o más)")
    riesgosas = {h for h in herramientas if h in RIESGOSAS or h.startswith("mcp__")}
    aprobacion = seccion("Aprobación humana")
    if riesgosas and "Aprobación humana" in titulos and not VERBOS_PAUSA.search(aprobacion):
        errores.append(f"usa {', '.join(sorted(riesgosas))} pero «Aprobación humana» no dice cuándo se detiene y pide permiso")
    return errores


if __name__ == "__main__":
    if len(sys.argv) < 2 or "--permitidas" not in sys.argv:
        print(__doc__)
        print("FALLA: indica el archivo del agente y --permitidas con las herramientas del mapa de la tarea")
        sys.exit(2)
    permitidas = {h.strip() for h in sys.argv[sys.argv.index("--permitidas") + 1].split(",") if h.strip()}
    errores = validar(sys.argv[1], permitidas)
    if errores:
        print("FALLA")
        for e in errores:
            print(" -", e)
        sys.exit(1)
    print("PASA: encabezado, herramientas, secciones, barandales y aprobación humana en orden")
