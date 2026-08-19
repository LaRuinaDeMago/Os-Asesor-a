#!/usr/bin/env python3
"""
fase0_metadatos_zip.py — Lo que no se ha mirado en ningun momento.

ContaPlus sabe de que empresa es una copia cuando la restaura. Tiene que
leerlo de algun sitio. Dos candidatos que todos los scripts anteriores han
ignorado:

  1. El COMENTARIO del archivo ZIP (y el de cada entrada).
  2. La RUTA INTERNA COMPLETA de cada fichero. Hasta ahora se ha usado
     os.path.basename() en todas partes, tirando el directorio. Si dentro del
     ZIP los ficheros cuelgan de una carpeta con el codigo o el nombre de la
     empresa, ahi esta la identidad y se ha estado descartando.

Tambien se mira el nombre del propio fichero .DAT: si el patron completo
(no solo el numero) codifica algo mas.

REGLA DURA: se reportan RECUENTOS y FORMAS, no contenidos. Las rutas internas
se muestran con la parte variable enmascarada (los digitos como #, las letras
como A) para ver el PATRON sin ver el valor. Si algo tiene forma de NIF, no se
imprime.

Uso:
    python fase0_metadatos_zip.py "RUTA"
"""

import os
import re
import sys
import json
import zipfile
import argparse
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, "fase0_metadatos_zip.json")
RE_NIF = re.compile(r"\b(\d{8}[A-Za-z]|[A-HJ-NP-SUVWXYZ]\d{7}[0-9A-Ja-j])\b")


def patron(s):
    """'SP_C_04' -> 'AA_A_##'. Ensena la forma, nunca el valor."""
    out = []
    for c in s:
        if c.isdigit():
            out.append("#")
        elif c.isalpha():
            out.append("A")
        else:
            out.append(c)
    return "".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--muestra", type=int, default=400)
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    paso = max(1, len(dats) // args.muestra)
    muestra = dats[::paso][:args.muestra]
    print(f"{len(dats)} contenedores. Muestreando {len(muestra)}.")

    com_zip = Counter()
    com_zip_len = []
    com_entrada = 0
    con_directorio = 0
    sin_directorio = 0
    patrones_dir = Counter()
    dirs_distintos = set()
    patrones_fichero = Counter()
    nombres_dat_distintos = set()
    fechas_zip = Counter()
    errores = Counter()

    for ruta in muestra:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            base = os.path.splitext(os.path.basename(ruta))[0]
            patrones_fichero[patron(base)] += 1
            nombres_dat_distintos.add(base)
            with zipfile.ZipFile(ruta) as z:
                c = z.comment
                com_zip_len.append(len(c))
                if c:
                    com_zip[patron(c.decode("cp1252", "replace"))[:40]] += 1
                for i in z.infolist():
                    if i.comment:
                        com_entrada += 1
                    d = os.path.dirname(i.filename)
                    if d:
                        con_directorio += 1
                        patrones_dir[patron(d)] += 1
                        dirs_distintos.add(d)
                    else:
                        sin_directorio += 1
                    fechas_zip[i.date_time[0]] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    salida = {
        "version": "metadatos_zip_v1",
        "muestreados": len(muestra),
        "comentario_del_zip": {
            "con_comentario": sum(1 for x in com_zip_len if x > 0),
            "long_max": max(com_zip_len) if com_zip_len else 0,
            "patrones": dict(com_zip.most_common(10)),
        },
        "entradas_con_comentario": com_entrada,
        "rutas_internas": {
            "entradas_con_directorio": con_directorio,
            "entradas_sin_directorio": sin_directorio,
            "directorios_distintos": len(dirs_distintos),
            "patrones_de_directorio": dict(patrones_dir.most_common(10)),
        },
        "nombre_del_dat": {
            "distintos": len(nombres_dat_distintos),
            "patrones": dict(patrones_fichero.most_common(10)),
        },
        "anio_de_la_marca_de_tiempo_del_zip": dict(sorted(fechas_zip.items())),
        "errores": dict(errores),
        "nota": "Solo patrones enmascarados y recuentos.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 68)
    print("  1) COMENTARIO DEL ZIP")
    print("=" * 68)
    cz = salida["comentario_del_zip"]
    print(f"   contenedores con comentario : {cz['con_comentario']} de {len(muestra)}")
    print(f"   longitud maxima             : {cz['long_max']}")
    for p, n in cz["patrones"].items():
        print(f"      {n:>5}x  {p}")
    print(f"   entradas con comentario     : {com_entrada}")
    print("")
    print("=" * 68)
    print("  2) RUTAS INTERNAS  <== lo que se estaba tirando")
    print("=" * 68)
    ri = salida["rutas_internas"]
    print(f"   entradas CON directorio : {ri['entradas_con_directorio']}")
    print(f"   entradas SIN directorio : {ri['entradas_sin_directorio']}")
    print(f"   directorios distintos   : {ri['directorios_distintos']}")
    for p, n in ri["patrones_de_directorio"].items():
        print(f"      {n:>6}x  {p}")
    print("")
    print("=" * 68)
    print("  3) NOMBRE DEL PROPIO .DAT")
    print("=" * 68)
    nd = salida["nombre_del_dat"]
    print(f"   nombres distintos : {nd['distintos']}")
    for p, n in nd["patrones"].items():
        print(f"      {n:>5}x  {p}")
    print("")
    print("=" * 68)
    print("  4) ANIO DE LA MARCA DE TIEMPO DE LAS ENTRADAS")
    print("=" * 68)
    for a, n in salida["anio_de_la_marca_de_tiempo_del_zip"].items():
        print(f"      {a}: {n:>7}")
    if errores:
        print(f"\n   Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
