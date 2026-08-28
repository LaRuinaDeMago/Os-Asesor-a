#!/usr/bin/env python3
"""cruzar_303_importes.py — FASE 2b: cruza la contabilidad contra los 303
presentados BUSCANDO IMPORTES, no leyendo casillas.

POR QUE ESTE ENFOQUE Y NO EL DE extraer_303_pdf.py
----------------------------------------------------
`extraer_303_pdf.py` (fase 2a) intento lo dificil: localizar la etiqueta
"Casilla 01" en el texto plano del PDF y quedarse con el primer numero de los
80 caracteres siguientes. Medido: 98-99% de las etiquetas se reconocen, pero
la consistencia interna de los valores extraidos fue del 1,2%. La razon es
estructural, no un bug: en un 303 los importes viven en una REJILLA, y al
aplanar la rejilla a texto el numero que queda cerca de una etiqueta suele
ser el de otra casilla. Aparcado, y con razon.

Este script no repite ese error porque no necesita resolverlo. Le da la
vuelta a la pregunta:

    en vez de   "que numero hay en la casilla 01 de este PDF?"   (dificil)
    pregunta    "el importe 12.500,00 que sale de la contabilidad,
                 aparece escrito en algun sitio de este PDF?"     (facil)

El importe ya lo tenemos: lo produjo `reconstruir_303.py` en 303_LOCAL.json.
No hay que extraerlo del PDF, solo CONFIRMARLO. Eso es buscar una cadena en
un texto, y sobrevive a que la rejilla se aplane en cualquier orden.

LO QUE RESUELVE, Y SON DOS COSAS A LA VEZ
-------------------------------------------
1. QUIEN ES CADA CUBO. `303_LOCAL.json` viene indexado por nombre de carpeta
   del corpus .DAT, y eso NO identifica al cliente: esta medido en
   `fase0_huella_cliente.py` que una copia de ContaPlus no contiene la
   identidad de la empresa. Algunas de esas carpetas son un cliente; otras
   agrupan por equipo ("ordenador de Fulanito") y mezclan varios.

2. SI LA CADENA DE LECTURA ES CORRECTA. Que los importes reconstruidos desde
   el .DAT aparezcan en el 303 que Hacienda ya dio por bueno valida el parseo
   del .DAT, la clasificacion de cuentas y la logica de tramos de una vez.

Y las dos salen de la MISMA operacion: si los importes del cubo X del 2021T2
aparecen en el 303 que vive en la carpeta de un cliente concreto, entonces X
es ese cliente Y la reconstruccion de ese trimestre es correcta.

COMO SE PROTEGE DE LA CASUALIDAD (leer antes de fiarse de un numero)
----------------------------------------------------------------------
Un solo importe coincidiendo no demuestra nada: 1.000,00 aparece en medio
mundo. Tres defensas, y ninguna es opcional:

  a) Se ignoran los importes por debajo de --min-importe: los pequenos y
     redondos colisionan solos.
  b) Se ignoran los importes que aparecen en DEMASIADAS carpetas distintas
     (--max-difusion): si un numero esta en el 40% de los clientes no
     distingue a nadie. Es la idea de "termino demasiado comun" de toda la
     vida.
  c) Se exige CORROBORACION EN VARIOS TRIMESTRES. Que un cubo case con una
     carpeta en un trimestre puede ser suerte; en tres, no.

Y, como en el resto del proyecto, el script NO decide solo si el resultado es
bueno: publica el HISTOGRAMA de aciertos y la distancia entre el mejor
candidato y el segundo. Si la separacion es limpia (bimodal), el cruce es
real; si es una nube continua, no lo es y el script lo dice con esas
palabras en vez de maquillarlo. Misma prueba de estabilidad que ya se uso
para validar la huella de NIF el 12-08-2026.

LO QUE ESTE SCRIPT NO HACE
----------------------------
No reconstruye un 303 (ver la cabecera de reconstruir_303.py: faltan
prorrata, bienes de inversion, intracomunitarias, ISP y compensacion de
cuotas). Por tanto, que un trimestre NO case no demuestra que este mal: puede
ser justo una de esas partidas. Eso se cuenta aparte, nunca se fuerza para
que cuadre.

REGLA DE DATOS (.claude/rules/datos.md — diseno de tres roles)
---------------------------------------------------------------
Lo ejecuta el titular, no Claude. Claude NUNCA abre la carpeta de documentos
ni el fichero _LOCAL de salida. Por pantalla solo salen RECUENTOS: ni un
nombre de carpeta, ni un nombre de fichero, ni un importe. Los errores se
agrupan por TIPO de excepcion, nunca por su mensaje, porque los mensajes
arrastran rutas y datos.

Uso:
    python cruzar_303_importes.py "RUTA_DE_DOCUMENTOS" --limite 150
    python cruzar_303_importes.py "RUTA_DE_DOCUMENTOS"
"""
import argparse
import bisect
import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from contrato_datos import RE_IMPORTE_EN_TEXTO, importes_en_texto

