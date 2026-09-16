#!/usr/bin/env python3
"""test_muestras_sinteticas.py — que las muestras midan lo que dicen medir.

POR QUE ESTA BATERIA
----------------------
`crear_muestras_sinteticas.py` fabrica los documentos contra los que se va a
medir el OCR. Si una muestra esta mal, el error no se ve como un error: se ve
como "el modelo no lee bien", y se persigue durante una sesion entera al sitio
equivocado. Una regla de medida torcida es peor que no tener regla.

Ya paso una version en pequeno, el 16-09-2026 y en este mismo fichero: el
emisor y su NIF se dibujaron en BLANCO sobre papel blanco (la tinta por defecto
de Pillow sobre RGB es blanca). El script termino en 0, el PNG peso lo normal y
la verdad conocida decia lo correcto. La unica forma de enterarse fue abrir la
imagen con los ojos.

Asi que esta bateria comprueba las dos mitades:

  1. Que los numeros de cada receta cuadran y que la verdad conocida sobrevive
     al contrato real del motor.
  2. Que el guard de tinta SE PONE ROJO con el defecto reintroducido. Un guard
     que pasa igual con el codigo roto no esta comprobando nada -- misma
     leccion que la FAMILIA G de `test_adversarial.py` y que la bateria de
     `test_puerta_cloud.py`.

REGLA DE DATOS
----------------
Ni un dato real. Los emisores son inventados y los NIF se componen llamando a
`nif_sintetico()`, que calcula el digito de control. No hay ni un literal con
forma de NIF en este fichero.
"""
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import contrato_datos
import crear_muestras_sinteticas as m
import nif_check
from crear_factura_sintetica import eur, nif_sintetico, num_es

resultados = []
saltadas = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


def _falla(fn, excepcion=Exception):
    """True si `fn()` levanta la excepcion esperada. Para probar los rechazos."""
    try:
        fn()
    except excepcion:
        return True
    except Exception:
        return False
    return False


# ---------------------------------------------------------------------------
# 0. El formateo de importes
# ---------------------------------------------------------------------------
# Primero de todo, y con motivo: un importe MALFORMADO en el documento contra
# el que se mide el OCR no se lee como un fallo del documento, se lee como un
# fallo del modelo. Es la peor clase de error que pueden tener estas muestras.
#
# Hubo uno real, dormido desde antes y despertado por la receta `con_retencion`
# (16-09-2026): `num_es(-300.00)` devolvia `-.300,00`, porque la agrupacion de
# miles contaba el signo menos como un digito mas.
def pruebas_formateo():
    casos = {
        # El caso que fallaba, y sus vecinos de los dos lados.
        -300.00: "-300,00", -100.00: "-100,00", -999.99: "-999,99",
        -1000.00: "-1.000,00", -1234.50: "-1.234,50", -1.00: "-1,00",
        # Positivos: lo de siempre, que no puede romperse al arreglar lo otro.
        300.00: "300,00", 0.00: "0,00", 1234.50: "1.234,50",
        1234567.89: "1.234.567,89", 1210.50: "1.210,50",
        # Redondeo del dinero: HALF_UP, no el "mitad al par" de round().
        0.005: "0,01", -0.005: "-0,01", 2.675: "2,68", 999.999: "1.000,00",
        # Y un menos delante de un cero seria mentira.
        -0.004: "0,00",
    }
    for valor, esperado in casos.items():
        obtenido = num_es(valor)
        comprobar(f"num_es({valor}) = {esperado!r}", obtenido == esperado,
                  f"devolvio {obtenido!r}", "P0")

    comprobar("eur() solo anade la moneda a num_es()",
              eur(-300.00) == "-300,00 EUR" and eur(1420.00) == "1.420,00 EUR",
              f"{eur(-300.00)!r} / {eur(1420.00)!r}", "P0")

    # Y que ninguna receta imprima un importe con separador de miles pegado al
    # signo: la forma exacta que tenia el defecto.
    for receta in m.RECETAS:
        c = m.calcular(receta)
        importes = [c["base_total"], c["iva_total"], c["total"], c["pie_total"]]
        if c["retencion"] is not None:
            importes.append(-c["retencion"])
        for t in c["tramos"]:
            importes += [t["base"], t["cuota"]]
        malformados = [f"{v} -> {num_es(v)}" for v in importes
                       if num_es(v).startswith("-.") or num_es(v).startswith(".")]
        comprobar(f"{receta['nombre']}: ningun importe sale malformado",
                  not malformados, "; ".join(malformados), "P0")


