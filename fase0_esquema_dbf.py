#!/usr/bin/env python3
"""
fase0_esquema_dbf.py — Iteracion 4: el esquema, sin los datos.

Lee UNICAMENTE la cabecera de los .dbf que viven dentro de los contenedores
ZIP (.DAT). Una cabecera dBase contiene: version, numero de registros,
longitud de registro, codigo de pagina, y la definicion de los campos
(nombre, tipo, longitud). NO contiene ninguna fila.

GARANTIA ESTRUCTURAL, no una promesa
------------------------------------
El byte 8-9 de todo .dbf indica donde TERMINA la cabecera. Este script lee
exactamente esa cantidad de bytes y se detiene. No es que evite mirar los
datos: es que nunca llega a ellos. Si la cabecera declarase un tamano
absurdo, hay un tope duro de 65535 bytes.

Uso:
    python fase0_esquema_dbf.py "RUTA" [--objetivos Diario.dbf,SubCta.dbf]
"""

import os
import sys
import json
import zipfile
import struct
import argparse
from collections import defaultdict, Counter

SALIDA = "fase0_esquema_dbf.json"
TOPE_CABECERA = 65535

# Byte 29 de la cabecera: identificador de driver de idioma -> codigo de pagina
CODEPAGES = {
    0x00: "no declarado", 0x01: "cp437 (DOS EEUU)", 0x02: "cp850 (DOS internacional)",
    0x03: "cp1252 (Windows ANSI)", 0x04: "cp10000 (Mac)", 0x64: "cp852",
    0x65: "cp866", 0x66: "cp865", 0x67: "cp861", 0x6A: "cp737", 0x6B: "cp857",
    0x78: "cp950", 0x79: "cp949", 0x7A: "cp936", 0x7B: "cp932",
    0x7C: "cp874", 0x7D: "cp1255", 0x7E: "cp1256",
    0xC8: "cp1250", 0xC9: "cp1251", 0xCA: "cp1254", 0xCB: "cp1253",
    0x57: "cp1252 (ANSI)", 0x58: "cp1252 (Europa occidental)", 0x59: "cp1252",
}

VERSIONES = {
    0x02: "FoxBASE", 0x03: "dBase III+ sin memo", 0x04: "dBase IV sin memo",
    0x05: "dBase V sin memo", 0x30: "Visual FoxPro", 0x31: "Visual FoxPro autoinc",
    0x32: "Visual FoxPro varchar", 0x43: "dBase IV con .dbt",
    0x83: "dBase III+ con memo", 0x8B: "dBase IV con memo",
    0xF5: "FoxPro 2.x con memo", 0xFB: "FoxPro sin memo",
}


