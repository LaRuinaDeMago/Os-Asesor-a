#!/usr/bin/env python3
"""
fase0_empresas_por_copia.py — Cuantas empresas hay en cada copia. Sin inferir.

EL HALLAZGO QUE LO PERMITE
--------------------------
Los .DAT no se llaman SP_C_04 sino SP_C_04A, SP_C_04B, ... El patron real es
AA_A_##A: dos letras, guion bajo, letra, guion bajo, NUMERO y una LETRA final.

  - El NUMERO es el codigo de empresa dentro de esa copia.
  - La LETRA final es la parte/modulo del backup de esa misma empresa.

Eso explica por que fallaba la restriccion del script anterior: varios ficheros
con el mismo numero y distinta letra son LA MISMA empresa, y se contaban como
empresas distintas.

Y da la medicion directa: dentro de una carpeta de copia, el numero de codigos
DISTINTOS es el numero de empresas de ese backup. Sin huella dactilar, sin
umbrales, sin inferencia de ningun tipo.

Se cuentan por separado los codigos con datos y los que solo tienen ficheros
vacios (1.384 bytes), porque un codigo cuyos ficheros estan todos vacios no es
una empresa con contabilidad.

REGLA DURA: solo recuentos y nombres de carpeta. Ningun dato de cliente.

Uso:
    python fase0_empresas_por_copia.py "RUTA"
"""

import os
import re
import sys
import json
import argparse
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, "fase0_empresas_por_copia.json")

# SP_C_04A -> prefijo SP_C_, codigo 04, parte A
RE_NOMBRE = re.compile(r"^(?P<pre>.*?)(?P<cod>\d+)(?P<parte>[A-Za-z]?)$")
VACIO = 2048


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe.")
        return 1

    # carpeta -> codigo -> {partes, con_datos, bytes}
    por_carpeta = defaultdict(lambda: defaultdict(
        lambda: {"partes": set(), "con_datos": 0, "total": 0}))
    sin_patron = 0

    for dp, _, fns in os.walk(raiz):
        rel = os.path.relpath(dp, raiz)
        carp = rel.split(os.sep)[0] if rel != "." else "(raiz)"
        for f in fns:
            if not f.lower().endswith(".dat"):
                continue
            base = os.path.splitext(f)[0]
            m = RE_NOMBRE.match(base)
            if not m:
                sin_patron += 1
                continue
            cod = f"{m.group('pre')}{m.group('cod')}"
            e = por_carpeta[carp][cod]
            e["partes"].add(m.group("parte").upper())
            e["total"] += 1
            try:
                if os.path.getsize(os.path.join(dp, f)) >= VACIO:
                    e["con_datos"] += 1
            except OSError:
                pass

    filas = []
    for carp, cods in sorted(por_carpeta.items()):
        con_datos = [c for c, e in cods.items() if e["con_datos"] > 0]
        filas.append({
            "carpeta": carp,
            "codigos_distintos": len(cods),
            "EMPRESAS_CON_DATOS": len(con_datos),
            "ficheros": sum(e["total"] for e in cods.values()),
            "partes_por_empresa": round(
                sum(len(e["partes"]) for e in cods.values()) / len(cods), 1) if cods else 0,
        })

    salida = {
        "version": "empresas_por_copia_v1",
        "ficheros_sin_patron_reconocible": sin_patron,
        "carpetas": filas,
        "nota": "Solo recuentos y nombres de carpeta.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("=" * 92)
    print("  EMPRESAS POR COPIA — contando codigos distintos, sin inferir nada")
    print("=" * 92)
    print(f"  {'cods':>6}{'CON DATOS':>11}{'fich':>7}{'partes':>8}  carpeta")
    print("  " + "-" * 88)
    for r in sorted(filas, key=lambda x: -x["EMPRESAS_CON_DATOS"]):
        print(f"  {r['codigos_distintos']:>6}{r['EMPRESAS_CON_DATOS']:>11}"
              f"{r['ficheros']:>7}{r['partes_por_empresa']:>8}  {r['carpeta'][:58]}")
    if sin_patron:
        print(f"\n  Ficheros sin patron reconocible: {sin_patron}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
