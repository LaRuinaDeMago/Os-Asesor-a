"""
SUITE DE PRUEBAS — numeracion_correlativa.py
Primera pieza del módulo de facturas EMITIDAS (distinto de la validación de
facturas recibidas que hace motor_veredicto.py). Todo sintético, sin ningún
dato de cliente real — los números de serie no tienen identidad asociada.

Ejecutar con: python3 test_numeracion_correlativa.py
"""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from numeracion_correlativa import (
    siguiente_numero, detectar_huecos, validar_numero_nuevo, validar_ledger,
)

FALLOS = []


def check(cond, nombre):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


print("=== siguiente_numero ===")
check(siguiente_numero(set()) == 1, "serie vacia empieza en 1 por defecto")
check(siguiente_numero(set(), numero_inicial=100) == 100,
      "serie vacia respeta numero_inicial si se le da otro (serie heredada de otro sistema)")
check(siguiente_numero({1, 2, 3}) == 4, "serie sin huecos -> siguiente es max+1")
check(siguiente_numero({1, 2, 3, 5}) == 6,
      "con un hueco YA existente (2->3->5), el siguiente sigue siendo max+1: "
      "el hueco se avisa aparte, no se rellena solo inventando un numero")

print("\n=== detectar_huecos ===")
check(detectar_huecos(set()) == [], "serie vacia: sin huecos que reportar")
check(detectar_huecos({1, 2, 3, 4}) == [], "serie completa: sin huecos")
check(detectar_huecos({1, 2, 4, 5}) == [3], "un hueco simple, detectado")
check(detectar_huecos({1, 3, 5}) == [2, 4], "dos huecos, los dos detectados")
check(detectar_huecos({5, 6, 7}, numero_inicial=1) == [1, 2, 3, 4],
      "serie que 'empieza' en 5 sin numero_inicial=5 explicito: los 4 numeros "
      "de antes se leen como hueco -- fuerza a declarar el inicio real, no lo adivina")
check(detectar_huecos({5, 6, 7}, numero_inicial=5) == [],
      "la MISMA serie, con el inicio real declarado (5): sin huecos, correcto")

print("\n=== validar_numero_nuevo ===")
check(validar_numero_nuevo(4, {1, 2, 3})[0] == "OK",
      "el correlativo exacto esperado -> OK")
check(validar_numero_nuevo(2, {1, 2, 3})[0] == "FALLO",
      "numero ya usado -> FALLO (duplicado)")
check("duplicado" in validar_numero_nuevo(2, {1, 2, 3})[1],
      "el motivo del duplicado lo dice explicitamente, no solo 'FALLO'")
check(validar_numero_nuevo(10, {1, 2, 3})[0] == "FALLO",
      "numero que salta por delante (deja hueco 4-9) -> FALLO")
check("hueco" in validar_numero_nuevo(10, {1, 2, 3})[1].lower(),
      "el motivo dice que es un hueco, no solo que esta mal")
check(validar_numero_nuevo(1, set())[0] == "OK",
      "primera factura de una serie nueva: 1 es el correlativo correcto")
check(validar_numero_nuevo(3, set())[0] == "FALLO",
      "primera factura de una serie nueva pero proponiendo el numero 3: "
      "FALLO, deja hueco (1 y 2 no existen)")

print("\n=== validar_ledger (el historico completo, no solo el ultimo numero) ===")
ledger_sano = [
    {'serie': 'A', 'numero': 1}, {'serie': 'A', 'numero': 2}, {'serie': 'A', 'numero': 3},
    {'serie': 'B', 'numero': 1}, {'serie': 'B', 'numero': 2},
]
informe_sano = validar_ledger(ledger_sano)
check(informe_sano['A']['sano'] and informe_sano['B']['sano'],
      "ledger sin huecos ni duplicados en ninguna serie -> las dos sanas")
check(informe_sano['A']['n_facturas'] == 3, "cuenta bien las facturas por serie (A: 3)")

ledger_roto = [
    {'serie': 'A', 'numero': 1}, {'serie': 'A', 'numero': 2}, {'serie': 'A', 'numero': 2},
    {'serie': 'A', 'numero': 4},
    {'serie': 'B', 'numero': 1},
]
informe_roto = validar_ledger(ledger_roto)
check(not informe_roto['A']['sano'], "serie A con duplicado y hueco -> NO sana")
check(informe_roto['A']['duplicados'] == [2], "el duplicado detectado es exactamente el 2")
check(informe_roto['A']['huecos'] == [3], "el hueco detectado es exactamente el 3")
check(informe_roto['B']['sano'], "serie B, sin tocar por el problema de A, sigue sana "
      "-- las series NO se contaminan entre si")

print("\n=== Ninguna funcion necesita ni acepta un dato de cliente ===")
# Control de diseno, no solo de comportamiento: las firmas de las cuatro
# funciones publicas no tienen ningun parametro de nombre/NIF/importe.
import inspect
for fn in (siguiente_numero, detectar_huecos, validar_numero_nuevo, validar_ledger):
    params = set(inspect.signature(fn).parameters)
    check(not (params & {'nif', 'cliente', 'nombre', 'importe', 'nif_cliente'}),
          f"{fn.__name__} no tiene ningun parametro de identidad de cliente")

print("\n" + "=" * 50)
if FALLOS:
    print(f"❌ {len(FALLOS)} PRUEBA(S) FALLIDA(S): {FALLOS}")
    sys.exit(1)
print("✅ TODAS LAS PRUEBAS PASAN")
