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
    # OJO con lo que esta prueba puede y no puede demostrar. Comparar
    # `nif_sintetico()` con `nif_sintetico("9876543", "B")` NO detecta un cambio
    # de los valores por defecto: si alguien los cambia, cambian los dos lados y
    # la prueba sigue pasando. Se deja porque SI detecta que la firma deje de
    # aceptar argumentos o que el camino por defecto se desvie del explicito --
    # pero se dice lo que prueba, en vez de dejar que parezca que prueba mas.
    por_defecto = nif_sintetico()
    comprobar("el camino por defecto y el explicito dan lo mismo",
              por_defecto == nif_sintetico("9876543", "B"), severidad="P0")
    # Y esto si son propiedades, no una tautologia: se cumplen o no, al margen
    # de cuales sean los valores por defecto.
    valido, tipo, _mot = nif_check.valida_nif(por_defecto)
    comprobar("el CIF por defecto es valido, de tipo CIF y de 9 caracteres",
              valido and tipo == "CIF" and len(por_defecto) == 9,
              f"{tipo}, valido={valido}, {len(por_defecto)} caracteres", "P0")
    comprobar("y su letra de organizacion es de control NUMERICO",
              por_defecto[0] in __import__("crear_factura_sintetica")
              .LETRAS_CONTROL_NUMERICO, severidad="P0")

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
#: Los numeros que CADA receta tiene que dar, escritos AQUI y a mano.
#:
#: Esto no es duplicar `calcular()`: es lo contrario. La version anterior de
#: esta bateria comprobaba que `base_total` fuera la suma de las bases -- y
#: `calcular()` lo construye COMO la suma de las bases, asi que la prueba no
#: podia fallar nunca. Igual con el IVA y con cada cuota: se recalculaba
#: exactamente lo mismo que se estaba comprobando. Una bateria que pasa igual
#: con el codigo roto no esta comprobando nada (FAMILIA G de
#: test_adversarial.py, y la misma leccion de test_puerta_cloud.py).
#:
#: Con los valores escritos a mano, un cambio en `calcular()` O en una receta
#: tiene que pasar por aqui. Anadir una receta obliga a declarar sus numeros,
#: que es exactamente la friccion que se quiere.
ESPERADO = {
    "doble_lectura_letras": {
        "tramos": ((21, 1000.00, 210.00), (5, 200.00, 10.00)),
        "base_total": 1200.00, "iva_total": 220.00, "retencion": None,
        "total": 1420.00, "pie_total": 1420.00,
    },
    "doble_lectura_descuadre": {
        "tramos": ((21, 1000.00, 210.00),),
        "base_total": 1000.00, "iva_total": 210.00, "retencion": None,
        # El pie NO coincide con el total: dos digitos permutados.
        "total": 1210.00, "pie_total": 1120.00,
    },
    "con_retencion": {
        "tramos": ((21, 2000.00, 420.00),),
        "base_total": 2000.00, "iva_total": 420.00, "retencion": 300.00,
        # 2000 + 420 - 300. NO es base + IVA, y ese es el punto de la receta.
        "total": 2120.00, "pie_total": 2120.00,
    },
}


def pruebas_recetas():
    comprobar("hay al menos una receta", len(m.RECETAS) > 0, severidad="P0")

    # Que no haya recetas sin numeros declarados ni numeros sin receta: si no,
    # se podria anadir una receta y que esta bateria no la mirase.
    nombres = {r["nombre"] for r in m.RECETAS}
    comprobar("toda receta tiene sus numeros declarados en ESPERADO",
              nombres == set(ESPERADO),
              f"solo en RECETAS: {nombres - set(ESPERADO)} | "
              f"solo en ESPERADO: {set(ESPERADO) - nombres}", "P0")

    for receta in m.RECETAS:
        nombre = receta["nombre"]
        if nombre not in ESPERADO:
            continue
        c, e = m.calcular(receta), ESPERADO[nombre]

        for campo in ("base_total", "iva_total", "retencion", "total",
                      "pie_total"):
            comprobar(f"{nombre}: {campo} = {e[campo]}",
                      c[campo] == e[campo], f"salio {c[campo]}", "P0")

        salieron = tuple((t["tipo"], t["base"], t["cuota"]) for t in c["tramos"])
        comprobar(f"{nombre}: los tramos de IVA son los declarados",
                  salieron == e["tramos"], f"salieron {salieron}", "P0")

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
        # Se PIDE el del modulo, no se recalcula aqui: recalcularlo seria
        # comprobar esta bateria contra si misma, y un cambio del formato en el
        # dibujo pasaria desapercibido.
        nif_pie = m.nif_del_pie(receta, nif)
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