# ---------------------------------------------------------------------------
# 1. El importe escrito con letras
# ---------------------------------------------------------------------------
def pruebas_letras():
    comprobar("la autocomprobacion de letras del propio modulo pasa",
              not _falla(m._autocomprobar_letras, AssertionError), severidad="P0")

    # Los que se rompen solos si alguien toca el conversor.
    for n, esperado in ((100, "cien"), (101, "ciento uno"), (1000, "mil"),
                        (1210, "mil doscientos diez"), (21000, "veintiun mil"),
                        (16, "dieciseis"), (0, "cero")):
        comprobar(f"numero_a_letras({n}) = {esperado!r}",
                  m.numero_a_letras(n) == esperado,
                  f"devolvio {m.numero_a_letras(n)!r}")

    comprobar("el apocope se aplica delante de EUROS (veintiun, no veintiuno)",
              m.importe_a_letras(1421.0) == "MIL CUATROCIENTOS VEINTIUN EUROS",
              m.importe_a_letras(1421.0))
    comprobar("los centimos se escriben aparte",
              m.importe_a_letras(1210.50).endswith("CON CINCUENTA CENTIMOS"),
              m.importe_a_letras(1210.50))

    # Fuera de rango NO devuelve algo aproximado: no devuelve nada. Es la misma
    # regla del motor -- si no se puede, no es OK.
    comprobar("fuera de rango levanta en vez de aproximar",
              _falla(lambda: m.numero_a_letras(1000000), ValueError),
              severidad="P0")
    comprobar("un no-entero levanta en vez de redondear por su cuenta",
              _falla(lambda: m.numero_a_letras(12.5), ValueError))


# ---------------------------------------------------------------------------
# 2. El NIF sintetico
# ---------------------------------------------------------------------------
def pruebas_nif():
    comprobar("sin argumentos devuelve el mismo CIF de siempre (no rompe a "
              "quien ya lo llamaba)",
              nif_sintetico() == nif_sintetico("9876543", "B"), severidad="P0")

    for digitos, letra in (("9876543", "B"), ("1234567", "A"), ("2233445", "B")):
        nif = nif_sintetico(digitos, letra)
        valido, tipo, _motivo = nif_check.valida_nif(nif)
        comprobar(f"el CIF compuesto con letra {letra} pasa el validador del "
                  f"proyecto", valido and tipo == "CIF", severidad="P0")

    comprobar("una letra de control ALFABETICO se rechaza en vez de componer "
              "un NIF falso",
              _falla(lambda: nif_sintetico("1234567", "P"), ValueError),
              severidad="P0")
    comprobar("un numero de digitos incorrecto se rechaza",
              _falla(lambda: nif_sintetico("123", "B"), ValueError))


