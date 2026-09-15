#!/usr/bin/env python3
"""diag_orden_extraccion_pdf.py — por que una casilla con valor en el PDF sale
como "NO reconocida" en verificar_303_pdf.py, SIN QUE NI UN CARACTER de
contenido real (nombre, NIF, importe) salga nunca de esta maquina.

Nace de un caso real (SP_C_13, 2025T2): el 303 trae valor en la casilla 07,
pero extraer_casillas() no la encuentra. La hipotesis, segun los propios
comentarios de extraer_303_pdf.py (el impreso agrupa las casillas POR
COLUMNA -- BASE / TIPO / CUOTA -- no fila a fila), es que pdfplumber no
aplana el texto en el orden que extraer_numero_tras() asume (valor
INMEDIATAMENTE despues de su propia etiqueta, antes de la etiqueta
siguiente).

COMO SE MANTIENE SEGURO -- y esta vez de verdad, no con un "no lo leas":
la primera version de este script imprimia el texto del PDF con los importes
sustituidos por cifras falsas. Error: la pagina de identificacion de un 303
lleva el NIF y la razon social del cliente EN TEXTO PLANO, y esa version los
habria imprimido igual. Corregido antes de que nadie lo ejecutara.

Esta version no imprime NUNCA un fragmento de texto del documento -- ni
siquiera redactado. Solo mide, para cada etiqueta de casilla que ya usa el
proyecto (numero de recuadro impreso en TODOS los 303, igual en cualquier
cliente -- no identifica a nadie), DONDE esta el siguiente numero-con-forma-
de-importe y la siguiente etiqueta, en CARACTERES DE DISTANCIA. Eso basta
para saber si extraer_numero_tras() encuentra el valor de una casilla o si
otra etiqueta se cruza antes -- sin que ni un digito de un importe real, ni
una letra de un nombre, entren en la salida.

Uso (en local; la salida es segura de pegar tal cual):
    python diag_orden_extraccion_pdf.py "ruta\al\303 de un trimestre.pdf"
"""
import sys

from contrato_datos import RE_IMPORTE_EN_TEXTO
from extraer_303_pdf import (
    exigir_pdfplumber, patron_casilla, extraer_numero_tras,
    RE_ETIQUETA_CUALQUIERA, CASILLAS_DEVENGADO, CASILLAS_DEDUCIBLE,
    CASILLA_TOTAL_DEVENGADO, CASILLA_TOTAL_A_DEDUCIR, CASILLA_RESULTADO_GENERAL,
)

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

#: Solo casillas que ya conoce el proyecto -- ninguna nueva, ningun dato.
ETIQUETAS_A_MIRAR = tuple(dict.fromkeys(
    CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE
    + (12, 13, CASILLA_TOTAL_DEVENGADO, CASILLA_TOTAL_A_DEDUCIR, CASILLA_RESULTADO_GENERAL)
))


def analizar_etiqueta(texto, n):
    """Devuelve una lista de dicts, uno por cada vez que aparece la etiqueta
    de la casilla n en el texto. Cada dict es SOLO numeros y booleanos:
    nunca un fragmento de texto."""
    patron = patron_casilla(n)
    apariciones = []
    pos = 0
    while True:
        m = patron.search(texto, pos)
        if not m:
            break
        fin = m.end()
        m_imp = RE_IMPORTE_EN_TEXTO.search(texto, fin)
        m_etq = RE_ETIQUETA_CUALQUIERA.search(texto, fin)

        dist_importe = (m_imp.start() - fin) if m_imp else None
        dist_etiqueta = (m_etq.start() - fin) if m_etq else None
        etiqueta_corta_antes = (
            dist_etiqueta is not None
            and (dist_importe is None or dist_etiqueta < dist_importe)
        )
        encontrado_de_verdad = extraer_numero_tras(texto, fin) is not None

        apariciones.append({
            "distancia_a_siguiente_importe": dist_importe,
            "distancia_a_siguiente_etiqueta": dist_etiqueta,
            "una_etiqueta_se_cruza_antes_del_importe": etiqueta_corta_antes,
            "extraer_numero_tras_lo_encuentra": encontrado_de_verdad,
        })
        pos = fin
    return apariciones


def main():
    exigir_pdfplumber()
    if len(sys.argv) < 2:
        print("Uso: python diag_orden_extraccion_pdf.py \"ruta\\al\\303.pdf\"")
        sys.exit(1)

    ruta = sys.argv[1]
    with pdfplumber.open(ruta) as pdf:
        texto = "\n".join((p.extract_text() or "") for p in pdf.pages)

    print("=" * 70)
    print("DIAGNOSTICO ESTRUCTURAL -- ni un importe, ni un nombre, ni un NIF")
    print("Solo distancias en caracteres y booleanos. Seguro de pegar.")
    print("=" * 70)
    print(f"  longitud total del texto extraido: {len(texto)} caracteres")
    print()

    for n in ETIQUETAS_A_MIRAR:
        apariciones = analizar_etiqueta(texto, n)
        if not apariciones:
            print(f"  casilla {n:>3}: la ETIQUETA no aparece en el texto ni una vez")
            continue
        print(f"  casilla {n:>3}: etiqueta encontrada {len(apariciones)} vez(veces)")
        for i, a in enumerate(apariciones, 1):
            veredicto = "SI" if a["extraer_numero_tras_lo_encuentra"] else "NO"
            print(f"      aparicion {i}: extraer_numero_tras() encuentra un valor -> {veredicto}"
                  f" | distancia al siguiente importe: {a['distancia_a_siguiente_importe']}"
                  f" | distancia a la siguiente etiqueta: {a['distancia_a_siguiente_etiqueta']}"
                  f" | una etiqueta se cruza antes que el importe: {a['una_etiqueta_se_cruza_antes_del_importe']}")


if __name__ == "__main__":
    main()