def leer_cabecera(stream):
    """Lee y parsea SOLO la cabecera. Nunca toca la zona de registros."""
    cab = stream.read(32)
    if len(cab) < 32:
        raise ValueError("fichero mas corto que una cabecera dBase")

    version = cab[0]
    aa, mm, dd = cab[1], cab[2], cab[3]
    n_registros = struct.unpack("<I", cab[4:8])[0]
    long_cabecera = struct.unpack("<H", cab[8:10])[0]
    long_registro = struct.unpack("<H", cab[10:12])[0]
    driver = cab[29]

    if long_cabecera <= 32 or long_cabecera > TOPE_CABECERA:
        raise ValueError(f"longitud de cabecera implausible: {long_cabecera}")

    # <-- AQUI ESTA EL LIMITE DURO: solo lo que falta de cabecera, nada mas.
    resto = stream.read(long_cabecera - 32)

    campos = []
    off = 0
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:      # terminador de la lista de campos
            break
        bruto = resto[off:off + 32]
        nombre = bruto[0:11].split(b"\x00")[0].decode("ascii", "replace")
        tipo = chr(bruto[11])
        longitud = bruto[16]
        decimales = bruto[17]
        campos.append({"nombre": nombre, "tipo": tipo,
                       "long": longitud, "dec": decimales})
        off += 32

    suma = sum(c["long"] for c in campos) + 1  # +1 del byte de borrado
    return {
        "version_byte": f"0x{version:02X}",
        "version": VERSIONES.get(version, "desconocida"),
        "ultima_actualizacion": f"{1900 + aa if aa >= 70 else 2000 + aa}-{mm:02d}-{dd:02d}",
        "n_registros": n_registros,
        "long_cabecera": long_cabecera,
        "long_registro": long_registro,
        "codepage_byte": f"0x{driver:02X}",
        "codepage": CODEPAGES.get(driver, f"desconocido (0x{driver:02X})"),
        "n_campos": len(campos),
        "campos": campos,
        "cuadra_long_registro": (suma == long_registro),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--objetivos", default="Diario.dbf,SubCta.dbf",
                    help="Nombres internos a inspeccionar, separados por coma.")
    ap.add_argument("--n-muestras", type=int, default=15,
                    help="Contenedores a muestrear, repartidos por la carpeta.")
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)
    objetivos = [o.strip().lower() for o in args.objetivos.split(",") if o.strip()]

    dats = []
    for dirpath, _, filenames in os.walk(raiz):
        for n in filenames:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dirpath, n))
    dats.sort()
    if not dats:
        print("No hay contenedores .DAT en esa ruta.")
        return 1

    # Muestreo repartido: uno de cada N, para cubrir toda la horquilla temporal.
    paso = max(1, len(dats) // args.n_muestras)
    muestra = dats[::paso][:args.n_muestras]

    print(f"{len(dats)} contenedores. Muestreando {len(muestra)} repartidos.")
    print("Leyendo SOLO cabeceras...")

    resultados = defaultdict(list)
    errores = Counter()

    for ruta in muestra:
        try:
            with zipfile.ZipFile(ruta) as z:
                por_nombre = {os.path.basename(i.filename).lower(): i.filename
                              for i in z.infolist() if not i.is_dir()}
                for obj in objetivos:
                    real = por_nombre.get(obj)
                    if not real:
                        continue
                    with z.open(real) as f:
                        resultados[obj].append(leer_cabecera(f))
        except Exception as e:
            errores[f"{type(e).__name__}"] += 1

    salida = {"version": "esquema_dbf_v1", "n_contenedores": len(dats),
              "n_muestreados": len(muestra), "tablas": {}, "errores": dict(errores)}

    for obj, lst in resultados.items():
        if not lst:
            continue
        firmas = Counter(tuple((c["nombre"], c["tipo"], c["long"], c["dec"])
                               for c in h["campos"]) for h in lst)
        principal = firmas.most_common(1)[0][0]
        salida["tablas"][obj] = {
            "n_cabeceras_leidas": len(lst),
            "n_esquemas_distintos": len(firmas),
            "estable_en_el_tiempo": len(firmas) == 1,
            "codepages_vistos": dict(Counter(h["codepage"] for h in lst)),
            "versiones_vistas": dict(Counter(h["version"] for h in lst)),
            "long_registro": dict(Counter(h["long_registro"] for h in lst)),
            "registros_min": min(h["n_registros"] for h in lst),
            "registros_max": max(h["n_registros"] for h in lst),
            "registros_suma_muestra": sum(h["n_registros"] for h in lst),
            "cuadra_long_registro": all(h["cuadra_long_registro"] for h in lst),
            "campos": [{"nombre": n, "tipo": t, "long": l, "dec": d}
                       for (n, t, l, d) in principal],
        }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    for obj, b in salida["tablas"].items():
        print("")
        print("=" * 70)
        print(f"  {obj}")
        print("=" * 70)
        print(f"  cabeceras leidas   : {b['n_cabeceras_leidas']}")
        print(f"  esquemas distintos : {b['n_esquemas_distintos']}"
              f"   -> {'ESTABLE' if b['estable_en_el_tiempo'] else 'CAMBIA EN EL TIEMPO'}")
        print(f"  codigo de pagina   : {b['codepages_vistos']}")
        print(f"  version dBase      : {b['versiones_vistas']}")
        print(f"  long. de registro  : {b['long_registro']}  (cuadra: {b['cuadra_long_registro']})")
        print(f"  registros por copia: min {b['registros_min']}  max {b['registros_max']}")
        print("")
        print(f"  {'campo':<14}{'tipo':<6}{'long':>5}{'dec':>5}")
        print("  " + "-" * 32)
        for c in b["campos"]:
            print(f"  {c['nombre']:<14}{c['tipo']:<6}{c['long']:>5}{c['dec']:>5}")

    if errores:
        print("")
        print(f"Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
