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
    # NO se sale aqui. Corregido el 09-09-2026: un `sys.exit(1)` en el CUERPO
    # del modulo mata a cualquiera que lo importe, aunque no vaya a abrir un
    # PDF. Eso tenia desactivado a `ensayo_cruce_303.py` (11o auditor) en todo
    # clon sin pdfplumber — y ese ensayo, por su propio diseno, no lee ni un
    # PDF: sustituye `importes_del_pdf`. Un auditor apagado por una dependencia
    # que no usa es la version de "OK por omision" que este proyecto tiene
    # prohibida, con el color cambiado: un rojo que no significa nada.
    # La exigencia se traslada a `exigir_pdfplumber()`, en el punto donde de
    # verdad hace falta: al arrancar el script como programa.
    pdfplumber = None


def exigir_pdfplumber():
    """Corta la ejecucion si falta pdfplumber. Se llama al empezar main(), no
    al importar: importar el modulo para probar su logica tiene que seguir
    siendo posible sin la biblioteca de lectura de PDF."""
    if pdfplumber is None:
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

# REESCRITO 14-09-2026, Y ESTA VEZ CON EL DOCUMENTO DELANTE
# ----------------------------------------------------------
# El comentario que habia aqui decia la verdad y era el problema: "se buscan
# variantes razonables porque NO SE HA VISTO NI UN SOLO DOCUMENTO REAL". Las
# tres variantes que se adivinaron ("Casilla 01", "01.", "[01]") no son la
# forma real. En el 303 de la AEAT cada casilla es una REJILLA: un recuadro
# pequenio con el numero a dos digitos, y al lado el recuadro del valor. Al
# aplanar a texto queda asi (cifras inventadas):
#
#     07 9.999,99 08 21,00 09 2.099,99
#
# Ninguna de las tres variantes casa con ese "07". Pero `\b0?9\s*[.\)]` SI
# casaba con el "9." de DENTRO de "9.999,99" -- el punto de millar espanol es
# identico a la marca de una lista numerada. Medido antes de tocar nada: sobre
# esa linea, el extractor no encontraba la casilla 07, y se inventaba una
# casilla 02 = 99,99 y una casilla 09 = 999,99, leyendo trozos de los importes.
# No era imprecision: era ruido con forma de dato.
#
# Es candidato a explicar el "1,2% de consistencia interna" mucho mejor que la
# rejilla, que es la explicacion que se le dio en su dia sin haber visto el
# documento. (La otra mitad, el regex de importes que exigia el punto de
# millar, ya se corrigio el 26-08.)
#
# AVISO HONESTO SOBRE ESTE ARREGLO: se ha validado contra una RECONSTRUCCION
# del formulario (la forma de la rejilla, con cifras inventadas), no contra un
# PDF real -- en Cloud no hay ninguno, ni puede haberlo. Lo que dira si ha
# servido es la tasa de consistencia de este mismo script sobre el archivo
# real. Hasta esa medicion, esto es una hipotesis bien fundada, no un hecho.
def patron_casilla(n):
    #: La etiqueta de la rejilla lleva SIEMPRE dos digitos: "01", "07", "28".
    etiqueta = f"0{n}" if n < 10 else f"{n}"
    return re.compile(
        # "Casilla 07" (por si algun modelo o ejercicio lo escribe asi)
        rf'(?:casilla\s*0?{n}\b'
        # "[07]"
        rf'|\[0?{n}\]'
        # "07." / "7)" de una lista. Con dos guardas: que no venga pegado a un
        # digito o a un separador (estaria DENTRO de un importe) y que no le
        # siga otro digito ("9.999" quedaria dentro, "09. 1.234,56" no).
        rf'|(?<![\d.,])0?{n}\s*[.\)](?!\d)'
        # La forma REAL: la etiqueta suelta de la rejilla, aislada de todo
        # digito y de todo separador decimal o de millar.
        rf'|(?<![\d.,]){etiqueta}(?![\d.,])'
        rf')',
        re.IGNORECASE
    )


