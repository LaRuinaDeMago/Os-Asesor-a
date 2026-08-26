#!/usr/bin/env python3
"""extraer_303_pdf.py — FASE 2a: extrae los numeros de casilla de verdad, y
se AUTO-VALIDA por consistencia interna antes de que nadie se fie de nada.

Reutiliza los patrones confirmados por reconocer_303_pdf.py (fase 1): "Casilla
NN" aparece en el 98-99% de los 1.168 PDF del modelo 303 encontrados.

COMO SE AUTO-VALIDA, SIN QUE NINGUN VALOR LLEGUE AL CHAT
---------------------------------------------------------
Para cada documento, una vez extraidas las casillas, se comprueban DOS cosas
que tienen que ser ciertas en un 303 real, cualquiera que sea el cliente:

  1. base(casilla) > cuota(casilla) en cada tramo de IVA devengado (01>03,
     04>06, 07>09) siempre que el tipo no sea 0%.
  2. cuota/base este cerca de un tipo de IVA legal conocido (4, 5, 10, 21%),
     con margen de redondeo.

Si estas dos cosas se cumplen en la gran mayoria de documentos, la extraccion
esta encontrando los numeros correctos, aunque nadie -- ni Claude, ni este
informe -- haya visto ni uno solo. Es la misma logica que ya uso
guard_aritmetica_base_tipo en el motor, aplicada aqui a la CONFIANZA en el
extractor, no a la factura.

QUE SIGUE SIN HACER: no cruza todavia contra 303_LOCAL.json ni compara con
la contabilidad. Eso es la fase 2b, y solo tiene sentido si este informe
sale limpio.

Uso:
    python extraer_303_pdf.py "RUTA_DE_DOCUMENTOS"
"""
import logging
import os
import re
import sys
from collections import Counter
from contrato_datos import RE_IMPORTE_EN_TEXTO, parse_numero

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # silencia el ruido de ToUnicode

try:
    import pdfplumber
except ImportError:
    print("Falta pdfplumber. Instalar con: pip install pdfplumber")
    sys.exit(1)

PATRON_NOMBRE = re.compile(
    r'303.{0,15}?(?P<trim>1|2|3|4|primer|segundo|tercer|cuarto)'
    r'[a-záéíóú°º]{0,4}\.?\s*trimestre.{0,5}?(?P<anio>20\d{2})',
    re.IGNORECASE
)
# TRIM_A_NUM vivia aqui y no lo usaba nadie: este script solo comprueba que el
# NOMBRE del fichero encaje con PATRON_NOMBRE, no extrae el trimestre. Era un
# resto de copiar el bloque. Quien si lo usa es cruzar_303_importes.py, que
# tiene el suyo. Quitado el 26-08-2026.

# ARREGLADO 26-08-2026: aqui vivia r'-?\d{1,3}(?:\.\d{3})*,\d{2}',
# que exige el punto de millar y por tanto leia "12345,67" como
# "345,67" -- un numero distinto, en silencio. El 47% de los importes
# del archivo real vienen sin separador, asi que este patron estaba
# corrompiendo casi la mitad de las lecturas. Es candidato serio a
# explicar parte del 1,2% de consistencia interna que se atribuyo
# entero a la rejilla del PDF. Ahora manda contrato_datos.py.
NUM_ES = RE_IMPORTE_EN_TEXTO
TIPOS_LEGALES = (0, 4, 5, 10, 21)
TOL_TIPO = 0.6   # puntos porcentuales de margen sobre el tipo legal mas cercano

# Casilla -> patron que la localiza. Se buscan variantes razonables porque no
# se ha visto ni un solo documento real: "Casilla 01", "01." al principio de
# linea/celda, o el numero solo seguido de espacio y luego un numero-moneda.
def patron_casilla(n):
    return re.compile(
        rf'(?:casilla\s*0?{n}\b|\b0?{n}\s*[.\)]|\[0?{n}\])',
        re.IGNORECASE
    )

CASILLAS_DEVENGADO = (1, 2, 3, 4, 5, 6, 7, 8, 9)
CASILLAS_DEDUCIBLE = (28, 29)


def _num_es_a_float(s):
    return parse_numero(s).valor


def extraer_numero_tras(texto, pos_inicio, ventana=80):
    """El primer numero con formato ES dentro de una ventana de caracteres
    despues de donde aparecio la etiqueta de la casilla."""
    trozo = texto[pos_inicio:pos_inicio + ventana]
    m = NUM_ES.search(trozo)
    return _num_es_a_float(m.group(0)) if m else None


