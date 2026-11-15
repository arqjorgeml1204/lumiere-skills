#!/usr/bin/env python3
"""revisa_whatsapp.py · revisa una plantilla de WhatsApp (mensaje que se manda fuera de la ventana de 24 h).

Dice:
  - si suena a UTILIDAD (retoma algo que el cliente pidió: su cita, su pedido, su cotización)
    o a MARKETING (ofrece algo, promociona, invita a comprar);
  - si una plantilla registrada como utilidad corre riesgo de que Meta la recategorice como marketing
    (y te la cobre como tal);
  - si trae una forma visible de dejar de recibir mensajes (botón «No, gracias» o «Responde BAJA…»).
    Sin baja visible, la gente bloquea el número y baja su calificación de calidad.

Es una revisión de palabras, no la decisión de Meta: la clasificación final la hace Meta al aprobar o revisar.

Uso:
  python revisa_whatsapp.py plantilla.txt [--categoria utilidad|marketing] [--botones "Sí, agendar|No, gracias"]
"""
import argparse
import re
import sys

PROMO = [
    r"\boferta", r"\bdescuento", r"\bpromoci[oó]n", r"\bpromo\b", r"\bgratis\b", r"\baprovecha", r"\bsolo hoy",
    r"\b[uú]ltim[oa]s? (d[ií]as|lugares|piezas)", r"\bhay (agenda|lugares|espacio) disponible", r"\bdato [uú]til",
    r"\bte (recomendamos|sugerimos)", r"\bnuev[oa]s? (producto|servicio|temporada)", r"\btemporada\b", r"\b\d+ ?%",
    r"\bcompra", r"\breserva ya", r"\bno te lo pierdas", r"\binvit(a|amos)",
]
UTIL = [
    r"\btu (solicitud|pedido|cita|cotizaci[oó]n|reserva|visita|diagn[oó]stico|orden|factura)",
    r"\bretomo", r"\bseguimiento de tu", r"\bconfirm(a|amos|o)", r"\brecordatorio", r"\bqued[oó] agendad",
]
BAJA = re.compile(r"(?i)(\bbaja\b|no,? gracias|dejar de recibir|no (te|le) escribo m[aá]s|ya no (quiero|deseo)|\bstop\b|darte de baja)")


def main():
    ap = argparse.ArgumentParser(description="Revisa una plantilla de WhatsApp.")
    ap.add_argument("archivo")
    ap.add_argument("--categoria", choices=["utilidad", "marketing"], help="categoría con la que la registraste en Meta")
    ap.add_argument("--botones", default="", help="textos de los botones, separados por |")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    import signal
    if hasattr(signal, "SIGPIPE"):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    t = open(a.archivo, encoding="utf-8").read()
    todo = t + "\n" + a.botones.replace("|", "\n")
    promo = [p for p in PROMO if re.search(p, t, re.I)]
    util = [p for p in UTIL if re.search(p, t, re.I)]
    parece = "MARKETING" if promo else ("UTILIDAD" if util else "DUDOSA")
    print(f"PLANTILLA · parece: {parece}")
    if parece == "DUDOSA":
        print("  (DUDOSA: no ofrece nada, pero tampoco retoma algo que el cliente pidió. Si es un aviso de algo suyo, di de qué: «tu cita», «tu pedido».)")
    print("  señales de marketing:", [re.search(p, t, re.I).group(0) for p in promo] or "ninguna")
    print("  señales de utilidad: ", [re.search(p, t, re.I).group(0) for p in util] or "ninguna")
    falla = False
    if a.categoria == "utilidad" and promo:
        falla = True
        print("  FALLA recategorización: la registraste como utilidad pero ofrece algo; Meta puede pasarla a marketing y cobrarla como tal. "
              "Quita la oferta o regístrala como marketing.")
    baja = bool(BAJA.search(todo))
    if parece != "UTILIDAD" or a.categoria == "marketing":
        if baja:
            print("  PASA  baja visible: la persona sabe cómo dejar de recibir mensajes")
        else:
            falla = True
            pospone = re.search(r"(?i)\b(ahora no|m[aá]s (tarde|adelante)|luego)\b", todo)
            extra = f" «{pospone.group(0)}» pospone, no da de baja: la persona no sabe cómo dejar de recibir mensajes." if pospone else ""
            print("  FALLA baja visible: agrega un botón «No, gracias» o la línea «Responde BAJA y no te escribo más»." + extra +
                  " Sin baja, la gente bloquea y baja la calificación de tu número.")
    else:
        print(f"  {'PASA ' if baja else 'AVISO'} baja visible: {'sí' if baja else 'no (en utilidad no es obligatoria, pero ayuda)'}")
    print("VEREDICTO:", "FALLA" if falla else "PASA")


if __name__ == "__main__":
    main()
