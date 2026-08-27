#!/usr/bin/env python3
"""diag_coherencia_por_lado.py — la coherencia (base*tipo=cuota) separada por
LADO, para confirmar o descartar la hipotesis ISP.

DE DONDE SALE ESTA PREGUNTA
-----------------------------
`diag_coherencia_303.py` midio el 27-08-2026, sobre el 303_LOCAL.json ya
regenerado con la base derivada del asiento: 64,9% de coherencia global. Mejor
que el 0% de antes del arreglo, pero "a medias", no "sano".

HIPOTESIS A COMPROBAR: la inversion del sujeto pasivo (ISP). En una ISP, la
linea 477 (repercutido) no tiene ninguna venta detras -- es una COMPRA en la
que el comprador se autorrepercute el IVA (construccion en subcontrata,
ciertos residuos/metales, telefonos/microprocesadores...). El derivador de
base de reconstruir_303.py busca, para toda linea 477, un ingreso (7xx) del
que derivar la base. En una ISP no hay ninguno: el resultado seria base=0 con
cuota real -- exactamente el patron de descuadre que se ha medido.

Si esta hipotesis es correcta, el lado DEVENGADO deberia salir claramente peor
que el DEDUCIBLE, y el contador "base<1 con cuota>=1" deberia ser alto en
devengado.

QUE MIDE ESTE SCRIPT, SIN TOCAR NINGUN PDF
---------------------------------------------
Solo lee 303_LOCAL.json (la reconstruccion desde ContaPlus, NO los modelos
presentados en la carpeta de documentos) y separa la misma comprobacion de
diag_coherencia_303.py en dos, una por lado. Es coherencia interna, un paso
ANTES de comparar contra el 303 real.

REGLA DE DATOS: lo ejecuta el titular. Solo imprime RECUENTOS, nunca un
importe ni una clave de cliente.

Uso:
    python diag_coherencia_por_lado.py
"""
import json
from collections import Counter

TOL = 0.5
TIPOS = (4, 5, 7, 8, 10, 16, 18, 21)


def main():
    with open("303_LOCAL.json", "r", encoding="utf-8") as f:
        datos = json.load(f)

    por_lado = {"deducible": Counter(), "devengado": Counter()}
    casos_base_cero_cuota_no = {"deducible": 0, "devengado": 0}

    for _cli, tris in datos.items():
        for _tri, lados in tris.items():
            for lado, celdas in lados.items():
                for tipo_txt, v in celdas.items():
                    try:
                        tipo = int(tipo_txt)
                    except ValueError:
                        continue
                    if tipo not in TIPOS:
                        continue
                    base, cuota = v["base"], v["cuota"]
                    if abs(base) < 1:
                        if abs(cuota) >= 1:
                            casos_base_cero_cuota_no[lado] += 1
                        continue
                    efectivo = cuota / base * 100.0
                    if abs(efectivo - tipo) <= TOL:
                        por_lado[lado]["coherente"] += 1
                    else:
                        por_lado[lado]["incoherente"] += 1

    print("COHERENCIA POR LADO (sin mirar ningun PDF, solo 303_LOCAL.json)")
    print("=" * 70)
    for lado in ("deducible", "devengado"):
        c = por_lado[lado]
        total = c["coherente"] + c["incoherente"]
        pct = c["coherente"] * 100.0 / total if total else 0
        print(f"  {lado:<12} coherente={c['coherente']:>4}  incoherente={c['incoherente']:>4}  "
              f"({pct:.1f}%)   base<1 con cuota>=1: {casos_base_cero_cuota_no[lado]}")
    print()
    print("COMO SE LEE:")
    print("  Si 'devengado' sale claramente peor que 'deducible', y el contador")
    print("  'base<1 con cuota>=1' de devengado es alto, confirma la hipotesis ISP:")
    print("  las lineas 477 sin venta detras se estan quedando con base=0.")


if __name__ == "__main__":
    main()
