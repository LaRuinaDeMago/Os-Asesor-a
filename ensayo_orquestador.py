#!/usr/bin/env python3
"""ensayo_orquestador.py — construir_historico_y_secuencia() no pierde facturas
en formato español.

POR QUE EXISTE
---------------
`orquestador.py` no tenía ningún ensayo propio. `construir_historico_y_secuencia()`
alimenta `guard_importe_atipico` y `guard_secuencia_documental_proveedor` — dos de
los 16 guards de `evaluar_fila_v4()` — y hasta hoy nunca se había ejecutado en
ninguna prueba con datos en formato español.

EL BUG QUE ESTO CAZA (encontrado en auditoría propia, 26-08-2026)
-------------------------------------------------------------------
La función hacía `float(r.get('total_factura', 0) or 0)` con un `except
ValueError: t = 0`. El motor SÍ entiende el formato español ('132,90') vía
`contrato_datos.parse_numero()` — es lo que decide que esa factura sea VERDE —
pero esta función no, así que cualquier factura con totales en formato español
producía `t = 0`, nunca entraba en el histórico (`if t > 0`), y
`guard_importe_atipico` se quedaba sin datos para ese proveedor, en silencio,
sin que nada lo dijera. Reproducido antes de arreglarlo: tres facturas reales
con totales '132,90'/'140,00'/'135,50' producían un histórico vacío, `{}`.

REGLA DE DATOS: todo inventado. Sin ficheros, sin red, sin tocar disco del
despacho.

Uso:  python3 ensayo_orquestador.py
"""
import sys

from orquestador import construir_historico_y_secuencia

resultados = []


def comprobar(nombre, condicion, obtenido="", esperado="", sev="P1"):
    resultados.append((nombre, condicion, sev))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}")
    if not condicion:
        print(f"           obtenido: {obtenido}")
        print(f"           esperado: {esperado}   [{sev}]")


def main():
    print("=" * 72)
    print("ENSAYO — construir_historico_y_secuencia() de orquestador.py")
    print("=" * 72)

    print("\nFORMATO ESPAÑOL (el bug real, reproducido antes de arreglarlo):")
    filas_espanol = [
        {'nif': 'B12345674', 'proveedor': 'Proveedor Piloto SL',
         'total_factura': '132,90', 'nº_documento': 'F1'},
        {'nif': 'B12345674', 'proveedor': 'Proveedor Piloto SL',
         'total_factura': '140,00', 'nº_documento': 'F2'},
        {'nif': 'B12345674', 'proveedor': 'Proveedor Piloto SL',
         'total_factura': '135,50', 'nº_documento': 'F3'},
    ]
    hist, sec = construir_historico_y_secuencia(filas_espanol)
    comprobar("tres facturas en formato español SÍ alimentan el histórico por NIF",
              hist.get('B12345674', {}).get('n_facturas_normales') == 3,
              hist.get('B12345674'), "n_facturas_normales=3", "P0")
    comprobar("y también por nombre de proveedor (busqueda de respaldo)",
              hist.get('Proveedor Piloto SL', {}).get('n_facturas_normales') == 3,
              hist.get('Proveedor Piloto SL'), "n_facturas_normales=3", "P0")
    media_esperada = round((132.90 + 140.00 + 135.50) / 3, 2)
    comprobar("la media se calcula sobre los importes REALES, no sobre ceros",
              hist.get('B12345674', {}).get('media') == media_esperada,
              hist.get('B12345674', {}).get('media'), media_esperada, "P0")

    print("\nFORMATO ANGLOSAJÓN (no debe romperse por arreglar el español):")
    filas_ingles = [
        {'nif': 'B99999999', 'proveedor': 'Otro Proveedor',
         'total_factura': '100.00', 'nº_documento': 'G1'},
        {'nif': 'B99999999', 'proveedor': 'Otro Proveedor',
         'total_factura': '105.00', 'nº_documento': 'G2'},
    ]
    hist2, _ = construir_historico_y_secuencia(filas_ingles)
    comprobar("formato con punto decimal sigue funcionando igual que antes",
              hist2.get('B99999999', {}).get('n_facturas_normales') == 2,
              hist2.get('B99999999'), "n_facturas_normales=2", "P0")

    print("\nCASOS SIN DATO (no deben reventar ni contarse como importe real):")
    filas_vacias = [
        {'nif': 'B12345678', 'proveedor': 'Proveedor Sin Dato',
         'total_factura': '', 'nº_documento': 'H1'},
        {'nif': 'B12345678', 'proveedor': 'Proveedor Sin Dato',
         'total_factura': None, 'nº_documento': 'H2'},
        {'nif': 'B12345678', 'proveedor': 'Proveedor Sin Dato',
         'total_factura': 'ilegible', 'nº_documento': 'H3'},
    ]
    hist3, _ = construir_historico_y_secuencia(filas_vacias)
    comprobar("total ausente/ilegible no entra en el histórico (no es un 0 real)",
              'B12345678' not in hist3, hist3.get('B12345678'), "sin entrada", "P0")

    print("\n" + "=" * 72)
    fallos = [r for r in resultados if not r[1]]
    p0 = [r for r in fallos if r[2] == "P0"]
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
          f"FALLAN: {len(fallos)}  (de ellas P0: {len(p0)})")
    if fallos:
        print("\nDEFECTOS CONFIRMADOS EN PIE:")
        for nombre, _, sev in fallos:
            print(f"  [{sev}] {nombre}")
        sys.exit(1)
    print("\nEl histórico que alimenta importe_atipico y secuencia_documental")
    print("no pierde facturas por el formato en que vienen los importes.")
    sys.exit(0)


if __name__ == "__main__":
    main()
