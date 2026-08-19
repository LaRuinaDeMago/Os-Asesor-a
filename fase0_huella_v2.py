#!/usr/bin/env python3
"""
fase0_huella_v2.py — Huella por NOMBRE de contraparte, no solo por NIF.

POR QUE
-------
La v1 identificaba a cada empresa por el conjunto de NIF de sus contrapartes.
Medido despues: el campo NIF de SubCta.dbf solo esta relleno en 898 de 1.287
contenedores (70%), mientras que TITULO lo esta en los 1.287 (100%). Los 38
contenedores que se quedaron sin huella eran justo los que no tenian ningun
NIF — clientes pequenos donde no se rellena el NIF del proveedor.

Aqui la huella se construye con NOMBRE + NIF: el nombre normalizado de cada
contraparte (mayusculas, sin acentos, sin puntuacion) mas el NIF cuando existe.
Cobertura del 100% de los contenedores con SubCta.

LO QUE NO CAMBIA: los nombres se hashean en memoria y NUNCA salen. Solo se
publican recuentos. El agrupamiento es exacto aunque Claude no vea ni un
nombre; nunca ha hecho falta verlos.

Mantiene los tres controles de la v1, que son los que dicen si el resultado
vale:
  1. histograma de similitud (dos modas = separacion limpia)
  2. estabilidad del nº de grupos frente al umbral
  3. conflictos del MISMO ejercicio (fusion real) vs de anos distintos (deriva)

Uso:
    python fase0_huella_v2.py "RUTA"
"""

import os
import re
import sys
import csv
import json
import zipfile
import struct
import hashlib
import unicodedata
import argparse
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
INVENTARIO = os.path.join(BASE, "inventario_LOCAL.csv")
SALIDA = os.path.join(BASE, "fase0_huella_v2.json")
SALIDA_LOCAL = os.path.join(BASE, "fase0_huella_v2_LOCAL.json")

TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000
MIN_ELEM = 1
UMBRALES = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
UMBRAL_REF = 0.40
UMBRAL_CONFLICTO = 0.20

# Cuentas de tercero: proveedores, acreedores, clientes, deudores.
GRUPOS_TERCERO = (b"400", b"401", b"410", b"411", b"430", b"431", b"440", b"460")


