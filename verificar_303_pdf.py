#!/usr/bin/env python3
"""verificar_303_pdf.py -- FASE 2b: compara, numero contra numero, la
reconstruccion de `303_LOCAL.json` contra el 303 REAL presentado (PDF),
para los casos que Diego ya ha identificado a mano.

POR QUE ESTE, Y NO UN CRUCE AUTOMATICO
----------------------------------------
`cruzar_303_importes.py` ya intento resolver esto adivinando SOLO, sin
ayuda: que carpeta de `\\PC01\\Documentos` es que cliente. Fallo (solape
bajo, 27-08-2026) porque intentaba resolver dos problemas a la vez --
identidad Y aritmetica -- con una sola senal (el importe).

Este script NO intenta identidad. Diego ya la resolvio a mano, abriendo
ContaPlus, para un puñado de casos concretos (ver PENDIENTE.md §1). Lo
unico que hace este script es la resta: coge el total que ya calculo
`reconstruir_303.py` para una clave+trimestre CONCRETA que Diego senala, lo
compara contra lo que dice el PDF real de ESE mismo trimestre, y dice si
cuadra. Ninguna adivinanza de por medio.

REGLA DE DATOS -- disenio de tres roles, sin excepcion
----------------------------------------------------------
Diego mantiene un fichero MANIFEST (LOCAL, con la extension que quiera,
pero el nombre debe llevar `_LOCAL`) con una linea por caso:

    CLAVE_CLIENTE|TRIMESTRE|RUTA_AL_PDF

Por ejemplo (con datos inventados, nunca reales):
    CARPETA_X::SP_C_10|2025T1|C:\\ruta\\al\\303_1T2025.pdf

Este script LEE ese fichero, pero NUNCA imprime su contenido: por consola
solo salen recuentos y diferencias en EUROS (un numero no identifica a
nadie). Cada caso se refiere por su POSICION en el manifest ("caso 1",
"caso 2"...), nunca por su clave ni por su ruta.

Uso:
    python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt
    python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt --json 303_LOCAL.json
"""
import argparse
import json
import os
import sys

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from extraer_303_pdf import extraer_casillas, CASILLAS_DEVENGADO, CASILLAS_DEDUCIBLE

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Tolerancia por debajo de la cual una diferencia se considera redondeo,
#: no un desacuerdo real. 1 euro es generoso a proposito: lo que importa
#: aqui es no gastar la atencion de Diego en centimos de redondeo cuando
#: el objetivo es decidir si la CADENA de lectura es de fiar.
TOLERANCIA_REDONDEO = 1.00


def exigir_pdfplumber():
    if pdfplumber is None:
        print("Falta pdfplumber. Instalar con: pip install pdfplumber",
              file=sys.stderr)
        sys.exit(1)


def totales_contabilidad(datos, clave, trimestre):
    """Suma, del lado de la CONTABILIDAD (303_LOCAL.json), los totales
    devengado y deducible para una clave+trimestre. Devuelve None si no
    existe esa clave o trimestre (para que el llamador lo declare, en vez
    de comparar contra un cero que no significa nada).

    Devuelve (base_dev, cuota_dev, base_ded, cuota_ded, tiene_no_catalogado).
    """
    entrada = datos.get(clave)
    if entrada is None:
        return None
    lados = entrada.get(trimestre)
    if lados is None:
        return None

    def sumar(lado_nombre):
        base = cuota = 0.0
        no_catalogado = False
        for tipo, celda in lados.get(lado_nombre, {}).items():
            if tipo == "tipo_no_catalogado" and (celda.get("base") or celda.get("cuota")):
                no_catalogado = True
            base += celda.get("base", 0.0)
            cuota += celda.get("cuota", 0.0)
        return base, cuota, no_catalogado

    base_dev, cuota_dev, no_cat_dev = sumar("devengado")
    base_ded, cuota_ded, no_cat_ded = sumar("deducible")
    return (round(base_dev, 2), round(cuota_dev, 2),
            round(base_ded, 2), round(cuota_ded, 2),
            no_cat_dev or no_cat_ded)


def totales_pdf(casillas):
    """A partir de {n_casilla: valor} (lo que devuelve extraer_casillas),
    calcula los mismos cuatro totales que totales_contabilidad(), para que
    los dos lados se puedan restar directamente."""
    base_dev = sum(casillas.get(n, 0.0) for n in (1, 4, 7))
    cuota_dev = sum(casillas.get(n, 0.0) for n in (3, 6, 9))
    base_ded = casillas.get(28, 0.0)
    cuota_ded = casillas.get(29, 0.0)
    casillas_vistas = sum(1 for n in CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE if n in casillas)
    return round(base_dev, 2), round(cuota_dev, 2), round(base_ded, 2), round(cuota_ded, 2), casillas_vistas


def comparar_caso(contab, pdf, tolerancia=TOLERANCIA_REDONDEO):
    """Funcion PURA, sin E/S: compara los totales ya calculados de los dos
    lados. Separada de main() para poder probarla con datos sinteticos, sin
    necesitar un PDF real ni un 303_LOCAL.json real (mismo patron que
    ensayo_cruce_303.py usa con importes_del_pdf).

    contab: tupla de totales_contabilidad() (o None si no habia datos).
    pdf: tupla de totales_pdf().

    Devuelve un dict con el veredicto y las diferencias, nunca un nombre."""
    if contab is None:
        return {"estado": "NO_COMPROBADO",
                "motivo": "no hay datos de contabilidad para esa clave+trimestre"}

    base_dev_c, cuota_dev_c, base_ded_c, cuota_ded_c, no_catalogado = contab
    base_dev_p, cuota_dev_p, base_ded_p, cuota_ded_p, n_casillas_pdf = pdf

    if n_casillas_pdf == 0:
        return {"estado": "NO_COMPROBADO",
                "motivo": "no se reconocio ninguna casilla en el PDF"}

    diffs = {
        "base_devengado": round(base_dev_c - base_dev_p, 2),
        "cuota_devengado": round(cuota_dev_c - cuota_dev_p, 2),
        "base_deducible": round(base_ded_c - base_ded_p, 2),
        "cuota_deducible": round(cuota_ded_c - cuota_ded_p, 2),
    }
    max_diff = max(abs(v) for v in diffs.values())

    if max_diff < 0.005:
        estado = "CUADRA_EXACTO"
    elif max_diff <= tolerancia:
        estado = "CUADRA_CON_REDONDEO"
    else:
        estado = "NO_CUADRA"

    return {
        "estado": estado,
        "diferencias": diffs,
        "max_diferencia": max_diff,
        "aviso_tipo_no_catalogado": no_catalogado,
    }