#: Cualquier etiqueta de casilla (2-3 digitos aislados). Marca donde TERMINA
#: el valor de la casilla anterior: en la rejilla, lo que hay entre una
#: etiqueta y la siguiente es el valor de la primera, y nada mas.
RE_ETIQUETA_CUALQUIERA = re.compile(r'(?<![\d.,])\d{2,3}(?![\d.,])')

CASILLAS_DEVENGADO = (1, 2, 3, 4, 5, 6, 7, 8, 9)
CASILLAS_DEDUCIBLE = (28, 29)

# ======================================================================
# EL CUADRE INTERNO: la aritmetica que el propio impreso lleva escrita
# ======================================================================
# ANADIDO 15-09-2026. Hasta hoy, la unica auto-validacion era heuristica:
# "cuota/base tiene que parecerse a un tipo legal". Eso da una tasa global
# que nadie sabe interpretar (el famoso 1,2%) y no dice NADA sobre un
# documento concreto: no distingue "este PDF se ha leido bien" de "este no".
#
# Pero el modelo 303 lleva sus propias sumas IMPRESAS al lado de cada total:
#
#   Total cuota devengada (152+167+03+155+06+09+11+13+15+158+170+18+21+24+26) -> 27
#   Total a deducir       (29+31+33+35+37+39+41+42+43+44)                     -> 45
#   Resultado regimen general (27 - 45)                                       -> 46
#
# Eso NO es una heuristica: es la definicion de la casilla, escrita por la
# AEAT en su propio documento. Si leemos bien el PDF, tiene que cumplirse al
# centimo. Si no se cumple, la lectura esta mal -- y lo sabemos POR ESE
# DOCUMENTO, sin compararlo con nada externo y sin saber de quien es.
#
# Es exactamente el mismo principio que ya usa guard_aritmetica_base_tipo en
# el motor, pero con la formula del impreso en vez de con un tipo de IVA.
#
# POR QUE SUMAR UN SUPERCONJUNTO ES SEGURO: las casillas 150-170 (tipos
# reducidos temporales) no existen en los modelos de ejercicios antiguos. En
# un PDF que no las lleve simplemente no se leen, cuentan como 0, y la suma
# sigue cuadrando. Al reves seria un problema; asi no.
# ----------------------------------------------------------------------
# LO ANTERIOR, VERIFICADO CONTRA EL IMPRESO OFICIAL — 15-09-2026
# ----------------------------------------------------------------------
# El corpus del despacho va de 2016 a 2026 y el modelo 303 ha cambiado en
# esos anios. Si la formula de la casilla 27 no fuera la misma en 2022 que
# hoy, `cuadre_interno()` daria FALLO sobre PDF perfectamente leidos.
#
# Comprobado, no supuesto: se descargaron los formularios oficiales de la
# AEAT y se leyo la formula IMPRESA en cada uno. No de un resumen -- de los
# bytes del PDF. (En una consulta anterior, ese mismo dia, un resumen
# automatico afirmo que la ISP soportada va a "las casillas 40-43", que en
# el impreso son otra cosa. Un resumen no es una fuente.)
#
#   2022  https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/
#           Manual/Practicos/IVA/IVA_2022/Imagenes/C7-mod303-4T_es_es.pdf
#   2023  .../IVA_2023/Imagenes/C9-mod303_es_es.pdf
#   2024  .../IVA_2024/Imagenes/Cap_9_303_es_es.pdf
#   2026  del formulario que maneja el despacho
#
#: Formula impresa de cada casilla-total, ano por ano, tal cual se leyo.
#: `ensayo_extraer_casillas.py` comprueba que lo que sumamos las cubre TODAS:
#: si alguien recorta las constantes de abajo, se pone en rojo.
FORMULAS_IMPRESAS_VERIFICADAS = {
    # La 27 solo CRECE: cada anio anade filas de tipos reducidos temporales.
    2022: {27: (3, 6, 9, 11, 13, 15, 18, 21, 24, 26)},
    2023: {27: (152, 3, 155, 6, 9, 11, 13, 15, 158, 18, 21, 24, 26)},
    2024: {27: (152, 167, 3, 155, 6, 9, 11, 13, 15, 158, 170, 18, 21, 24, 26)},
    2026: {27: (152, 167, 3, 155, 6, 9, 11, 13, 15, 158, 170, 18, 21, 24, 26)},
}
# ----------------------------------------------------------------------
# LAS TRES COLUMNAS DEL IMPRESO — leidas del formulario oficial
# ----------------------------------------------------------------------
# El impreso de 2022 agrupa las casillas POR COLUMNA en el propio PDF, y eso
# da la estructura completa sin interpretarla:
#
#   deducible  BASE   28 30 32 34 36 38 40
#   deducible  CUOTA  29 31 33 35 37 39 41 42 43 44   <- es la formula de la 45
#   devengado  CUOTA  03 06 09 11 13 15 18 21 24 26   <- es la formula de la 27
#   devengado  BASE   01 04 07 10 12 14 16 19 22 25
#   devengado  TIPO   02 05 08 17 20 23
#
# Confirmacion INDEPENDIENTE de las dos formulas: salen de la columna, no de
# la linea del total. Y de paso da lo que faltaba para comparar las BASES.
# El de 2024 anade los tripletes de tipos reducidos temporales, cada uno
# (base, tipo, cuota): 150/151/152, 165/166/167, 153/154/155, 156/157/158,
# 168/169/170.
BASES_DEVENGADO = (150, 165, 1, 153, 4, 7, 10, 12, 14, 156, 168, 16, 19, 22, 25)
BASES_DEDUCIBLE = (28, 30, 32, 34, 36, 38, 40)

