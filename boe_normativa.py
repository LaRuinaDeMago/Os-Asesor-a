#!/usr/bin/env python3
"""boe_normativa.py — lee el texto CONSOLIDADO del BOE y avisa si ha cambiado.

QUE HACE, Y LA LINEA QUE NO CRUZA
------------------------------------
Usa la API de datos abiertos del BOE (legislacion consolidada) para traer un
articulo concreto, quedarse con la version EN VIGOR hoy, y calcular una huella
de su texto. Con eso contesta una sola pregunta, y la contesta sola:

    .Ha cambiado el articulo 91 de la LIVA desde el dia que lo leimos?

Eso es automatizable de verdad, y no interpreta nada: compara texto contra
texto. Lo que NO hace, ni hara, es decirte QUE significa el cambio. Eso lo lee
un asesor. La automatizacion detecta; la persona ratifica.

POR QUE ESTO SI Y UN RESUMIDOR NO
------------------------------------
El 15-09-2026, una consulta resumida por un modelo afirmo que la ISP soportada
del 303 va a "las casillas 40-43" -- que en el impreso son otra cosa. Se
descarto porque estaba corroborada contra el documento. La diferencia entre
aquello y esto es exacta: aquello producia una AFIRMACION nueva; esto produce
una COMPARACION entre dos textos oficiales. Una se puede equivocar, la otra no.

LA RED NO SE TOCA EN LA AUDITORIA
-----------------------------------
`audit_project.py` tiene que correr sin red, rapido y determinista. Por eso el
modo que descarga es explicito (`--comprobar`) y se lanza a mano o desde una
tarea programada. Lo que la auditoria mira es la HUELLA ya guardada.

Uso:
    python boe_normativa.py --comprobar        # descarga y compara con lo guardado
    python boe_normativa.py --ver a91          # imprime el texto en vigor de un articulo
"""
import argparse
import datetime
import hashlib
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = ("https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
       "id/{norma}/texto/bloque/{bloque}")

#: Clases de parrafo que el BOE usa para notas editoriales y para el texto
#: DEROGADO que conserva a modo de historia. Incluirlas en la huella haria que
#: cambiara cada vez que el BOE anota algo, y --peor-- meteria en el texto
#: "en vigor" redacciones que ya no lo estan.
CLASES_NO_VIGENTES = ("nota_pie", "nota_pie_2", "cita_con_pleca", "nota")


def descargar(norma, bloque, timeout=60):
    req = urllib.request.Request(API.format(norma=norma, bloque=bloque),
                                 headers={"Accept": "application/xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def version_en_vigor(xml_bytes, hoy=None):
    """Devuelve (titulo, fecha_vigencia, norma_modificadora, texto) de la
    version vigente HOY. El consolidado trae todas las historicas: quedarse
    con la ultima del fichero seria un error el dia que el BOE publique una
    con entrada en vigor futura, que es justo lo que hace con las reformas."""
    hoy = hoy or datetime.date.today().strftime("%Y%m%d")
    bloque = ET.fromstring(xml_bytes).find(".//bloque")
    if bloque is None:
        return None
    candidatas = [v for v in bloque.findall("version")
                  if (v.get("fecha_vigencia") or "99999999") <= hoy]
    if not candidatas:
        return None
    v = max(candidatas, key=lambda x: x.get("fecha_vigencia") or "")
    lineas = [html.unescape(ET.tostring(p, encoding="unicode", method="text")).strip()
              for p in v.iter("p") if p.get("class") not in CLASES_NO_VIGENTES]
    texto = "\n".join(x for x in lineas if x)
    return bloque.get("titulo"), v.get("fecha_vigencia"), v.get("id_norma"), texto


def huella(texto):
    """Hash del texto normalizado. Se colapsan los espacios para que un
    reformateo del BOE no se confunda con una reforma legal."""
    return hashlib.sha256(re.sub(r"\s+", " ", texto).strip().encode("utf-8")).hexdigest()[:16]


def comprobar(registros, hoy=None):
    """registros: iterable de objetos con .norma_boe, .bloque_boe, .vigencia_boe
    y .huella_boe. Devuelve (iguales, cambiados, fallidos)."""
    iguales, cambiados, fallidos = [], [], []
    for reg in registros:
        if not getattr(reg, "bloque_boe", ""):
            continue
        try:
            r = version_en_vigor(descargar(reg.norma_boe, reg.bloque_boe), hoy)
        except Exception as e:
            fallidos.append((reg.clave, type(e).__name__))
            continue
        if r is None:
            fallidos.append((reg.clave, "sin version en vigor"))
            continue
        _, fecha, norma_mod, texto = r
        h = huella(texto)
        if h == reg.huella_boe and fecha == reg.vigencia_boe:
            iguales.append(reg.clave)
        else:
            cambiados.append((reg.clave, reg.vigencia_boe, fecha, norma_mod, h))
    return iguales, cambiados, fallidos


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--comprobar", action="store_true",
                     help="Descarga los articulos registrados y compara con la huella guardada")
    ap.add_argument("--ver", metavar="BLOQUE",
                     help="Imprime el texto en vigor de un bloque (ej. a91)")
    ap.add_argument("--norma", default="BOE-A-1992-28740",
                     help="Identificador BOE de la norma (por defecto, la LIVA)")
    args = ap.parse_args()

    if args.ver:
        r = version_en_vigor(descargar(args.norma, args.ver))
        if r is None:
            print("No se ha podido leer ese bloque.", file=sys.stderr)
            return 1
        titulo, fecha, norma_mod, texto = r
        print(f"=== {titulo} — en vigor desde {fecha} (modificado por {norma_mod}) ===")
        print(f"=== huella: {huella(texto)} ===\n")
        print(texto)
        return 0

    if args.comprobar:
        import fuentes_externas as fx
        import autoridad_guards as ag
        # AMPLIADO 15-09-2026. Antes esto solo miraba `fuentes_externas`, que
        # tenia DOS articulos enganchados. Las 15 citas VERIFICADAS de
        # `autoridad_guards` -- las que respaldan los guards que deciden
        # veredictos -- no las vigilaba nadie: se registraban con su bloque
        # pero sin huella, asi que aunque se hubieran pasado por aqui habrian
        # salido todas como "cambiadas". Una verificacion que nadie vuelve a
        # mirar no caduca con un aviso: caduca en silencio.
        registros = list(fx.FUENTES) + [
            a for a in ag.AUTORIDADES
            if getattr(a, "bloque_boe", "") and getattr(a, "huella_boe", "")]
        iguales, cambiados, fallidos = comprobar(registros)
        print(f"Comprobados contra el BOE: {len(iguales)} sin cambios, "
              f"{len(cambiados)} CAMBIADOS, {len(fallidos)} no comprobados")
        for clave, antes, ahora, norma_mod, h in cambiados:
            print(f"\n  ⚠ {clave}")
            print(f"    vigencia guardada: {antes}   vigencia actual: {ahora}")
            print(f"    modificado por: {norma_mod}")
            print(f"    huella nueva: {h}")
            print("    -> hay que LEER el articulo y decidir. El programa no")
            print("       interpreta el cambio, solo lo detecta.")
        for clave, motivo in fallidos:
            print(f"  · {clave}: no comprobado ({motivo})")
        return 1 if cambiados else 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
