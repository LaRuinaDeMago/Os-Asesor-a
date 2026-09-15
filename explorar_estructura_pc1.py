#!/usr/bin/env python3
r"""explorar_estructura_pc1.py — la comprobacion de 20 minutos que decide el
tamano de "extrapolar el 303 a otros modelos (111/115/347/349...)".

DE DONDE SALE ESTO
--------------------
15-09-2026, revisando dos analisis externos del proyecto. Uno de ellos senalo
algo cierto y sin contestar: nadie ha mirado como esta organizada `\\PC01\
Documentos` por dentro, mas alla de los clientes ya tocados para el 303.

Hay una pista real y ya verificada en el propio historial: el commit 264b8b4
(14-09-2026) dice que `trimestre_del_nombre()` dejaba fuera 145 de 1.168
ficheros de modelo 303 por escribir "2T" en vez de "2 trimestre" -- y que en
la carpeta de un cliente conviven 111, 115, 130 y 349 con el mismo formato de
nombre. Eso confirma DOS cosas a la vez: los nombres de fichero no son
uniformes ni siquiera dentro de un solo modelo, y otros modelos SI viven
mezclados en las mismas carpetas que el 303 -- al menos en los clientes que
ya se han mirado.

Lo que no se sabe: si eso es la norma en TODA la carpeta, o solo en los
clientes que ya se tocaron para el 303. La pregunta decide el tamano del
trabajo: si son carpetas por cliente con nombres razonablemente parecidos,
emparejar modelo<->cliente<->periodo es casi mecanico. Si es un volcado
plano con nombres inconsistentes, es un proyecto del tamano del que ya se
resolvio hoy para el 303, multiplicado por cada modelo nuevo.

QUE HACE, Y POR QUE ES MAS SEGURO TODAVIA QUE reconocer_303_pdf.py
---------------------------------------------------------------------
Ese script (Fase 1 del 303) al menos ABRE cada PDF para buscar patrones de
texto. Este NO abre ningun fichero. Solo mira:
  - nombres de carpeta de primer nivel (nunca impresos, solo CONTADOS),
  - profundidad a la que vive cada fichero dentro de su carpeta de primer
    nivel (aplanado / con subcarpetas / mixto),
  - si el NOMBRE del fichero contiene un numero de modelo AEAT conocido,
  - si además contiene algo que parece un trimestre/periodo,
  - extension del fichero.

Nunca se imprime un nombre de carpeta, un nombre de fichero completo, ni una
ruta. Solo recuentos y porcentajes -- misma disciplina que
reconocer_303_pdf.py y diag_orden_extraccion_pdf.py.

Uso (en local, la salida es segura de pegar tal cual):
    python explorar_estructura_pc1.py "\\PC01\Documentos"
"""
import os
import re
import sys
from collections import Counter

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Modelos AEAT mas frecuentes en una gestoria pequenia. No pretende ser
#: exhaustiva -- es un primer barrido, ampliable si aparecen mas.
MODELOS_CONOCIDOS = (
    "036", "037", "100", "111", "115", "123", "130", "131", "180", "184",
    "190", "200", "202", "296", "303", "347", "349", "390",
)

#: ANADIDO 15-09-2026, sobre una revision externa que senalo esto con razon:
#: un certificado digital (FNMT, Sede Electronica...) NO es un documento, es
#: una CREDENCIAL de acceso en nombre de un cliente. Si algun dia un script
#: recorre PC1 en bloque para procesar documentos, esto no puede caer dentro
#: del mismo tratamiento que un PDF por descuido de que la extension no
#: coincide con ".pdf" -- tiene que quedar fuera, marcado, a proposito.
#: Se cuenta aqui, SIN abrir ni tocar el fichero, para que se vea desde la
#: primera pasada si hay alguno y cuantos.
EXTENSIONES_CREDENCIAL = (".pfx", ".p12", ".cer", ".crt", ".key", ".pem")

#: Un numero de 3 digitos aislado (no pegado a otro digito ni a una coma/
#: punto decimal) -- misma logica de "etiqueta aislada" que ya usa
#: extraer_303_pdf.py para las casillas del 303.
_RE_MODELO = {m: re.compile(rf'(?<!\d){m}(?!\d)') for m in MODELOS_CONOCIDOS}

