#!/usr/bin/env python3
"""ensayo_diag_contrapartida_tipo0.py -- ensayo de diag_contrapartida_tipo0.py.

TODO SINTETICO. Fabrica un contenedor .DAT minimo (ZIP con un Diario.dbf,
misma tecnica que ensayo_retro_semaforo.py -- reutiliza su escribir_dbf(),
nunca la reescribe) con tres asientos disenados a proposito:

  1. Una liquidacion de IVA de verdad: linea 477 con tipo '0' (IVA=0) y su
     contrapartida en una cuenta 4750 (Hacienda) por el MISMO importe.
  2. Una venta real: linea 477 con tipo 21 -- debe IGNORARSE (no es tipo 0).
  3. Un caso ambiguo: linea 477 con tipo '0' pero contrapartida en una
     cuenta de banco (572) con un importe que NO coincide -- para
     comprobar que el diagnostico lo cuenta aparte, sin fingir que es una
     liquidacion limpia.

Uso:
    python ensayo_diag_contrapartida_tipo0.py
"""
import os
import sys
import tempfile
import zipfile
from collections import Counter

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from ensayo_retro_semaforo import escribir_dbf
from diag_contrapartida_tipo0 import analizar_contenedor

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def main():
    print("=" * 68)
    print("ENSAYO: diag_contrapartida_tipo0.py (corpus sintetico, ningun dato real)")
    print("=" * 68)

    tmp = tempfile.mkdtemp()
    ruta_dbf = os.path.join(tmp, "Diario.dbf")
    ruta_dat = os.path.join(tmp, "SP_C_01.DAT")

    filas = [
        # Asiento 1: liquidacion de IVA -- 477 tipo 0, contrapartida en 4750
        {"ASIEN": 1, "SUBCTA": "477000001", "EURODEBE": 0, "EUROHABER": 1000.00,
         "IVA": 0, "FECHA": "20250401"},
        {"ASIEN": 1, "SUBCTA": "475000001", "EURODEBE": 1000.00, "EUROHABER": 0,
         "IVA": 0, "FECHA": "20250401"},
        # Asiento 2: venta real, tipo 21 -- debe ignorarse por completo
        {"ASIEN": 2, "SUBCTA": "477000001", "EURODEBE": 0, "EUROHABER": 210.00,
         "IVA": 21, "FECHA": "20250402"},
        {"ASIEN": 2, "SUBCTA": "430000001", "EURODEBE": 1210.00, "EUROHABER": 0,
         "IVA": 0, "FECHA": "20250402"},
        # Asiento 3: tipo 0, pero contrapartida en banco con importe distinto
        {"ASIEN": 3, "SUBCTA": "472000001", "EURODEBE": 50.00, "EUROHABER": 0,
         "IVA": 0, "FECHA": "20250403"},
        {"ASIEN": 3, "SUBCTA": "572000001", "EURODEBE": 0, "EUROHABER": 999.00,
         "IVA": 0, "FECHA": "20250403"},
    ]
    escribir_dbf(ruta_dbf, filas)
    with zipfile.ZipFile(ruta_dat, "w") as z:
        z.write(ruta_dbf, "Diario.dbf")

    contador_prefijos = Counter()
    stats = Counter()
    vistos = set()
    analizar_contenedor(ruta_dat, contador_prefijos, stats, vistos)

    print("\n=== Deteccion de asientos tipo '0' ===")
    comprobar("detecta los 2 asientos con linea tipo '0' (1 y 3), no el de tipo 21",
              stats["asientos_tipo0_examinados"] == 2,
              f"stats={dict(stats)}")

    print("\n=== Contrapartidas ===")
    comprobar("cuenta la contrapartida 4750 del asiento de liquidacion",
              contador_prefijos.get("4750", 0) == 1, f"contador={dict(contador_prefijos)}")
    comprobar("cuenta la contrapartida 5720 del asiento ambiguo",
              contador_prefijos.get("5720", 0) == 1, f"contador={dict(contador_prefijos)}")
    comprobar("NUNCA cuenta la contrapartida 4300 del asiento de tipo 21 (se ignora entero)",
              contador_prefijos.get("4300", 0) == 0, f"contador={dict(contador_prefijos)}")

    print("\n=== Coincidencia de importe ===")
    comprobar("1 de 2 contrapartidas coincide en importe (la de 4750, no la de 5720)",
              stats["contrapartida_importe_coincide"] == 1
              and stats["contrapartidas_totales"] == 2,
              f"stats={dict(stats)}")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 68)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. Distingue liquidacion (contrapartida Hacienda, "
          "importe exacto) de un caso ambiguo, e ignora por completo las "
          "lineas con un tipo de IVA real.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
