#!/usr/bin/env python3
"""crear_muestras_sinteticas.py — facturas FABRICADAS como imagen, con verdad conocida.

QUE PROBLEMA RESUELVE, Y POR QUE NO BASTABA CON LO QUE YA HABIA
----------------------------------------------------------------
`crear_factura_sintetica.py` fabrica UNA factura en HTML. Sirvio para el Paso 1
del 16-09-2026 y encontro dos defectos reales. Pero dejo DOS preguntas sin
contestar, y estan escritas tal cual en PENDIENTE.md:

    "`total_factura_2` y `nif_margen` NO se pudieron comprobar: en esta factura
     fabricada el pie lleva el mismo valor que el cuadro, asi que copiar y leer
     dos veces son indistinguibles."

Ese es un fallo de DISENO DEL DOCUMENTO, no del motor ni del modelo. Si el pie
dice exactamente lo mismo que el cuadro, una lectura honrada y un copia-pega
producen la misma salida, y la medicion no puede distinguirlos. La doble lectura
-- que existe justamente para cazar un total mal leido -- seguiria sin estar
probada aunque saliera "bien".

Este modulo fabrica documentos donde SI se pueden distinguir, y ademas lo hace
como IMAGEN, que es lo que de verdad llega: una foto, no un HTML.

LAS RECETAS, Y QUE PREGUNTA CIERRA CADA UNA
---------------------------------------------
  · `doble_lectura_letras`   El pie lleva el total EN LETRAS ("SON: MIL
      DOSCIENTOS DIEZ EUROS") y el NIF con otra puntuacion (`B-9876543-1`).
      El valor es el MISMO, asi que el documento es sano -- pero la NOTACION
      es distinta, y eso ya no se puede copiar del cuadro. Si `nif_margen`
      vuelve con guiones, se ha leido el pie. Mide ademas algo que ningun
      ensayo ha medido: si el modelo sabe leer un importe escrito con letras,
      que es como lo imprime media facturacion espanola.

  · `doble_lectura_descuadre`   El pie lleva un total NUMERICO DISTINTO del
      cuadro (1.210,00 frente a 1.120,00: dos digitos permutados, que es el
      error de tecleo real, no uno inventado). Aqui la discriminacion es
      total: si `total_factura_2` trae el del pie, se ha leido; si trae el del
      cuadro, es un espejo. Y de paso dispara el guard de doble lectura, que
      nunca se ha visto disparar sobre un documento de verdad.

  · `con_retencion`   Factura de profesional con retencion de IRPF al 15%.
      El total NO es base + IVA: es base + IVA - retencion. Un modelo que
      "entiende" facturas pero suma de memoria falla justo aqui. Ejercita
      `irpf_retencion`, que el contrato tiene declarado y ninguna muestra
      habia usado nunca.

CADA RECETA SALE DOS VECES, Y ESO ES EL EXPERIMENTO
-----------------------------------------------------
De cada receta se escriben DOS imagenes con la MISMA verdad conocida:

    <nombre>_limpia.png      el documento perfecto, como un PDF nativo
    <nombre>_degradada.jpg   el mismo documento, fotografiado mal

Que compartan verdad es justo lo que las hace utiles: si la limpia acierta y
la degradada falla, la diferencia es atribuible A LA DEGRADACION y a nada mas.
Es una variable aislada, no una impresion.

QUE DEGRADACION SE SIMULA, Y CUAL NO (declarado, no disimulado)
----------------------------------------------------------------
Se simula: giro leve, luz desigual (sombra sobre el papel), desenfoque,
ruido de sensor y compresion JPEG agresiva. Todo con semilla fija: la misma
receta da siempre la misma imagen, o no se podrian comparar dos ejecuciones.

NO se simula la deformacion de perspectiva (el papel visto en angulo, con los
margenes en trapecio). Se deja fuera a proposito y se dice aqui para que nadie
lea "la degradada pasa" como "las fotos en angulo pasan": eso no se ha medido.

QUE NO LLEVA, Y ES DELIBERADO
-------------------------------
Ni un dato real. Los emisores son inventados y los NIF se COMPONEN llamando a
`crear_factura_sintetica.nif_sintetico()`, que calcula el digito de control y lo
verifica contra `nif_check.valida_nif`. No hay ni un literal con forma de NIF en
este fichero: uno solo haria saltar `scripts/privacy_scan.py`, y ensanchar su
lista blanca para un fichero de pruebas seria debilitar la barrera por comodidad.

Las IMAGENES que genera NO se versionan (`.gitignore`), por el mismo motivo que
no se versiona el HTML del otro generador: llevan un NIF con checksum valido y
el escaner -- correctamente -- no puede distinguir uno sintetico de uno real.
Lo que vive en el repositorio es la receta.

USO
-----
    python crear_muestras_sinteticas.py

Escribe `muestras_sinteticas/` con las imagenes y, al lado de cada par, un
`<nombre>_verdad.json` con la verdad conocida usando los NOMBRES DE CAMPO DEL
CONTRATO (`contrato_datos.py`). Esa eleccion es lo que convierte la comparacion
en algo mecanico en vez de a ojo.

Y como pasarlas por la cadena (la puerta las deja salir por ser SINTETICAS
declaradas, sin DPA -- ver `.claude/rules/datos.md`):

    set OS_ASESORIA_CLOUD=1
    python captura_orquestador.py --imagen muestras_sinteticas/<fichero> \
           --procedencia SINTETICO
"""
import json
import os
import random
import sys

