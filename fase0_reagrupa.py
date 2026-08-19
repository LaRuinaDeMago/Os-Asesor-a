#!/usr/bin/env python3
"""
fase0_reagrupa.py — Arregla los tres fallos que dejaron el mapa en 35 clientes.

FALLO 1 — Umbral arbitrario. fase0_huella_cliente.py exigia 5 NIF para admitir
un contenedor. Ese 5 lo eligio Claude a ojo, sin medir. Descarto 106
contenedores, entre ellos un bulto de 40 con exactamente 3 NIF que tiene toda la
pinta de ser un tipo de cliente pequeno (autonomos). Aqui el umbral baja a 1.

FALLO 2 — Fusion o deriva, sin distinguir. Cuatro grupos tienen parejas internas
que apenas se parecen. Hay dos explicaciones opuestas y hasta ahora no se habian
separado:
    - parejas de EJERCICIOS DISTINTOS  -> deriva temporal. Legitima: los
      proveedores de 2018 y los de 2025 pueden ser casi otros.
    - parejas del MISMO EJERCICIO      -> DOS EMPRESAS. Imposible que la misma
      empresa tenga dos maestros de subcuentas distintos el mismo ano.
Solo lo segundo es una fusion. Este script las separa y lo dice con numeros.

FALLO 3 — Estructura de carpetas ignorada. Se han tratado las 37 subcarpetas
como si todas fueran copias de seguridad, cuando algunas son envios al Registro
Mercantil. Se clasifican y se cuentan sus PDF, lo que habilita el contraste que
propuso el titular: la carpeta del Registro de 2025 deberia tener 11 PDF.

REGLA DURA: los NIF se hashean en memoria y solo se publican recuentos. Los
nombres de subcarpeta SI se imprimen —el titular ha confirmado que no contienen
clientes y las muestras vistas son fechas— pero se filtra cualquiera que
contenga algo con forma de NIF, por si acaso. Errores por TIPO de excepcion.

Uso:
    python fase0_reagrupa.py "RUTA"
"""

import os
import re
import sys
import csv
import json
import zipfile
import struct
import hashlib
import argparse
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
INVENTARIO = os.path.join(BASE, "inventario_LOCAL.csv")
SALIDA = os.path.join(BASE, "fase0_reagrupa.json")
SALIDA_LOCAL = os.path.join(BASE, "fase0_reagrupa_LOCAL.json")

TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000
MIN_NIFS = 1                 # antes 5, elegido a ojo
UMBRAL = 0.40                # el de la meseta estable
UMBRAL_CONFLICTO = 0.20      # por debajo de esto, dos copias no son la misma empresa

RE_DNI = re.compile(rb"^\d{8}[A-Za-z]$")
RE_NIE = re.compile(rb"^[XYZxyz]\d{7}[A-Za-z]$")
RE_CIF = re.compile(rb"^[A-HJ-NP-SUVWa-hj-np-suvw]\d{7}[0-9A-Ja-j]$")
RE_NIF_TXT = re.compile(r"\b(\d{8}[A-Za-z]|[A-HJ-NP-SUVWXYZ]\d{7}[0-9A-Ja-j])\b")
RE_REGISTRO = re.compile(r"REGISTRO|MERCANTIL|DEPOSIT|PRESENTAD|ENVIAD", re.I)
RE_ANIO = re.compile(r"\b(20\d{2})\b")


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