#: Casillas que llevan un PORCENTAJE, no euros. Varias vienen PREIMPRESAS en
#: el formulario (4,00 / 10,00 / 21,00 / 1,75 / 0,50 / 1,40 / 5,20), asi que
#: cualquier logica que las trate como importe se equivoca en los 1.168 PDF.
CASILLAS_DE_TIPO = (2, 5, 8, 17, 20, 23, 151, 154, 157, 166, 169)

#: OJO, Y ES UNA DIFERENCIA DE FONDO CON LA 27 Y LA 45: el 303 **no imprime
#: ningun total de bases**. No hay una casilla "total base devengada". Asi que
#: BASES_DEVENGADO no es una formula citada del impreso: es la COLUMNA
#: entera, sumada por nosotros. Sigue siendo el conjunto correcto contra el
#: que comparar nuestra base reconstruida --y es muchisimo mejor que 01+04+07,
#: que deja fuera la ISP y las intracomunitarias-- pero su respaldo es la
#: estructura del impreso, no una linea que diga "= tal + tal". Se declara
#: aparte por eso.

#: La 45 NO ha cambiado: identica en 2022, 2023, 2024 y 2026.
#: La 46 tampoco: "Resultado regimen general (27 - 45)" en los cuatro.
FORMULA_45_VERIFICADA = (29, 31, 33, 35, 37, 39, 41, 42, 43, 44)

#: NO VERIFICADO: 2016-2021. La AEAT no publica esos formularios en la
#: biblioteca actual. Consecuencia si alguno tuviera una casilla que no
#: sumamos: `cuadre_interno()` diria FALLO sobre un PDF bien leido. Es un
#: error CONSERVADOR -- "no te fies de esta lectura" -- nunca un falso
#: verde. Si aparecen muchos FALLO concentrados en anios antiguos, es el
#: primer sitio donde mirar.
ANIOS_SIN_VERIFICAR = "2016-2021"

SUMANDOS_TOTAL_DEVENGADO = (152, 167, 3, 155, 6, 9, 11, 13, 15,
                             158, 170, 18, 21, 24, 26)
