#!/usr/bin/env python3
"""diag_aritmetica_tipo.py — ¿el septimo arreglo ha vuelto a mover el problema?

HIPOTESIS A COMPROBAR (25-08-2026, revision propia de RUN 7)
--------------------------------------------------------------
El septimo arreglo reescala por_tipo (la BASE de cada tramo) para que su suma
cuadre exacta con base_total. Pero tramos_iva construye la CUOTA de cada tramo
como `base * tipo/100` — es decir, la cuota se deriva de la base YA reescalada,
no del dato de cuota original de cada linea de IVA.

guard_aritmetica_tramos (guards["aritmetica_base_tipo"]) compara
sum(tramos cuota) contra iva_total — que es la suma CRUDA de cuota de las
lineas de IVA, sin tocar por ningun arreglo de hoy. Si el reescalado del
arreglo 7 desplaza la cuota derivada lejos de la cuota real, este guard
puede haber empeorado exactamente igual que le paso a suma_tramos con el
arreglo 6 — el mismo patron, un nivel mas abajo.

Este script NO reimplementa nada: importa reconstruir_compra y
guard_aritmetica_tramos tal cual estan hoy en el repo, reproduce la MISMA
deduplicacion de dos capas que usa retro_semaforo.py, y mide el FALLO de
aritmetica_base_tipo desglosado por NUMERO DE TRAMOS del asiento. Si la
hipotesis es correcta, el FALLO tiene que concentrarse en 2+/3+/4+ tramos
y ser bajo en 1 tramo — igual que le paso a cuadre_total con el arreglo 6.

Solo cuenta y desglosa por numero de tramos. Nunca imprime NIF, importes,
ni ningun valor de una factura concreta.

Uso:
    python diag_aritmetica_tipo.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta, numero_documento, reconstruir_compra
import motor_veredicto as mv
import contrato_datos


def main():
    raiz = os.path.abspath(sys.argv[1])
    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores.")

    vistos_contenido = set()
    vistos_clave_documental = set()
    n_compras = 0

    por_ntramos = Counter()             # cuantos asientos tienen N tramos
    fallo_por_ntramos = Counter()       # de esos, cuantos dan FALLO en aritmetica_base_tipo
    ok_por_ntramos = Counter()
    nocomp_por_ntramos = Counter()

    # Para cuantificar el desplazamiento, no solo contarlo: diferencia entre
    # calc (suma de cuota de tramos, ya reescalada via base) e iva_total real.
    suma_abs_desvio_por_ntramos = Counter()

    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                nombre = next((i.filename for i in z.infolist()
                               if not i.is_dir()
                               and os.path.basename(i.filename).lower() == "diario.dbf"), None)
                if nombre is None:
                    continue
                with z.open(nombre) as fh:
                    len_reg, campos = parse_cabecera(fh)
                    idx = {c["nombre"]: c for c in campos}
                    cA, cS = idx.get("ASIEN"), idx.get("SUBCTA")
                    cED, cEH = idx.get("EURODEBE"), idx.get("EUROHABER")
                    cIVA, cNIF = idx.get("IVA"), idx.get("TERNIF")
                    cREC = idx.get("RECEQUIV")
                    cBASE, cFEC = idx.get("BASEIMPO"), idx.get("FECHA")
                    cNFACTICK = idx.get("NFACTICK")
                    cDOCUMENTO = idx.get("DOCUMENTO")
                    cFACTURA = idx.get("FACTURA")
                    if not (cA and cS):
                        continue

                    grupos = {}
                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        h_linea = hashlib.blake2b(rec, digest_size=8).digest()
                        grupos.setdefault(int(num(rec, cA)), []).append((
                            cuenta(rec, cS), num(rec, cED), num(rec, cEH),
                            num(rec, cIVA), txt(rec, cNIF), num(rec, cBASE),
                            txt(rec, cFEC),
                            numero_documento(rec, cNFACTICK, cDOCUMENTO, cFACTURA),
                            num(rec, cREC),
                            h_linea,
                        ))
                        del rec

                    for _, lineas in sorted(grupos.items()):
                        huella = hashlib.blake2b(
                            b"".join(sorted(l[9] for l in lineas)),
                            digest_size=16).digest()
                        if huella in vistos_contenido:
                            continue
                        vistos_contenido.add(huella)

                        fila = reconstruir_compra(lineas)
                        if fila is None or fila in ("SIN_IVA", "ISP"):
                            continue

                        clave_doc = contrato_datos.canonizar(fila).clave_documental()
                        clave_h = hashlib.blake2b(
                            repr(clave_doc).encode("utf-8"), digest_size=12).digest()
                        if clave_h in vistos_clave_documental:
                            continue
                        vistos_clave_documental.add(clave_h)

                        n_compras += 1
                        tramos = fila.get("tramos_iva") or []
                        n_tramos = len(tramos)
                        por_ntramos[n_tramos] += 1

                        estado, _ = mv.guard_aritmetica_tramos(tramos, fila.get("iva_total"))
                        if estado == "FALLO":
                            fallo_por_ntramos[n_tramos] += 1
                        elif estado == "OK":
                            ok_por_ntramos[n_tramos] += 1
                        else:
                            nocomp_por_ntramos[n_tramos] += 1

                        if tramos and fila.get("iva_total") is not None:
                            calc = round(sum(t['cuota'] for t in tramos), 2)
                            suma_abs_desvio_por_ntramos[n_tramos] += abs(calc - fila["iva_total"])
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 70)
    print(f"  compras evaluadas (deduplicadas, igual que retro_semaforo): {n_compras:,}")
    print("=" * 70)
    print("")
    print("aritmetica_base_tipo (guard_aritmetica_tramos) POR NUMERO DE TRAMOS:")
    print(f"   {'tramos':>7}  {'n':>8}  {'FALLO':>8}  {'%FALLO':>7}  {'OK':>8}  {'NO_COMP':>8}  {'desvio_medio':>13}")
    for n_t in sorted(por_ntramos):
        n = por_ntramos[n_t]
        f = fallo_por_ntramos.get(n_t, 0)
        ok = ok_por_ntramos.get(n_t, 0)
        nc = nocomp_por_ntramos.get(n_t, 0)
        pctf = round(f * 100.0 / n, 2) if n else 0.0
        desvio_medio = round(suma_abs_desvio_por_ntramos.get(n_t, 0.0) / n, 4) if n else 0.0
        print(f"   {n_t:>7}  {n:>8,}  {f:>8,}  {pctf:>6}%  {ok:>8,}  {nc:>8,}  {desvio_medio:>13}")

    total_fallo = sum(fallo_por_ntramos.values())
    print("")
    print(f"  TOTAL FALLO aritmetica_base_tipo: {total_fallo:,} / {n_compras:,} "
          f"({round(total_fallo*100.0/n_compras,2) if n_compras else 0}%)")
    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
