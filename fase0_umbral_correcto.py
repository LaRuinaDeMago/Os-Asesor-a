#!/usr/bin/env python3
"""
fase0_umbral_correcto.py — Elegir el umbral por restriccion, no a ojo.

EL FALLO QUE ARREGLA
--------------------
El test de fusion anterior preguntaba: ".hay parejas del mismo ejercicio con
similitud por debajo de 0,20?". Dio cero y se concluyo que no habia fusiones.
Pero dos clientes de actividad parecida que comparten el 40% de proveedores
—exactamente el caso del que aviso el titular, porque copia cuadros de cuentas
entre clientes similares— tienen similitud 0,40, muy por encima de ese liston.
Se fusionan y el test los da por buenos.

LA RESTRICCION QUE NO ADMITE DISCUSION
--------------------------------------
Dentro de una misma CARPETA DE COPIA, una empresa aparece UNA SOLA VEZ por
ejercicio. Es como funciona una copia de seguridad de ContaPlus: un contenedor
por empresa y ejercicio.

    -> Si un grupo contiene dos contenedores de la MISMA carpeta y el MISMO
       ejercicio, son DOS EMPRESAS DISTINTAS. Por definicion, sin umbrales.

Eso convierte la eleccion del umbral en una medicion: el umbral correcto es el
MAS BAJO que no viole la restriccion ni una sola vez. Un umbral mas bajo fusiona
clientes; uno mas alto parte al mismo cliente en trozos por deriva temporal.

Se prueban umbrales de 0,30 a 0,95 y se reporta, para cada uno, cuantas
violaciones quedan. La respuesta la dan los datos.

REGLA DURA: nombres y NIF hasheados en memoria; solo salen recuentos.

Uso:
    python fase0_umbral_correcto.py "RUTA"
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
SALIDA = os.path.join(BASE, "fase0_umbral.json")
SALIDA_LOCAL = os.path.join(BASE, "fase0_umbral_LOCAL.json")

TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000
UMBRALES = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65,
            0.70, 0.75, 0.80, 0.85, 0.90, 0.95]

RE_DNI = re.compile(rb"^\d{8}[A-Za-z]$")
RE_NIE = re.compile(rb"^[XYZxyz]\d{7}[A-Za-z]$")
RE_CIF = re.compile(rb"^[A-HJ-NP-SUVWa-hj-np-suvw]\d{7}[0-9A-Ja-j]$")
GRUPOS_TERCERO = (b"400", b"401", b"410", b"411", b"430", b"431", b"440", b"460")


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

    ejercicio_de = {}
    if os.path.exists(INVENTARIO):
        with open(INVENTARIO, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                if r.get("ejercicio"):
                    try:
                        ejercicio_de[r["ruta"]] = int(r["ejercicio"])
                    except ValueError:
                        pass
    if not ejercicio_de:
        print("ERROR: hace falta inventario_LOCAL.csv (ejecuta fase0_inventario.py).")
        return 1

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores. Extrayendo huellas (NIF + nombre)...")

    rutas, huellas, clave = [], [], []
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
                    cC = next((c for c in campos if c["nombre"] == "COD"), None)
                    cT = next((c for c in campos if c["nombre"] == "TITULO"), None)
                    cN = next((c for c in campos if c["nombre"] == "NIF"), None)
                    s = set()
                    leidos = 0
                    while leidos < TOPE_REGISTROS:
                        rec = f.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        leidos += 1
                        cod = rec[cC["ini"]:cC["ini"] + cC["long"]].strip(b" \x00") if cC else b""
                        if cod[:3] not in GRUPOS_TERCERO:
                            del rec
                            continue
                        if cN:
                            v = rec[cN["ini"]:cN["ini"] + cN["long"]].strip(b" \x00")
                            if v and forma_nif(v):
                                s.add(hashlib.blake2b(b"N" + v, digest_size=8).digest())
                        if cT:
                            t = rec[cT["ini"]:cT["ini"] + cT["long"]].strip(b" \x00")
                            if len(t) >= 5:
                                s.add(hashlib.blake2b(b"T" + t.upper(), digest_size=8).digest())
                        del rec
            if not s:
                continue
            e = ejercicio_de.get(ruta)
            if not e:
                continue
            rel = os.path.relpath(ruta, raiz)
            carp = rel.split(os.sep)[0] if os.sep in rel else "(raiz)"
            rutas.append(ruta)
            huellas.append(frozenset(s))
            clave.append((carp, e))   # restriccion: unica por empresa
        except Exception as e:
            errores[type(e).__name__] += 1

    n = len(rutas)
    print(f"Huellas con ejercicio conocido: {n}")
    print(f"Comparando {n*(n-1)//2:,} pares...")

    pares = []
    for i in range(n):
        hi = huellas[i]
        for j in range(i + 1, n):
            hj = huellas[j]
            inter = len(hi & hj)
            if not inter:
                continue
            sim = inter / len(hi | hj)
            if sim >= UMBRALES[0]:
                pares.append((sim, i, j))
    pares.sort(reverse=True)

    print("Probando umbrales contra la restriccion...")
    filas = []
    mapas = {}
    for u in UMBRALES:
        uf = UnionFind(n)
        for sim, i, j in pares:
            if sim >= u:
                uf.union(i, j)
        raices = [uf.find(k) for k in range(n)]
        por_grupo = defaultdict(list)
        for k, r in enumerate(raices):
            por_grupo[r].append(k)
        # VIOLACIONES: dos contenedores del mismo grupo, misma carpeta, mismo ejercicio
        viol = 0
        grupos_viol = 0
        for r, miembros in por_grupo.items():
            c = Counter(clave[k] for k in miembros)
            v = sum(x - 1 for x in c.values() if x > 1)
            if v:
                grupos_viol += 1
            viol += v
        filas.append({"umbral": u, "grupos": len(por_grupo),
                      "VIOLACIONES": viol, "grupos_con_violacion": grupos_viol,
                      "grupo_mayor": max(len(v) for v in por_grupo.values())})
        mapas[u] = raices

    limpio = next((f for f in filas if f["VIOLACIONES"] == 0), None)
    u_ok = limpio["umbral"] if limpio else UMBRALES[-1]
    raices = mapas[u_ok]
    por_grupo = defaultdict(list)
    for k, r in enumerate(raices):
        por_grupo[r].append(k)
    idx = {r: i for i, r in enumerate(sorted(por_grupo))}

    activos = defaultdict(set)
    for k in range(n):
        activos[clave[k][1]].add(idx[raices[k]])

    salida = {
        "version": "umbral_v1",
        "huellas": n,
        "tabla_umbrales": filas,
        "UMBRAL_SIN_VIOLACIONES": u_ok,
        "GRUPOS": len(por_grupo),
        "clientes_activos_por_ejercicio": {str(k): len(v) for k, v in sorted(activos.items())},
        "errores": dict(errores),
        "nota": "Solo recuentos. Ningun nombre, NIF ni hash.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({"AVISO": "Lleva rutas. No compartir.", "umbral": u_ok,
                   "contenedor_a_grupo": {rutas[k]: idx[raices[k]] for k in range(n)}},
                  f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 70)
    print("  EL UMBRAL, DECIDIDO POR LA RESTRICCION")
    print("  (violacion = dos contenedores del mismo grupo, misma carpeta")
    print("   y mismo ejercicio -> imposible en una sola empresa)")
    print("=" * 70)
    print(f"  {'umbral':>8}{'grupos':>9}{'mayor':>8}{'VIOLACIONES':>13}{'grupos malos':>14}")
    print("  " + "-" * 52)
    for f_ in filas:
        marca = "   <== LIMPIO" if f_["VIOLACIONES"] == 0 and f_["umbral"] == u_ok else ""
        print(f"  {f_['umbral']:>8.2f}{f_['grupos']:>9}{f_['grupo_mayor']:>8}"
              f"{f_['VIOLACIONES']:>13}{f_['grupos_con_violacion']:>14}{marca}")
    print("")
    print(f"  UMBRAL CORRECTO: {u_ok}     CLIENTES: {len(por_grupo)}")
    print("")
    print("  CLIENTES ACTIVOS POR EJERCICIO:")
    for e, v in sorted(activos.items()):
        print(f"     {e}: {len(v):>3}  " + "#" * len(v))
    if errores:
        print(f"\n  Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    print(f"Escrito: {SALIDA_LOCAL}   <- lleva rutas, NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
