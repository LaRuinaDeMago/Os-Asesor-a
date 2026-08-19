#!/usr/bin/env python3
"""
fase0_huella_cliente.py — Agrupar contenedores por cliente SIN saber quien es.

EL PROBLEMA
-----------
Una copia de ContaPlus no dice de que empresa es: el nombre y el NIF viven en
el registro global de la instalacion, no en la copia. Medido y descartado:
nombre de subcarpeta (van por fecha), codigo de empresa (varia por ano),
datempre.dbf (vacio), DATOS.ASC (0 bytes), LegalC.dbf (catalogo fijo de 15
libros), M390A.dbf (plantilla en blanco), TelDat/Datnic (vacias).

LA IDEA
-------
El conjunto de NIF de contrapartes de SubCta.dbf es una HUELLA DACTILAR de la
empresa. Dos copias del mismo cliente comparten casi todos sus proveedores;
dos clientes distintos comparten pocos. Agrupando por similitud (Jaccard), los
contenedores se separan solos en clientes — y nunca hace falta saber quien es
ninguno.

LA PRUEBA DE QUE FUNCIONA, Y ES LO IMPORTANTE
---------------------------------------------
No basta con que salga un numero de grupos: hay que demostrar que la
separacion es REAL y no un artefacto del umbral elegido.

  - Si el nº de grupos se mantiene ESTABLE en un rango ancho de umbrales, la
    estructura existe de verdad.
  - Si cambia sin parar segun el umbral, NO hay agrupacion natural y esta via
    no sirve. El script lo dira, no lo maquillara.

Ademas se publica el histograma de similitudes. Dos modas separadas (alta =
misma empresa, baja = distintas) es la firma de una separacion limpia. Una
sola moda difusa significa que no.

RIESGO CONOCIDO QUE ESTO MIDE: el titular copia cuadros de cuentas entre
clientes de actividad parecida. Si al copiar se arrastran proveedores con su
NIF, dos clientes podrian parecerse demasiado. Por eso la prueba de estabilidad
es obligatoria antes de fiarse del resultado.

REGLA DURA
----------
Lee NIF reales y es incapaz de emitirlos: se hashean en memoria y solo se
publican recuentos. El fichero _LOCAL lleva la correspondencia contenedor ->
grupo para que la revise el titular; nunca se versiona ni lo lee Claude.
Errores agrupados por TIPO de excepcion, nunca por mensaje.

Uso:
    python fase0_huella_cliente.py "RUTA"
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
SALIDA = os.path.join(BASE, "fase0_huella.json")
SALIDA_LOCAL = os.path.join(BASE, "fase0_huella_LOCAL.json")

TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000
MIN_NIFS = 5           # por debajo de esto la huella no es fiable
UMBRALES = [0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]

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
        campos.append({"nombre": b[0:11].split(b"\x00")[0].decode("ascii", "replace"),
                       "tipo": chr(b[11]), "ini": pos, "long": b[16]})
        pos += b[16]
        off += 32
    return len_reg, campos


def forma_nif(v):
    return bool(RE_DNI.match(v) or RE_NIE.match(v) or RE_CIF.match(v))


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

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()

    print(f"{len(dats)} contenedores. Extrayendo la huella de cada uno...")
    print("(los NIF se hashean en memoria; solo se publican recuentos)")

    rutas, huellas, subcarp = [], [], []
    sin_subcta = 0
    huella_pobre = 0
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
                    c = next((x for x in campos if x["nombre"] == "NIF"), None)
                    if c is None:
                        sin_subcta += 1
                        continue
                    s = set()
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
                    huella_pobre += 1
                    continue
                rel = os.path.relpath(ruta, raiz)
                rutas.append(ruta)
                huellas.append(frozenset(s))
                subcarp.append(rel.split(os.sep)[0] if os.sep in rel else "(raiz)")
        except Exception as e:
            errores[type(e).__name__] += 1

    n = len(huellas)
    print(f"Huellas utilizables: {n}   (sin SubCta: {sin_subcta}, "
          f"con menos de {MIN_NIFS} NIF: {huella_pobre})")
    if n < 2:
        print("No hay suficientes huellas para agrupar.")
        return 1

    print(f"Comparando {n*(n-1)//2:,} pares...")

    # ---- similitudes por pares + histograma ----
    hist = Counter()
    pares = []          # (similitud, i, j) solo por encima del umbral minimo
    umbral_min = min(UMBRALES)
    for i in range(n):
        hi = huellas[i]
        for j in range(i + 1, n):
            hj = huellas[j]
            inter = len(hi & hj)
            if inter == 0:
                hist[0] += 1
                continue
            sim = inter / len(hi | hj)
            hist[int(sim * 10)] += 1
            if sim >= umbral_min:
                pares.append((sim, i, j))

    # ---- agrupar a cada umbral: .es estable la estructura? ----
    estabilidad = []
    grupos_por_umbral = {}
    for u in UMBRALES:
        uf = UnionFind(n)
        for sim, i, j in pares:
            if sim >= u:
                uf.union(i, j)
        raices = [uf.find(k) for k in range(n)]
        tam = Counter(raices)
        estabilidad.append({
            "umbral": u,
            "n_grupos": len(tam),
            "grupo_mayor": max(tam.values()),
            "grupos_de_uno": sum(1 for v in tam.values() if v == 1),
        })
        grupos_por_umbral[u] = raices

    # Umbral de referencia: el del tramo mas estable (menor variacion relativa)
    mejor = None
    for k in range(1, len(estabilidad) - 1):
        a, b, c = estabilidad[k-1], estabilidad[k], estabilidad[k+1]
        var = abs(a["n_grupos"] - b["n_grupos"]) + abs(b["n_grupos"] - c["n_grupos"])
        if mejor is None or var < mejor[0]:
            mejor = (var, b["umbral"])
    u_ref = mejor[1] if mejor else 0.60
    raices = grupos_por_umbral[u_ref]

    # ---- calidad de los grupos al umbral de referencia ----
    por_grupo = defaultdict(list)
    for k, r in enumerate(raices):
        por_grupo[r].append(k)
    tam = Counter(len(v) for v in por_grupo.values())
    subcarp_por_grupo = [len({subcarp[k] for k in miembros})
                         for miembros in por_grupo.values()]

    salida = {
        "version": "huella_v1",
        "contenedores_totales": len(dats),
        "huellas_utilizables": n,
        "sin_subcta_o_sin_campo_nif": sin_subcta,
        "huella_demasiado_pobre": huella_pobre,
        "histograma_similitud": {f"{k/10:.1f}-{(k+1)/10:.1f}": v
                                 for k, v in sorted(hist.items())},
        "estabilidad_por_umbral": estabilidad,
        "umbral_de_referencia": u_ref,
        "n_grupos_en_el_umbral_de_referencia": len(por_grupo),
        "tam_de_grupo": {str(k): v for k, v in sorted(tam.items())},
        "grupos_que_abarcan_varias_subcarpetas": sum(1 for x in subcarp_por_grupo if x > 1),
        "subcarpetas_por_grupo_max": max(subcarp_por_grupo) if subcarp_por_grupo else 0,
        "errores": dict(errores),
        "nota": "Solo recuentos. Ningun NIF, ningun hash, ningun nombre.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    idx = {r: i for i, r in enumerate(sorted(por_grupo))}
    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({
            "AVISO": "Lleva rutas reales. Nunca compartir ni versionar.",
            "umbral": u_ref,
            "contenedor_a_grupo": {rutas[k]: idx[raices[k]] for k in range(n)},
        }, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    print("")
    print("=" * 70)
    print("  HISTOGRAMA DE SIMILITUD ENTRE PARES")
    print("  (dos modas separadas = separacion limpia; una sola = no sirve)")
    print("=" * 70)
    total = sum(hist.values())
    for k in sorted(hist):
        v = hist[k]
        barra = "#" * int(v / total * 200) if total else ""
        print(f"  {k/10:.1f}-{(k+1)/10:.1f}  {v:>12,}  {barra}")
    print("")
    print("=" * 70)
    print("  ESTABILIDAD — .existe la estructura o la fabrica el umbral?")
    print("=" * 70)
    print(f"  {'umbral':>8}{'grupos':>9}{'mayor':>8}{'sueltos':>9}")
    print("  " + "-" * 34)
    for e in estabilidad:
        print(f"  {e['umbral']:>8.2f}{e['n_grupos']:>9}{e['grupo_mayor']:>8}{e['grupos_de_uno']:>9}")
    print("")
    print(f"  Umbral de referencia (tramo mas estable): {u_ref}")
    print(f"  GRUPOS DETECTADOS: {len(por_grupo)}")
    print(f"  Grupos presentes en mas de una subcarpeta: "
          f"{salida['grupos_que_abarcan_varias_subcarpetas']} "
          f"(max {salida['subcarpetas_por_grupo_max']} subcarpetas)")
    print("")
    print("  Tamano de grupo (nº de copias por grupo):")
    for k, v in sorted(tam.items()):
        print(f"     {k:>4} copias: {v:>5} grupos")
    if errores:
        print(f"\n  Errores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    print(f"Escrito: {SALIDA_LOCAL}   <- lleva rutas, NO compartir")
    print("")
    print("COMO LEERLO:")
    print("  1. Mira ESTABILIDAD. Si el nº de grupos apenas cambia entre 0,4 y")
    print("     0,8, la estructura es real. Si cambia en cada fila, NO SIRVE.")
    print("  2. El nº de grupos deberia parecerse al nº de clientes distintos")
    print("     que han pasado por la asesoria en diez anos.")
    print("  3. Un grupo debe abarcar VARIAS subcarpetas: la misma empresa")
    print("     copiada en fechas distintas. Si cada grupo vive en una sola,")
    print("     estamos agrupando por fecha y no por cliente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
