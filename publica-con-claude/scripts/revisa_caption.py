#!/usr/bin/env python3
"""revisa_caption.py · revisa un caption de Instagram escrito en español antes de publicarlo.

Qué revisa (nunca reescribe; solo marca y explica):
  - la primera línea: lo que Instagram enseña antes de «… más» (~125 caracteres);
  - que la palabra clave (--clave) aparezca en esa primera línea, para que te encuentre el buscador;
  - spanglish: palabras en inglés que se colaron sin querer («important», «the», «workflow»…);
  - muletillas de texto hecho con IA en español («cabe destacar», «en el panorama actual»…);
  - rayas largas (—), caracteres invisibles y espacios raros que deja el copiar y pegar de un chat;
  - cuántas cosas le pides a la gente (más de 2 pedidos dispersa la acción);
  - hashtags: cuántos son y si están al final.

Uso:
  python revisa_caption.py caption.txt --clave "base de datos"
  python revisa_caption.py caption.txt --permitidas Remotion,GitHub
  python revisa_caption.py caption.txt --json

Solo lee el archivo. No usa internet.
"""
import argparse
import json
import re
import sys
import unicodedata

VISIBLE = 125

# Palabras en inglés que no deberían aparecer en un texto en español, salvo nombres propios o términos que tú permitas.
INGLES = set("""the and of to is are was were be been with for your you our this that these those it its from by on at as
an or not but if then than so very just also more most only into about over after before because while which what
when where who how why can could should would will important however moreover furthermore therefore
workflow insights leverage seamless seamlessly unlock boost game changer gamechanger delve journey powerful amazing
awesome check out learn free tips tricks today now new best way ways step steps guide""".split())
# Términos en inglés que en el español de redes ya se usan tal cual: no cuentan como spanglish.
PERMITIDAS = set("""reel reels post posts feed hashtag hashtags prompt prompts skill skills app apps link online software
hardware email emails podcast influencer influencers marketing startup startups chatbot chatbots bot bots youtube instagram
facebook tiktok claude chatgpt gemini github google meta whatsapp ok wifi""".split())

