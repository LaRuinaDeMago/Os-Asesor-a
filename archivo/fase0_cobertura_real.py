#!/usr/bin/env python3
"""
fase0_cobertura_real.py — .Esta el 100% del historico? Medido, no opinado.

Usa el hallazgo verificado (dentro de una carpeta, el numero del nombre es el
codigo de empresa) para responder por ejercicio, SIN depender del enlace entre
carpetas, que sigue pendiente:

  - empresas distintas por ejercicio en la carpeta MAS COMPLETA que lo
    contenga  -> cota INFERIOR fiable de clientes ese ano
  - total de copias empresa-ejercicio por ano
  - en cuantas carpetas distintas aparece cada ejercicio (redundancia)

Y hace inventario de TODO lo que hay en el arbol que no sea .dat ni .pdf, para
que no quede ni un fichero sin clasificar.

Solo recuentos. Ningun dato de cliente.

Uso:
    python fase0_cobertura_real.py "RUTA"
"""

import os
import re
import sys
import json
import zipfile
import struct
import argparse
from collections import defaultdict, Counter

BASE = os.path.dirname(os.path.abspath(__file__))
SALIDA = os.path.join(BASE, "fase0_cobertura_real.json")
RE_NOMBRE = re.compile(r"^(?P<pre>.*?)(?P<cod>\d+)(?P<parte>[A-Za-z]?)$")
VACIO = 2048
TOPE_CABECERA = 65535


def ejercicio_de(ruta):
    try:
        with zipfile.ZipFile(ruta) as z:
            interno = None
            for i in z.infolist():
                if not i.is_dir() and os.path.basename(i.filename).lower() == "diario.dbf":
                    interno = i.filename
                    break
            if interno is None:
                return None
            with z.open(interno) as f:
                cab = f.read(32)
                len_cab = struct.unpack("<H", cab[8:10])[0]
                len_reg = struct.unpack("<H", cab[10:12])[0]
                if len_cab <= 32 or len_cab > TOPE_CABECERA:
                    return None
                resto = f.read(len_cab - 32)
                off, pos, cF = 0, 1, None
                while off + 32 <= len(resto):
                    if resto[off] == 0x0D:
                        break
                    b = resto[off:off + 32]
                    if b[0:11].split(b"\x00")[0] == b"FECHA":
                        cF = (pos, b[16])
                    pos += b[16]
                    off += 32
                if not cF:
                    return None
                anios = Counter()
                leidos = 0
                while leidos < 4000:
                    rec = f.read(len_reg)
                    if len(rec) < len_reg or rec[:1] == b"\x1a":
                        break
                    leidos += 1
                    v = rec[cF[0]:cF[0] + cF[1]].strip(b" \x00")
                    if len(v) == 8 and v.isdigit():
                        anios[int(v[:4])] += 1
                return anios.most_common(1)[0][0] if anios else None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    # carpeta -> ejercicio -> set(codigos)
    cob = defaultdict(lambda: defaultdict(set))
    otros = Counter()
    otros_bytes = Counter()
    errores = Counter()

    print("Recorriendo el arbol...")
    for dp, _, fns in os.walk(raiz):
        rel = os.path.relpath(dp, raiz)
        carp = rel.split(os.sep)[0] if rel != "." else "(raiz)"
        for f in fns:
            ext = os.path.splitext(f)[1].lower()
            ruta = os.path.join(dp, f)
            if ext not in (".dat", ".pdf"):
                otros[ext or "(sin ext)"] += 1
                try:
                    otros_bytes[ext or "(sin ext)"] += os.path.getsize(ruta)
                except OSError:
                    pass
                continue
            if ext != ".dat":
                continue
            try:
                if os.path.getsize(ruta) < VACIO:
                    continue
            except OSError:
                continue
            m = RE_NOMBRE.match(os.path.splitext(f)[0])
            if not m:
                errores["nombre_sin_patron"] += 1
                continue
            cod = f"{m.group('pre')}{m.group('cod')}"
            e = ejercicio_de(ruta)
            if e:
                cob[carp][e].add(cod)
            else:
                errores["sin_ejercicio"] += 1

    # --- por ejercicio ---
    ejercicios = sorted({e for c in cob.values() for e in c})
    filas = []
    for e in ejercicios:
        por_carp = {c: len(v[e]) for c, v in cob.items() if e in v}
        filas.append({
            "ejercicio": e,
            "COTA_INFERIOR_CLIENTES": max(por_carp.values()) if por_carp else 0,
            "copias_totales": sum(por_carp.values()),
            "carpetas_que_lo_contienen": len(por_carp),
        })

    salida = {
        "version": "cobertura_real_v1",
        "por_ejercicio": filas,
        "otros_ficheros": {k: {"n": v, "MB": round(otros_bytes[k] / (1024 * 1024), 2)}
                           for k, v in otros.most_common()},
        "errores": dict(errores),
        "nota": "Solo recuentos. La cota inferior es el maximo de empresas de "
                "una sola carpeta para ese ejercicio.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 70)
    print("  COBERTURA REAL POR EJERCICIO")
    print("  (cota inferior = empresas de la carpeta mas completa de ese ano)")
    print("=" * 70)
    print(f"  {'ejercicio':>10}{'CLIENTES (min)':>16}{'copias':>9}{'carpetas':>10}")
    print("  " + "-" * 45)
    for r in filas:
        print(f"  {r['ejercicio']:>10}{r['COTA_INFERIOR_CLIENTES']:>16}"
              f"{r['copias_totales']:>9}{r['carpetas_que_lo_contienen']:>10}")
    print("")
    print("=" * 70)
    print("  FICHEROS QUE NO SON .dat NI .pdf (sin clasificar hasta ahora)")
    print("=" * 70)
    for k, v in salida["otros_ficheros"].items():
        print(f"   {k:<14}{v['n']:>6}{v['MB']:>10.2f} MB")
    if errores:
        print(f"\n  Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