logging.getLogger("pdfminer").setLevel(logging.ERROR)  # ruido de ToUnicode

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    import pdfplumber
except ImportError:
    print("Falta pdfplumber. Instalar con: pip install pdfplumber")
    sys.exit(1)

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "cruce_303_agregado.json")

#: Recuento de la FORMA de los importes leidos (con o sin separador de
#: millar). Nunca guarda un valor, solo cuantos habia de cada forma.
ESTADISTICA_FORMATO = Counter()

# Reutilizados TAL CUAL de extraer_303_pdf.py: esta parte esta medida y
# funciona (98-99% de reconocimiento sobre 1.168 documentos). Lo que se tira
# de aquel script es la asociacion etiqueta->numero, no la lectura.
PATRON_NOMBRE = re.compile(
    r'303.{0,15}?(?P<trim>1|2|3|4|primer|segundo|tercer|cuarto)'
    r'[a-záéíóú°º]{0,4}\.?\s*trimestre.{0,5}?(?P<anio>20\d{2})',
    re.IGNORECASE
)
TRIM_A_NUM = {"1": 1, "2": 2, "3": 3, "4": 4,
              "primer": 1, "segundo": 2, "tercer": 3, "cuarto": 4}
#: El patron de importes y su conversion viven en contrato_datos.py, que es la
#: unica regla de numeros del proyecto. NO se copian aqui: el 26-08-2026 se
#: descubrio que habia TRES copias del patron y las tres estaban mal (exigian
#: el punto de millar, asi que "12345,67" se leia como "345,67" en silencio,
#: devolviendo un numero distinto sin dar ningun error). Ver el comentario
#: largo de RE_IMPORTE_EN_TEXTO en contrato_datos.py.
NUM_ES = RE_IMPORTE_EN_TEXTO

#: Solo para diagnostico: cuantos importes venian agrupados y cuantos no. Si
#: casi ninguno viene agrupado, el patron viejo estaba destrozando los
#: importes de este archivo en concreto.
NUM_AGRUPADO = re.compile(r"^-?\d{1,3}(?:[.\u0020\u00a0\u2009]\d{3})+,\d{2}$")


#: Reserva para los nombres que el patron estricto no reconoce. En la primera
#: pasada real (26-08-2026) se quedaron fuera 145 de 1.168 ficheros — un 12%
#: del archivo — pese a que el titular los nombra de forma uniforme
#: ("MODELO 303-2º TRIMESTRE 2024"). El estricto exige la palabra "trimestre"
#: entera y pegada al numero; este acepta las abreviaturas normales ("2T",
#: "2 TRIM") siempre que ademas haya un ano de cuatro cifras en el nombre.
#: Sigue exigiendo las DOS cosas: sin ano no hay trimestre que valga.
PATRON_TRIM_SUELTO = re.compile(r'(?<!\d)([1-4])\s*[ºª°o]?\s*(?:t\b|trim)',
                                re.IGNORECASE)
PATRON_ANIO_SUELTO = re.compile(r'(?<!\d)(20\d{2})(?!\d)')

