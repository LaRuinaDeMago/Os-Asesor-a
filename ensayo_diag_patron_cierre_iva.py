#!/usr/bin/env python3
"""ensayo_diag_patron_cierre_iva.py -- ensayo de diag_patron_cierre_iva.py.

TODO SINTETICO. `analizar()` es una funcion pura sobre un diccionario en
memoria -- nunca abre un 303_LOCAL.json real.

QUE PRUEBA
----------
A. Un caso que CONFIRMA la hipotesis (tipo 0 con 1-2 apuntes, cancela casi
   exacto el resto del lado) se mide como tal: ratio ~1.0, pocos apuntes.
B. Un caso que la REFUTA (tipo 0 disperso, muchos apuntes, no cancela) se
   mide como tal: ratio lejos de 1.0, apuntes altos.
C. Una celda sin ningun otro tipo con que comparar se cuenta aparte, nunca
   se fuerza un ratio que no significa nada (division por cero evitada).

Uso:
    python ensayo_diag_patron_cierre_iva.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diag_patron_cierre_iva import analizar

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def celda(base, cuota, apuntes=1):
    return {"base": base, "cuota": cuota, "apuntes": apuntes}


def main():
    print("=" * 68)
    print("ENSAYO: diag_patron_cierre_iva.py (todo sintetico)")
    print("=" * 68)

    # === A. Confirma la hipotesis =========================================
    print("\n=== A. Caso que CONFIRMA (liquidacion tipica: 1-2 apuntes) ===")
    datos_a = {
        "CLIENTE_SINTETICO_A": {
            "2025T1": {
                "devengado": {"21": celda(1000, 210, 5), "0": celda(0, -210, 1)},
                "deducible": {"21": celda(500, 105, 3), "0": celda(0, -105, 2)},
            },
        },
    }
    r_a = analizar(datos_a)
    comprobar("detecta las 2 celdas con tipo 0 (devengado + deducible)",
              r_a["total_celdas_con_tipo0"] == 2, f"r={r_a}")
    comprobar("los dos ratios caen exactos en 1.0 (cancela perfecto)",
              all(abs(x - 1.0) < 1e-9 for x in r_a["ratios"]), f"ratios={r_a['ratios']}")
    comprobar("los apuntes del tipo 0 son 1 y 2 -- el patron tipico de liquidacion",
              set(r_a["apuntes_tipo0"]) == {1, 2}, f"apuntes={dict(r_a['apuntes_tipo0'])}")

    # === B. Refuta la hipotesis ============================================
    print("\n=== B. Caso que REFUTA (ruido disperso, muchos apuntes) ===")
    datos_b = {
        "CLIENTE_SINTETICO_B": {
            "2025T1": {
                "devengado": {"21": celda(1000, 210, 5), "0": celda(50, 12, 30)},
                "deducible": {},
            },
        },
    }
    r_b = analizar(datos_b)
    comprobar("detecta 1 celda con tipo 0",
              r_b["total_celdas_con_tipo0"] == 1, f"r={r_b}")
    comprobar("el ratio NO esta cerca de 1.0 (no cancela nada)",
              not (0.9 <= r_b["ratios"][0] <= 1.1), f"ratio={r_b['ratios']}")
    comprobar("cuenta los 30 apuntes de ruido, no los confunde con 1-2",
              30 in r_b["apuntes_tipo0"], f"apuntes={dict(r_b['apuntes_tipo0'])}")

    # === C. Sin otro tipo con que comparar (evita division por cero) ======
    print("\n=== C. Un lado que es TODO tipo 0 -- no hay nada que cancelar ===")
    datos_c = {
        "CLIENTE_SINTETICO_C": {
            "2025T1": {
                "devengado": {"0": celda(100, 21, 1)},
                "deducible": {},
            },
        },
    }
    r_c = analizar(datos_c)
    comprobar("se cuenta aparte, no se calcula un ratio inventado",
              r_c["sin_otros_tipos_con_que_comparar"] == 1 and len(r_c["ratios"]) == 0,
              f"r={r_c}")

    print()
    print("=" * 68)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. El diagnostico distingue confirmar de refutar, y "
          "no fuerza un ratio cuando no hay nada con que comparar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
