"""revisar_planos.py — revisa los planos (PRD, design doc, RFC, comunicado) antes de entregarlos.

Uso:  python revisar_planos.py <carpeta de los planos> --repo <raíz del repositorio> [--final]

Busca en la carpeta prd.md, design-doc.md, rfc.md y comunicado.md (al menos uno de los tres primeros) y comprueba:
- secciones obligatorias presentes y no vacías, sin «[completar» de la plantilla;
- cada decisión (### dentro de «Alternativas consideradas») con 2 o más opciones, qué se gana y qué se
  sacrifica en cada una, la elegida, el trade-off y el costo de revertir (alto, medio o bajo);
- métricas de éxito con número en la meta y número o fecha en el plazo;
- requisitos con prioridad P0/P1/P2, al menos un P0, y cada P0 citado en el «Plan de pruebas» del design doc;
- riesgos con mitigación y plan de despliegue que diga cómo se vuelve atrás;
- cada ruta de archivo citada entre comillas invertidas existe en el repo (o es otro documento de la misma
  carpeta de planos), o está marcada «(nuevo)» o «(fuera del repo)»; y lo marcado «(nuevo)» todavía no existe;
- «TODO», «TBD» o «por definir» solo con dueño, y cada pregunta abierta con dueño;
- extensión razonable (ni un plano vacío ni uno que nadie va a leer);
- con --final, además, informe-planos.md con sus secciones y las decisiones más caras de revertir.
Imprime PASA o FALLA con la lista de problemas. Sale con 0 si PASA, 1 si FALLA y 2 si el uso es incorrecto.
Solo lee. Solo biblioteca estándar (Python 3.10+).
"""
import argparse
import os
import re
import sys
import unicodedata

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")  # acentos correctos en la consola de Windows

# archivo: (nombre para mostrar, secciones obligatorias, (mínimo, máximo) de palabras)
DOCUMENTOS = {
    "prd.md": ("PRD", ["Problema", "Para quién", "Metas", "No-metas", "Métricas de éxito", "Requisitos",
                       "Preguntas abiertas"], (250, 2000)),
    "design-doc.md": ("Design doc", ["Contexto", "Propuesta", "Alternativas consideradas", "Impacto en el código",
                                     "Datos", "Riesgos y mitigación", "Plan de pruebas",
                                     "Plan de despliegue y vuelta atrás", "Preguntas abiertas"], (400, 3500)),
    "rfc.md": ("RFC", ["Resumen", "Motivación", "Propuesta", "Alternativas consideradas",
                       "Preguntas para quien comenta", "Plazo y quién decide"], (200, 2000)),
    "comunicado.md": ("Comunicado", ["Comunicado de prensa", "Preguntas frecuentes"], (150, 3000)),
}
INFORME = ("informe-planos.md", ["Qué documentos y por qué", "Resultado del revisor",
                                 "Decisiones más caras de revertir", "A quién pedir comentarios"])
LIMITE_SECCION = {("comunicado.md", "comunicado de prensa"): 500, ("comunicado.md", "preguntas frecuentes"): 2500}
EXTENSIONES = {"js", "mjs", "cjs", "ts", "tsx", "jsx", "py", "json", "md", "sql", "prisma", "yml", "yaml", "toml",
               "html", "css", "scss", "go", "rb", "java", "kt", "swift", "dart", "rs", "php", "cs", "vue", "svelte",
               "txt", "cfg", "ini", "lock", "sh", "ps1", "env", "example", "xml", "gradle", "csv"}
PARECE_RUTA = re.compile(r"\.?[\w\-\[\]]+(?:\.[\w\-]+)*(?:/[\w.\-\[\]]+)*/?")
MARCA = re.compile(r"\s*\((nuev[oa]|fuera del repo)\)", re.I)
PENDIENTE = re.compile(r"\bTODO\b|\bTBD\b|\bFIXME\b|(?i:por definir|por decidir)")
DUENO = re.compile(r"due[ñn][oa]\s*:\s*\S|@[\w.\-]+", re.I)
COSTO = re.compile(r"costo de revertir\s*:?\**\s*:?\s*\**\s*(alto|media|medio|bajo)", re.I)


