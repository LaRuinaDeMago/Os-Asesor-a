#!/usr/bin/env python3
"""
fase0_asientos.py — Iteracion 6. La pregunta de la Fase 0 punto 5, BIEN hecha.

La iteracion anterior midio por LINEA y dio 0%. Era la pregunta equivocada:
en ContaPlus una factura se reparte en varias lineas de un mismo asiento.
  600xxxx  gasto       DEBE = base
  472xxxx  IVA sop.    DEBE = cuota   <- aqui viven IVA y TERNIF
  400xxxx  proveedor   HABER = total

Este script agrupa por ASIENTO y mide:
  1. .Que porcentaje de asientos tiene el patron completo compra/venta?
  2. De esos, .cuantos traen NIF de contraparte y tipo de IVA?
  3. .Se puede DERIVAR la base?  (base + cuota == total, y base*tipo == cuota)
     Eso resolveria que BASEIMPO solo venga RELLENO en el 0,78% de las lineas
     (o sea: viene inutilizable el 99,2% de las veces — la frase anterior
     decia "vacio al 0,78%" y se leia justo al reves).

     CONFIRMADO EL 26-08-2026 con diag_baseimpo.py, sobre 44.522 apuntes de
     IVA del corpus real: 44.243 (99,4%) traen un CERO LITERAL, no un campo
     vacio. Legible, y aun asi no es una base. Las 279 que si traen cifra no
     tienen tipo de IVA con el que contrastarlas. Medicion independiente que
     coincide con el 0,78% de entonces.

     POR QUE IMPORTA MAS DE LO QUE PARECE: reconstruir_303.py se escribio el
     21-08 SIN esta alternativa (usaba BASEIMPO en bruto), asi que llevaba
     desde entonces sumando ceros y llamandolos base imponible. Se encontro
     el 26-08 y sigue pendiente de arreglar. retro_semaforo.py si la tiene,
     en reconstruir_compra(), y por eso sus cifras son validas.
  4. .Cuantos asientos UNICOS hay, descontando duplicacion entre copias?

REGLA DURA: lee filas, solo incrementa contadores. Ningun valor se guarda ni
se emite. Los hashes de identidad viven solo en memoria; se publica el
recuento, nunca el hash.

Uso:
    python fase0_asientos.py "RUTA"
"""

import os
import sys
import json
import zipfile
import struct
import hashlib
import argparse
from collections import Counter, defaultdict

SALIDA = "fase0_asientos.json"
TOPE_CABECERA = 65535
TOL = 0.02  # tolerancia en euros para cuadrar importes


def parse_cabecera(stream):
    cab = stream.read(32)
    if len(cab) < 32:
        raise ValueError("cabecera corta")
    len_cab = struct.unpack("<H", cab[8:10])[0]
    len_reg = struct.unpack("<H", cab[10:12])[0]
    if len_cab <= 32 or len_cab > TOPE_CABECERA:
        raise ValueError("cabecera implausible")
    resto = stream.read(len_cab - 32)
    campos, off, pos = [], 0, 1
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:
            break
        b = resto[off:off + 32]
        campos.append({"nombre": b[0:11].split(b"\x00")[0].decode("ascii", "replace"),
                       "tipo": chr(b[11]), "ini": pos, "long": b[16]})
        pos += b[16]
        off += 32
    return len_reg, campos