def extraer_casillas(texto):
    valores = {}
    for n in CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE:
        patron = patron_casilla(n)
        m = patron.search(texto)
        if m:
            v = extraer_numero_tras(texto, m.end())
            if v is not None:
                valores[n] = v
    return valores


def main():
    raiz = os.path.abspath(sys.argv[1])

    total_303 = 0
    con_extraccion_minima = 0   # al menos una casilla devengado + 28/29
    docs_sanity = Counter()     # "todas_ok" / "alguna_mal" / "sin_tramos_para_probar"
    tramos_ok = 0
    tramos_mal = 0
    tramos_no_evaluables = 0
    casillas_encontradas = Counter()

    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() != ".pdf" or "303" not in n:
                continue
            ruta = os.path.join(dp, n)
            m_nombre = PATRON_NOMBRE.search(n)
            if not m_nombre:
                continue
            total_303 += 1

            try:
                with pdfplumber.open(ruta) as pdf:
                    texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
            except Exception:
                continue
            if len(texto.strip()) < 20:
                continue

            valores = extraer_casillas(texto)
            for n_casilla in valores:
                casillas_encontradas[n_casilla] += 1

            tiene_devengado = any(k in valores for k in CASILLAS_DEVENGADO)
            tiene_deducible = any(k in valores for k in CASILLAS_DEDUCIBLE)
            if tiene_devengado or tiene_deducible:
                con_extraccion_minima += 1

            # --- auto-validacion por consistencia interna --------------
            algun_tramo_probado = False
            doc_todo_bien = True
            for base_c, cuota_c in ((1, 3), (4, 6), (7, 9)):
                if base_c in valores and cuota_c in valores:
                    base_v, cuota_v = valores[base_c], valores[cuota_c]
                    if base_v == 0:
                        continue
                    algun_tramo_probado = True
                    tipo_efectivo = round(cuota_v / base_v * 100, 2) if base_v else None
                    ok_orden = (base_v >= cuota_v) or tipo_efectivo == 0
                    ok_tipo = tipo_efectivo is not None and any(
                        abs(tipo_efectivo - t) <= TOL_TIPO for t in TIPOS_LEGALES)
                    if ok_orden and ok_tipo:
                        tramos_ok += 1
                    else:
                        tramos_mal += 1
                        doc_todo_bien = False

            if not algun_tramo_probado:
                docs_sanity["sin_tramos_para_probar"] += 1
                tramos_no_evaluables += 1
            elif doc_todo_bien:
                docs_sanity["todos_los_tramos_ok"] += 1
            else:
                docs_sanity["algun_tramo_no_cuadra"] += 1

    print("=" * 70)
    print("EXTRACCION DE CASILLAS 303 -- FASE 2a (auto-validacion, sin cruzar)")
    print("=" * 70)
    print(f"  documentos 303 con nombre reconocido      : {total_303:,}")
    print(f"  con extraccion minima (>=1 casilla)       : {con_extraccion_minima:,}")
    print("")
    print("CASILLAS ENCONTRADAS (en cuantos documentos aparece cada una):")
    for n in CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE:
        c = casillas_encontradas.get(n, 0)
        pct = round(c * 100.0 / total_303, 1) if total_303 else 0
        print(f"    casilla {n:>2}: {c:>5,} / {total_303:,}  ({pct}%)")
    print("")
    print("AUTO-VALIDACION POR CONSISTENCIA (base>=cuota Y tipo efectivo legal,")
    print("por CADA tramo devengado que tenga los dos numeros -- nunca se ve")
    print("el valor, solo si la relacion entre ellos es la esperada):")
    print(f"    tramos que SI cuadran      : {tramos_ok:,}")
    print(f"    tramos que NO cuadran      : {tramos_mal:,}")
    print(f"    tramos sin datos que probar: {tramos_no_evaluables:,}")
    total_tramos = tramos_ok + tramos_mal
    if total_tramos:
        print(f"    >> tasa de consistencia: {round(tramos_ok*100.0/total_tramos,1)}%")
    print("")
    print("POR DOCUMENTO:")
    for k, n in docs_sanity.most_common():
        print(f"    {k:<28} {n:>5,}")
    print("")
    print("Si 'tasa de consistencia' es alta (>95%), la extraccion es fiable")
    print("y toca la fase 2b: cruzar contra 303_LOCAL.json. Si no, hay que")
    print("revisar los patrones de casilla antes de comparar nada.")


if __name__ == "__main__":
    main()
