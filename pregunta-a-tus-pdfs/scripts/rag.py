"""RAG mínimo y verificable sobre tus documentos. Solo biblioteca estándar (Python 3.9+).

Comandos:
  python rag.py indexar <carpeta>            corta tus documentos en fragmentos y crea <carpeta>/.rag/fragmentos.json
  python rag.py buscar <carpeta> "<pregunta>" [-k 5]   devuelve los fragmentos más parecidos (BM25)
  python rag.py verificar <carpeta> <respuestas.md>    comprueba que cada cita «…» exista en la página citada

Formatos que lee: .txt, .md, .docx y .pdf. Para .pdf usa pypdf si está instalado; si no, lee el texto
de archivos «<nombre>.pdf.p<N>.txt» (uno por página) que puede escribir Claude al abrir el PDF.
Formato de cita en respuestas.md: [archivo.pdf, p. 3] «texto copiado tal cual del documento»
"""
import json
import math
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

TAM, SOLAPE = 900, 150
VACIAS = set("""a al algo como con de del el ella ellos en entre era es esa ese eso esta este esto fue ha hay la las le les lo los
mas me mi muy no o para pero por que se si sin sobre su sus te tu un una uno unos y ya the of and to in is are""".split())


def normal(t: str) -> str:
    t = unicodedata.normalize("NFD", t.lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def palabras(t: str) -> list[str]:
    out = []
    for p in re.findall(r"[a-z0-9ñ]+", normal(t)):
        if p in VACIAS or len(p) < 2:
            continue
        for suf in ("es", "s"):  # raíz muy simple: plural → singular
            if len(p) > 4 and p.endswith(suf):
                p = p[: -len(suf)]
                break
        out.append(p)
    return out


def paginas(archivo: Path) -> list[tuple[str, str]]:
    """Devuelve [(etiqueta de página o sección, texto)]."""
    suf = archivo.suffix.lower()
    if suf in (".txt", ".md"):
        m = re.match(r"(.+\.pdf)\.p(\d+)\.txt$", archivo.name, re.I)
        etiqueta = f"p. {m.group(2)}" if m else "texto"
        return [(etiqueta, archivo.read_text(encoding="utf-8", errors="replace"))]
    if suf == ".docx":
        with zipfile.ZipFile(archivo) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        parrafos = [re.sub(r"<[^>]+>", "", p) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S)]
        return [("documento", "\n".join(p for p in parrafos if p.strip()))]
    if suf == ".pdf":
        try:
            from pypdf import PdfReader  # opcional
        except ImportError:
            return []  # se usarán los <nombre>.pdf.p<N>.txt
        return [(f"p. {i + 1}", pg.extract_text() or "") for i, pg in enumerate(PdfReader(str(archivo)).pages)]
    return []


def nombre_doc(archivo: Path) -> str:
    m = re.match(r"(.+\.pdf)\.p\d+\.txt$", archivo.name, re.I)
    return m.group(1) if m else archivo.name


