#!/usr/bin/env python3
"""
fase0_relleno.py — Iteracion 5. PRIMERA LECTURA DE FILAS REALES.

Responde cuatro preguntas en una sola pasada:

  1. RELLENO: de las lineas del diario, .cuantas traen de verdad TERNIF,
     BASEIMPO, IVA, TIPOOPE...? (Fase 0, punto 5 — la puerta de todo)
  2. DEDUPLICACION: .cuantas lineas UNICAS hay, descontando que cada copia
     arrastra el historico anterior? (supuesto S15)
  3. TEST_ENCODING: .cp1252 o cp850? Contando bytes, no leyendo texto.
  4. DISTRIBUCION DE CUENTAS: que grupos del PGC aparecen y con que peso
     (Fase 0, punto 3 — dice que ramas del arbol escribir primero).

REGLA DURA
----------
Este script LEE filas reales, pero es incapaz de emitirlas:
  - Ningun valor de campo se guarda en ninguna variable que sobreviva a la
    iteracion. Solo se incrementan contadores enteros.
  - La deduplicacion usa hashes que viven SOLO en memoria y de los que solo
    se publica el RECUENTO, nunca el hash (art. 4.5: un hash de un
    identificador sigue siendo dato personal).
  - Lo unico que se publica de una cuenta contable son sus 3 primeros
    digitos, que son estructura del Plan General Contable, no dato de nadie.
  - No escribe fichero _LOCAL: aqui no hay nada que le sirva a nadie mirar.

Uso:
    python fase0_relleno.py "RUTA"
"""

import os
import sys
import json
import zipfile
import struct
import hashlib
import argparse
from collections import Counter, defaultdict

SALIDA = "fase0_relleno.json"
TOPE_CABECERA = 65535

# Campos cuyo relleno decide si el motor puede reejecutarse sobre el historico
CLAVE = ["TERNIF", "TERNOM", "BASEIMPO", "IVA", "TIPOOPE", "CONCEPTO",
         "FECHA", "FECHA_OP", "FECHA_EX", "SUBCTA", "CONTRA", "FACTURA",
         "DOCUMENTO", "EURODEBE", "EUROHABER", "RECTIFICA", "LCRITCAJA",
         "LRECT349", "LARREND347", "METAL", "NIRPF", "TBIENTRAN"]

# Combinacion minima para reconstruir la entrada del motor, MEDIDA POR LINEA.
#
# ⚠️ ESTA MEDICION DA ~0% Y ESE NUMERO NO SIGNIFICA LO QUE PARECE. Se conserva
# tal cual porque es el dato en bruto, pero la conclusion correcta esta en
# FASE0_RESULTADOS.md (seccion "Error metodologico corregido"):
#
#   - Es la PREGUNTA equivocada. En ContaPlus una factura se reparte entre
#     varias lineas del MISMO asiento (6xx la base, 472 la cuota y el tipo,
#     400 la contraparte), asi que NINGUNA linea puede traer los cinco campos.
#     La unidad de analisis es el ASIENTO. Medido bien: 68,26%.
#
#   - Ademas exige BASEIMPO, que el motor NO necesita: `reconstruir_compra()`
#     en retro_semaforo.py deriva la base de las lineas de gasto cuando
#     BASEIMPO no sirve, que es casi siempre. Medido el 26-08-2026 con
#     diag_baseimpo.py sobre 44.522 apuntes de IVA: el 99,4% son un CERO
#     literal.
#
# O sea: un 0% aqui NO dice que el historico sea inservible. Dice que esta
# metrica mira donde no hay que mirar. Se deja porque el recuento por campo
# (mas arriba) si vale, y porque borrar el numero seria esconder de donde
# salio la correccion.
MINIMO_MOTOR = ["TERNIF", "BASEIMPO", "IVA", "SUBCTA", "FECHA"]


