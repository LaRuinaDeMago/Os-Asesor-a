#!/usr/bin/env python3
"""diag_coherencia_por_volumen.py — la incoherencia, ¿en celdas grandes o pequeñas?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
Medido el 27-08-2026: devengado 60,1% coherente, deducible 67,1%. La hipotesis
ISP (lineas 477 sin venta detras -> base=0) se confirma PARCIALMENTE -- el
contador "base<1 con cuota>=1" es 22 en devengado frente a 1 en deducible --
pero NO explica la mayoria: 22 de 67 incoherentes en devengado, y deducible
tiene un 33% de incoherencia que la hipotesis ISP no puede explicar (ISP no
afecta al lado deducible de la misma forma).

LA SIGUIENTE PREGUNTA, ANTES DE TEORIZAR MAS: la incoherencia que queda,
¿esta en celdas con POCOS apuntes (una factura rara descuadrando un trimestre
casi vacio -- ruido esperable, no un bug) o tambien en celdas GRANDES (cientos
de apuntes -- eso si seria una senal real de que la derivacion falla de forma
sistematica)?

QUE MIDE
---------
Separa las celdas comprobables (tipo>0, base>=1) en tramos por NUMERO DE
APUNTES, y da la coherencia dentro de cada tramo. Ademas, la metrica que mas
importa para decidir si el 303 va a cuadrar: que FRACCION DEL VOLUMEN TOTAL
DE APUNTES vive en celdas coherentes frente a incoherentes -- una celda de
1 apunte pesa lo mismo que una de 5.000 si solo se cuentan celdas, y eso
puede esconder la respuesta real.

REGLA DE DATOS: lo ejecuta el titular. Solo RECUENTOS, nunca un importe ni
una clave de cliente.

Uso:
    python diag_coherencia_por_volumen.py
"""
import json
from collections import Counter

TOL = 0.5
TIPOS = (4, 5, 7, 8, 10, 16, 18, 21)
TRAMOS = ((1, 2), (3, 9), (10, 49), (50, 199), (200, 10**9))


def tramo_de(n):
    for lo, hi in TRAMOS:
        if lo <= n <= hi:
            return f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
    return "?"


def main():
    with open("303_LOCAL.json", "r", encoding="utf-8") as f:
        datos = json.load(f)

    por_tramo = Counter()
    por_tramo_coherente = Counter()
    apuntes_en_coherentes = 0
    apuntes_en_incoherentes = 0
    apuntes_sin_comprobar = 0

    for _cli, tris in datos.items():
        for _tri, lados in tris.items():
            for _lado, celdas in lados.items():
                for tipo_txt, v in celdas.items():
                    try:
                        tipo = int(tipo_txt)
                    except ValueError:
                        continue
                    n = v.get("apuntes", 0)
                    if tipo not in TIPOS or abs(v["base"]) < 1:
                        apuntes_sin_comprobar += n
                        continue
                    efectivo = v["cuota"] / v["base"] * 100.0
                    coherente = abs(efectivo - tipo) <= TOL
                    t = tramo_de(n)
                    por_tramo[t] += 1
                    if coherente:
                        por_tramo_coherente[t] += 1
                        apuntes_en_coherentes += n
                    else:
                        apuntes_en_incoherentes += n

    print("COHERENCIA POR TAMAÑO DE CELDA (numero de apuntes agregados)")
    print("=" * 70)
    for lo, hi in TRAMOS:
        t = f"{lo}-{hi}" if hi < 10**9 else f"{lo}+"
        total = por_tramo.get(t, 0)
        coh = por_tramo_coherente.get(t, 0)
        pct = coh * 100.0 / total if total else 0
        print(f"  {t:<10} celdas={total:>4}  coherentes={coh:>4}  ({pct:.1f}%)")

    print()
    total_apuntes = apuntes_en_coherentes + apuntes_en_incoherentes
    pct_vol = apuntes_en_coherentes * 100.0 / total_apuntes if total_apuntes else 0
    print("LO QUE MAS IMPORTA -- VOLUMEN DE APUNTES, NO NUMERO DE CELDAS:")
    print(f"  apuntes en celdas COHERENTES  : {apuntes_en_coherentes:>7,}  ({pct_vol:.1f}%)")
    print(f"  apuntes en celdas INCOHERENTES: {apuntes_en_incoherentes:>7,}  ({100-pct_vol:.1f}%)")
    print(f"  apuntes sin comprobar (tipo 0%/no catalogado/base<1): {apuntes_sin_comprobar:>7,}")
    print()
    print("COMO SE LEE:")
    print("  - Si la coherencia SUBE con el tamaño del tramo (mejor en 50+ que en")
    print("    1-2), la incoherencia es sobre todo RUIDO de celdas pequeñas: pocas")
    print("    facturas raras en trimestres casi vacios, no un fallo sistematico.")
    print("  - Si el % de VOLUMEN en celdas coherentes es alto (>85-90%) aunque el")
    print("    % de CELDAS no lo sea, la mayoria de los apuntes reales SI cuadran")
    print("    y el problema esta concentrado en pocos casos, no extendido.")
    print("  - Si la coherencia es baja o pareja en TODOS los tramos, incluidos")
    print("    los grandes, hay algo sistematico que sigue sin explicarse.")


if __name__ == "__main__":
    main()
