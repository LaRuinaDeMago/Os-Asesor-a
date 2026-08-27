#!/usr/bin/env python3
"""diag_rescalado_multitipo.py — ¿el reescalado de los asientos multi-tipo
introduce un sesgo sistematico?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
Medido el 27-08-2026 sobre 303_LOCAL.json ya con la base derivada del
asiento: la coherencia (base*tipo=cuota) EMPEORA con el tamaño de la celda
(72,9% en celdas de 1-2 apuntes -> 43,9% en celdas de 200+) y el 57,7% del
VOLUMEN de apuntes vive en celdas incoherentes. Eso es la firma de un SESGO
SISTEMATICO, no de ruido: el ruido aleatorio se cancela al agregar mas datos;
un sesgo consistente se acumula.

LA SOSPECHA: `derivar_bases_por_tipo()` en reconstruir_303.py, para un
asiento con VARIOS tipos de IVA, calcula la base de cada tipo a partir de
cuota/tipo (que por construccion SI cuadra: cuota/(tipo/100)*tipo/100=cuota)
y LUEGO la reescala para que la SUMA cuadre con el gasto/ingreso contable
total del asiento. Ese reescalado rompe a proposito la relacion base*tipo=
cuota para CADA TIPO POR SEPARADO, y si el gasto contable diverge de forma
sistematica del total implicito por las cuotas (por ejemplo, si la cuenta de
gasto incluye conceptos que no llevan IVA, o de otro tipo, mezclados en la
misma linea), el factor de reescalado seria consistentemente mayor o menor
que 1 -- y ESO si se acumula al agregar muchos asientos, en vez de
cancelarse.

QUE MIDE ESTE SCRIPT, LEYENDO EL CORPUS REAL DIRECTAMENTE
------------------------------------------------------------
Para cada asiento con 2 o mas tipos de IVA DISTINTOS en el mismo lado:
  1. La distribucion del FACTOR de reescalado (contrapartida contable /
     suma de bases derivadas por cuota-tipo). Si se concentra lejos de 1,
     confirma el sesgo.
  2. Que fraccion del VOLUMEN TOTAL de apuntes viene de asientos multi-tipo
     frente a mono-tipo -- para saber si esto explica lo suficiente como
     para importar.

Nunca se imprime un importe, un NIF ni una clave de cliente: solo la forma
de la distribucion (en bins) y recuentos.

REGLA DE DATOS: lo ejecuta el titular.

Uso:
    python diag_rescalado_multitipo.py "RUTA_DEL_CORPUS"
    python diag_rescalado_multitipo.py "RUTA_DEL_CORPUS" --limite 200
"""
import argparse
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import MAX_REGISTROS_POR_FICHERO, PREF_GASTO, cuenta, num, parse_cabecera, txt
from reconstruir_303 import PREF_INGRESO, PREF_REPERCUTIDO, PREF_SOPORTADO

#: Bins del factor de reescalado. Centrados en 1.0 (sin sesgo).
BINS_FACTOR = ((0, 0.5), (0.5, 0.8), (0.8, 0.95), (0.95, 1.05),
               (1.05, 1.2), (1.2, 1.5), (1.5, 2.0), (2.0, 10**6))


def bin_de(factor):
    for lo, hi in BINS_FACTOR:
        if lo <= factor < hi:
            return f"{lo}-{hi}" if hi < 10**6 else f"{lo}+"
    return "?"


