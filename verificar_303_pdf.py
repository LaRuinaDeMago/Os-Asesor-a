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
pero el nombre debe llevar `_LOCAL`). Admite dos formas de linea:

    CLAVE_CLIENTE|CARPETA_DEL_CLIENTE      <- la recomendada
    CLAVE_CLIENTE|TRIMESTRE|RUTA_AL_PDF    <- un caso suelto

Por ejemplo (con datos inventados, nunca reales):
    CARPETA_X::SP_C_10|\\\\PC01\\Documentos\\CLIENTE_INVENTADO
    CARPETA_X::SP_C_10|2025T1|C:\\ruta\\al\\303_1T2025.pdf

**Usa la primera siempre que puedas.** La de tres campos se paga POR
TRIMESTRE (buscar el PDF, copiar la ruta, escribir la linea): diez anios de
un cliente son 40 lineas a mano. La de dos se paga POR CLIENTE, que es donde
esta el trabajo de verdad -- abrir ContaPlus y ver que empresa es `SP_C_10`
--, y eso se hace una vez y ya esta. Del trimestre se encarga el script: lo
lee del nombre del fichero, con el patron que ya se peleo con los 1.168 PDF
reales del archivo (`trimestre_del_nombre`, en cruzar_303_importes.py).

Antes de la pasada larga conviene una en seco, que no abre ni un PDF:
    python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt --solo-expandir

Este script LEE ese fichero, pero NUNCA imprime su contenido: por consola
solo salen recuentos, etiquetas de trimestre y diferencias en EUROS (ninguna
de las tres identifica a nadie). Cada caso se refiere por su POSICION en el
manifest ("caso 1", "caso 2"...) y cada linea por la suya ("entrada 1"),
nunca por su clave, su carpeta ni su ruta.

Uso:
    python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt
    python verificar_303_pdf.py --manifest verificacion_303_LOCAL.txt --json 303_LOCAL.json
