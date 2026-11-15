#!/usr/bin/env python3
"""analiza_guion.py · revisa la voz de un guion de reel en español antes de grabarlo (skill publica-con-claude).

Lee la voz de:
  - un .txt (un tramo de voz por línea; el primero es el gancho);
  - un .md (columna «Voz…» de una tabla, o líneas que empiezan con «> »);
  - un .datos.ts de Remotion (cada `voz: "..."` es un tramo).
Con una carpeta, revisa todos los guiones que encuentre dentro.

Mide con ~3 palabras por segundo (voz ágil y continua). Si tu voz es más lenta, usa --pps 2.5.

Uso:
  python analiza_guion.py guion.txt
  python analiza_guion.py carpeta/ --resumen        (una línea por guion)
  python analiza_guion.py guiones.md --seccion A009 (solo el guion bajo ese encabezado)
  python analiza_guion.py guion.txt --json

FALLA = corrígelo antes de grabar. AVISO = mejora recomendada.
El cierre empieza en la primera despedida («Sígueme», «Para mañana…») o en el primer «Comenta PALABRA»;
si no hay ninguna, se toma el último tramo. Solo lee archivos; no usa internet.
"""
import argparse
import json
import re
import sys
from pathlib import Path

PPS = 132 / 43
WORD = re.compile(r"[\wÁÉÍÓÚÜÑáéíóúüñ$%]+", re.U)
NUMS = set("""cero dos tres cuatro cinco seis siete ocho nueve diez once doce quince veinte treinta cuarenta
cincuenta sesenta setenta ochenta noventa cien ciento cientos mil millón millones doble triple mitad
docena segundos minutos horas días semanas meses años pesos dólares""".split())
VOZ_TS = re.compile(r'voz:\s*("(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`|\'(?:[^\'\\]|\\.)*\')', re.S)
# Dónde empieza el cierre: frases de despedida o el primer «Comenta PALABRA». Si no hay ninguna, el último tramo.
CIERRE = re.compile(r"(Para mañana|En el curso te|Con esto cerramos|Hice una skill|Siguiente módulo|Siguiente capítulo|Sígueme|Sigue a|[Cc]omenta [«\"]?[A-ZÁÉÍÓÚÑ]{2,})")
PEDIDOS = re.compile(r"(?i)\b(comenta|sígueme|déjal[ao] en los comentarios|dímelo|guárdalo|mándaselo|te leo|la guía (técnica )?está)\b")
BUCLE_PLANTILLA = re.compile(r"(?i)^\s*(¿y si\b[^?]{0,25}\?|pero lo (bueno|mejor) (es|viene)|pero no cualquiera|¿y cómo\b[^?]{0,20}\?)")
TECNICO = re.compile(r"(?i)^\s*¿?(qué (es|son)\b|así funciona|hoy (te )?(explico|vemos|aprendes))")
HUECO = re.compile(r"(\b[Cc]ierre M\d|\+ *CTA\b|\bTODO\b|\bPENDIENTE\b|<[^>]{2,}>)")

# Límites de la regla 5ac (calibrados con METRICAS.md: Día 4 = 17× la mediana)
GANCHO_MAX_S = 5.0     # 1.ª frase del gancho; la del Día 4 dura 4,2 s
TRAMO_MAX_S = 8.0      # un tramo de voz más largo necesita 2+ planos (5ab: plano ≤ 4 s)
CIERRE_MAX_S = 8.0
CIERRE_MAX_PCT = 20


def palabras(s):
    return WORD.findall(s)


def marcas(full):
    """Palabras con mayúscula a media frase (Netflix, Claude…): cuentan como dato concreto en todo el guion."""
    return {m.group(1) for m in re.finditer(r"(?<=[\w,;:]) ([A-ZÁÉÍÓÚ][\wáéíóúñ]{2,})", full)}


def concreto(s, mk):
    return bool(re.search(r"\d", s)) or any(w.lower() in NUMS or w in mk for w in palabras(s))


def voz_ts(texto):
    return [m.group(1)[1:-1].replace('\\"', '"').replace("\\n", " ") for m in VOZ_TS.finditer(texto)]


def voz_md(texto):
    lines = texto.splitlines()
    out, col = [], None
    for l in lines:
        if l.startswith("|"):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            if col is None:
                for i, c in enumerate(cells):
                    if re.match(r"Voz\b", c) and "v1" not in c and "comparar" not in c:
                        col = i
                        break
                continue
            if set("".join(cells)) <= set("-: "):
                continue
            if col < len(cells):
                v = re.sub(r"→.*$", "", cells[col]).strip().strip("«»\"*")
                if v:
                    out.append(v)
        elif l.strip():
            col = None
    if out:
        return out
    corte = next((i for i, l in enumerate(lines) if re.search(r"(?i)^#+ .*texto completo", l)), len(lines))
    return [l[2:].strip() for l in lines[:corte] if l.startswith("> ") and len(l) > 6]


def seccion(texto, nombre):
    """Solo el bloque bajo el primer encabezado que contiene `nombre`, hasta el siguiente del mismo nivel."""
    lines = texto.splitlines()
    for i, l in enumerate(lines):
        if l.startswith("#") and nombre.lower() in l.lower():
            nivel = len(l) - len(l.lstrip("#"))
            fin = next((j for j in range(i + 1, len(lines)) if lines[j].startswith("#") and len(lines[j]) - len(lines[j].lstrip("#")) <= nivel), len(lines))
            return "\n".join(lines[i:fin])
    return ""