def procesar_contenedor(ruta, stats):
    with zipfile.ZipFile(ruta) as z:
        nombre = next((i.filename for i in z.infolist()
                       if not i.is_dir()
                       and os.path.basename(i.filename).lower() == "diario.dbf"), None)
        if nombre is None:
            stats["incidencias"]["contenedor sin Diario.dbf"] += 1
            return
        with z.open(nombre) as fh:
            len_reg, campos = parse_cabecera(fh)
            idx = {c["nombre"]: c for c in campos}
            cS, cED, cEH = idx.get("SUBCTA"), idx.get("EURODEBE"), idx.get("EUROHABER")
            cIVA, cBASE, cA = idx.get("IVA"), idx.get("BASEIMPO"), idx.get("ASIEN")
            if not (cS and cA):
                stats["incidencias"]["Diario.dbf sin SUBCTA o ASIEN"] += 1
                return
            lineas_por_asiento = defaultdict(list)
            leidos = 0
            while True:
                rec = fh.read(len_reg)
                if len(rec) < len_reg or rec[:1] == b"\x1a":
                    break
                leidos += 1
                if leidos > MAX_REGISTROS_POR_FICHERO:
                    raise ValueError("demasiados registros")
                if rec[:1] == b"*":
                    continue
                pref = cuenta(rec, cS)
                h = hashlib.blake2b(rec, digest_size=8).digest()
                lineas_por_asiento[int(num(rec, cA))].append((
                    pref, num(rec, cED), num(rec, cEH),
                    num(rec, cIVA) if cIVA else 0.0,
                    num(rec, cBASE) if cBASE else 0.0, h))
                del rec

            for _asien, lineas in lineas_por_asiento.items():
                huella = hashlib.blake2b(
                    b"".join(sorted(l[5] for l in lineas)), digest_size=16).digest()
                if huella in stats["vistos"]:
                    continue
                stats["vistos"].add(huella)

                gasto_total = round(sum(l[1] for l in lineas if l[0].startswith(PREF_GASTO)), 2)
                ingreso_total = round(sum(l[2] for l in lineas if l[0].startswith(PREF_INGRESO)), 2)

                for pref_iva, contrapartida, cuota_fn in (
                        (PREF_SOPORTADO, gasto_total, lambda l: l[1] - l[2]),
                        (PREF_REPERCUTIDO, ingreso_total, lambda l: l[2] - l[1])):
                    ivas = [(l[3], cuota_fn(l), l[4]) for l in lineas if l[0] == pref_iva]
                    if not ivas:
                        continue
                    n_apuntes = len(ivas)
                    tipos_distintos = {int(t) for t, _c, _b in ivas}
                    if len(tipos_distintos) < 2:
                        stats["apuntes_monotipo"] += n_apuntes
                        continue
                    stats["apuntes_multitipo"] += n_apuntes
                    derivado = {}
                    for tipo, cuota, base_directa in ivas:
                        base = base_directa
                        if base <= 0 and tipo > 0:
                            base = round(cuota / (tipo / 100.0), 2)
                        derivado[int(tipo)] = derivado.get(int(tipo), 0.0) + base
                    suma_derivada = sum(derivado.values())
                    if suma_derivada > 0 and contrapartida > 0:
                        factor = contrapartida / suma_derivada
                        stats["factores"][bin_de(factor)] += 1
                        stats["factor_suma"] += factor
                        stats["factor_n"] += 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta")
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: esa carpeta no existe.", file=sys.stderr)
        sys.exit(2)
    dats = sorted(os.path.join(dp, n) for dp, _, fns in os.walk(raiz)
                  for n in fns if n.lower().endswith(".dat"))
    if not dats:
        print("ERROR: no hay ningun .DAT ahi dentro.", file=sys.stderr)
        sys.exit(2)
    if args.limite:
        dats = dats[:args.limite]
    print(f"{len(dats):,} contenedores a revisar.")

    stats = {"vistos": set(), "incidencias": Counter(), "factores": Counter(),
              "apuntes_monotipo": 0, "apuntes_multitipo": 0,
              "factor_suma": 0.0, "factor_n": 0}
    paso = max(1, len(dats) // 20)
    for i, ruta in enumerate(dats, start=1):
        try:
            if zipfile.is_zipfile(ruta):
                procesar_contenedor(ruta, stats)
            else:
                stats["incidencias"]["no es ZIP"] += 1
        except Exception as e:
            stats["incidencias"]["contenedor:" + type(e).__name__] += 1
        if i % paso == 0 or i == len(dats):
            print(f"    {i * 100 // len(dats):>3}%  ({i:,}/{len(dats):,})")

    print()
    print("=" * 70)
    print("FACTOR DE REESCALADO EN ASIENTOS MULTI-TIPO (1.0 = sin sesgo)")
    print("=" * 70)
    for lo, hi in BINS_FACTOR:
        b = f"{lo}-{hi}" if hi < 10**6 else f"{lo}+"
        n = stats["factores"].get(b, 0)
        print(f"    {b:<12} {'#' * min(50, n):<50} {n:,}")
    if stats["factor_n"]:
        media = stats["factor_suma"] / stats["factor_n"]
        print(f"\n  factor medio: {media:.3f}  (sobre {stats['factor_n']:,} asientos multi-tipo)")

    total = stats["apuntes_monotipo"] + stats["apuntes_multitipo"]
    pct_multi = stats["apuntes_multitipo"] * 100.0 / total if total else 0
    print()
    print("PESO DE LOS ASIENTOS MULTI-TIPO EN EL VOLUMEN TOTAL:")
    print(f"    apuntes en asientos de UN tipo   : {stats['apuntes_monotipo']:>8,}")
    print(f"    apuntes en asientos MULTI-tipo   : {stats['apuntes_multitipo']:>8,}  ({pct_multi:.1f}%)")
    if stats["incidencias"]:
        print()
        print("INCIDENCIAS:", dict(stats["incidencias"]))
    print()
    print("COMO SE LEE:")
    print("  - Si el factor se concentra lejos de 1.0 (por ejemplo, casi todo por")
    print("    encima de 1.2 o por debajo de 0.8), el reescalado esta introduciendo")
    print("    un sesgo sistematico: confirma la hipotesis.")
    print("  - Si ademas el peso de multi-tipo en el volumen total es alto, ese")
    print("    sesgo basta para explicar por que las celdas grandes salen peor.")
    print("  - Si el factor esta centrado en 1.0 (la mayoria en 0.95-1.05), el")
    print("    reescalado NO es la causa y hay que seguir buscando por otro lado.")


if __name__ == "__main__":
    main()