#: ANADIDO 15-09-2026, tras una primera pasada real que solo reconocio el
#: 9,2% de los ficheros: version SUELTA del mismo patron, sin exigir que el
#: numero este aislado. Sirve para medir CUANTO estaba perdiendo el patron
#: estricto por numeros pegados a una fecha sin separador ("3032024.pdf").
#: Nunca sustituye al estricto -- se cuentan los dos, y la DIFERENCIA entre
#: ambos es el dato que importa, no ninguno de los dos por separado.
_RE_MODELO_SUELTO = {m: re.compile(re.escape(m)) for m in MODELOS_CONOCIDOS}

#: Y la hipotesis mas probable de por que "estricto" se queda corto: en
#: castellano lo normal no es nombrar el modelo por su numero, es nombrarlo
#: por lo que es -- "IVA trimestral", "retenciones alquiler". Esto NO
#: identifica el modelo exacto (ambiguo a proposito: "iva" puede ser 303 o
#: 390), es una SEGUNDA senal independiente para saber si el nombre lleva
#: informacion fiscal reconocible aunque no lleve el numero desnudo.
PALABRAS_FISCALES = re.compile(
    r'\biva\b|\birpf\b|retenci|alquiler|arrendamient|intracomunitari'
    r'|censal|pago\s*fraccionad|operaciones?\s*(con\s*)?terceros'
    r'|resumen\s*anual|sociedades|autonomo|declaraci[oó]n',
    re.IGNORECASE,
)

#: ANADIDO 15-09-2026: Diego comprobo a mano (busqueda de Windows sobre PC1,
#: sin que ningun nombre pasara por el chat) que unos 5.305 PDF contienen la
#: palabra "modelo". Senal fuerte -- es la forma habitual de referirse a un
#: impreso de la AEAT -- pero AMBIGUA a proposito: "modelo de contrato",
#: "modelo de carta" tambien la llevan. Se cuenta aparte, nunca se suma sin
#: mas a "con algo reconocible", para no inflar el numero con falsos
#: positivos que no son modelos presentados.
_RE_PALABRA_MODELO = re.compile(r'\bmodelo\b', re.IGNORECASE)

#: Trimestre o periodo en el nombre: "1T"/"2T"/"3T"/"4T", "1er/2do/3er/4to
#: trimestre", "mensual", o un mes con anio. Deliberadamente laxo: aqui solo
#: interesa saber SI hay algo con pinta de periodo, no cual exactamente.
_RE_PERIODO = re.compile(
    r'\b[1-4]\s*[tT]\b'
    r'|(?:primer|segundo|tercer|cuarto)\s*trimestre'
    r'|\btrimestre\b'
    r'|\bmensual\b'
    r'|\b(?:ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)[a-z]*\.?\s*20\d{2}\b',
    re.IGNORECASE,
)

_RE_ANIO = re.compile(r'\b20[0-3]\d\b')


