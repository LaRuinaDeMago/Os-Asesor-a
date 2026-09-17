#!/usr/bin/env python3
"""test_comparar_dos_lecturas.py — que el comparador de dos lecturas reales
mida bien, y que jamas imprima un valor.

POR QUE ESTA BATERIA
----------------------
`comparar_dos_lecturas_reales.py` existe para una pregunta muy concreta del
17-09-2026 (primera factura real de punta a punta): si Gemini lee la MISMA
foto dos veces, ¿lee lo mismo? Las dos entradas son SIEMPRE reales -- a
diferencia de `comparar_captura_vs_verdad.py`, aqui no hay ningun caso
SINTETICO que autorice imprimir un valor. La barrera tiene que sostenerse
sin esa via de escape.

Misma disciplina que `test_comparar_captura.py`: se planta un senuelo (un
importe y un texto que no existen en la vida real, con pinta reconocible) en
un campo que DIFIERE a proposito, y se comprueba que ese senuelo nunca
aparece en lo que el script imprime -- solo el nombre del campo y la
palabra COINCIDE/DIFIERE/NO_VINO.

REGLA DE DATOS
----------------
Ni un dato real. Todas las filas de aqui son inventadas a mano para esta
bateria."""
import contextlib
import io
import sys
import tempfile
import os

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json

import comparar_dos_lecturas_reales as m
import comparar_captura_vs_verdad as cmp

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


SENUELO_IMPORTE = "999999,99"
SENUELO_TEXTO = "SENUELO_NO_ES_UN_NIF_REAL"


def pruebas_comparar():
    """La funcion comparar(): estados correctos, exclusion correcta."""
    fila_a = {"total_factura": "1.420,00", "nº_documento": "A26/7.612",
              "_coste": "0.0009"}
    fila_b = {"total_factura": "1420.00", "nº_documento": "A26/7.612",
              "_coste": "0.0012"}
    resultado, error = m.comparar([fila_a], [fila_b])
    comprobar("mismo importe escrito distinto -> COINCIDE (mismo criterio "
              "que comparar_campo)",
              error is None and
              [e for _, c, e in resultado if c == "total_factura"] == [cmp.COINCIDE],
              severidad="P0")
    comprobar("_coste NO se compara -- es de la LLAMADA, no de la LECTURA",
              not any(c == "_coste" for _, c, _ in resultado), severidad="P0")

    fila_c = {"total_factura": "1.420,00"}
    fila_d = {"total_factura": "1.720,00"}
    resultado, error = m.comparar([fila_c], [fila_d])
    comprobar("un importe realmente distinto -> DIFIERE",
              error is None and resultado[0][2] == cmp.DIFIERE, severidad="P0")

    fila_e = {"nif_margen": "B-12345674"}
    fila_f = {}
    resultado, error = m.comparar([fila_e], [fila_f])
    comprobar("un campo ausente en la segunda lectura -> NO_VINO",
              error is None and resultado[0][2] == cmp.NO_VINO, severidad="P1")


def pruebas_tramos_iva_crudos_de_csv():
    """EL BUG REAL, encontrado el 17-09-2026 con la primera factura real de
    verdad: `comparar_tramos()` (dentro de comparar_campo) da por hecho que
    su lado 'esperado' ya llega desempaquetado -- cierto en su uso original
    (contra una verdad JSON ya cargada), falso aqui, donde los DOS lados son
    texto crudo salido de un csv.DictReader. Sin desempaquetar antes, iterar
    sobre el texto caracter a caracter no encontraba ningun tramo real, y DOS
    LECTURAS IDENTICAS daban DIFIERE siempre -- justo lo que le paso a Diego."""
    raw = json.dumps([{"tipo": 21, "base": 100, "cuota": 21},
                      {"tipo": 10, "base": 50, "cuota": 5}])
    resultado, error = m.comparar([{"tramos_iva": raw}], [{"tramos_iva": raw}])
    comprobar("MISMA cadena cruda de tramos_iva en los dos lados -> COINCIDE",
              error is None and resultado == [(1, "tramos_iva", cmp.COINCIDE)],
              detalle=repr(resultado), severidad="P0")

    raw_incompleto = json.dumps([{"tipo": 21, "base": 100, "cuota": 21}])
    resultado, error = m.comparar([{"tramos_iva": raw}],
                                  [{"tramos_iva": raw_incompleto}])
    comprobar("tramos_iva genuinamente distintos (falta un tramo) SIGUE "
              "detectandose como DIFIERE tras el arreglo",
              error is None and resultado == [(1, "tramos_iva", cmp.DIFIERE)],
              detalle=repr(resultado), severidad="P0")

    resultado, error = m.comparar([{"tramos_iva": ""}], [{"tramos_iva": ""}])
    comprobar("las dos vacias (caso ISP, sin desglose de IVA) -> COINCIDE",
              error is None and resultado == [(1, "tramos_iva", cmp.COINCIDE)],
              detalle=repr(resultado), severidad="P0")


def pruebas_recuento_distinto():
    """Distinto numero de facturas: se declara, no se empareja a ciegas."""
    resultado, error = m.comparar([{"a": "1"}], [{"a": "1"}, {"a": "2"}])
    comprobar("recuento distinto: no compara nada",
              resultado is None, severidad="P0")
    comprobar("recuento distinto: el error dice CUANTAS, no CUALES",
              error is not None and "1" in error and "2" in error,
              detalle=repr(error), severidad="P1")


def pruebas_no_imprime_valores():
    """La barrera de verdad: ni un senuelo sobrevive a la impresion."""
    fila_1 = {"total_factura": SENUELO_IMPORTE, "proveedor": SENUELO_TEXTO}
    fila_2 = {"total_factura": "1.00", "proveedor": "OTRO"}
    resultado, error = m.comparar([fila_1], [fila_2])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        m.imprimir_resultados(resultado, 1)
    salida = buf.getvalue()
    comprobar("el importe senuelo NO aparece en lo impreso",
              SENUELO_IMPORTE not in salida, severidad="P0")
    comprobar("el texto senuelo NO aparece en lo impreso",
              SENUELO_TEXTO not in salida, severidad="P0")
    comprobar("pero SI dice que 'total_factura' DIFIERE (el nombre del "
              "campo no es un dato, es estructura)",
              "total_factura" in salida and cmp.DIFIERE in salida,
              severidad="P0")
    comprobar("y SI dice que 'proveedor' DIFIERE",
              "proveedor" in salida, severidad="P0")


def pruebas_leer_csv_real():
    """leer_csv() de verdad, con un fichero temporal -- que el CSV se lea
    igual que orquestador.py lee facturas.csv (mismo encoding)."""
    with tempfile.TemporaryDirectory() as tmp:
        ruta = os.path.join(tmp, "prueba.csv")
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write("total_factura,proveedor\r\n121,ejemplo\r\n")
        filas = m.leer_csv(ruta)
        comprobar("leer_csv lee la fila esperada",
                  filas == [{"total_factura": "121", "proveedor": "ejemplo"}],
                  detalle=repr(filas), severidad="P0")


def main():
    print("=" * 72)
    print("COMPARADOR DE DOS LECTURAS REALES — bateria")
    print("=" * 72)
    pruebas_comparar()
    pruebas_tramos_iva_crudos_de_csv()
    pruebas_recuento_distinto()
    pruebas_no_imprime_valores()
    pruebas_leer_csv_real()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nCompara con el mismo criterio que comparar_captura_vs_verdad.py,")
    print("declara cuando no puede emparejar filas, y ningun senuelo sobrevive")
    print("a la impresion -- solo nombres de campo y estados.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
