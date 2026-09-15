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
F. explicar_por_isp(): el caso real que la motivo -- SP_C_13, 2025T2
   (11-09-2026, cifras sinteticas equivalentes aqui): la diferencia en
   devengado Y en deducible coincidia EXACTA con la cuota de ISP del PDF.
   Declara lo que explica y lo que NO, nunca ajusta el veredicto.
G. leer_manifest(), regresion del primer caso real (14-09-2026): una ruta
   de \\PC01\\Documentos con espacios, copiada con "Copiar como ruta de
   acceso" de Windows, llega envuelta en comillas -- y una clave copiada
   del listado de cuadre_303_ficha.py entero (con el numero y el "(?)"
   delante) en vez de solo la carpeta. Las dos cosas pasaron a la vez en
   el manifest real de Diego. Sin este arreglo, os.path.exists() busca un
   fichero que empieza y termina en '"' -- no existe nunca, y el mensaje
   ("el PDF indicado no existe") no dice por que.

Uso:
    python ensayo_verificar_303_pdf.py
"""
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from verificar_303_pdf import (
    totales_contabilidad, totales_pdf, comparar_caso, leer_manifest,
    comparar_contra_totales,
    pdfs_303_por_trimestre, expandir_entradas,
    explicar_por_isp, CASILLA_ISP_CUOTA, CASILLA_ISP_BASE,
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

    # AÑADIDO 15-09-2026: el tipo "0" (asiento de liquidacion/cierre de IVA)
    # NO se suma al total -- mismo hallazgo y mismo arreglo que ya tiene
    # cuadre_303_ficha.py (commit 6b2acb2, FAMILIA G de ensayo_cuadre_ficha.py).
    # Sin esto, totales_contabilidad() tenia su PROPIA suma (nunca recibio
    # aquel arreglo) y reproducia el mismo "TOTAL cancelado" con datos reales:
    # caso SP_C_13 2025T2, cifras inventadas de la misma forma aqui.
    datos_con_liquidacion = {
        "CLAVE_TRES": {"2025T1": {
            "devengado": {"21": celda(6285.30, 1319.90),
                          "0": celda(0.0, -1319.90)},
            "deducible": {"21": celda(338.00, 70.98),
                          "0": celda(0.0, -70.98)},
        }},
    }
    r3 = totales_contabilidad(datos_con_liquidacion, "CLAVE_TRES", "2025T1")
    comprobar("la cuota devengada NO queda cancelada por el tipo '0'",
              r3[1] == 1319.90, f"cuota_devengado={r3[1]} (se cancelaria a 0,00 sin el arreglo)")
    comprobar("ni la cuota deducible",
              r3[3] == 70.98, f"cuota_deducible={r3[3]} (se cancelaria a 0,00 sin el arreglo)")
    comprobar("pero se declara aparte -- nunca desaparece en silencio",
              r3[5] == {"devengado": {"base": 0.0, "cuota": -1319.90},
                        "deducible": {"base": 0.0, "cuota": -70.98}},
              f"liquidacion_excluida={r3[5]}")

    # Un tipo "0" realmente vacio (base y cuota ambas 0) no es una liquidacion
    # de nada: no debe declararse como si lo fuera.
    datos_sin_liquidacion_real = {
        "CLAVE_CUATRO": {"2025T1": {
            "devengado": {"21": celda(100.0, 21.0), "0": celda(0.0, 0.0)},
            "deducible": {},
        }},
    }
    r4 = totales_contabilidad(datos_sin_liquidacion_real, "CLAVE_CUATRO", "2025T1")
    comprobar("un tipo '0' realmente vacio (base y cuota 0) no se declara",
              r4[5] == {}, f"liquidacion_excluida={r4[5]}")

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
    contab_ok = (1000.0, 210.0, 500.0, 105.0, False, {})

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

    contab_sucio = (1000.0, 210.0, 500.0, 105.0, True, {})
    r_sucio = comparar_caso(contab_sucio, idéntico)
    comprobar("el aviso de tipo_no_catalogado viaja hasta el resultado final",
              r_sucio.get("aviso_tipo_no_catalogado") is True, f"r={r_sucio}")

    contab_con_liquidacion = (1000.0, 210.0, 500.0, 105.0, False,
                               {"devengado": {"base": 0.0, "cuota": -50.0}})
    r_liq = comparar_caso(contab_con_liquidacion, idéntico)
    comprobar("la liquidacion excluida tambien viaja hasta el resultado final",
              r_liq.get("liquidacion_excluida") == {"devengado": {"base": 0.0, "cuota": -50.0}},
              f"r={r_liq}")
    comprobar("y si no hay liquidacion excluida, la clave ni aparece (no un {} vacio)",
              "liquidacion_excluida" not in comparar_caso(contab_ok, idéntico))

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

    # === F. explicar_por_isp() -- el caso real que lo motivo ================
    print("\n=== F. explicar_por_isp() (caso real SP_C_13, cifras equivalentes) ===")
    # Mismas magnitudes que el caso real: nuestra reconstruccion capta bien
    # el tramo 21% (1319.90 devengado, 70.98 deducible) pero el PDF real
    # trae ademas 420.00 de ISP en los dos lados, que este script no modela.
    diffs_caso_real = {
        "base_devengado": 0.0, "cuota_devengado": -420.0,
        "base_deducible": 0.0, "cuota_deducible": -420.0,
    }
    oficiales_caso_real = {CASILLA_ISP_CUOTA: 420.0}
    exp = explicar_por_isp(diffs_caso_real, oficiales_caso_real, 1.0)
    comprobar("con ISP=420 y diferencia=-420 en los dos lados, ISP explica AMBOS",
              exp["isp_explica_devengado"] and exp["isp_explica_deducible"], f"exp={exp}")
    comprobar("y el resto sin explicar es (casi) cero en los dos lados",
              abs(exp["diferencia_devengado_sin_isp"]) <= 1.0
              and abs(exp["diferencia_deducible_sin_isp"]) <= 1.0, f"exp={exp}")

    diffs_solo_devengado = {
        "base_devengado": 0.0, "cuota_devengado": -420.0,
        "base_deducible": 0.0, "cuota_deducible": -420.0 - 55.0,  # 55 EUR de mas, sin explicar
    }
    exp2 = explicar_por_isp(diffs_solo_devengado, oficiales_caso_real, 1.0)
    comprobar("si ISP NO explica un lado (quedan 55 EUR de mas), lo declara sin explicar",
              exp2["isp_explica_devengado"] and not exp2["isp_explica_deducible"],
              f"exp2={exp2}")
    comprobar("y el importe exacto que falta por explicar es 55.0, no se pierde",
              abs(exp2["diferencia_deducible_sin_isp"]) == 55.0, f"exp2={exp2}")

    comprobar("sin casilla de ISP en el PDF (None), no se finge una explicacion",
              explicar_por_isp(diffs_caso_real, {}, 1.0) is None)

    # AÑADIDO 15-09-2026: segunda confirmacion real sobre SP_C_13, ya con la
    # casilla 07 y el "tipo 0" arreglados. El devengado paso a cuadrar SOLO
    # (diferencia 0,00) mientras el deducible seguia necesitando el ISP --
    # la version anterior de explicar_por_isp() le sumaba el ISP a los DOS
    # lados sin condicion, y eso convertia un devengado ya perfecto en un
    # falso "420 EUR sin explicar". Cifras equivalentes al caso real.
    diffs_asimetrico = {
        "base_devengado": 0.16, "cuota_devengado": 0.0,   # YA cuadraba
        "base_deducible": -2000.0, "cuota_deducible": -420.0,  # seguia sin explicar
    }
    oficiales_con_base = {CASILLA_ISP_CUOTA: 420.0, CASILLA_ISP_BASE: 2000.0}
    exp3 = explicar_por_isp(diffs_asimetrico, oficiales_con_base, 1.0)
    comprobar("el devengado, que YA cuadraba, no se toca -- el ISP no se le aplica",
              exp3["isp_hacia_falta_devengado"] is False, f"exp3={exp3}")
    comprobar("y su diferencia sigue siendo la bruta (0.0), no 420 EUR de mas",
              exp3["diferencia_devengado_sin_isp"] == 0.0, f"exp3={exp3}")
    comprobar("sigue diciendo que el devengado esta explicado (trivialmente, ya cuadraba)",
              exp3["isp_explica_devengado"] is True, f"exp3={exp3}")
    comprobar("el deducible SI necesitaba el ajuste, y lo explica entero",
              exp3["isp_hacia_falta_deducible"] is True and exp3["isp_explica_deducible"] is True,
              f"exp3={exp3}")

    # Y la BASE: el mismo mecanismo, pero comprobando la casilla 12 en vez
    # de la 13. En el caso real, la base deducible quedaba sin explicar por
    # exactamente la base del ISP (2.000,00), y nada lo comprobaba antes.
    comprobar("la base del ISP tambien se declara",
              exp3.get("isp_base_declarada") == 2000.0, f"exp3={exp3}")
    comprobar("la base devengado (0.16, redondeo) no necesitaba el ajuste tampoco",
              exp3["isp_base_hacia_falta_devengado"] is False, f"exp3={exp3}")
    comprobar("la base deducible SI la explica entera la base del ISP",
              exp3["isp_base_hacia_falta_deducible"] is True
              and exp3["isp_explica_base_deducible"] is True, f"exp3={exp3}")
    comprobar("y su resto sin explicar es (casi) cero",
              abs(exp3["diferencia_base_deducible_sin_isp"]) <= 1.0, f"exp3={exp3}")

    # Solo hay casilla de BASE de ISP (12), sin cuota (13) legible: el
    # resultado no debe fingir claves de cuota que no se ha podido comprobar.
    exp4 = explicar_por_isp(diffs_asimetrico, {CASILLA_ISP_BASE: 2000.0}, 1.0)
    comprobar("con solo la base de ISP legible, no aparecen claves de cuota",
              "isp_cuota_declarada" not in exp4 and "isp_explica_devengado" not in exp4,
              f"exp4={exp4}")
    comprobar("pero si las de base",
              "isp_base_declarada" in exp4, f"exp4={exp4}")

    # comparar_caso() con oficiales: declara la explicacion, pero el
    # veredicto sigue siendo NO_CUADRA -- ISP no "arregla" el desacuerdo,
    # solo dice a que se debe.
    contab_caso_real = (1000.0, 1319.90, 500.0, 70.98, False)
    pdf_caso_real = (1000.0, 1319.90 + 420.0, 500.0, 70.98 + 420.0, 9)
    r_caso_real = comparar_caso(contab_caso_real, pdf_caso_real, 1.0, oficiales=oficiales_caso_real)
    comprobar("el veredicto SIGUE siendo NO_CUADRA aunque ISP explique todo -- "
              "declarar no es lo mismo que aprobar",
              r_caso_real["estado"] == "NO_CUADRA", f"r={r_caso_real}")
    comprobar("pero la explicacion de ISP viaja dentro del resultado",
              "explicacion_isp" in r_caso_real
              and r_caso_real["explicacion_isp"]["isp_explica_devengado"]
              and r_caso_real["explicacion_isp"]["isp_explica_deducible"],
              f"r={r_caso_real}")

    r_exacto_sin_oficiales = comparar_caso((1000.0, 100.0, 500.0, 50.0, False),
                                            (1000.0, 100.0, 500.0, 50.0, 9),
                                            1.0, oficiales=oficiales_caso_real)
    comprobar("si YA cuadra exacto, no hace falta explicacion (no se calcula de mas)",
              "explicacion_isp" not in r_exacto_sin_oficiales, f"r={r_exacto_sin_oficiales}")

    # === G. leer_manifest() -- regresion del primer caso real (14-09) =======
    print("\n=== G. leer_manifest(): comillas de Windows + linea de listado completa ===")
    import tempfile as _tempfile
    tmp2 = _tempfile.mkdtemp()
    ruta_manifest2 = os.path.join(tmp2, "prueba2_LOCAL.txt")
    # Exactamente la forma real: clave con "NNN. (?) " delante (copiada del
    # listado entero) y ruta entre comillas (Windows, "Copiar como ruta de
    # acceso", cuando el nombre lleva espacios -- que en \\PC01\Documentos
    # es casi siempre). Rutas y carpetas inventadas, nunca las reales.
    linea_real = ('348. (?) CARPETA_SINTETICA::SP_C_99|2025T2|'
                  '"C:\\ruta con espacios\\algo.pdf"')
    linea_sin_marca = '  5.     OTRA_CARPETA::SP_C_01|2025T1|C:\\sin_comillas\\ni_espacios.pdf'
    with open(ruta_manifest2, "w", encoding="utf-8") as f:
        f.write(linea_real + "\n")
        f.write(linea_sin_marca + "\n")
    casos2 = leer_manifest(ruta_manifest2)
    comprobar("la clave pierde el 'NNN. (?) ' del listado, no solo los espacios",
              casos2[0][0] == "CARPETA_SINTETICA::SP_C_99", f"clave={casos2[0][0]!r}")
    comprobar("la ruta pierde las comillas envolventes de Windows",
              casos2[0][2] == "C:\\ruta con espacios\\algo.pdf", f"ruta={casos2[0][2]!r}")
    comprobar("una carpeta sin marca '(?)' (solo espacios) tambien se limpia bien",
              casos2[1][0] == "OTRA_CARPETA::SP_C_01", f"clave2={casos2[1][0]!r}")
    comprobar("una ruta sin comillas no se rompe por limpiarla de mas",
              casos2[1][2] == "C:\\sin_comillas\\ni_espacios.pdf", f"ruta2={casos2[1][2]!r}")
    os.remove(ruta_manifest2)
    os.rmdir(tmp2)

    # === I. Contra los TOTALES del propio modelo (casillas 27 y 45) ========
    print("\n=== I. La segunda comparacion: casillas 27 y 45 ===")
    # EL PATRON DE SP_C_13, con cifras INVENTADAS. Nuestra reconstruccion suma
    # TODO el 477/472 del trimestre. El 303 reparte: el regimen general
    # ordinario en 03+06+09, y la ISP aparte, en 12/13. Asi que nuestro
    # devengado sale mas alto EXACTAMENTE la cuota de ISP -- y lo mismo del
    # lado deducible. No es un descuadre contable: es una diferencia de
    # casilla.
    ISP = 420.00
    cuota_general, cuota_ded_general = 1319.90, 70.98
    # contabilidad: (base_dev, cuota_dev, base_ded, cuota_ded, no_catalogado)
    contab = (0.0, cuota_general + ISP, 0.0, cuota_ded_general + ISP, False)
    # pdf 03+06+09 y 29: solo el regimen general
    pdf = (0.0, cuota_general, 0.0, cuota_ded_general, 4)
    oficiales = {12: 2000.00, 13: ISP,
                 27: cuota_general + ISP,      # el total SI incluye la ISP
                 45: cuota_ded_general + ISP}

    r = comparar_caso(contab, pdf, tolerancia=1.00, oficiales=oficiales)
    comprobar("contra 03+06+09 sigue saliendo NO_CUADRA (no se toca el veredicto)",
              r["estado"] == "NO_CUADRA", r["estado"])
    comprobar("y la diferencia es exactamente la ISP, en los dos lados",
              r["diferencias"]["cuota_devengado"] == ISP
              and r["diferencias"]["cuota_deducible"] == ISP,
              str(r["diferencias"]))
    t = r.get("contra_totales_del_modelo")
    comprobar("aparece la comparacion contra los totales del modelo", t is not None)
    comprobar("y contra las casillas 27 y 45 CUADRA EXACTO",
              t and t["cuadra_exacto"], str(t))

    # Un descuadre CONTABLE de verdad no lo tapa: si falta un apunte, falla
    # tambien contra el total. Esa es toda la diferencia entre las dos cosas.
    contab_mal = (0.0, cuota_general + ISP - 500.0, 0.0, cuota_ded_general + ISP, False)
    t_mal = comparar_contra_totales(contab_mal, oficiales, 1.00)
    comprobar("un descuadre real NO se tapa: contra el total tambien falla",
              t_mal and not t_mal["cuadra"], str(t_mal))

    comprobar("sin las casillas 27/45 legibles no se inventa la comparacion",
              comparar_contra_totales(contab, {12: 1.0, 13: ISP}, 1.00) is None)
    comprobar("ni cuando falta solo una de las dos",
              comparar_contra_totales(contab, {27: 1.0}, 1.00) is None)

    # --- LAS BASES, la mitad que faltaba (15-09-2026) -------------------
    # Mismo patron que la cuota: nuestra base devengada suma todo el 477, y
    # 01+04+07 es solo el regimen general. La base de la ISP esta en la 12.
    BASE_GENERAL, BASE_ISP = 6285.14, 2000.00
    contab_b = (BASE_GENERAL + BASE_ISP, cuota_general + ISP,
                2338.00, cuota_ded_general + ISP, False)
    oficiales_b = dict(oficiales)
    oficiales_b.update({1: BASE_GENERAL, 12: BASE_ISP, 28: 2338.00})
    t_b = comparar_contra_totales(contab_b, oficiales_b, 1.00,
                                  casillas_todas=oficiales_b)
    comprobar("aparece la comparacion de BASES", "bases" in t_b, str(t_b.keys()))
    comprobar("y contra la COLUMNA entera de bases cuadra (01 + 12, no solo 01)",
              t_b["bases"]["cuadra"], str(t_b["bases"]))
    comprobar("dice cuantas casillas de base ha llegado a leer",
              t_b["bases"]["casillas_leidas"] == 3, str(t_b["bases"]))

    # Y no tapa un descuadre real de base.
    contab_b_mal = (BASE_GENERAL + BASE_ISP - 900.0, cuota_general + ISP,
                    2338.00, cuota_ded_general + ISP, False)
    t_b_mal = comparar_contra_totales(contab_b_mal, oficiales_b, 1.00,
                                      casillas_todas=oficiales_b)
    comprobar("una base que falta de verdad sigue saliendo mal",
              not t_b_mal["bases"]["cuadra"], str(t_b_mal["bases"]))

    # Si el PDF no trae ninguna casilla de base legible, no se inventa nada.
    t_sin_bases = comparar_contra_totales(contab_b, oficiales, 1.00,
                                          casillas_todas={27: 1.0, 45: 1.0})
    comprobar("sin casillas de base leidas no se publica comparacion de bases",
              "bases" not in t_sin_bases, str(t_sin_bases))

    # === H. Manifest por CLIENTE, no por trimestre (14-09-2026) ============
    print("\n=== H. expandir_entradas(): una linea por cliente, no por trimestre ===")
    # POR QUE: la linea de tres campos se paga por TRIMESTRE (buscar el PDF,
    # copiar la ruta). Lo caro de verdad -- abrir ContaPlus para saber que
    # empresa es SP_C_10 -- se paga por CLIENTE y solo una vez. Diez anios de
    # un cliente eran 40 lineas a mano; ahora es una.
    import tempfile as _tf
    raiz = _tf.mkdtemp()
    carpeta_cliente = os.path.join(raiz, "CLIENTE_INVENTADO_SL")
    # Nombres de fichero con las variantes reales que ya documenta
    # cruzar_303_importes.py ("1er trimestre", "4T"). Carpeta y cliente
    # inventados, nunca los reales.
    ficheros = [
        ("2024", "MODELO 303-1\u00ba TRIMESTRE 2024.pdf"),
        ("2024", "MODELO 303-2\u00ba TRIMESTRE 2024.pdf"),
        ("2023", "MODELO 303 4T 2023.pdf"),            # sin contabilidad reconstruida
        ("2025", "modelo 303 - 1er trimestre 2025.pdf"),
        ("2025", "modelo 303 - 1er trimestre 2025 (copia).pdf"),  # -> ambiguo
        # CONTRASTE QUE DE VERDAD CONTRASTA (corregido el 14-09-2026 tras
        # sabotear el filtro): el fichero de prueba era "modelo 347 2024.pdf",
        # que ya se cae solo porque no lleva trimestre en el nombre -- asi que
        # la comprobacion pasaba aunque se quitara el filtro de "303". Un 349
        # SI es trimestral y se nombra igual, y en la carpeta de un cliente
        # conviven con el 303 los 111, 115, 130 y 349. Sin filtro se compararia
        # un 303 contra un 349, y 2024T1 ademas tiene contabilidad: crearia un
        # caso falso, no un hueco.
        ("otros", "MODELO 349-1\u00ba TRIMESTRE 2024.pdf"),  # trimestral, pero no es un 303
        ("otros", "resumen 303 sin periodo.pdf"),      # 303 sin trimestre legible
    ]
    for sub, nombre in ficheros:
        d = os.path.join(carpeta_cliente, sub)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, nombre), "w").close()   # vacios: solo se lee el NOMBRE

    por_tri = pdfs_303_por_trimestre(carpeta_cliente)
    comprobar("encuentra los PDF del 303 en SUBCARPETAS, no solo en la raiz",
              set(por_tri) == {"2024T1", "2024T2", "2023T4", "2025T1"},
              f"trimestres={sorted(por_tri)}")
    comprobar("otro modelo TRIMESTRAL (349) no se cuela por parecerse en el nombre",
              all("349" not in r for rutas in por_tri.values() for r in rutas),
              f"{[r for rutas in por_tri.values() for r in rutas if '349' in r]}")
    comprobar("un 303 sin trimestre legible en el nombre no entra (no se adivina)",
              all("sin periodo" not in r for rutas in por_tri.values() for r in rutas))
    comprobar("dos PDF del mismo trimestre quedan LOS DOS, para poder declararlo",
              len(por_tri["2025T1"]) == 2, f"2025T1={len(por_tri['2025T1'])}")

    clave = "CARPETA_SINTETICA::SP_C_10"
    datos_h = {clave: {"2024T1": {}, "2024T2": {}, "2025T1": {}}}
    casos_h, incid_h = expandir_entradas([(clave, None, carpeta_cliente)], datos_h)
    comprobar("una sola linea de manifest produce los casos de varios trimestres",
              len(casos_h) == 2, f"casos={len(casos_h)}")
    comprobar("y son exactamente los que tienen PDF Y contabilidad",
              sorted(c[1] for c in casos_h) == ["2024T1", "2024T2"],
              f"{sorted(c[1] for c in casos_h)}")
    texto_h = " ".join(t for _, t in incid_h)
    comprobar("un trimestre con contabilidad pero AMBIGUO no se compara a ciegas",
              all(c[1] != "2025T1" for c in casos_h) and "ambiguo" in texto_h, texto_h)
    comprobar("un PDF sin contabilidad reconstruida se CUENTA, no desaparece",
              "1 PDF sin contabilidad" in texto_h, texto_h)

    # La comprobacion que de verdad importa de esta familia.
    comprobar("las incidencias no filtran la carpeta, la clave ni un nombre de fichero",
              all(x not in texto_h for x in ("CLIENTE_INVENTADO_SL", clave, raiz,
                                              "SP_C_10", ".pdf")),
              texto_h)

    casos_mixto, _ = expandir_entradas(
        [(clave, "2021T3", "C:\\ruta\\suelta.pdf"), (clave, None, carpeta_cliente)],
        datos_h)
    comprobar("una linea de tres campos sigue pasando intacta (manifest ya escrito)",
              casos_mixto[0] == (clave, "2021T3", "C:\\ruta\\suelta.pdf"),
              f"{casos_mixto[0]}")

    _, incid_no = expandir_entradas([(clave, None, os.path.join(raiz, "NO_EXISTE"))], datos_h)
    comprobar("una carpeta que no existe se declara, no se ignora",
              "no existe" in incid_no[0][1], incid_no[0][1])
    _, incid_clave = expandir_entradas([("CLAVE_QUE_NO_ESTA", None, carpeta_cliente)], datos_h)
    comprobar("una clave que no esta en la contabilidad se declara con su motivo",
              "no aparece en el JSON" in incid_clave[0][1], incid_clave[0][1])

    import shutil as _shutil
    _shutil.rmtree(raiz)

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

    # AMPLIADO 14-09-2026: main() ya no es el unico sitio donde se compone
    # texto para consola. expandir_entradas() construye las incidencias, y
    # tiene a mano la clave y la carpeta -- justo lo que no puede salir.
    for nombre_fn, prohibidos in (("expandir_entradas", ("clave", "tercero")),
                                   ("pdfs_303_por_trimestre", ("nombre", "raiz"))):
        fn = next(n for n in ast.walk(arbol)
                  if isinstance(n, ast.FunctionDef) and n.name == nombre_fn)
        vistos = set()
        for nodo in ast.walk(fn):
            if (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name)
                    and nodo.func.id == "print"):
                for arg in ast.walk(nodo):
                    if isinstance(arg, ast.Name):
                        vistos.add(arg.id)
        comprobar(f"{nombre_fn}() no imprime {' ni '.join(prohibidos)}",
                  not (vistos & set(prohibidos)), f"nombres en prints: {vistos}")

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
