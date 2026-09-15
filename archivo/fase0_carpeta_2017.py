#!/usr/bin/env python3
"""
fase0_carpeta_2017.py — .Que son los 124 .DAT de la carpeta del Registro 2017?

El inventario no detecto ni un ejercicio 2017, pero la carpeta
"CONTABILIDADES 2017 ENVIADAS REGISTRO MERCANTIL" contiene 124 ficheros .DAT.
O estan vacios, o llevan fechas que no se leyeron. Este script lo resuelve.

Solo recuentos. Ningun nombre, ninguna ruta, ningun valor.

Uso:
    python fase0_carpeta_2017.py "RUTA"
"""

import os
import sys
import zipfile
import struct
import argparse
from collections import Counter


def campos_de(resto):
    campos, off, pos = [], 0, 1
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:
            break
        b = resto[off:off + 32]
        nombre = b[0:11].split(b"\x00")[0].decode("ascii", "replace")
        campos.append({"nombre": nombre, "ini": pos, "long": b[16]})
        pos += b[16]
        off += 32
    return campos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    objetivo = None
    for d in os.listdir(raiz):
        p = os.path.join(raiz, d)
        if os.path.isdir(p) and "2017" in d and "REGISTRO" in d.upper():
            objetivo = p
            break
    if not objetivo:
        print("No encuentro la carpeta del Registro de 2017.")
        return 1

    dats = []
    for dp, _, fns in os.walk(objetivo):
        for f in fns:
            if f.lower().endswith(".dat"):
                dats.append(os.path.join(dp, f))

    print(f".DAT en la carpeta del Registro 2017: {len(dats)}")

    vacios = 0
    con_diario = 0
    sin_diario = 0
    anios = Counter()
    lineas = 0
    tablas = Counter()
    errores = Counter()

    for r in dats:
        try:
            if os.path.getsize(r) < 2048:
                vacios += 1
                continue
            if not zipfile.is_zipfile(r):
                errores["no_es_zip"] += 1
                continue
            with zipfile.ZipFile(r) as z:
                nm = {os.path.basename(i.filename).lower(): i
                      for i in z.infolist() if not i.is_dir()}
                for k in nm:
                    tablas[k] += 1
                if "diario.dbf" not in nm:
                    sin_diario += 1
                    continue
                con_diario += 1
                with z.open(nm["diario.dbf"].filename) as f:
                    cab = f.read(32)
                    len_cab = struct.unpack("<H", cab[8:10])[0]
                    len_reg = struct.unpack("<H", cab[10:12])[0]
                    campos = campos_de(f.read(len_cab - 32))
                    cF = next((c for c in campos if c["nombre"] == "FECHA"), None)
                    while True:
                        rec = f.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        lineas += 1
                        if cF:
                            v = rec[cF["ini"]:cF["ini"] + cF["long"]].strip(b" \x00")
                            if len(v) == 8 and v.isdigit():
                                anios[v[:4].decode()] += 1
                        del rec
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print(f"  vacios (< 2 KB)        : {vacios}")
    print(f"  con Diario.dbf         : {con_diario}")
    print(f"  sin Diario.dbf         : {sin_diario}")
    print(f"  lineas de asiento      : {lineas:,}")
    print("")
    print("  EJERCICIOS ENCONTRADOS:")
    for a, n in sorted(anios.items()):
        print(f"     {a}: {n:>8,} lineas")
    print("")
    print("  Tablas mas frecuentes dentro:")
    for t, n in tablas.most_common(8):
        print(f"     {t:<20}{n:>5}")
    if errores:
        print(f"\n  Errores: {dict(errores)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
