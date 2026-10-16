"""Calcula cuánto cuesta y cuánto tarda la IA de tu app, y simula 5 optimizaciones.

Uso:
  python costo_ia.py buscar <carpeta del proyecto>
      Encuentra dónde llamas a la IA (archivo:línea), qué modelos usas, si ya usas streaming o caché,
      cuánto miden tus prompts largos y qué archivos de registro de uso hay.

  python costo_ia.py medir <uso.csv | uso.jsonl | uso.json> [opciones]
      Lee tu registro de uso, calcula costo y latencia y escribe en --salida:
      informe-costo-ia.md y uso_normalizado.csv.

Opciones de «medir»:
  --precios RUTA         precios.json (por defecto: ../referencia/precios.json junto a este script)
  --salida CARPETA       dónde escribir el informe (por defecto: carpeta actual)
  --fijos f=N,g=M        tokens de la parte fija del prompt (sistema + herramientas + documentos fijos) por función; «*=N» para todas
  --simples f,g          funciones con tareas simples (clasificar, extraer, respuestas cortas) candidatas a modelo más barato
  --ya-streaming f,g     funciones que ya usan streaming («*» = todas)
  --ubicaciones RUTA     JSON {"funcion": "app/x.py:42"} o {"funcion": {"llamada": "...", "prompt": "..."}}
  --supuestos RUTA       JSON con supuestos que quieras cambiar (lista en referencia/optimizaciones.md)
  --dias N               días que cubre el archivo (si no trae fechas o quieres forzarlo)
  --entrada-incluye-cache auto|si|no   si tu columna de entrada ya incluye los tokens en caché (auto: según proveedor)
  --hoy AAAA-MM-DD       fecha de referencia (para pruebas)

Solo biblioteca estándar, Python 3.10 o superior. Nunca se cae por una fila rota: la ignora y la reporta.
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import sys
import unicodedata
from collections import defaultdict

SUPUESTOS = {
    "ttl_cache_s": 300,                       # la caché de Claude dura 5 min y se renueva con cada acierto
    "horas_activas_dia": 12,                  # si no hay fechas por llamada: horas del día con tráfico
    "recorte_prompt": 0.25,                   # fracción de la parte fija que se podría quitar (ajústala tras leer el prompt)
    "repeticion_respuestas": 0.05,            # fracción de preguntas idénticas si el registro no trae la entrada o su hash
    "ventana_respuestas_h": 24,               # una respuesta guardada sirve durante estas horas
    "factor_latencia_cache": 0.1,             # un token leído de caché tarda ~10 % de lo que tarda uno sin caché
    "factor_latencia_modelo_economico": 0.5,  # el modelo pequeño responde en ~la mitad del tiempo
    "latencia_respuesta_guardada_ms": 50,     # responder desde tu propia caché de respuestas
    "umbral_salida_simple": 100,              # sin --simples: una función con salida promedio <= esto se considera simple (clasificar, extraer)
    "dias_mes": 30,
    "modelo_economico": {},                   # {"anthropic": "claude-haiku-5-5"} para cambiar el destino del enrutado
}

RIESGO = {
    "a": (0, "Ninguno para la calidad: la respuesta es la misma. Técnico: el prefijo debe ser idéntico en cada llamada."),
    "b": (2, "Medio-alto: un modelo pequeño puede fallar en casos difíciles. Pruébalo con 20 casos reales antes (skill mejora-prompt)."),
    "c": (1, "Medio: quitar instrucciones o ejemplos puede cambiar respuestas. Empieza por duplicados y compara antes/después."),
    "d": (0, "Ninguno para la calidad y no cambia el costo. Requiere que tu pantalla muestre el texto mientras llega."),
    "e": (1, "Medio: respuestas viejas si tus datos cambian. Solo para preguntas idénticas y con caducidad."),
}
NOMBRE = {
    "a": "Caché de prompts (parte fija)",
    "b": "Modelo más barato para tareas simples (enrutar)",
    "c": "Recortar el prompt fijo",
    "d": "Streaming (respuesta en flujo)",
    "e": "Caché de respuestas repetidas",
}

# ---------------------------------------------------------------- utilidades


def clave_col(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


ALIAS = {
    "modelo": ["modelo", "model", "modelname", "modelid", "engine", "modelversion"],
    "funcion": ["funcion", "feature", "function", "endpoint", "ruta", "route", "tag", "task", "tarea",
                "casouso", "usecase", "accion", "action", "operacion", "operation", "componente"],
    "fecha": ["fecha", "timestamp", "time", "createdat", "created", "date", "ts", "datetime", "fechahora"],
    "entrada": ["tokensentrada", "inputtokens", "prompttokens", "prompttokencount", "intokens", "tokensin",
                "tokensinput"],
    "salida": ["tokenssalida", "outputtokens", "completiontokens", "candidatestokencount", "outtokens",
               "tokensout", "tokensoutput"],
    "pensamiento": ["thoughtstokencount"],
    "cache_lectura": ["tokenscachelectura", "cachereadinputtokens", "cachedtokens", "cachedcontenttokencount",
                      "cacheread", "tokenscacheread", "cachelectura", "cachereadtokens", "totalcachedtokens"],
    "cache_escritura": ["tokenscacheescritura", "cachecreationinputtokens", "cachecreationtokens", "cachewrite",
                        "tokenscachewrite", "cacheescritura", "cachewritetokens"],
    "latencia_ms": ["latenciams", "latencyms", "durationms", "elapsedms", "duracionms", "responsetimems",
                    "tiempoms", "latencia", "latency", "duration", "duracion", "elapsed"],
    "latencia_s": ["latencias", "latencys", "durations", "elapseds", "latencyseconds", "durationseconds",
                   "segundos", "seconds", "tiempos"],
    "ttft_ms": ["ttftms", "timetofirsttokenms", "primertokenms", "ttft"],
    "llamadas": ["llamadas", "calls", "count", "requests", "llamadasdia", "callsperday", "n", "peticiones"],
    "hash": ["hashentrada", "prompthash", "inputhash", "hash", "requesthash"],
    "texto": ["textoentrada", "pregunta", "usermessage", "mensaje", "inputtext", "query", "consulta", "question"],
}
SIN_UNIDAD = {"latencia", "latency", "duration", "duracion", "elapsed"}


def numero(v, campo):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        raise ValueError(f"valor no numérico en «{campo}»: {v!r}")
    if isinstance(v, (int, float)):
        x = float(v)
    else:
        s = str(v).strip().replace(" ", "").replace("_", "")
        if re.fullmatch(r"-?\d{1,3}(,\d{3})+(\.\d+)?", s):
            s = s.replace(",", "")
        elif s.count(",") == 1 and "." not in s:
            s = s.replace(",", ".")
        try:
            x = float(s)
        except ValueError:
            raise ValueError(f"valor no numérico en «{campo}»: {v!r}") from None
    if math.isnan(x) or math.isinf(x):
        raise ValueError(f"valor no numérico en «{campo}»: {v!r}")
    if x < 0:
        raise ValueError(f"valor negativo en «{campo}»: {v!r}")
    return x


def fecha(v):
    if v is None or str(v).strip() == "":
        return None
    if isinstance(v, (int, float)) or re.fullmatch(r"\d{9,13}(\.\d+)?", str(v).strip()):
        x = float(v)
        if x > 1e11:
            x /= 1000
        return dt.datetime.fromtimestamp(x, dt.timezone.utc).replace(tzinfo=None)
    s = str(v).strip().replace("Z", "+00:00")
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        d = None
        for f in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                d = dt.datetime.strptime(s, f)
                break
            except ValueError:
                pass
        if d is None:
            raise ValueError(f"fecha que no entiendo: {v!r}")
    if d.tzinfo:
        d = d.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return d


def aplanar(obj, prefijo=""):
    plano = {}
    for k, v in obj.items():
        nombre = f"{prefijo}.{k}" if prefijo else str(k)
        if isinstance(v, dict):
            plano.update(aplanar(v, nombre))
        else:
            plano[nombre] = v
    return plano


def usd(x, dec=None):
    if dec is None:
        dec = 2 if abs(x) >= 1 else 4
    if abs(x) < 0.5 * 10 ** -dec:
        x = 0.0  # evita «$-0.0000»
    return f"${x:,.{dec}f}"


def miles(x):
    return f"{x:,.0f}"


def ms(x):
    return "sin datos" if x is None else (f"{x/1000:.2f} s" if x >= 1000 else f"{x:.0f} ms")


def percentil(pares, q):
    """pares: lista de (valor, peso). Percentil ponderado (el primer valor que acumula q del peso)."""
    pares = sorted((v, w) for v, w in pares if v is not None and w > 0)
    total = sum(w for _, w in pares)
    if not total:
        return None
    acum = 0.0
    for v, w in pares:
        acum += w
        if acum >= q * total - 1e-9:
            return v
    return pares[-1][0]


# ---------------------------------------------------------------- precios


def cargar_precios(ruta):
    with open(ruta, encoding="utf-8-sig") as f:
        datos = json.load(f)
    modelos = {}
    for prov, p in datos["proveedores"].items():
        for clave, m in p["modelos"].items():
            modelos[clave] = dict(m, proveedor=prov)
    return datos, modelos


def normalizar_modelo(s: str) -> str:
    s = str(s).strip().lower()
    s = s.split("/")[-1]
    s = re.sub(r"^(?:[a-z]{2,6}\.)?anthropic\.", "", s)
    s = re.sub(r"-v\d+(:\d+)?$", "", s)
    return s.replace("@", "-")


def buscar_precio(modelo, modelos):
    s = normalizar_modelo(modelo)
    for clave in sorted(modelos, key=len, reverse=True):
        if s == clave or (s.startswith(clave) and s[len(clave)] in "-_:"):
            return clave
    return None


def precio(clave, modelos, total_entrada, hoy):
    m = modelos[clave]
    p = {k: m[k] for k in ("entrada", "cache_escritura", "cache_lectura", "salida")}
    if m.get("vigente_hasta") and hoy > dt.date.fromisoformat(m["vigente_hasta"]):
        p.update(m["siguiente"])
    if m.get("umbral") and total_entrada > m["umbral"]:
        p.update(m["sobre_umbral"])
    if p["cache_lectura"] is None:
        p["cache_lectura"] = p["entrada"]
    if p["cache_escritura"] is None:
        p["cache_escritura"] = p["entrada"]
    return p


def costo(p, e, cr, cw, s):
    return (e * p["entrada"] + cr * p["cache_lectura"] + cw * p["cache_escritura"] + s * p["salida"]) / 1e6


# ---------------------------------------------------------------- lectura del registro


def leer_registros(ruta):
    """Devuelve (lista de (num_linea, dict plano) | (num_linea, None, error))."""
    ext = os.path.splitext(ruta)[1].lower()
    try:
        texto = open(ruta, encoding="utf-8-sig").read()
    except UnicodeDecodeError:
        texto = open(ruta, encoding="latin-1").read()
    salida = []
    if ext in (".jsonl", ".ndjson") or (ext == ".json" and not texto.lstrip().startswith("[")):
        for i, linea in enumerate(texto.splitlines(), 1):
            if not linea.strip():
                continue
            try:
                obj = json.loads(linea)
                if not isinstance(obj, dict):
                    raise ValueError("la línea no es un objeto JSON")
                salida.append((i, aplanar(obj), None))
            except (json.JSONDecodeError, ValueError) as e:
                salida.append((i, None, f"JSON roto ({e.__class__.__name__})"))
    elif ext == ".json":
        try:
            lista = json.loads(texto)
        except json.JSONDecodeError as e:
            return [(e.lineno, None, "el archivo JSON está roto; no se pudo leer")]
        for i, obj in enumerate(lista, 1):
            salida.append((i, aplanar(obj), None) if isinstance(obj, dict) else (i, None, "el elemento no es un objeto"))
    else:
        # separador: el que más aparece en el encabezado (Excel en español suele usar «;»)
        primera = next((l for l in texto.splitlines() if l.strip()), "")
        sep = max(",;\t|", key=primera.count)
        lector = csv.reader(texto.splitlines(), delimiter=sep if primera.count(sep) else ",")
        try:
            cab = next(lector)
        except StopIteration:
            return []
        for i, fila in enumerate(lector, 2):
            if not any(c.strip() for c in fila):
                continue
            if len(fila) != len(cab):
                salida.append((i, None, f"tiene {len(fila)} columnas y el encabezado {len(cab)}"))
                continue
            salida.append((i, dict(zip(cab, fila)), None))
    return salida


def mapear_columnas(claves):
    """Para un conjunto de nombres de columna, decide cuál corresponde a cada campo."""
    norm = {}
    for c in claves:
        norm.setdefault(clave_col(c), c)
        norm.setdefault(clave_col(c.split(".")[-1]), c)
        if "." in c:  # usage.prompt_tokens_details.cached_tokens -> también por el último par
            norm.setdefault(clave_col("".join(c.split(".")[-2:])), c)
    mapa = {}
    for campo, alias in ALIAS.items():
        for a in alias:
            if a in norm:
                mapa[campo] = (norm[a], a)
                break
    return mapa


def normalizar(registros, modelos, args, avisos):
    filas, ignoradas, sin_precio = [], [], defaultdict(int)
    columnas_vistas = {}
    for linea, crudo, error in registros:
        if error:
            ignoradas.append((linea, error))
            continue
        firma = tuple(sorted(crudo))
        if firma not in columnas_vistas:
            columnas_vistas[firma] = mapear_columnas(crudo.keys())
        mapa = columnas_vistas[firma]
        val = lambda campo: crudo.get(mapa[campo][0]) if campo in mapa else None
        try:
            modelo = val("modelo")
            if modelo is None or not str(modelo).strip():
                raise ValueError("sin modelo")
            e = numero(val("entrada"), "entrada")
            s = numero(val("salida"), "salida")
            if e is None and s is None:
                raise ValueError("sin tokens de entrada ni de salida")
            e, s = e or 0.0, s or 0.0
            s += numero(val("pensamiento"), "pensamiento") or 0.0
            cr = numero(val("cache_lectura"), "cache_lectura") or 0.0
            cw = numero(val("cache_escritura"), "cache_escritura") or 0.0
            lat = numero(val("latencia_ms"), "latencia")
            if lat is None and "latencia_s" in mapa:
                lat = numero(val("latencia_s"), "latencia") * 1000 if val("latencia_s") not in (None, "") else None
            ttft = numero(val("ttft_ms"), "ttft")
            n = numero(val("llamadas"), "llamadas")
            n = 1.0 if n is None else n
            f = fecha(val("fecha")) if "fecha" in mapa else None
        except ValueError as ex:
            ignoradas.append((linea, str(ex)))
            continue
        clave = buscar_precio(modelo, modelos)
        if not clave:
            sin_precio[str(modelo)] += 1
            ignoradas.append((linea, f"modelo sin precio en precios.json: {modelo}"))
            continue
        prov = modelos[clave]["proveedor"]
        incluye = args.entrada_incluye_cache
        if incluye == "auto":
            incluye = "no" if mapa.get("entrada", ("", ""))[1] == "tokensentrada" or prov == "anthropic" else "si"
        if incluye == "si" and (cr or cw):
            if cr + cw > e + 0.5:
                avisos.add(f"Línea {linea} y quizá otras: la caché ({cr+cw:.0f}) es mayor que la entrada ({e:.0f}); revisa --entrada-incluye-cache.")
            e = max(0.0, e - cr - cw)
        h = val("hash")
        if h in (None, "") and val("texto") not in (None, ""):
            t = re.sub(r"\s+", " ", str(val("texto")).strip().lower())
            h = hashlib.sha1(t.encode()).hexdigest()[:16]
        func = val("funcion")
        filas.append({
            "linea": linea, "fecha": f, "funcion": str(func).strip() if func not in (None, "") else "(sin función)",
            "modelo": str(modelo).strip(), "clave": clave, "proveedor": prov, "n": n,
            "e": e, "cr": cr, "cw": cw, "s": s, "lat": lat, "ttft": ttft,
            "hash": str(h) if h not in (None, "") else None,
            "col_lat": mapa.get("latencia_ms", ("", ""))[1],
        })
    # latencia sin unidad que parece venir en segundos
    sin_u = [r for r in filas if r["col_lat"] in SIN_UNIDAD and r["lat"] is not None]
    if sin_u and max(r["lat"] for r in sin_u) < 100:
        for r in sin_u:
            r["lat"] *= 1000
        avisos.add("La columna de latencia no dice su unidad y todos sus valores son menores que 100: la tomé en segundos.")
    return filas, ignoradas, dict(sin_precio), columnas_vistas


# ---------------------------------------------------------------- análisis


def regresion(filas):
    """latencia = a + b·(entrada total/1000) + c·(salida/1000), mínimos cuadrados ponderados."""
    datos = [(1.0, (r["e"] + r["cr"] + r["cw"]) / 1000, r["s"] / 1000, r["lat"], r["n"]) for r in filas if r["lat"] is not None]
    if len(datos) < 10:
        return None
    A = [[0.0] * 3 for _ in range(3)]
    B = [0.0] * 3
    for x0, x1, x2, y, w in datos:
        x = (x0, x1, x2)
        for i in range(3):
            B[i] += w * x[i] * y
            for j in range(3):
                A[i][j] += w * x[i] * x[j]
    try:
        coef = resolver3(A, B)
    except ZeroDivisionError:
        return None
    a, b, c = coef
    if c <= 0:
        return None
    nota = ""
    if b < 0:
        b, nota = 0.0, "el efecto de la entrada no se distingue en tus datos (se tomó como 0)"
    wt = sum(d[4] for d in datos)
    media = sum(d[3] * d[4] for d in datos) / wt
    sst = sum(d[4] * (d[3] - media) ** 2 for d in datos)
    sse = sum(d[4] * (d[3] - (a + b * d[1] + c * d[2])) ** 2 for d in datos)
    r2 = 1 - sse / sst if sst else 0.0
    return {"a": a, "b": b / 1000, "c": c / 1000, "r2": r2, "n": len(datos), "nota": nota}


def resolver3(A, B):
    M = [A[i][:] + [B[i]] for i in range(3)]
    for col in range(3):
        piv = max(range(col, 3), key=lambda r: abs(M[r][col]))
        if abs(M[piv][col]) < 1e-12:
            raise ZeroDivisionError
        M[col], M[piv] = M[piv], M[col]
        for r in range(3):
            if r != col:
                fac = M[r][col] / M[col][col]
                for k in range(col, 4):
                    M[r][k] -= fac * M[col][k]
    return [M[i][3] / M[i][i] for i in range(3)]


def calcular_dias(filas, args, avisos):
    if args.dias:
        return float(args.dias), f"{args.dias:g} (indicado con --dias)"
    fechas = [r["fecha"] for r in filas if r["fecha"]]
    if fechas:
        d = (max(fechas).date() - min(fechas).date()).days + 1
        return float(d), f"{d} (del {min(fechas).date()} al {max(fechas).date()})"
    avisos.add("El archivo no trae fechas: supuse que cubre 1 día. Usa --dias si cubre otro periodo.")
    return 1.0, "1 (supuesto: el archivo no trae fechas)"


def aciertos_cache(filas, sup, dias):
    """Probabilidad de que el prefijo siga en caché en cada llamada (medido con fechas o estimado)."""
    ttl = sup["ttl_cache_s"]
    grupos = defaultdict(list)
    for r in filas:
        grupos[(r["funcion"], r["clave"])].append(r)
    metodo = {}
    for (func, _), rs in grupos.items():
        con_fecha = [r for r in rs if r["fecha"] and r["n"] == 1]
        if len(con_fecha) == len(rs) and len(rs) > 1:
            rs.sort(key=lambda r: r["fecha"])
            previo = None
            for r in rs:
                r["p_hit"] = 1.0 if previo and (r["fecha"] - previo).total_seconds() <= ttl else 0.0
                previo = r["fecha"]
            metodo[func] = "medido con las fechas de tus llamadas"
        else:
            por_dia = sum(r["n"] for r in rs) / dias
            tasa = por_dia / (sup["horas_activas_dia"] * 3600)
            p = 1 - math.exp(-ttl * tasa)
            for r in rs:
                r["p_hit"] = p
            metodo[func] = f"estimado: {por_dia:,.0f} llamadas/día repartidas en {sup['horas_activas_dia']} h"
    return metodo


def repeticiones(filas, sup):
    con_hash = [r for r in filas if r["hash"]]
    if con_hash and len(con_hash) == len(filas):
        ventana = sup["ventana_respuestas_h"] * 3600
        visto = {}
        for r in sorted(filas, key=lambda r: (r["fecha"] or dt.datetime.min, r["linea"])):
            k = (r["funcion"], r["hash"])
            t = r["fecha"]
            antes = visto.get(k)
            r["p_rep"] = 1.0 if antes is not None and (t is None or antes is None or (t - antes).total_seconds() <= ventana) else 0.0
            visto[k] = t if antes is None or r["p_rep"] == 0.0 else antes
        return f"medido: misma pregunta en la misma función dentro de {sup['ventana_respuestas_h']} h"
    for r in filas:
        r["p_rep"] = sup["repeticion_respuestas"]
    return f"supuesto {sup['repeticion_respuestas']:.0%} (tu registro no trae la pregunta ni su hash)"


def parte_fija(filas, args):
    fijos_arg = {}
    for par in (args.fijos or "").split(","):
        if "=" in par:
            k, v = par.split("=", 1)
            fijos_arg[k.strip()] = float(v)
    por_func = defaultdict(list)
    for r in filas:
        por_func[r["funcion"]].append(r)
    fijos, origen = {}, {}
    for func, rs in por_func.items():
        if func in fijos_arg or "*" in fijos_arg:
            fijos[func] = fijos_arg.get(func, fijos_arg.get("*"))
            origen[func] = "medido en tu código (--fijos)"
            continue
        con_cache = [r for r in rs if r["cr"] + r["cw"] > 0]
        if con_cache:
            w = sum(r["n"] for r in con_cache)
            fijos[func] = sum((r["cr"] + r["cw"]) * r["n"] for r in con_cache) / w
            origen[func] = "medido con los tokens de caché del registro"
        else:
            fijos[func] = min(r["e"] + r["cr"] + r["cw"] for r in rs)
            origen[func] = "estimado: la entrada más pequeña observada (tope superior; confírmalo con --fijos)"
    return fijos, origen


def simular(r, F, ctx, cache=False, recorte=0.0, modelo=None, rep=False):
    """Costo esperado por llamada y lista de (latencia, peso) para una fila, bajo un escenario."""
    sup, modelos, hoy = ctx["sup"], ctx["modelos"], ctx["hoy"]
    reg = ctx["regs"].get(r["clave"]) or ctx["regs"].get("_global")
    clave = modelo or r["clave"]
    total = r["e"] + r["cr"] + r["cw"]
    Fr = min(F or 0.0, total)
    quitar = Fr * recorte
    total2 = total - quitar
    F2 = Fr - quitar
    esc = total2 / total if total else 1.0
    minimo = modelos[clave].get("minimo_cache") or 0
    if cache and F2 > 0 and F2 >= minimo:
        p = r["p_hit"]
        cr2, cw2 = F2 * p, F2 * (1 - p)
        e2 = total2 - F2
    else:
        e2, cr2, cw2 = r["e"] * esc, r["cr"] * esc, r["cw"] * esc
    c = costo(precio(clave, modelos, total2, hoy), e2, cr2, cw2, r["s"])
    p_rep = r["p_rep"] if rep else 0.0
    lat = None
    if r["lat"] is not None:
        lat = r["lat"]
        if reg:
            lat -= reg["b"] * quitar
            nuevos = max(0.0, cr2 - r["cr"] * esc)
            lat -= reg["b"] * (1 - sup["factor_latencia_cache"]) * nuevos
        if modelo and modelo != r["clave"]:
            lat *= sup["factor_latencia_modelo_economico"]
        lat = max(lat, 0.1 * r["lat"])
    pares = [(lat, r["n"] * (1 - p_rep))]
    if p_rep:
        pares.append((sup["latencia_respuesta_guardada_ms"] if lat is not None else None, r["n"] * p_rep))
    return c * (1 - p_rep), pares


def economico_para(r, ctx):
    prov = r["proveedor"]
    destino = ctx["sup"]["modelo_economico"].get(prov) or ctx["precios"]["proveedores"][prov].get("modelo_economico")
    if not destino or destino not in ctx["modelos"] or destino == r["clave"]:
        return None
    total = r["e"] + r["cr"] + r["cw"]
    p_actual = precio(r["clave"], ctx["modelos"], total, ctx["hoy"])
    p_dest = precio(destino, ctx["modelos"], total, ctx["hoy"])
    if p_dest["entrada"] >= p_actual["entrada"] and p_dest["salida"] >= p_actual["salida"]:
        return None
    return destino


def escenario(filas, fijos, ctx, opciones_por_func):
    """opciones_por_func: {funcion: set de letras}. Devuelve (costo total periodo, pares de latencia, costo por funcion)."""
    total, pares, por_func = 0.0, [], defaultdict(float)
    for r in filas:
        ops = opciones_por_func.get(r["funcion"], set())
        modelo = economico_para(r, ctx) if "b" in ops else None
        c, pp = simular(r, fijos.get(r["funcion"]), ctx, cache="a" in ops,
                        recorte=ctx["sup"]["recorte_prompt"] if "c" in ops else 0.0, modelo=modelo, rep="e" in ops)
        total += c * r["n"]
        por_func[r["funcion"]] += c * r["n"]
        pares.extend(pp)
    return total, pares, por_func


# ---------------------------------------------------------------- informe


def tabla(cab, filas):
    out = ["| " + " | ".join(cab) + " |", "|" + "|".join("---" for _ in cab) + "|"]
    out += ["| " + " | ".join(str(x) for x in f) + " |" for f in filas]
    return "\n".join(out)


def ubicacion(ubic, func, tipo):
    u = ubic.get(func)
    if isinstance(u, dict):
        return u.get(tipo) or u.get("llamada") or u.get("prompt") or "sin ubicar"
    return u or "sin ubicar (pásala con --ubicaciones)"


def medir(args):
    aqui = os.path.dirname(os.path.abspath(__file__))
    ruta_precios = args.precios or os.path.join(aqui, "..", "referencia", "precios.json")
    precios_datos, modelos = cargar_precios(ruta_precios)
    hoy = dt.date.fromisoformat(args.hoy) if args.hoy else dt.date.today()
    sup = dict(SUPUESTOS)
    if args.supuestos:
        with open(args.supuestos, encoding="utf-8-sig") as f:
            sup.update(json.load(f))
    avisos = set()

    print(f"Precios: {os.path.abspath(ruta_precios)}")
    viejos = []
    for prov, p in precios_datos["proveedores"].items():
        edad = (hoy - dt.date.fromisoformat(p["consultado"])).days
        print(f"  {prov}: consultados el {p['consultado']} ({edad} días) · verifica en {p['fuente']}")
        if edad > 60:
            viejos.append(f"{prov} ({edad} días)")
    if viejos:
        avisos.add("PRECIOS VIEJOS: " + ", ".join(viejos) + ". Verifícalos en la URL fuente y actualiza precios.json antes de decidir.")
        print("  AVISO: precios con más de 60 días:", ", ".join(viejos))
    for clave, m in modelos.items():
        if m.get("vigente_hasta"):
            cambio = dt.date.fromisoformat(m["vigente_hasta"])
            if hoy <= cambio and (cambio - hoy).days <= sup["dias_mes"]:
                avisos.add(f"{clave} cambia de precio después del {cambio}: la proyección mensual de ese modelo puede quedarse corta.")

    registros = leer_registros(args.archivo)
    filas, ignoradas, sin_precio, columnas = normalizar(registros, modelos, args, avisos)
    print(f"Filas leídas: {len(registros)} · usadas: {len(filas)} · ignoradas: {len(ignoradas)}")
    for linea, motivo in ignoradas[:10]:
        print(f"  ignorada línea {linea}: {motivo}")
    if len(ignoradas) > 10:
        print(f"  ... y {len(ignoradas) - 10} más (ver el informe)")
    if not filas:
        print("FALLA: ninguna fila válida. Revisa el formato en referencia/formato_uso.md")
        return 1

    dias, dias_txt = calcular_dias(filas, args, avisos)
    # latencia: un ajuste por modelo (cada modelo tiene su velocidad) y uno global de respaldo
    regs = {"_global": regresion(filas)}
    for clave in {r["clave"] for r in filas}:
        rs = [r for r in filas if r["clave"] == clave and r["lat"] is not None]
        if len(rs) >= 30:
            regs[clave] = regresion(rs)
    regs = {k: v for k, v in regs.items() if v}
    ctx = {"sup": sup, "regs": regs, "modelos": modelos, "hoy": hoy, "precios": precios_datos}
    metodo_hit = aciertos_cache(filas, sup, dias)
    metodo_rep = repeticiones(filas, sup)
    fijos, origen_fijos = parte_fija(filas, args)
    ubic = {}
    if args.ubicaciones:
        with open(args.ubicaciones, encoding="utf-8-sig") as f:
            ubic = json.load(f)
    ya_stream = {x.strip() for x in (args.ya_streaming or "").split(",") if x.strip()}

    # costo actual
    for r in filas:
        tot = r["e"] + r["cr"] + r["cw"]
        r["costo"] = costo(precio(r["clave"], modelos, tot, hoy), r["e"], r["cr"], r["cw"], r["s"])
    llamadas = sum(r["n"] for r in filas)
    total = sum(r["costo"] * r["n"] for r in filas)
    mes = lambda x: x / dias * sup["dias_mes"]
    funcs = sorted({r["funcion"] for r in filas}, key=lambda f: -sum(r["costo"] * r["n"] for r in filas if r["funcion"] == f))
    lat_antes = [(r["lat"], r["n"]) for r in filas]
    p50, p95 = percentil(lat_antes, 0.5), percentil(lat_antes, 0.95)

    # simulaciones por optimización y función
    simples_arg = {x.strip() for x in (args.simples or "").split(",") if x.strip()}
    stats = {}
    for f in funcs:
        rs = [r for r in filas if r["funcion"] == f]
        w = sum(r["n"] for r in rs)
        stats[f] = {
            "n": w, "costo": sum(r["costo"] * r["n"] for r in rs),
            "e_tot": sum((r["e"] + r["cr"] + r["cw"]) * r["n"] for r in rs) / w,
            "s": sum(r["s"] * r["n"] for r in rs) / w,
            "cr": sum(r["cr"] * r["n"] for r in rs) / w,
            "p50": percentil([(r["lat"], r["n"]) for r in rs], 0.5),
            "p95": percentil([(r["lat"], r["n"]) for r in rs], 0.95),
            "modelos": sorted({r["clave"] for r in rs}),
            "proveedor": rs[0]["proveedor"],
        }
    if simples_arg:
        simples = simples_arg & set(funcs)
        criterio_simple = "indicadas por ti tras revisar el código (--simples)"
    else:
        simples = {f for f in funcs if stats[f]["s"] <= sup["umbral_salida_simple"]}
        criterio_simple = f"heurística: salida promedio <= {sup['umbral_salida_simple']} tokens (confírmalo leyendo el código)"

    resultados = {}  # letra -> {func: ahorro periodo}
    motivos = {}     # (letra, func) -> por qué no aplica
    for letra in "abce":
        resultados[letra] = {}
        for f in funcs:
            rs_f = [r for r in filas if r["funcion"] == f]
            if letra == "b" and f not in simples:
                motivos[(letra, f)] = "no aplica (tarea no simple)"
                continue
            if letra == "b" and not any(economico_para(r, ctx) for r in rs_f):
                motivos[(letra, f)] = "no aplica (ya usa el modelo barato)"
                continue
            if letra == "a":
                minimo = max(modelos[k].get("minimo_cache") or 0 for k in stats[f]["modelos"])
                if fijos[f] < minimo:
                    motivos[(letra, f)] = f"no aplica (parte fija {miles(fijos[f])} < mínimo {miles(minimo)} del modelo)"
                    continue
            if letra == "e" and not any(r["p_rep"] for r in rs_f):
                motivos[(letra, f)] = "no aplica (sin preguntas repetidas)"
                continue
            c_esc, _, _ = escenario([r for r in filas if r["funcion"] == f], fijos, ctx, {f: {letra}})
            resultados[letra][f] = stats[f]["costo"] - c_esc
    lat_esc = {}
    for letra in "abce":
        ops = {f: {letra} for f in resultados[letra] if resultados[letra][f] > 0}
        c_esc, pares, _ = escenario(filas, fijos, ctx, ops)
        lat_esc[letra] = (total - c_esc, percentil(pares, 0.5), percentil(pares, 0.95), ops)

    # streaming: espera percibida = tiempo al primer token
    def ttft(r):
        if r["ttft"] is not None:
            return r["ttft"]
        reg = regs.get(r["clave"]) or regs.get("_global")
        if r["lat"] is None or not reg:
            return None
        return min(r["lat"], max(0.0, reg["a"] + reg["b"] * (r["e"] + r["cr"] + r["cw"])))
    stream_por_func = {}
    for f in funcs:
        rs = [r for r in filas if r["funcion"] == f]
        if f in ya_stream or "*" in ya_stream:
            continue
        antes = percentil([(r["lat"], r["n"]) for r in rs], 0.5)
        despues = percentil([(ttft(r), r["n"]) for r in rs], 0.5)
        if antes is not None and despues is not None:
            stream_por_func[f] = (antes, despues)
    pares_stream = [(ttft(r) if (r["funcion"] in stream_por_func) else r["lat"], r["n"]) for r in filas]
    s50 = percentil(pares_stream, 0.5)

    # top 3 por ahorro en dinero
    candidatos = [(ahorro, RIESGO[letra][0], letra, f) for letra in "abce" for f, ahorro in resultados[letra].items() if ahorro > 0.0005 * total]
    candidatos.sort(key=lambda x: (-x[0], x[1]))
    top, usados = [], set()
    for ahorro, _, letra, f in candidatos:
        # recortar y cachear el mismo prefijo se combinan; el modelo barato también: se permiten juntos
        if (letra, f) in usados:
            continue
        top.append((letra, f, ahorro))
        usados.add((letra, f))
        if len(top) == 3:
            break
    ops_top = defaultdict(set)
    for letra, f, _ in top:
        ops_top[f].add(letra)
    c_top, pares_top, por_func_top = escenario(filas, fijos, ctx, ops_top)

    # ------------------------------------------------ escribir informe
    os.makedirs(args.salida, exist_ok=True)
    L = []
    L.append("# Informe de costo y velocidad de IA\n")
    L.append(f"Generado por `costo_ia.py` (skill calcula-costo-ia de Lumière Autómata) el {hoy}. "
             "Todos los números salen de tu registro y de `precios.json`; los supuestos están en la sección 6.\n")
    L.append("## 0. Datos usados\n")
    L.append(tabla(["Dato", "Valor"], [
        ["Archivo", f"`{os.path.basename(args.archivo)}`"],
        ["Filas leídas / usadas / ignoradas", f"{len(registros)} / {len(filas)} / {len(ignoradas)}"],
        ["Llamadas representadas", miles(llamadas)],
        ["Días que cubre", dias_txt],
        ["Precios", "; ".join(f"{k}: {p['consultado']} ({p['fuente']})" for k, p in precios_datos['proveedores'].items())],
    ]))
    L.append("\nLos precios cambian: verifícalos en esas URL antes de decidir.\n")
    if avisos:
        L.append("**Avisos**\n")
        L += [f"- {a}" for a in sorted(avisos)]
        L.append("")

    L.append("## 1. Cuánto cuesta hoy\n")
    L.append(tabla(["Periodo", "Costo (USD)"], [
        ["Todo el archivo", usd(total)], ["Por día", usd(total / dias)],
        [f"Proyección a {sup['dias_mes']} días", usd(mes(total))], ["Por llamada (promedio)", usd(total / llamadas, 6)],
    ]))
    L.append("\n### Por modelo\n")
    filas_m = []
    for clave in sorted({r["clave"] for r in filas}):
        rs = [r for r in filas if r["clave"] == clave]
        c = sum(r["costo"] * r["n"] for r in rs)
        p = modelos[clave]
        filas_m.append([f"`{clave}`", miles(sum(r["n"] for r in rs)), usd(mes(c)), f"{c/total:.0%}",
                        f"${p['entrada']} / ${p['cache_lectura']} / ${p['cache_escritura']} / ${p['salida']}"])
    L.append(tabla(["Modelo", "Llamadas", "Costo/mes", "% del total", "Precio entrada / caché lectura / caché escritura / salida por MTok"], filas_m))
    L.append("\n### Por función de tu app\n")
    filas_f = []
    for f in funcs:
        st = stats[f]
        rep = min(1.0, fijos[f] / st["e_tot"]) if st["e_tot"] else 0
        filas_f.append([f, miles(st["n"] / dias), usd(mes(st["costo"])), f"{st['costo']/total:.0%}", miles(st["e_tot"]),
                        miles(st["s"]), f"{rep:.0%}", f"{st['cr']/st['e_tot']:.0%}" if st["e_tot"] else "0%",
                        ms(st["p50"]), ms(st["p95"])])
    L.append(tabla(["Función", "Llamadas/día", "Costo/mes", "%", "Entrada prom.", "Salida prom.",
                    "Parte fija (se repite)", "Ya leída de caché", "p50", "p95"], filas_f))
    L.append("\n«Parte fija» = tokens fijos de la función ÷ entrada promedio. Origen de la parte fija:\n")
    L += [f"- **{f}**: {miles(fijos[f])} tokens, {origen_fijos[f]}." for f in funcs]

    L.append("\n## 2. Cuánto tarda hoy\n")
    L.append(f"- Latencia total de una llamada: **p50 {ms(p50)}**, **p95 {ms(p95)}** (p50 = la mitad de las llamadas tarda menos que esto; p95 = 95 de cada 100).")
    if regs:
        L.append("- De dónde sale el tiempo, medido con tus llamadas (un ajuste por modelo con 30 filas o más; «todos» se usa para los demás):\n")
        filas_r = []
        todos_con_ajuste = all(r["clave"] in regs for r in filas)
        for k, reg in sorted(regs.items()):
            if k == "_global" and todos_con_ajuste:
                continue
            filas_r.append(["todos" if k == "_global" else f"`{k}`", reg["n"], f"{reg['a']:.0f} ms", f"{reg['b']*1000:.1f} ms",
                            f"{reg['c']*100:.0f} ms", f"{reg['r2']:.2f}", reg["nota"] or ""])
        L.append(tabla(["Modelo", "Filas", "Fijo por llamada", "Por cada 1,000 tokens de entrada", "Por cada 100 tokens de salida", "R²", "Nota"], filas_r))
        L.append("\nR² cerca de 1 = el ajuste explica bien tus tiempos; cerca de 0 = hay otra causa (red, colas, herramientas).\n")
        L.append("- Lectura: si la salida pesa mucho más que la entrada, lo que más acelera es pedir respuestas más cortas o usar streaming; si pesa la entrada, la caché y el recorte.")
    else:
        L.append("- No hay suficientes latencias (mínimo 10 filas) para medir de dónde sale el tiempo: los ahorros de latencia de la sección 3 no se pueden calcular.")

    L.append("\n## 3. Simulación de las 5 optimizaciones\n")
    L.append("Cada fila aplica UNA optimización, sola, en las funciones donde ahorra. Supuestos en la sección 6.\n")
    filas_s = []
    for letra in "abcde":
        if letra == "d":
            filas_s.append([NOMBRE["d"], ", ".join(stream_por_func) or "ninguna (ya la usan o faltan datos)", usd(mes(total)), "$0 (0%)",
                            (f"total {ms(p50)} igual; espera percibida p50 {ms(p50)} → {ms(s50)}" if stream_por_func else "sin datos para estimar el primer token"), RIESGO["d"][1]])
            continue
        ahorro, n50, n95, ops = lat_esc[letra]
        donde = ", ".join(ops) or "ninguna (no ahorra)"
        filas_s.append([NOMBRE[letra], donde, usd(mes(total - ahorro)), f"{usd(mes(ahorro))} ({ahorro/total:.0%})",
                        f"p50 {ms(p50)} → {ms(n50)}; p95 {ms(p95)} → {ms(n95)}", RIESGO[letra][1]])
    L.append(tabla(["Optimización", "Dónde aplica", "Costo/mes después", "Ahorro/mes", "Latencia", "Riesgo para la calidad"], filas_s))
    L.append("\n### Detalle por función (ahorro al mes; negativo = sale más caro)\n")
    det = []
    for f in funcs:
        celdas = [f]
        for letra in "abce":
            if f in resultados[letra]:
                v = mes(resultados[letra][f])
                celdas.append(usd(0.0 if abs(v) < 0.00005 else v))
            else:
                celdas.append(motivos.get((letra, f), "no aplica"))
        celdas.append(f"{ms(stream_por_func[f][0])} → {ms(stream_por_func[f][1])}" if f in stream_por_func else "no aplica")
        det.append(celdas)
    L.append(tabla(["Función", "(a) Caché de prompts", "(b) Modelo barato", "(c) Recortar", "(e) Caché de respuestas", "(d) Streaming: espera p50"], det))
    L.append("\nNotas: (a) la caché solo funciona si la parte fija llega al mínimo del modelo; si el resultado es negativo, "
             "tus llamadas están tan separadas que pagas la escritura (más cara) sin aprovechar la lectura. "
             "En OpenAI y Gemini la caché ya es automática: el ahorro llega al poner lo fijo al inicio y lo variable al final. "
             "(d) streaming no baja el costo ni el tiempo total: baja la espera que siente tu usuario. "
             "Referencia: Anthropic reporta que la caché de prompts reduce hasta 90 % el costo y hasta 85 % la latencia en prompts largos "
             "(https://claude.com/blog/prompt-caching).\n")

    L.append("## 4. Antes y después (top 3 aplicado junto)\n")
    if top:
        L.append(tabla(["Métrica", "Antes", "Después", "Cambio"], [
            [f"Costo/mes ({sup['dias_mes']} días)", usd(mes(total)), usd(mes(c_top)), f"-{(total - c_top)/total:.0%}"],
            ["Costo por llamada", usd(total / llamadas, 6), usd(c_top / llamadas, 6), ""],
            ["Latencia p50", ms(p50), ms(percentil(pares_top, 0.5)), ""],
            ["Latencia p95", ms(p95), ms(percentil(pares_top, 0.95)), ""],
        ]))
        L.append("\nPor función (costo/mes): " + "; ".join(f"{f}: {usd(mes(stats[f]['costo']))} → {usd(mes(por_func_top[f]))}" for f in funcs) + ".\n")
    else:
        L.append("Ninguna optimización de costo ahorra con tus datos. Revisa los supuestos de la sección 6.\n")

    L.append("## 5. Top 3 cambios recomendados\n")
    L.append("Orden: mayor ahorro mensual en dinero; si empatan, el de menor riesgo. **Nada se aplica a tu código sin tu permiso.**\n")
    for i, (letra, f, ahorro) in enumerate(top, 1):
        st = stats[f]
        prov = st["proveedor"]
        if letra == "a":
            que = ("Marca la parte fija con `cache_control` (o el `cache_control` automático de la petición) y deja al inicio solo lo que no cambia: nada de fechas, nombres ni la pregunta del usuario antes del corte."
                   if prov == "anthropic" else "La caché es automática: mueve todo lo fijo al inicio del prompt y lo variable (fecha, usuario, pregunta) al final, para que el inicio sea idéntico en cada llamada.")
            donde = ubicacion(ubic, f, "prompt")
        elif letra == "b":
            destino = next((economico_para(r, ctx) for r in filas if r["funcion"] == f and economico_para(r, ctx)), "?")
            que = f"Cambia el modelo de `{', '.join(st['modelos'])}` a `{destino}` solo en esta función, o enruta: `{destino}` primero y el modelo grande si la respuesta no pasa tu validación."
            donde = ubicacion(ubic, f, "llamada")
        elif letra == "c":
            que = f"Recorta ~{sup['recorte_prompt']:.0%} de la parte fija (~{miles(fijos[f]*sup['recorte_prompt'])} tokens): quita instrucciones repetidas, ejemplos de más y texto que el modelo no usa."
            donde = ubicacion(ubic, f, "prompt")
        else:
            que = "Guarda la respuesta por (función, pregunta normalizada) con caducidad y reutilízala cuando llegue la misma pregunta."
            donde = ubicacion(ubic, f, "llamada")
        L.append(f"{i}. **{NOMBRE[letra]} en `{f}`** — ahorro ≈ {usd(mes(ahorro))}/mes ({ahorro/total:.0%} del total).")
        L.append(f"   - Dónde: `{donde}`")
        L.append(f"   - Qué cambiar: {que}")
        L.append(f"   - Riesgo: {RIESGO[letra][1]}")
        L.append("   - Cómo comprobarlo: aplica el cambio, junta un día de registros nuevos y vuelve a correr `costo_ia.py medir`.")
    if stream_por_func:
        mejor = max(stream_por_func, key=lambda f: stream_por_func[f][0] - stream_por_func[f][1])
        a_, d_ = stream_por_func[mejor]
        if a_ - d_ >= 1000:
            L.append(f"\nAdemás, para velocidad (no cambia el costo): **streaming en `{mejor}`** — la espera percibida p50 pasa de {ms(a_)} a ~{ms(d_)}. "
                     f"Dónde: `{ubicacion(ubic, mejor, 'llamada')}`. Usa `stream=True` (o `messages.stream`) y muestra el texto mientras llega.")
    L.append("")

    L.append("## 6. Supuestos\n")
    L.append(tabla(["Supuesto", "Valor", "¿Medido o supuesto?"], [
        ["Acierto de caché de prompts", f"TTL {sup['ttl_cache_s']} s", "; ".join(f"{f}: {m}" for f, m in metodo_hit.items())],
        ["Tareas simples para (b)", ", ".join(sorted(simples)) or "ninguna", criterio_simple],
        ["Modelo barato por proveedor", ", ".join(f"{p}: {sup['modelo_economico'].get(p) or d.get('modelo_economico')}" for p, d in precios_datos['proveedores'].items()), "elegido en precios.json; cámbialo en supuestos"],
        ["Recorte posible del prompt fijo (c)", f"{sup['recorte_prompt']:.0%}", "supuesto: ajústalo tras leer el prompt"],
        ["Preguntas repetidas (e)", f"{sum(r['p_rep'] * r['n'] for r in filas) / llamadas:.0%} de todas las llamadas", metodo_rep],
        ["Velocidad de un token leído de caché", f"{sup['factor_latencia_cache']:.0%} del normal", "supuesto"],
        ["Velocidad del modelo barato", f"{sup['factor_latencia_modelo_economico']:.0%} del tiempo actual", "supuesto: mídelo con 20 llamadas reales"],
        ["Respuesta desde tu caché de respuestas", f"{sup['latencia_respuesta_guardada_ms']} ms", "supuesto"],
        ["Espera percibida con streaming", "tiempo al primer token", "medido (columna ttft)" if any(r["ttft"] for r in filas) else "estimado con el modelo de latencia de la sección 2"],
        ["Mes", f"{sup['dias_mes']} días", "convención"],
    ]))
    L.append("\nAl cambiar de modelo se supone que el número de tokens no cambia; entre generaciones de tokenizador puede variar (Claude 4.7+ produce ~30 % más tokens que 4.6 y anteriores).\n")

    L.append("## 7. Cálculo de ejemplo (para revisarlo a mano)\n")
    r = filas[0]
    tot = r["e"] + r["cr"] + r["cw"]
    p = precio(r["clave"], modelos, tot, hoy)
    L.append(f"Línea {r['linea']} del archivo · función `{r['funcion']}` · modelo `{r['modelo']}` → precio `{r['clave']}`:\n")
    L.append("```")
    L.append(f"entrada sin caché   {r['e']:>10,.0f} tokens × ${p['entrada']}/MTok = ${r['e']*p['entrada']/1e6:.6f}")
    L.append(f"lectura de caché    {r['cr']:>10,.0f} tokens × ${p['cache_lectura']}/MTok = ${r['cr']*p['cache_lectura']/1e6:.6f}")
    L.append(f"escritura de caché  {r['cw']:>10,.0f} tokens × ${p['cache_escritura']}/MTok = ${r['cw']*p['cache_escritura']/1e6:.6f}")
    L.append(f"salida              {r['s']:>10,.0f} tokens × ${p['salida']}/MTok = ${r['s']*p['salida']/1e6:.6f}")
    L.append(f"total de la llamada                                  = ${r['costo']:.6f}" + (f"  (× {r['n']:g} llamadas)" if r["n"] != 1 else ""))
    L.append("```\n")

    L.append("## 8. Filas ignoradas\n")
    if ignoradas:
        L += [f"- Línea {l}: {m}" for l, m in ignoradas[:50]]
        if len(ignoradas) > 50:
            L.append(f"- ... y {len(ignoradas) - 50} más.")
        if sin_precio:
            L.append("\nModelos sin precio (agrégalos a `precios.json` con su fuente): " + ", ".join(f"`{m}` ({n} filas)" for m, n in sin_precio.items()))
    else:
        L.append("Ninguna.")
    L.append("\n## Columnas reconocidas\n")
    for mapa in list(columnas.values())[:3]:
        L.append("- " + ", ".join(f"{campo} ← `{col}`" for campo, (col, _) in sorted(mapa.items())))

    ruta_inf = os.path.join(args.salida, "informe-costo-ia.md")
    with open(ruta_inf, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    ruta_csv = os.path.join(args.salida, "uso_normalizado.csv")
    with open(ruta_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["linea_origen", "fecha", "funcion", "modelo", "modelo_precio", "proveedor", "llamadas", "tokens_entrada",
                    "tokens_cache_lectura", "tokens_cache_escritura", "tokens_salida", "latencia_ms", "ttft_ms", "hash_entrada", "costo_usd"])
        for r in filas:
            w.writerow([r["linea"], r["fecha"].isoformat(sep=" ") if r["fecha"] else "", r["funcion"], r["modelo"], r["clave"], r["proveedor"],
                        f"{r['n']:g}", f"{r['e']:g}", f"{r['cr']:g}", f"{r['cw']:g}", f"{r['s']:g}",
                        "" if r["lat"] is None else f"{r['lat']:g}", "" if r["ttft"] is None else f"{r['ttft']:g}",
                        r["hash"] or "", f"{r['costo']:.8f}"])

    print(f"Días: {dias_txt}")
    print(f"Costo: {usd(total)} en el archivo · {usd(total/dias)}/día · {usd(mes(total))}/mes · {usd(total/llamadas, 6)}/llamada")
    print(f"Latencia: p50 {ms(p50)} · p95 {ms(p95)}")
    for letra in "abce":
        print(f"  ({letra}) {NOMBRE[letra]}: ahorro {usd(mes(lat_esc[letra][0]))}/mes")
    print(f"  (d) {NOMBRE['d']}: $0; " + (f"espera percibida p50 {ms(p50)} → {ms(s50)}" if stream_por_func else "sin datos para estimar el primer token"))
    if top:
        print(f"Top 3 junto: {usd(mes(total))}/mes → {usd(mes(c_top))}/mes (-{(total-c_top)/total:.0%})")
        for i, (letra, f, ahorro) in enumerate(top, 1):
            print(f"  {i}. {NOMBRE[letra]} en {f}: {usd(mes(ahorro))}/mes")
    print(f"Escrito: {ruta_inf}")
    print(f"Escrito: {ruta_csv}")
    return 0


# ---------------------------------------------------------------- buscar

EXT_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs", ".go", ".rb", ".php", ".java", ".kt", ".cs", ".swift", ".dart"}
SALTAR = {".git", "node_modules", "venv", ".venv", "env", "__pycache__", "dist", "build", ".next", ".expo", "vendor", "site-packages"}
PAT = {
    "sdk": re.compile(r"(import\s+anthropic|from\s+anthropic|@anthropic-ai/sdk|import\s+openai|from\s+openai|require\(['\"]openai['\"]\)|from\s+['\"]openai['\"]|google\.genai|google-genai|@google/genai|google\.generativeai|@google/generative-ai|litellm|langchain|@ai-sdk/)"),
    "llamada": re.compile(r"(messages\.create|messages\.stream|chat\.completions\.create|responses\.create|generate_content|generateContent|generateText|streamText|litellm\.completion|\.invoke\()"),
    "modelo": re.compile(r"['\"`]((?:claude|gpt|gemini|o[134])(?:-[\w.]+)+)['\"`]"),
    "streaming": re.compile(r"(stream\s*=\s*True|stream:\s*true|messages\.stream|\.stream\(|streamText|generate_content_stream|generateContentStream)"),
    "cache": re.compile(r"(cache_control|cacheControl|prompt_cache_key|prompt_cache_retention|cached_content|cachedContent)"),
    "usage": re.compile(r"(\.usage\b|usage_metadata|usageMetadata)"),
}


def modelo_de_llamada(bloque, texto):
    """Lee model=... en los argumentos de la llamada; si es una variable, busca su valor en el archivo."""
    m = re.search(r"\bmodel\s*[=:]\s*(?:['\"`]([^'\"`]+)['\"`]|([A-Za-z_][\w.]*))", bloque)
    if not m:
        return "(no se ve en la llamada)"
    if m.group(1):
        return m.group(1)
    var = m.group(2).split(".")[-1]
    v = re.search(rf"^\s*{re.escape(var)}\s*(?::\s*\w+\s*)?=\s*['\"`]([^'\"`]+)['\"`]", texto, re.M)
    return f"{v.group(1)} (variable {var})" if v else f"(variable {var}: revisa su valor)"


def buscar(carpeta):
    llamadas, prompts, registros, avisos = [], [], [], []
    for raiz, dirs, archivos in os.walk(carpeta):
        dirs[:] = [d for d in dirs if d not in SALTAR]
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            rel = os.path.relpath(ruta, carpeta)
            ext = os.path.splitext(nombre)[1].lower()
            low = nombre.lower()
            if ext in (".jsonl", ".ndjson", ".csv", ".log") or (ext == ".json" and re.search(r"(uso|usage|token|llm|ia|ai|log)", low)):
                try:
                    tam = os.path.getsize(ruta)
                except OSError:
                    tam = 0
                registros.append((rel, tam))
                continue
            if ext in (".md", ".txt", ".j2", ".jinja", ".tmpl", ".prompt") and "prompt" in rel.lower():
                try:
                    t = open(ruta, encoding="utf-8", errors="replace").read()
                    prompts.append((rel + ":1", len(t), "archivo de prompt"))
                except OSError:
                    pass
                continue
            if ext not in EXT_CODIGO:
                continue
            try:
                texto = open(ruta, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            lineas = texto.splitlines()
            if PAT["sdk"].search(texto) or PAT["llamada"].search(texto):
                registra = "sí" if PAT["usage"].search(texto) else "no"
                for i, l in enumerate(lineas, 1):
                    if not PAT["llamada"].search(l):
                        continue
                    bloque = "\n".join(lineas[i - 1: i + 12])  # la llamada y sus argumentos
                    llamadas.append((f"{rel}:{i}", modelo_de_llamada(bloque, texto),
                                     "sí" if PAT["streaming"].search(bloque) else "no",
                                     "sí" if PAT["cache"].search(bloque) else "no", registra))
            comillas = r'("""|\'\'\')' if ext == ".py" else r'(`)'
            for m in re.finditer(comillas + r"(.*?)\1", texto, re.S):
                cuerpo = m.group(2)
                if len(cuerpo) >= 400:
                    n = texto.count("\n", 0, m.start()) + 1
                    pre = lineas[n - 1].split("=")[0].strip()[:40] if "=" in lineas[n - 1] else ""
                    prompts.append((f"{rel}:{n}", len(cuerpo), pre or "texto largo"))
    print(f"# Dónde usa IA el proyecto: {os.path.abspath(carpeta)}\n")
    print("## Llamadas a la IA\n")
    if llamadas:
        print(tabla(["Archivo:línea", "Modelo", "¿Streaming?", "¿Caché?", "¿El archivo registra usage?"], llamadas))
    else:
        print("No encontré llamadas a SDK de IA (anthropic, openai, google-genai, litellm, langchain, ai-sdk). Revisa a mano si usas HTTP directo.")
    print("\n## Prompts largos (candidatos a parte fija)\n")
    if prompts:
        print(tabla(["Archivo:línea", "Caracteres", "≈ tokens (caracteres ÷ 4)", "Nombre"],
                    [(u, miles(c), miles(c / 4), nom) for u, c, nom in sorted(prompts, key=lambda x: -x[1])]))
        print("\n≈ tokens es aproximado (en español suele ser algo más). Para la cifra exacta usa el campo usage de una llamada real o el conteo de tokens del proveedor.")
    else:
        print("No encontré textos de 400 caracteres o más.")
    print("\n## Posibles registros de uso\n")
    if registros:
        print(tabla(["Archivo", "Tamaño"], [(r, f"{t/1024:,.1f} KB") for r, t in registros]))
    else:
        print("Ninguno. Sin registros: pide volúmenes estimados (referencia/formato_uso.md, «Sin registros»).")
    if llamadas and all(x[4] == "no" for x in llamadas):
        print("\nAviso: ninguna llamada parece leer `usage`; tu app no está registrando tokens. Ver referencia/formato_uso.md, «Empieza a registrar».")
    return 0


