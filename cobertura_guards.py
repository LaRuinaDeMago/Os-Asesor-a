#!/usr/bin/env python3
"""cobertura_guards.py — ¿qué guards están de verdad puestos a prueba?

POR QUE HACE FALTA ESTO
-----------------------
`audit_project.py` comprueba que ningún guard sea HUERFANO (que exista y no lo
llame nadie). Eso ya ha cazado cuatro casos reales.

Pero un guard puede estar perfectamente cableado y no estar probado NUNCA. Es un
agujero distinto y más silencioso: la suite pasa, el auditor da verde, y nadie
ha comprobado jamás que ese guard sepa decir FALLO cuando toca.

Este script contesta la pregunta que faltaba:

    De todos los guards que corren en el veredicto, ¿cuáles han llegado alguna
    vez a un estado distinto de OK/NO_APLICA durante las pruebas?

Un guard que en toda la batería solo devuelve OK o NO_APLICA es un guard que
NUNCA ha demostrado que sirva para algo.

COMO FUNCIONA
-------------
Envuelve `evaluar_fila_v4`, ejecuta las dos suites tal cual, y anota qué estados
alcanzó cada guard. No modifica las suites ni el motor.

Uso:  python3 cobertura_guards.py
"""
import io
import contextlib
import sys
from collections import defaultdict

import motor_veredicto as mv

#: Estados BENIGNOS: "he mirado y no hay nada que decir". Cualquier otro estado
#: es el guard haciendo su trabajo.
#:
#: Se define por lo benigno y no por lo util a proposito. La primera version
#: listaba los estados utiles ("FALLO", "NO_COMPROBADO", "AMBAR") y daba por no
#: probado a `confianza_captura`, que habla otro idioma —ALTA/MEDIA/BAJA— y SI
#: habia llegado a BAJA. Una lista blanca de lo bueno se queda corta en cuanto
#: aparece un vocabulario nuevo; una lista de lo inocuo, no. Es la misma leccion
#: del escaner de privacidad: lo desconocido no se declara limpio.
ESTADOS_BENIGNOS = frozenset({"OK", "NO_APLICA", "ALTA"})

vistos = defaultdict(set)
_original = mv.evaluar_fila_v4


def _espia(*a, **kw):
    v, motivo, guards = _original(*a, **kw)
    for nombre, (estado, _) in guards.items():
        vistos[nombre].add(estado)
    return v, motivo, guards


def main():
    mv.evaluar_fila_v4 = _espia
    # Las suites importan el motor y llaman a evaluar_fila_v4; el espia las
    # observa sin que ellas se enteren.
    silencio = io.StringIO()
    for modulo in ("test_motor_veredicto", "test_adversarial"):
        try:
            with contextlib.redirect_stdout(silencio):
                __import__(modulo)
        except SystemExit:
            pass          # las suites terminan con sys.exit(); es lo normal
        except Exception as e:
            print(f"  aviso: {modulo} lanzo {type(e).__name__}")
    mv.evaluar_fila_v4 = _original

    if not vistos:
        print("Ninguna suite ejercito el motor. Algo va mal.")
        return 2

    ejercitados, solo_ok = [], []
    for nombre in sorted(vistos):
        estados = vistos[nombre]
        utiles = estados - ESTADOS_BENIGNOS
        if utiles:
            ejercitados.append((nombre, utiles))
        else:
            solo_ok.append((nombre, estados))

    print("=" * 68)
    print("COBERTURA REAL DE LOS GUARDS EN LAS SUITES")
    print("=" * 68)
    print(f"  guards observados          : {len(vistos)}")
    print(f"  probados en estado util    : {len(ejercitados)}")
    print(f"  SOLO vistos en estado benigno: {len(solo_ok)}")
    print()
    print("PROBADOS de verdad (han llegado a un estado que NO es benigno):")
    for nombre, utiles in ejercitados:
        print(f"  ✔ {nombre:<32} -> {', '.join(sorted(utiles))}")

    if solo_ok:
        print()
        print("NUNCA HAN SALTADO — cableados, pero sin demostrar que sirvan:")
        for nombre, estados in solo_ok:
            print(f"  ✗ {nombre:<32} (solo {', '.join(sorted(estados))})")
        print()
        print("  No es necesariamente un fallo: algunos dependen de datos que la")
        print("  captura todavia no emite (confianza por campo, doble lectura,")
        print("  triangulacion, patron de cartera). Pero conviene saber cuales")
        print("  son y no confundir 'cableado' con 'probado'.")

    print()
    print(f"  cobertura util: {len(ejercitados)}/{len(vistos)} "
          f"({len(ejercitados) * 100 // len(vistos)}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
