#!/usr/bin/env python3
"""reconocer_303_pdf.py — FASE 1 (reconocimiento): ?el texto de los PDF del
303 tiene la forma esperada, antes de intentar extraer un solo numero?

NO EXTRAE NINGUN VALOR TODAVIA. Solo comprueba, por PRESENCIA, que patrones
de texto aparecen en cada documento -- para calibrar la fase 2 (extraccion
real) contra patrones ya confirmados, en vez de adivinar a ciegas.

QUE HACE
--------
1. Busca ficheros cuyo nombre contenga "303" (case-insensitive).
2. Intenta parsear trimestre y anio del propio nombre de fichero (patron
   dado por Diego: "modelo 303 - 1er trimestre 2025", con variantes de
   ordinal/espaciado).
3. Extrae el texto de cada PDF con pdfplumber (biblioteca de codigo abierto,
   lectura mecanica de texto -- no interpreta ni "entiende" el documento).
4. Cuenta, en AGREGADO, cuantos documentos contienen cada patron candidato
   (numeros de casilla, etiquetas conocidas del modelo 303, formato de
   moneda espanol). Nunca imprime el texto extraido ni un valor concreto.

REGLA DE DATOS: ni un nombre de carpeta, ni un nombre de fichero completo
(mas alla de si matchea el patron de "modelo 303"), ni el texto de un PDF,
se imprime en ningun momento. Solo recuentos.

Uso:
    python reconocer_303_pdf.py "RUTA_DE_DOCUMENTOS"
"""
import os
import re
import sys
from collections import Counter

try:
    import pdfplumber
except ImportError:
    print("Falta pdfplumber. Instalar con: pip install pdfplumber")
    sys.exit(1)

# Ordinal en varias formas: 1er/1º/1o/primer, 2º/2do/segundo, etc. Flexible
# a proposito porque el nombre real puede variar de un fichero a otro.
PATRON_NOMBRE = re.compile(
    r'303.{0,15}?(?P<trim>1|2|3|4|primer|segundo|tercer|cuarto)'
    r'[a-záéíóú°º]{0,4}\.?\s*trimestre.{0,5}?(?P<anio>20\d{2})',
    re.IGNORECASE
)

TRIM_A_NUM = {"1": 1, "2": 2, "3": 3, "4": 4,
              "primer": 1, "segundo": 2, "tercer": 3, "cuarto": 4}

# Patrones candidatos a buscar EN EL TEXTO del PDF -- no se sabe de antemano
# cual de ellos aparece de verdad, por eso se prueban varios y se cuenta cada
# uno por separado.
PATRONES_TEXTO = {
    "'Casilla' (palabra suelta)": re.compile(r'\bcasilla\b', re.IGNORECASE),
    "numero de casilla '01' acotado": re.compile(r'(?<!\d)01(?!\d)'),
    "numero de casilla '03' acotado": re.compile(r'(?<!\d)03(?!\d)'),
    "numero de casilla '28' acotado": re.compile(r'(?<!\d)28(?!\d)'),
    "numero de casilla '29' acotado": re.compile(r'(?<!\d)29(?!\d)'),
    "'Base imponible'": re.compile(r'base\s+imponible', re.IGNORECASE),
    "'Cuota' (palabra suelta)": re.compile(r'\bcuota\b', re.IGNORECASE),
    "'IVA devengado'": re.compile(r'iva\s+devengado', re.IGNORECASE),
    "'IVA deducible'": re.compile(r'iva\s+deducible', re.IGNORECASE),
    "'Regimen general'": re.compile(r'r[eé]gimen\s+general', re.IGNORECASE),
    "'Resultado' (palabra suelta)": re.compile(r'\bresultado\b', re.IGNORECASE),
    "numero con formato moneda ES (1.234,56)":
        re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}'),
}


def main():
    raiz = os.path.abspath(sys.argv[1])
    if not os.path.isdir(raiz):
        print(f"No existe o no es una carpeta: (ruta dada por parametro)")
        sys.exit(1)

    total_pdfs = 0
    candidatos_303 = 0
    con_trimestre_parseado = 0
    con_texto_extraible = 0
    con_error_lectura = 0
    hits_patron = Counter()
    numeros_moneda_por_doc = Counter()   # cuantos docs tienen N numeros-moneda
    trimestres_vistos = Counter()        # solo (anio,trim) -- nunca cliente

    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() != ".pdf":
                continue
            total_pdfs += 1
            if "303" not in n:
                continue
            candidatos_303 += 1

            m = PATRON_NOMBRE.search(n)
            anio_trim = None
            if m:
                trim_raw = m.group("trim").lower()
                trim_num = TRIM_A_NUM.get(trim_raw)
                anio = int(m.group("anio"))
                if trim_num:
                    con_trimestre_parseado += 1
                    anio_trim = (anio, trim_num)
                    trimestres_vistos[anio_trim] += 1

            ruta = os.path.join(dp, n)
            try:
                with pdfplumber.open(ruta) as pdf:
                    texto = "\n".join(
                        (pagina.extract_text() or "") for pagina in pdf.pages)
            except Exception:
                con_error_lectura += 1
                continue

            if len(texto.strip()) < 20:
                continue
            con_texto_extraible += 1

            n_monedas = 0
            for etiqueta, patron in PATRONES_TEXTO.items():
                encontrados = patron.findall(texto)
                if encontrados:
                    hits_patron[etiqueta] += 1
                if etiqueta.startswith("numero con formato moneda"):
                    n_monedas = len(encontrados)
            numeros_moneda_por_doc[min(n_monedas, 20)] += 1  # tope 20 para el histograma

    print("=" * 70)
    print("RECONOCIMIENTO DE PDF DEL MODELO 303 (fase 1 -- nada se extrae aun)")
    print("=" * 70)
    print(f"  PDF totales encontrados                : {total_pdfs:,}")
    print(f"  con '303' en el nombre                  : {candidatos_303:,}")
    print(f"  con trimestre/anio parseado del nombre  : {con_trimestre_parseado:,}")
    print(f"  con texto extraible (>20 caracteres)    : {con_texto_extraible:,}")
    print(f"  con error al abrir/leer                 : {con_error_lectura:,}")
    print("")
    print("TRIMESTRES DISTINTOS VISTOS (anio, trimestre) -- solo la fecha,")
    print("nunca el cliente:")
    print(f"    {len(trimestres_vistos)} combinaciones (anio,trimestre) distintas")
    if trimestres_vistos:
        anios = sorted(set(a for a, t in trimestres_vistos))
        print(f"    rango de anios: {min(anios)}-{max(anios)}")
    print("")
    print("PATRONES ENCONTRADOS, POR DOCUMENTO (cuantos de los")
    print(f"{con_texto_extraible:,} documentos con texto contienen cada patron):")
    for etiqueta, n in hits_patron.most_common():
        pct = round(n * 100.0 / con_texto_extraible, 1) if con_texto_extraible else 0
        print(f"    {etiqueta:<42} {n:>5,} / {con_texto_extraible:,}  ({pct}%)")
    print("")
    print("NUMEROS CON FORMATO MONEDA POR DOCUMENTO (histograma, tope 20):")
    for n_monedas in sorted(numeros_moneda_por_doc):
        etiqueta = f"{n_monedas}+" if n_monedas == 20 else str(n_monedas)
        print(f"    {etiqueta:>4} numeros  ->  {numeros_moneda_por_doc[n_monedas]:>4,} documentos")


if __name__ == "__main__":
    main()
