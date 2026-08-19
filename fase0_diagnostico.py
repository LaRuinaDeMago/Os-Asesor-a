#!/usr/bin/env python3
"""
fase0_diagnostico.py — .Por que salen 35 grupos si hay 43 clientes?

Tres preguntas, una pasada. Ninguna se responde por conjetura.

  A) .QUE SON LOS 2.570 CONTENEDORES SIN DIARIO?  (67% del corpus, sin mirar)
     Se listan sus tablas internas y el TAMANO DESCOMPRIMIDO de cada una. Un
     .dbf vacio pesa solo su cabecera; uno con datos pesa mucho mas. Asi se
     sabe si llevan contabilidad de verdad SIN descomprimir nada: el tamano
     esta en el indice del ZIP.

  B) .ESTA LA HUELLA FUSIONANDO CLIENTES?
     Dos controles:
       - similitud MINIMA dentro de cada grupo. Un cliente real tiene todos
         sus pares altos; un grupo pegado por contagio tendra parejas que
         apenas se parecen.
       - contenedores del MISMO grupo, MISMO ejercicio y MISMA carpeta de
         copia. Eso deberia ser imposible: una empresa aparece una vez por
         copia. Si pasa, hay dos empresas dentro de un grupo.

  C) .CUANTO SE COMIO EL UMBRAL ARBITRARIO DE 5 NIF?
     Distribucion real de NIF por contenedor. Si muchos tienen 3 o 4, el
     umbral (elegido a ojo, sin medir) esta tirando clientes a la basura.

REGLA DURA: solo recuentos, tamanos y nombres de tabla presentes en 20+
subcarpetas distintas. Ningun NIF, ningun nombre, ninguna ruta en el agregado.
Errores por TIPO de excepcion. No aborta.

Uso:
    python fase0_diagnostico.py "RUTA"
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

BASE = os.path.dirname(os.path.abspath(__file__))
MAPA_HUELLA = os.path.join(BASE, "fase0_huella_LOCAL.json")
SALIDA = os.path.join(BASE, "fase0_diagnostico.json")

TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000
MIN_SUBCARPETAS = 20

RE_DNI = re.compile(rb"^\d{8}[A-Za-z]$")
RE_NIE = re.compile(rb"^[XYZxyz]\d{7}[A-Za-z]$")
RE_CIF = re.compile(rb"^[A-HJ-NP-SUVWa-hj-np-suvw]\d{7}[0-9A-Ja-j]$")


def forma_nif(v):
    return bool(RE_DNI.match(v) or RE_NIE.match(v) or RE_CIF.match(v))


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es una carpeta.")
        return 1

    grupo_de = {}
    if os.path.exists(MAPA_HUELLA):
        with open(MAPA_HUELLA, encoding="utf-8") as f:
            grupo_de = {k: int(v) for k, v in json.load(f)["contenedor_a_grupo"].items()}

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores. Diagnostico en marcha...")

    # ---------- A) los contenedores SIN diario ----------
    sin_d_n = 0
    sin_d_tam_zip = []
    sin_d_entradas = []
    sin_d_desc_total = []
    # nombre de tabla -> {subcarpetas, apariciones, tam descomprimido}
    tablas_sin_d = defaultdict(lambda: {"subs": set(), "n": 0, "desc": [], "con_datos": 0})
    subcarp_sin_d = set()
    con_d_n = 0

    # ---------- C) NIF por contenedor ----------
    nifs_por_cont = []
    huellas = {}

    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            rel = os.path.relpath(ruta, raiz)
            sub = rel.split(os.sep)[0] if os.sep in rel else "(raiz)"
            with zipfile.ZipFile(ruta) as z:
                info = [i for i in z.infolist() if not i.is_dir()]
                nombres = {os.path.basename(i.filename).lower(): i for i in info}
                tiene_diario = "diario.dbf" in nombres

                if tiene_diario:
                    con_d_n += 1
                else:
                    sin_d_n += 1
                    subcarp_sin_d.add(sub)
                    sin_d_tam_zip.append(os.path.getsize(ruta))
                    sin_d_entradas.append(len(info))
                    sin_d_desc_total.append(sum(i.file_size for i in info))
                    for i in info:
                        b = os.path.basename(i.filename)
                        t = tablas_sin_d[b]
                        t["subs"].add(sub)
                        t["n"] += 1
                        t["desc"].append(i.file_size)
                        # Un .dbf con datos pesa mucho mas que su cabecera.
                        # Umbral generoso: 4 KB. Sin descomprimir nada.
                        if i.file_size > 4096:
                            t["con_datos"] += 1

                # ---------- huella (para B y C) ----------
                if "subcta.dbf" in nombres:
                    try:
                        with z.open(nombres["subcta.dbf"].filename) as f:
                            len_reg, campos = parse_cabecera(f)
                            c = next((x for x in campos if x["nombre"] == "NIF"), None)
                            s = set()
                            if c:
                                leidos = 0
                                while leidos < TOPE_REGISTROS:
                                    rec = f.read(len_reg)
                                    if len(rec) < len_reg or rec[:1] == b"\x1a":
                                        break
                                    if rec[:1] == b"*":
                                        continue
                                    leidos += 1
                                    v = rec[c["ini"]:c["ini"] + c["long"]].strip(b" \x00")
                                    if v and forma_nif(v):
                                        s.add(hashlib.blake2b(v, digest_size=8).digest())
                                    del rec
                            nifs_por_cont.append(len(s))
                            if ruta in grupo_de:
                                huellas[ruta] = frozenset(s)
                    except Exception as e:
                        errores[f"subcta:{type(e).__name__}"] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    # ---------- A: consolidar tablas de los sin-diario ----------
    tablas = {}
    ocultas = 0
    for nom, t in sorted(tablas_sin_d.items(), key=lambda kv: -sum(kv[1]["desc"])):
        if len(t["subs"]) < MIN_SUBCARPETAS:
            ocultas += 1
            continue
        d = t["desc"]
        tablas[nom] = {
            "apariciones": t["n"],
            "subcarpetas": len(t["subs"]),
            "desc_total_MB": round(sum(d) / (1024 * 1024), 2),
            "desc_medio": round(sum(d) / len(d)) if d else 0,
            "desc_max": max(d) if d else 0,
            "copias_con_datos_mas_de_4KB": t["con_datos"],
        }

    # ---------- B: fusion de grupos ----------
    por_grupo = defaultdict(list)
    for ruta, g in grupo_de.items():
        if ruta in huellas:
            por_grupo[g].append(ruta)

    fusion = []
    for g, rutas in sorted(por_grupo.items()):
        if len(rutas) < 2:
            fusion.append({"grupo": g, "n": len(rutas), "sim_min": None, "sim_media": None})
            continue
        sims = []
        for i in range(len(rutas)):
            hi = huellas[rutas[i]]
            for j in range(i + 1, len(rutas)):
                hj = huellas[rutas[j]]
                u = len(hi | hj)
                sims.append(len(hi & hj) / u if u else 0.0)
        fusion.append({
            "grupo": g, "n": len(rutas),
            "sim_min": round(min(sims), 3),
            "sim_media": round(sum(sims) / len(sims), 3),
            "pares_bajo_0_2": sum(1 for s in sims if s < 0.2),
        })

    sospechosos = [f for f in fusion if f["sim_min"] is not None and f["sim_min"] < 0.2]

    # ---------- C: distribucion de NIF ----------
    dist = Counter()
    for n in nifs_por_cont:
        dist[min(n, 60) if n < 60 else 60] += 1
    bajo_umbral = sum(1 for n in nifs_por_cont if 1 <= n < 5)

    salida = {
        "version": "diagnostico_v1",
        "contenedores": len(dats),
        "con_diario": con_d_n,
        "sin_diario": sin_d_n,
        "A_contenedores_sin_diario": {
            "subcarpetas_en_que_viven": len(subcarp_sin_d),
            "tam_zip_min": min(sin_d_tam_zip) if sin_d_tam_zip else 0,
            "tam_zip_max": max(sin_d_tam_zip) if sin_d_tam_zip else 0,
            "tam_zip_medio": round(sum(sin_d_tam_zip) / len(sin_d_tam_zip)) if sin_d_tam_zip else 0,
            "casi_vacios_menos_de_2KB": sum(1 for t in sin_d_tam_zip if t < 2048),
            "entradas_por_contenedor_media": round(sum(sin_d_entradas) / len(sin_d_entradas), 1) if sin_d_entradas else 0,
            "descomprimido_total_MB": round(sum(sin_d_desc_total) / (1024 * 1024), 1),
            "tablas": tablas,
            "tablas_ocultas_por_precaucion": ocultas,
        },
        "B_fusion_de_grupos": {
            "grupos": fusion,
            "grupos_sospechosos_sim_min_bajo_0_2": len(sospechosos),
        },
        "C_nif_por_contenedor": {
            "contenedores_con_subcta": len(nifs_por_cont),
            "con_1_a_4_nif_descartados_por_el_umbral": bajo_umbral,
            "distribucion": {str(k): v for k, v in sorted(dist.items())},
        },
        "errores": dict(errores),
        "nota": "Solo recuentos y tamanos. Ningun NIF, nombre ni ruta.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    a = salida["A_contenedores_sin_diario"]
    print("")
    print("=" * 74)
    print(f"  A) LOS {sin_d_n} CONTENEDORES SIN DIARIO")
    print("=" * 74)
    print(f"   viven en {a['subcarpetas_en_que_viven']} subcarpetas")
    print(f"   tam del ZIP: {a['tam_zip_min']} - {a['tam_zip_max']} bytes "
          f"(medio {a['tam_zip_medio']})")
    print(f"   CASI VACIOS (< 2 KB)     : {a['casi_vacios_menos_de_2KB']}")
    print(f"   entradas por contenedor  : {a['entradas_por_contenedor_media']}")
    print(f"   dato descomprimido total : {a['descomprimido_total_MB']} MB")
    print("")
    if tablas:
        print(f"   {'tabla':<20}{'aparic':>8}{'MB':>9}{'medio B':>10}{'con datos':>11}")
        print("   " + "-" * 58)
        for nom, t in list(tablas.items())[:20]:
            print(f"   {nom:<20}{t['apariciones']:>8}{t['desc_total_MB']:>9.2f}"
                  f"{t['desc_medio']:>10}{t['copias_con_datos_mas_de_4KB']:>11}")
    else:
        print("   NO HAY NINGUNA TABLA presente en 20+ subcarpetas.")
        print("   -> los contenedores sin diario estan practicamente vacios.")
    print("")
    print("=" * 74)
    print("  B) .LA HUELLA FUSIONA CLIENTES?")
    print("=" * 74)
    print(f"   {'grupo':>6}{'copias':>8}{'sim min':>10}{'sim media':>11}{'pares<0.2':>11}")
    print("   " + "-" * 46)
    for f_ in sorted(fusion, key=lambda x: (x["sim_min"] is None, x["sim_min"])):
        smin = f"{f_['sim_min']:.3f}" if f_["sim_min"] is not None else "  -"
        smed = f"{f_['sim_media']:.3f}" if f_["sim_media"] is not None else "  -"
        pb = f_.get("pares_bajo_0_2", 0)
        marca = "  <== SOSPECHOSO" if f_["sim_min"] is not None and f_["sim_min"] < 0.2 else ""
        print(f"   {f_['grupo']:>6}{f_['n']:>8}{smin:>10}{smed:>11}{pb:>11}{marca}")
    print("")
    print(f"   Grupos con alguna pareja por debajo de 0,2: {len(sospechosos)}")
    print("")
    print("=" * 74)
    print("  C) .CUANTO SE COMIO EL UMBRAL DE 5 NIF?")
    print("=" * 74)
    c = salida["C_nif_por_contenedor"]
    print(f"   contenedores con SubCta.dbf : {c['contenedores_con_subcta']}")
    print(f"   DESCARTADOS por tener 1-4 NIF: {c['con_1_a_4_nif_descartados_por_el_umbral']}")
    print("")
    print("   NIF por contenedor:")
    for k in sorted(dist, key=int):
        n = dist[k]
        et = f"{k}" if k < 60 else "60+"
        print(f"     {et:>4} NIF: {n:>5}")
    if errores:
        print(f"\n   Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
