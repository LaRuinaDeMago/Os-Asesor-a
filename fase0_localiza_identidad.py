#!/usr/bin/env python3
"""
fase0_localiza_identidad.py — .En que campo vive la identidad del cliente?

Necesitamos agrupar los 1.287 contenedores por cliente para construir el
inventario. Sabemos que NO sirven: el nombre de subcarpeta (van por fecha), el
codigo de empresa de ContaPlus (varia por ano) ni datempre.dbf (esta vacio).

Este script recorre TODOS los campos de las tablas candidatas y, para cada uno,
mide dos cosas:
  1. En cuantos contenedores contiene algo con FORMA de NIF/CIF/NIE.
  2. Cuantos valores DISTINTOS tiene (contando hashes en memoria).

El resultado se interpreta solo:
    ~1 valor distinto      -> el NIF del despacho (presentador)
    ~57 valores distintos  -> el NIF del CLIENTE. Ese es el que buscamos.
    ~1.287 distintos       -> un numero de referencia, no una identidad.

REGLA DURA
----------
Lee valores reales, pero es incapaz de emitirlos:
  - Nunca imprime ni escribe el valor de un campo.
  - Los hashes existen SOLO en memoria para contar distintos; se publica el
    RECUENTO, jamas el hash (art. 4.5: un hash de un identificador sigue
    siendo dato personal).
  - Los errores se agrupan por TIPO de excepcion, nunca por su mensaje: un
    mensaje de error puede arrastrar el dato que lo provoco.
  - No escribe ningun fichero _LOCAL: aqui no hay nada que mirar a mano.

Uso:
    python fase0_localiza_identidad.py "RUTA"
"""

import os
import re
import sys
import json
import zipfile
import struct
import hashlib
import argparse
from collections import Counter, defaultdict

# La salida se escribe SIEMPRE junto al script, nunca en el directorio desde el
# que se lance. Asi el comando funciona desde cualquier carpeta y el resultado
# aparece siempre en el mismo sitio.
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fase0_identidad.json")
TOPE_CABECERA = 65535

TABLAS = ["M390A.dbf", "LegalC.dbf", "SubCta.dbf", "TelDat.dbf"]

# Forma de NIF/CIF/NIE espanol. Solo FORMA, no se valida el digito de control:
# aqui solo hace falta distinguir "esto parece un identificador" de "esto es
# un importe o una fecha".
RE_DNI = re.compile(rb"^\d{8}[A-Za-z]$")
RE_NIE = re.compile(rb"^[XYZxyz]\d{7}[A-Za-z]$")
RE_CIF = re.compile(rb"^[A-HJ-NP-SUVWa-hj-np-suvw]\d{7}[0-9A-Ja-j]$")


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
        campos.append({
            "nombre": b[0:11].split(b"\x00")[0].decode("ascii", "replace"),
            "tipo": chr(b[11]), "ini": pos, "long": b[16],
        })
        pos += b[16]
        off += 32
    return len_reg, campos