def cortar(texto: str) -> list[str]:
    texto = re.sub(r"[ \t]+", " ", texto).strip()
    trozos, i = [], 0
    while i < len(texto):
        fin = min(len(texto), i + TAM)
        if fin < len(texto):
            espacio = texto.rfind(" ", i + TAM // 2, fin)
            fin = espacio if espacio > 0 else fin
        trozos.append(texto[i:fin].strip())
        if fin >= len(texto):
            break
        i = max(fin - SOLAPE, i + 1)
        while i < len(texto) and texto[i - 1] != " ":
            i += 1
    return [t for t in trozos if t]


def indexar(carpeta: Path) -> None:
    frag, docs, completas = [], set(), {}
    # se excluyen el índice y las respuestas que escribe la propia skill (si no, se citaría a sí misma)
    archivos = [a for a in sorted(carpeta.rglob("*")) if a.is_file() and ".rag" not in a.parts and not a.name.lower().startswith("respuestas")]
    con_texto = {nombre_doc(a) for a in archivos if re.search(r"\.pdf\.p\d+\.txt$", a.name, re.I)}
    for a in archivos:
        if a.suffix.lower() == ".pdf" and a.name in con_texto:
            continue  # ya tiene su texto por página: no se indexa dos veces
        for etiqueta, texto in paginas(a):
            completas[f"{nombre_doc(a)}|{etiqueta}"] = re.sub(r"\s+", " ", texto).strip()
            for j, t in enumerate(cortar(texto)):
                frag.append({"id": f"{nombre_doc(a)}|{etiqueta}|{j}", "doc": nombre_doc(a), "pagina": etiqueta, "texto": t})
                docs.add(nombre_doc(a))
    if not frag:
        print("No encontré texto. ¿Los PDF son escaneos? Necesitan OCR o el texto por página (<nombre>.pdf.p<N>.txt).")
        sys.exit(1)
    (carpeta / ".rag").mkdir(exist_ok=True)
    (carpeta / ".rag" / "fragmentos.json").write_text(json.dumps(frag, ensure_ascii=False, indent=1), encoding="utf-8")
    (carpeta / ".rag" / "paginas.json").write_text(json.dumps(completas, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Indexados {len(frag)} fragmentos de {len(docs)} documento(s): {', '.join(sorted(docs))}")
    print("Etiquetas para citar: " + "; ".join(sorted({f"[{f['doc']}, {f['pagina']}]" for f in frag})))


def cargar(carpeta: Path) -> list[dict]:
    ruta = carpeta / ".rag" / "fragmentos.json"
    if not ruta.exists():
        print("Primero: python rag.py indexar <carpeta>")
        sys.exit(1)
    return json.loads(ruta.read_text(encoding="utf-8"))


def buscar(carpeta: Path, pregunta: str, k: int = 5) -> list[tuple[float, dict]]:
    frag = cargar(carpeta)
    toks = [palabras(f["texto"]) for f in frag]
    n, media = len(frag), sum(map(len, toks)) / max(1, len(frag))
    df = Counter(p for t in toks for p in set(t))
    k1, b = 1.5, 0.75
    q = palabras(pregunta)
    puntos = []
    for f, t in zip(frag, toks):
        tf = Counter(t)
        s = sum(math.log(1 + (n - df[p] + 0.5) / (df[p] + 0.5)) * tf[p] * (k1 + 1) / (tf[p] + k1 * (1 - b + b * len(t) / media)) for p in q if p in tf)
        if s > 0:
            puntos.append((s, f))
    return sorted(puntos, key=lambda x: -x[0])[:k]


CITA = re.compile(r"\[([^\],]+),\s*([^\]]+)\]\s*«([^»]+)»")


def verificar(carpeta: Path, respuestas: Path) -> int:
    cargar(carpeta)
    paginas_txt = json.loads((carpeta / ".rag" / "paginas.json").read_text(encoding="utf-8"))
    texto = respuestas.read_text(encoding="utf-8")
    citas = CITA.findall(texto)
    lineas_fuentes = "\n".join(l for l in texto.splitlines() if l.lstrip().startswith("Fuentes"))
    sueltas = len(re.findall(r"«[^»]+»", lineas_fuentes)) - len(CITA.findall(lineas_fuentes))
    if not citas:
        print("No hay citas con el formato [archivo, p. N] «texto».")
        return 1
    espacios = lambda s: re.sub(r"\s+", " ", s).strip()
    fallas = 0
    for doc, pag, cita in citas:
        fuente = paginas_txt.get(f"{doc.strip()}|{pag.strip()}", "")
        ok = bool(fuente) and espacios(cita) in fuente
        fallas += not ok
        motivo = "OK   " if ok else ("FALLA (no existe esa página: usa la etiqueta exacta que imprime indexar/buscar)" if not fuente else "FALLA (el texto no está tal cual en esa página)")
        print(f"{motivo} [{doc}, {pag}] «{cita[:120]}{'…' if len(cita) > 120 else ''}»")
    if sueltas > 0:
        fallas += sueltas
        print(f"FALLA {sueltas} cita(s) en líneas «Fuentes» sin el formato [archivo, etiqueta] «texto»")
    print(f"{len(citas) - (fallas - max(0, sueltas))}/{len(citas) + max(0, sueltas)} citas verificadas")
    return 1 if fallas else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "indexar":
        indexar(Path(a[1]))
    elif len(a) >= 3 and a[0] == "buscar":
        k = int(a[a.index("-k") + 1]) if "-k" in a else 5
        res = buscar(Path(a[1]), a[2], k)
        if not res or res[0][0] < 2.0:
            print("AVISO: coincidencia débil o nula. Reformula con sinónimos o términos del documento; si sigue igual, la respuesta probablemente no está.")
        for s, f in res:
            print(f"\n[{f['doc']}, {f['pagina']}] puntaje {s:.2f}\n{f['texto']}")
    elif len(a) >= 3 and a[0] == "verificar":
        sys.exit(verificar(Path(a[1]), Path(a[2])))
    else:
        print(__doc__)
        sys.exit(2)
