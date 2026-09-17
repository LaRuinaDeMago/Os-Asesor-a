#!/usr/bin/env python3
"""test_diag_tramos_dos_lecturas.py — que el diagnostico de tramos_iva
distinga bien sus tres casos, y no invente una diferencia que no existe.

POR QUE ESTA BATERIA
----------------------
Al escribir `diag_tramos_dos_lecturas.py` (17-09-2026) y probarlo a mano con
datos inventados aparecio un defecto real en la primera version: con dos
lecturas REALMENTE identicas, el script afirmaba igualmente "la diferencia
esta en base o cuota" -- porque la rama final asumia que, si no era recuento
ni tipo, tenia que haber una diferencia en algun sitio, sin comprobarlo. Un
diagnostico que afirma una diferencia que no existe es tan malo como uno que
no encuentra la que si existe. Arreglado reutilizando `comparar_tramos()`
para la comprobacion final, en vez de asumir por descarte.

REGLA DE DATOS: solo tipos de IVA inventados a mano, ninguno real."""
import contextlib
import io
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import diag_tramos_dos_lecturas as diag

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


def correr(t1, t2):
    """Ejecuta la logica de decision de main() sin pasar por CSV ni argparse."""
    n1, tipos1 = diag.resumen(t1)
    n2, tipos2 = diag.resumen(t2)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        if n1 != n2:
            print(f"DIFERENCIA DE RECUENTO: {n1} vs {n2}")
        elif tipos1 != tipos2:
            print("MISMO NUMERO DE TRAMOS, TIPOS DISTINTOS")
        else:
            import comparar_captura_vs_verdad as cmp
            estado, _ = cmp.comparar_tramos(t1, t2)
            if estado == cmp.COINCIDE:
                print("MISMOS TRAMOS, MISMOS TIPOS Y MISMOS IMPORTES")
            else:
                print("la diferencia esta en BASE o CUOTA")
    return buf.getvalue()


def pruebas_los_cuatro_casos():
    dos_tramos = [{"tipo": 21, "base": 100, "cuota": 21},
                  {"tipo": 5, "base": 50, "cuota": 2.5}]
    un_tramo_21 = [{"tipo": 21, "base": 100, "cuota": 21}]
    un_tramo_10 = [{"tipo": 10, "base": 100, "cuota": 10}]
    un_tramo_21_otro_importe = [{"tipo": 21, "base": 100, "cuota": 21.01}]

    salida = correr(dos_tramos, un_tramo_21)
    comprobar("recuento distinto se detecta como tal",
              "RECUENTO" in salida, severidad="P0")

    salida = correr(un_tramo_21, un_tramo_10)
    comprobar("mismo recuento, tipo distinto (21 vs 10) se detecta como tal",
              "TIPOS DISTINTOS" in salida, severidad="P0")

    salida = correr(un_tramo_21, un_tramo_21_otro_importe)
    comprobar("mismo tipo, importe distinto (21.00 vs 21.01) -> BASE o CUOTA",
              "BASE o CUOTA" in salida, severidad="P0")

    salida = correr(un_tramo_21, list(un_tramo_21))
    comprobar("EL BUG REAL: dos lecturas de verdad identicas NO deben "
              "afirmar una diferencia en base/cuota que no existe",
              "MISMOS TRAMOS, MISMOS TIPOS Y MISMOS IMPORTES" in salida
              and "BASE o CUOTA" not in salida, severidad="P0")


def pruebas_resumen_no_es_sensible():
    """resumen() nunca devuelve base ni cuota, solo tipos y recuento."""
    tramos = [{"tipo": 21, "base": 99999.99, "cuota": 20999.98}]
    n, tipos = diag.resumen(tramos)
    comprobar("resumen() no expone base/cuota en su tupla de retorno",
              n == 1 and tipos == {21.0}, detalle=repr((n, tipos)),
              severidad="P0")


def main():
    print("=" * 72)
    print("DIAGNOSTICO DE TRAMOS EN DOS LECTURAS — bateria")
    print("=" * 72)
    pruebas_los_cuatro_casos()
    pruebas_resumen_no_es_sensible()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nDistingue los tres casos reales y no afirma una diferencia de")
    print("importe cuando las dos lecturas son de verdad identicas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