def forma_nif(v):
    return bool(RE_DNI.match(v) or RE_NIE.match(v) or RE_CIF.match(v))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--max-registros", type=int, default=40,
                    help="Registros a leer por tabla y contenedor (por defecto 40).")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es una carpeta.")
        return 1

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()

    objetivos = {t.lower(): t for t in TABLAS}
    print(f"{len(dats)} contenedores. Buscando el campo de identidad en:")
    print("   " + ", ".join(TABLAS))
    print("(se leen valores, pero solo para contar; nada se guarda ni se imprime)")
    print("")

    # tabla -> campo -> metricas
    stats = defaultdict(lambda: defaultdict(
        lambda: {"nif": 0, "lleno": 0, "vistos": set()}))
    contenedores_con = Counter()
    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                presentes = {}
                for i in z.infolist():
                    b = os.path.basename(i.filename).lower()
                    if b in objetivos and not i.is_dir():
                        presentes[b] = i.filename
                for clave, interno in presentes.items():
                    tabla = objetivos[clave]
                    try:
                        with z.open(interno) as f:
                            len_reg, campos = parse_cabecera(f)
                            contenedores_con[tabla] += 1
                            leidos = 0
                            # Un contenedor aporta como mucho un valor distinto
                            # por campo: nos interesa la identidad del fichero,
                            # no cuantas filas tiene.
                            primero = {}
                            while leidos < args.max_registros:
                                rec = f.read(len_reg)
                                if len(rec) < len_reg or rec[:1] == b"\x1a":
                                    break
                                if rec[:1] == b"*":
                                    continue
                                leidos += 1
                                for c in campos:
                                    if c["tipo"] != "C":
                                        continue
                                    v = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
                                    if not v:
                                        continue
                                    s = stats[tabla][c["nombre"]]
                                    if c["nombre"] not in primero:
                                        primero[c["nombre"]] = True
                                        s["lleno"] += 1
                                        s["vistos"].add(
                                            hashlib.blake2b(v, digest_size=12).digest())
                                        if forma_nif(v):
                                            s["nif"] += 1
                                    del v
                                del rec
                    except Exception as e:
                        errores[f"{tabla}:{type(e).__name__}"] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    # ---- consolidar: solo nombres de campo y numeros ----
    salida = {"version": "identidad_v1", "n_contenedores": len(dats), "tablas": {}}
    for tabla in TABLAS:
        n_cont = contenedores_con.get(tabla, 0)
        filas = []
        for campo, s in stats.get(tabla, {}).items():
            filas.append({
                "campo": campo,
                "contenedores_con_valor": s["lleno"],
                "pct_con_forma_de_nif": round(s["nif"] / s["lleno"] * 100, 1) if s["lleno"] else 0.0,
                "valores_distintos": len(s["vistos"]),
            })
        filas.sort(key=lambda r: (-r["pct_con_forma_de_nif"], r["valores_distintos"]))
        salida["tablas"][tabla] = {"contenedores_con_la_tabla": n_cont, "campos": filas}

    salida["errores"] = dict(errores)
    salida["nota"] = "Solo nombres de campo y recuentos. Ningun valor, ningun hash."

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    for tabla in TABLAS:
        b = salida["tablas"][tabla]
        if not b["contenedores_con_la_tabla"]:
            continue
        print("=" * 70)
        print(f"  {tabla}   (en {b['contenedores_con_la_tabla']} contenedores)")
        print("=" * 70)
        print(f"  {'campo':<16}{'con valor':>11}{'% forma NIF':>13}{'distintos':>11}")
        print("  " + "-" * 51)
        # Primero los que tienen forma de NIF; si no hay, los mas discriminantes.
        conf = [r for r in b["campos"] if r["pct_con_forma_de_nif"] > 50]
        resto = [r for r in b["campos"] if r["pct_con_forma_de_nif"] <= 50]
        for r in conf[:10]:
            print(f"  {r['campo']:<16}{r['contenedores_con_valor']:>11}"
                  f"{r['pct_con_forma_de_nif']:>12.1f}%{r['valores_distintos']:>11}  <== NIF")
        if not conf:
            print("  (ningun campo con forma de NIF)")
        print("  ... campos de texto mas discriminantes:")
        for r in sorted(resto, key=lambda r: -r["valores_distintos"])[:8]:
            print(f"  {r['campo']:<16}{r['contenedores_con_valor']:>11}"
                  f"{r['pct_con_forma_de_nif']:>12.1f}%{r['valores_distintos']:>11}")
        print("")

    if errores:
        print(f"Errores (por tipo): {dict(errores)}")
    print(f"Escrito: {SALIDA}")
    print("")
    print("COMO LEERLO: busca un campo con ~57 valores distintos. Ese agrupa por")
    print("cliente. Uno con 1 distinto es el despacho; uno con ~1.287 es una")
    print("referencia por copia, no una identidad.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