def normalizar(t: str) -> str:
    t = unicodedata.normalize("NFD", t.strip().lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn").strip("*_ ")


def sin_comentarios(texto: str) -> str:
    return re.sub(r"<!--.*?-->", "", texto, flags=re.S)


def sin_codigo(texto: str) -> str:
    """Quita los bloques ``` (su contenido no cuenta como sección ni como ruta citada)."""
    return re.sub(r"^(`{3,}|~{3,}).*?^\1\s*$", "", texto, flags=re.S | re.M)


def secciones(texto: str) -> dict:
    """{título normalizado: contenido} de cada ## (los ### quedan dentro de su ##)."""
    partes = re.split(r"^##\s+(.+?)\s*$", texto, flags=re.M)
    return {normalizar(partes[i]): partes[i + 1] for i in range(1, len(partes), 2)}


def buscar_seccion(secs: dict, requerida: str):
    req = normalizar(requerida)
    for titulo, cuerpo in secs.items():
        if titulo == req or (titulo.startswith(req) and not titulo[len(req)].isalnum()):
            return cuerpo
    return None


def palabras(texto: str) -> int:
    return len(re.findall(r"\w+", texto))


def tabla(cuerpo: str):
    """Devuelve (encabezados normalizados, filas) de la primera tabla Markdown del texto."""
    filas = [l.strip() for l in cuerpo.splitlines() if l.strip().startswith("|")]
    if not filas:
        return [], []
    celdas = lambda l: [c.strip() for c in l.strip().strip("|").split("|")]
    encabezados = [normalizar(c) for c in celdas(filas[0])]
    datos = [celdas(l) for l in filas[1:] if not re.fullmatch(r"\|[\s:|\-]+\|?", l)]
    return encabezados, datos


def columna(encabezados, *claves):
    for i, e in enumerate(encabezados):
        if any(e.startswith(k) or k in e for k in claves):
            return i
    return None


def tiene_codigo(repo: str) -> bool:
    """True si el repo tiene algún archivo fuera de .git y docs/planos (si no, todo es «nuevo»)."""
    for carpeta, subcarpetas, nombres in os.walk(repo):
        rel = os.path.relpath(carpeta, repo).replace("\\", "/")
        subcarpetas[:] = [d for d in subcarpetas if d != ".git" and not (rel == "docs" and d == "planos")]
        if nombres:
            return True
    return False


def celda(fila, i):
    return fila[i].strip() if i is not None and i < len(fila) else ""


class Revision:
    def __init__(self, carpeta, repo):
        self.carpeta, self.repo = carpeta, repo
        self.problemas, self.decisiones, self.p0 = [], [], []
        self.rutas = {"existen": 0, "nuevas": 0, "fuera": 0}
        self.repo_tiene_codigo = tiene_codigo(repo)

    def mal(self, archivo, donde, que):
        self.problemas.append(f"{archivo} · {donde}: {que}" if donde else f"{archivo}: {que}")

    # ---------- revisiones comunes ----------
    def revisar_texto(self, archivo, texto):
        for n, linea in enumerate(texto.splitlines(), 1):
            if "[completar" in linea:
                self.mal(archivo, f"línea {n}", "queda un «[completar…]» de la plantilla")
            if PENDIENTE.search(linea) and not DUENO.search(linea):
                self.mal(archivo, f"línea {n}", "«TODO / por definir» sin dueño (agrega «dueño: <nombre>»)")

    def revisar_rutas(self, archivo, texto, registrar=True):
        """Cada `ruta/archivo.ext` o `carpeta/` citada debe existir en el repo o estar marcada.
        Devuelve cuántas rutas existentes cita. Con registrar=False solo cuenta (no suma ni reporta)."""
        existentes = 0
        problemas, rutas = list(self.problemas), dict(self.rutas)
        for n, linea in enumerate(sin_codigo(texto).splitlines(), 1):
            for m in re.finditer(r"`([^`\s]+)`", linea):
                ruta = m.group(1).strip()
                if not PARECE_RUTA.fullmatch(ruta):
                    continue
                ultimo = ruta.rstrip("/").rsplit("/", 1)[-1]
                es_carpeta = ruta.endswith("/") and len(ruta) > 1
                tiene_ext = "." in ultimo and ultimo.rsplit(".", 1)[1].lower() in EXTENSIONES
                if not (es_carpeta or tiene_ext):
                    continue
                marca = MARCA.match(linea[m.end():])
                destino = os.path.normpath(os.path.join(self.repo, ruta.lstrip("/")))
                dentro = os.path.commonpath([os.path.abspath(destino), os.path.abspath(self.repo)]) == os.path.abspath(self.repo)
                # también vale un documento hermano de la carpeta de planos (`prd.md`, `rfc.md`)
                existe = (dentro and os.path.exists(destino)) or os.path.isfile(os.path.join(self.carpeta, ruta))
                if marca and marca.group(1).lower().startswith("fuera"):
                    self.rutas["fuera"] += 1
                elif marca:
                    self.rutas["nuevas"] += 1
                    if existe:
                        self.mal(archivo, f"línea {n}", f"`{ruta}` está marcada (nuevo) pero ya existe en el repo")
                elif not dentro:
                    self.mal(archivo, f"línea {n}", f"`{ruta}` apunta fuera del repo")
                elif existe:
                    self.rutas["existen"] += 1
                    existentes += 1
                else:
                    self.mal(archivo, f"línea {n}", f"`{ruta}` no existe en el repo (si es nuevo, márcalo «(nuevo)»)")
        if not registrar:
            self.problemas, self.rutas = problemas, rutas
        return existentes

    def revisar_decisiones(self, archivo, cuerpo):
        bloques = re.split(r"^###\s+(.+?)\s*$", cuerpo, flags=re.M)
        if len(bloques) < 3:
            self.mal(archivo, "Alternativas consideradas", "no hay ninguna decisión (### Decisión…) con sus opciones")
            return
        for i in range(1, len(bloques), 2):
            titulo, texto = bloques[i].strip(), bloques[i + 1]
            donde = f"decisión «{titulo}»"
            enc, filas = tabla(texto)
            filas = [f for f in filas if any(c.strip() for c in f)]
            c_op, c_gana, c_sacr = columna(enc, "opcion"), columna(enc, "ganas"), columna(enc, "sacrificas")
            if None in (c_op, c_gana, c_sacr):
                self.mal(archivo, donde, "falta la tabla «| Opción | Qué ganas | Qué sacrificas |»")
            elif len(filas) < 2:
                self.mal(archivo, donde, f"tiene {len(filas)} alternativa(s); se necesitan al menos 2")
            else:
                for f in filas:
                    if not celda(f, c_gana) or not celda(f, c_sacr):
                        self.mal(archivo, donde, f"la opción «{celda(f, c_op)}» no dice qué se gana y qué se sacrifica")
            if not re.search(r"elegida\s*:?\**\s*:?\s*\**\s*\w", texto, re.I):
                self.mal(archivo, donde, "falta «Elegida:» con la opción y por qué")
            if not re.search(r"trade-?off\s*:?\**\s*:?\s*\**\s*\w", texto, re.I):
                self.mal(archivo, donde, "falta «Trade-off:» (qué ganas a cambio de qué)")
            costo = COSTO.search(texto)
            if not costo:
                self.mal(archivo, donde, "falta «Costo de revertir: alto | medio | bajo»")
            nivel = {"alto": 3, "medio": 2, "media": 2, "bajo": 1}.get(costo.group(1).lower(), 0) if costo else 0
            self.decisiones.append((nivel, archivo, titulo))

    # ---------- revisiones por tipo ----------
    def revisar_prd(self, secs):
        cuerpo = buscar_seccion(secs, "Métricas de éxito") or ""
        enc, filas = tabla(cuerpo)
        c_met, c_meta, c_plazo = columna(enc, "metrica"), columna(enc, "meta"), columna(enc, "plazo")
        if c_meta is None or c_plazo is None:
            self.mal("prd.md", "Métricas de éxito", "usa la tabla «| Métrica | Línea base | Meta | Plazo | Cómo se mide |»")
        elif not filas:
            self.mal("prd.md", "Métricas de éxito", "la tabla no tiene ninguna métrica")
        else:
            for f in filas:
                nombre = celda(f, c_met) or "(sin nombre)"
                if not re.search(r"\d", celda(f, c_meta)):
                    self.mal("prd.md", "Métricas de éxito", f"«{nombre}»: la meta no tiene número")
                if not re.search(r"\d", celda(f, c_plazo)):
                    self.mal("prd.md", "Métricas de éxito", f"«{nombre}»: el plazo no tiene número ni fecha")
        cuerpo = buscar_seccion(secs, "Requisitos") or ""
        enc, filas = tabla(cuerpo)
        c_id, c_pri = columna(enc, "id"), columna(enc, "prioridad")
        if c_id is None or c_pri is None:
            self.mal("prd.md", "Requisitos", "usa la tabla «| ID | Requisito | Prioridad |»")
            return
        for f in filas:
            pri = celda(f, c_pri).upper()
            if pri not in {"P0", "P1", "P2"}:
                self.mal("prd.md", "Requisitos", f"«{celda(f, c_id)}»: la prioridad debe ser P0, P1 o P2")
            elif pri == "P0":
                self.p0.append(celda(f, c_id))
        if filas and not self.p0:
            self.mal("prd.md", "Requisitos", "ningún requisito es P0: ¿qué es indispensable para lanzar?")

    def revisar_design(self, secs, existentes_impacto):
        cuerpo = buscar_seccion(secs, "Riesgos y mitigación") or ""
        enc, filas = tabla(cuerpo)
        c_r, c_m = columna(enc, "riesgo"), columna(enc, "mitigacion")
        if c_r is None or c_m is None:
            self.mal("design-doc.md", "Riesgos y mitigación", "usa la tabla «| Riesgo | Probabilidad | Impacto | Mitigación |»")
        else:
            for f in filas:
                if not celda(f, c_m):
                    self.mal("design-doc.md", "Riesgos y mitigación", f"«{celda(f, c_r)}» no tiene mitigación")
        despliegue = buscar_seccion(secs, "Plan de despliegue y vuelta atrás") or ""
        if not re.search(r"vuelta atr[aá]s|revertir|rollback", despliegue, re.I):
            self.mal("design-doc.md", "Plan de despliegue y vuelta atrás", "no dice cómo se vuelve atrás")
        if self.repo_tiene_codigo and existentes_impacto == 0:
            self.mal("design-doc.md", "Impacto en el código", "no cita ninguna ruta existente del repo: ¿se leyó el código?")
        pruebas = buscar_seccion(secs, "Plan de pruebas") or ""
        for rid in self.p0:
            if rid and not re.search(rf"(?<![\w-]){re.escape(rid)}(?![\w-])", pruebas):
                self.mal("design-doc.md", "Plan de pruebas", f"el requisito P0 {rid} del PRD no tiene prueba")

    def revisar_preguntas(self, archivo, secs):
        cuerpo = buscar_seccion(secs, "Preguntas abiertas")
        if cuerpo is None:
            return
        for linea in re.findall(r"^\s*(?:[-*]|\d+\.)\s+(.+)$", cuerpo, re.M):
            if not DUENO.search(linea):
                self.mal(archivo, "Preguntas abiertas", f"«{linea[:60]}» no tiene dueño")

    # ---------- documento completo ----------
    def revisar_documento(self, archivo, nombre, requeridas, rango):
        texto = sin_comentarios(open(os.path.join(self.carpeta, archivo), encoding="utf-8-sig").read())
        texto = texto.replace("\r\n", "\n")
        limpio = sin_codigo(texto)
        secs = secciones(limpio)
        for req in requeridas:
            cuerpo = buscar_seccion(secs, req)
            if cuerpo is None:
                self.mal(archivo, "", f"falta la sección «## {req}»")
            elif palabras(cuerpo) < 3:
                self.mal(archivo, req, "está vacía")
            limite = LIMITE_SECCION.get((archivo, normalizar(req)))
            if cuerpo is not None and limite and palabras(cuerpo) > limite:
                self.mal(archivo, req, f"tiene {palabras(cuerpo)} palabras; el máximo es {limite}")
        total = palabras(texto)
        if rango and total < rango[0]:
            self.mal(archivo, "", f"{total} palabras: muy corto para un {nombre} (mínimo {rango[0]}); le falta sustancia")
        if rango and total > rango[1]:
            self.mal(archivo, "", f"{total} palabras: nadie lo va a leer (máximo {rango[1]}); recorta")
        self.revisar_texto(archivo, texto)
        self.revisar_rutas(archivo, texto)
        alternativas = buscar_seccion(secs, "Alternativas consideradas")
        if alternativas is not None:
            self.revisar_decisiones(archivo, alternativas)
        self.revisar_preguntas(archivo, secs)
        return secs, total

    def ejecutar(self, final):
        resumen = []
        presentes = [a for a in DOCUMENTOS if os.path.exists(os.path.join(self.carpeta, a))]
        if not any(a in presentes for a in ("prd.md", "design-doc.md", "rfc.md")):
            self.mal(os.path.basename(self.carpeta) or self.carpeta, "", "no hay prd.md, design-doc.md ni rfc.md")
        secs_doc = {}
        for archivo in sorted(presentes, key=list(DOCUMENTOS).index):  # PRD primero: sus P0 se cruzan con el design doc
            nombre, requeridas, rango = DOCUMENTOS[archivo]
            secs, total = self.revisar_documento(archivo, nombre, requeridas, rango)
            secs_doc[archivo] = secs
            resumen.append(f"{archivo} ({total} palabras)")
            if archivo == "prd.md":
                self.revisar_prd(secs)
        if "design-doc.md" in secs_doc:
            impacto = buscar_seccion(secs_doc["design-doc.md"], "Impacto en el código") or ""
            existentes = self.revisar_rutas("design-doc.md", impacto, registrar=False)
            self.revisar_design(secs_doc["design-doc.md"], existentes)
        informe = os.path.join(self.carpeta, INFORME[0])
        if os.path.exists(informe):
            self.revisar_informe()
            resumen.append(INFORME[0])
        elif final:
            self.mal(INFORME[0], "", "falta (se escribe al final, cuando los planos ya PASAN)")
        return resumen

    def revisar_informe(self):
        archivo, requeridas = INFORME
        texto = sin_comentarios(open(os.path.join(self.carpeta, archivo), encoding="utf-8-sig").read()).replace("\r\n", "\n")
        secs = secciones(sin_codigo(texto))
        for req in requeridas:
            cuerpo = buscar_seccion(secs, req)
            if cuerpo is None:
                self.mal(archivo, "", f"falta la sección «## {req}»")
            elif req != "Resultado del revisor" and palabras(cuerpo) < 3:
                self.mal(archivo, req, "está vacía")
        if "PASA" not in texto:
            self.mal(archivo, "Resultado del revisor", "no muestra la salida del revisor con PASA")
        caras = buscar_seccion(secs, "Decisiones más caras de revertir") or ""
        esperadas = min(3, len(self.decisiones))
        listadas = len(re.findall(r"^\s*(?:[-*]|\d+\.)\s+\S", caras, re.M))
        if listadas < esperadas:
            self.mal(archivo, "Decisiones más caras de revertir", f"lista {listadas}; se esperan {esperadas}")
        self.revisar_texto(archivo, texto)
        self.revisar_rutas(archivo, texto)


def main():
    p = argparse.ArgumentParser(description="Revisa los planos de software antes de entregarlos.")
    p.add_argument("carpeta", help="carpeta con prd.md, design-doc.md, rfc.md…")
    p.add_argument("--repo", required=True, help="raíz del repositorio donde deben existir las rutas citadas")
    p.add_argument("--final", action="store_true", help="exige también informe-planos.md")
    a = p.parse_args()
    if not os.path.isdir(a.carpeta) or not os.path.isdir(a.repo):
        print("FALLA: la carpeta de planos o la del repo no existe")
        sys.exit(2)
    r = Revision(os.path.abspath(a.carpeta), os.path.abspath(a.repo))
    resumen = r.ejecutar(a.final)

    print(f"Planos: {a.carpeta}")
    print(f"Repo:   {a.repo}")
    print("Documentos: " + (", ".join(resumen) if resumen else "ninguno"))
    print(f"Rutas citadas: {r.rutas['existen']} existen en el repo, {r.rutas['nuevas']} marcadas (nuevo), "
          f"{r.rutas['fuera']} fuera del repo")
    if r.decisiones:
        print("Decisiones, de la más cara a la más barata de revertir:")
        etiqueta = {3: "alto", 2: "medio", 1: "bajo", 0: "sin costo"}
        for nivel, archivo, titulo in sorted(r.decisiones, key=lambda d: -d[0]):
            print(f"  [{etiqueta[nivel]}] {archivo} · {titulo}")
    if r.problemas:
        print(f"FALLA ({len(r.problemas)} problema{'s' if len(r.problemas) != 1 else ''})")
        for x in r.problemas:
            print(" -", x)
        sys.exit(1)
    print("PASA: secciones, decisiones con alternativas y trade-off, métricas medibles, P0 con prueba, "
          "vuelta atrás y rutas verificadas" + (" · informe completo" if a.final else ""))


if __name__ == "__main__":
    main()