#: Cuantos trimestres se han reconocido con cada patron. Solo recuento.
ESTADISTICA_NOMBRE = Counter()


def trimestre_del_nombre(nombre):
    """'Modelo 303 3er trimestre 2021.pdf' -> '2021T3'. None si no se puede."""
    m = PATRON_NOMBRE.search(nombre)
    if m:
        trim = TRIM_A_NUM.get(m.group("trim").lower())
        if trim:
            ESTADISTICA_NOMBRE["patron estricto"] += 1
            return f"{m.group('anio')}T{trim}"
    m_tri = PATRON_TRIM_SUELTO.search(nombre)
    m_anio = PATRON_ANIO_SUELTO.search(nombre)
    if m_tri and m_anio:
        ESTADISTICA_NOMBRE["patron de reserva"] += 1
        return f"{m_anio.group(1)}T{m_tri.group(1)}"
    ESTADISTICA_NOMBRE["no reconocido"] += 1
    return None


def carpeta_cliente(ruta, raiz):
    """La carpeta de PRIMER nivel bajo la raiz: en el archivo del despacho hay
    una carpeta por cliente, y dentro sus modelos de todos los anios."""
    rel = os.path.relpath(ruta, raiz)
    partes = rel.split(os.sep)
    return partes[0] if len(partes) > 1 else "(raiz)"


def importes_del_pdf(ruta):
    """Todos los importes en formato espanol que aparecen en el PDF, como
    conjunto de valores absolutos redondeados. No se mira DONDE aparecen: esa
    es justamente la parte que no funciona y que este enfoque no necesita."""
    with pdfplumber.open(ruta) as pdf:
        texto = "\n".join((p.extract_text() or "") for p in pdf.pages)
    if len(texto.strip()) < 20:
        return None          # PDF escaneado o vacio: no es utilizable
    # Estadistica de FORMA, no de valor: cuantos importes traian separador de
    # millar y cuantos no. Si casi ninguno lo traia, el patron viejo (que lo
    # exigia) estaba leyendo mal este archivo entero, y eso explica el cero.
    for m in NUM_ES.findall(texto):
        ESTADISTICA_FORMATO["agrupado" if NUM_AGRUPADO.match(m)
                            else "sin agrupar"] += 1
    # La conversion la hace importes_en_texto(), que descarta lo que no se
    # puede interpretar en vez de reventar.
    #
    # DEFECTO REAL corregido el 26-08-2026, introducido ese mismo dia al
    # unificar el patron: aqui habia `abs(parse_numero(m).valor)` a pelo. Un
    # solo importe INVALID en el documento hacia `abs(None)` -> TypeError, el
    # `except` del bucle de arriba lo contaba como "PDF ilegible", y se
    # perdian TODOS los importes de ese PDF por culpa de uno. Un fallo de una
    # linea que descarta un documento entero, en silencio, es justo lo que
    # este proyecto persigue.
    return {round(abs(v), 2) for v in importes_en_texto(texto)}


def importes_significativos(lados, min_importe):
    """Los importes que la contabilidad dice para un trimestre: cada base y
    cada cuota por tipo, mas los dos totales por lado. Se devuelven en valor
    absoluto porque el signo depende de como se contabilizo el apunte, no de
    lo que se declaro."""
    valores = set()
    for lado in ("devengado", "deducible"):
        total_base = 0.0
        total_cuota = 0.0
        for celda in lados.get(lado, {}).values():
            for clave in ("base", "cuota"):
                v = round(abs(celda.get(clave, 0.0)), 2)
                if v >= min_importe:
                    valores.add(v)
            total_base += celda.get("base", 0.0)
            total_cuota += celda.get("cuota", 0.0)
        for total in (total_base, total_cuota):
            v = round(abs(total), 2)
            if v >= min_importe:
                valores.add(v)
    return valores