# Graves: casi nunca las escribe una persona en un caption.
MULETILLAS = [
    "cabe destacar", "es importante destacar", "es importante mencionar", "vale la pena mencionar",
    "en el panorama actual", "en la era digital", "en el mundo actual", "en el vertiginoso",
    "sin lugar a dudas", "sin duda alguna", "en resumen", "en conclusión", "en definitiva",
    "potenciar", "potencia tu", "desbloquea", "desbloquear", "sumérgete", "adéntrate",
    "lleva tu", "al siguiente nivel", "revolucionar", "revoluciona", "transforma tu", "un mundo de posibilidades",
    "aprovecha al máximo", "sacarle el máximo provecho", "descubre cómo", "¿alguna vez te has preguntado",
    "fascinante", "apasionante", "sinergia", "imagina un mundo", "no es solo una", "no es solo un",
]
# Leves: son español normal, pero si se juntan suenan a IA. Solo dan AVISO.
MULETILLAS_LEVES = ["crucial", "fundamental", "robusto", "ecosistema", "no solo", "más que un"]
# Solo cuentan los pedidos dirigidos a quien lee (imperativo + algo que hacer), no los verbos que describen:
# «Netflix guarda el historial» o «mi cliente comenta que…» no son pedidos.
PEDIDOS = re.compile(
    r"\b(?:[Cc]omenta\s+[«\"']?[A-ZÁÉÍÓÚÑ]{2,}"
    r"|(?i:comenta\s+(?:aquí|abajo|cuál|qué|tu|la palabra))"
    r"|(?i:guárd(?:alo|ala|atelo|atela)|guarda\s+(?:este|esta)\s+(?:post|reel|video|carrusel|publicación))"
    r"|(?i:compárt(?:elo|ela)|comparte\s+(?:este|esta)\s+\w+|mánd(?:aselo|asela)|envíaselo)"
    r"|(?i:sígueme|sígue(?:nos)?|sigue\s+a\s+@\w+|suscríbete|dale\s+(?:like|me\s+gusta))"
    r"|(?i:link\s+en\s+(?:la|mi)\s+bio|déjal[ao]\s+en\s+los\s+comentarios|dímelo|dime\s+(?:cuál|qué|el|la)|te\s+leo|escríbeme))"
)
INVISIBLES = re.compile("[​‌‍⁠﻿­  ]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
PALABRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ']+")


def revisa(texto, clave=None, permitidas=()):
    perm = PERMITIDAS | {p.lower() for p in permitidas}
    lineas = [l for l in texto.splitlines()]
    primera = next((l.strip() for l in lineas if l.strip()), "")
    visible = primera[:VISIBLE]
    cuerpo = "\n".join(l for l in lineas if not l.strip().startswith("#"))
    hashtags = re.findall(r"(?<!\w)#[\wÁÉÍÓÚÜÑáéíóúüñ]+", texto)
    # Al final = después de la última línea que trae texto normal (no solo hashtags).
    texto_normal = [i for i, l in enumerate(lineas) if l.strip() and not re.fullmatch(r"(\s*#[\wÁÉÍÓÚÜÑáéíóúüñ]+)+\s*", l)]
    cola = "\n".join(lineas[(texto_normal[-1] + 1) if texto_normal else 0:])
    hashtags_al_final = all(h in cola for h in hashtags)
    ingles = []
    limpio = re.sub(r"https?://\S+|@\w+|#\w+", " ", cuerpo)
    for m in PALABRA.finditer(limpio):
        w = m.group(0)
        lw = w.lower().strip("'")
        if lw not in INGLES or lw in perm:
            continue
        # Con mayúscula a media frase es un nombre propio («The Verge», «Free Fire»): no es spanglish.
        antes = limpio[:m.start()].rstrip()
        inicio_frase = not antes or antes[-1] in ".!?¡¿:\n«\"("
        if w[0].isupper() and not inicio_frase:
            continue
        ingles.append(w)
    low = cuerpo.lower()
    muletillas = [m for m in MULETILLAS if m in low]
    leves = [m for m in MULETILLAS_LEVES if re.search(r"\b" + re.escape(m) + r"\b", low)]
    pedidos = [m.group(0) for m in PEDIDOS.finditer(cuerpo)]
    checks = []

    def add(id_, ok, detalle, grave=True):
        checks.append({"id": id_, "pasa": bool(ok), "grave": grave, "detalle": detalle})

    add("primera_linea", len(primera) <= VISIBLE,
        f"{len(primera)} caracteres; Instagram enseña ~{VISIBLE} antes de «… más». Lo que se ve: «{visible}»")
    if clave:
        add("clave_arriba", clave.lower() in primera.lower(),
            f"la palabra clave «{clave}» {'sí' if clave.lower() in primera.lower() else 'no'} está en la primera línea (el buscador de Instagram y Google la leen ahí)")
    add("sin_spanglish", not ingles,
        f"palabras en inglés: {sorted(set(ingles))}" if ingles else "sin palabras en inglés coladas")
    add("sin_muletillas_ia", not muletillas,
        f"muletillas de texto de IA: {muletillas}" if muletillas else "sin muletillas típicas de IA")
    add("pocas_leves", len(leves) <= 1, f"palabras que juntas suenan a IA: {leves}" if leves else "sin palabras de relleno", grave=False)
    rayas = texto.count("—")
    add("sin_rayas", rayas == 0, f"rayas largas (—): {rayas}. En redes casi nadie las teclea; cámbialas por coma o punto", grave=False)
    inv = len(INVISIBLES.findall(texto))
    add("sin_invisibles", inv == 0, f"caracteres invisibles o espacios raros: {inv} (se cuelan al copiar de un chat)")
    add("pocos_pedidos", len(pedidos) <= 2,
        f"pedidos: {len(pedidos)} ({', '.join(p.lower() for p in pedidos) or 'ninguno'}); máximo 2: una acción principal y, si acaso, una pregunta")
    add("tiene_pedido", len(pedidos) >= 1, "le pides algo a quien llegó al final" if pedidos else "no hay ninguna acción: ¿qué quieres que haga?", grave=False)
    add("hashtags", len(hashtags) <= 5 and hashtags_al_final,
        f"{len(hashtags)} hashtags{'' if hashtags_al_final else ', no todos al final'}; mejor 3 a 5, en la última línea", grave=False)
    emojis = len(EMOJI.findall(texto))
    add("emojis", emojis <= 3, f"emojis: {emojis}", grave=False)
    return {"caracteres": len(texto), "checks": checks}


def main():
    ap = argparse.ArgumentParser(description="Revisa un caption de Instagram en español.")
    ap.add_argument("archivo", help="archivo .txt con el caption, o - para leer de la entrada")
    ap.add_argument("--clave", help="palabra clave principal de la pieza")
    ap.add_argument("--permitidas", default="", help="términos en inglés permitidos, separados por comas")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    texto = sys.stdin.read() if a.archivo == "-" else open(a.archivo, encoding="utf-8").read()
    texto = unicodedata.normalize("NFC", texto)
    r = revisa(texto, a.clave, [p.strip() for p in a.permitidas.split(",") if p.strip()])
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    fallas = [c for c in r["checks"] if not c["pasa"] and c["grave"]]
    print(f"CAPTION · {r['caracteres']} caracteres · {'FALLA' if fallas else 'PASA'}")
    for c in r["checks"]:
        estado = "PASA " if c["pasa"] else ("FALLA" if c["grave"] else "AVISO")
        print(f"  {estado} {c['id']:18} {c['detalle']}")


if __name__ == "__main__":
    main()