"""
import argparse
import json
import os
import re
import sys

import logging
logging.getLogger("pdfminer").setLevel(logging.ERROR)

from extraer_303_pdf import (extraer_casillas, CASILLAS_DEVENGADO, CASILLAS_DEDUCIBLE,
                              localizar_valor_casilla,
                              CASILLAS_PARA_CUADRE, CASILLAS_PARA_AVISOS,
                              veredicto_lectura, conceptos_que_no_podemos_tener,
                              BASES_DEVENGADO, BASES_DEDUCIBLE)
#: NO se reescribe el reconocimiento de trimestre por nombre de fichero: ya
#: existe, y ya se peleo con el archivo real. `cruzar_303_importes.py` lo
#: amplio el 26-08-2026 porque el patron estricto dejaba fuera 145 de los
#: 1.168 ficheros (12%) por escribir "2T" en vez de "2 trimestre". Escribir
#: aqui una cuarta version seria repetir el error de los TRES regex de
#: importes, todos mal y en silencio (ver comentario en ese mismo fichero).
from cruzar_303_importes import trimestre_del_nombre

#: Casillas "oficiales" del 303 que ESTE script no modela (ISP, y los totales
#: que la AEAT ya agrega por su cuenta) pero que sirven para EXPLICAR una
#: diferencia en vez de dejarla como un misterio. Anadido 11-09-2026, caso
#: real (SP_C_13, 2025T2): la diferencia en devengado Y en deducible
#: coincidia EXACTA con el importe de ISP (casillas 12/13) -- una vez fuera
#: el bug del "tipo 0 fantasma", lo unico que quedaba sin explicar era
#: exactamente eso, ni un centimo mas.
CASILLA_ISP_BASE = 12
CASILLA_ISP_CUOTA = 13
CASILLA_TOTAL_DEVENGADO = 27
CASILLA_TOTAL_A_DEDUCIR = 45

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

    Devuelve (base_dev, cuota_dev, base_ded, cuota_ded, tiene_no_catalogado,
    liquidacion_excluida).

    EL TIPO "0" NO SE SUMA AL TOTAL. Mismo hallazgo y mismo motivo que ya
    tiene `cuadre_303_ficha.py` (commit 6b2acb2, 14-09-2026,
    `diag_patron_cierre_iva.py` + `diag_contrapartida_tipo0.py` sobre el
    corpus real): en el 91,3% de los casos su cuota cancela casi exacto el
    resto del lado, y en el 72% su contrapartida es una cuenta
    administrativa (Hacienda o reclasificacion del propio grupo 477/472),
    nunca un tercero real -- es el asiento de liquidacion/cierre trimestral
    de IVA, no una venta ni una compra. Esta funcion tenia su PROPIA suma,
    separada de la de `cuadre_303_ficha.py`, y no habia recibido aquel
    arreglo -- reproducia el mismo "TOTAL siempre distorsionado" con datos
    reales (caso SP_C_13, 2025T2, 15-09-2026: la cuota_devengado y la
    cuota_deducible quedaban canceladas casi enteras por su propio tipo "0").

    Distinto de tipo_no_catalogado (que se queda DENTRO del total a
    proposito, porque podria ser una casilla real de tipo desconocido): el
    tipo "0" se EXCLUYE, pero nunca en silencio -- se devuelve en
    `liquidacion_excluida` (un dict con "devengado"/"deducible", cada uno
    {"base":.., "cuota":..}) para que el llamador lo declare, igual que
    `cuadre_303_ficha.py` imprime su propia linea "(fuera del TOTAL)".
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
        liquidacion = None
        for tipo, celda in lados.get(lado_nombre, {}).items():
            if tipo == "0":
                if celda.get("base") or celda.get("cuota"):
                    liquidacion = {"base": celda.get("base", 0.0),
                                   "cuota": celda.get("cuota", 0.0)}
                continue
            if tipo == "tipo_no_catalogado" and (celda.get("base") or celda.get("cuota")):
                no_catalogado = True
            base += celda.get("base", 0.0)
            cuota += celda.get("cuota", 0.0)
        return base, cuota, no_catalogado, liquidacion

    base_dev, cuota_dev, no_cat_dev, liq_dev = sumar("devengado")
    base_ded, cuota_ded, no_cat_ded, liq_ded = sumar("deducible")
    liquidacion_excluida = {}
    if liq_dev is not None:
        liquidacion_excluida["devengado"] = liq_dev
    if liq_ded is not None:
        liquidacion_excluida["deducible"] = liq_ded
    return (round(base_dev, 2), round(cuota_dev, 2),
            round(base_ded, 2), round(cuota_ded, 2),
            no_cat_dev or no_cat_ded, liquidacion_excluida)


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


#: Casillas "oficiales" (ver comentario junto a las constantes CASILLA_*):
#: se extraen con la misma logica de extraer_303_pdf.py, reutilizada, no
#: reescrita -- para que las dos lecturas nunca puedan divergir en silencio.
#: Ademas de las cuatro que ya se leian, TODAS las que hacen falta para
#: cuadrar el impreso contra su propia aritmetica (`veredicto_lectura`).
CASILLAS_OFICIALES = tuple(dict.fromkeys(
    (CASILLA_ISP_BASE, CASILLA_ISP_CUOTA,
     CASILLA_TOTAL_DEVENGADO, CASILLA_TOTAL_A_DEDUCIR)
    + CASILLAS_PARA_CUADRE + CASILLAS_PARA_AVISOS
    + BASES_DEVENGADO + BASES_DEDUCIBLE))


def extraer_casillas_oficiales(texto):
    valores = {}
    for n in CASILLAS_OFICIALES:
        v = localizar_valor_casilla(texto, n)
        if v is not None:
            valores[n] = v
    return valores


def _evaluar_ajuste_isp(diff_bruta, isp_valor, tolerancia):
    """Aplica un importe de ISP a UNA diferencia -- pero solo si hacia falta
    Y solo si de verdad AYUDA.

    ARREGLADO 15-09-2026, segunda confirmacion real sobre SP_C_13 (ya con el
    'tipo 0' y la casilla 07 arreglados): la version anterior le sumaba el
    ISP a los dos lados sin condicion. Eso tenia sentido cuando los dos lados
    necesitaban el mismo ajuste (el caso original, 11-09), pero al arreglar
    los otros dos bugs el devengado paso a cuadrar SOLO (diferencia 0,00) --
    y sumarle el ISP igualmente lo EMPEORABA, informando "quedan 420 EUR sin
    explicar" sobre un lado que ya estaba perfecto.

    REVISADO EL MISMO DIA, en la revision de rigor antes de empujar a
    origin: la guarda de arriba ("no aplicar si ya cuadraba") no bastaba.
    Con una diferencia bruta FUERA de tolerancia pero causada por un
    problema real SIN relacion con la ISP, sumar la ISP igual puede alejar
    el numero del cero en vez de acercarlo -- ejemplo (cifras inventadas,
    no del corpus): diferencia bruta de 50 EUR mas una ISP de 420 EUR daba
    "sigue sin explicar: 470 EUR", cuando el problema real era de 50, no de
    470. Ahora el ajuste solo se aplica si ADEMAS reduce la magnitud de la
    diferencia; si no ayuda, se declara la diferencia bruta tal cual, sin
    maquillarla ni empeorarla.

    Devuelve (resto, se_aplico_el_ajuste, explica)."""
    if abs(diff_bruta) <= tolerancia:
        return diff_bruta, False, True
    resto = round(diff_bruta + isp_valor, 2)
    if abs(resto) >= abs(diff_bruta):
        return diff_bruta, False, False
    return resto, True, abs(resto) <= tolerancia


def explicar_por_isp(diffs, oficiales, tolerancia):
    """¿La diferencia de devengado y/o deducible coincide con el importe de
    ISP (casillas 12/13) que este script no modela? Anadido tras el caso
    real SP_C_13 (2025T2, 11-09-2026): la diferencia en los dos lados
    coincidia EXACTA con la cuota de ISP declarada en el propio PDF. No es
    una regla inventada -- es la misma cuenta que ya hace cualquier asesor
    a mano: la autorrepercusion de ISP suma en devengado (casilla 13) y
    exactamente lo mismo en deducible (misma cuota, derecho a deduccion
    inmediata en el mismo periodo).

    AMPLIADO 15-09-2026 (misma sesion, segunda confirmacion real): ademas de
    la CUOTA (13), tambien se comprueba la BASE (12) -- el mismo mecanismo
    de doble apunte (477 y 472, autorrepercusion) mueve tanto la base como
    la cuota, y en SP_C_13 la base del deducible quedaba sin explicar por
    exactamente el importe de la base de ISP, sin que nada lo comprobara.

    Devuelve None si no hay NINGUNA casilla de ISP en el PDF (ni base ni
    cuota -- no se puede evaluar la hipotesis, y NO se finge que "no aporta"
    cuando es que no se ha mirado). Si hay alguna, devuelve un dict
    declarando cuanto explica ISP y cuanto queda SIN explicar en cada lado
    -- nunca oculta el resto, y nunca aplica el ajuste donde no hacia falta
    ni donde no ayuda (ver `_evaluar_ajuste_isp`)."""
    isp_cuota = oficiales.get(CASILLA_ISP_CUOTA)
    isp_base = oficiales.get(CASILLA_ISP_BASE)
    if isp_cuota is None and isp_base is None:
        return None

    resultado = {}

    #: `_evaluar_ajuste_isp` devuelve si el ajuste se APLICO (necesitaba Y
    #: ayudaba) -- la clave del dict se conserva como "hacia_falta" por
    #: compatibilidad con el resto del script y los ensayos, aunque el
    #: nombre de variable local de aqui en adelante ya dice lo que de verdad
    #: significa.
    if isp_cuota is not None:
        resto_dev, se_aplico_dev, explica_dev = _evaluar_ajuste_isp(
            diffs["cuota_devengado"], isp_cuota, tolerancia)
        resto_ded, se_aplico_ded, explica_ded = _evaluar_ajuste_isp(
            diffs["cuota_deducible"], isp_cuota, tolerancia)
        resultado.update({
            "isp_cuota_declarada": isp_cuota,
            "diferencia_devengado_sin_isp": resto_dev,
            "isp_explica_devengado": explica_dev,
            "isp_hacia_falta_devengado": se_aplico_dev,
            "diferencia_deducible_sin_isp": resto_ded,
            "isp_explica_deducible": explica_ded,
            "isp_hacia_falta_deducible": se_aplico_ded,
        })

    if isp_base is not None:
        resto_base_dev, se_aplico_base_dev, explica_base_dev = _evaluar_ajuste_isp(
            diffs["base_devengado"], isp_base, tolerancia)
        resto_base_ded, se_aplico_base_ded, explica_base_ded = _evaluar_ajuste_isp(
            diffs["base_deducible"], isp_base, tolerancia)
        resultado.update({
            "isp_base_declarada": isp_base,
            "diferencia_base_devengado_sin_isp": resto_base_dev,
            "isp_explica_base_devengado": explica_base_dev,
            "isp_base_hacia_falta_devengado": se_aplico_base_dev,
            "diferencia_base_deducible_sin_isp": resto_base_ded,
            "isp_explica_base_deducible": explica_base_ded,
            "isp_base_hacia_falta_deducible": se_aplico_base_ded,
        })

    return resultado


def comparar_contra_totales(contab, oficiales, tolerancia, casillas_todas=None):
    """Segunda comparacion, contra los TOTALES QUE EL PROPIO MODELO CALCULA:
    casilla 27 (total cuota devengada) y casilla 45 (total a deducir).
    Devuelve None si el PDF no trae esas dos casillas legibles.

    POR QUE HACE FALTA UNA SEGUNDA (14-09-2026, caso SP_C_13)
    -----------------------------------------------------------
    La comparacion principal enfrenta nuestra cuota devengada contra
    03+06+09, que es SOLO el regimen general ordinario. Pero nuestra
    reconstruccion suma TODO el 477 del trimestre, y en el 477 caben cosas
    que el 303 declara en OTRAS casillas:

      - inversion del sujeto pasivo -> casillas 12 (base) y 13 (cuota)
      - adquisiciones intracomunitarias -> casillas 10 y 11
      - modificaciones de bases y cuotas -> casillas 14 y 15
      - recargo de equivalencia -> casillas 16 a 26

    Ninguna de ellas esta en 03+06+09. Asi que para un cliente con ISP,
    nuestro devengado sale mas alto POR DISENO, y la resta da justo el
    importe de la ISP -- que es exactamente el sintoma medido en SP_C_13, al
    centimo y en los dos lados.

    OJO, Y ESTO CORRIGE UNA HIPOTESIS ANTERIOR: la ISP **no** cae en el
    cajon del "tipo 0". `reconstruir_303.py` lo dice en su propia cabecera
    -- deriva la base como cuota/tipo, y eso "arregla SOLO el caso ISP sin
    necesitar detectarlo: una linea 477 de autorrepercusion no tiene venta
    detras, se deriva de su propia cuota, como cualquier otra". La ISP se
    contabiliza con su tipo real (21%), en dos lineas, 477 y 472. El "tipo
    0" es otra cosa distinta: el asiento de liquidacion trimestral. Se
    propuso el 14-09 separarlos dentro de ese cajon; era innecesario,
    porque nunca estuvieron en el mismo.

    La casilla 27 SI las incluye todas (27 = 03+06+09+11+13+15+...), y la 45
    hace lo propio del lado deducible. Comparar contra ellas quita de golpe
    toda esa familia de diferencias, sin detectar nada ni clasificar nada.

    NO decide el veredicto, a proposito: se declara al lado del principal y
    Diego ve cual cuadra. Cambiar la comparacion que manda es una decision
    contable, no un detalle de implementacion."""
    if not oficiales:
        return None
    if casillas_todas is None:
        casillas_todas = oficiales
    cuota_dev_27 = oficiales.get(CASILLA_TOTAL_DEVENGADO)
    cuota_ded_45 = oficiales.get(CASILLA_TOTAL_A_DEDUCIR)
    if cuota_dev_27 is None or cuota_ded_45 is None:
        return None

    base_dev_c, cuota_dev_c, base_ded_c, cuota_ded_c, *_ = contab
    d_dev = round(cuota_dev_c - cuota_dev_27, 2)
    d_ded = round(cuota_ded_c - cuota_ded_45, 2)
    peor = max(abs(d_dev), abs(d_ded))
    resultado = {
        "diferencia_cuota_devengado": d_dev,
        "diferencia_cuota_deducible": d_ded,
        "max_diferencia": peor,
        "cuadra": peor <= tolerancia,
        "cuadra_exacto": peor < 0.005,
    }

    # --- Y LAS BASES (anadido 15-09-2026) -----------------------------
    # La mitad que faltaba. El desglose de un NO_CUADRA enseña cuatro
    # diferencias, y hasta hoy las dos de BASE se comparaban contra
    # 01+04+07: solo el regimen general ordinario, sin la base de la ISP
    # (casilla 12) ni la de las intracomunitarias (10). Exactamente el mismo
    # defecto que tenia la cuota antes de compararla contra la 27 -- y un
    # numero grande ahi manda a investigar un descuadre que no existe.
    #
    # DIFERENCIA DE FONDO, y por eso va en su propia clave: el 303 NO imprime
    # ningun total de bases. Esto no es una formula citada del impreso; es la
    # COLUMNA de bases, sumada por nosotros. Mejor que 01+04+07 sin discusion,
    # pero con menos respaldo que la 27 y la 45.
    bases_dev = [casillas_todas[c] for c in BASES_DEVENGADO if c in casillas_todas]
    bases_ded = [casillas_todas[c] for c in BASES_DEDUCIBLE if c in casillas_todas]
    if bases_dev or bases_ded:
        db_dev = round(base_dev_c - round(sum(bases_dev), 2), 2)
        db_ded = round(base_ded_c - round(sum(bases_ded), 2), 2)
        peor_base = max(abs(db_dev), abs(db_ded))
        resultado["bases"] = {
            "diferencia_base_devengado": db_dev,
            "diferencia_base_deducible": db_ded,
            "max_diferencia": peor_base,
            "cuadra": peor_base <= tolerancia,
            "casillas_leidas": len(bases_dev) + len(bases_ded),
        }
    return resultado


def comparar_caso(contab, pdf, tolerancia=TOLERANCIA_REDONDEO, oficiales=None):
    """Funcion PURA, sin E/S: compara los totales ya calculados de los dos
    lados. Separada de main() para poder probarla con datos sinteticos, sin
    necesitar un PDF real ni un 303_LOCAL.json real (mismo patron que
    ensayo_cruce_303.py usa con importes_del_pdf).

    contab: tupla de totales_contabilidad() (o None si no habia datos).
    pdf: tupla de totales_pdf().
    oficiales: dict de extraer_casillas_oficiales() (opcional). Si se pasa
    y hay una diferencia, se comprueba si el ISP declarado la explica --
    nunca AJUSTA el veredicto (una diferencia sigue siendo NO_CUADRA aunque
    se explique), solo declara la causa mas probable para no investigar a
    ciegas.

    Devuelve un dict con el veredicto y las diferencias, nunca un nombre."""
    if contab is None:
        return {"estado": "NO_COMPROBADO",
                "motivo": "no hay datos de contabilidad para esa clave+trimestre"}

    base_dev_c, cuota_dev_c, base_ded_c, cuota_ded_c, no_catalogado, *resto = contab
    liquidacion_excluida = resto[0] if resto else {}
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

    resultado = {
        "estado": estado,
        "diferencias": diffs,
        "max_diferencia": max_diff,
        "aviso_tipo_no_catalogado": no_catalogado,
    }
    if liquidacion_excluida:
        resultado["liquidacion_excluida"] = liquidacion_excluida

    if oficiales is not None and estado != "CUADRA_EXACTO":
        explicacion = explicar_por_isp(diffs, oficiales, tolerancia)
        if explicacion is not None:
            resultado["explicacion_isp"] = explicacion
        totales = comparar_contra_totales(contab, oficiales, tolerancia,
                                           casillas_todas=oficiales)
        if totales is not None:
            resultado["contra_totales_del_modelo"] = totales

    return resultado


#: El listado de cuadre_303_ficha.py escribe cada carpeta como
#: "{numero:>3}.{marca} {carpeta}", con marca=" (?)" o cuatro espacios. Si
#: se copia la linea entera del listado (lo natural, y lo que paso el
#: primer caso real: 11-09-2026) en vez de solo la clave, ese prefijo se
#: cuela en la CLAVE y ya no coincide con ninguna entrada de 303_LOCAL.json.
#: Se limpia aqui, en el unico sitio que lee el manifest.
_RE_PREFIJO_LISTADO = re.compile(r'^\s*\d+\.\s*(\(\?\))?\s*')


def _limpiar_campo(valor):
    """Quita comillas envolventes (lo que pone Windows en 'Copiar como ruta
    de acceso' si el nombre lleva espacios -- y una ruta de \\PC01\\Documentos
    casi siempre los lleva) y espacios de sobra. Sin esto, os.path.exists()
    busca un fichero cuyo nombre literalmente empieza y termina en '"', que
    no existe nunca -- el primer caso real (11-09-2026) fallo exactamente
    asi, con "el PDF indicado no existe" sobre una ruta real y correcta."""
    valor = valor.strip()
    if len(valor) >= 2 and valor[0] == valor[-1] and valor[0] in "\"'":
        valor = valor[1:-1].strip()
    return valor


def leer_manifest(ruta):
    """Cada linea no vacia ni comentario (#) admite DOS formas:

        CLAVE|TRIMESTRE|RUTA_PDF   un caso suelto (la de siempre)
        CLAVE|CARPETA              TODOS los trimestres de esa carpeta

    Devuelve siempre tuplas de tres. En la forma de carpeta, el trimestre
    es None y el tercer campo es la carpeta: expandir_entradas() las
    convierte en casos concretos. Nunca se imprime el contenido.

    POR QUE LA FORMA DE DOS CAMPOS (anadida 14-09-2026). La linea de tres
    se paga POR TRIMESTRE: localizar el PDF de 2025T3, copiar su ruta,
    escribirla. Diez anios de un cliente son 40 lineas a mano. Pero lo
    unico que de verdad cuesta -- abrir ContaPlus para ver que empresa es
    `SP_C_10` -- se paga POR CLIENTE, y una vez hecho esta hecho para
    siempre. Localizar el PDF de un trimestre es mecanico: la carpeta ya es
    la del cliente, y el nombre del fichero ya declara el trimestre (el
    archivo del despacho tiene una carpeta por cliente y dentro sus
    modelos de todos los anios -- ver carpeta_cliente() en
    cruzar_303_importes.py). Una linea por cliente, no una por trimestre.

    Las dos formas conviven a proposito: un manifest ya escrito sigue
    valiendo tal cual."""
    casos = []
    with open(ruta, encoding="utf-8") as f:
        for n_linea, linea in enumerate(f, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            partes = linea.split("|")
            if len(partes) not in (2, 3):
                print(f"AVISO: linea {n_linea} del manifest no tiene 2 ni 3 "
                      f"partes separadas por '|' -- se ignora.", file=sys.stderr)
                continue
            campos = [_limpiar_campo(p) for p in partes]
            clave = _RE_PREFIJO_LISTADO.sub("", campos[0])
            if len(campos) == 2:
                casos.append((clave, None, campos[1]))      # carpeta por expandir
            else:
                casos.append((clave, campos[1], campos[2]))  # caso suelto
    return casos


def pdfs_303_por_trimestre(carpeta):
    """Recorre `carpeta` y sus subcarpetas (el archivo suele llevar una por
    anio dentro de la del cliente) y agrupa por trimestre los PDF cuyo
    NOMBRE declara un modelo 303.

    Devuelve {'2025T1': [rutas...]}. La lista puede tener mas de un
    elemento: eso es una AMBIGUEDAD real (un original y una
    complementaria, o dos copias del mismo), y quien llama tiene que
    declararla, nunca elegir uno en silencio.

    No imprime nada: ni un nombre de carpeta, ni uno de fichero."""
    por_trimestre = {}
    for raiz, _dirs, ficheros in os.walk(carpeta):
        for nombre in ficheros:
            if not nombre.lower().endswith(".pdf") or "303" not in nombre:
                continue
            trimestre = trimestre_del_nombre(nombre)
            if trimestre is None:
                continue
            por_trimestre.setdefault(trimestre, []).append(
                os.path.join(raiz, nombre))
    return por_trimestre


def expandir_entradas(entradas, datos):
    """Convierte las entradas del manifest en casos concretos
    (clave, trimestre, ruta_pdf), expandiendo las de forma carpeta.

    Devuelve (casos, incidencias). Cada incidencia es (n_entrada, texto) y
    SOLO lleva numeros y etiquetas de trimestre -- nunca una clave, una
    carpeta ni un nombre de fichero.

    Un trimestre se expande unicamente si la contabilidad tiene ese
    trimestre para esa clave. Los que no, se CUENTAN y se declaran: un PDF
    de 2016 cuando la reconstruccion solo llega a 2021 no es un fallo, pero
    tampoco puede desaparecer sin que nadie lo sepa."""
    casos = []
    incidencias = []
    for n, (clave, trimestre, tercero) in enumerate(entradas, start=1):
        if trimestre is not None:
            casos.append((clave, trimestre, tercero))
            continue

        if not os.path.isdir(tercero):
            incidencias.append((n, "la carpeta indicada no existe o no es una carpeta"))
            continue

        trimestres_contables = set(datos.get(clave) or {})
        if not trimestres_contables:
            incidencias.append((n, "esa clave no aparece en el JSON de la "
                                   "contabilidad: revisa que sea la del listado"))
            continue

        por_trimestre = pdfs_303_por_trimestre(tercero)
        if not por_trimestre:
            incidencias.append((n, "no hay ningun PDF cuyo nombre declare un "
                                   "modelo 303 con trimestre y anio"))
            continue

        expandidos = ambiguos = sin_contabilidad = 0
        for tri in sorted(por_trimestre):
            rutas = por_trimestre[tri]
            if len(rutas) > 1:
                # Dos PDF que dicen ser el mismo trimestre. Elegir uno seria
                # inventarse cual es el bueno: se declara y se deja fuera.
                incidencias.append((n, f"{tri}: {len(rutas)} PDF distintos declaran "
                                       "ese mismo trimestre -- ambiguo, no se elige "
                                       "ninguno"))
                ambiguos += 1
                continue
            if tri not in trimestres_contables:
                sin_contabilidad += 1
                continue
            casos.append((clave, tri, rutas[0]))
            expandidos += 1

        resumen = f"expande a {expandidos} trimestre(s)"
        if sin_contabilidad:
            resumen += (f"; {sin_contabilidad} PDF sin contabilidad reconstruida "
                        "para ese trimestre (no se comparan)")
        if ambiguos:
            resumen += f"; {ambiguos} trimestre(s) ambiguo(s)"
        incidencias.append((n, resumen))
    return casos, incidencias


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", required=True,
                     help="Fichero LOCAL con lineas CLAVE|CARPETA (todos los "
                          "trimestres de esa carpeta) o CLAVE|TRIMESTRE|RUTA_PDF "
                          "(un caso suelto). Debe llevar _LOCAL en el nombre.")
    ap.add_argument("--json", default="303_LOCAL.json",
                     help="Detalle producido por reconstruir_303.py")
    ap.add_argument("--solo-expandir", action="store_true",
                     help="Enseña en que casos se expande el manifest y para. "
                          "No abre ni un PDF: sirve para comprobar que las "
                          "carpetas son las buenas antes de la pasada larga.")
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

    # exigir_pdfplumber() NO se llama todavia: --solo-expandir no abre
    # ningun PDF, y obligar a instalarlo para mirar si las carpetas estan
    # bien seria pedir una dependencia por un trabajo que no la usa -- el
    # mismo error que tenia extraer_303_pdf.py al salirse en el import.
    with open(args.json, encoding="utf-8") as f:
        datos = json.load(f)

    entradas = leer_manifest(args.manifest)
    if not entradas:
        print("El manifest no tiene ninguna entrada valida.", file=sys.stderr)
        sys.exit(1)

    casos, incidencias = expandir_entradas(entradas, datos)

    if incidencias:
        print("=" * 68)
        print("EXPANSION DEL MANIFEST (por numero de entrada, nunca por nombre)")
        print("=" * 68)
        for n, texto in incidencias:
            print(f"  entrada {n}: {texto}")
        print()

    if not casos:
        print("Ninguna entrada del manifest ha producido un caso comparable.",
              file=sys.stderr)
        sys.exit(1)

    if args.solo_expandir:
        print(f"{len(casos)} caso(s) saldrian de este manifest. "
              "Sin --solo-expandir se comparan de verdad.")
        return

    exigir_pdfplumber()

    print("=" * 68)
    print(f"VERIFICACION 303: {len(casos)} caso(s) a comparar "
          f"(de {len(entradas)} entrada(s) del manifest)")
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
        oficiales = extraer_casillas_oficiales(texto)
        pdf_totales = totales_pdf(casillas)
        r = comparar_caso(contab, pdf_totales, args.tolerancia, oficiales=oficiales)

        # ¿Se ha LEIDO bien este PDF? Se contesta con la aritmetica que el
        # propio impreso lleva escrita (27 = 03+06+09+11+13+..., 45 = 29+31+...,
        # 46 = 27-45), no con una heuristica sobre tipos de IVA. Va ANTES de
        # interpretar ningun descuadre: si la lectura esta mal, comparar
        # contra la contabilidad no significa nada.
        todas_las_casillas = {**casillas, **oficiales}
        estado_lectura, detalle_lectura = veredicto_lectura(todas_las_casillas)
        r["lectura_pdf"] = estado_lectura
        # .Declara este 303 algo que nuestra reconstruccion NO PUEDE contener?
        # Si es asi, el caso no puede cuadrar y no hay ningun bug detras.
        conceptos = conceptos_que_no_podemos_tener(todas_las_casillas)
        if conceptos:
            r["conceptos_no_modelados"] = conceptos
        resultados.append(r)

        if estado_lectura != "OK":
            marca = ("LECTURA DEL PDF EN DUDA" if estado_lectura == "NO_COMPROBADO"
                     else "LECTURA DEL PDF INCORRECTA")
            print(f"  caso {i}: [{marca}]")
            if estado_lectura == "NO_COMPROBADO":
                print("           no se ha podido leer ningun total del impreso "
                      "(casillas 27/45/46), asi que no hay nada contra que")
                print("           cuadrarlo. Esto NO es un aprobado.")
            for nombre, d in detalle_lectura.items():
                if not d["cuadra"]:
                    print(f"           {nombre}: el impreso dice {d['total_leido']:.2f} "
                          f"pero sus propios sumandos dan {d['suma_de_sumandos']:.2f} "
                          f"(difieren {d['diferencia']:.2f} EUR)")
            print("           -> el descuadre de abajo puede ser de LECTURA, no de "
                  "contabilidad. Mira este PDF antes que el asiento.")

        if r["estado"] == "NO_COMPROBADO":
            print(f"  caso {i}: NO_COMPROBADO -- {r['motivo']}")
        else:
            aviso = "  [tipo_no_catalogado presente]" if r.get("aviso_tipo_no_catalogado") else ""
            print(f"  caso {i}: {r['estado']}  (diferencia maxima: "
                  f"{r['max_diferencia']:.2f} EUR){aviso}")
            liq = r.get("liquidacion_excluida")
            if liq:
                for lado, vals in liq.items():
                    print(f"           (fuera del TOTAL de la contabilidad) tipo 0% en "
                          f"{lado}: base {vals['base']:.2f} / cuota {vals['cuota']:.2f} -- "
                          "probablemente el asiento de liquidacion de IVA a Hacienda, no")
                    print("           una venta o compra real (mismo hallazgo que "
                          "cuadre_303_ficha.py, 14-09-2026).")
            if r["estado"] == "NO_CUADRA":
                # Desglose por campo (solo numeros: base/cuota devengado y
                # deducible, nunca un nombre) -- para distinguir un fallo de
                # LECTURA del PDF (extraer_303_pdf.py ya midio 1,2% de
                # consistencia en formularios tabulares, ver su cabecera) de
                # un desacuerdo contable real. Y que casillas 1-9/28/29
                # reconocio el extractor, sin sus valores todavia -- si
                # faltan casillas centrales (04, 07...), la lectura fallo
                # antes de llegar a comparar nada.
                print(f"           desglose: base_devengado={r['diferencias']['base_devengado']:.2f}  "
                      f"cuota_devengado={r['diferencias']['cuota_devengado']:.2f}  "
                      f"base_deducible={r['diferencias']['base_deducible']:.2f}  "
                      f"cuota_deducible={r['diferencias']['cuota_deducible']:.2f}")
                vistas = sorted(casillas.keys())
                faltan = sorted(set(CASILLAS_DEVENGADO + CASILLAS_DEDUCIBLE) - casillas.keys())
                print(f"           casillas reconocidas en el PDF: {vistas}")
                print(f"           casillas NO reconocidas: {faltan}")
            totales = r.get("contra_totales_del_modelo")
            if totales:
                # Casillas y euros. Ni una clave, ni una ruta.
                veredicto = ("CUADRA EXACTO" if totales["cuadra_exacto"]
                             else "cuadra (dentro de tolerancia)" if totales["cuadra"]
                             else "tampoco cuadra")
                print(f"           contra los TOTALES del propio modelo "
                      f"(casillas 27 y 45): {veredicto}")
                print(f"             devengado 27: {totales['diferencia_cuota_devengado']:.2f}  "
                      f"deducible 45: {totales['diferencia_cuota_deducible']:.2f}")
                if totales["cuadra"]:
                    print("             -> la diferencia de arriba es de CASILLA, no de")
                    print("                contabilidad: 03+06+09 es solo el regimen general,")
                    print("                y el 477 del trimestre lleva ademas ISP (12/13),")
                    print("                intracomunitarias (11) o modificaciones (15).")
                b = totales.get("bases")
                if b:
                    estado_b = "cuadran" if b["cuadra"] else "NO cuadran"
                    print(f"           y las BASES contra su columna entera "
                          f"({b['casillas_leidas']} casillas leidas): {estado_b}")
                    print(f"             devengado: {b['diferencia_base_devengado']:.2f}  "
                          f"deducible: {b['diferencia_base_deducible']:.2f}")
                    print("             (el 303 no imprime ningun total de bases: esto es")
                    print("              la columna sumada por nosotros, no una formula suya)")
            conceptos = r.get("conceptos_no_modelados")
            if conceptos:
                print("           ESTE 303 DECLARA COSAS QUE NUESTRA RECONSTRUCCION "
                      "NO PUEDE TENER:")
                for c in conceptos:
                    casillas_txt = ", ".join(f"{n}={v:.2f}"
                                             for n, v in sorted(c["casillas"].items()))
                    print(f"             - {c['concepto']}  (casilla {casillas_txt} EUR)")
                    print(f"               {c['motivo']}")
                print("             -> mira esto ANTES de buscar un bug: sale solo de")
                print("                las cuentas 477/472 por tipo, y esto no vive ahi.")
            explicacion = r.get("explicacion_isp")
            if explicacion:
                def _linea_isp(lado, se_aplico, explica, resto):
                    if not se_aplico and explica:
                        print(f"           -> {lado} ya cuadraba SIN necesitar el ISP "
                              "(no se le aplica el ajuste)")
                    elif not se_aplico:
                        print(f"           -> {lado} sigue SIN explicar: {resto:.2f} EUR "
                              "(sumarle el ISP no acerca el numero a cero, asi que no se "
                              "le aplica)")
                    elif explica:
                        print(f"           -> explica ENTERA la diferencia en {lado}")
                    else:
                        print(f"           -> tras descontar ISP, queda SIN explicar en "
                              f"{lado}: {resto:.2f} EUR")

                if "isp_cuota_declarada" in explicacion:
                    print(f"           ISP declarado en el PDF (casilla 13, cuota): "
                          f"{explicacion['isp_cuota_declarada']:.2f} EUR "
                          "(no modelado por este script, se declara aparte)")
                    _linea_isp("devengado", explicacion["isp_hacia_falta_devengado"],
                               explicacion["isp_explica_devengado"],
                               explicacion["diferencia_devengado_sin_isp"])
                    _linea_isp("deducible", explicacion["isp_hacia_falta_deducible"],
                               explicacion["isp_explica_deducible"],
                               explicacion["diferencia_deducible_sin_isp"])
                if "isp_base_declarada" in explicacion:
                    print(f"           ISP declarado en el PDF (casilla 12, base): "
                          f"{explicacion['isp_base_declarada']:.2f} EUR "
                          "(no modelado por este script, se declara aparte)")
                    _linea_isp("base devengado", explicacion["isp_base_hacia_falta_devengado"],
                               explicacion["isp_explica_base_devengado"],
                               explicacion["diferencia_base_devengado_sin_isp"])
                    _linea_isp("base deducible", explicacion["isp_base_hacia_falta_deducible"],
                               explicacion["isp_explica_base_deducible"],
                               explicacion["diferencia_base_deducible_sin_isp"])

    print()
    print("=" * 68)
    print("RESUMEN (esto es lo UNICO que hace falta compartir)")
    print("=" * 68)
    exactos = sum(1 for r in resultados if r["estado"] == "CUADRA_EXACTO")
    redondeo = sum(1 for r in resultados if r["estado"] == "CUADRA_CON_REDONDEO")
    no_cuadran = sum(1 for r in resultados if r["estado"] == "NO_CUADRA")
    no_comprobados = sum(1 for r in resultados if r["estado"] == "NO_COMPROBADO")
    lectura_ok = sum(1 for r in resultados if r.get("lectura_pdf") == "OK")
    lectura_mal = sum(1 for r in resultados if r.get("lectura_pdf") == "FALLO")
    lectura_sin = sum(1 for r in resultados if r.get("lectura_pdf") == "NO_COMPROBADO")
    con_conceptos = sum(1 for r in resultados if r.get("conceptos_no_modelados"))
    print(f"  casos totales            : {len(resultados)}")
    print(f"  cuadran exacto           : {exactos}")
    print(f"  cuadran con redondeo (<= {args.tolerancia:.2f} EUR): {redondeo}")
    print(f"  NO cuadran               : {no_cuadran}")
    print(f"  no comprobados           : {no_comprobados}")
    print()
    print("  Y antes de interpretar nada de lo anterior -- .se ha leido bien el PDF?")
    print("  (el impreso cuadrado contra SU PROPIA aritmetica: 27, 45 y 46)")
    print(f"    lectura correcta         : {lectura_ok}")
    print(f"    lectura INCORRECTA       : {lectura_mal}")
    print(f"    sin poder comprobarla    : {lectura_sin}")
    if lectura_mal or lectura_sin:
        print("    -> un descuadre en esos casos puede ser del lector, no de la")
        print("       contabilidad. No los mezcles con los demas.")
    print()
    print(f"  Casos cuyo 303 declara conceptos que NO salen de las cuentas de")
    print(f"  IVA (prorrata, regularizaciones, recargo, importaciones): {con_conceptos}")
    if con_conceptos:
        print("    -> esos NO pueden cuadrar, y no es un defecto de nadie. Cada")
        print("       uno lleva arriba el detalle de que concepto y cuanto.")
    print()
    if no_cuadran:
        print("  Los casos que NO cuadran hay que investigarlos uno a uno --")
        print("  no ajustar nada hasta saber por que (SIGUIENTES_PASOS.md §4).")
    if no_cuadran == 0 and no_comprobados == 0:
        print("  Todos los casos comprobados cuadran. Es la primera medicion")
        print("  real contra la unica verdad externa del proyecto.")


if __name__ == "__main__":
    main()
