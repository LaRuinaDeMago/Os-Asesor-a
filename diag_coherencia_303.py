#!/usr/bin/env python3
"""diag_coherencia_303.py — ¿es coherente consigo mismo lo que reconstruimos?

POR QUE EXISTE ESTE SCRIPT, Y POR QUE DEBIO EXISTIR ANTES
-----------------------------------------------------------
El 26-08-2026 se cruzo `303_LOCAL.json` contra los 1.043 modelos 303
presentados buscando importes iguales. Resultado: 4% de solape, y aflojar la
tolerancia a centimos NO lo mejoraba (4,0% -> 4,0%), lo que descarta el
redondeo. Los numeros, sencillamente, no son los mismos.

Pero ese cruce se hizo DANDO POR BUENO `303_LOCAL.json`, que nunca se habia
verificado. Es el error de metodo que el propio proyecto tiene escrito en
todas partes: validar el instrumento antes de fiarse de sus lecturas.
`extraer_303_pdf.py` si lo hacia -- se auto-validaba por consistencia interna
antes de publicar un numero -- y aqui se salto ese paso.

QUE COMPRUEBA, SIN NECESITAR NI UN PDF
----------------------------------------
Dos cosas que tienen que ser ciertas en cualquier contabilidad correcta,
sea del cliente que sea, y que no dependen de ninguna fuente externa:

  1. COHERENCIA ARITMETICA: si un apunte de IVA dice que el tipo es el 21%,
     su cuota tiene que ser el 21% de su base. Es exactamente lo que ya
     comprueba `guard_aritmetica_base_tipo` en el motor, aplicado aqui al
     agregado por trimestre en vez de a una factura.

  2. ORDEN DE MAGNITUD: si las bases salieran en centimos en vez de en euros
     (o al reves), el cruce contra el 303 no casaria NUNCA por mucha
     tolerancia que se le diera, y el sintoma seria justo el que se ha
     medido. Un error de escala se ve en la distribucion de magnitudes.

SI LA COHERENCIA SALE ALTA -> nuestros numeros son sanos, y el desajuste con
el 303 viene de otro sitio: lo mas probable, que un "cubo" del corpus no sea
un cliente suelto sino varias empresas mezcladas (ver el caso real de la
carpeta organizada por equipo). El cruce por importes no puede funcionar
mientras eso no se resuelva.

SI LA COHERENCIA SALE BAJA -> el problema esta en `reconstruir_303.py` y
llevamos cruzando contra el 303 unos numeros que no describen ninguna
contabilidad. Habria que arreglar eso antes de volver a mirar un PDF.

REGLA DE DATOS (.claude/rules/datos.md — diseno de tres roles)
---------------------------------------------------------------
Lee un fichero _LOCAL, asi que lo ejecuta el titular, no Claude. Por pantalla
solo salen RECUENTOS y PORCENTAJES: ni un importe, ni un nombre de carpeta,
ni una clave del JSON. Los errores, por TIPO de excepcion.

Uso:
    python diag_coherencia_303.py
    python diag_coherencia_303.py --json 303_LOCAL.json
"""
import argparse
import json
import math
import os
import sys
from collections import Counter

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))

#: Margen sobre el tipo declarado. 0,5 puntos porcentuales absorbe el
#: redondeo de sumar cientos de apuntes sin absorber un error de verdad.
TOL_PUNTOS = 0.5

#: Tipos con los que tiene sentido comprobar la aritmetica. El 0% se excluye
#: porque cuota 0 sobre base positiva es correcto y no prueba nada.
TIPOS_COMPROBABLES = (4, 5, 7, 8, 10, 16, 18, 21)