from crear_factura_sintetica import eur, nif_sintetico, num_es

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Pillow es lo que dibuja. Si falta, este modulo NO se muere al importarse:
#: un `sys.exit()` en la cabecera mata el proceso de quien lo importe -- que es
#: justo el defecto que `audit_project.py` vigila con "Modulos importables:
#: ninguno se sale al importarse". Se anota que no esta y se falla al usarlo,
#: con un mensaje que dice que hacer.
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    FALTA_PILLOW = None
except ImportError as _e:
    Image = ImageDraw = ImageFilter = ImageFont = None
    FALTA_PILLOW = str(_e)


def _exigir_pillow():
    """Para con un mensaje util, en vez de reventar con un AttributeError."""
    if FALTA_PILLOW is not None:
        raise RuntimeError(
            f"Falta Pillow, que es lo que dibuja las imagenes ({FALTA_PILLOW}).\n"
            f"    pip install Pillow          (o pip install -r requirements.txt)\n"
            f"Sin ella este generador no puede hacer nada: no hay modo "
            f"degradado ni 'casi'. O dibuja, o no dibuja.")

CARPETA = "muestras_sinteticas"

#: A4 a 150 ppp. Es la resolucion a la que sale un escaneo normal y a la que
#: se queda una foto de movil despues de recortarla: ni tan alta que esconda
#: los problemas de lectura, ni tan baja que los invente.
ANCHO, ALTO = 1240, 1754

#: Donde buscar una fuente de verdad. Se prueban por orden y la primera que
#: exista gana. Si no hay ninguna el script PARA: la fuente de mapa de bits que
#: trae Pillow dibuja un texto diminuto que ningun OCR leeria como una factura,
#: y una muestra ilegible mediria el dibujo, no el modelo.
FUENTES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/calibri.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
)
FUENTES_NEGRITA = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "/Library/Fonts/Arial Bold.ttf",
)


# ---------------------------------------------------------------------------
# El importe escrito con letras
# ---------------------------------------------------------------------------
# Una factura espanola de verdad suele imprimir el total dos veces: en cifras
# dentro del cuadro y en letras en el pie ("SON: ..."). Esa segunda forma es lo
# que hace que la doble lectura pueda MEDIRSE: un numero se puede copiar del
# cuadro, una frase en letras no.
#
# Cubre 0..999.999, que sobra para un total de factura. Mas arriba no se
# inventa nada: `numero_a_letras` levanta ValueError en vez de devolver algo
# parecido, que es la misma regla que el motor (si no se puede, no es OK).

_UNIDADES = ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
             "ocho", "nueve", "diez", "once", "doce", "trece", "catorce",
             "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve",
             "veinte", "veintiuno", "veintidos", "veintitres", "veinticuatro",
             "veinticinco", "veintiseis", "veintisiete", "veintiocho",
             "veintinueve")
_DECENAS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta",
            70: "setenta", 80: "ochenta", 90: "noventa"}
_CENTENAS = {100: "ciento", 200: "doscientos", 300: "trescientos",
             400: "cuatrocientos", 500: "quinientos", 600: "seiscientos",
             700: "setecientos", 800: "ochocientos", 900: "novecientos"}