def num(rec, c):
    if not c:
        return 0.0
    s = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def txt_lleno(rec, c):
    if not c:
        return False
    return bool(rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00"))


def cuenta(rec, c):
    """Devuelve SOLO los 3 primeros digitos: estructura del PGC, no dato."""
    if not c:
        return ""
    s = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
    return s[:3].decode("ascii", "replace") if len(s) >= 3 else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()

    print(f"{len(dats)} contenedores. Agrupando por asiento...")

    n_asientos = 0
    lineas_por_asiento = Counter()
    patron = Counter()
    con_nif = 0
    con_iva = 0
    con_nif_e_iva = 0
    cuadra_debe_haber = 0
    base_derivable = 0
    base_y_tipo_coherentes = 0
    simples_compra = 0
    simples_venta = 0
    reconstruibles = 0
    usa_euro = 0
    usa_pta = 0
    vistos = set()
    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                real = None
                for i in z.infolist():
                    if not i.is_dir() and os.path.basename(i.filename).lower() == "diario.dbf":
                        real = i.filename
                        break
                if real is None:
                    continue
                with z.open(real) as f:
                    len_reg, campos = parse_cabecera(f)
                    idx = {c["nombre"]: c for c in campos}
                    cA, cS = idx.get("ASIEN"), idx.get("SUBCTA")
                    cED, cEH = idx.get("EURODEBE"), idx.get("EUROHABER")
                    cPD, cPH = idx.get("PTADEBE"), idx.get("PTAHABER")
                    cIVA, cNIF = idx.get("IVA"), idx.get("TERNIF")

                    grupos = defaultdict(list)
                    while True:
                        rec = f.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        a = int(num(rec, cA))
                        ed, eh = num(rec, cED), num(rec, cEH)
                        pd, ph = num(rec, cPD), num(rec, cPH)
                        # Importe efectivo: euro si lo hay, si no el campo legado
                        debe = ed if (ed or eh) else pd
                        haber = eh if (ed or eh) else ph
                        if ed or eh:
                            usa_euro += 1
                        elif pd or ph:
                            usa_pta += 1
                        grupos[a].append((
                            cuenta(rec, cS), debe, haber,
                            num(rec, cIVA), txt_lleno(rec, cNIF),
                            hashlib.blake2b(rec, digest_size=8).digest(),
                        ))
                        del rec

                    for a, lineas in grupos.items():
                        n_asientos += 1
                        lineas_por_asiento[min(len(lineas), 12)] += 1
                        h = hashlib.blake2b(
                            b"".join(sorted(l[5] for l in lineas)), digest_size=16)
                        vistos.add(h.digest())

                        gs = [l[0] for l in lineas]
                        hay_gasto = any(g.startswith("6") for g in gs)
                        hay_ingreso = any(g.startswith("7") for g in gs)
                        hay_iva_sop = any(g == "472" for g in gs)
                        hay_iva_rep = any(g == "477" for g in gs)
                        hay_acree = any(g in ("400", "401", "410", "411") for g in gs)
                        hay_deudor = any(g in ("430", "431", "440", "460", "465") for g in gs)

                        es_compra = hay_gasto and hay_iva_sop and hay_acree
                        es_venta = hay_ingreso and hay_iva_rep and hay_deudor
                        if es_compra:
                            patron["compra_completa"] += 1
                        elif es_venta:
                            patron["venta_completa"] += 1
                        elif hay_gasto or hay_ingreso:
                            patron["gasto_o_ingreso_sin_patron"] += 1
                        else:
                            patron["otros"] += 1

                        nif = any(l[4] for l in lineas)
                        iva = any(l[3] > 0 for l in lineas)
                        if nif:
                            con_nif += 1
                        if iva:
                            con_iva += 1
                        if nif and iva:
                            con_nif_e_iva += 1

                        sd = sum(l[1] for l in lineas)
                        sh = sum(l[2] for l in lineas)
                        if abs(sd - sh) < TOL and sd > 0:
                            cuadra_debe_haber += 1

                        # --- .Se puede derivar la base? Asiento simple 3 lineas ---
                        if es_compra and len(lineas) == 3:
                            simples_compra += 1
                            base = sum(l[1] for l in lineas if l[0].startswith("6"))
                            cuota = sum(l[1] for l in lineas if l[0] == "472")
                            total = sum(l[2] for l in lineas
                                        if l[0] in ("400", "401", "410", "411"))
                            tipo = max((l[3] for l in lineas if l[0] == "472"), default=0.0)
                            if base > 0 and abs(base + cuota - total) < TOL:
                                base_derivable += 1
                                if tipo > 0 and abs(base * tipo / 100.0 - cuota) < max(TOL, base * 0.001):
                                    base_y_tipo_coherentes += 1
                        elif es_venta and len(lineas) == 3:
                            simples_venta += 1

                        if (es_compra or es_venta) and nif and iva:
                            reconstruibles += 1
                    grupos.clear()
        except Exception as e:
            errores[type(e).__name__] += 1

    unicos = len(vistos)
    del vistos

    def p(n, d):
        return round(n / d * 100, 2) if d else 0.0

    salida = {
        "version": "asientos_v1",
        "asientos_totales": n_asientos,
        "asientos_unicos": unicos,
        "factor_duplicacion": round(n_asientos / unicos, 2) if unicos else 0,
        "lineas_por_asiento": {str(k): v for k, v in sorted(lineas_por_asiento.items())},
        "patron": dict(patron),
        "patron_pct": {k: p(v, n_asientos) for k, v in patron.items()},
        "con_nif_contraparte_pct": p(con_nif, n_asientos),
        "con_tipo_iva_pct": p(con_iva, n_asientos),
        "con_nif_y_iva_pct": p(con_nif_e_iva, n_asientos),
        "cuadra_debe_haber_pct": p(cuadra_debe_haber, n_asientos),
        "RECONSTRUIBLES_POR_EL_MOTOR": {
            "n": reconstruibles,
            "pct": p(reconstruibles, n_asientos),
            "criterio": "patron compra/venta completo + NIF contraparte + tipo de IVA",
        },
        "derivacion_de_base": {
            "compras_simples_3_lineas": simples_compra,
            "ventas_simples_3_lineas": simples_venta,
            "base_mas_cuota_igual_total": base_derivable,
            "pct_sobre_compras_simples": p(base_derivable, simples_compra),
            "ademas_base_por_tipo_igual_cuota": base_y_tipo_coherentes,
            "pct_coherentes": p(base_y_tipo_coherentes, simples_compra),
        },
        "campo_de_importe": {"lineas_en_euro": usa_euro, "lineas_en_campo_legado": usa_pta},
        "errores": dict(errores),
        "nota": "Solo recuentos. Ningun valor, ningun hash publicado.",
    }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 64)
    print(f"  asientos totales     : {n_asientos:,}")
    print(f"  ASIENTOS UNICOS      : {unicos:,}")
    print(f"  factor duplicacion   : {salida['factor_duplicacion']}x")
    print(f"  cuadran debe=haber   : {salida['cuadra_debe_haber_pct']}%")
    print("=" * 64)
    print("")
    print("PATRON DEL ASIENTO:")
    for k, v in patron.most_common():
        print(f"   {k:<32}{v:>9,}  ({p(v, n_asientos):>5.2f}%)")
    print("")
    print("INFORMACION DISPONIBLE A NIVEL DE ASIENTO:")
    print(f"   con NIF de contraparte : {salida['con_nif_contraparte_pct']:>6.2f}%")
    print(f"   con tipo de IVA        : {salida['con_tipo_iva_pct']:>6.2f}%")
    print(f"   con ambos              : {salida['con_nif_y_iva_pct']:>6.2f}%")
    print("")
    r = salida["RECONSTRUIBLES_POR_EL_MOTOR"]
    print(f"*** RECONSTRUIBLES POR EL MOTOR: {r['n']:,}  ({r['pct']}%) ***")
    print("")
    d = salida["derivacion_de_base"]
    print("MISTERIO DE BASEIMPO — .se puede derivar la base?")
    print(f"   compras simples de 3 lineas   : {d['compras_simples_3_lineas']:,}")
    print(f"   base + cuota = total          : {d['base_mas_cuota_igual_total']:,}"
          f"  ({d['pct_sobre_compras_simples']}%)")
    print(f"   ademas base x tipo = cuota    : {d['ademas_base_por_tipo_igual_cuota']:,}"
          f"  ({d['pct_coherentes']}%)")
    print("")
    print("LINEAS POR ASIENTO:")
    for k, v in sorted(lineas_por_asiento.items()):
        et = f"{k}" if k < 12 else "12+"
        print(f"   {et:>3} lineas: {v:>9,}  ({p(v, n_asientos):>5.2f}%)")
    if errores:
        print(f"\nErrores: {dict(errores)}")
    print(f"\nEscrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