def leer_archivo_pdf(raiz, limite, incidencias):
    """Recorre el archivo y devuelve {(carpeta, trimestre): {importes}}.

    Se filtra por nombre de fichero igual que extraer_303_pdf.py: alli se
    midio que ese filtro encuentra 1.168 modelos 303 reales, asi que la via
    esta comprobada y no hace falta abrir todos los PDF del despacho para
    descartarlos despues."""
    candidatos = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() != ".pdf" or "303" not in n:
                continue
            tri = trimestre_del_nombre(n)
            if tri is None:
                incidencias["PDF de 303 sin trimestre reconocible en el nombre"] += 1
                continue
            ruta = os.path.join(dp, n)
            candidatos.append((ruta, tri, carpeta_cliente(ruta, raiz)))

    total = len(candidatos)
    print(f"{total:,} PDF del modelo 303 localizados por nombre "
          f"(estricto: {ESTADISTICA_NOMBRE['patron estricto']:,}  "
          f"reserva: {ESTADISTICA_NOMBRE['patron de reserva']:,}  "
          f"sin reconocer: {ESTADISTICA_NOMBRE['no reconocido']:,}).")
    if limite and limite < total:
        # CORREGIDO 26-08-2026, tras la primera ejecucion real: coger los N
        # PRIMEROS es coger las primeras carpetas por orden alfabetico. En la
        # prueba de 150 PDF salieron solo 7 carpetas de cliente frente a 24
        # cubos en la contabilidad, asi que la mayoria de los cubos no tenia
        # NINGUNA carpeta con la que casar y el cero era inevitable.
        # Es el mismo error que ya se corrigio en cuadre_303_ficha.py: una
        # muestra tomada por orden no es una muestra.
        por_carpeta = defaultdict(list)
        for c in candidatos:
            por_carpeta[c[2]].append(c)
        repartidos = []
        indice = 0
        while len(repartidos) < limite:
            quedan = False
            for carpeta in sorted(por_carpeta):
                grupo = por_carpeta[carpeta]
                if indice < len(grupo):
                    quedan = True
                    repartidos.append(grupo[indice])
                    if len(repartidos) >= limite:
                        break
            if not quedan:
                break
            indice += 1
        candidatos = repartidos
        print(f"  --limite {limite}: {len(candidatos):,} PDF repartidos entre "
              f"{len(por_carpeta):,} carpetas (no los primeros por orden).")
    if not candidatos:
        return {}, 0

    # Avance cada 5%: un script callado varios minutos se parece demasiado a
    # uno colgado (misma leccion ya escrita en EMPEZAR_AQUI.md sobre el
    # retro-semaforo).
    paso = max(1, len(candidatos) // 20)
    por_celda = defaultdict(set)
    leidos = 0
    for i, (ruta, tri, carpeta) in enumerate(candidatos, start=1):
        try:
            importes = importes_del_pdf(ruta)
            if importes is None:
                incidencias["PDF sin texto extraible (escaneado?)"] += 1
            else:
                por_celda[(carpeta, tri)] |= importes
                leidos += 1
        except Exception as e:
            # Por TIPO de excepcion, nunca el mensaje: arrastra rutas y datos.
            incidencias["PDF:" + type(e).__name__] += 1
        if i % paso == 0 or i == len(candidatos):
            print(f"    {i * 100 // len(candidatos):>3}%  ({i:,}/{len(candidatos):,})")
    return por_celda, leidos


#: Niveles de tolerancia con los que se mide el solape. La igualdad EXACTA es
#: mucho pedir a un agregado: nuestra base suma cientos de apuntes y el 303
#: declara un total redondeado, asi que un desfase de centimos es lo normal,
#: no la excepcion. Medir a varios niveles distingue dos diagnosticos que
#: llevan a sitios opuestos:
#:
#:   - si el solape sube mucho al aflojar a centimos -> son los MISMOS
#:     numeros con diferencias de redondeo, y el cruce sirve.
#:   - si no sube al aflojar ni siquiera un 1% -> no son los mismos numeros,
#:     y aflojar mas solo produciria coincidencias por casualidad.
#:
#: El ultimo nivel esta a proposito absurdamente flojo: es el CONTROL. Si con
#: un 5% de margen tampoco hay solape, no queda ninguna duda de que el
#: problema no es la precision.
TOLERANCIAS = (
    ("exacto",  0.00, 0.0000),
    ("+-0,02",  0.02, 0.0000),
    ("+-1,00",  1.00, 0.0000),
    ("+-0,1%",  0.00, 0.0010),
    ("+-1%",    0.00, 0.0100),
    ("+-5% (control)", 0.00, 0.0500),
)


def solape(objetivo, ordenados, tol_abs, tol_rel):
    """Cuantos importes del objetivo tienen alguno cerca en la lista dada.
    `ordenados` es la lista de importes del PDF ya ordenada, para poder
    buscar el mas proximo por biseccion en vez de comparar todo con todo."""
    if not ordenados:
        return 0
    n = 0
    for v in objetivo:
        i = bisect.bisect_left(ordenados, v)
        distancia = None
        for j in (i - 1, i):
            if 0 <= j < len(ordenados):
                d = abs(ordenados[j] - v)
                distancia = d if distancia is None else min(distancia, d)
        if distancia is not None and distancia <= max(tol_abs, abs(v) * tol_rel):
            n += 1
    return n


def filtrar_difusos(por_celda, max_difusion):
    """Quita los importes que aparecen en demasiadas carpetas distintas. Un
    numero presente en media cartera no identifica a nadie, y ademas infla el
    recuento de aciertos de todos los candidatos por igual."""
    carpetas = {carpeta for carpeta, _tri in por_celda}
    if len(carpetas) < 3:
        return por_celda, 0, len(carpetas)
    # Se cuenta en cuantas CARPETAS DISTINTAS aparece cada importe, no en
    # cuantas celdas. La diferencia no es cosmetica: un importe que se repite
    # en varios trimestres del MISMO cliente (una cuota fija, un alquiler)
    # contaria como "muy difuso" contandolo por celdas, y es justo lo
    # contrario -- es senal de ese cliente, no ruido comun a todos.
    carpetas_por_importe = defaultdict(set)
    for (carpeta, _tri), importes in por_celda.items():
        for v in importes:
            carpetas_por_importe[v].add(carpeta)
    en_cuantas = {v: len(cs) for v, cs in carpetas_por_importe.items()}
    tope = max(2, int(len(carpetas) * max_difusion))
    difusos = {v for v, n in en_cuantas.items() if n > tope}
    del carpetas_por_importe
    limpio = {clave: (importes - difusos) for clave, importes in por_celda.items()}
    return limpio, len(difusos), len(carpetas)


def cruzar(contabilidad, por_celda, min_importe, min_aciertos):
    """El nucleo del cruce, separado de main() (28-08-2026) para poder
    ensayarlo en seco con datos sinteticos -- este script nunca habia tenido
    un ensayo propio, ni siquiera sintetico, pese a producir un cruce
    cliente<->contabilidad del que Diego se fiaria para decisiones reales.
    La lectura de PDF (importes_del_pdf) no se toca ni se ensaya aqui: esa
    parte reutiliza el patron ya medido en extraer_303_pdf.py (98-99% de
    reconocimiento sobre 1.168 documentos). Lo que nunca se habia probado es
    este algoritmo de cruce en si -- exactamente lo que faltaba.

    Devuelve un dict con el `resultado` (cubo -> mejor carpeta candidata) y
    los histogramas/diagnosticos que main() imprime."""
    aciertos = defaultdict(Counter)
    casados = defaultdict(Counter)
    trimestres_contabilidad = 0
    mejor_solape_por_trimestre = Counter()
    trimestres_sin_pdf = 0
    solape_por_tolerancia = {nombre: [0, 0] for nombre, _a, _r in TOLERANCIAS}
    ordenados_por_celda = {clave: sorted(importes)
                           for clave, importes in por_celda.items()}

    for cubo, trimestres in contabilidad.items():
        for tri, lados in trimestres.items():
            objetivo = importes_significativos(lados, min_importe)
            if not objetivo:
                continue
            trimestres_contabilidad += 1
            hubo_pdf = False
            mejor_aqui = 0
            mejor_por_tol = {nombre: 0 for nombre, _a, _r in TOLERANCIAS}
            for (carpeta, tri_pdf), importes in por_celda.items():
                if tri_pdf != tri:
                    continue
                hubo_pdf = True
                n = len(objetivo & importes)
                mejor_aqui = max(mejor_aqui, n)
                if n:
                    aciertos[cubo][carpeta] += n
                    if n >= min_aciertos:
                        casados[cubo][carpeta] += 1
                ordenados = ordenados_por_celda[(carpeta, tri_pdf)]
                for nombre, tol_abs, tol_rel in TOLERANCIAS:
                    m = solape(objetivo, ordenados, tol_abs, tol_rel)
                    if m > mejor_por_tol[nombre]:
                        mejor_por_tol[nombre] = m
            if hubo_pdf:
                mejor_solape_por_trimestre[mejor_aqui] += 1
                for nombre in mejor_por_tol:
                    solape_por_tolerancia[nombre][0] += mejor_por_tol[nombre]
                    solape_por_tolerancia[nombre][1] += len(objetivo)
            else:
                trimestres_sin_pdf += 1

    resultado = {}
    hist_trimestres = Counter()
    hist_separacion = Counter()
    for cubo in contabilidad:
        marcador = casados.get(cubo, Counter())
        if not marcador:
            resultado[cubo] = {"carpeta": None, "motivo": "ningun trimestre casado"}
            hist_trimestres[0] += 1
            continue
        orden = marcador.most_common()
        mejor, n_mejor = orden[0]
        n_segundo = orden[1][1] if len(orden) > 1 else 0
        hist_trimestres[n_mejor] += 1
        hist_separacion[n_mejor - n_segundo] += 1
        resultado[cubo] = {
            "carpeta": mejor,
            "trimestres_casados": n_mejor,
            "trimestres_del_segundo": n_segundo,
            "aciertos_totales": aciertos[cubo][mejor],
        }

    return {
        "resultado": resultado,
        "hist_trimestres": hist_trimestres,
        "hist_separacion": hist_separacion,
        "trimestres_contabilidad": trimestres_contabilidad,
        "trimestres_sin_pdf": trimestres_sin_pdf,
        "mejor_solape_por_trimestre": mejor_solape_por_trimestre,
        "solape_por_tolerancia": solape_por_tolerancia,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("documentos", help="Raiz del archivo de modelos presentados")
    ap.add_argument("--json", default=os.path.join(AQUI, "303_LOCAL.json"),
                    help="Detalle producido por reconstruir_303.py")
    ap.add_argument("--limite", type=int, default=0,
                    help="Procesar solo los N primeros PDF. Para una prueba "
                         "rapida antes de la pasada completa.")
    ap.add_argument("--min-importe", type=float, default=100.0,
                    help="Ignorar importes por debajo de esto (colisionan solos)")
    ap.add_argument("--max-difusion", type=float, default=0.30,
                    help="Ignorar importes presentes en mas de esta fraccion de "
                         "carpetas (no distinguen a nadie)")
    ap.add_argument("--min-aciertos", type=int, default=3,
                    help="Aciertos minimos en un trimestre para darlo por casado")
    ap.add_argument("--detalle", default=os.path.join(AQUI, "cruce_303_LOCAL.json"),
                    help="Fichero con el cruce cubo -> carpeta de cliente. "
                         "DEBE llevar _LOCAL: lleva nombres de cliente.")
    args = ap.parse_args()

    if "_LOCAL" not in os.path.basename(args.detalle):
        print("ERROR: --detalle debe contener _LOCAL en el nombre: la salida "
              "relaciona contabilidades con nombres de cliente reales, y "
              ".gitignore solo protege *_LOCAL.*", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(args.json):
        print(f"ERROR: no encuentro {args.json}. Generalo con:\n"
              f"  python reconstruir_303.py \"RUTA_DEL_CORPUS\" "
              f"--detalle 303_LOCAL.json", file=sys.stderr)
        sys.exit(1)
    raiz = os.path.abspath(args.documentos)
    if not os.path.isdir(raiz):
        print(f"ERROR: no puedo abrir la carpeta de documentos indicada.",
              file=sys.stderr)
        sys.exit(1)

    with open(args.json, "r", encoding="utf-8") as f:
        contabilidad = json.load(f)

    incidencias = Counter()
    por_celda, leidos = leer_archivo_pdf(raiz, args.limite, incidencias)
    if not por_celda:
        print("\nNo se ha podido leer ningun 303. Nada que cruzar.")
        if incidencias:
            print(f"Incidencias: {dict(incidencias)}")
        sys.exit(1)

    por_celda, n_difusos, n_carpetas = filtrar_difusos(por_celda, args.max_difusion)
    print(f"\n{leidos:,} PDF leidos con texto  |  {n_carpetas:,} carpetas de "
          f"cliente en el archivo")
    print(f"{n_difusos:,} importes descartados por aparecer en demasiadas carpetas.")

    # --- El cruce -------------------------------------------------------
    # Nucleo extraido a cruzar() (28-08-2026) para poder ensayarlo en seco.
    cr = cruzar(contabilidad, por_celda, args.min_importe, args.min_aciertos)
    resultado = cr["resultado"]
    hist_trimestres = cr["hist_trimestres"]
    hist_separacion = cr["hist_separacion"]
    trimestres_contabilidad = cr["trimestres_contabilidad"]
    trimestres_sin_pdf = cr["trimestres_sin_pdf"]
    mejor_solape_por_trimestre = cr["mejor_solape_por_trimestre"]
    solape_por_tolerancia = cr["solape_por_tolerancia"]

    con_match = [r for r in resultado.values() if r.get("carpeta")]
    solidos = [r for r in con_match
               if r["trimestres_casados"] >= 3
               and r["trimestres_casados"] > r["trimestres_del_segundo"]]
    ambiguos = [r for r in con_match
                if r["trimestres_casados"] <= r["trimestres_del_segundo"]]

    print()
    print("=" * 70)
    print("CRUCE CONTABILIDAD <-> 303 PRESENTADOS")
    print("=" * 70)
    print(f"  cubos en la contabilidad          : {len(contabilidad):,}")
    print(f"  trimestres con importes que buscar: {trimestres_contabilidad:,}")
    print(f"  cubos con algun trimestre casado  : {len(con_match):,}")
    print(f"  de esos, SOLIDOS (>=3 trimestres y sin empate): {len(solidos):,}")
    print(f"  AMBIGUOS (empatan con otra carpeta)          : {len(ambiguos):,}")
    print()
    print("TRIMESTRES CASADOS POR CUBO (cuantos cubos casan en N trimestres):")
    for n in sorted(hist_trimestres):
        print(f"    {n:>3} trimestres  {'#' * min(50, hist_trimestres[n]):<50} "
              f"{hist_trimestres[n]:,}")
    print()
    print("DIAGNOSTICO — MEJOR SOLAPE POR TRIMESTRE (aunque no llegue al minimo):")
    print(f"  (trimestres de la contabilidad sin NINGUN 303 del mismo periodo: "
          f"{trimestres_sin_pdf:,})")
    for n in sorted(mejor_solape_por_trimestre):
        etiqueta = f"{n} importes" if n else "0 importes  <- nada en comun"
        print(f"    {etiqueta:<28} "
              f"{'#' * min(45, mejor_solape_por_trimestre[n]):<45} "
              f"{mejor_solape_por_trimestre[n]:,}")
    print("  Si el mejor solape es casi siempre 0, el problema NO es el umbral:")
    print("  o los importes no se leen bien, o no son los mismos numeros.")
    print()
    print("DIAGNOSTICO DECISIVO — SOLAPE SEGUN LA TOLERANCIA:")
    print("  (que fraccion de los importes buscados encuentra pareja)")
    for nombre, _a, _r in TOLERANCIAS:
        encontrados, buscados = solape_por_tolerancia[nombre]
        pct = (encontrados * 100.0 / buscados) if buscados else 0.0
        print(f"    {nombre:<16} {encontrados:>7,} de {buscados:>7,}   "
              f"{pct:>5.1f}%  {'#' * int(pct / 2)}")
    print("  COMO SE LEE:")
    print("    - sube mucho al aflojar a centimos -> son los MISMOS numeros y")
    print("      solo fallaba el redondeo: el cruce sirve, con tolerancia.")
    print("    - plano y bajo hasta el 5% de control -> NO son los mismos")
    print("      numeros. El problema no es la precision, es la identidad:")
    print("      esos cubos no se corresponden con un cliente suelto.")
    formato_total = sum(ESTADISTICA_FORMATO.values())
    if formato_total:
        sin_agrupar = ESTADISTICA_FORMATO.get("sin agrupar", 0)
        print()
        print("FORMA DE LOS IMPORTES LEIDOS EN LOS PDF:")
        print(f"    con separador de millar : {ESTADISTICA_FORMATO.get('agrupado', 0):>9,}")
        print(f"    sin separador de millar : {sin_agrupar:>9,}"
              f"   ({sin_agrupar * 100 // formato_total}%)")
    print()
    print("DISTANCIA ENTRE EL MEJOR CANDIDATO Y EL SEGUNDO:")
    print("  (si casi todo esta en 0, no hay separacion y el cruce NO vale)")
    for d in sorted(hist_separacion):
        print(f"    +{d:<3}  {'#' * min(50, hist_separacion[d]):<50} "
              f"{hist_separacion[d]:,}")
    if incidencias:
        print()
        print("LO QUE NO SE HA PODIDO LEER (no se mete en ningun recuento):")
        for k, n in incidencias.most_common():
            print(f"    {k:<52} {n:>7,}")

    agregado = {
        "version": "1.0",
        "cubos": len(contabilidad),
        "trimestres_buscados": trimestres_contabilidad,
        "pdf_leidos": leidos,
        "carpetas_en_archivo": n_carpetas,
        "cubos_con_match": len(con_match),
        "cubos_solidos": len(solidos),
        "cubos_ambiguos": len(ambiguos),
        "hist_trimestres_casados": dict(hist_trimestres),
        "hist_separacion": dict(hist_separacion),
        "solape_por_tolerancia": {n: {"encontrados": v[0], "buscados": v[1]}
                                  for n, v in solape_por_tolerancia.items()},
        "mejor_solape_por_trimestre": dict(mejor_solape_por_trimestre),
        "formato_importes": dict(ESTADISTICA_FORMATO),
        "reconocimiento_de_nombres": dict(ESTADISTICA_NOMBRE),
        "parametros": {"min_importe": args.min_importe,
                       "max_difusion": args.max_difusion,
                       "min_aciertos": args.min_aciertos,
                       "limite": args.limite},
        "incidencias": dict(incidencias),
        "aviso": ("Que un trimestre no case NO demuestra un error contable: "
                  "reconstruir_303.py no calcula prorrata, bienes de inversion, "
                  "intracomunitarias, ISP ni compensacion de cuotas."),
    }
    with open(SALIDA_AGREGADA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, ensure_ascii=False, indent=2)

    with open(args.detalle, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print()
    print(f"Agregado (se puede subir) : {SALIDA_AGREGADA}")
    print(f"Cruce cubo -> cliente     : {os.path.abspath(args.detalle)}")
    print()
    print("COMO LEER ESTO, Y ES LO QUE IMPORTA:")
    print("  - Si hay muchos cubos SOLIDOS y la distancia al segundo casi nunca")
    print("    es 0, el cruce es real: ya sabes de que cliente es cada")
    print("    contabilidad Y que la reconstruccion de esos trimestres cuadra")
    print("    con lo que se presento.")
    print("  - Si casi todo sale ambiguo o con distancia 0, este metodo NO")
    print("    funciona con estos datos. Es un resultado valido y se para aqui,")
    print("    no se baja el liston hasta que salga bonito.")


if __name__ == "__main__":
    main()