SUMANDOS_TOTAL_A_DEDUCIR = (29, 31, 33, 35, 37, 39, 41, 42, 43, 44)
CASILLA_TOTAL_DEVENGADO = 27
CASILLA_TOTAL_A_DEDUCIR = 45
CASILLA_RESULTADO_GENERAL = 46

#: Todas las que hacen falta para poder cuadrar el impreso consigo mismo.
CASILLAS_PARA_CUADRE = tuple(dict.fromkeys(
    SUMANDOS_TOTAL_DEVENGADO + SUMANDOS_TOTAL_A_DEDUCIR
    + (CASILLA_TOTAL_DEVENGADO, CASILLA_TOTAL_A_DEDUCIR, CASILLA_RESULTADO_GENERAL)))

#: Las que hacen falta para avisar de un concepto que no podemos tener
#: (ver CONCEPTOS_FUERA_DE_LAS_CUENTAS_DE_IVA, mas abajo). Casi todas estan
#: ya en el cuadre; 33 y 35 no, y sin leerlas el aviso de importaciones no
#: saltaria nunca.
CASILLAS_PARA_AVISOS = (33, 35)

#: Margen en euros. El impreso redondea a dos decimales en cada casilla, asi
#: que una suma de quince sumandos puede desviarse algun centimo sin que la
#: lectura este mal.
TOL_CUADRE = 0.05


# ======================================================================
# POR QUE UN CASO PUEDE NO CUADRAR SIN QUE HAYA NINGUN BUG
# ======================================================================
# ANADIDO 15-09-2026. `EMPEZAR_AQUI.md` lo dice desde el primer dia y es la
# frase mas importante de todo el cuadre del 303:
#
#     "no reconstruye un 303. Un 303 lleva prorrata, bienes de inversion,
#      intracomunitarias, ISP y compensacion de cuotas, y nada de eso se
#      deduce de las cuentas de IVA."
#
# Nuestra reconstruccion sale SOLO de las cuentas 477 y 472, agregadas por
# tipo de IVA. Hay casillas del 303 cuyo contenido no vive ahi: una
# regularizacion anual de prorrata no es una factura, y un recargo de
# equivalencia va a un tipo (5,20 / 1,75 / 1,40 / 0,50) que ni siquiera esta
# en el catalogo de TIPOS_LEGALES.
#
# Si una de esas casillas trae importe, el caso NO PUEDE cuadrar, y eso no es
# un defecto de nadie. Sin decirlo, Diego se pasa la tarde buscando un bug que
# no existe -- que es justo la friccion que hay que quitar.
#
# SE DECLARA COMO PISTA, NO COMO VEREDICTO. Que ContaPlus lleve o no cada uno
# de estos conceptos a las cuentas 477/472 es una pregunta empirica sobre el
# corpus, sin contestar todavia. Por eso el texto dice "mira esto antes de
# buscar un bug", nunca "esto explica la diferencia".
#
#   (casillas de CUOTA, nombre, por que no lo tenemos)
# Solo casillas de cuota: las de tipo (17, 20, 23, 157, 169...) llevan un
# porcentaje, y mirarlas daria un aviso en cualquier impreso preimpreso.
CONCEPTOS_FUERA_DE_LAS_CUENTAS_DE_IVA = (
    # CITA LITERAL de las instrucciones de la AEAT (consultadas 15-09-2026):
    # "Se hara constar el resultado de la regularizacion de las deducciones
    #  provisionales practicadas durante el ejercicio como consecuencia de la
    #  aplicacion del porcentaje definitivo de prorrata que corresponda. Se
    #  cumplimentara UNICAMENTE EN EL 4T O MES 12, o en los supuestos de cese
    #  de actividad."
    # Ese "unicamente en el 4T" es util de verdad: un cliente con prorrata
    # tiene los trimestres 1T, 2T y 3T perfectamente comparables. Solo el 4T
    # queda fuera de alcance.
    ((44,), "regularizacion por el porcentaje definitivo de prorrata",
     "ajuste anual, no un apunte de factura: no esta en el 472. Segun la AEAT "
     "solo se rellena en el 4T, asi que 1T/2T/3T de ese mismo cliente SI se "
     "pueden comparar"),
    ((43,), "regularizacion de bienes de inversion",
     "ajuste plurianual, no sale de las cuentas de IVA del trimestre"),
    ((42,), "compensaciones del Regimen Especial A.G. y P.",
     "no es una cuota de IVA soportada: no pasa por el 472"),
    ((41,), "rectificacion de deducciones",
     "puede no llevar contrapartida en el 472 del trimestre"),
    ((33, 35), "IVA de importaciones",
     "lo liquida la Aduana, y suele contabilizarse aparte del 472 corriente"),
    ((158, 170, 18, 21, 24, 26), "recargo de equivalencia",
     "sus tipos (5,20 / 1,75 / 1,40 / 0,50) no estan en TIPOS_LEGALES, "
     "asi que caen en tipo_no_catalogado"),
)