def _grupo_a_letras(n):
    """0..999 con letras. `cien` exacto, `ciento ...` cuando lleva resto."""
    if n == 0:
        return ""
    if n == 100:
        return "cien"
    partes = []
    centena = (n // 100) * 100
    if centena:
        partes.append(_CENTENAS[centena])
    resto = n % 100
    if resto:
        if resto < 30:
            partes.append(_UNIDADES[resto])
        else:
            decena, unidad = (resto // 10) * 10, resto % 10
            partes.append(_DECENAS[decena] +
                          (" y " + _UNIDADES[unidad] if unidad else ""))
    return " ".join(partes)


def _apocopar(texto):
    """`veintiuno` -> `veintiun`, `treinta y uno` -> `treinta y un`.

    El apocope no es un adorno: delante de un sustantivo masculino ("un mil",
    "veintiun euros") es la forma correcta, y una muestra con una falta de
    ortografia mide la falta, no el modelo."""
    return texto[:-1] if texto.endswith("uno") else texto


def numero_a_letras(n, apocope_final=False):
    """Entero 0..999.999 escrito con letras, en minusculas.

    `apocope_final` cuando detras va un sustantivo masculino (EUROS): entonces
    `...veintiuno` pasa a `...veintiun`."""
    if not isinstance(n, int) or n < 0 or n > 999999:
        raise ValueError(
            f"numero_a_letras solo cubre enteros 0..999999, recibido {n!r}. "
            f"Antes que devolver algo aproximado, no devuelve nada.")
    if n == 0:
        return "cero"
    miles, resto = divmod(n, 1000)
    partes = []
    if miles == 1:
        partes.append("mil")
    elif miles:
        partes.append(_apocopar(_grupo_a_letras(miles)) + " mil")
    if resto:
        partes.append(_grupo_a_letras(resto))
    texto = " ".join(partes)
    return _apocopar(texto) if apocope_final else texto


def importe_a_letras(x):
    """`1210.00` -> `MIL DOSCIENTOS DIEZ EUROS`, como lo imprime una factura.

    Con centimos anade `CON N CENTIMOS`. En mayusculas porque asi es como
    aparece en el pie de las facturas reales, y la muestra debe parecerse a lo
    que de verdad va a llegar, no a lo que es comodo dibujar."""
    entero = int(round(x * 100)) // 100
    centimos = int(round(x * 100)) % 100
    texto = numero_a_letras(entero, apocope_final=True) + " euros"
    if centimos:
        texto += " con " + numero_a_letras(centimos, apocope_final=False) \
                 + " centimos"
    return texto.upper()


def _autocomprobar_letras():
    """Los casos que se equivocan solos si alguien toca lo de arriba.

    Corre en cada ejecucion, no en una suite aparte: un generador que produce
    muestras mal escritas contamina cada medicion que se haga con ellas, y el
    coste de comprobarlo aqui es cero."""
    casos = {
        100: "cien", 101: "ciento uno", 110: "ciento diez", 200: "doscientos",
        500: "quinientos", 700: "setecientos", 900: "novecientos",
        1000: "mil", 1210: "mil doscientos diez", 21: "veintiuno",
        21000: "veintiun mil", 31000: "treinta y un mil",
        1120: "mil ciento veinte", 999999:
            "novecientos noventa y nueve mil novecientos noventa y nueve",
    }
    for n, esperado in casos.items():
        obtenido = numero_a_letras(n)
        if obtenido != esperado:
            raise AssertionError(
                f"numero_a_letras({n}) = {obtenido!r}, se esperaba {esperado!r}")
    # El apocope delante de EUROS, que es donde de verdad se usa.
    if importe_a_letras(1421.0) != "MIL CUATROCIENTOS VEINTIUN EUROS":
        raise AssertionError("el apocope delante de EUROS no se aplica")
    if importe_a_letras(1210.50) != "MIL DOSCIENTOS DIEZ EUROS CON CINCUENTA CENTIMOS":
        raise AssertionError("los centimos no se escriben bien")


# ---------------------------------------------------------------------------
# Las recetas
# ---------------------------------------------------------------------------
# Cada una existe porque cierra una pregunta concreta que hoy esta abierta. No
# hay ninguna "por tener variedad": una muestra que no mide nada cuesta lo
# mismo de generar y despues hay que mirarla igual.

#: Como se escribe el total en el pie. Es EL parametro del experimento.
PIE_LETRAS = "letras"          # el mismo importe, con letras: no se puede copiar
PIE_DESCUADRE = "descuadre"    # otro importe: discriminacion total
PIE_NORMAL = "normal"          # en cifras, igual que el cuadro

RECETAS = (
    {
        "nombre": "doble_lectura_letras",
        "emisor": "SUMINISTROS EJEMPLO FICTICIO SL",
        "nif_digitos": "9876543", "nif_letra": "B",
        "direccion": "Calle Inventada 00, 00000 Ciudad Ejemplo",
        "num_documento": "A26/7.612",
        "fecha": "26/03/2026",
        "lineas": (("Material de oficina", 1000.00, 21),
                   ("Producto a tipo reducido", 200.00, 5)),
        "retencion_pct": None,
        "pie": PIE_LETRAS,
        #: En el pie, con puntos y guiones. Es la forma en que de verdad se
        #: imprime en el margen de media facturacion, y aqui hace de marcador:
        #: si `nif_margen` vuelve con guiones, se ha leido el pie de verdad.
        "nif_pie_con_guiones": True,
        "mide": ("¿`nif_margen` vuelve con la puntuacion del PIE (con guiones) "
                 "o con la de la CABECERA (sin ellos)? Con guiones = lo ha "
                 "leido. Y: ¿sabe leer un importe escrito con letras?"),
    },
    {
        "nombre": "doble_lectura_descuadre",
        "emisor": "DISTRIBUCIONES MUESTRA INVENTADA SA",
        "nif_digitos": "1234567", "nif_letra": "A",
        "direccion": "Avenida Ficticia 00, 00000 Villa Ejemplo",
        "num_documento": "F-2026/0431",
        "fecha": "14/04/2026",
        "lineas": (("Suministro de material", 1000.00, 21),),
        "retencion_pct": None,
        "pie": PIE_DESCUADRE,
        #: 1.210,00 en el cuadro y 1.120,00 en el pie: dos digitos permutados,
        #: que es el error de tecleo que de verdad ocurre. No un numero
        #: cualquiera: si el descuadre fuera enorme, cualquier lectura lo
        #: cazaria y la prueba seria mas facil de lo que es el problema.
        "pie_total": 1120.00,
        "nif_pie_con_guiones": False,
        "mide": ("¿`total_factura_2` trae el del PIE (1.120,00) o el del CUADRO "
                 "(1.210,00)? Si trae el del cuadro, la doble lectura es un "
                 "espejo y no vale nada. Y el motor deberia ponerse ROJO."),
    },
    {
        "nombre": "con_retencion",
        "emisor": "SERVICIOS PROFESIONALES DE MUESTRA SL",
        "nif_digitos": "2233445", "nif_letra": "B",
        "direccion": "Plaza Imaginaria 00, 00000 Pueblo Ejemplo",
        "num_documento": "2026/084",
        "fecha": "02/06/2026",
        "lineas": (("Servicios profesionales prestados", 2000.00, 21),),
        #: Retencion de IRPF. El total deja de ser base + IVA, y ese es el
        #: punto: un modelo que suma de memoria en vez de leer falla aqui y
        #: solo aqui.
        "retencion_pct": 15,
        "pie": PIE_NORMAL,
        "nif_pie_con_guiones": False,
        "mide": ("¿`irpf_retencion` llega con 300,00 y `total_factura` con "
                 "2.120,00 -- que NO es base + IVA? Es la unica receta donde "
                 "sumar de memoria da un numero distinto de leer."),
    },
)


def calcular(receta):
    """Los numeros de una receta, calculados aqui y comprobados aqui.

    Devuelve un dict con los importes. Nada se escribe a mano: si una linea
    dice 1.000,00 al 21%, la cuota SALE de multiplicar, no de que alguien haya
    tecleado 210,00 al lado. Un documento cuya aritmetica no cuadre haria que
    el motor diera ROJO por el documento y no por lo que se quiere medir, y
    costaria media sesion averiguarlo."""
    tramos = []
    for descripcion, base, tipo in receta["lineas"]:
        cuota = round(base * tipo / 100, 2)
        tramos.append({"descripcion": descripcion, "tipo": tipo,
                       "base": round(base, 2), "cuota": cuota})

    base_total = round(sum(t["base"] for t in tramos), 2)
    iva_total = round(sum(t["cuota"] for t in tramos), 2)

    retencion = None
    if receta["retencion_pct"] is not None:
        retencion = round(base_total * receta["retencion_pct"] / 100, 2)

    total = round(base_total + iva_total - (retencion or 0), 2)

    # La comprobacion que hace que esto sea una receta y no una esperanza.
    recalculado = round(sum(round(t["base"] * t["tipo"] / 100, 2)
                            for t in tramos), 2)
    if recalculado != iva_total:
        raise AssertionError(
            f"{receta['nombre']}: el IVA total no coincide con la suma de los "
            f"tramos ({recalculado} vs {iva_total})")

    pie_total = receta.get("pie_total", total)
    if receta["pie"] == PIE_DESCUADRE and pie_total == total:
        raise AssertionError(
            f"{receta['nombre']}: declarada como descuadre pero el pie lleva "
            f"el mismo importe que el cuadro. Seria exactamente el defecto de "
            f"diseno que esta receta existe para corregir.")

    return {"tramos": tramos, "base_total": base_total, "iva_total": iva_total,
            "retencion": retencion, "total": total, "pie_total": pie_total}


# ---------------------------------------------------------------------------
# El dibujo
# ---------------------------------------------------------------------------
_CACHE_FUENTES = {}


def fuente(tam, negrita=False):
    """Una fuente TrueType de verdad, o se para.

    No hay respaldo a la fuente de mapa de bits de Pillow. Dibujaria un texto
    diminuto e irregular que ningun OCR leeria como una factura: la muestra
    mediria el dibujo en vez del modelo, y saldria un 'no lo lee' que no
    significaria nada. Es la misma regla de siempre -- si no se puede hacer
    bien, no se hace a medias."""
    clave = (tam, negrita)
    if clave in _CACHE_FUENTES:
        return _CACHE_FUENTES[clave]
    for ruta in (FUENTES_NEGRITA if negrita else FUENTES):
        if os.path.exists(ruta):
            _CACHE_FUENTES[clave] = ImageFont.truetype(ruta, tam)
            return _CACHE_FUENTES[clave]
    raise RuntimeError(
        "No hay ninguna fuente TrueType de las buscadas:\n  " +
        "\n  ".join(FUENTES_NEGRITA if negrita else FUENTES) +
        "\nInstala una (en Debian/Ubuntu: fonts-dejavu-core) o anade la ruta "
        "de una del sistema a FUENTES / FUENTES_NEGRITA.")


#: El negro del papel. Explicito y no por defecto: la tinta por defecto de
#: ImageDraw sobre RGB es BLANCA (ink = -1), asi que un `d.text()` sin `fill`
#: dibuja texto invisible sobre papel blanco. Paso de verdad el 16-09-2026 en
#: la primera version de este fichero: el nombre del emisor y su NIF -- los dos
#: CAMPOS_CRITICOS -- se dibujaron en blanco y la muestra salia sin emisor. No
#: fallo nada: el fichero se escribio, el script devolvio 0 y la imagen pesaba
#: lo normal. Solo se vio MIRANDOLA.
NEGRO = (17, 17, 17)
GRIS = (68, 68, 68)


def _texto(dib, xy, texto, f, color=NEGRO):
    """Escribe con color EXPLICITO siempre. Ver el comentario de NEGRO."""
    dib.text(xy, texto, font=f, fill=color)


def _derecha(dib, x_dcha, y, texto, f, color=NEGRO):
    """Escribe alineado a la derecha, que es como van los importes."""
    ancho = dib.textbbox((0, 0), texto, font=f)[2]
    dib.text((x_dcha - ancho, y), texto, font=f, fill=color)


def nif_del_pie(receta, nif):
    """Como se escribe el NIF EN EL PIE, que puede no ser como en la cabecera.

    En un solo sitio a proposito. Estuvo duplicado entre `dibujar()` y la
    bateria durante un rato, y esa duplicacion tenia un filo: si el formato del
    pie cambiara en el dibujo, la bateria seguiria comprobando el formato viejo
    y diria que todo bien. El campo `nif_margen` de la verdad conocida saldria
    con una cosa y el papel llevaria otra -- justo el tipo de desajuste que
    haria parecer que el modelo lee mal.

    Los guiones no son decoracion: son el MARCADOR del experimento. Si
    `nif_margen` vuelve con ellos, el modelo ha leido el pie; si vuelve como la
    cabecera, lo ha copiado."""
    if receta["nif_pie_con_guiones"]:
        return f"{receta['nif_letra']}-{receta['nif_digitos']}-{nif[-1]}"
    return nif


def dibujar(receta, cifras):
    """La factura limpia, como saldria de una impresora."""
    _exigir_pillow()
    nif = nif_sintetico(receta["nif_digitos"], receta["nif_letra"])
    img = Image.new("RGB", (ANCHO, ALTO), (255, 255, 255))
    d = ImageDraw.Draw(img)
    izq, dcha = 90, ANCHO - 90

    #: Donde se ha escrito de verdad, anotado SOBRE LA MARCHA por el propio
    #: dibujo. La primera version llevaba estas coordenadas escritas a mano y
    #: no valia: al cambiar el numero de lineas de una receta, la banda se
    #: corria y acababa cayendo encima de la raya horizontal del bloque de
    #: totales -- con lo que la tinta de la RAYA daba por buena una etiqueta
    #: invisible. Un guard al que le vale la tinta del vecino es un falso
    #: verde. Derivadas del layout no pueden desincronizarse de el.
    zonas = []

    # -- aviso, para que nadie confunda una muestra con un documento ---------
    d.rectangle([izq, 70, dcha, 150], fill=(255, 233, 233),
                outline=(204, 0, 0), width=3)
    _texto(d, (izq + 18, 86), "DOCUMENTO FABRICADO PARA PRUEBAS",
           fuente(22, True), (153, 0, 0))
    _texto(d, (izq + 18, 116), "No corresponde a ninguna empresa ni operacion real.",
           fuente(17), (153, 0, 0))

    # -- cabecera ------------------------------------------------------------
    y = 200
    _texto(d, (izq, y), receta["emisor"], fuente(29, True))
    _texto(d, (izq, y + 44), f"NIF: {nif}", fuente(20))
    _texto(d, (izq, y + 76), receta["direccion"], fuente(18), (51, 51, 51))
    zonas.append(("emisor y NIF de cabecera", izq, izq + 500, y, y + 70))

    _derecha(d, dcha, y, "FACTURA", fuente(26, True))
    _derecha(d, dcha, y + 44, f"Numero: {receta['num_documento']}", fuente(20))
    _derecha(d, dcha, y + 76, f"Fecha: {receta['fecha']}", fuente(20))

    # -- cuadro de conceptos -------------------------------------------------
    y = 360
    columnas = (izq, izq + 520, izq + 720, izq + 900, dcha)
    alto_fila = 48
    d.rectangle([izq, y, dcha, y + alto_fila], fill=(238, 238, 238),
                outline=(120, 120, 120))
    _texto(d, (columnas[0] + 12, y + 13), "Concepto", fuente(19, True))
    for etiqueta, x in (("Base imponible", columnas[2] - 12),
                        ("% IVA", columnas[3] - 12),
                        ("Cuota IVA", columnas[4] - 12)):
        _derecha(d, x, y + 13, etiqueta, fuente(19, True))

    y += alto_fila
    y_primera_fila = y
    for t in cifras["tramos"]:
        d.rectangle([izq, y, dcha, y + alto_fila], outline=(150, 150, 150))
        for x in columnas[1:-1]:
            d.line([x, y, x, y + alto_fila], fill=(150, 150, 150))
        _texto(d, (columnas[0] + 12, y + 13), t["descripcion"], fuente(19))
        _derecha(d, columnas[2] - 12, y + 13, num_es(t["base"]), fuente(19))
        _derecha(d, columnas[3] - 12, y + 13, f"{t['tipo']}%", fuente(19))
        _derecha(d, columnas[4] - 12, y + 13, num_es(t["cuota"]), fuente(19))
        y += alto_fila
    # Solo la columna de Concepto, y por dentro de sus bordes: si la zona
    # tocara las lineas del cuadro, esas lineas la darian por escrita.
    zonas.append(("columna Concepto del cuadro", columnas[0] + 8,
                  columnas[1] - 8, y_primera_fila + 6, y - 6))

    # -- bloque de totales ---------------------------------------------------
    y += 46
    x_etq, x_val = dcha - 430, dcha
    filas = [("Base imponible total", cifras["base_total"]),
             ("Total IVA", cifras["iva_total"])]
    if cifras["retencion"] is not None:
        filas.append((f"Retencion IRPF {receta['retencion_pct']}%",
                      -cifras["retencion"]))
    y_primera_etiqueta = y
    for etiqueta, valor in filas:
        _texto(d, (x_etq, y), etiqueta, fuente(20))
        _derecha(d, x_val, y, num_es(valor) + " EUR", fuente(20))
        y += 38
    # Hasta x_etq+250: los importes van alineados a la derecha en x_val y
    # quedan fuera. Y hasta `y - 10`, para no rozar la raya de abajo.
    zonas.append(("etiquetas del bloque de totales", x_etq, x_etq + 250,
                  y_primera_etiqueta, y - 10))

    y += 10
    d.line([x_etq, y, x_val, y], fill=NEGRO, width=3)
    y += 14
    _texto(d, (x_etq, y), "TOTAL FACTURA", fuente(23, True))
    _derecha(d, x_val, y, eur(cifras["total"]), fuente(23, True))
    zonas.append(("etiqueta TOTAL FACTURA", x_etq, x_etq + 250, y, y + 30))

    # -- pie: AQUI esta el experimento --------------------------------------
    y_pie = ALTO - 300
    d.line([izq, y_pie, dcha, y_pie], fill=(150, 150, 150))
    y_pie += 20

    nif_pie = nif_del_pie(receta, nif)
    etiqueta_nif = "N.I.F./C.I.F." if receta["nif_pie_con_guiones"] else "NIF"
    _texto(d, (izq, y_pie),
           f"{receta['emisor']}  ·  {etiqueta_nif} {nif_pie}", fuente(17), GRIS)
    _texto(d, (izq, y_pie + 28), receta["direccion"], fuente(17), GRIS)

    if receta["pie"] == PIE_LETRAS:
        linea_total = "SON: " + importe_a_letras(cifras["pie_total"])
    else:
        linea_total = "Total a pagar: " + eur(cifras["pie_total"])
    _texto(d, (izq, y_pie + 70), linea_total, fuente(19, True), (34, 34, 34))
    _texto(d, (izq, y_pie + 104), "Forma de pago: transferencia",
           fuente(17), GRIS)
    # El pie es EL bloque que estas muestras existen para medir: si sale en
    # blanco, la muestra no mide nada y ademas lo pareceria todo correcto.
    zonas.append(("pie: emisor y NIF del margen", izq, izq + 900,
                  y_pie, y_pie + 50))
    zonas.append(("pie: linea del total", izq, izq + 900,
                  y_pie + 66, y_pie + 96))

    _comprobar_hay_tinta(img, receta, zonas)
    return img, nif, nif_pie


#: Cuantos pixeles oscuros bastan para decir "aqui hay algo escrito". Se
#: muestrea de 2 en 2, asi que una sola palabra pequena ya pasa de sobra; el
#: umbral esta para que una raya fina o una mota no cuenten como texto.
MINIMO_PIXELES_OSCUROS = 40


def _comprobar_hay_tinta(img, receta, zonas):
    """Que cada bloque que deberia llevar texto lleve pixeles oscuros de verdad.

    Existe por un defecto real, encontrado el 16-09-2026 en este mismo fichero:
    la tinta por defecto de Pillow sobre RGB es BLANCA, y la primera version
    dibujo el emisor y su NIF invisibles. El script termino en 0, el PNG peso lo
    normal y la unica forma de enterarse fue abrir la imagen. Eso es exactamente
    el falso verde que este proyecto tiene prohibido dar -- un OK que significa
    'no lo he comprobado'.

    No comprueba QUE pone: eso es trabajo del OCR, y es justo lo que se quiere
    medir. Comprueba que hay algo escrito, que es barato y caza la clase entera.

    Las zonas llegan del propio `dibujar()`, derivadas del layout mientras
    dibuja. Escritas a mano se desincronizaban en cuanto una receta cambiaba de
    numero de lineas."""
    px = img.load()
    vacias = []
    for nombre, x0, x1, y0, y1 in zonas:
        oscuros = 0
        for y in range(max(0, y0), min(ALTO, y1), 2):
            for x in range(max(0, x0), min(ANCHO, x1), 2):
                if sum(px[x, y]) < 400:
                    oscuros += 1
                    if oscuros > MINIMO_PIXELES_OSCUROS:
                        break
            if oscuros > MINIMO_PIXELES_OSCUROS:
                break
        if oscuros <= MINIMO_PIXELES_OSCUROS:
            vacias.append(f"{nombre} ({oscuros} pixeles oscuros)")
    if vacias:
        raise AssertionError(
            f"{receta['nombre']}: hay bloques SIN TEXTO VISIBLE en la imagen: "
            + "; ".join(vacias) +
            ". Lo mas probable es un `d.text()` sin `fill`: la tinta por "
            "defecto de Pillow sobre RGB es BLANCA. Usa `_texto()`.")


# ---------------------------------------------------------------------------
# La degradacion
# ---------------------------------------------------------------------------
# Lo que le pasa a una factura entre la impresora y el JSON: alguien la
# fotografia con el movil, torcida, con la sombra de su propia mano encima, y
# la app la comprime. Ninguno de esos pasos es opcional en la vida real, y
# ninguno estaba representado en las muestras que habia.
#
# Todo va con SEMILLA FIJA, derivada del nombre de la receta. La misma receta
# da siempre la misma imagen degradada -- si el ruido fuera aleatorio de verdad,
# dos ejecuciones no se podrian comparar y la muestra dejaria de servir para
# medir nada.

GIRO_GRADOS = -1.4        # el papel nunca queda recto sobre la mesa
DESENFOQUE = 1.1          # el movil enfoca donde puede
SOMBRA_MINIMA = 0.58      # cuanto llega a oscurecer la zona peor iluminada
RUIDO_SIGMA = 11          # ruido de sensor con poca luz
CALIDAD_JPEG = 42         # lo que hace una app de mensajeria con una foto


def _mapa_de_luz(tam, semilla):
    """Una sombra suave y desigual sobre el papel, como una mano o una lampara.

    Se compone pequeno (64x64) y se agranda: asi sale un degradado continuo sin
    recorrer dos millones de pixeles en Python."""
    rnd = random.Random(semilla)
    lado = 64
    # El foco de luz cae en algun sitio de la mitad superior, no en el centro:
    # centrado seria simetrico, y una foto real nunca lo es.
    cx, cy = rnd.uniform(0.25, 0.75), rnd.uniform(0.10, 0.45)
    datos = bytearray(lado * lado)
    for j in range(lado):
        for i in range(lado):
            dx, dy = i / (lado - 1) - cx, j / (lado - 1) - cy
            dist = (dx * dx + dy * dy) ** 0.5
            brillo = 1.0 - (1.0 - SOMBRA_MINIMA) * min(dist / 0.95, 1.0)
            datos[j * lado + i] = int(round(max(0.0, min(1.0, brillo)) * 255))
    return Image.frombytes("L", (lado, lado), bytes(datos)).resize(
        tam, Image.BICUBIC)


def _ruido(tam, semilla):
    """Ruido de sensor, centrado en 128 para poder sumarse sin desplazar el gris.

    Se genera a un tercio de la resolucion y se agranda: el ruido de una camara
    con poca luz sale en grumos, no pixel a pixel, asi que ademas de ser mas
    rapido se parece mas."""
    rnd = random.Random(semilla + 1)
    pequeno = (max(1, tam[0] // 3), max(1, tam[1] // 3))
    datos = bytearray(pequeno[0] * pequeno[1])
    for k in range(len(datos)):
        datos[k] = max(0, min(255, int(128 + rnd.gauss(0, RUIDO_SIGMA))))
    return Image.frombytes("L", pequeno, bytes(datos)).resize(tam, Image.BILINEAR)


def degradar(img, semilla):
    """La misma factura, fotografiada mal. Determinista."""
    from PIL import ImageChops

    # 1. Torcida. `fillcolor` blanco para que las esquinas no salgan negras,
    #    que delataria el giro en vez de simularlo.
    out = img.rotate(GIRO_GRADOS, resample=Image.BICUBIC, expand=False,
                     fillcolor=(255, 255, 255))

    # 2. Luz desigual.
    luz = _mapa_de_luz(out.size, semilla).convert("RGB")
    out = ImageChops.multiply(out, luz)

    # 3. Desenfoque.
    out = out.filter(ImageFilter.GaussianBlur(DESENFOQUE))

    # 4. Ruido de sensor, aditivo: img + (ruido - 128).
    ruido = _ruido(out.size, semilla).convert("RGB")
    out = ImageChops.add(out, ruido, scale=1, offset=-128)

    return out


# ---------------------------------------------------------------------------
# La verdad conocida
# ---------------------------------------------------------------------------
def verdad_conocida(receta, cifras, nif, nif_pie):
    """Lo que el documento dice, con los NOMBRES DE CAMPO DEL CONTRATO.

    Esa eleccion es la que convierte la comparacion en algo mecanico: se lee el
    JSON que devuelve la captura, se lee este, y se comparan claves. Si la
    verdad usara nombres propios habria que traducir a mano cada vez, que es
    justo donde se cuelan los errores de comparacion."""
    dia, mes, ano = receta["fecha"].split("/")
    v = {
        "_muestra": receta["nombre"],
        "_que_mide": receta["mide"],
        "_procedencia": "SINTETICO",
        "nif": nif,
        "proveedor": receta["emisor"],
        "nº_documento": receta["num_documento"],
        "fecha_expedicion": f"{ano}-{mes}-{dia}",
        "base_total": cifras["base_total"],
        "iva_total": cifras["iva_total"],
        "total_factura": cifras["total"],
        # La segunda lectura, desde el pie. En `doble_lectura_descuadre` este
        # valor NO coincide con `total_factura`, y esa es toda la gracia.
        "total_factura_2": cifras["pie_total"],
        "nif_margen": nif_pie,
        "nombre_margen": receta["emisor"],
        "tramos_iva": [{"tipo": t["tipo"], "base": t["base"], "cuota": t["cuota"]}
                       for t in cifras["tramos"]],
    }
    if cifras["retencion"] is not None:
        # EN NEGATIVO, y no por gusto: es la convencion que el propio prompt de
        # captura le pide a la IA -- "retencion de IRPF si aparece, EN NEGATIVO
        # si existe, 0 si no aplica" (captura_orquestador.py). El motor la SUMA
        # (`guard_cuadre_total`: base + IVA + irpf + recargo), asi que con el
        # signo correcto el total cuadra y con el signo cambiado da un descuadre
        # de DOS VECES la retencion.
        #
        # Escrita en positivo estuvo, hasta que se paso esta misma verdad por el
        # motor de verdad: dio ROJO con "total_calc=2720.0 decl=2120.0". Y el
        # dano habria sido el de siempre y del reves: Gemini habria devuelto
        # -300,00 correctamente, la verdad conocida habria dicho 300,00, y la
        # comparacion habria cantado un fallo del modelo que no existia. La
        # regla de medir, torcida otra vez.
        v["irpf_retencion"] = -cifras["retencion"]
    # Campos planos por tipo: solo existen para 21/10/4. El 5% vive unicamente
    # dentro de `tramos_iva` -- es el hueco que el contrato tiene declarado y el
    # motivo por el que ese campo tuvo que arreglarse el 16-09-2026.
    for t in cifras["tramos"]:
        if t["tipo"] in (21, 10, 4):
            v[f"base_{t['tipo']}"] = t["base"]
    return v


def _comprobar_contra_el_contrato(verdad):
    """La verdad conocida, pasada por el contrato real del motor.

    No es decoracion. Si un dia alguien renombra un campo en `contrato_datos.py`
    y aqui se queda el nombre viejo, la comparacion campo a campo empezaria a
    dar 'el modelo no ha traido X' cuando lo que pasa es que X ya no se llama
    asi. Eso costaria una sesion entera de perseguir un fantasma.

    Se comprueba lo que de verdad importa: que los campos criticos y los que
    esta muestra existe para medir SOBREVIVEN al canonizado con valor."""
    import contrato_datos

    fila = {k: v for k, v in verdad.items() if not k.startswith("_")}
    canon = contrato_datos.canonizar(fila)

    obligatorios = list(contrato_datos.CAMPOS_CRITICOS)
    for opcional in ("total_factura_2", "nif_margen", "irpf_retencion"):
        if opcional in fila:
            obligatorios.append(opcional)

    perdidos = []
    for campo in obligatorios:
        estado = canon.estado(campo)
        if estado not in contrato_datos.UTILIZABLES:
            perdidos.append(f"{campo} (estado {estado})")
    if perdidos:
        raise AssertionError(
            f"{verdad['_muestra']}: el contrato no da por utilizables estos "
            f"campos de la verdad conocida: {', '.join(perdidos)}. O el nombre "
            f"del campo ha cambiado, o el valor no tiene la forma que espera.")

    tramos = canon.tramos()
    if len(tramos) != len(verdad["tramos_iva"]):
        raise AssertionError(
            f"{verdad['_muestra']}: el contrato lee {len(tramos)} tramos de "
            f"IVA y la verdad declara {len(verdad['tramos_iva'])}.")


def main():
    _exigir_pillow()
    _autocomprobar_letras()

    raiz = os.path.dirname(os.path.abspath(__file__))
    destino = os.path.join(raiz, CARPETA)
    os.makedirs(destino, exist_ok=True)

    print("=" * 72)
    print("MUESTRAS SINTETICAS — facturas fabricadas, con verdad conocida")
    print("=" * 72)
    print(f"  carpeta: {CARPETA}/   (no se versiona: ver .gitignore)")
    print()

    generadas = []
    for receta in RECETAS:
        cifras = calcular(receta)
        img, nif, nif_pie = dibujar(receta, cifras)

        # Semilla derivada del nombre: estable entre ejecuciones y entre
        # maquinas (`hash()` de Python NO lo es, cambia en cada proceso).
        semilla = sum(ord(c) * (i + 1) for i, c in enumerate(receta["nombre"]))

        limpia = os.path.join(destino, f"{receta['nombre']}_limpia.png")
        degradada = os.path.join(destino, f"{receta['nombre']}_degradada.jpg")
        img.save(limpia, "PNG")
        degradar(img, semilla).save(degradada, "JPEG", quality=CALIDAD_JPEG)

        verdad = verdad_conocida(receta, cifras, nif, nif_pie)
        verdad["_imagenes"] = [os.path.basename(limpia),
                               os.path.basename(degradada)]
        _comprobar_contra_el_contrato(verdad)

        ruta_verdad = os.path.join(destino, f"{receta['nombre']}_verdad.json")
        with open(ruta_verdad, "w", encoding="utf-8") as f:
            json.dump(verdad, f, ensure_ascii=False, indent=2)

        generadas.append((receta, cifras, verdad, limpia, degradada))

        print(f"  · {receta['nombre']}")
        print(f"      {os.path.basename(limpia)}  "
              f"({os.path.getsize(limpia) // 1024} KB)")
        print(f"      {os.path.basename(degradada)}  "
              f"({os.path.getsize(degradada) // 1024} KB)  "
              f"girada {GIRO_GRADOS}°, JPEG q{CALIDAD_JPEG}")
        print(f"      {os.path.basename(ruta_verdad)}")
        print(f"      MIDE: {receta['mide']}")
        print()

    print("-" * 72)
    print("VERDAD CONOCIDA — resumen para comparar de un vistazo")
    print("-" * 72)
    for receta, cifras, verdad, _l, _d in generadas:
        print(f"  {receta['nombre']}")
        print(f"      nº_documento     {verdad['nº_documento']}")
        print(f"      fecha_expedicion {verdad['fecha_expedicion']}")
        print(f"      base_total       {num_es(cifras['base_total'])}")
        print(f"      iva_total        {num_es(cifras['iva_total'])}")
        if cifras["retencion"] is not None:
            print(f"      irpf_retencion   {num_es(cifras['retencion'])}")
        print(f"      total_factura    {num_es(cifras['total'])}")
        marca = "  <-- DISTINTO del cuadro, a proposito" \
            if cifras["pie_total"] != cifras["total"] else ""
        print(f"      total_factura_2  {num_es(cifras['pie_total'])}{marca}")
        marca_nif = "  <-- con guiones, como en el pie" \
            if receta["nif_pie_con_guiones"] else ""
        print(f"      nif_margen       {verdad['nif_margen']}{marca_nif}")
        print(f"      tramos_iva       " + ", ".join(
            f"{t['tipo']}% base {num_es(t['base'])} cuota {num_es(t['cuota'])}"
            for t in cifras["tramos"]))
        print()

    print("-" * 72)
    print("COMO PASARLAS POR LA CADENA")
    print("-" * 72)
    print("  La puerta las deja salir por ser SINTETICAS declaradas: no hace")
    print("  falta DPA ni OS_ASESORIA_DATOS_REALES (ver .claude/rules/datos.md).")
    print()
    print("      set OS_ASESORIA_CLOUD=1                  (Windows; export en Linux)")
    print(f"      python captura_orquestador.py --imagen {CARPETA}/<fichero> \\")
    print("             --procedencia SINTETICO")
    print()
    print("  Y EL ORDEN IMPORTA: primero la _limpia de cada receta. Si la limpia")
    print("  ya falla, la degradada no anade informacion -- el problema no es la")
    print("  foto. Solo cuando la limpia acierta, la degradada mide de verdad")
    print("  cuanto aguanta, porque el documento es EL MISMO.")
    print()
    print("  LIMITE DECLARADO: no se simula la perspectiva (el papel en angulo,")
    print("  con los margenes en trapecio). Que la degradada pase NO significa")
    print("  que una foto torcida en angulo pase: eso no se ha medido.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
