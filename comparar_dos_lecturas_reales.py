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
import contrato_datos

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


def _vacio(v):
    """Solo un booleano -- si hay contenido o no, nunca cual."""
    return v is None or not str(v).strip()


#: Para un NO_VINO, DE QUE LADO falta el dato importa: "las dos lecturas
#: coinciden en no traerlo" no es lo mismo que "la primera lo traia y la
#: segunda lo perdio" -- esto ultimo es justo la inestabilidad que este
#: script existe para encontrar, y antes de esta nota las dos se veian
#: identicas bajo la misma etiqueta NO_VINO. Ningun valor entra aqui, solo
#: de que lado falta.
AUSENTE_EN_LAS_DOS = "ausente en las dos lecturas (no es inestabilidad)"
SEGUNDA_LO_PERDIO = "la 1ª lectura lo traia, la 2ª no -- SI es inestabilidad"
PRIMERA_LO_PERDIO = "la 2ª lectura lo traia, la 1ª no -- SI es inestabilidad"


def _nota_no_vino(v1, v2):
    v1_vacio, v2_vacio = _vacio(v1), _vacio(v2)
    if v1_vacio and v2_vacio:
        return AUSENTE_EN_LAS_DOS
    if v2_vacio:
        return SEGUNDA_LO_PERDIO
    if v1_vacio:
        return PRIMERA_LO_PERDIO
    return ""


def comparar(filas1, filas2):
    """Compara fila a fila (por POSICION, no por contenido -- ver docstring
    del modulo sobre por que eso exige el mismo orden de captura) y campo a
    campo. Devuelve (resultados, error): si error no es None, resultados es
    None y no se ha comparado nada. Cada resultado es (fila, campo, estado,
    nota) -- nota solo se rellena para NO_VINO (ver _nota_no_vino) y para el
    resto va vacia."""
    if len(filas1) != len(filas2):
        return None, (f"recuento distinto: {len(filas1)} factura(s) en el "
                      f"primer fichero, {len(filas2)} en el segundo -- no se "
                      f"puede emparejar fila a fila con seguridad")
    resultados = []
    for i, (f1, f2) in enumerate(zip(filas1, filas2), start=1):
        for col in sorted(set(f1) | set(f2)):
            if col in CAMPOS_EXCLUIDOS:
                continue
            v1, v2 = f1.get(col), f2.get(col)
            # BUG REAL, encontrado el 17-09-2026 con la primera factura real:
            # comparar_tramos() (dentro de comparar_campo) da por hecho que su
            # PRIMER argumento ya llega desempaquetado -- en su uso original
            # (comparar_captura_vs_verdad.py) siempre es asi, porque viene de
            # un JSON de verdad ya cargado, nunca de un CSV. Aqui los DOS
            # lados vienen crudos del CSV (texto), asi que iterar sobre ese
            # texto caracter a caracter no encuentra ningun tramo real -- y
            # DOS LECTURAS IDENTICAS daban DIFIERE siempre. Reproducido antes
            # de arreglar: `comparar_campo('tramos_iva', x, x)` con la MISMA
            # cadena en los dos lados ya daba DIFIERE. Se desempaqueta aqui,
            # en el unico sitio que sabe que los dos lados son crudos.
            if col == "tramos_iva":
                v1p = contrato_datos.parse_estructura(v1)
                v2p = contrato_datos.parse_estructura(v2)
            else:
                v1p, v2p = v1, v2
            estado, _detalle = cmp.comparar_campo(col, v1p, v2p)
            nota = _nota_no_vino(v1, v2) if estado == cmp.NO_VINO else ""
            resultados.append((i, col, estado, nota))
    return resultados, None


def imprimir_resultados(resultados, n_filas):
    """Toda la impresion, separada de la lectura de fichero para poder
    probarla directamente con datos sinteticos (ver test_comparar_dos_lecturas.py)."""
    print(f"{n_filas} factura(s) comparada(s) campo a campo -- "
          f"solo el nombre del campo y el resultado, nunca el valor.\n")

    por_estado = {}
    for fila_i, col, estado, nota in resultados:
        por_estado.setdefault(estado, []).append((fila_i, col, nota))

    orden = (cmp.DIFIERE, cmp.NO_VINO, cmp.SOLO_PUNTUACION, cmp.COINCIDE)
    for estado in orden:
        items = por_estado.get(estado, [])
        if not items:
            continue
        print(f"{estado} ({len(items)}):")
        for fila_i, col, nota in items:
            etiqueta = f"fila {fila_i}: {col}" if n_filas > 1 else col
            if nota:
                etiqueta += f"  [{nota}]"
            print(f"  {etiqueta}")
        print()

    # Solo un NO_VINO donde una lectura tenia el dato y la otra lo perdio
    # cuenta como inestabilidad real. Las dos vacias no es un problema -- es
    # que el documento no trae ese campo, y las dos lecturas coinciden en eso.
    inestable = bool(por_estado.get(cmp.DIFIERE)) or any(
        nota in (SEGUNDA_LO_PERDIO, PRIMERA_LO_PERDIO)
        for _, _, nota in por_estado.get(cmp.NO_VINO, []))

    if inestable:
        print("Hay diferencias entre las dos lecturas -- justo lo que este "
              "script existe para encontrar. No es necesariamente un "
              "problema (algunos campos, como la puntuacion de un texto, "
              "pueden variar sin que la factura este mal leida), pero "
              "conviene mirarlos uno a uno en tu propio CSV.")
    else:
        print("Las dos lecturas coinciden en todo lo que se puede comparar. "
              "Los campos NO_VINO, si los hay, estan ausentes en las DOS "
              "lecturas por igual -- no es inestabilidad, es que el "
              "documento no trae ese dato.")


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