# ---------------------------------------------------------------------------
# 6. La verdad conocida, pasada por el MOTOR de verdad
# ---------------------------------------------------------------------------
# Esto existe por una afirmacion que se escribio en la documentacion antes de
# medirla: "el motor deberia ponerse ROJO" con la receta del descuadre. Resulto
# ser cierta -- pero al ir a comprobarla aparecio otra cosa que no lo era.
#
# `con_retencion` daba ROJO con `total_calc=2720.0 decl=2120.0`, y NO era un
# fallo del motor: la verdad conocida escribia la retencion en POSITIVO. El
# prompt de captura le pide a la IA "retencion de IRPF si aparece, EN NEGATIVO
# si existe", y `guard_cuadre_total` la SUMA (base + IVA + irpf + recargo). Con
# el signo cambiado el descuadre es de dos veces la retencion.
#
# El dano habria sido del reves y peor: Gemini habria devuelto -300,00 bien, la
# verdad habria dicho 300,00, y la comparacion habria cantado un fallo del
# modelo que no existia.
#
#: El veredicto que el motor tiene que dar sobre CADA verdad conocida.
VEREDICTO_ESPERADO = {
    # AMBAR y no VERDE, y no es un defecto: la verdad conocida describe el
    # DOCUMENTO, y `verificacion` (la confianza que el modelo declara de su
    # propia lectura) no es una propiedad del papel -- la pone la captura. Sin
    # ella el motor dice NO_COMPROBADO y baja a AMBAR, que es exactamente lo que
    # tiene que hacer: si no se ha podido comprobar, no es OK.
    "doble_lectura_letras": ("AMBAR", None),
    "con_retencion": ("AMBAR", None),
    # ROJO, y por el guard concreto: no vale que salga rojo por otra cosa.
    "doble_lectura_descuadre": ("ROJO", "doble_lectura_total"),
}


def pruebas_motor():
    from motor_veredicto import evaluar_fila_v4

    comprobar("toda receta tiene veredicto esperado declarado",
              {r["nombre"] for r in m.RECETAS} == set(VEREDICTO_ESPERADO),
              severidad="P0")

    for receta in m.RECETAS:
        nombre = receta["nombre"]
        if nombre not in VEREDICTO_ESPERADO:
            continue
        c = m.calcular(receta)
        nif = nif_sintetico(receta["nif_digitos"], receta["nif_letra"])
        verdad = m.verdad_conocida(receta, c, nif, m.nif_del_pie(receta, nif))
        fila = {k: v for k, v in verdad.items() if not k.startswith("_")}

        # alta_cliente_anio=2020 para que `fecha_posterior_alta` no falle por
        # una fecha de 2026; no influye en lo que se mide aqui.
        veredicto, motivo, guards = evaluar_fila_v4(
            fila, set(), {}, {}, {}, {}, 2020, None, None)
        esperado, guard_culpable = VEREDICTO_ESPERADO[nombre]

        comprobar(f"{nombre}: el motor da {esperado}", veredicto == esperado,
                  f"dio {veredicto}: {motivo}", "P0")

        fallos = [k for k, est in guards.items() if est[0] == "FALLO"]
        if guard_culpable:
            comprobar(f"{nombre}: y el guard que falla es {guard_culpable}",
                      fallos == [guard_culpable],
                      f"fallaron {fallos or 'ninguno'}", "P0")
        else:
            comprobar(f"{nombre}: y ningun guard esta en FALLO",
                      not fallos, f"fallaron {fallos}", "P0")

    # El signo de la retencion, fijado contra su autoridad: el prompt.
    con_ret = [r for r in m.RECETAS if r["retencion_pct"] is not None]
    for receta in con_ret:
        c = m.calcular(receta)
        nif = nif_sintetico(receta["nif_digitos"], receta["nif_letra"])
        verdad = m.verdad_conocida(receta, c, nif, m.nif_del_pie(receta, nif))
        comprobar(f"{receta['nombre']}: irpf_retencion va en NEGATIVO, como "
                  f"pide el prompt de captura",
                  verdad["irpf_retencion"] < 0,
                  f"vale {verdad['irpf_retencion']}", "P0")
        comprobar(f"{receta['nombre']}: base + IVA + irpf = total (por eso el "
                  f"signo importa)",
                  round(verdad["base_total"] + verdad["iva_total"]
                        + verdad["irpf_retencion"], 2) == verdad["total_factura"],
                  severidad="P0")


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
    pruebas_motor()

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
