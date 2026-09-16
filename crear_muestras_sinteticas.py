#!/usr/bin/env python3
"""crear_muestras_sinteticas.py — un banco de facturas fabricadas, en imagen
real y con degradacion simulada, para tener sobre las que trabajar en
CUALQUIER sesion (Cloud incluida) sin esperar a una factura real ni cruzar
la puerta del DPA. Un comando, listas en segundos -- no hace falta que
esten pre-generadas.

POR QUE EXISTE, Y EN QUE SE DIFERENCIA DE crear_factura_sintetica.py
----------------------------------------------------------------------
crear_factura_sintetica.py fabrica UN documento de usar y tirar, pensado
para pasarlo por Gemini una vez (por eso su salida esta en .gitignore: se
regenera cuando hace falta). Este fichero fabrica varias, con conocimiento
explicito de lo que cada una fuerza a probar, y SUS IMAGENES SI SE VERSIONAN
-- son material de referencia para desarrollo, no un test efimero.

[19-09-2026, propuesta de Diego: tener ejemplos "a mano" en sesiones Cloud
sin DPA, quiza anonimizando fotos reales. Descartado ese camino y elegido
este en su lugar -- razonamiento completo en la conversacion de esa fecha,
resumen aqui porque es la decision que explica por que este fichero existe:
con 33 clientes en un mercado local, una factura real "anonimizada" sigue
siendo reidentificable por proveedor+fecha+importe aunque se tape el NIF
(`.claude/rules/datos.md`, seccion de uso secundario), y una imagen es
exactamente el punto ciego que el escaner de privacidad no puede verificar
(`puerta_cloud.py`: "la procedencia de una imagen es una declaracion, no
una medicion"). Cien por cien fabricado evita el problema de raiz en vez de
mitigarlo.]

LAS MUESTRAS, Y QUE FUERZA A PROBAR CADA UNA
-----------------------------------------------
  · mixto_recargo — IVA mixto (21% + 10%) CON recargo de equivalencia,
      calculado con RECARGO_POR_TIPO de contrato_datos.py (no inventado: es
      la tabla que ya usa el motor). El campo escalar recargo_equivalencia
      no habia visto un documento real ni sintetico hasta hoy.
  · doble_lectura — el total y el NIF aparecen en el pie con una REDACCION
      DISTINTA a la de la cabecera (el total tambien escrito en letras, el
      NIF con guiones), no la misma cadena repetida. La sintetica del
      16-09 repetia el mismo texto en los dos sitios: total_factura_2 y
      nif_margen salieron identicos a los de cabecera sin que se pudiera
      saber si la lectura fue independiente o una copia (ver PENDIENTE.md,
      Paso 1). Esta si lo distingue: copiar el primer valor no reproduce
      una redaccion en letras sin haberla leido de verdad.
  · degradada — una copia de doble_lectura con desenfoque, rotacion, poca
      luz y compresion JPEG agresiva aplicados de verdad con Pillow --
      simulando una foto de movil mala sin usar ni un byte de una foto
      real.

Cada imagen lleva su verdad conocida en un .json al lado (mismos nombres de
campo que pide PROMPT_CAPTURA en captura_orquestador.py), para poder
comparar campo a campo en cualquier ensayo futuro sin teclearla a mano.

QUE NO LLEVA, Y POR QUE LA SALIDA NO SE VERSIONA (comprobado, no supuesto)
-----------------------------------------------------------------------------
Ningun NIF real: todos se COMPONEN con digito de control valido en
ejecucion via crear_factura_sintetica.nif_sintetico() (reutilizada, no
copiada: ver el parametro `digitos` que se le anadio para esto -- mismo
algoritmo en un solo sitio, no dos).

Se escribio primero pensando en commitear las imagenes ("tenerlas a mano"),
y se ejecuto `scripts/privacy_scan.py` contra ellas antes de dar nada por
bueno. Bloqueo las dos cosas, correctamente:
  · los .png/.jpg, como binario no reconocido -- una imagen es exactamente
    el punto ciego que el escaner nunca puede verificar por contenido
    (`puerta_cloud.py`: "la procedencia de una imagen es una declaracion,
    no una medicion"), asi que bloquea SIEMPRE, sea real o fabricada.
  · los .json, por el NIF con digito de control valido -- indistinguible
    de uno real para el escaner, aunque compuesto y no literal.
Es el MISMO caso que ya resolvio crear_factura_sintetica.py para su propio
.html, con el mismo motivo: "un NIF escrito como literal haria saltar el
escaner, y ensancharle la lista blanca por comodidad debilitaria la
barrera". La solucion es la misma: la RECETA se versiona (este .py, texto
puro, cero NIF), la SALIDA no -- se regenera con un comando, en segundos.

USO
----
    python crear_muestras_sinteticas.py

Escribe en muestras_sinteticas/ (en .gitignore, igual que las salidas de
crear_factura_sintetica.py).
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

from crear_factura_sintetica import nif_sintetico, eur
from contrato_datos import RECARGO_POR_TIPO

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CARPETA_SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "muestras_sinteticas")

ANCHO, ALTO = 1000, 1300
MARGEN = 60
BLANCO = (255, 255, 255)
NEGRO = (17, 17, 17)
GRIS = (90, 90, 90)
ROJO_AVISO = (150, 0, 0)
FONDO_AVISO = (255, 233, 233)


# ---------------------------------------------------------------------------
# Numero a letras — solo para el pie de "doble_lectura". Ver el docstring del
# modulo: es lo que convierte la segunda lectura en una comprobacion real en
# vez de una cadena repetida.
# ---------------------------------------------------------------------------
_UNIDADES = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
_DIECIS = ["diez", "once", "doce", "trece", "catorce", "quince", "dieciseis",
           "diecisiete", "dieciocho", "diecinueve"]
_DECENAS = ["", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta",
            "setenta", "ochenta", "noventa"]
_CENTENAS = ["", "ciento", "doscientos", "trescientos", "cuatrocientos",
             "quinientos", "seiscientos", "setecientos", "ochocientos",
             "novecientos"]


def _menor_mil(n):
    if n == 0:
        return ""
    if n == 100:
        return "cien"
    c, resto = divmod(n, 100)
    partes = []
    if c:
        partes.append(_CENTENAS[c])
    if resto:
        if resto < 10:
            partes.append(_UNIDADES[resto])
        elif resto < 20:
            partes.append(_DIECIS[resto - 10])
        else:
            d, u = divmod(resto, 10)
            if u == 0:
                partes.append(_DECENAS[d])
            elif d == 2:
                partes.append("veinti" + _UNIDADES[u])
            else:
                partes.append(_DECENAS[d] + " y " + _UNIDADES[u])
    return " ".join(partes)


def numero_a_letras_euros(importe):
    """Un importe (con centimos en .00) a su forma en letras, mayusculas,
    como a veces aparece en el pie de una factura real ("SON: MIL
    DOSCIENTOS DIEZ EUROS"). No cubre millones: no hace falta para una
    factura de PYME/autonomo, y forzarlo seria precision de mas sin
    necesidad real (CLAUDE.md)."""
    entero = round(importe)
    if entero >= 1_000_000:
        raise ValueError("numero_a_letras_euros: no cubre importes de 7 cifras")
    if entero == 0:
        letras = "cero"
    elif entero < 1000:
        letras = _menor_mil(entero)
    else:
        miles, resto = divmod(entero, 1000)
        prefijo = "mil" if miles == 1 else f"{_menor_mil(miles)} mil"
        letras = prefijo + (f" {_menor_mil(resto)}" if resto else "")
    sufijo = "EURO" if entero == 1 else "EUROS"
    return f"{letras.strip().upper()} {sufijo}"


# ---------------------------------------------------------------------------
# Fuentes — con caida a Linux/DejaVu y al bitmap por defecto de Pillow, para
# que esto tambien corra en una sesion Cloud, no solo en este PC con Windows.
# ---------------------------------------------------------------------------
def cargar_fuente(tamano, negrita=False):
    nombres = (["arialbd.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
               if negrita else
               ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"])
    rutas_base = ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/",
                  "/usr/share/fonts/truetype/liberation/", "")
    for base in rutas_base:
        for nombre in nombres:
            try:
                return ImageFont.truetype(base + nombre, tamano)
            except OSError:
                continue
    return ImageFont.load_default()


F_TITULO = cargar_fuente(28, negrita=True)
F_NORMAL = cargar_fuente(18)
F_NEGRITA = cargar_fuente(18, negrita=True)
F_PEQUENA = cargar_fuente(14)
F_TOTAL = cargar_fuente(22, negrita=True)


# ---------------------------------------------------------------------------
# Recetas — cada una con su aritmetica comprobada por asercion ANTES de
# dibujar nada. Si algo no cuadrara, el fallo es de la receta, no del motor
# ni de la lectura -- misma disciplina que crear_factura_sintetica.py.
# ---------------------------------------------------------------------------
def receta_mixto_recargo():
    tramos = [
        {"concepto": "Genero de temporada", "base": 800.00, "tipo": 21},
        {"concepto": "Complementos", "base": 300.00, "tipo": 10},
    ]
    for t in tramos:
        t["cuota"] = round(t["base"] * t["tipo"] / 100, 2)
        t["recargo"] = round(t["base"] * RECARGO_POR_TIPO[t["tipo"]] / 100, 2)

    base_total = round(sum(t["base"] for t in tramos), 2)
    iva_total = round(sum(t["cuota"] for t in tramos), 2)
    recargo_total = round(sum(t["recargo"] for t in tramos), 2)
    total = round(base_total + iva_total + recargo_total, 2)

    return {
        "nombre": "mixto_recargo",
        "emisor": "COMERCIAL EJEMPLO MINORISTA SL",
        "direccion": "Avenida Inventada 12, 00001 Ciudad Ejemplo",
        "nif": nif_sintetico("1122334"),
        "num_documento": "F-2026/00458",
        "fecha_iso": "2026-04-10",
        "fecha_mostrar": "10/04/2026",
        "tramos": tramos,
        "recargo_total": recargo_total,
        "base_total": base_total,
        "iva_total": iva_total,
        "total": total,
        "pie_total_texto": None,   # sin segunda lectura en esta muestra
        "pie_nif_texto": None,
    }


def receta_doble_lectura():
    tramos = [{"concepto": "Servicios de asesoramiento", "base": 1000.00,
               "tipo": 21, "cuota": 210.00, "recargo": 0.0}]
    base_total, iva_total = 1000.00, 210.00
    total = round(base_total + iva_total, 2)
    nif = nif_sintetico("2233445")

    return {
        "nombre": "doble_lectura",
        "emisor": "ASESORAMIENTO EJEMPLO CONSULTORES SL",
        "direccion": "Plaza Inventada 3, 00002 Ciudad Ejemplo",
        "nif": nif,
        "num_documento": "A26/9.104",
        "fecha_iso": "2026-05-02",
        "fecha_mostrar": "02/05/2026",
        "tramos": tramos,
        "recargo_total": 0.0,
        "base_total": base_total,
        "iva_total": iva_total,
        "total": total,
        # Redaccion DISTINTA a la de la cabecera/cuadro -- ver docstring.
        "pie_total_texto": f"SON: {numero_a_letras_euros(total)} ({eur(total)})",
        "pie_nif_texto": f"N.I.F./C.I.F. {nif[0]}-{nif[1:8]}-{nif[8]}",
    }


# ---------------------------------------------------------------------------
# Dibujo
# ---------------------------------------------------------------------------
def dibujar_factura(receta):
    img = Image.new("RGB", (ANCHO, ALTO), BLANCO)
    d = ImageDraw.Draw(img)
    y = MARGEN

    # Aviso, igual que en la version HTML: nunca se ambiguo sobre que esto
    # es fabricado.
    d.rectangle([MARGEN - 10, y, ANCHO - MARGEN + 10, y + 44], fill=FONDO_AVISO,
                outline=ROJO_AVISO, width=2)
    d.text((MARGEN, y + 12), "DOCUMENTO FABRICADO PARA PRUEBAS \u2014 no corresponde "
           "a ninguna empresa ni operacion real.", font=F_PEQUENA, fill=ROJO_AVISO)
    y += 70

    # Cabecera: emisor a la izquierda, datos de factura a la derecha.
    d.text((MARGEN, y), receta["emisor"], font=F_TITULO, fill=NEGRO)
    d.text((MARGEN, y + 36), f"NIF: {receta['nif']}", font=F_NORMAL, fill=NEGRO)
    d.text((MARGEN, y + 58), receta["direccion"], font=F_NORMAL, fill=NEGRO)

    der = ANCHO - MARGEN
    d.text((der, y), "FACTURA", font=F_NEGRITA, fill=NEGRO, anchor="ra")
    d.text((der, y + 26), f"Numero: {receta['num_documento']}", font=F_NORMAL,
           fill=NEGRO, anchor="ra")
    d.text((der, y + 48), f"Fecha: {receta['fecha_mostrar']}", font=F_NORMAL,
           fill=NEGRO, anchor="ra")
    y += 110

    # Tabla de conceptos.
    col_concepto, col_base, col_tipo, col_cuota = MARGEN, 560, 720, 820
    filas_alto = 34
    d.rectangle([MARGEN, y, ANCHO - MARGEN, y + filas_alto], fill=(235, 235, 235))
    d.text((col_concepto + 6, y + 8), "Concepto", font=F_NEGRITA, fill=NEGRO)
    d.text((col_base + 6, y + 8), "Base", font=F_NEGRITA, fill=NEGRO)
    d.text((col_tipo + 6, y + 8), "% IVA", font=F_NEGRITA, fill=NEGRO)
    d.text((col_cuota + 6, y + 8), "Cuota", font=F_NEGRITA, fill=NEGRO)
    y += filas_alto

    for t in receta["tramos"]:
        d.rectangle([MARGEN, y, ANCHO - MARGEN, y + filas_alto], outline=(180, 180, 180))
        d.text((col_concepto + 6, y + 8), t["concepto"], font=F_NORMAL, fill=NEGRO)
        d.text((col_base + 6, y + 8), eur(t["base"]), font=F_NORMAL, fill=NEGRO)
        d.text((col_tipo + 6, y + 8), f"{t['tipo']}%", font=F_NORMAL, fill=NEGRO)
        d.text((col_cuota + 6, y + 8), eur(t["cuota"]), font=F_NORMAL, fill=NEGRO)
        y += filas_alto
        if t.get("recargo"):
            d.rectangle([MARGEN, y, ANCHO - MARGEN, y + filas_alto], outline=(180, 180, 180))
            d.text((col_concepto + 6, y + 8),
                    f"  Recargo de equivalencia ({RECARGO_POR_TIPO[t['tipo']]}%)",
                    font=F_PEQUENA, fill=GRIS)
            d.text((col_cuota + 6, y + 8), eur(t["recargo"]), font=F_PEQUENA, fill=GRIS)
            y += filas_alto

    y += 30
    # Totales, alineados a la derecha.
    ancho_totales = 420
    x_tot = ANCHO - MARGEN - ancho_totales
    for etiqueta, valor in (("Base imponible total", receta["base_total"]),
                            ("Total IVA", receta["iva_total"])):
        d.text((x_tot, y), etiqueta, font=F_NORMAL, fill=NEGRO)
        d.text((x_tot + ancho_totales, y), eur(valor), font=F_NORMAL, fill=NEGRO,
               anchor="ra")
        y += 28
    if receta["recargo_total"]:
        d.text((x_tot, y), "Total recargo de equivalencia", font=F_NORMAL, fill=NEGRO)
        d.text((x_tot + ancho_totales, y), eur(receta["recargo_total"]), font=F_NORMAL,
               fill=NEGRO, anchor="ra")
        y += 28

    y += 6
    d.line([x_tot, y, x_tot + ancho_totales, y], fill=NEGRO, width=2)
    y += 10
    d.text((x_tot, y), "TOTAL FACTURA", font=F_TOTAL, fill=NEGRO)
    d.text((x_tot + ancho_totales, y), eur(receta["total"]), font=F_TOTAL, fill=NEGRO,
           anchor="ra")
    y += 60

    # Pie: aqui vive la segunda lectura, cuando la receta la trae.
    y = ALTO - 140
    d.line([MARGEN, y, ANCHO - MARGEN, y], fill=(180, 180, 180), width=1)
    y += 14
    pie_id = (f"{receta['emisor']}  \u00b7  "
              f"{receta['pie_nif_texto'] or ('NIF ' + receta['nif'])}  \u00b7  "
              f"{receta['direccion']}")
    d.text((MARGEN, y), pie_id, font=F_PEQUENA, fill=GRIS)
    y += 22
    pie_total = receta["pie_total_texto"] or f"Total a pagar: {eur(receta['total'])}"
    d.text((MARGEN, y), f"{pie_total}  \u00b7  Forma de pago: transferencia",
           font=F_PEQUENA, fill=GRIS)

    return img


def degradar(img, semilla_angulo=3.2):
    """Simula una foto de movil mala: rotacion ligera, desenfoque, poca luz
    y compresion JPEG agresiva -- en ese orden, porque es el orden real
    (la camara desenfoca y sub-expone al capturar; la compresion es el
    ULTIMO paso, al guardar). Devuelve la imagen ya en modo RGB, lista para
    guardarse como JPEG con calidad baja por quien la reciba."""
    img = img.rotate(semilla_angulo, expand=True, fillcolor=BLANCO, resample=Image.BICUBIC)
    img = img.filter(ImageFilter.GaussianBlur(radius=1.6))
    img = ImageEnhance.Brightness(img).enhance(0.78)
    img = ImageEnhance.Contrast(img).enhance(0.85)
    return img


def verdad_conocida(receta):
    """Mismos nombres de campo que PROMPT_CAPTURA en captura_orquestador.py,
    para poder comparar el JSON que devuelva un modelo directamente contra
    este fichero, sin traducir nada a mano."""
    tramos_iva = [{"tipo": t["tipo"], "base": t["base"], "cuota": t["cuota"]}
                  for t in receta["tramos"]]
    base_por_tipo = {10: 0.0, 4: 0.0, 21: 0.0}
    for t in receta["tramos"]:
        if t["tipo"] in base_por_tipo:
            base_por_tipo[t["tipo"]] += t["base"]

    verdad = {
        "nif": receta["nif"],
        "proveedor": receta["emisor"],
        "fecha_expedicion": receta["fecha_iso"],
        "nº_documento": receta["num_documento"],
        "base_10": base_por_tipo[10],
        "base_4": base_por_tipo[4],
        "base_21": base_por_tipo[21],
        "base_total": receta["base_total"],
        "iva_total": receta["iva_total"],
        "recargo_equivalencia": receta["recargo_total"],
        "total_factura": receta["total"],
        "tramos_iva": tramos_iva,
    }
    if receta["pie_total_texto"]:
        verdad["total_factura_2"] = receta["total"]
        verdad["nif_margen"] = receta["nif"]
        verdad["nombre_margen"] = receta["emisor"]
        verdad["_nota_doble_lectura"] = (
            "El pie usa una REDACCION DISTINTA (letras/guiones) del mismo "
            "valor -- ver receta_doble_lectura(). Si el modelo devuelve "
            "estos dos campos vacios en vez del valor correcto, la lectura "
            "de la segunda ubicacion fallo; si devuelve el valor SIN "
            "haberlo decodificado de la redaccion distinta, sospechar copia."
        )
    return verdad


def comprobar_aritmetica(receta):
    """Aserciones antes de dibujar: si la receta no cuadra, el fallo es
    nuestro, no del motor ni del modelo. Misma disciplina que
    crear_factura_sintetica.py ("Cuadran a proposito")."""
    suma_bases = round(sum(t["base"] for t in receta["tramos"]), 2)
    suma_cuotas = round(sum(t["cuota"] for t in receta["tramos"]), 2)
    assert suma_bases == receta["base_total"], (receta["nombre"], "base_total")
    assert suma_cuotas == receta["iva_total"], (receta["nombre"], "iva_total")
    for t in receta["tramos"]:
        assert round(t["base"] * t["tipo"] / 100, 2) == t["cuota"], \
            (receta["nombre"], "base*tipo=cuota", t)
    esperado = round(receta["base_total"] + receta["iva_total"]
                      + receta["recargo_total"], 2)
    assert esperado == receta["total"], (receta["nombre"], "total", esperado)


def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    recetas = [receta_mixto_recargo(), receta_doble_lectura()]

    print("=" * 70)
    print("MUESTRAS SINTETICAS — banco de referencia (0 datos reales)")
    print("=" * 70)

    for receta in recetas:
        comprobar_aritmetica(receta)
        img = dibujar_factura(receta)
        ruta_png = os.path.join(CARPETA_SALIDA, f"muestra_{receta['nombre']}.png")
        img.save(ruta_png)

        ruta_json = os.path.join(CARPETA_SALIDA, f"muestra_{receta['nombre']}.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(verdad_conocida(receta), f, ensure_ascii=False, indent=2)

        print(f"  {ruta_png}")
        print(f"  {ruta_json}")

    # La degradada parte de doble_lectura: es la que mas interesa ver
    # sobrevivir a una foto mala, porque es la que prueba lectura
    # independiente, no solo aritmetica.
    receta_base = recetas[1]
    img_limpia = dibujar_factura(receta_base)
    img_mala = degradar(img_limpia)
    ruta_degradada = os.path.join(CARPETA_SALIDA, "muestra_degradada.jpg")
    img_mala.save(ruta_degradada, "JPEG", quality=35)
    ruta_json_degradada = os.path.join(CARPETA_SALIDA, "muestra_degradada.json")
    with open(ruta_json_degradada, "w", encoding="utf-8") as f:
        json.dump(verdad_conocida(receta_base), f, ensure_ascii=False, indent=2)
    print(f"  {ruta_degradada}  (misma verdad que muestra_doble_lectura, "
          f"con desenfoque+rotacion+poca luz+JPEG agresivo)")
    print(f"  {ruta_json_degradada}")

    print()
    print("Esta carpeta NO se versiona (mismo motivo que factura_sintetica_*:")
    print("lleva un NIF con digito de control valido, indistinguible de uno")
    print("real para el escaner de privacidad). Se regenera con este mismo")
    print("comando cada vez que haga falta -- tarda segundos.")
    print()
    print("Para ejercitar la cadena de verdad con Gemini contra alguna, igual")
    print("que con crear_factura_sintetica.py:")
    print("    set OS_ASESORIA_CLOUD=1")
    print("    python captura_orquestador.py --imagen "
          f"{os.path.relpath(ruta_png, os.path.dirname(os.path.abspath(__file__)))} "
          "--procedencia SINTETICO")
    return 0


if __name__ == "__main__":
    sys.exit(main())
