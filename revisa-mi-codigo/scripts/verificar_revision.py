#!/usr/bin/env python3
"""Comprueba una revisión de código contra el cambio real antes de entregarla.

Hecho por Lumière Autómata (skill «revisa-mi-codigo»). Solo biblioteca estándar, Python 3.10+.

Uso:
    python verificar_revision.py CARPETA_REVISION
        (la carpeta revision-codigo/ que crea preparar_revision.py: lee revision-codigo.md, cambio.diff,
         herramientas.json y contexto.json)
    python verificar_revision.py --diff cambio.diff --revision revision-codigo.md [--repo CARPETA]
                                 [--herramientas herramientas.json]
    (la revisión puede ser .md con el formato de la plantilla o .json)

Qué comprueba:
  1. Cada comentario cita archivo:línea y esa línea existe: dentro de las líneas cambiadas (OK), en el contexto
     del cambio o fuera del diff pero en el archivo (AVISO: «contexto»), o en ningún lado (FALLA).
  2. Cada comentario tiene nivel válido (Bloquea, Sugerencia, Detalle, Bien hecho), qué ves y por qué importa;
     los que no son «Bien hecho» además traen una propuesta concreta.
  3. Hay al menos un comentario «Bien hecho».
  4. No hay frases duras («esto está mal», «obvio»…); las que minimizan («simplemente», «es fácil») son AVISO.
  5. El veredicto existe y es coherente: con un «Bloquea» o con pruebas que fallan no se puede «Aprobar».
  6. La sección de pruebas nombra cada herramienta que se ejecutó, y hay 2 o 3 lecciones para quien empieza.
La última línea dice PASA o FALLA. Código de salida: 0 = PASA, 1 = FALLA, 2 = error de uso.
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

NIVELES = {"bloquea": "Bloquea", "sugerencia": "Sugerencia", "detalle": "Detalle", "bien hecho": "Bien hecho"}
VEREDICTOS = {"aprobar": "Aprobar", "aprobar con cambios": "Aprobar con cambios", "necesita cambios": "Necesita cambios"}
FRASES_DURAS = ["esto esta mal", "esta mal hecho", "esta fatal", "obvio", "obviamente", "cualquiera sabe",
                "es basico", "no sabes", "no entiendes", "hiciste mal", "te equivocaste", "que flojera",
                "horrible", "basura", "porqueria", "tonto", "tonteria", "estupido", "ridiculo", "pesimo",
                "inaceptable", "como se te ocurre", "error de novato",
                "nunca jamas", "deberias saber"]
FRASES_MINIMIZAN = ["simplemente", "solo tienes que", "nada mas tienes que", "es facil", "es trivial", "facilisimo"]
CAMPOS = {"que veo": "que", "que hace": "que", "por que importa": "porque", "por que": "porque",
          "propuesta": "propuesta", "sugerencia concreta": "propuesta"}


def normal(texto):
    t = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ------------------------------------------------------------------ diff
def leer_diff(texto):
    """{ruta: {"cambiadas": set, "contexto": set, "borrado": bool}} con números de línea del archivo nuevo."""
    archivos, actual, nueva = {}, None, 0
    for linea in texto.splitlines():
        if linea.startswith("diff --git "):
            m = re.match(r"diff --git a/(.+?) b/(.+)$", linea)
            actual = m.group(2) if m else None
            if actual:
                archivos[actual] = {"cambiadas": set(), "contexto": set(), "borrado": False}
            continue
        if actual is None:
            continue
        if linea.startswith("+++ "):
            destino = linea[4:].strip()
            if destino == "/dev/null":
                archivos[actual]["borrado"] = True
            elif destino.startswith("b/") and destino[2:] != actual:
                archivos[destino[2:]] = archivos.pop(actual)
                actual = destino[2:]
            continue
        if linea.startswith("--- "):
            continue
        m = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", linea)
        if m:
            nueva = int(m.group(1))
            continue
        if linea.startswith("+"):
            archivos[actual]["cambiadas"].add(nueva)
            nueva += 1
        elif linea.startswith(" "):
            archivos[actual]["contexto"].add(nueva)
            nueva += 1
    return archivos


# ------------------------------------------------------------------ revisión
def campos_de(cuerpo):
    """Separa «**Qué veo:** …», «**Por qué importa:** …», «**Propuesta:** …» (en la misma línea o debajo)."""
    datos = {}
    piezas = re.split(r"^\s*[-*]?\s*\*\*([^*]+?):?\*\*:?", cuerpo, flags=re.M)
    for i in range(1, len(piezas) - 1, 2):
        clave = CAMPOS.get(normal(piezas[i]).strip().rstrip(":").strip())
        if clave:
            datos[clave] = piezas[i + 1].strip()
    return datos


def leer_revision_md(texto):
    sin_codigo = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), texto, flags=re.S)
    rev = {"veredicto": None, "comentarios": [], "errores_formato": [], "secciones": {}}
    m = re.search(r"^\s*\*{0,2}Veredicto:?\*{0,2}:?\s*\*{0,2}([^*\n]+)", sin_codigo, re.M | re.I)
    if m:
        crudo = re.split(r"\s+[—–-]\s+|[(.:;,]", m.group(1))[0]
        rev["veredicto_texto"] = crudo.strip().strip("«»\"' ")
        rev["veredicto"] = VEREDICTOS.get(normal(rev["veredicto_texto"]))
    for m in re.finditer(r"^##\s+(.+?)\s*\n(.*?)(?=^##\s|\Z)", sin_codigo, re.S | re.M):
        rev["secciones"][normal(m.group(1)).strip()] = m.group(2)
    bloques = re.split(r"^(?=###\s)", sin_codigo, flags=re.M)
    for b in bloques:
        if not b.startswith("###"):
            continue
        encabezado, _, cuerpo = b.partition("\n")
        cuerpo = re.split(r"^##\s", cuerpo, flags=re.M)[0]
        if "[" not in encabezado:
            continue
        m = re.match(r"^###\s*\[([^\]]+)\]\s*`?([^\s`]+?):(\d+)(?:-(\d+))?`?(?:\s+.*)?$", encabezado.strip())
        if not m:
            rev["errores_formato"].append(f"encabezado de comentario sin «archivo:línea» válido: «{encabezado.strip()}»")
            continue
        c = {"nivel_texto": m.group(1).strip(), "archivo": m.group(2), "desde": int(m.group(3)),
             "hasta": int(m.group(4) or m.group(3)), "texto": cuerpo}
        c.update(campos_de(cuerpo))
        rev["comentarios"].append(c)
    rev["texto_revisable"] = re.sub(r"`[^`\n]*`", "", sin_codigo)
    return rev


def leer_revision_json(texto):
    datos = json.loads(texto)
    rev = {"veredicto_texto": datos.get("veredicto", ""), "comentarios": [], "errores_formato": [], "secciones": {}}
    rev["veredicto"] = VEREDICTOS.get(normal(rev["veredicto_texto"] or ""))
    partes = [rev["veredicto_texto"] or ""]
    for i, c in enumerate(datos.get("comentarios", []), 1):
        linea = str(c.get("linea", ""))
        m = re.fullmatch(r"(\d+)(?:-(\d+))?", linea)
        if not c.get("archivo") or not m:
            rev["errores_formato"].append(f"comentario {i}: falta «archivo» o «linea» numérica")
            continue
        rev["comentarios"].append({"nivel_texto": c.get("nivel", ""), "archivo": c["archivo"], "desde": int(m.group(1)),
                                   "hasta": int(m.group(2) or m.group(1)), "que": c.get("que_veo", ""),
                                   "porque": c.get("porque", ""), "propuesta": c.get("propuesta", "")})
        partes += [c.get("que_veo", ""), c.get("porque", ""), c.get("propuesta", "")]
    rev["secciones"]["resultado de pruebas y revisores"] = str(datos.get("pruebas", ""))
    rev["secciones"]["lo que aprendes de este cambio"] = "\n".join(f"- {l}" for l in datos.get("lecciones", []))
    rev["texto_revisable"] = "\n".join(partes + list(datos.get("lecciones", [])))
    return rev


def palabras(texto):
    return len(re.findall(r"\w+", texto or ""))


def seccion(rev, *claves):
    for nombre, cuerpo in rev["secciones"].items():
        if any(c in nombre for c in claves):
            return cuerpo
    return None


# ------------------------------------------------------------------ verificación
def verificar(rev, diff, repo, herramientas):
    fallas, avisos, ok = [], [], []
    fallas += rev["errores_formato"]
    comentarios = rev["comentarios"]
    if not comentarios:
        fallas.append("no encontré comentarios con el formato «### [Nivel] archivo:línea»")
    conteo = {n: 0 for n in NIVELES.values()}
    for i, c in enumerate(comentarios, 1):
        cita = f"{c['archivo']}:{c['desde']}" + (f"-{c['hasta']}" if c["hasta"] != c["desde"] else "")
        etiqueta = f"comentario {i} ({cita})"
        nivel = NIVELES.get(normal(c["nivel_texto"]).strip())
        if not nivel:
            fallas.append(f"{etiqueta}: nivel «{c['nivel_texto']}» no válido (usa Bloquea, Sugerencia, Detalle o Bien hecho)")
        else:
            conteo[nivel] += 1
        ruta = c["archivo"].replace("\\", "/").removeprefix("./")
        lineas = range(c["desde"], c["hasta"] + 1)
        info = diff.get(ruta)
        if c["hasta"] < c["desde"]:
            fallas.append(f"{etiqueta}: el rango de líneas está al revés")
        elif info and any(n in info["cambiadas"] for n in lineas):
            ok.append(f"{etiqueta}: línea dentro del cambio")
        elif info and any(n in info["contexto"] for n in lineas):
            avisos.append(f"{etiqueta}: la línea es CONTEXTO (se ve en el diff pero no cambió)")
        else:
            total = None
            if repo and (repo / ruta).is_file():
                total = len((repo / ruta).read_text(encoding="utf-8", errors="replace").splitlines())
            if total is not None and c["hasta"] <= total:
                avisos.append(f"{etiqueta}: la línea existe pero está FUERA del cambio (contexto)")
            elif info is None and total is None:
                fallas.append(f"{etiqueta}: el archivo «{ruta}» no está en el cambio" + (" ni en el proyecto" if repo else
                              " (pasa --repo para aceptar archivos de contexto)"))
            else:
                fallas.append(f"{etiqueta}: la línea {c['hasta'] if total else c['desde']} no existe en «{ruta}»"
                              + (f" (tiene {total} líneas)" if total else " ni en el cambio"))
        if palabras(c.get("que")) < 3:
            fallas.append(f"{etiqueta}: falta «Qué veo» (qué hace ese código, en tus palabras)")
        if palabras(c.get("porque")) < 5:
            fallas.append(f"{etiqueta}: falta «Por qué importa» o es muy corto (al menos 5 palabras)")
        if nivel and nivel != "Bien hecho" and palabras(c.get("propuesta")) < 4:
            fallas.append(f"{etiqueta}: falta «Propuesta» concreta (al menos 4 palabras: qué cambiar y cómo)")
    if comentarios and conteo["Bien hecho"] == 0:
        fallas.append("no hay ningún comentario «Bien hecho»: un buen editor también dice qué funciona")
    texto = normal(rev.get("texto_revisable", ""))
    duras = sorted({f for f in FRASES_DURAS if re.search(rf"\b{re.escape(f)}\b", texto)})
    if duras:
        fallas.append("frases duras (tono de juez, no de editor): " + ", ".join(f"«{d}»" for d in duras))
    suaves = sorted({f for f in FRASES_MINIMIZAN if re.search(rf"\b{re.escape(f)}\b", texto)})
    if suaves:
        avisos.append("frases que minimizan el esfuerzo de quien escribió el código: " + ", ".join(f"«{s}»" for s in suaves))
    v = rev.get("veredicto")
    if not v:
        fallas.append(f"falta «Veredicto:» con Aprobar, Aprobar con cambios o Necesita cambios"
                      + (f" (encontré «{rev.get('veredicto_texto')}»)" if rev.get("veredicto_texto") else ""))
    elif conteo["Bloquea"] and v != "Necesita cambios":
        fallas.append(f"veredicto «{v}» con {conteo['Bloquea']} comentario(s) «Bloquea»: debe ser «Necesita cambios»")
    elif not conteo["Bloquea"] and v == "Necesita cambios":
        avisos.append("veredicto «Necesita cambios» sin ningún «Bloquea»: ¿falta marcar cuál lo impide?")
    sec_pruebas = seccion(rev, "prueba", "revisores", "herramientas")
    if sec_pruebas is None:
        fallas.append("falta la sección «## Resultado de pruebas y revisores» con el resultado real")
    elif palabras(sec_pruebas) < 3:
        fallas.append("la sección de pruebas está casi vacía: copia el resultado real de cada herramienta")
    if sec_pruebas is not None and herramientas is not None:
        nombres = lambda h: [x.strip(" )") for x in re.split(r" / | \(", normal(h["herramienta"])) if x.strip(" )")]
        falta = [h["herramienta"] for h in herramientas if not any(x in normal(sec_pruebas) for x in nombres(h))]
        if falta:
            fallas.append("la sección de pruebas no menciona: " + ", ".join(falta) + " (copia el resultado real de herramientas.json)")
        fallan = [h["herramienta"] for h in herramientas if h["estado"] == "FALLA"]
        if fallan and v == "Aprobar":
            fallas.append(f"veredicto «Aprobar» pero fallan: {', '.join(fallan)}")
        for h in herramientas:
            if h["estado"] == "FALLA" and "falla" not in normal(sec_pruebas):
                fallas.append(f"«{h['herramienta']}» FALLA en la ejecución real pero la revisión no lo dice")
                break
    lecciones = seccion(rev, "lo que aprendes")
    n = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", lecciones or "", re.M))
    if not 2 <= n <= 3:
        fallas.append(f"«## Lo que aprendes de este cambio» debe tener 2 o 3 lecciones (encontré {n})")
    return fallas, avisos, ok, conteo


def main():
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpeta", nargs="?", help="carpeta revision-codigo/ creada por preparar_revision.py")
    ap.add_argument("--diff")
    ap.add_argument("--revision")
    ap.add_argument("--repo", help="carpeta del proyecto (para aceptar líneas de contexto fuera del diff)")
    ap.add_argument("--herramientas", help="herramientas.json con el resultado real de pruebas y revisores")
    a = ap.parse_args()
    herr_ruta = Path(a.herramientas) if a.herramientas else None
    repo = Path(a.repo).resolve() if a.repo else None
    if a.carpeta:
        c = Path(a.carpeta)
        diff_ruta = Path(a.diff) if a.diff else c / "cambio.diff"
        rev_ruta = Path(a.revision) if a.revision else next((p for p in (c / "revision-codigo.md", c / "revision.md",
                                                                          c / "revision.json") if p.exists()), c / "revision-codigo.md")
        herr_ruta = herr_ruta or (c / "herramientas.json" if (c / "herramientas.json").exists() else None)
        if repo is None and (c / "contexto.json").exists():
            proyecto = json.loads((c / "contexto.json").read_text(encoding="utf-8")).get("proyecto")
            repo = Path(proyecto) if proyecto and Path(proyecto).is_dir() else None
    elif a.diff and a.revision:
        diff_ruta, rev_ruta = Path(a.diff), Path(a.revision)
    else:
        print(__doc__)
        print("FALLA: indica la carpeta de la revisión, o --diff y --revision")
        return 2
    for r in (diff_ruta, rev_ruta):
        if not r.is_file():
            print(f"FALLA: no existe {r}")
            return 2
    diff = leer_diff(diff_ruta.read_text(encoding="utf-8", errors="replace"))
    texto = rev_ruta.read_text(encoding="utf-8-sig", errors="replace")
    try:
        rev = leer_revision_json(texto) if rev_ruta.suffix.lower() == ".json" else leer_revision_md(texto)
    except json.JSONDecodeError as e:
        print(f"FALLA: la revisión JSON no es válida: {e}")
        return 1
    herramientas = json.loads(herr_ruta.read_text(encoding="utf-8")) if herr_ruta and herr_ruta.is_file() else None

    print(f"== Verificando {rev_ruta.name} contra {diff_ruta.name} ({len(diff)} archivos en el cambio)")
    fallas, avisos, ok, conteo = verificar(rev, diff, repo, herramientas)
    for m in ok:
        print(f"  [OK] {m}")
    for m in avisos:
        print(f"  [AVISO] {m}")
    for m in fallas:
        print(f"  [FALLA] {m}")
    resumen = ", ".join(f"{v} {k}" for k, v in conteo.items())
    print(f"\nComentarios: {len(rev['comentarios'])} ({resumen}); veredicto: {rev.get('veredicto') or 'sin veredicto'}; "
          f"pruebas: {'contrastadas con herramientas.json' if herramientas is not None else 'sin herramientas.json'}")
    if fallas:
        print(f"FALLA: {len(fallas)} problema(s); corrige la revisión y vuelve a verificar")
        return 1
    print(f"PASA: cada cita existe en el cambio, cada comentario tiene nivel, porqué y propuesta, el tono es de editor"
          + (f" ({len(avisos)} aviso(s) de contexto o tono)" if avisos else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