def parse_cabecera(stream):
    cab = stream.read(32)
    if len(cab) < 32:
        raise ValueError("cabecera corta")
    n_reg = struct.unpack("<I", cab[4:8])[0]
    len_cab = struct.unpack("<H", cab[8:10])[0]
    len_reg = struct.unpack("<H", cab[10:12])[0]
    if len_cab <= 32 or len_cab > TOPE_CABECERA:
        raise ValueError("cabecera implausible")
    resto = stream.read(len_cab - 32)
    campos, off, pos = [], 0, 1  # pos 0 = bandera de borrado
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:
            break
        b = resto[off:off + 32]
        nombre = b[0:11].split(b"\x00")[0].decode("ascii", "replace")
        campos.append({"nombre": nombre, "tipo": chr(b[11]),
                       "ini": pos, "long": b[16]})
        pos += b[16]
        off += 32
    return n_reg, len_cab, len_reg, campos


def relleno(tipo, bruto):
    """.Este campo trae informacion? Devuelve bool. No devuelve el valor."""
    if tipo == "C":
        return bool(bruto.strip(b" \x00"))
    if tipo == "N" or tipo == "F":
        s = bruto.strip(b" \x00")
        if not s:
            return False
        try:
            return float(s) != 0.0
        except ValueError:
            return False
    if tipo == "D":
        s = bruto.strip(b" \x00")
        return len(s) == 8 and s.isdigit() and s != b"00000000"
    if tipo == "L":
        return bruto[:1] in (b"T", b"t", b"Y", b"y")
    return bool(bruto.strip(b" \x00"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--tabla", default="Diario.dbf")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    dats = []
    for dirpath, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dirpath, n))
    dats.sort()
    objetivo = args.tabla.lower()

    print(f"{len(dats)} contenedores. Leyendo filas de {args.tabla}...")
    print("(solo se incrementan contadores; ningun valor se guarda)")

    lleno = Counter()             # campo -> nº de lineas con dato
    total_lineas = 0
    borradas = 0
    completas_motor = 0
    copias_leidas = 0
    errores = Counter()

    vistos = set()                # hashes de linea (SOLO en memoria)
    grupos_cuenta = Counter()     # 3 primeros digitos de SUBCTA
    bytes_cp850 = 0
    bytes_cp1252 = 0
    bytes_utf8 = 0
    lineas_por_copia = []

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                real = None
                for i in z.infolist():
                    if not i.is_dir() and os.path.basename(i.filename).lower() == objetivo:
                        real = i.filename
                        break
                if real is None:
                    continue
                with z.open(real) as f:
                    n_reg, len_cab, len_reg, campos = parse_cabecera(f)
                    idx = {c["nombre"]: c for c in campos}
                    copias_leidas += 1
                    n_esta = 0
                    while True:
                        rec = f.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        n_esta += 1
                        total_lineas += 1
                        if rec[:1] == b"*":
                            borradas += 1
                            continue

                        # --- identidad de linea (hash, solo en memoria) ---
                        vistos.add(hashlib.blake2b(rec, digest_size=16).digest())

                        # --- relleno campo a campo ---
                        ok_min = True
                        for nom in CLAVE:
                            c = idx.get(nom)
                            if not c:
                                continue
                            bruto = rec[c["ini"]:c["ini"] + c["long"]]
                            if relleno(c["tipo"], bruto):
                                lleno[nom] += 1
                            elif nom in MINIMO_MOTOR:
                                ok_min = False
                            del bruto
                        if ok_min:
                            completas_motor += 1

                        # --- grupo de cuenta: 3 digitos del PGC ---
                        c = idx.get("SUBCTA")
                        if c:
                            s = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
                            if len(s) >= 3 and s[:3].isdigit():
                                grupos_cuenta[s[:3].decode("ascii")] += 1

                        # --- TEST_ENCODING sobre campos de texto ---
                        for nom in ("CONCEPTO", "TERNOM"):
                            c = idx.get(nom)
                            if not c:
                                continue
                            for b in rec[c["ini"]:c["ini"] + c["long"]]:
                                if 0xA0 <= b <= 0xA5:
                                    bytes_cp850 += 1
                                elif 0xE0 <= b <= 0xFC:
                                    bytes_cp1252 += 1
                                elif b == 0xC3:
                                    bytes_utf8 += 1
                    lineas_por_copia.append(n_esta)
        except Exception as e:
            errores[type(e).__name__] += 1

    unicas = len(vistos)
    del vistos

    def pct(n):
        return round(n / total_lineas * 100, 2) if total_lineas else 0.0

    vivas = total_lineas - borradas
    salida = {
        "version": "relleno_v1",
        "copias_leidas": copias_leidas,
        "lineas_totales": total_lineas,
        "lineas_marcadas_borradas": borradas,
        "lineas_vivas": vivas,
        "lineas_unicas_por_contenido": unicas,
        "factor_de_duplicacion": round(vivas / unicas, 2) if unicas else 0,
        "relleno_por_campo_pct": {k: pct(lleno.get(k, 0)) for k in CLAVE},
        "relleno_por_campo_n": {k: lleno.get(k, 0) for k in CLAVE},
        "lineas_reconstruibles_por_el_motor": {
            "n": completas_motor,
            "pct_sobre_vivas": round(completas_motor / vivas * 100, 2) if vivas else 0,
            "campos_exigidos": MINIMO_MOTOR,
        },
        "test_encoding": {
            "bytes_rango_cp850_A0_A5": bytes_cp850,
            "bytes_rango_cp1252_E0_FC": bytes_cp1252,
            "bytes_marca_utf8_C3": bytes_utf8,
            "veredicto": ("cp1252" if bytes_cp1252 > bytes_cp850 * 2
                          else "cp850" if bytes_cp850 > bytes_cp1252 * 2
                          else "AMBIGUO — revisar"),
        },
        "grupos_pgc_top40": dict(grupos_cuenta.most_common(40)),
        "n_grupos_pgc_distintos": len(grupos_cuenta),
        "lineas_por_copia": {
            "min": min(lineas_por_copia) if lineas_por_copia else 0,
            "max": max(lineas_por_copia) if lineas_por_copia else 0,
            "media": round(sum(lineas_por_copia) / len(lineas_por_copia), 1)
                     if lineas_por_copia else 0,
            "copias_vacias": sum(1 for x in lineas_por_copia if x == 0),
        },
        "errores": dict(errores),
        "nota": "Solo recuentos. Ningun valor de campo, ningun hash publicado.",
    }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    print("")
    print("=" * 64)
    print(f"  copias leidas          : {copias_leidas}")
    print(f"  lineas totales         : {total_lineas:,}")
    print(f"  marcadas como borradas : {borradas:,}")
    print(f"  lineas vivas           : {vivas:,}")
    print(f"  LINEAS UNICAS          : {unicas:,}")
    print(f"  factor de duplicacion  : {salida['factor_de_duplicacion']}x")
    print("=" * 64)
    print("")
    print("RELLENO POR CAMPO (% sobre lineas totales):")
    for k in CLAVE:
        n = lleno.get(k, 0)
        barra = "#" * int(pct(n) / 2.5)
        print(f"  {k:<12}{pct(n):>7.2f}%  {barra}")
    print("")
    r = salida["lineas_reconstruibles_por_el_motor"]
    print(f"RECONSTRUIBLES POR EL MOTOR: {r['n']:,}  ({r['pct_sobre_vivas']}% de las vivas)")
    print(f"   exigiendo: {', '.join(MINIMO_MOTOR)}")
    print("   ⚠️  MEDIDO POR LINEA, y por eso sale ~0%. NO significa que el")
    print("       historico sea inservible: una factura se reparte entre VARIAS")
    print("       lineas del mismo asiento, asi que ninguna linea puede traer")
    print("       los cinco campos. Por ASIENTO el resultado real es 68,26%.")
    print("       Ademas exige BASEIMPO, que el motor no necesita (lo deriva del")
    print("       gasto). Ver FASE0_RESULTADOS.md, 'Error metodologico corregido'.")
    print("")
    t = salida["test_encoding"]
    print(f"TEST_ENCODING -> {t['veredicto']}")
    print(f"   rango cp850 (A0-A5) : {t['bytes_rango_cp850_A0_A5']:,}")
    print(f"   rango cp1252(E0-FC) : {t['bytes_rango_cp1252_E0_FC']:,}")
    print(f"   marca utf8  (C3)    : {t['bytes_marca_utf8_C3']:,}")
    print("")
    print(f"GRUPOS DEL PGC ({len(grupos_cuenta)} distintos). Top 25:")
    for g, n in grupos_cuenta.most_common(25):
        print(f"   {g}  {n:>9,}  ({n/vivas*100:>5.2f}%)")
    if errores:
        print("")
        print(f"Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