def leer_manifest(ruta):
    """Cada linea no vacia ni comentario (#): CLAVE|TRIMESTRE|RUTA_PDF.
    Nunca se imprime el contenido -- solo se devuelve para procesarlo."""
    casos = []
    with open(ruta, encoding="utf-8") as f:
        for n_linea, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split("|")
            if len(partes) != 3:
                print(f"AVISO: linea {n_linea} del manifest no tiene 3 "
                      f"partes separadas por '|' -- se ignora.", file=sys.stderr)
                continue
            clave, trimestre, ruta_pdf = (p.strip() for p in partes)
            casos.append((clave, trimestre, ruta_pdf))
    return casos


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True,
                     help="Fichero LOCAL con lineas CLAVE|TRIMESTRE|RUTA_PDF. "
                          "Debe llevar _LOCAL en el nombre.")
    ap.add_argument("--json", default="303_LOCAL.json",
                     help="Detalle producido por reconstruir_303.py")
    ap.add_argument("--tolerancia", type=float, default=TOLERANCIA_REDONDEO,
                     help="Diferencia en euros por debajo de la cual se "
                          "considera redondeo, no desacuerdo (por defecto 1.00)")
    args = ap.parse_args()

    if "_LOCAL" not in os.path.basename(args.manifest):
        print("ERROR: --manifest debe contener _LOCAL en el nombre: lleva "
              "claves de cliente y rutas de fichero.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.manifest):
        print(f"ERROR: no encuentro {args.manifest}.", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.json):
        print(f"ERROR: no encuentro {args.json}. Generalo con reconstruir_303.py.",
              file=sys.stderr)
        sys.exit(1)

    exigir_pdfplumber()

    with open(args.json, encoding="utf-8") as f:
        datos = json.load(f)

    casos = leer_manifest(args.manifest)
    if not casos:
        print("El manifest no tiene ningun caso valido.", file=sys.stderr)
        sys.exit(1)

    print("=" * 68)
    print(f"VERIFICACION 303: {len(casos)} caso(s) en el manifest")
    print("=" * 68)

    resultados = []
    for i, (clave, trimestre, ruta_pdf) in enumerate(casos, start=1):
        contab = totales_contabilidad(datos, clave, trimestre)

        if not os.path.exists(ruta_pdf):
            resultados.append({"estado": "NO_COMPROBADO",
                                "motivo": "el PDF indicado no existe"})
            print(f"  caso {i}: NO_COMPROBADO -- el PDF indicado no existe")
            continue

        try:
            with pdfplumber.open(ruta_pdf) as pdf:
                texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
        except Exception as e:
            resultados.append({"estado": "NO_COMPROBADO",
                                "motivo": f"error abriendo el PDF ({type(e).__name__})"})
            print(f"  caso {i}: NO_COMPROBADO -- error abriendo el PDF "
                  f"({type(e).__name__})")
            continue

        casillas = extraer_casillas(texto)
        pdf_totales = totales_pdf(casillas)
        r = comparar_caso(contab, pdf_totales, args.tolerancia)
        resultados.append(r)

        if r["estado"] == "NO_COMPROBADO":
            print(f"  caso {i}: NO_COMPROBADO -- {r['motivo']}")
        else:
            aviso = "  [tipo_no_catalogado presente]" if r.get("aviso_tipo_no_catalogado") else ""
            print(f"  caso {i}: {r['estado']}  (diferencia maxima: "
                  f"{r['max_diferencia']:.2f} EUR){aviso}")

    print()
    print("=" * 68)
    print("RESUMEN (esto es lo UNICO que hace falta compartir)")
    print("=" * 68)
    exactos = sum(1 for r in resultados if r["estado"] == "CUADRA_EXACTO")
    redondeo = sum(1 for r in resultados if r["estado"] == "CUADRA_CON_REDONDEO")
    no_cuadran = sum(1 for r in resultados if r["estado"] == "NO_CUADRA")
    no_comprobados = sum(1 for r in resultados if r["estado"] == "NO_COMPROBADO")
    print(f"  casos totales            : {len(resultados)}")
    print(f"  cuadran exacto           : {exactos}")
    print(f"  cuadran con redondeo (<= {args.tolerancia:.2f} EUR): {redondeo}")
    print(f"  NO cuadran               : {no_cuadran}")
    print(f"  no comprobados           : {no_comprobados}")
    print()
    if no_cuadran:
        print("  Los casos que NO cuadran hay que investigarlos uno a uno --")
        print("  no ajustar nada hasta saber por que (SIGUIENTES_PASOS.md §4).")
    if no_cuadran == 0 and no_comprobados == 0:
        print("  Todos los casos comprobados cuadran. Es la primera medicion")
        print("  real contra la unica verdad externa del proyecto.")


if __name__ == "__main__":
    main()
