#!/usr/bin/env python3
"""
fase0_sonda_contenedores.py — Iteracion 3.

Los .DAT resultaron ser archivos ZIP (firma PK\\x03\\x04). Esta sonda los abre
EN MEMORIA (no extrae nada a disco, no modifica nada) y responde:

  .Que ficheros hay dentro? .Cuanto dato real contienen descomprimidos?
  .Cual es el fichero grande que lleva los asientos?

SALVAGUARDA DE IDENTIDAD
------------------------
Un nombre de fichero interno solo se reporta si aparece en 20 o mas
SUBCARPETAS DISTINTAS de primer nivel. Si las subcarpetas son por cliente,
un nombre presente en 20 clientes distintos es por fuerza un nombre de
sistema, no el de una empresa. Todo lo demas se cuenta pero no se nombra.

Ademas: NUNCA se lee el contenido de las entradas. Solo se lee el indice del
ZIP (nombres, tamanos, metodo de compresion). El dato contable no se toca.

Uso:
    python fase0_sonda_contenedores.py "RUTA\\A\\LA\\CARPETA"
"""

import sys
import os
import json
import zipfile
import argparse
from collections import Counter, defaultdict

SALIDA = "fase0_contenedores.json"
SALIDA_LOCAL = "fase0_contenedores_LOCAL.json"

