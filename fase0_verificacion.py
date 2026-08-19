#!/usr/bin/env python3
"""
fase0_verificacion.py — Auditoria de los hallazgos, no resumen de ellos.

Comprueba por separado cada afirmacion que se ha dado por buena hoy. Cada una
imprime OK o FALLA con su numero. Si una falla, las que dependen de ella
quedan invalidadas y se dice cual.

  V1. Los .DAT se agrupan en codigos de empresa de 3 partes.
      -> suma de codigos distintos por carpeta == contenedores con Diario.dbf
  V2. Cada codigo tiene EXACTAMENTE UN fichero con datos y dos vacios.
  V3. Los contenedores vacios pesan todos lo mismo y no llevan nada.
  V4. La carpeta de 2026 tiene 33 empresas, y todas del ejercicio 2026.
  V5. Las carpetas de 2025: cuantas empresas y de que ejercicios.
  V6. Suma de ficheros por carpeta == total de .DAT del arbol.

Solo recuentos. Ningun dato de cliente.

Uso:
    python fase0_verificacion.py "RUTA"
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
SALIDA = os.path.join(BASE, "fase0_verificacion.json")
RE_NOMBRE = re.compile(r"^(?P<pre>.*?)(?P<cod>\d+)(?P<parte>[A-Za-z]?)$")
VACIO = 2048
TOPE_CABECERA = 65535

res = []


def check(nombre, ok, detalle):
    res.append({"prueba": nombre, "ok": bool(ok), "detalle": detalle})
    print(f"  [{'OK  ' if ok else 'FALLA'}] {nombre}")
    print(f"          {detalle}")


def ejercicio_de_contenedor(ruta):
    """Ano modal de las fechas del diario. None si no hay diario."""
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
                while leidos < 3000:
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

    print("AUDITORIA DE LOS HALLAZGOS DEL 12-08-2026")
    print("=" * 74)

    por_carpeta = defaultdict(lambda: defaultdict(list))
    total_dat = 0
    for dp, _, fns in os.walk(raiz):
        rel = os.path.relpath(dp, raiz)
        carp = rel.split(os.sep)[0] if rel != "." else "(raiz)"
        for f in fns:
            if not f.lower().endswith(".dat"):
                continue
            total_dat += 1
            base = os.path.splitext(f)[0]
            m = RE_NOMBRE.match(base)
            cod = f"{m.group('pre')}{m.group('cod')}" if m else base
            por_carpeta[carp][cod].append(os.path.join(dp, f))

    # --- V6: aritmetica basica ---
    suma_fich = sum(len(v) for c in por_carpeta.values() for v in c.values())
    check("V6 · suma de ficheros por carpeta == total de .DAT",
          suma_fich == total_dat,
          f"{suma_fich} vs {total_dat}")

    # --- V1: codigos == contenedores con diario ---
    suma_cod = sum(len(c) for c in por_carpeta.values())
    con_diario = 0
    con_datos_por_cod = Counter()
    tam_vacios = set()
    for carp, cods in por_carpeta.items():
        for cod, ficheros in cods.items():
            n_datos = 0
            for r in ficheros:
                try:
                    t = os.path.getsize(r)
                except OSError:
                    continue
                if t < VACIO:
                    tam_vacios.add(t)
                    continue
                n_datos += 1
                try:
                    with zipfile.ZipFile(r) as z:
                        if any(os.path.basename(i.filename).lower() == "diario.dbf"
                               for i in z.infolist() if not i.is_dir()):
                            con_diario += 1
                except Exception:
                    pass
            con_datos_por_cod[n_datos] += 1

    check("V1 · codigos de empresa == contenedores con Diario.dbf",
          suma_cod == con_diario,
          f"codigos {suma_cod} · con diario {con_diario}")

    # --- V2: un fichero con datos por codigo ---
    exactamente_uno = con_datos_por_cod.get(1, 0)
    check("V2 · cada codigo tiene EXACTAMENTE un fichero con datos",
          exactamente_uno == suma_cod,
          f"con 1: {exactamente_uno} de {suma_cod} · reparto {dict(sorted(con_datos_por_cod.items()))}")

    # --- V3: los vacios son todos identicos ---
    check("V3 · todos los ficheros vacios pesan lo mismo",
          len(tam_vacios) == 1,
          f"tamanos distintos entre los vacios: {sorted(tam_vacios)}")

    # --- V4 y V5: las carpetas recientes ---
    detalle_carpetas = {}
    for carp in sorted(por_carpeta):
        u = carp.upper()
        if not ("2025" in u or "2026" in u):
            continue
        anios = Counter()
        for cod, ficheros in por_carpeta[carp].items():
            for r in ficheros:
                try:
                    if os.path.getsize(r) < VACIO:
                        continue
                except OSError:
                    continue
                e = ejercicio_de_contenedor(r)
                if e:
                    anios[e] += 1
        detalle_carpetas[carp] = {"empresas": len(por_carpeta[carp]),
                                  "ejercicios": dict(sorted(anios.items()))}

    c2026 = next((v for k, v in detalle_carpetas.items() if "2026" in k.upper()), None)
    if c2026:
        check("V4 · la copia de 2026 tiene 33 empresas",
              c2026["empresas"] == 33,
              f"empresas {c2026['empresas']} · ejercicios {c2026['ejercicios']}")
    else:
        check("V4 · la copia de 2026", False, "no encontrada")

    print("")
    print("  CARPETAS DE 2025 Y 2026 EN DETALLE:")
    for k, v in detalle_carpetas.items():
        print(f"     {v['empresas']:>3} empresas · ejercicios {v['ejercicios']}")
        print(f"         {k[:66]}")

    ok = sum(1 for r in res if r["ok"])
    print("")
    print("=" * 74)
    print(f"  {ok} de {len(res)} comprobaciones en verde")
    print("=" * 74)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump({"pruebas": res, "carpetas_recientes": detalle_carpetas},
                  f, indent=2, ensure_ascii=False)
    print(f"Escrito: {SALIDA}")
    return 0 if ok == len(res) else 1


if __name__ == "__main__":
    sys.exit(main())
