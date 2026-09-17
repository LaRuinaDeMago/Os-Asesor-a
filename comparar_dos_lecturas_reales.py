#!/usr/bin/env python3
"""comparar_dos_lecturas_reales.py — compara DOS lecturas de Gemini de la
MISMA factura real, campo a campo, sin imprimir ni un solo valor.

PARA QUE SIRVE
---------------
Paso 2 del primer ensayo con datos reales (PENDIENTE.md, 17-09-2026): pasar
la misma foto por `captura_orquestador.py` dos veces y saber si el modelo lee
lo mismo las dos veces, o si hay variabilidad entre llamadas -- una pregunta
que este proyecto lleva dos meses queriendo MEDIR en vez de suponer.

`comparar_captura_vs_verdad.py` ya compara una lectura contra una VERDAD
conocida (para las muestras sinteticas). Este script reutiliza su misma
funcion `comparar_campo()` -- mismo criterio por tipo de campo (importes por
valor numerico, fechas por dia, tramos_iva sin importar el orden -- ver ese
modulo para el porque de cada uno) en vez de duplicar la logica aqui, que es
justo la clase de error que `diag_logica_duplicada.py` existe para cazar.
Pero a diferencia de aquel, aqui NINGUNO de los dos CSV es sintetico: los dos
son datos reales, asi que la salida no lleva jamas un valor, solo el nombre
del campo y si COINCIDE, DIFIERE, o no vino en una de las dos.

USO
----
    python comparar_dos_lecturas_reales.py facturas_reales_LOCAL.csv facturas_reales_LOCAL_run2.csv

Los dos ficheros tienen que venir de capturar LA MISMA carpeta (mismo orden
de fila) -- si el numero de facturas no coincide, el script lo dice y no
compara nada, en vez de emparejar filas que no son la misma factura.

Diego: esto lo ejecutas tu, en tu terminal, igual que los demas scripts que
tocan datos reales. Lo que imprime al final SI es seguro de pegar en el
chat, letra por letra -- es la misma disciplina que ya sigue
`medir_estructura_capturas.py`.
"""
import argparse
import csv
import sys

import comparar_captura_vs_verdad as cmp

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Metadatos de LA LLAMADA, no de la LECTURA -- coste y tokens cambian entre
#: dos llamadas por diseño (cada una se factura aparte) y no dicen nada sobre
#: si el modelo leyo lo mismo. Compararlos aqui seria ruido puro.
CAMPOS_EXCLUIDOS = ("_tokens_entrada", "_tokens_salida", "_coste",
                    "_modelo", "_proveedor")


def leer_csv(ruta):
    with open(ruta, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def comparar(filas1, filas2):
    """Compara fila a fila (por POSICION, no por contenido -- ver docstring
    del modulo sobre por que eso exige el mismo orden de captura) y campo a
    campo. Devuelve (resultados, error): si error no es None, resultados es
    None y no se ha comparado nada."""
    if len(filas1) != len(filas2):
        return None, (f"recuento distinto: {len(filas1)} factura(s) en el "
                      f"primer fichero, {len(filas2)} en el segundo -- no se "
                      f"puede emparejar fila a fila con seguridad")
    resultados = []
    for i, (f1, f2) in enumerate(zip(filas1, filas2), start=1):
        for col in sorted(set(f1) | set(f2)):
            if col in CAMPOS_EXCLUIDOS:
                continue
            estado, _detalle = cmp.comparar_campo(col, f1.get(col), f2.get(col))
            resultados.append((i, col, estado))
    return resultados, None


def imprimir_resultados(resultados, n_filas):
    """Toda la impresion, separada de la lectura de fichero para poder
    probarla directamente con datos sinteticos (ver test_comparar_dos_lecturas.py)."""
    print(f"{n_filas} factura(s) comparada(s) campo a campo -- "
          f"solo el nombre del campo y el resultado, nunca el valor.\n")

    por_estado = {}
    for fila_i, col, estado in resultados:
        por_estado.setdefault(estado, []).append((fila_i, col))

    orden = (cmp.DIFIERE, cmp.NO_VINO, cmp.SOLO_PUNTUACION, cmp.COINCIDE)
    for estado in orden:
        items = por_estado.get(estado, [])
        if not items:
            continue
        print(f"{estado} ({len(items)}):")
        for fila_i, col in items:
            etiqueta = f"fila {fila_i}: {col}" if n_filas > 1 else col
            print(f"  {etiqueta}")
        print()

    if por_estado.get(cmp.DIFIERE) or por_estado.get(cmp.NO_VINO):
        print("Hay diferencias entre las dos lecturas -- justo lo que este "
              "script existe para encontrar. No es necesariamente un "
              "problema (algunos campos, como la puntuacion de un texto, "
              "pueden variar sin que la factura este mal leida), pero "
              "conviene mirarlos uno a uno en tu propio CSV.")
    else:
        print("Las dos lecturas coinciden en todos los campos comparados.")


def main():
    parser = argparse.ArgumentParser(
        description="Compara dos lecturas reales de la misma factura, sin imprimir valores.")
    parser.add_argument("csv1", help="Primera captura (ej. facturas_reales_LOCAL.csv)")
    parser.add_argument("csv2", help="Segunda captura de la MISMA foto (ej. ..._run2.csv)")
    args = parser.parse_args()

    try:
        filas1 = leer_csv(args.csv1)
    except OSError as e:
        print(f"ERROR: no se pudo leer {args.csv1!r} ({type(e).__name__})")
        sys.exit(1)
    try:
        filas2 = leer_csv(args.csv2)
    except OSError as e:
        print(f"ERROR: no se pudo leer {args.csv2!r} ({type(e).__name__})")
        sys.exit(1)

    resultados, error = comparar(filas1, filas2)
    if error:
        print(f"NO COMPARADO: {error}")
        sys.exit(1)

    imprimir_resultados(resultados, len(filas1))


if __name__ == "__main__":
    main()