def extrae(path, nombre=None):
    t = path.read_text(encoding="utf-8", errors="replace")
    if nombre:
        t = seccion(t, nombre)
    if path.suffix == ".ts":
        return voz_ts(t)
    if path.suffix == ".md":
        return voz_md(t)
    return [l.strip() for l in t.splitlines() if l.strip()]


def revisa(beats, pps):
    beats = [re.sub(r"\s+", " ", b).strip() for b in beats if b.strip()]
    full = " ".join(beats)
    mk = marcas(full)
    n = len(palabras(full))
    seg = lambda s: len(palabras(s)) / pps
    gancho = beats[0]
    frase1 = re.split(r"(?<=[.?!])\s+", gancho)[0]
    m = CIERRE.search(full)
    cola = full[m.start():] if m else beats[-1]
    cierre_p = len(palabras(cola))
    cierre_s = cierre_p / pps
    pct = round(100 * cierre_p / n)
    largos = [i + 1 for i, b in enumerate(beats) if seg(b) > TRAMO_MAX_S]
    secos, racha = [], 0
    for i, b in enumerate(beats):
        racha = 0 if concreto(b, mk) else racha + 1
        if racha == 3:
            secos.append(i + 1)
    pedidos = len(PEDIDOS.findall(cola))
    g_words = {w.lower() for w in palabras(gancho) if len(w) > 4}
    vuelve = len(beats) > 1 and bool(g_words & {w.lower() for w in palabras(beats[-1])})
    plantilla = [b[:40] for b in beats if BUCLE_PLANTILLA.search(b)]
    huecos = [b[:50] for b in beats if HUECO.search(b)]
    checks = [  # (id, pasa, detalle, grave): grave → FALLA; si no → AVISO
        ("gancho_1_frase", seg(frase1) <= GANCHO_MAX_S,
         f"1.ª frase del gancho: {seg(frase1):.1f} s ({len(palabras(frase1))} palabras); máx. {GANCHO_MAX_S:.0f} s", True),
        ("gancho_sin_termino", not TECNICO.search(gancho), "el gancho no abre con «qué es…» ni con el término", True),
        ("datos_cada_3", not secos,
         f"3 tramos seguidos sin número ni marca, hasta el tramo {secos}" if secos else "hay número o marca al menos cada 3 tramos", True),
        ("cierre_corto", cierre_s <= CIERRE_MAX_S and pct <= CIERRE_MAX_PCT,
         f"cierre: {cierre_s:.1f} s = {pct} % de la voz; máx. {CIERRE_MAX_S:.0f} s y {CIERRE_MAX_PCT} %", True),
        ("un_pedido", pedidos <= 2, f"pedidos en el cierre: {pedidos}; máx. 2 (una palabra + una pregunta)", True),
        ("sin_huecos", not huecos, f"texto sin terminar: {huecos}" if huecos else "sin marcadores pendientes", True),
        ("tramos_cortos", not largos,
         f"tramos de voz de más de {TRAMO_MAX_S:.0f} s (2+ planos, 5ab): {largos or 'ninguno'}", False),
        ("bucles_concretos", not plantilla, f"bucles de plantilla: {plantilla}" if plantilla else "bucles específicos", False),
        ("vuelve_al_gancho", vuelve, "el final retoma el gancho" if vuelve else "el final no retoma ninguna palabra del gancho", False),
    ]
    return {
        "tramos": len(beats), "palabras": n, "segundos": round(n / pps, 1), "gancho": gancho,
        "checks": [{"id": c, "pasa": bool(p), "detalle": d, "grave": g} for c, p, d, g in checks],
    }


def archivos(rutas):
    for r in rutas:
        p = Path(r)
        if p.is_dir():
            for f in sorted(p.rglob("*")):
                if "node_modules" in f.parts or "_respaldos" in f.parts:
                    continue
                if f.name.endswith(".datos.ts") or (f.suffix == ".md" and re.search(r"(?i)teleprompter|contexto|textos", f.name)):
                    yield f
        elif p.exists():
            yield p


def main():
    ap = argparse.ArgumentParser(description="Revisa la voz de un guion de reel en español (regla 5ac).")
    ap.add_argument("rutas", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--resumen", action="store_true", help="una línea por guion")
    ap.add_argument("--seccion", help="en un .md con varios guiones (p. ej. IDEAS_REEL.md), solo el encabezado que contiene este texto, como «A009»")
    ap.add_argument("--pps", type=float, default=PPS, help="palabras por segundo de la voz")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    res = []
    for f in archivos(a.rutas):
        beats = extrae(f, a.seccion)
        if len(beats) < 2:
            continue
        r = revisa(beats, a.pps)
        r["archivo"] = str(f)
        res.append(r)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return
    for r in res:
        fallas = [c["id"] for c in r["checks"] if not c["pasa"] and c["grave"]]
        avisos = [c["id"] for c in r["checks"] if not c["pasa"] and not c["grave"]]
        if a.resumen:
            print(f"{'FALLA' if fallas else 'PASA '} {Path(r['archivo']).name:26} {r['segundos']:5}s  "
                  f"falla: {', '.join(fallas) or '—'} · aviso: {', '.join(avisos) or '—'}")
            continue
        print(f"\n{r['archivo']}\n  {r['palabras']} palabras · ~{r['segundos']} s · {r['tramos']} tramos")
        print(f"  Gancho: {r['gancho'][:90]}")
        for c in r["checks"]:
            estado = "PASA " if c["pasa"] else ("FALLA" if c["grave"] else "AVISO")
            print(f"  {estado} {c['id']:18} {c['detalle']}")
    if not res:
        print("No encontré voz en esas rutas.")


if __name__ == "__main__":
    main()