class UnionFind:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, x):
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es una carpeta.")
        return 1

    # ---------- FALLO 3: clasificar las subcarpetas ----------
    print("Clasificando subcarpetas...")
    subs = sorted(d for d in os.listdir(raiz) if os.path.isdir(os.path.join(raiz, d)))
    info_sub = []
    for s in subs:
        p = os.path.join(raiz, s)
        n_dat = n_pdf = n_otros = 0
        for dp, _, fns in os.walk(p):
            for f in fns:
                e = os.path.splitext(f)[1].lower()
                if e == ".dat":
                    n_dat += 1
                elif e == ".pdf":
                    n_pdf += 1
                else:
                    n_otros += 1
        m = RE_ANIO.findall(s)
        info_sub.append({
            "nombre": s if not RE_NIF_TXT.search(s) else "(oculta: contiene algo con forma de NIF)",
            "tipo": "REGISTRO" if RE_REGISTRO.search(s) else "copia",
            "anios_en_el_nombre": sorted(set(m)),
            "n_dat": n_dat, "n_pdf": n_pdf, "n_otros": n_otros,
        })

    # ---------- ejercicio por contenedor, del inventario ya calculado ----------
    ejercicio_de = {}
    if os.path.exists(INVENTARIO):
        with open(INVENTARIO, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                if r.get("ejercicio"):
                    try:
                        ejercicio_de[r["ruta"]] = int(r["ejercicio"])
                    except ValueError:
                        pass
        print(f"Ejercicios cargados del inventario: {len(ejercicio_de)}")
    else:
        print("AVISO: no encuentro inventario_LOCAL.csv. Sin ejercicio no se")
        print("       puede distinguir fusion de deriva. Ejecuta antes")
        print("       fase0_inventario.py.")

    # ---------- FALLO 1: huellas con umbral 1 ----------
    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores. Extrayendo huellas con umbral {MIN_NIFS}...")

    rutas, huellas = [], []
    sin_nada = 0
    errores = Counter()
    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                interno = None
                for i in z.infolist():
                    if not i.is_dir() and os.path.basename(i.filename).lower() == "subcta.dbf":
                        interno = i.filename
                        break
                if interno is None:
                    continue
                with z.open(interno) as f:
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
            if len(s) < MIN_NIFS:
                sin_nada += 1
                continue
            rutas.append(ruta)
            huellas.append(frozenset(s))
        except Exception as e:
            errores[type(e).__name__] += 1

    n = len(rutas)
    print(f"Huellas utilizables: {n}  (sin ningun NIF: {sin_nada})")
    print(f"Comparando {n*(n-1)//2:,} pares...")

    uf = UnionFind(n)
    pares_altos = []
    for i in range(n):
        hi = huellas[i]
        for j in range(i + 1, n):
            hj = huellas[j]
            inter = len(hi & hj)
            if not inter:
                continue
            sim = inter / len(hi | hj)
            if sim >= UMBRAL:
                uf.union(i, j)
                pares_altos.append((i, j, sim))

    raices = [uf.find(k) for k in range(n)]
    por_grupo = defaultdict(list)
    for k, r in enumerate(raices):
        por_grupo[r].append(k)

    # ---------- FALLO 2: fusion vs deriva ----------
    diag = []
    for r, miembros in por_grupo.items():
        conflictos_mismo_anio = 0
        bajos_otro_anio = 0
        anios = Counter()
        peor = 1.0
        for k in miembros:
            e = ejercicio_de.get(rutas[k])
            if e:
                anios[e] += 1
        for a in range(len(miembros)):
            i = miembros[a]
            for b in range(a + 1, len(miembros)):
                j = miembros[b]
                u = len(huellas[i] | huellas[j])
                sim = len(huellas[i] & huellas[j]) / u if u else 0.0
                peor = min(peor, sim)
                if sim < UMBRAL_CONFLICTO:
                    ei, ej = ejercicio_de.get(rutas[i]), ejercicio_de.get(rutas[j])
                    if ei and ej and ei == ej:
                        conflictos_mismo_anio += 1
                    else:
                        bajos_otro_anio += 1
        diag.append({
            "grupo": r, "copias": len(miembros),
            "sim_min": round(peor, 3),
            "CONFLICTOS_MISMO_EJERCICIO": conflictos_mismo_anio,
            "bajos_entre_ejercicios_distintos": bajos_otro_anio,
            "ejercicios": len(anios),
            "copias_por_ejercicio_max": max(anios.values()) if anios else 0,
        })
    diag.sort(key=lambda d: -d["CONFLICTOS_MISMO_EJERCICIO"])

    fusionados = [d for d in diag if d["CONFLICTOS_MISMO_EJERCICIO"] > 0]
    solo_deriva = [d for d in diag
                   if d["CONFLICTOS_MISMO_EJERCICIO"] == 0 and d["bajos_entre_ejercicios_distintos"] > 0]

    idx = {r: i for i, r in enumerate(sorted(por_grupo))}
    salida = {
        "version": "reagrupa_v1",
        "umbral_nif_antes": 5, "umbral_nif_ahora": MIN_NIFS,
        "umbral_similitud": UMBRAL,
        "huellas_utilizables": n,
        "contenedores_sin_ningun_nif": sin_nada,
        "GRUPOS_ANTES": 35,
        "GRUPOS_AHORA": len(por_grupo),
        "grupos_con_fusion_confirmada": len(fusionados),
        "grupos_con_solo_deriva_temporal": len(solo_deriva),
        "diagnostico_por_grupo": diag,
        "subcarpetas": info_sub,
        "resumen_subcarpetas": {
            "total": len(info_sub),
            "de_copia": sum(1 for s in info_sub if s["tipo"] == "copia"),
            "de_registro": sum(1 for s in info_sub if s["tipo"] == "REGISTRO"),
            "pdf_totales": sum(s["n_pdf"] for s in info_sub),
        },
        "errores": dict(errores),
        "nota": "Solo recuentos y nombres de carpeta. Ningun NIF ni cliente.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({"AVISO": "Lleva rutas. No compartir.",
                   "contenedor_a_grupo": {rutas[k]: idx[raices[k]] for k in range(n)}},
                  f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    print("")
    print("=" * 76)
    print("  1) EFECTO DE BAJAR EL UMBRAL DE 5 NIF A 1")
    print("=" * 76)
    print(f"   huellas utilizables : 1.181  ->  {n}")
    print(f"   GRUPOS DETECTADOS   :    35  ->  {len(por_grupo)}")
    print("")
    print("=" * 76)
    print("  2) .FUSION O DERIVA TEMPORAL?")
    print("=" * 76)
    print(f"   {'grupo':>6}{'copias':>8}{'sim min':>9}{'MISMO ANO':>11}{'otros anos':>12}{'ejerc':>7}")
    print("   " + "-" * 53)
    for d in diag[:16]:
        marca = "  <== FUSION" if d["CONFLICTOS_MISMO_EJERCICIO"] > 0 else ""
        print(f"   {idx[d['grupo']]:>6}{d['copias']:>8}{d['sim_min']:>9.3f}"
              f"{d['CONFLICTOS_MISMO_EJERCICIO']:>11}"
              f"{d['bajos_entre_ejercicios_distintos']:>12}{d['ejercicios']:>7}{marca}")
    print("")
    print(f"   Grupos con FUSION confirmada (dos copias del mismo ano que no")
    print(f"   se parecen)            : {len(fusionados)}")
    print(f"   Grupos con solo deriva temporal (legitimos) : {len(solo_deriva)}")
    print("")
    print("=" * 76)
    print("  3) LAS SUBCARPETAS")
    print("=" * 76)
    rs = salida["resumen_subcarpetas"]
    print(f"   {rs['total']} subcarpetas: {rs['de_copia']} de copia, "
          f"{rs['de_registro']} de Registro. {rs['pdf_totales']} PDF en total.")
    print("")
    print(f"   {'tipo':<9}{'dat':>6}{'pdf':>6}  nombre")
    print("   " + "-" * 70)
    for s in sorted(info_sub, key=lambda x: (x["tipo"] != "REGISTRO", x["nombre"])):
        print(f"   {s['tipo']:<9}{s['n_dat']:>6}{s['n_pdf']:>6}  {s['nombre'][:56]}")
    if errores:
        print(f"\n   Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    print(f"Escrito: {SALIDA_LOCAL}   <- lleva rutas, NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
