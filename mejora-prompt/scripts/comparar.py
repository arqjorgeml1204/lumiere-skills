"""Compara las salidas del prompt original y del final y escribe el informe antes/después.

Uso: python comparar.py resultados.json informe.md
Solo usa la biblioteca estándar de Python (3.9+). Sale con código 1 si el JSON no es válido
o si el prompt final no supera al original.
"""
import json
import sys


def es_json_con_claves(salida: str, claves: list[str]) -> tuple[bool, str]:
    try:
        datos = json.loads(salida)
    except (json.JSONDecodeError, TypeError):
        return False, "no es JSON válido"
    if not isinstance(datos, dict):
        return False, "el JSON no es un objeto"
    faltan = [c for c in claves if c not in datos]
    return (not faltan, f"faltan claves: {', '.join(faltan)}" if faltan else "JSON válido")


def validar(r: dict) -> list[str]:
    errores = []
    for campo in ("prompt", "criterios", "casos"):
        if campo not in r:
            errores.append(f"falta el campo «{campo}»")
    for c in r.get("casos", []):
        for v in ("original", "final"):
            if v not in c or "salida" not in c[v] or "criterios" not in c[v]:
                errores.append(f"caso {c.get('id', '?')}: falta «{v}» con salida y criterios")
                continue
            faltan = [k for k in r.get("criterios", []) if k not in c[v]["criterios"]]
            if faltan:
                errores.append(f"caso {c.get('id', '?')} ({v}): faltan criterios {faltan}")
    return errores


def main(entrada: str, salida: str) -> int:
    with open(entrada, encoding="utf-8") as f:
        r = json.load(f)
    errores = validar(r)
    if errores:
        print("resultados.json no es válido:")
        for e in errores:
            print(" -", e)
        return 1

    criterios = r["criterios"]
    filas, total = [], {"original": [0, 0], "final": [0, 0]}
    for c in r["casos"]:
        celdas = []
        for v in ("original", "final"):
            res = dict(c[v]["criterios"])
            nota = c[v].get("nota", "")
            if r.get("tipo_salida", r.get("formato")) == "json" and "formato" in res:
                ok, motivo = es_json_con_claves(c[v]["salida"], r.get("claves", []))
                res["formato"] = ok
                nota = f"{motivo}. {nota}".strip(" .") if not ok else nota
            si = sum(1 for k in criterios if res[k])
            total[v][0] += si
            total[v][1] += len(criterios)
            fallos = [k for k in criterios if not res[k]]
            celdas.append(f"{si}/{len(criterios)}" + (f" (falla: {', '.join(fallos)})" if fallos else "") + (f" — {nota}" if nota else ""))
        etiqueta = c["id"] + (" · trampa" if c.get("trampa") else "")
        filas.append(f"| {etiqueta} | {c['entrada'][:60]} | {celdas[0]} | {celdas[1]} |")

    pct = {v: 100 * a / b if b else 0 for v, (a, b) in total.items()}
    mejora = pct["final"] > pct["original"]
    md = [
        f"# Informe antes/después · {r['prompt']}",
        "",
        f"Criterios: {', '.join(criterios)}" + (f" · formato comprobado: JSON con {', '.join(r.get('claves', []))}" if r.get("tipo_salida", r.get("formato")) == "json" else ""),
        *( [f"Modelo usado en las pruebas: {r['modelo_prueba']}", ""] if r.get("modelo_prueba") else [] ),
        "",
        "| Caso | Entrada | Prompt original | Prompt final |",
        "|---|---|---|---|",
        *filas,
        "",
        f"**Criterios cumplidos: {pct['original']:.0f} % → {pct['final']:.0f} %**" + ("" if mejora else " · el prompt final NO mejora al original: revisar antes de entregar"),
        "",
        "Generado por scripts/comparar.py (skill mejora-prompt, Lumière Autómata).",
    ]
    with open(salida, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"Informe escrito en {salida}: {pct['original']:.0f} % -> {pct['final']:.0f} %")
    return 0 if mejora else 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