def conceptos_que_no_podemos_tener(casillas, umbral=0.005):
    """Casillas con importe que nuestra reconstruccion (477/472 por tipo) no
    puede contener. Devuelve una lista de dicts; vacia si no hay ninguna.

    Solo numeros de casilla, nombres de concepto y euros: nada identificable.
    """
    encontrados = []
    for numeros, nombre, motivo in CONCEPTOS_FUERA_DE_LAS_CUENTAS_DE_IVA:
        con_importe = {n: casillas[n] for n in numeros
                       if n in casillas and abs(casillas[n]) > umbral}
        if con_importe:
            encontrados.append({
                "concepto": nombre,
                "motivo": motivo,
                "casillas": con_importe,
                "importe_total": round(sum(con_importe.values()), 2),
            })
    return encontrados


def cuadre_interno(casillas):
    """Comprueba el impreso contra SU PROPIA aritmetica.

    `casillas`: dict {n: valor} como el que devuelve extraer_casillas(),
    ampliado con las casillas de CASILLAS_PARA_CUADRE.

    Devuelve un dict con una entrada por formula comprobable. Una formula
    solo se comprueba si el TOTAL se ha leido: sin el no hay nada contra que
    contrastar, y eso es NO_COMPROBADO, no un aprobado -- misma regla que el
    motor. Una casilla sumando que no aparece cuenta como 0, que es lo que
    vale una casilla vacia en el impreso.

    Nunca recibe ni devuelve nada identificable: numeros de casilla y euros.
    """
    resultado = {}

    for nombre, total_c, sumandos in (
            ("devengado", CASILLA_TOTAL_DEVENGADO, SUMANDOS_TOTAL_DEVENGADO),
            ("deducible", CASILLA_TOTAL_A_DEDUCIR, SUMANDOS_TOTAL_A_DEDUCIR)):
        if total_c not in casillas:
            continue
        suma = round(sum(casillas.get(c, 0.0) for c in sumandos), 2)
        diferencia = round(casillas[total_c] - suma, 2)
        resultado[nombre] = {
            "total_leido": casillas[total_c],
            "suma_de_sumandos": suma,
            "diferencia": diferencia,
            "cuadra": abs(diferencia) <= TOL_CUADRE,
        }

    if all(c in casillas for c in (CASILLA_TOTAL_DEVENGADO,
                                    CASILLA_TOTAL_A_DEDUCIR,
                                    CASILLA_RESULTADO_GENERAL)):
        esperado = round(casillas[CASILLA_TOTAL_DEVENGADO]
                         - casillas[CASILLA_TOTAL_A_DEDUCIR], 2)
        diferencia = round(casillas[CASILLA_RESULTADO_GENERAL] - esperado, 2)
        resultado["resultado_46"] = {
            "total_leido": casillas[CASILLA_RESULTADO_GENERAL],
            "suma_de_sumandos": esperado,
            "diferencia": diferencia,
            "cuadra": abs(diferencia) <= TOL_CUADRE,
        }

    return resultado