# ---------------------------------------------------------------------------
# 3. La aritmetica de cada receta
# ---------------------------------------------------------------------------
def pruebas_recetas():
    comprobar("hay al menos una receta", len(m.RECETAS) > 0, severidad="P0")

    for receta in m.RECETAS:
        c = m.calcular(receta)
        nombre = receta["nombre"]

        suma_bases = round(sum(t["base"] for t in c["tramos"]), 2)
        suma_cuotas = round(sum(t["cuota"] for t in c["tramos"]), 2)
        comprobar(f"{nombre}: base_total es la suma de las bases",
                  c["base_total"] == suma_bases, severidad="P0")
        comprobar(f"{nombre}: iva_total es la suma de las cuotas",
                  c["iva_total"] == suma_cuotas, severidad="P0")

        for t in c["tramos"]:
            esperada = round(t["base"] * t["tipo"] / 100, 2)
            comprobar(f"{nombre}: la cuota al {t['tipo']}% sale de multiplicar",
                      t["cuota"] == esperada,
                      f"{t['cuota']} vs {esperada}", "P0")

        esperado = round(c["base_total"] + c["iva_total"] - (c["retencion"] or 0), 2)
        comprobar(f"{nombre}: el total cuadra con base + IVA - retencion",
                  c["total"] == esperado, f"{c['total']} vs {esperado}", "P0")

    # La receta de retencion existe para que el total NO sea base + IVA. Si
    # coincidieran, no mediria nada: sumar de memoria y leer darian lo mismo.
    con_ret = [r for r in m.RECETAS if r["retencion_pct"] is not None]
    comprobar("hay una receta con retencion de IRPF", bool(con_ret), severidad="P0")
    for receta in con_ret:
        c = m.calcular(receta)
        comprobar(f"{receta['nombre']}: el total NO es base + IVA (si lo fuera, "
                  f"sumar de memoria y leer serian indistinguibles)",
                  c["total"] != round(c["base_total"] + c["iva_total"], 2),
                  severidad="P0")

    # Y la del descuadre existe para que el pie NO coincida con el cuadro.
    descuadres = [r for r in m.RECETAS if r["pie"] == m.PIE_DESCUADRE]
    comprobar("hay una receta con el pie descuadrado", bool(descuadres),
              severidad="P0")
    for receta in descuadres:
        c = m.calcular(receta)
        comprobar(f"{receta['nombre']}: el pie lleva OTRO importe que el cuadro "
                  f"-- es toda la razon de ser de la receta",
                  c["pie_total"] != c["total"],
                  f"pie {c['pie_total']} vs cuadro {c['total']}", "P0")

    # Sabotaje: una receta declarada como descuadre pero con el pie igual debe
    # ser RECHAZADA, no aceptada en silencio. Seria exactamente el defecto de
    # diseno que estas muestras existen para corregir.
    saboteada = dict(descuadres[0])
    saboteada["pie_total"] = m.calcular(descuadres[0])["total"]
    comprobar("un descuadre declarado pero con el pie IGUAL se rechaza",
              _falla(lambda: m.calcular(saboteada), AssertionError),
              severidad="P0")

    comprobar("dos recetas distintas no comparten nombre de fichero",
              len({r["nombre"] for r in m.RECETAS}) == len(m.RECETAS),
              severidad="P0")


# ---------------------------------------------------------------------------
# 4. La verdad conocida, contra el contrato real del motor
# ---------------------------------------------------------------------------
def pruebas_contrato():
    for receta in m.RECETAS:
        c = m.calcular(receta)
        nif = nif_sintetico(receta["nif_digitos"], receta["nif_letra"])
        nif_pie = (f"{receta['nif_letra']}-{receta['nif_digitos']}-{nif[-1]}"
                   if receta["nif_pie_con_guiones"] else nif)
        verdad = m.verdad_conocida(receta, c, nif, nif_pie)

        comprobar(f"{receta['nombre']}: la verdad pasa el contrato del motor",
                  not _falla(lambda: m._comprobar_contra_el_contrato(verdad),
                             AssertionError),
                  severidad="P0")

        fila = {k: v for k, v in verdad.items() if not k.startswith("_")}
        canon = contrato_datos.canonizar(fila)
        for campo in contrato_datos.CAMPOS_CRITICOS:
            comprobar(f"{receta['nombre']}: {campo} sobrevive al canonizado",
                      canon.estado(campo) in contrato_datos.UTILIZABLES,
                      f"estado {canon.estado(campo)}", "P0")

        comprobar(f"{receta['nombre']}: el 5% solo vive en tramos_iva (no hay "
                  f"campo plano base_5, y es asi a proposito)",
                  "base_5" not in verdad)

        if receta["nif_pie_con_guiones"]:
            comprobar(f"{receta['nombre']}: nif_margen trae la puntuacion del "
                      f"PIE, distinta de la cabecera",
                      verdad["nif_margen"] != verdad["nif"],
                      severidad="P0")


