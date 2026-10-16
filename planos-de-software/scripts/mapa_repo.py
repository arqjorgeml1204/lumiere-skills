"""mapa_repo.py — saca el mapa de un repositorio para escribir planos sobre el código real.

Uso:  python mapa_repo.py <raíz del repo> [--buscar pago,reserva,anticipo] [--salida mapa-repo.md]

Imprime (o guarda en --salida) un informe en Markdown con:
- árbol de carpetas y archivos (sin node_modules, .git, entornos virtuales ni compilados);
- lenguajes por número de archivos;
- dependencias (package.json, requirements*.txt, pyproject.toml y otros manifiestos);
- modelo de datos (esquemas, migraciones, modelos del ORM);
- rutas HTTP detectadas (Express, FastAPI, Flask) con archivo y línea;
- pruebas y cuántos casos tiene cada archivo;
- configuración y entorno (.env.example, Docker, CI);
- dónde aparece cada palabra de --buscar (archivo:línea), para saber qué módulos tocaría el cambio.
Solo lee: no modifica nada del repo. Solo biblioteca estándar (Python 3.10+).
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # acentos correctos en la consola de Windows

IGNORAR = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".next", ".nuxt",
           "coverage", ".pytest_cache", ".mypy_cache", ".idea", ".vscode", "target", ".expo", ".turbo", "vendor"}
TEXTO = {".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".json", ".md", ".sql", ".prisma", ".yml", ".yaml",
         ".toml", ".html", ".css", ".go", ".rb", ".java", ".kt", ".swift", ".dart", ".rs", ".php", ".cs", ".vue",
         ".svelte", ".txt", ".cfg", ".ini", ".sh", ".ps1", ".example", ".env"}
LENGUAJE = {".js": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript", ".jsx": "JavaScript (JSX)",
            ".ts": "TypeScript", ".tsx": "TypeScript (TSX)", ".py": "Python", ".go": "Go", ".rb": "Ruby",
            ".java": "Java", ".kt": "Kotlin", ".swift": "Swift", ".dart": "Dart", ".rs": "Rust", ".php": "PHP",
            ".cs": "C#", ".vue": "Vue", ".svelte": "Svelte", ".sql": "SQL", ".prisma": "Prisma"}
MANIFIESTOS = {"package.json", "requirements.txt", "requirements-dev.txt", "pyproject.toml", "Pipfile", "go.mod",
               "Gemfile", "pubspec.yaml", "composer.json", "Cargo.toml", "pom.xml", "build.gradle"}
RUTA_JS = re.compile(r"\b(?:app|router|server)\.(get|post|put|patch|delete)\(\s*['\"`]([^'\"`]+)")
RUTA_PY = re.compile(r"@(?:app|router|bp|blueprint)\.(get|post|put|patch|delete|route)\(\s*['\"]([^'\"]+)")
MONTAJE_JS = re.compile(r"\bapp\.use\(\s*['\"`]([^'\"`]+)['\"`]\s*,\s*(\w+)")
CASO_PRUEBA = re.compile(r"^\s*(?:it|test)\s*\(|^\s*(?:async\s+)?def\s+test_", re.M)
MAX_BYTES = 1_000_000


def plural(n: int, uno: str, varios: str) -> str:
    return f"{n} {uno if n == 1 else varios}"


def recorrer(raiz: str):
    """Devuelve las rutas relativas (con /) de los archivos del repo, ordenadas."""
    archivos = []
    for carpeta, subcarpetas, nombres in os.walk(raiz):
        rel = os.path.relpath(carpeta, raiz).replace("\\", "/")
        # docs/planos se salta: son los planos mismos, no el código que describen
        subcarpetas[:] = sorted(d for d in subcarpetas if d not in IGNORAR and not (rel == "docs" and d == "planos"))
        for n in sorted(nombres):
            archivos.append(n if rel == "." else f"{rel}/{n}")
    return archivos


def leer(raiz: str, rel: str) -> str:
    ruta = os.path.join(raiz, rel)
    if os.path.getsize(ruta) > MAX_BYTES:
        return ""
    with open(ruta, encoding="utf-8", errors="ignore") as f:
        return f.read()


def es_texto(rel: str) -> bool:
    nombre = rel.rsplit("/", 1)[-1]
    return os.path.splitext(nombre)[1].lower() in TEXTO or nombre in MANIFIESTOS or nombre.startswith(".env")


def arbol(archivos, profundidad=4, maximo=250):
    lineas, vistos = [], set()
    for rel in archivos:
        partes = rel.split("/")
        for i in range(1, len(partes)):
            carpeta = "/".join(partes[:i])
            if carpeta not in vistos and i <= profundidad:
                vistos.add(carpeta)
                lineas.append("  " * (i - 1) + partes[i - 1] + "/")
        if len(partes) <= profundidad:
            lineas.append("  " * (len(partes) - 1) + partes[-1])
    if len(lineas) > maximo:
        lineas = lineas[:maximo] + [f"… {len(lineas) - maximo} líneas más"]
    return lineas


def dependencias(raiz, archivos):
    salida = []
    for rel in archivos:
        nombre = rel.rsplit("/", 1)[-1]
        if nombre not in MANIFIESTOS:
            continue
        texto = leer(raiz, rel)
        if nombre == "package.json":
            try:
                datos = json.loads(texto)
            except json.JSONDecodeError:
                salida.append(f"- `{rel}`: no se pudo leer (JSON inválido)")
                continue
            for clave in ("dependencies", "devDependencies"):
                deps = datos.get(clave) or {}
                if deps:
                    salida.append(f"- `{rel}` · {clave}: " + ", ".join(f"{k} {v}" for k, v in deps.items()))
            scripts = datos.get("scripts") or {}
            if scripts:
                salida.append(f"- `{rel}` · scripts: " + ", ".join(f"{k} → `{v}`" for k, v in scripts.items()))
        elif nombre.startswith("requirements"):
            deps = [l.strip() for l in texto.splitlines() if l.strip() and not l.strip().startswith("#")]
            salida.append(f"- `{rel}`: " + (", ".join(deps) if deps else "vacío"))
        elif nombre == "pyproject.toml":
            m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", texto, re.S | re.M)
            deps = re.findall(r"['\"]([^'\"]+)['\"]", m.group(1)) if m else []
            salida.append(f"- `{rel}`: " + (", ".join(deps) if deps else "sin lista [project].dependencies"))
        else:
            salida.append(f"- `{rel}` (ábrelo para ver las dependencias)")
    return salida or ["- No se encontró ningún manifiesto de dependencias."]


def modelo_datos(archivos):
    patron = re.compile(r"(^|/)(models?|migrations?|entities|schemas?|prisma|db)(/|\.|$)|\.sql$|\.prisma$|"
                        r"\.entity\.[jt]s$|\.model\.[jt]s$|(^|/)models\.py$|(^|/)schema\.(rb|sql|py|ts|js)$", re.I)
    return [f"- `{r}`" for r in archivos if patron.search(r)] or ["- No se encontraron archivos de modelo de datos."]


def rutas_http(raiz, archivos):
    salida = []
    for rel in archivos:
        ext = os.path.splitext(rel)[1].lower()
        if ext not in {".js", ".mjs", ".cjs", ".ts", ".py"}:
            continue
        for n, linea in enumerate(leer(raiz, rel).splitlines(), 1):
            for patron in (RUTA_JS, RUTA_PY):
                m = patron.search(linea)
                if m:
                    salida.append(f"- {m.group(1).upper()} `{m.group(2)}` → {rel}:{n}")
            m = MONTAJE_JS.search(linea)
            if m:
                salida.append(f"- (montaje) prefijo `{m.group(1)}` → {m.group(2)} en {rel}:{n}")
    return salida or ["- No se detectaron rutas HTTP (Express, FastAPI o Flask)."]


def pruebas(raiz, archivos):
    patron = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]+\.py$|_test\.(py|go)$|\.(test|spec)\.[jt]sx?$")
    salida = []
    for rel in archivos:
        if patron.search(rel) and es_texto(rel):
            casos = len(CASO_PRUEBA.findall(leer(raiz, rel)))
            salida.append(f"- `{rel}` · {plural(casos, 'caso', 'casos')}")
    return salida or ["- No hay pruebas automáticas: el plan de pruebas tendrá que crearlas."]


def configuracion(archivos):
    patron = re.compile(r"(^|/)\.env[^/]*$|(^|/)Dockerfile|docker-compose|^\.github/workflows/|(^|/)README", re.I)
    return [f"- `{r}`" for r in archivos if patron.search(r)] or ["- No se encontró configuración de entorno, Docker ni CI."]


def buscar(raiz, archivos, palabras):
    salida = []
    for palabra in palabras:
        patron = re.compile(re.escape(palabra), re.I)
        hallazgos = []
        for rel in archivos:
            if not es_texto(rel):
                continue
            lineas = [n for n, l in enumerate(leer(raiz, rel).splitlines(), 1) if patron.search(l)]
            if lineas:
                hallazgos.append(f"  - `{rel}` · {plural(len(lineas), 'vez', 'veces')} (línea{'s' if len(lineas) > 1 else ''} {', '.join(map(str, lineas[:5]))}"
                                 + ("…" if len(lineas) > 5 else "") + ")")
        salida.append(f"- **{palabra}**: " + (plural(len(hallazgos), "archivo", "archivos") if hallazgos
                                              else "no aparece en el repo (probablemente sea código nuevo)"))
        salida.extend(hallazgos)
    return salida


def main():
    p = argparse.ArgumentParser(description="Mapa de un repositorio para escribir planos sobre el código real.")
    p.add_argument("raiz")
    p.add_argument("--buscar", default="", help="palabras del pedido separadas por coma")
    p.add_argument("--salida", help="archivo .md donde guardar el mapa")
    a = p.parse_args()
    raiz = os.path.abspath(a.raiz)
    if not os.path.isdir(raiz):
        print(f"FALLA: no existe la carpeta {raiz}")
        sys.exit(2)
    archivos = recorrer(raiz)
    lenguajes = Counter(LENGUAJE[os.path.splitext(r)[1].lower()] for r in archivos if os.path.splitext(r)[1].lower() in LENGUAJE)
    palabras = [x.strip() for x in a.buscar.split(",") if x.strip()]

    md = [f"# Mapa del repositorio: {os.path.basename(raiz)}", "",
          f"Generado con mapa_repo.py · {len(archivos)} archivos (sin dependencias instaladas ni compilados).", "",
          "## Lenguajes", ""]
    md += [f"- {l}: {plural(n, 'archivo', 'archivos')}" for l, n in lenguajes.most_common()] or ["- Sin código reconocido."]
    md += ["", "## Árbol", "", "```"] + arbol(archivos) + ["```", "", "## Dependencias", ""] + dependencias(raiz, archivos)
    md += ["", "## Modelo de datos", ""] + modelo_datos(archivos)
    md += ["", "## Rutas HTTP", ""] + rutas_http(raiz, archivos)
    md += ["", "## Pruebas", ""] + pruebas(raiz, archivos)
    md += ["", "## Configuración y entorno", ""] + configuracion(archivos)
    if palabras:
        md += ["", "## Dónde aparece cada palabra del pedido", ""] + buscar(raiz, archivos, palabras)
    md += ["", "Siguiente paso: abre y lee los archivos de rutas, modelo de datos, servicios y pruebas que tocaría el cambio."]
    texto = "\n".join(md) + "\n"

    if a.salida:
        os.makedirs(os.path.dirname(os.path.abspath(a.salida)), exist_ok=True)
        with open(a.salida, "w", encoding="utf-8") as f:
            f.write(texto)
        print(f"Mapa guardado en {a.salida} ({len(archivos)} archivos, {len(palabras)} palabras buscadas)")
    else:
        print(texto)


if __name__ == "__main__":
    main()
