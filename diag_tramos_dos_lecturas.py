#!/usr/bin/env python3
"""diag_tramos_dos_lecturas.py — por que `tramos_iva` dio DIFIERE entre dos
lecturas reales de la misma factura, sin imprimir ni base ni cuota.

PARA QUE SIRVE
---------------
`comparar_dos_lecturas_reales.py` ya dijo que `tramos_iva` DIFIERE entre
`facturas_reales_LOCAL.csv` y `facturas_reales_LOCAL_run2.csv` (17-09-2026,
Paso 2 del primer ensayo real). Ese script, a proposito, no dice EN QUE se
diferencian -- solo el nombre del campo y el estado. Este script existe para
la pregunta siguiente: ¿es un tramo que aparece o desaparece entero, o son
los mismos tramos con un importe que no cuadra exactamente?

El tipo de IVA (21, 10, 4, 5, 0) es una categoria legal cerrada, no un dato
de cliente -- por eso este script SI dice que tipos hay, igual que ya lo
hace cualquier resumen del motor ("guard X = FALLO"). Lo que nunca imprime
es base ni cuota: esos si son importes de la factura real.

Diego: esto lo ejecutas TU, en tu terminal, igual que los demas scripts
sobre ficheros _LOCAL. Lo que imprime es seguro de pegar en el chat.

USO
----
    python diag_tramos_dos_lecturas.py facturas_reales_LOCAL.csv facturas_reales_LOCAL_run2.csv
"""
import argparse
import csv
import sys

import contrato_datos
import comparar_captura_vs_verdad as cmp

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def tramos_de(ruta):
    with open(ruta, encoding="utf-8") as f:
        fila = next(csv.DictReader(f))
    return contrato_datos.parse_estructura(fila.get("tramos_iva"))


def resumen(tramos):
    """(numero de tramos, conjunto de tipos de IVA) -- nunca base ni cuota."""
    if not isinstance(tramos, (list, tuple)):
        return 0, set()
    tipos = set()
    for t in tramos:
        if isinstance(t, dict):
            d = contrato_datos.parse_numero(t.get("tipo"))
            if d.estado in contrato_datos.UTILIZABLES:
                tipos.add(d.valor)
    return len(tramos), tipos


def main():
    parser = argparse.ArgumentParser(
        description="Por que tramos_iva difiere entre dos lecturas reales, sin importes.")
    parser.add_argument("csv1")
    parser.add_argument("csv2")
    args = parser.parse_args()

    t1 = tramos_de(args.csv1)
    t2 = tramos_de(args.csv2)
    n1, tipos1 = resumen(t1)
    n2, tipos2 = resumen(t2)

    print(f"{args.csv1}: {n1} tramo(s), tipos de IVA: {sorted(tipos1)}")
    print(f"{args.csv2}: {n2} tramo(s), tipos de IVA: {sorted(tipos2)}")
    print()

    if n1 != n2:
        print(f"DIFERENCIA DE RECUENTO: una lectura trae {n1} tramo(s) y la "
              f"otra {n2} -- una de las dos se ha dejado (o inventado) un "
              f"tramo entero.")
        return
    if tipos1 != tipos2:
        print("MISMO NUMERO DE TRAMOS, TIPOS DISTINTOS: las dos lecturas "
              "coinciden en cuantos tramos hay pero no en que tipo de IVA "
              "llevan -- eso es mas grave que un redondeo.")
        return

    # Mismo recuento y mismos tipos por fuera: para saber si de verdad hay
    # una diferencia en base/cuota (y no solo confirmar de nuevo lo que ya
    # sabiamos), se reutiliza comparar_tramos() -- SOLO su estado, nunca su
    # detalle (que si lleva las cifras). Evita duplicar la logica de
    # comparacion Y evita afirmar una diferencia que no exista de verdad.
    estado, _detalle_con_importes = cmp.comparar_tramos(t1, t2)
    if estado == cmp.COINCIDE:
        print("MISMOS TRAMOS, MISMOS TIPOS Y MISMOS IMPORTES: no hay ninguna "
              "diferencia real entre las dos lecturas para este campo.")
    else:
        print("MISMOS TRAMOS Y MISMOS TIPOS DE IVA en las dos lecturas: la "
              "diferencia esta en BASE o CUOTA (el importe), no en la "
              "estructura ni en el tipo aplicado -- probablemente redondeo "
              "o un digito mal leido. Eso no lo imprime este script; si "
              "quieres saber cuanto difiere, mira tu mismo esas dos "
              "columnas en el CSV.")


if __name__ == "__main__":
    main()