# ---------------------------------------------------------------- main


class Args:
    pass


def parsear(argv):
    if len(argv) < 2 or argv[0] not in ("buscar", "medir"):
        return None
    a = Args()
    a.cmd, a.archivo = argv[0], argv[1]
    opciones = {"--precios": "precios", "--salida": "salida", "--fijos": "fijos", "--simples": "simples",
                "--ya-streaming": "ya_streaming", "--ubicaciones": "ubicaciones", "--supuestos": "supuestos",
                "--dias": "dias", "--entrada-incluye-cache": "entrada_incluye_cache", "--hoy": "hoy"}
    for v in opciones.values():
        setattr(a, v, None)
    a.salida, a.entrada_incluye_cache = ".", "auto"
    i = 2
    while i < len(argv):
        if argv[i] not in opciones or i + 1 >= len(argv):
            raise SystemExit(f"Opción no reconocida o sin valor: {argv[i]}\n\n{__doc__}")
        setattr(a, opciones[argv[i]], argv[i + 1])
        i += 2
    if a.dias:
        a.dias = float(a.dias)
    if a.entrada_incluye_cache not in ("auto", "si", "no"):
        raise SystemExit("--entrada-incluye-cache debe ser auto, si o no")
    return a


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    args = parsear(sys.argv[1:])
    if not args:
        print(__doc__)
        sys.exit(2)
    if not os.path.exists(args.archivo):
        print(f"FALLA: no existe {args.archivo}")
        sys.exit(2)
    sys.exit(buscar(args.archivo) if args.cmd == "buscar" else medir(args))