def main():
    if len(sys.argv) < 2:
        print('Uso: python explorar_estructura_pc1.py "\\\\PC01\\Documentos"')
        sys.exit(1)

    raiz = os.path.abspath(sys.argv[1]) if not sys.argv[1].startswith("\\\\") else sys.argv[1]
    if not os.path.isdir(raiz):
        print("No existe o no es una carpeta (ruta dada por parametro)")
        sys.exit(1)

    # --- 1. Carpetas de primer nivel: cuantas hay, nunca como se llaman ---
    try:
        primer_nivel = [e for e in os.scandir(raiz) if e.is_dir()]
    except OSError as e:
        print(f"No se pudo listar la carpeta raiz: {type(e).__name__}")
        sys.exit(1)
    ficheros_sueltos_en_raiz = sum(1 for e in os.scandir(raiz) if e.is_file())

    n_carpetas_primer_nivel = len(primer_nivel)

    total_ficheros = 0
    extensiones = Counter()
    profundidad_por_carpeta = {}   # nombre de carpeta (NUNCA impreso) -> set de profundidades vistas
    ficheros_por_carpeta = Counter()  # idem, solo para el histograma final

    con_modelo_reconocido = Counter()   # modelo -> numero de ficheros
    total_con_algun_modelo = 0
    total_sin_ningun_modelo = 0
    con_periodo = 0
    con_modelo_y_periodo = 0
    con_anio = 0
    credenciales_encontradas = 0

    total_con_modelo_suelto = 0     # patron SIN exigir aislamiento
    total_con_palabra_fiscal = 0    # "iva", "retenciones", etc., sin numero
    con_algo_reconocible = 0        # modelo (estricto o suelto) O palabra fiscal
    sin_nada_reconocible = 0        # ni numero ni palabra -- el resto de verdad
    total_con_palabra_modelo = 0    # "modelo" literal -- ambigua, se cuenta aparte
    palabra_modelo_y_numero = 0     # "modelo" + un numero (estricto o suelto) a la vez
    palabra_modelo_sola = 0         # "modelo" SIN ningun numero junto -- el caso ambiguo de verdad

    for carpeta in primer_nivel:
        profundidad_por_carpeta[carpeta.path] = set()
        for dp, _, fns in os.walk(carpeta.path):
            profundidad = dp[len(carpeta.path):].count(os.sep)
            for n in fns:
                total_ficheros += 1
                ficheros_por_carpeta[carpeta.path] += 1
                profundidad_por_carpeta[carpeta.path].add(profundidad)

                ext = os.path.splitext(n)[1].lower() or "(sin extension)"
                extensiones[ext] += 1
                if ext in EXTENSIONES_CREDENCIAL:
                    credenciales_encontradas += 1

                modelos_en_este = [m for m in MODELOS_CONOCIDOS if _RE_MODELO[m].search(n)]
                if modelos_en_este:
                    total_con_algun_modelo += 1
                    for m in modelos_en_este:
                        con_modelo_reconocido[m] += 1
                else:
                    total_sin_ningun_modelo += 1

                modelo_suelto = any(_RE_MODELO_SUELTO[m].search(n) for m in MODELOS_CONOCIDOS)
                if modelo_suelto:
                    total_con_modelo_suelto += 1

                if _RE_PALABRA_MODELO.search(n):
                    total_con_palabra_modelo += 1
                    if modelos_en_este or modelo_suelto:
                        palabra_modelo_y_numero += 1
                    else:
                        palabra_modelo_sola += 1
                palabra_fiscal = bool(PALABRAS_FISCALES.search(n))
                if palabra_fiscal:
                    total_con_palabra_fiscal += 1
                if modelos_en_este or modelo_suelto or palabra_fiscal:
                    con_algo_reconocible += 1
                else:
                    sin_nada_reconocible += 1

                tiene_periodo = bool(_RE_PERIODO.search(n))
                tiene_anio = bool(_RE_ANIO.search(n))
                if tiene_periodo:
                    con_periodo += 1
                if tiene_anio:
                    con_anio += 1
                if modelos_en_este and tiene_periodo:
                    con_modelo_y_periodo += 1

    # --- Histograma de profundidad: aplanado (solo 0-1) vs anidado ---
    hist_profundidad = Counter()
    for path, profs in profundidad_por_carpeta.items():
        maxprof = max(profs) if profs else 0
        hist_profundidad[maxprof] += 1

    # --- Histograma de cuantos ficheros trae cada carpeta de primer nivel ---
    hist_tamano_carpeta = Counter()
    for path, n in ficheros_por_carpeta.items():
        cubo = ("0", "1-10", "11-50", "51-200", "201-1000", "1000+")[
            0 if n == 0 else 1 if n <= 10 else 2 if n <= 50 else 3 if n <= 200 else 4 if n <= 1000 else 5
        ]
        hist_tamano_carpeta[cubo] += 1

    print("=" * 70)
    print("ESTRUCTURA DE PC1 -- solo nombres y conteos, ningun fichero abierto")
    print("=" * 70)
    print(f"  carpetas de primer nivel (candidatas a 'un cliente')  : {n_carpetas_primer_nivel:,}")
    print(f"  ficheros SUELTOS en la raiz (fuera de cualquier carpeta): {ficheros_sueltos_en_raiz:,}")
    print(f"  ficheros totales (recursivo, dentro de esas carpetas) : {total_ficheros:,}")
    print()

    print("PROFUNDIDAD MAXIMA DENTRO DE CADA CARPETA DE PRIMER NIVEL")
    print("(0 = todo suelto directamente en la carpeta; 1+ = hay subcarpetas):")
    for prof in sorted(hist_profundidad):
        etiqueta = "0 (plano)" if prof == 0 else f"{prof} nivel(es) de subcarpetas"
        print(f"    {etiqueta:<28} {hist_profundidad[prof]:>4,} carpetas")
    print()

    print("TAMANIO DE CADA CARPETA DE PRIMER NIVEL, EN NUMERO DE FICHEROS:")
    for cubo in ("0", "1-10", "11-50", "51-200", "201-1000", "1000+"):
        if hist_tamano_carpeta.get(cubo):
            print(f"    {cubo:<12} ficheros  ->  {hist_tamano_carpeta[cubo]:>4,} carpetas")
    print()

    print("EXTENSIONES DE FICHERO (todas, no solo PDF):")
    for ext, n in extensiones.most_common(15):
        pct = round(n * 100.0 / total_ficheros, 1) if total_ficheros else 0
        print(f"    {ext:<18} {n:>7,}  ({pct}%)")
    print()

    if credenciales_encontradas:
        print("!" * 70)
        print(f"  ATENCION: {credenciales_encontradas:,} fichero(s) con extension de")
        print("  CERTIFICADO DIGITAL (.pfx/.p12/.cer/.crt/.key/.pem) encontrados.")
        print("  Esto NO es documentacion -- es una CREDENCIAL de acceso a la Sede")
        print("  Electronica en nombre de un cliente. Si en el futuro algun script")
        print("  recorre PC1 para procesar documentos en bloque, estos ficheros")
        print("  tienen que quedar EXCLUIDOS a proposito, nunca solo ignorados")
        print("  porque su extension no coincide con .pdf.")
        print("!" * 70)
        print()

    print("RECONOCIMIENTO DE MODELO AEAT POR NOMBRE DE FICHERO:")
    print(f"    con ALGUN modelo conocido en el nombre  : {total_con_algun_modelo:,} "
          f"({round(total_con_algun_modelo*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    sin ningun modelo reconocido en el nombre: {total_sin_ningun_modelo:,} "
          f"({round(total_sin_ningun_modelo*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print("    desglose por modelo (un fichero puede contar en varios si el nombre es ambiguo):")
    for modelo, n in con_modelo_reconocido.most_common():
        print(f"        modelo {modelo:<5} {n:>7,}")
    print()

    print("SEGUNDA PASADA -- dos señales mas, para saber si el patron")
    print("estricto se estaba quedando corto (anadido tras una primera")
    print("medicion real que dio un 9,2% muy por debajo de lo esperado):")
    print(f"    con el mismo numero de modelo, SIN exigir que este aislado : "
          f"{total_con_modelo_suelto:,} "
          f"({round(total_con_modelo_suelto*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    con una PALABRA fiscal reconocible (iva/irpf/retenciones/...) : "
          f"{total_con_palabra_fiscal:,} "
          f"({round(total_con_palabra_fiscal*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    con ALGO reconocible (numero estricto O suelto O palabra)  : "
          f"{con_algo_reconocible:,} "
          f"({round(con_algo_reconocible*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    sin NADA reconocible de lo anterior                        : "
          f"{sin_nada_reconocible:,} "
          f"({round(sin_nada_reconocible*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print()

    print("LA PALABRA 'MODELO' LITERAL EN EL NOMBRE (ambigua a proposito:")
    print("'modelo de contrato' tambien la lleva, no solo un impreso AEAT):")
    print(f"    ficheros con 'modelo' en el nombre       : {total_con_palabra_modelo:,} "
          f"({round(total_con_palabra_modelo*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    de esos, ADEMAS con un numero de modelo  : {palabra_modelo_y_numero:,} "
          "  <- estos casi seguro SI son un impreso AEAT")
    print(f"    de esos, 'modelo' SIN ningun numero junto: {palabra_modelo_sola:,} "
          "  <- aqui vive la ambiguedad real (contratos, cartas...)")
    print()

    print("PERIODO EN EL NOMBRE (trimestre/mes/'mensual'):")
    print(f"    ficheros con algo que parece un periodo : {con_periodo:,} "
          f"({round(con_periodo*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    ficheros con un anio (20XX) en el nombre : {con_anio:,} "
          f"({round(con_anio*100.0/total_ficheros,1) if total_ficheros else 0}%)")
    print(f"    con MODELO reconocido Y periodo a la vez : {con_modelo_y_periodo:,} "
          f"(de los {total_con_algun_modelo:,} con modelo reconocido)")
    print()

    print("CÓMO LEER ESTO:")
    print("  - Muchas carpetas de primer nivel con profundidad 0-1 y tamaño")
    print("    moderado (1-200 ficheros) apunta a 'carpeta por cliente, todo")
    print("    junto' -- el mismo patrón que ya funciona para el 303.")
    print("  - Un 'sin modelo reconocido' alto (>20-30%) señala nombres poco")
    print("    uniformes -- como ya se midió para el 303 (145 de 1.168, 12%),")
    print("    solo que aquí sería sobre todos los modelos a la vez.")
    print("  - Muchos ficheros sueltos en la raíz, o carpetas con miles de")
    print("    ficheros y profundidad alta, apuntan más a volcado plano que")
    print("    a estructura por cliente.")


if __name__ == "__main__":
    main()
