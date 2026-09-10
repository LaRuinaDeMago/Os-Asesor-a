#!/usr/bin/env python3
"""diag_calibracion_sospechosa.py — ¿la señal SOSPECHOSA de
diag_carpetas_multiempresa.py es real, o el artefacto de "sin continuidad
temporal entre copias" ya documentado el 27-08-2026?

DE DONDE SALE ESTO
--------------------
Contra el corpus real completo, `diag_carpetas_multiempresa.py` dio
**27 de 27 carpetas sospechosas (100%)** -- magnitud casi identica al primer
resultado "imposible" que el propio script documenta en su cabecera (27 de
28, el 27-08, atribuido entonces a un artefacto de muestreo). Pero esta vez
el diagnostico de "codigos delgados" NO lo explica (solo 78 de 958 codigos,
8%, tienen 1-2 proveedores). Hay dos hipotesis igual de plausibles y no se
elige ninguna sin mas datos:

  A) Artefacto de continuidad temporal: dos copias de la MISMA empresa
     solapan poco por pura estadistica (cada periodo ve una fraccion
     distinta del total de proveedores de la empresa a lo largo de los anos).
  B) Real: el corpus esta organizado por EQUIPO/COPIA en vez de por cliente
     en la mayoria de sus carpetas -- ya hay un caso confirmado a mano
     ("Contabilidad ordenador de Jose") de que esto pasa.

QUE MIDE ESTE SCRIPT, Y COMO DISTINGUE LAS DOS HIPOTESIS
-------------------------------------------------------------
Cruza la senal SOSPECHOSA contra la pista de nombre que YA usa
`cuadre_303_ficha.py` (`suena_a_equipo`: contiene "ordenador", "copia",
"backup", "pc0/1/2"...). Si sospechosa correlaciona con "suena a equipo", la
hipotesis B (real) gana. Si sale sospechosa por igual entre carpetas con
nombre de equipo y carpetas con nombre de cliente concreto, es la A
(artefacto) -- y en ese caso la senal SOSPECHOSA de diag_carpetas_multiempresa.py
no es fiable tal cual esta hoy.

REGLA DE DATOS: nunca se imprime un nombre de carpeta, solo la tabla de
contingencia (4 numeros) y el numero medio de grupos por categoria. Diego
puede pegar la salida completa en el chat sin problema.

Uso:
    python diag_calibracion_sospechosa.py "RUTA_DEL_CORPUS"
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from diag_carpetas_multiempresa import calcular_sospechosas
from cuadre_303_ficha import suena_a_equipo


#: Por debajo de esta tasa entre las carpetas que NO suenan a equipo/copia
#: (las que deberian ser, en su mayoria, un cliente concreto), la senal
#: SOSPECHOSA se considera informativa. Por encima, esta saturada: dispara
#: incluso donde se esperaria que casi nunca lo hiciera, y eso es la firma
#: del artefacto de continuidad temporal, no de mezcla real. 0.5 no es un
#: numero fino: cualquier cosa por encima de la mitad ya significa que la
#: senal no distingue mejor que lanzar una moneda.
UMBRAL_TASA_INFORMATIVA = 0.5


def calcular_contingencia(detalle):
    """Cruza {carpeta_real: n_grupos} contra suena_a_equipo(). Devuelve un
    dict con los recuentos, las dos tasas, y un veredicto de si la senal
    SOSPECHOSA es informativa en ESTE corpus -- nunca un nombre. Extraido a
    funcion el 27-08-2026 para que `consolidar_identidad.py` pueda importar
    el mismo calculo y el mismo veredicto, en vez de fiarse ciegamente de la
    marca SOSPECHOSA sin haberla calibrado."""
    celdas = {(True, True): [], (True, False): [], (False, True): [], (False, False): []}
    for nombre, n_grupos in detalle.items():
        eq = suena_a_equipo(nombre)
        sosp = n_grupos >= 2
        celdas[(eq, sosp)].append(n_grupos)

    n_equipo = len(celdas[(True, True)]) + len(celdas[(True, False)])
    n_no_equipo = len(celdas[(False, True)]) + len(celdas[(False, False)])
    tasa_equipo = (len(celdas[(True, True)]) / n_equipo) if n_equipo else None
    tasa_no_equipo = (len(celdas[(False, True)]) / n_no_equipo) if n_no_equipo else None

    # Sin carpetas de nombre "cliente concreto" con las que contrastar, no
    # hay manera de calibrar nada -- NO_COMPROBADO, no un OK ni un FALLO por
    # omision (misma disciplina que motor_veredicto.py).
    if tasa_no_equipo is None:
        informativa = None
    else:
        informativa = tasa_no_equipo < UMBRAL_TASA_INFORMATIVA

    return {
        "celdas": celdas,
        "n_equipo": n_equipo,
        "n_no_equipo": n_no_equipo,
        "tasa_equipo": tasa_equipo,
        "tasa_no_equipo": tasa_no_equipo,
        "informativa": informativa,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("carpeta")
    ap.add_argument("--min-nifs", type=int, default=3)
    ap.add_argument("--max-difusion", type=float, default=0.30)
    args = ap.parse_args()

    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: esa carpeta no existe.", file=sys.stderr)
        sys.exit(2)

    print("Calculando (recorre el corpus una vez)...")
    r = calcular_sospechosas(raiz, args.min_nifs, args.max_difusion, progreso=True)
    if r is None:
        print("ERROR: no hay ningun .DAT ahi dentro.", file=sys.stderr)
        sys.exit(2)

    detalle = r["n_grupos_por_carpeta_real"]
    if not detalle:
        print("ERROR: ninguna carpeta con senal suficiente para medir.",
              file=sys.stderr)
        sys.exit(2)

    c = calcular_contingencia(detalle)

    def resumen(lista):
        if not lista:
            return "0 carpetas"
        media = sum(lista) / len(lista)
        return f"{len(lista)} carpetas, media {media:.1f} grupos"

    print()
    print("=" * 70)
    print("TABLA DE CONTINGENCIA: nombre sugiere equipo/copia  x  SOSPECHOSA")
    print("=" * 70)
    print(f"  suena a equipo/copia  Y  sospechosa:      {resumen(c['celdas'][(True, True)])}")
    print(f"  suena a equipo/copia  Y  sana:             {resumen(c['celdas'][(True, False)])}")
    print(f"  NO suena a equipo/copia  Y  sospechosa:    {resumen(c['celdas'][(False, True)])}")
    print(f"  NO suena a equipo/copia  Y  sana:          {resumen(c['celdas'][(False, False)])}")

    print()
    print("TASA DE SOSPECHOSAS POR GRUPO:")
    tasa_eq = c["tasa_equipo"]
    tasa_no_eq = c["tasa_no_equipo"]
    print(f"  entre las que SUENAN a equipo/copia: "
          f"{f'{tasa_eq:.0%}' if tasa_eq is not None else 'sin datos'} "
          f"({c['n_equipo']} carpetas)")
    print(f"  entre las que NO suenan a equipo/copia: "
          f"{f'{tasa_no_eq:.0%}' if tasa_no_eq is not None else 'sin datos'} "
          f"({c['n_no_equipo']} carpetas)")

    print()
    print("COMO SE LEE:")
    print("  - Si la tasa entre las que 'suenan a equipo' es claramente mas alta")
    print("    que entre las que no -- la senal SOSPECHOSA es real: correlaciona")
    print("    con lo que ya sabiamos por el nombre.")
    print("  - Si las dos tasas son parecidas (sobre todo si la segunda tambien")
    print("    es alta), SOSPECHOSA no distingue nada por si sola hoy: es el")
    print("    artefacto de continuidad temporal, no mezcla real de empresas.")

    print()
    print("=" * 70)
    if c["informativa"] is None:
        print("VEREDICTO: NO_COMPROBADO -- no hay carpetas con nombre de cliente")
        print("concreto con las que contrastar. No se puede calibrar todavia.")
    elif c["informativa"]:
        print(f"VEREDICTO: INFORMATIVA -- la tasa entre las que NO suenan a "
              f"equipo ({tasa_no_eq:.0%}) esta por debajo del "
              f"{UMBRAL_TASA_INFORMATIVA:.0%}. La marca SOSPECHOSA distingue "
              f"algo real en este corpus.")
    else:
        print(f"VEREDICTO: NO INFORMATIVA -- la tasa entre las que NO suenan a "
              f"equipo ({tasa_no_eq:.0%}) tambien esta por encima del "
              f"{UMBRAL_TASA_INFORMATIVA:.0%}. La marca SOSPECHOSA no distingue "
              f"nada en este corpus: es el artefacto de continuidad temporal, "
              f"no mezcla real. No se recomienda usarla para priorizar revision.")
    print("=" * 70)


if __name__ == "__main__":
    main()