# ---------------------------------------------------------------------------
# 5. El dibujo: el guard de tinta tiene que saber ponerse rojo
# ---------------------------------------------------------------------------
def pruebas_dibujo():
    if m.FALTA_PILLOW is not None:
        saltadas.append(
            "las pruebas de dibujo (guard de tinta y determinismo de la "
            "degradacion): falta Pillow. `pip install -r requirements.txt`. "
            "NO es un aprobado: es que no se ha podido comprobar.")
        return

    for receta in m.RECETAS:
        img, nif, nif_pie = m.dibujar(receta, m.calcular(receta))
        comprobar(f"{receta['nombre']}: la imagen limpia se dibuja sin quejarse",
                  img.size == (m.ANCHO, m.ALTO), str(img.size), "P0")

    # EL SABOTAJE. Se reintroduce el defecto exacto del 16-09: dibujar sin
    # `fill`, que sobre RGB sale BLANCO. El guard tiene que cazarlo en TODAS
    # las recetas. Si pasara alguna, el guard no estaria comprobando nada.
    original = m._texto
    try:
        m._texto = lambda dib, xy, texto, f, color=m.NEGRO: dib.text(xy, texto, font=f)
        for receta in m.RECETAS:
            comprobar(f"{receta['nombre']}: con el texto en BLANCO, el guard de "
                      f"tinta se pone ROJO",
                      _falla(lambda: m.dibujar(receta, m.calcular(receta)),
                             AssertionError),
                      severidad="P0")
    finally:
        m._texto = original

    # Y al deshacer el sabotaje vuelve a pasar: un guard que se queda rojo para
    # siempre tampoco sirve.
    comprobar("deshecho el sabotaje, las tres vuelven a pasar",
              all(not _falla(lambda: m.dibujar(r, m.calcular(r)), AssertionError)
                  for r in m.RECETAS),
              severidad="P0")

    # La degradacion tiene que ser DETERMINISTA: si no, dos ejecuciones no se
    # pueden comparar y la muestra deja de medir.
    receta = m.RECETAS[0]
    limpia, _n, _p = m.dibujar(receta, m.calcular(receta))
    a = m.degradar(limpia, 1234).tobytes()
    b = m.degradar(limpia, 1234).tobytes()
    c = m.degradar(limpia, 9999).tobytes()
    comprobar("degradar con la MISMA semilla da la MISMA imagen",
              a == b, severidad="P0")
    comprobar("degradar con OTRA semilla da otra imagen (el ruido es ruido)",
              a != c)
    comprobar("la degradada no es identica a la limpia",
              a != limpia.tobytes(), severidad="P0")


def main():
    print("=" * 72)
    print("MUESTRAS SINTETICAS — bateria")
    print("=" * 72)
    pruebas_formateo()
    pruebas_letras()
    pruebas_nif()
    pruebas_recetas()
    pruebas_contrato()
    pruebas_dibujo()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")

    if saltadas:
        print("\nNO COMPROBADO (y eso no es un aprobado):")
        for s in saltadas:
            print(f"  ⚠ {s}")

    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1

    print("\nLas recetas cuadran, la verdad conocida sobrevive al contrato del")
    print("motor, y el guard de tinta ha demostrado que sabria ponerse rojo si")
    print("alguien volviera a dibujar en blanco sobre blanco.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
