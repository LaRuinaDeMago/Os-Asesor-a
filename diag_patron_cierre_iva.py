#!/usr/bin/env python3
"""diag_patron_cierre_iva.py -- ¿el "tipo 0%" que cancela el trimestre es
un asiento de liquidacion/cierre de IVA, no ruido aleatorio?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
Comparando fichas de `cuadre_303_ficha.py` de 5 clientes x 4 trimestres
(14-09-2026), el patron aparecio en las 20 fichas: un tipo real (21%, a
veces 10%) con su cuota correcta, y un "tipo 0" con una cuota NEGATIVA que
cancela casi exacto el total del lado (devengado o deducible), dejando el
TOTAL en 0,00. `diag_coherencia_por_lado.py` (27-08-2026) midio 99,7-99,9%
de coherencia y concluyo que esto era raro -- pero esa comprobacion mira
base x tipo = cuota DENTRO de un tipo, nunca compara un tipo CONTRA otros
del mismo lado, asi que no podia ver este patron aunque fuera universal.

HIPOTESIS: no es ruido, es el asiento de liquidacion trimestral (el que
traspasa el saldo de 477/472 a la cuenta de Hacienda al presentar el 303).
Toca la cuenta 477/472 igual que una venta o compra real -- por eso entra
en el mismo filtro -- pero no es una venta ni compra, asi que no tiene un
tipo de IVA grabado en el campo IVA del Diario.dbf: cae en "tipo 0" con la
cuota completa del traspaso, casi siempre en 1-2 apuntes.

COMO SE COMPRUEBA, SIN VER NINGUN NOMBRE NI IMPORTE DE UN CLIENTE CONCRETO
------------------------------------------------------------------------
Para cada (cliente, trimestre, lado) con un tipo "0" presente:
  ratio = |cuota del tipo 0| / |suma de cuotas de los demas tipos|
Si la hipotesis es correcta, ese ratio deberia agruparse muy cerca de 1.0
(cancela casi exacto) en la gran mayoria de casos -- no disperso al azar.
Tambien se cuenta cuantos apuntes tiene el tipo "0" (la liquidacion deberia
ser 1-2 lineas, nunca decenas).

Solo se imprimen recuentos y la distribucion del ratio. Ningun nombre,
ninguna clave de cliente, ningun importe de un caso concreto.

Uso:
    python diag_patron_cierre_iva.py 303_LOCAL.json
"""
import json
import sys
from collections import Counter

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def analizar(datos):
    total_celdas_con_tipo0 = 0
    ratios = []
    apuntes_tipo0 = Counter()
    solo_tipo0 = 0          # el lado ENTERO es tipo 0 (nada que cancelar)
    sin_otros_tipos = 0
    por_lado = Counter()    # cuantas celdas con tipo0 hay en cada lado

    for _clave, trimestres in datos.items():
        for _tri, lados in trimestres.items():
            for lado, celdas in lados.items():
                if "0" not in celdas:
                    continue
                celda0 = celdas["0"]
                cuota0 = celda0.get("cuota", 0.0)
                if cuota0 == 0.0:
                    continue
                total_celdas_con_tipo0 += 1
                por_lado[lado] += 1
                apuntes_tipo0[celda0.get("apuntes", 0)] += 1

                suma_otros = sum(
                    c.get("cuota", 0.0) for t, c in celdas.items() if t != "0"
                )
                if suma_otros == 0.0:
                    sin_otros_tipos += 1
                    continue
                ratio = abs(cuota0) / abs(suma_otros)
                ratios.append(ratio)

    return {
        "total_celdas_con_tipo0": total_celdas_con_tipo0,
        "por_lado": por_lado,
        "sin_otros_tipos_con_que_comparar": sin_otros_tipos,
        "ratios": ratios,
        "apuntes_tipo0": apuntes_tipo0,
    }


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else "303_LOCAL.json"
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)

    r = analizar(datos)

    print("=" * 68)
    print("PATRON DEL 'TIPO 0' QUE CANCELA EL TRIMESTRE -- solo recuentos")
    print("=" * 68)
    print(f"  celdas (cliente+trimestre+lado) con tipo '0' presente: "
          f"{r['total_celdas_con_tipo0']:,}")
    for lado, n in r["por_lado"].items():
        print(f"    en {lado}: {n:,}")
    print(f"  de esas, sin ningun otro tipo con que comparar (todo el lado "
          f"es tipo 0): {r['sin_otros_tipos_con_que_comparar']:,}")
    print()

    print("REPARTO DE APUNTES DEL TIPO '0' (si la hipotesis es correcta, "
          "casi todo deberia ser 1-2):")
    for n_apuntes in sorted(r["apuntes_tipo0"]):
        print(f"    {n_apuntes:>3} apunte(s): {r['apuntes_tipo0'][n_apuntes]:>5} celdas")
    print()

    ratios = r["ratios"]
    if ratios:
        cerca_de_1 = sum(1 for x in ratios if 0.95 <= x <= 1.05)
        muy_cerca_de_1 = sum(1 for x in ratios if 0.999 <= x <= 1.001)
        lejos = sum(1 for x in ratios if not (0.5 <= x <= 1.5))
        print(f"RATIO |cuota tipo 0| / |suma de los demas tipos| "
              f"({len(ratios):,} celdas comparables):")
        print(f"    entre 0,999 y 1,001 (cancela casi exacto): "
              f"{muy_cerca_de_1:,}  ({100*muy_cerca_de_1/len(ratios):.1f}%)")
        print(f"    entre 0,95 y 1,05 (cancela aproximado):    "
              f"{cerca_de_1:,}  ({100*cerca_de_1/len(ratios):.1f}%)")
        print(f"    fuera de 0,5-1,5 (no parece cancelar):     "
              f"{lejos:,}  ({100*lejos/len(ratios):.1f}%)")
        print(f"    mediana del ratio: {sorted(ratios)[len(ratios)//2]:.4f}")

    print()
    print("COMO SE LEE:")
    print("  - Si la mayoria cancela casi exacto (ratio ~1.0) y el tipo '0'")
    print("    casi siempre tiene 1-2 apuntes -> confirma la hipotesis: es")
    print("    el asiento de liquidacion trimestral de IVA, no ruido.")
    print("  - Si los ratios estan dispersos y hay muchos apuntes en el")
    print("    tipo '0' -> la hipotesis NO se sostiene, hay que buscar otra")
    print("    explicacion antes de tocar el codigo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