MIN_SUBCARPETAS = 20   # umbral para declarar un nombre "de sistema"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)

    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es carpeta.")
        return 1

    # subcarpeta de primer nivel -> indice anonimo (nunca se imprime el nombre)
    sub_idx = {}

    def indice_sub(ruta):
        rel = os.path.relpath(ruta, raiz)
        primero = rel.split(os.sep)[0] if os.sep in rel else "(raiz)"
        if primero not in sub_idx:
            sub_idx[primero] = len(sub_idx)
        return sub_idx[primero]

    dats = []
    for dirpath, _, filenames in os.walk(raiz):
        for n in filenames:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dirpath, n))

    print(f"Contenedores .DAT encontrados: {len(dats)}. Leyendo indices...")

    n_zip = 0
    n_no_zip = 0
    n_corruptos = 0
    errores = Counter()

    # nombre interno -> {subcarpetas: set, n_apariciones, bytes_desc, bytes_comp}
    entradas = defaultdict(lambda: {
        "subs": set(), "n": 0, "desc": 0, "comp": 0,
        "desc_max": 0, "metodos": Counter(),
    })
    ext_interna = Counter()
    n_entradas_total = 0
    bytes_desc_total = 0
    entradas_por_cont = []

    for ruta in sorted(dats):
        try:
            if not zipfile.is_zipfile(ruta):
                n_no_zip += 1
                continue
            si = indice_sub(ruta)
            with zipfile.ZipFile(ruta) as z:
                info = z.infolist()   # solo el indice; no se lee contenido
                n_zip += 1
                entradas_por_cont.append(len(info))
                for it in info:
                    if it.is_dir():
                        continue
                    base = os.path.basename(it.filename)
                    e = entradas[base]
                    e["subs"].add(si)
                    e["n"] += 1
                    e["desc"] += it.file_size
                    e["comp"] += it.compress_size
                    e["desc_max"] = max(e["desc_max"], it.file_size)
                    e["metodos"][it.compress_type] += 1
                    ext_interna[os.path.splitext(base)[1].lower() or "(sin ext)"] += 1
                    n_entradas_total += 1
                    bytes_desc_total += it.file_size
        except zipfile.BadZipFile:
            n_corruptos += 1
        except Exception as ex:
            errores[type(ex).__name__] += 1

    # --- separar nombres genericos (seguros) de los que no lo son ---
    genericos = {}
    n_no_genericos = 0
    bytes_no_genericos = 0
    for base, e in entradas.items():
        if len(e["subs"]) >= MIN_SUBCARPETAS:
            genericos[base] = {
                "en_n_subcarpetas": len(e["subs"]),
                "n_apariciones": e["n"],
                "bytes_descomprimidos": e["desc"],
                "bytes_comprimidos": e["comp"],
                "tam_desc_max": e["desc_max"],
                "tam_desc_medio": round(e["desc"] / e["n"]) if e["n"] else 0,
            }
        else:
            n_no_genericos += 1
            bytes_no_genericos += e["desc"]

    genericos = dict(sorted(genericos.items(),
                            key=lambda kv: -kv[1]["bytes_descomprimidos"]))

    salida = {
        "version": "contenedores_v1",
        "n_contenedores_dat": len(dats),
        "n_son_zip": n_zip,
        "n_no_son_zip": n_no_zip,
        "n_zip_corruptos": n_corruptos,
        "n_subcarpetas_primer_nivel": len(sub_idx),
        "entradas_por_contenedor": {
            "min": min(entradas_por_cont) if entradas_por_cont else 0,
            "max": max(entradas_por_cont) if entradas_por_cont else 0,
            "media": round(sum(entradas_por_cont) / len(entradas_por_cont), 1)
                     if entradas_por_cont else 0,
        },
        "n_entradas_total": n_entradas_total,
        "bytes_descomprimidos_total": bytes_desc_total,
        "extensiones_internas": dict(ext_interna.most_common(20)),
        "nombres_de_sistema": genericos,
        "nombres_no_genericos": {
            "cuantos": n_no_genericos,
            "bytes_descomprimidos": bytes_no_genericos,
            "nota": ("Aparecen en menos de %d subcarpetas distintas. "
                     "No se nombran por precaucion." % MIN_SUBCARPETAS),
        },
        "errores": dict(errores),
        "nota": "Solo indices ZIP. No se ha leido el contenido de ninguna entrada.",
    }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({
            "AVISO": "Lleva TODOS los nombres internos. Nunca compartir ni versionar.",
            "raiz": raiz,
            "todas_las_entradas": {
                b: {"n": e["n"], "subs": len(e["subs"]), "desc": e["desc"]}
                for b, e in sorted(entradas.items(), key=lambda kv: -kv[1]["desc"])
            },
        }, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    print("")
    print("=" * 66)
    print(f"  Contenedores      : {len(dats)}")
    print(f"  Son ZIP validos   : {n_zip}")
    print(f"  No son ZIP        : {n_no_zip}")
    print(f"  ZIP corruptos     : {n_corruptos}")
    print(f"  Subcarpetas niv.1 : {len(sub_idx)}")
    print(f"  Entradas totales  : {n_entradas_total}")
    print(f"  Dato descomprimido: {bytes_desc_total / (1024*1024):.1f} MB")
    print("=" * 66)
    print("")
    print("Extensiones DENTRO de los ZIP:")
    for ext, n in ext_interna.most_common(12):
        print(f"   {ext:<14} {n:>7}")
    print("")
    print(f"Nombres de sistema (presentes en >= {MIN_SUBCARPETAS} subcarpetas distintas):")
    print(f"{'nombre':<20}{'subs':>6}{'aparic':>8}{'MB desc':>10}{'medio KB':>10}")
    print("-" * 56)
    for b, v in list(genericos.items())[:25]:
        print(f"{b:<20}{v['en_n_subcarpetas']:>6}{v['n_apariciones']:>8}"
              f"{v['bytes_descomprimidos']/(1024*1024):>10.1f}"
              f"{v['tam_desc_medio']/1024:>10.1f}")
    print("")
    print(f"Nombres NO genericos (no se muestran): {n_no_genericos} distintos, "
          f"{bytes_no_genericos/(1024*1024):.1f} MB")
    if errores:
        print(f"Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}         <- solo numeros y nombres de sistema")
    print(f"Escrito: {SALIDA_LOCAL}   <- lleva todos los nombres, NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
