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

    # Tabla de contingencia: suena_a_equipo (si/no) x sospechosa (si/no).
    # SOLO recuentos y medias -- nunca un nombre.
    celdas = {(True, True): [], (True, False): [], (False, True): [], (False, False): []}
    for nombre, n_grupos in detalle.items():
        eq = suena_a_equipo(nombre)
        sosp = n_grupos >= 2
        celdas[(eq, sosp)].append(n_grupos)

    def resumen(lista):
        if not lista:
            return "0 carpetas"
        media = sum(lista) / len(lista)
        return f"{len(lista)} carpetas, media {media:.1f} grupos"

    print()
    print("=" * 70)
    print("TABLA DE CONTINGENCIA: nombre sugiere equipo/copia  x  SOSPECHOSA")
    print("=" * 70)
    print(f"  suena a equipo/copia  Y  sospechosa:      {resumen(celdas[(True, True)])}")
    print(f"  suena a equipo/copia  Y  sana:             {resumen(celdas[(True, False)])}")
    print(f"  NO suena a equipo/copia  Y  sospechosa:    {resumen(celdas[(False, True)])}")
    print(f"  NO suena a equipo/copia  Y  sana:          {resumen(celdas[(False, False)])}")

    n_equipo = len(celdas[(True, True)]) + len(celdas[(True, False)])
    n_no_equipo = len(celdas[(False, True)]) + len(celdas[(False, False)])
    tasa_equipo = (len(celdas[(True, True)]) / n_equipo) if n_equipo else None
    tasa_no_equipo = (len(celdas[(False, True)]) / n_no_equipo) if n_no_equipo else None

    print()
    print("TASA DE SOSPECHOSAS POR GRUPO:")
    print(f"  entre las que SUENAN a equipo/copia: "
          f"{f'{tasa_equipo:.0%}' if tasa_equipo is not None else 'sin datos'} "
          f"({n_equipo} carpetas)")
    print(f"  entre las que NO suenan a equipo/copia: "
          f"{f'{tasa_no_equipo:.0%}' if tasa_no_equipo is not None else 'sin datos'} "
          f"({n_no_equipo} carpetas)")

    print()
    print("COMO SE LEE:")
    print("  - Si la tasa entre las que 'suenan a equipo' es claramente mas alta")
    print("    que entre las que no -- la senal SOSPECHOSA es real: correlaciona")
    print("    con lo que ya sabiamos por el nombre.")
    print("  - Si las dos tasas son parecidas (sobre todo si la segunda tambien")
    print("    es alta), SOSPECHOSA no distingue nada por si sola hoy: es el")
    print("    artefacto de continuidad temporal, no mezcla real de empresas.")


if __name__ == "__main__":
    main()
