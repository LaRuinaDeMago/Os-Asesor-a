#!/usr/bin/env python3
"""ensayo_verificar_303_pdf.py -- ensayo de verificar_303_pdf.py.

TODO SINTETICO. No abre ningun PDF real ni ningun 303_LOCAL.json real:
`comparar_caso()`, `totales_contabilidad()` y `totales_pdf()` son funciones
puras que se prueban con diccionarios inventados, igual que
ensayo_cruce_303.py prueba `cruzar()` sin abrir un PDF.

QUE PRUEBA
----------
A. totales_contabilidad(): suma bien por lado, detecta tipo_no_catalogado,
   y devuelve None si la clave o el trimestre no existen (nunca compara
   contra un cero que no significa nada).
B. totales_pdf(): mapea las casillas del modelo 303 (01-09, 28-29) a los
   mismos cuatro totales que el lado de contabilidad.
C. comparar_caso(): clasifica CUADRA_EXACTO / CUADRA_CON_REDONDEO /
   NO_CUADRA / NO_COMPROBADO segun corresponda -- con el umbral exacto.
D. leer_manifest(): parsea CLAVE|TRIMESTRE|RUTA, ignora comentarios y
   lineas vacias, avisa (no revienta) con una linea mal formada.
E. Privacidad: main() nunca imprime la clave ni la ruta de un caso -- solo
   su posicion ("caso N"). Comprobado por AST, no por ojo.

Uso:
    python ensayo_verificar_303_pdf.py
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verificar_303_pdf import (
    totales_contabilidad, totales_pdf, comparar_caso, leer_manifest,
)

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
    print("ENSAYO: verificar_303_pdf.py (todo sintetico)")
    print("=" * 68)

    # === A. totales_contabilidad() ==========================================
    print("\n=== A. totales_contabilidad() ===")
    datos = {
        "CLAVE_UNO": {
            "2025T1": {
                "devengado": {"21": celda(1000.0, 210.0), "4": celda(100.0, 4.0)},
                "deducible": {"21": celda(500.0, 105.0)},
            },
        },
    }
    r = totales_contabilidad(datos, "CLAVE_UNO", "2025T1")
    comprobar("suma bien varios tipos en devengado",
              r[0] == 1100.0 and r[1] == 214.0, f"r={r}")
    comprobar("y el deducible por separado",
              r[2] == 500.0 and r[3] == 105.0, f"r={r}")
    comprobar("sin tipo_no_catalogado, el aviso es False", r[4] is False, f"r={r}")

    datos_sucio = {
        "CLAVE_DOS": {"2025T1": {
            "devengado": {"tipo_no_catalogado": celda(50.0, 0.0)},
            "deducible": {},
        }},
    }
    r2 = totales_contabilidad(datos_sucio, "CLAVE_DOS", "2025T1")
    comprobar("tipo_no_catalogado con importe SI activa el aviso",
              r2[4] is True, f"r2={r2}")

    comprobar("clave inexistente -> None, no un cero silencioso",
              totales_contabilidad(datos, "CLAVE_QUE_NO_EXISTE", "2025T1") is None)
    comprobar("trimestre inexistente -> None",
              totales_contabilidad(datos, "CLAVE_UNO", "2099T4") is None)

    # === B. totales_pdf() ====================================================
    print("\n=== B. totales_pdf() ===")
    casillas = {1: 1000.0, 2: 21.0, 3: 210.0, 28: 500.0, 29: 105.0}
    base_dev, cuota_dev, base_ded, cuota_ded, n_vistas = totales_pdf(casillas)
    comprobar("base devengado = solo casillas 1+4+7 (2,5,8 son el tipo, no base)",
              base_dev == 1000.0, f"base_dev={base_dev}")
    comprobar("cuota devengado = solo casillas 3+6+9",
              cuota_dev == 210.0, f"cuota_dev={cuota_dev}")
    comprobar("deducible = casillas 28 y 29 directas",
              base_ded == 500.0 and cuota_ded == 105.0)
    comprobar("cuenta cuantas casillas relevantes vio (5 en este caso)",
              n_vistas == 5, f"n_vistas={n_vistas}")
    comprobar("sin ninguna casilla reconocida, todo sale a cero y n_vistas=0",
              totales_pdf({})[:4] == (0.0, 0.0, 0.0, 0.0) and totales_pdf({})[4] == 0)

    # === C. comparar_caso() ==================================================
    print("\n=== C. comparar_caso() ===")
    contab_ok = (1000.0, 210.0, 500.0, 105.0, False)

    idéntico = (1000.0, 210.0, 500.0, 105.0, 5)
    comprobar("totales identicos -> CUADRA_EXACTO",
              comparar_caso(contab_ok, idéntico)["estado"] == "CUADRA_EXACTO")

    con_centimos = (1000.0, 210.3, 500.0, 105.0, 5)
    comprobar("30 centimos de diferencia -> CUADRA_CON_REDONDEO (tolerancia 1 EUR)",
              comparar_caso(contab_ok, con_centimos)["estado"] == "CUADRA_CON_REDONDEO")

    con_diferencia_grande = (1000.0, 210.0, 500.0, 200.0, 5)
    r_grande = comparar_caso(contab_ok, con_diferencia_grande)
    comprobar("95 EUR de diferencia en deducible -> NO_CUADRA",
              r_grande["estado"] == "NO_CUADRA", f"r={r_grande}")
    comprobar("y la diferencia exacta se reporta (95.0), no solo el veredicto",
              r_grande["max_diferencia"] == 95.0, f"r={r_grande}")

    comprobar("sin datos de contabilidad (None) -> NO_COMPROBADO, no un NO_CUADRA falso",
              comparar_caso(None, idéntico)["estado"] == "NO_COMPROBADO")

    sin_casillas = (0.0, 0.0, 0.0, 0.0, 0)
    comprobar("PDF sin ninguna casilla reconocida -> NO_COMPROBADO, no CUADRA por casualidad",
              comparar_caso(contab_ok, sin_casillas)["estado"] == "NO_COMPROBADO")

    contab_sucio = (1000.0, 210.0, 500.0, 105.0, True)
    r_sucio = comparar_caso(contab_sucio, idéntico)
    comprobar("el aviso de tipo_no_catalogado viaja hasta el resultado final",
              r_sucio.get("aviso_tipo_no_catalogado") is True, f"r={r_sucio}")

    # frontera exacta del umbral de redondeo
    en_el_limite = (1000.0, 211.0, 500.0, 105.0, 5)  # exactamente 1.00 de diferencia
    comprobar("una diferencia de EXACTAMENTE la tolerancia cuenta como redondeo, no como fallo",
              comparar_caso(contab_ok, en_el_limite, tolerancia=1.0)["estado"] == "CUADRA_CON_REDONDEO")
    pasado_el_limite = (1000.0, 211.01, 500.0, 105.0, 5)
    comprobar("una diferencia de 1.01 sobre una tolerancia de 1.00 ya es NO_CUADRA",
              comparar_caso(contab_ok, pasado_el_limite, tolerancia=1.0)["estado"] == "NO_CUADRA")

    # === D. leer_manifest() ==================================================
    print("\n=== D. leer_manifest() ===")
    import tempfile
    tmp = tempfile.mkdtemp()
    ruta_manifest = os.path.join(tmp, "prueba_LOCAL.txt")
    with open(ruta_manifest, "w", encoding="utf-8") as f:
        f.write("# comentario, se ignora\n")
        f.write("\n")
        f.write("CLAVE_A::SP_C_01|2025T1|C:\\ruta\\a.pdf\n")
        f.write("linea mal formada sin separadores\n")
        f.write("CLAVE_B::SP_C_02|2025T2|C:\\ruta\\b.pdf\n")
    casos = leer_manifest(ruta_manifest)
    comprobar("2 casos validos leidos, la linea mal formada se ignora (con aviso)",
              len(casos) == 2, f"casos={len(casos)}")
    comprobar("cada caso es la tupla (clave, trimestre, ruta) en orden",
              casos[0] == ("CLAVE_A::SP_C_01", "2025T1", "C:\\ruta\\a.pdf"), f"casos[0]={casos[0]}")
    os.remove(ruta_manifest)
    os.rmdir(tmp)

    # === E. Privacidad: main() nunca imprime clave ni ruta ==================
    print("\n=== E. Privacidad, comprobada por AST (no por ojo) ===")
    arbol = ast.parse(open(os.path.join(os.path.dirname(__file__),
                                         "verificar_303_pdf.py"), encoding="utf-8").read())
    main_fn = next(n for n in ast.walk(arbol)
                   if isinstance(n, ast.FunctionDef) and n.name == "main")
    nombres_impresos = set()
    for nodo in ast.walk(main_fn):
        if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                and nodo.func.id == "print"):
            for arg in ast.walk(nodo):
                if isinstance(arg, ast.Name):
                    nombres_impresos.add(arg.id)
    comprobar("ningun print() dentro de main() referencia 'clave' o 'ruta_pdf' "
              "directamente (los f-strings solo usan i, r['estado'] y numeros)",
              "clave" not in nombres_impresos and "ruta_pdf" not in nombres_impresos,
              f"nombres vistos en prints: {nombres_impresos}")

    print()
    print("=" * 68)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. La comparacion cuenta lo que hay, distingue "
          "redondeo de desacuerdo real, y nunca imprime una clave ni una ruta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
