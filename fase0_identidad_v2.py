#!/usr/bin/env python3
"""
fase0_identidad_v2.py — .Donde vive la identidad del cliente? (corregido)

QUE ARREGLA RESPECTO A LA v1
----------------------------
La v1 solo leia el PRIMER registro de cada tabla y contenedor, asi que de
SubCta.dbf (cientos de filas) solo miraba una. El control lo delato: NIF salio
con 29 valores distintos cuando tenia que dar miles. Aqui se leen todos los
registros hasta un tope.

QUE MIDE, Y POR QUE ESTA VEZ ES LA PREGUNTA CORRECTA
----------------------------------------------------
Un campo de IDENTIDAD tiene una firma inconfundible:
  - es CONSTANTE dentro de un contenedor (todas sus filas dicen lo mismo), y
  - VARIA entre contenedores, con tantos valores distintos como clientes haya.
Un campo de DATO varia dentro del propio contenedor. Distinguir esas dos cosas
es lo que la v1 no hacia.

Por cada campo de texto se publica:
  - valores distintos en todo el corpus
  - % de contenedores en los que el campo es constante
  - % de valores con forma de NIF/CIF/NIE

Ademas:
  - DATOS.ASC: cuantos ficheros DISTINTOS hay (por hash de su contenido). Si
    salen ~57 es el manifiesto de empresa del backup. Si sale 1, es cabecera.
  - M390A.dbf: cuantos campos NUMERICOS traen valor distinto de cero. Responde
    si el modulo del 390 esta relleno o es una plantilla en blanco, que la v1
    no podia contestar porque solo miraba campos de texto.

REGLA DURA
----------
Lee valores reales y es incapaz de emitirlos: solo contadores y hashes que
viven en memoria, de los que se publica el RECUENTO y nunca el hash. Los
errores se agrupan por TIPO de excepcion, jamas por su mensaje. No escribe
ningun fichero _LOCAL. La salida se escribe junto al script, no en el
directorio desde el que se lance.

Uso:
    python fase0_identidad_v2.py "RUTA"
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

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "fase0_identidad_v2.json")
TOPE_CABECERA = 65535
TOPE_REGISTROS = 1500       # por tabla y contenedor

TABLAS = ["LegalC.dbf", "SubCta.dbf", "TelDat.dbf", "Datnic.dbf"]

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


def h(v):
    return hashlib.blake2b(v, digest_size=12).digest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
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
    print(f"{len(dats)} contenedores.")
    print("Leyendo TODOS los registros (la v1 solo leia el primero).")
    print("Nada se guarda ni se imprime: solo contadores.")
    print("")

    glob = defaultdict(lambda: defaultdict(
        lambda: {"vistos": set(), "nif": 0, "n": 0,
                 "cont_con_campo": 0, "cont_constante": 0}))
    cont_con_tabla = Counter()

    asc_hashes = set()
    asc_n = 0
    asc_tam = []
    asc_con_nif = 0

    m390_num_no_cero = []
    m390_leidos = 0

    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                mapa = {}
                for i in z.infolist():
                    if i.is_dir():
                        continue
                    mapa.setdefault(os.path.basename(i.filename).lower(), i.filename)

                # ---------- DATOS.ASC: .manifiesto de empresa? ----------
                if "datos.asc" in mapa:
                    try:
                        with z.open(mapa["datos.asc"]) as f:
                            data = f.read(65536)
                        asc_n += 1
                        asc_tam.append(len(data))
                        asc_hashes.add(h(data))
                        if any(forma_nif(t) for t in re.split(rb"[^0-9A-Za-z]+", data) if t):
                            asc_con_nif += 1
                        del data
                    except Exception as e:
                        errores[f"DATOS.ASC:{type(e).__name__}"] += 1

                # ---------- M390A: .estan rellenas las casillas? ----------
                if "m390a.dbf" in mapa:
                    try:
                        with z.open(mapa["m390a.dbf"]) as f:
                            len_reg, campos = parse_cabecera(f)
                            rec = f.read(len_reg)
                            if len(rec) == len_reg:
                                m390_leidos += 1
                                nz = 0
                                for c in campos:
                                    if c["tipo"] not in ("N", "F"):
                                        continue
                                    s = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
                                    if s:
                                        try:
                                            if float(s) != 0.0:
                                                nz += 1
                                        except ValueError:
                                            pass
                                m390_num_no_cero.append(nz)
                            del rec
                    except Exception as e:
                        errores[f"M390A:{type(e).__name__}"] += 1

                # ---------- tablas: constante dentro / distinto fuera ----------
                for clave, tabla in objetivos.items():
                    if clave not in mapa:
                        continue
                    try:
                        with z.open(mapa[clave]) as f:
                            len_reg, campos = parse_cabecera(f)
                            cont_con_tabla[tabla] += 1
                            locales = defaultdict(set)
                            leidos = 0
                            while leidos < TOPE_REGISTROS:
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
                                    g = glob[tabla][c["nombre"]]
                                    g["n"] += 1
                                    g["vistos"].add(h(v))
                                    if forma_nif(v):
                                        g["nif"] += 1
                                    locales[c["nombre"]].add(h(v))
                                    del v
                                del rec
                            for campo, s in locales.items():
                                g = glob[tabla][campo]
                                g["cont_con_campo"] += 1
                                if len(s) == 1:
                                    g["cont_constante"] += 1
                            locales.clear()
                    except Exception as e:
                        errores[f"{tabla}:{type(e).__name__}"] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    # ---------------- consolidar ----------------
    salida = {"version": "identidad_v2", "n_contenedores": len(dats), "tablas": {}}
    for tabla in TABLAS:
        filas = []
        for campo, g in glob.get(tabla, {}).items():
            cc = g["cont_con_campo"]
            filas.append({
                "campo": campo,
                "valores_leidos": g["n"],
                "distintos_en_el_corpus": len(g["vistos"]),
                "contenedores_con_el_campo": cc,
                "pct_constante_en_contenedor": round(g["cont_constante"] / cc * 100, 1) if cc else 0.0,
                "pct_forma_nif": round(g["nif"] / g["n"] * 100, 1) if g["n"] else 0.0,
            })
        # Candidato a identidad: constante dentro, y pocos distintos fuera.
        filas.sort(key=lambda r: (-r["pct_constante_en_contenedor"],
                                  r["distintos_en_el_corpus"]))
        salida["tablas"][tabla] = {
            "contenedores_con_la_tabla": cont_con_tabla.get(tabla, 0),
            "campos": filas,
        }

    salida["datos_asc"] = {
        "contenedores_con_el_fichero": asc_n,
        "FICHEROS_DISTINTOS": len(asc_hashes),
        "tam_min": min(asc_tam) if asc_tam else 0,
        "tam_max": max(asc_tam) if asc_tam else 0,
        "contenedores_con_algo_con_forma_de_nif": asc_con_nif,
    }
    salida["m390a"] = {
        "registros_leidos": m390_leidos,
        "campos_numericos_no_cero_min": min(m390_num_no_cero) if m390_num_no_cero else 0,
        "campos_numericos_no_cero_max": max(m390_num_no_cero) if m390_num_no_cero else 0,
        "campos_numericos_no_cero_media": round(sum(m390_num_no_cero) / len(m390_num_no_cero), 1) if m390_num_no_cero else 0,
        "copias_totalmente_a_cero": sum(1 for x in m390_num_no_cero if x == 0),
    }
    salida["errores"] = dict(errores)
    salida["nota"] = "Solo nombres de campo y recuentos. Ningun valor, ningun hash."

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    a = salida["datos_asc"]
    print("=" * 74)
    print("  DATOS.ASC — .es el manifiesto de empresa del backup?")
    print("=" * 74)
    print(f"   contenedores con el fichero : {a['contenedores_con_el_fichero']}")
    print(f"   FICHEROS DISTINTOS          : {a['FICHEROS_DISTINTOS']}   <== la cifra clave")
    print(f"   tamano (bytes)              : {a['tam_min']} - {a['tam_max']}")
    print(f"   con algo con forma de NIF   : {a['contenedores_con_algo_con_forma_de_nif']}")
    print("")
    m = salida["m390a"]
    print("=" * 74)
    print("  M390A.dbf — .plantilla en blanco o modelo relleno?")
    print("=" * 74)
    print(f"   registros leidos            : {m['registros_leidos']}")
    print(f"   casillas numericas != 0     : min {m['campos_numericos_no_cero_min']}  "
          f"media {m['campos_numericos_no_cero_media']}  max {m['campos_numericos_no_cero_max']}")
    print(f"   copias enteramente a cero   : {m['copias_totalmente_a_cero']}")
    print("")
    for tabla in TABLAS:
        b = salida["tablas"].get(tabla)
        if not b or not b["contenedores_con_la_tabla"]:
            continue
        print("=" * 74)
        print(f"  {tabla}   (en {b['contenedores_con_la_tabla']} contenedores)")
        print("=" * 74)
        print(f"  {'campo':<14}{'leidos':>9}{'distintos':>11}{'constante':>11}{'formaNIF':>10}")
        print("  " + "-" * 55)
        for r in b["campos"][:14]:
            marca = ""
            if r["pct_constante_en_contenedor"] >= 95 and 5 <= r["distintos_en_el_corpus"] <= 400:
                marca = "  <== CANDIDATO"
            print(f"  {r['campo']:<14}{r['valores_leidos']:>9}"
                  f"{r['distintos_en_el_corpus']:>11}"
                  f"{r['pct_constante_en_contenedor']:>10.1f}%"
                  f"{r['pct_forma_nif']:>9.1f}%{marca}")
        print("")
    if errores:
        print(f"Errores (por tipo): {dict(errores)}")
    print(f"Escrito: {SALIDA}")
    print("")
    print("COMO LEERLO: el campo de identidad es CONSTANTE dentro de cada")
    print("contenedor (~100%) y tiene pocos valores distintos en el corpus.")
    print("Si SubCta.NIF no da ahora miles de distintos, el bug sigue ahi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