def magnitud(v):
    """Orden de magnitud: 1.234,56 -> 3 (mil y pico). Para detectar de un
    vistazo si todo el fichero esta multiplicado o dividido por 100."""
    v = abs(v)
    if v < 1:
        return -1
    return int(math.floor(math.log10(v)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", default=os.path.join(AQUI, "303_LOCAL.json"))
    args = ap.parse_args()

    if not os.path.exists(args.json):
        print(f"ERROR: no encuentro {args.json}", file=sys.stderr)
        sys.exit(1)

    with open(args.json, "r", encoding="utf-8") as f:
        datos = json.load(f)

    veredicto = Counter()
    magnitudes_base = Counter()
    magnitudes_cuota = Counter()
    desviaciones = Counter()
    tipos_vistos = Counter()
    n_cubos = len(datos)
    n_trimestres = 0
    celdas_sin_base = 0

    for _cubo, trimestres in datos.items():
        for _tri, lados in trimestres.items():
            n_trimestres += 1
            for lado in ("devengado", "deducible"):
                for tipo_txt, celda in lados.get(lado, {}).items():
                    base = celda.get("base", 0.0)
                    cuota = celda.get("cuota", 0.0)
                    tipos_vistos[tipo_txt] += 1
                    if base:
                        magnitudes_base[magnitud(base)] += 1
                    if cuota:
                        magnitudes_cuota[magnitud(cuota)] += 1

                    try:
                        tipo = int(tipo_txt)
                    except ValueError:
                        veredicto["tipo no catalogado"] += 1
                        continue
                    if tipo not in TIPOS_COMPROBABLES:
                        veredicto["tipo 0% o no comprobable"] += 1
                        continue
                    if abs(base) < 1:
                        celdas_sin_base += 1
                        veredicto["sin base con la que comparar"] += 1
                        continue

                    efectivo = cuota / base * 100.0
                    diferencia = efectivo - tipo
                    if abs(diferencia) <= TOL_PUNTOS:
                        veredicto["COHERENTE (la cuota es el tipo de la base)"] += 1
                    else:
                        veredicto["INCOHERENTE"] += 1
                    # Redondeo a 1 punto para ver si el error es sistematico
                    # (todo desviado igual) o disperso (ruido de agregacion).
                    desviaciones[round(diferencia)] += 1

    comprobables = (veredicto["COHERENTE (la cuota es el tipo de la base)"]
                    + veredicto["INCOHERENTE"])

    print("=" * 70)
    print("COHERENCIA INTERNA DE LO QUE RECONSTRUIMOS  (sin mirar ningun PDF)")
    print("=" * 70)
    print(f"  cubos                    : {n_cubos:,}")
    print(f"  trimestres               : {n_trimestres:,}")
    print(f"  celdas comprobables      : {comprobables:,}")
    print()
    for k, n in veredicto.most_common():
        print(f"    {k:<46} {n:>8,}")
    if comprobables:
        ok = veredicto["COHERENTE (la cuota es el tipo de la base)"]
        pct = ok * 100.0 / comprobables
        print()
        print(f"  COHERENCIA: {pct:.1f}%  ({ok:,} de {comprobables:,})")
        print()
        if pct >= 90:
            print("  -> Nuestros numeros son SANOS. La cuota es el tipo de la")
            print("     base en la practica totalidad de los casos, asi que el")
            print("     desajuste contra el 303 NO viene de aqui. La causa mas")
            print("     probable es de IDENTIDAD: un cubo del corpus no es un")
            print("     cliente suelto. Hasta resolver eso, el cruce por")
            print("     importes no puede funcionar.")
        elif pct >= 50:
            print("  -> A medias. Una parte de la reconstruccion es sana y otra")
            print("     no. Hay que mirar el desglose de desviaciones de abajo")
            print("     antes de seguir cruzando contra nada.")
        else:
            print("  -> Nuestros numeros NO son coherentes consigo mismos. El")
            print("     problema esta en reconstruir_303.py, no en los PDF. Se")
            print("     arregla eso antes de volver a mirar un modelo.")

    print()
    print("DESVIACION RESPECTO AL TIPO DECLARADO (en puntos porcentuales):")
    print("  (todo en 0 = sano;  todo desviado LO MISMO = error sistematico;")
    print("   disperso = mezcla de tipos dentro de la misma cuenta)")
    for d, n in sorted(desviaciones.items())[:25]:
        print(f"    {d:>+4} puntos   {'#' * min(45, n):<45} {n:,}")

    print()
    print("ORDEN DE MAGNITUD DE LAS BASES (0 = unidades, 3 = miles, 5 = cientos de miles):")
    for m, n in sorted(magnitudes_base.items()):
        etiqueta = "menos de 1" if m < 0 else f"10^{m}"
        print(f"    {etiqueta:<12} {'#' * min(45, n):<45} {n:,}")
    print()
    print("ORDEN DE MAGNITUD DE LAS CUOTAS:")
    for m, n in sorted(magnitudes_cuota.items()):
        etiqueta = "menos de 1" if m < 0 else f"10^{m}"
        print(f"    {etiqueta:<12} {'#' * min(45, n):<45} {n:,}")
    print()
    print("TIPOS DE IVA PRESENTES (cuantas celdas de cada uno):")
    for t, n in tipos_vistos.most_common():
        print(f"    tipo {t:<20} {n:>8,}")
    print()
    print("Todo lo de arriba son recuentos: se puede pegar en el chat entero.")


if __name__ == "__main__":
    main()