def normaliza(b):
    """Nombre -> forma canonica. Nunca se devuelve fuera: solo se hashea."""
    s = b.decode("cp1252", "replace").upper().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\b(S\.?L\.?U?|S\.?A\.?|C\.?B\.?|S\.?C\.?|SLU|SLL)\b", "", s)
    s = re.sub(r"[^A-Z0-9]+", "", s)
    return s


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

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores. Huella por NOMBRE + NIF de contraparte...")
    print("(los nombres se hashean en memoria; nunca salen de esta maquina)")

    rutas, huellas, tam = [], [], []
    sin_subcta = sin_nada = 0
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
                    sin_subcta += 1
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
                        # Solo terceros: las cuentas de estructura del PGC son
                        # iguales en todas las empresas y no distinguen nada.
                        if not cod[:3] in GRUPOS_TERCERO:
                            del rec
                            continue
                        if cT:
                            t = rec[cT["ini"]:cT["ini"] + cT["long"]].strip(b" \x00")
                            if t:
                                c = normaliza(t)
                                if len(c) >= 4:
                                    s.add(hashlib.blake2b(c.encode(), digest_size=8).digest())
                        if cN:
                            v = rec[cN["ini"]:cN["ini"] + cN["long"]].strip(b" \x00")
                            if v:
                                s.add(hashlib.blake2b(v, digest_size=8).digest())
                        del rec
            if len(s) < MIN_ELEM:
                sin_nada += 1
                continue
            rutas.append(ruta)
            huellas.append(frozenset(s))
            tam.append(len(s))
        except Exception as e:
            errores[type(e).__name__] += 1

    n = len(rutas)
    print(f"Huellas utilizables: {n}  (sin SubCta: {sin_subcta}, vacias: {sin_nada})")
    print(f"Elementos por huella: min {min(tam) if tam else 0}  "
          f"media {round(sum(tam)/len(tam)) if tam else 0}  max {max(tam) if tam else 0}")
    print(f"Comparando {n*(n-1)//2:,} pares...")

    hist = Counter()
    pares = []
    for i in range(n):
        hi = huellas[i]
        for j in range(i + 1, n):
            hj = huellas[j]
            inter = len(hi & hj)
            if not inter:
                hist[0] += 1
                continue
            sim = inter / len(hi | hj)
            hist[min(int(sim * 10), 9)] += 1
            if sim >= UMBRALES[0]:
                pares.append((sim, i, j))

    estabilidad = []
    grupos_u = {}
    for u in UMBRALES:
        uf = UnionFind(n)
        for sim, i, j in pares:
            if sim >= u:
                uf.union(i, j)
        raices = [uf.find(k) for k in range(n)]
        tamg = Counter(raices)
        estabilidad.append({"umbral": u, "n_grupos": len(tamg),
                            "grupo_mayor": max(tamg.values()),
                            "sueltos": sum(1 for v in tamg.values() if v == 1)})
        grupos_u[u] = raices

    raices = grupos_u[UMBRAL_REF]
    por_grupo = defaultdict(list)
    for k, r in enumerate(raices):
        por_grupo[r].append(k)

    diag = []
    for r, miembros in por_grupo.items():
        confl = otros = 0
        peor = 1.0
        for a in range(len(miembros)):
            i = miembros[a]
            for b in range(a + 1, len(miembros)):
                j = miembros[b]
                u = len(huellas[i] | huellas[j])
                sim = len(huellas[i] & huellas[j]) / u if u else 0.0
                peor = min(peor, sim)
                if sim < UMBRAL_CONFLICTO:
                    ei = ejercicio_de.get(rutas[i])
                    ej = ejercicio_de.get(rutas[j])
                    if ei and ej and ei == ej:
                        confl += 1
                    else:
                        otros += 1
        diag.append({"grupo": r, "copias": len(miembros), "sim_min": round(peor, 3),
                     "CONFLICTOS_MISMO_EJERCICIO": confl,
                     "bajos_entre_anos": otros})
    diag.sort(key=lambda d: -d["CONFLICTOS_MISMO_EJERCICIO"])
    fusion = [d for d in diag if d["CONFLICTOS_MISMO_EJERCICIO"] > 0]

    # clientes activos por ejercicio
    activos = defaultdict(set)
    idx = {r: i for i, r in enumerate(sorted(por_grupo))}
    for k in range(n):
        e = ejercicio_de.get(rutas[k])
        if e:
            activos[e].add(idx[raices[k]])

    salida = {
        "version": "huella_v2_nombre",
        "huellas_utilizables": n,
        "sin_subcta": sin_subcta, "huellas_vacias": sin_nada,
        "elementos_por_huella": {"min": min(tam) if tam else 0,
                                 "media": round(sum(tam) / len(tam), 1) if tam else 0,
                                 "max": max(tam) if tam else 0},
        "histograma_similitud": {f"{k/10:.1f}": v for k, v in sorted(hist.items())},
        "estabilidad_por_umbral": estabilidad,
        "GRUPOS": len(por_grupo),
        "grupos_con_fusion": len(fusion),
        "clientes_activos_por_ejercicio": {str(k): len(v) for k, v in sorted(activos.items())},
        "diagnostico_por_grupo": diag[:20],
        "errores": dict(errores),
        "nota": "Solo recuentos. Ningun nombre, ningun NIF, ningun hash.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)
    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({"AVISO": "Lleva rutas. No compartir.",
                   "umbral": UMBRAL_REF,
                   "contenedor_a_grupo": {rutas[k]: idx[raices[k]] for k in range(n)}},
                  f, indent=2, ensure_ascii=False)

    print("")
    print("=" * 68)
    print("  HISTOGRAMA DE SIMILITUD")
    print("=" * 68)
    total = sum(hist.values())
    for k in sorted(hist):
        v = hist[k]
        print(f"  {k/10:.1f}-{(k+1)/10:.1f}  {v:>12,}  " + "#" * int(v / total * 160))
    print("")
    print("=" * 68)
    print("  ESTABILIDAD")
    print("=" * 68)
    print(f"  {'umbral':>8}{'grupos':>9}{'mayor':>8}{'sueltos':>9}")
    for e in estabilidad:
        print(f"  {e['umbral']:>8.2f}{e['n_grupos']:>9}{e['grupo_mayor']:>8}{e['sueltos']:>9}")
    print("")
    print("=" * 68)
    print(f"  GRUPOS (umbral {UMBRAL_REF}): {len(por_grupo)}      "
          f"con fusion real: {len(fusion)}")
    print("=" * 68)
    print("")
    print("  CLIENTES ACTIVOS POR EJERCICIO:")
    for e, v in sorted(activos.items()):
        print(f"     {e}: {len(v):>3} clientes  " + "#" * len(v))
    if errores:
        print(f"\n  Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    print(f"Escrito: {SALIDA_LOCAL}   <- lleva rutas, NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