def veredicto_lectura(casillas):
    """Traduce cuadre_interno() a los tres estados del motor, para un
    documento concreto:

      OK             -> alguna formula del impreso se ha podido comprobar y
                        TODAS las comprobables cuadran. La lectura es buena.
      FALLO          -> alguna formula no cuadra. La lectura esta mal, y da
                        igual lo que diga la comparacion contra la
                        contabilidad: hay que mirar el PDF.
      NO_COMPROBADO  -> no se ha leido ningun total, asi que no hay nada que
                        cuadrar. NO es un aprobado.
    """
    c = cuadre_interno(casillas)
    if not c:
        return "NO_COMPROBADO", c
    if all(v["cuadra"] for v in c.values()):
        return "OK", c
    return "FALLO", c


def _num_es_a_float(s):
    return parse_numero(s).valor


def extraer_numero_tras(texto, pos_inicio, ventana=80):
    """El primer numero con formato ES despues de la etiqueta de la casilla,
    SIN PASAR de la siguiente etiqueta.

    El corte por la etiqueta siguiente (anadido 14-09-2026) no es un detalle:
    sin el, la ventana de 80 caracteres se comia las casillas de al lado, y
    eso pasa en los dos sentidos:

      - Una casilla VACIA se quedaba con el valor de la siguiente. En
        "01 02 4,00 03 ..." (los tramos del 4% y el 10% casi siempre vienen
        vacios) la casilla 01 leia 4,00 -- que ni siquiera es un importe, es
        el TIPO de la casilla 02.
      - Y peor: `contrato_datos` acepta el espacio como separador de millar
        (con razon: en el archivo real los hay). Asi que en
        "28 1.111,11 29 233,33" el lector veia "29 233,33" como UN numero,
        29.233,33 -- la etiqueta fundida con su propio valor. Cortar por la
        etiqueta siguiente lo deshace, porque el corte va antes que la lectura.
    """
    fin = pos_inicio + ventana
    m_etiqueta = RE_ETIQUETA_CUALQUIERA.search(texto, pos_inicio, fin)
    if m_etiqueta:
        fin = m_etiqueta.start()
    m = NUM_ES.search(texto, pos_inicio, fin)
    return _num_es_a_float(m.group(0)) if m else None


def localizar_valor_casilla(texto, n):
    """Busca el valor de la casilla n probando CADA aparicion de su etiqueta
    en el texto, en orden, hasta que una de ellas tenga un numero detras.

    Por que hace falta un bucle y no basta con la primera aparicion
    (encontrado 15-09-2026, caso real SP_C_13 2025T2, con el diagnostico
    hecho a ciegas: solo distancias en caracteres, nunca un importe): la
    etiqueta de una casilla es un numero de dos o tres digitos aislado, y ese
    mismo numero puede aparecer antes en el documento por pura coincidencia
    -- la formula que el propio impreso escribe junto al total ("...+ 06 + 09
    + 11 + 13..." contiene la etiqueta "06" suelta, identica a la de la
    casilla de verdad), una fecha, un codigo. Si la PRIMERA aparicion es una
    de esas coincidencias, no lleva ningun importe detras dentro de la
    ventana -- u otra etiqueta se cruza antes -- y quedarse solo con ella
    pierde el valor real que esta mas adelante, en la rejilla de verdad.
    Medido en el caso real: la casilla 07 (base del 21%, con dato) volvia
    NO_ENCONTRADA porque su primera aparicion en el texto no era la rejilla.

    Devuelve None solo si NINGUNA aparicion tiene un numero detras -- que es
    lo mismo que dice el impreso cuando la casilla esta en blanco.
    """
    patron = patron_casilla(n)
    pos = 0
    while True:
        m = patron.search(texto, pos)
        if not m:
            return None
        v = extraer_numero_tras(texto, m.end())
        if v is not None:
            return v
        pos = m.end()


def extraer_casillas(texto):
    valores = {}
    for n in CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE:
        v = localizar_valor_casilla(texto, n)
        if v is not None:
            valores[n] = v
    return valores


def main():
    exigir_pdfplumber()
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
