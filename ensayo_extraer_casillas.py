#!/usr/bin/env python3
"""ensayo_extraer_casillas.py — ensayo de la lectura de casillas del 303.

POR QUE EXISTE, Y POR QUE NO EXISTIA ANTES
--------------------------------------------
`extraer_303_pdf.py` es la pieza de la que cuelga TODO el cuadre contra el 303
presentado: `verificar_303_pdf.py` importa su `extraer_casillas()` y
`patron_casilla()` en vez de reescribirlos, precisamente para que las dos
lecturas no puedan divergir. Y hasta hoy no tenia ni una prueba.

Se notaba en el codigo: el comentario de `patron_casilla()` decia, literalmente,
que los patrones eran "variantes razonables porque NO SE HA VISTO NI UN SOLO
DOCUMENTO REAL". Tres formas adivinadas, cero contrastadas, y un 1,2% de
consistencia interna que se atribuyo a la rejilla del PDF.

QUE SE VIO EL 14-09-2026, con el formulario delante
-----------------------------------------------------
En el 303 cada casilla es una REJILLA: un recuadro con el numero a dos digitos
y, al lado, el recuadro del valor. Aplanado a texto queda

    07 9.999,99 08 21,00 09 2.099,99

y ahi salieron DOS defectos, los dos medidos antes de tocar nada:

 1. Ninguna de las tres variantes adivinadas casa con ese "07" suelto -- pero
    `\\b0?9\\s*[.\\)]` SI casaba con el "9." de DENTRO de "9.999,99", porque el
    punto de millar espanol es identico a la marca de una lista numerada. El
    extractor no encontraba la casilla 07 y se inventaba una casilla 02 = 99,99
    y una casilla 09 = 999,99, leyendo trozos de los importes.
 2. La ventana de 80 caracteres no respetaba la casilla siguiente. Una casilla
    vacia se quedaba con el valor de la de al lado -- y en el 303 los tramos
    del 4% y del 10% vienen vacios casi siempre.

AVISO QUE NO SE PUEDE OMITIR: todo esto se prueba contra una RECONSTRUCCION de
la rejilla, con cifras inventadas. En Cloud no hay ni puede haber un PDF real.
Lo que dira si el arreglo sirve de verdad es la tasa de consistencia de
`extraer_303_pdf.py` sobre el archivo real, en el PC de la asesoria.
"""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from extraer_303_pdf import (extraer_casillas, patron_casilla,
                              extraer_numero_tras, localizar_valor_casilla,
                              TIPOS_LEGALES, TOL_TIPO,
                              veredicto_lectura,
                              conceptos_que_no_podemos_tener,
                              FORMULAS_IMPRESAS_VERIFICADAS, FORMULA_45_VERIFICADA,
                              SUMANDOS_TOTAL_DEVENGADO, SUMANDOS_TOTAL_A_DEDUCIR,
                              BASES_DEVENGADO, BASES_DEDUCIBLE, CASILLAS_DE_TIPO)

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK   {titulo}")
    else:
        print(f"  FALLA  {titulo}" + (f"   {detalle}" if detalle else ""))
        FALLOS.append(titulo)


#: La rejilla del 303 tal como se ve en el formulario, con cifras INVENTADAS
#: de la misma forma. Los tramos del 4% y del 10% vacios, que es lo normal.
#: base 9.999,99 al 21% -> cuota 2.099,99 (aritmetica coherente a proposito:
#: si el lector acierta, la auto-validacion del script tiene que aprobarlo).
REJILLA = "\n".join([
    "01 02 4,00 03",
    "04 05 10,00 06",
    "07 9.999,99 08 21,00 09 2.099,99",
    "10 11",
    "12 3.000,00 13 630,00",
    "27 2.729,99",
    "28 1.111,11 29 233,33",
    "45 233,33",
])


def main():
    print("=== ENSAYO: leer las casillas del 303 sin inventarse ninguna ===\n")

    print("A. La rejilla real: base y cuota del tramo con datos")
    v = extraer_casillas(REJILLA)
    comprobar("casilla 07 (base del 21%) se encuentra y vale lo que pone",
              v.get(7) == 9999.99, f"07={v.get(7)}")
    comprobar("casilla 09 (cuota del 21%) idem", v.get(9) == 2099.99, f"09={v.get(9)}")
    comprobar("casilla 28 (base deducible) idem", v.get(28) == 1111.11, f"28={v.get(28)}")
    comprobar("casilla 29 (cuota deducible) idem", v.get(29) == 233.33, f"29={v.get(29)}")

    print("\nB. Las casillas VACIAS no se quedan con el valor de la siguiente")
    # Regresion directa: con la ventana sin cortar, la casilla 01 leia 4,00 --
    # que ni siquiera es un importe, es el TIPO de la casilla 02.
    for n in (1, 3, 4, 6):
        comprobar(f"casilla {n:02d} vacia se queda vacia, no hereda",
                  n not in v, f"{n:02d}={v.get(n)}")

    print("\nC. Las casillas de TIPO son tipo, y se leen como tal")
    # 02, 05 y 08 no son importes: son el porcentaje. Leerlas bien no estorba
    # (verificar_303_pdf.py suma 1+4+7 y 3+6+9, nunca 2/5/8) y sirve de control.
    comprobar("casilla 02 lee el 4,00 del tipo, no un importe", v.get(2) == 4.0, f"02={v.get(2)}")
    comprobar("casilla 08 lee el 21,00 del tipo", v.get(8) == 21.0, f"08={v.get(8)}")

    print("\nD. EL DEFECTO PRINCIPAL: no casar con digitos DENTRO de un importe")
    # "9.999,99" lleva un "9." que es identico a la marca de lista "9.".
    solo_importe = "9.999,99"
    comprobar("la casilla 09 no se encuentra dentro del importe 9.999,99",
              patron_casilla(9).search(solo_importe) is None,
              f"casa con {solo_importe!r}")
    comprobar("ni la 02 dentro de 2.099,99",
              patron_casilla(2).search("2.099,99") is None)
    comprobar("ni la 01 dentro de 1.319,90",
              patron_casilla(1).search("1.319,90") is None)
    comprobar("sobre la fila entera no aparecen casillas fantasma",
              set(extraer_casillas("07 9.999,99 08 21,00 09 2.099,99")) == {7, 8, 9},
              f"{sorted(extraer_casillas('07 9.999,99 08 21,00 09 2.099,99'))}")

    print("\nE. La etiqueta no se funde con su valor por el separador de espacio")
    # contrato_datos acepta el espacio como separador de millar (y hace bien:
    # en el archivo real los hay). Sin cortar por la etiqueta siguiente,
    # "29 233,33" se leia como UN numero: 29.233,33.
    v_ded = extraer_casillas("28 1.111,11 29 233,33")
    comprobar("la casilla 28 no se traga '29 233,33' como 29.233,33",
              v_ded.get(28) == 1111.11, f"28={v_ded.get(28)}")
    comprobar("y la 29 vale 233,33, no 29.233,33",
              v_ded.get(29) == 233.33, f"29={v_ded.get(29)}")

    print("\nF. Casillas de dos digitos (las oficiales que usa verificar_303_pdf)")
    for n, esperado in ((12, 3000.00), (13, 630.00), (27, 2729.99), (45, 233.33)):
        m = patron_casilla(n).search(REJILLA)
        leido = extraer_numero_tras(REJILLA, m.end()) if m else None
        comprobar(f"casilla {n} se localiza y vale lo que pone",
                  leido == esperado, f"{n}={leido} (esperado {esperado})")

    print("\nG. Lo que NO puede confundirse con una etiqueta de casilla")
    comprobar("un anio (2024) no se toma por la casilla 20 ni la 24",
              patron_casilla(24).search("ejercicio 2024") is None
              and patron_casilla(20).search("ejercicio 2024") is None)
    comprobar("un porcentaje (100,00 %) no se toma por la casilla 10",
              patron_casilla(10).search("65 100,00 %") is None
              or extraer_numero_tras("65 100,00 %",
                                     patron_casilla(10).search("65 100,00 %").end()) is None)
    comprobar("un tipo de recargo (1,75) no se toma por la casilla 75",
              patron_casilla(75).search("157 1,75 158") is None)

    print("\nH. Con la lectura buena, la auto-validacion del script APRUEBA")
    # Es la comprobacion que produce la "tasa de consistencia": cuota/base
    # tiene que caer en un tipo legal. Si el lector acierta, aprueba; con los
    # valores que sacaba antes (999,99 y 99,99) no habia manera.
    base_v, cuota_v = v.get(7), v.get(9)
    tipo_efectivo = round(cuota_v / base_v * 100, 2)
    comprobar("cuota/base del tramo leido da un tipo legal (21%)",
              any(abs(tipo_efectivo - t) <= TOL_TIPO for t in TIPOS_LEGALES),
              f"tipo efectivo={tipo_efectivo}")
    comprobar("y la base es mayor que la cuota, como en cualquier 303 real",
              base_v >= cuota_v)

    print("\nI. EL CUADRE INTERNO: el impreso contra su propia aritmetica")
    # No es una heuristica: el 303 lleva sus sumas IMPRESAS al lado de cada
    # total (27 = 152+167+03+155+06+09+11+13+15+..., 45 = 29+31+...,
    # 46 = 27-45). Si leemos bien, cuadra al centimo. Cifras inventadas.
    bien = {3: 100.00, 9: 2099.99, 13: 420.00,        # devengado
            29: 233.33, 41: 50.00,                     # deducible
            27: 2619.99, 45: 283.33, 46: 2336.66}
    estado, detalle = veredicto_lectura(bien)
    comprobar("un PDF bien leido sale OK", estado == "OK", f"{estado} {detalle}")
    comprobar("y se han comprobado las tres formulas",
              set(detalle) == {"devengado", "deducible", "resultado_46"}, str(set(detalle)))

    # Un solo sumando mal leido rompe la suma del impreso: eso es lo que
    # distingue "el PDF se ha leido mal" de "la contabilidad no cuadra".
    mal = dict(bien); mal[9] = 999.99
    estado_mal, detalle_mal = veredicto_lectura(mal)
    comprobar("un sumando mal leido lo delata", estado_mal == "FALLO", estado_mal)
    comprobar("y dice en que lado y por cuanto",
              detalle_mal["devengado"]["diferencia"] == 1100.0,
              str(detalle_mal["devengado"]))
    comprobar("sin acusar al lado que si cuadra",
              detalle_mal["deducible"]["cuadra"], str(detalle_mal["deducible"]))

    # SIN TOTAL NO HAY APROBADO. Es la regla del motor: si no se ha podido
    # comprobar, no es OK.
    estado_sin, detalle_sin = veredicto_lectura({3: 100.0, 9: 2099.99})
    comprobar("sin ningun total leido sale NO_COMPROBADO, nunca OK",
              estado_sin == "NO_COMPROBADO", estado_sin)
    comprobar("y no se inventa ninguna formula comprobada", detalle_sin == {}, str(detalle_sin))

    # Una casilla vacia vale 0 en el impreso: no puede romper el cuadre.
    solo_21 = {9: 2099.99, 27: 2099.99, 29: 233.33, 45: 233.33, 46: 1866.66}
    comprobar("un impreso con casi todo vacio cuadra igual",
              veredicto_lectura(solo_21)[0] == "OK", str(veredicto_lectura(solo_21)))

    # Un modelo de ejercicio antiguo no lleva las casillas 150-170: sumar un
    # superconjunto tiene que ser seguro.
    comprobar("un modelo antiguo, sin las casillas 150-170, tambien cuadra",
              veredicto_lectura({3: 50.0, 6: 25.0, 9: 100.0, 27: 175.0,
                                 29: 75.0, 45: 75.0, 46: 100.0})[0] == "OK")

    # Y el margen: dos decimales por casilla, quince sumandos.
    casi = dict(bien); casi[27] = 2620.02
    comprobar("tres centimos de redondeo no se cuentan como error",
              veredicto_lectura(casi)[0] == "OK", str(veredicto_lectura(casi)[1].get("devengado")))
    lejos = dict(bien); lejos[27] = 2621.99
    comprobar("dos euros si", veredicto_lectura(lejos)[0] == "FALLO")

    print("\nJ. Avisar de lo que NO PODEMOS tener, antes de que busque un bug")
    # EMPEZAR_AQUI.md lo dice desde el principio: "no reconstruye un 303. Un
    # 303 lleva prorrata, bienes de inversion, ISP y compensacion de cuotas, y
    # nada de eso se deduce de las cuentas de IVA". Si una de esas casillas
    # trae importe, el caso NO PUEDE cuadrar -- y callarlo cuesta una tarde
    # buscando un bug que no existe. Cifras inventadas.
    normal = {3: 100.0, 9: 2099.99, 29: 233.33, 27: 2199.99, 45: 233.33}
    comprobar("un 303 corriente no dispara ningun aviso",
              conceptos_que_no_podemos_tener(normal) == [],
              str(conceptos_que_no_podemos_tener(normal)))

    con_prorrata = dict(normal); con_prorrata[44] = -312.45
    avisos = conceptos_que_no_podemos_tener(con_prorrata)
    comprobar("la regularizacion de prorrata (casilla 44) se avisa",
              len(avisos) == 1 and "prorrata" in avisos[0]["concepto"], str(avisos))
    comprobar("y dice la casilla y el importe, para poder cuadrarlo a mano",
              avisos[0]["casillas"] == {44: -312.45}, str(avisos[0]["casillas"]))

    con_recargo = dict(normal); con_recargo[24] = 88.40
    a_rec = conceptos_que_no_podemos_tener(con_recargo)
    comprobar("el recargo de equivalencia se avisa (su tipo no esta en TIPOS_LEGALES)",
              len(a_rec) == 1 and "recargo" in a_rec[0]["concepto"], str(a_rec))

    con_importacion = dict(normal); con_importacion[33] = 1200.0
    comprobar("el IVA de importaciones se avisa",
              any("importacion" in c["concepto"]
                  for c in conceptos_que_no_podemos_tener(con_importacion)))

    # Un CERO en esas casillas es lo normal en un impreso: no puede avisar.
    con_ceros = dict(normal); con_ceros.update({43: 0.0, 44: 0.0, 42: 0.0, 24: 0.0})
    comprobar("una casilla a cero NO dispara aviso (seria ruido en cada 303)",
              conceptos_que_no_podemos_tener(con_ceros) == [],
              str(conceptos_que_no_podemos_tener(con_ceros)))

    # Varias a la vez se declaran todas, no solo la primera.
    varias = dict(normal); varias.update({44: -100.0, 42: 50.0, 24: 10.0})
    comprobar("si hay varios conceptos, se declaran todos",
              len(conceptos_que_no_podemos_tener(varias)) == 3,
              str([c["concepto"] for c in conceptos_que_no_podemos_tener(varias)]))

    # Una casilla de TIPO (un porcentaje preimpreso) no puede disparar nada.
    con_tipos = dict(normal); con_tipos.update({17: 5.2, 20: 1.4, 23: 5.2, 157: 1.75})
    comprobar("un porcentaje preimpreso del recargo no dispara el aviso",
              conceptos_que_no_podemos_tener(con_tipos) == [],
              str(conceptos_que_no_podemos_tener(con_tipos)))

    print("\nK. Las formulas, contra el impreso oficial de CADA ANIO")
    # El corpus va de 2016 a 2026 y el 303 ha cambiado. Estas formulas se
    # leyeron de los PDF oficiales de la AEAT (2022, 2023, 2024) y del
    # formulario de 2026. Si alguien recorta las constantes, esto se pone rojo.
    nuestros_27 = set(SUMANDOS_TOTAL_DEVENGADO)
    for anio, formulas in sorted(FORMULAS_IMPRESAS_VERIFICADAS.items()):
        faltan = set(formulas[27]) - nuestros_27
        comprobar(f"sumamos TODAS las casillas de la 27 del impreso de {anio}",
                  not faltan, f"faltan: {sorted(faltan)}")

    comprobar("la 45 es exactamente la del impreso (identica 2022-2026)",
              set(FORMULA_45_VERIFICADA) == set(SUMANDOS_TOTAL_A_DEDUCIR),
              f"nosotros={sorted(SUMANDOS_TOTAL_A_DEDUCIR)} "
              f"impreso={sorted(FORMULA_45_VERIFICADA)}")

    # La 27 solo crece: la de un anio tiene que estar contenida en la del
    # siguiente. Si eso dejara de cumplirse, el superconjunto no valdria y
    # habria que elegir formula por anio.
    anios = sorted(FORMULAS_IMPRESAS_VERIFICADAS)
    for previo, actual in zip(anios, anios[1:]):
        comprobar(f"la 27 de {previo} esta contenida en la de {actual} (solo crece)",
                  set(FORMULAS_IMPRESAS_VERIFICADAS[previo][27])
                  <= set(FORMULAS_IMPRESAS_VERIFICADAS[actual][27]),
                  f"{previo} tiene de mas: "
                  f"{sorted(set(FORMULAS_IMPRESAS_VERIFICADAS[previo][27]) - set(FORMULAS_IMPRESAS_VERIFICADAS[actual][27]))}")

    # Y que el superconjunto funciona DE VERDAD: un impreso de 2022, sin las
    # casillas de tipos reducidos temporales, tiene que cuadrar igual.
    de_2022 = {3: 500.0, 9: 1000.0, 13: 200.0, 27: 1700.0,
               29: 300.0, 45: 300.0, 46: 1400.0}
    comprobar("un impreso de 2022 cuadra con la formula de 2026 (superconjunto)",
              veredicto_lectura(de_2022)[0] == "OK", str(veredicto_lectura(de_2022)))

    print("\nL. Las tres columnas del impreso no se pisan entre si")
    # El impreso de 2022 agrupa las casillas POR COLUMNA. Eso da una
    # confirmacion INDEPENDIENTE: la columna de cuotas del devengado es,
    # casilla por casilla, la formula de la 27. Si las dos dejaran de
    # coincidir, una de las dos transcripciones esta mal.
    cuotas_dev = set(SUMANDOS_TOTAL_DEVENGADO)
    bases_dev = set(BASES_DEVENGADO)
    tipos = set(CASILLAS_DE_TIPO)
    comprobar("ninguna casilla es a la vez base y cuota del devengado",
              not (cuotas_dev & bases_dev), f"repetidas: {sorted(cuotas_dev & bases_dev)}")
    comprobar("ninguna casilla de TIPO se cuela entre las bases o las cuotas",
              not (tipos & (cuotas_dev | bases_dev)),
              f"repetidas: {sorted(tipos & (cuotas_dev | bases_dev))}")
    comprobar("las tres columnas del devengado tienen el mismo numero de filas",
              len(cuotas_dev) == len(bases_dev) == 15,
              f"cuotas={len(cuotas_dev)} bases={len(bases_dev)}")

    cuotas_ded = set(SUMANDOS_TOTAL_A_DEDUCIR)
    bases_ded = set(BASES_DEDUCIBLE)
    comprobar("ninguna casilla es a la vez base y cuota del deducible",
              not (cuotas_ded & bases_ded), f"repetidas: {sorted(cuotas_ded & bases_ded)}")
    # 42, 43 y 44 no tienen columna de base en el impreso: son un importe
    # suelto. Por eso el deducible tiene 10 cuotas y solo 7 bases.
    comprobar("el deducible tiene 7 bases y 10 cuotas (42, 43 y 44 no llevan base)",
              len(bases_ded) == 7 and len(cuotas_ded) == 10,
              f"bases={len(bases_ded)} cuotas={len(cuotas_ded)}")

    # Y la comprobacion que de verdad ata las dos lecturas: en el impreso,
    # cada fila del deducible es (base, cuota) con la base impar-1. Si la
    # transcripcion de una columna estuviera desplazada, esto cae.
    parejas = [(28,29),(30,31),(32,33),(34,35),(36,37),(38,39),(40,41)]
    comprobar("cada base del deducible va con la cuota siguiente, como en el impreso",
              all(b in bases_ded and c in cuotas_ded for b, c in parejas),
              str([(b,c) for b,c in parejas if b not in bases_ded or c not in cuotas_ded]))

    print("\nM. EL BUG REAL (SP_C_13, 2025T2): una coincidencia mas temprana")
    print("   no puede tapar el valor de verdad que viene despues")
    # Encontrado con un diagnostico ciego (solo distancias en caracteres,
    # ningun importe): la casilla 07 tenia dato en el PDF real y
    # extraer_casillas() la devolvia como no encontrada. Causa: su etiqueta
    # "07" aparece SUELTA mas de una vez en el documento (una fecha, un
    # codigo, la formula impresa que cita otras casillas...), y el codigo
    # viejo se quedaba con la PRIMERA aparicion aunque no llevara ningun
    # numero detras -- nunca llegaba a probar la de la rejilla de verdad.
    #
    # Cifras inventadas, misma FORMA que el caso real: una fecha con "07"
    # suelto, sin importe cerca (otra etiqueta se cruza antes), y mas abajo
    # la rejilla de verdad con la casilla 07 rellena.
    texto_con_fecha_antes = "\n".join([
        "Periodo: 07 08 2025",     # "07" fantasma: justo detras viene "08",
                                    # otra etiqueta, nunca un importe
        "01 02 4,00 03",
        "04 05 10,00 06",
        "07 9.999,99 08 21,00 09 2.099,99",
    ])
    v_fecha = extraer_casillas(texto_con_fecha_antes)
    comprobar("la casilla 07 se encuentra pese a la coincidencia temprana",
              v_fecha.get(7) == 9999.99, f"07={v_fecha.get(7)}")

    # La misma idea, pero con la FORMULA impresa que el propio 303 escribe
    # junto al total -- "(...+ 06 + 09 + 11 + 13...)" -- citando etiquetas
    # sueltas de casillas ANTES de la rejilla real. Ninguna casilla debe
    # confundir esa cita con su propio valor.
    texto_con_formula_antes = "\n".join([
        "Total cuota devengada (03 + 06 + 09 + 11 + 13) ... importe pendiente",
        "01 02 4,00 03 500,00",
        "04 05 10,00 06",
        "07 9.999,99 08 21,00 09 2.099,99",
    ])
    v_formula = extraer_casillas(texto_con_formula_antes)
    comprobar("la 03 de la formula no tapa la 03 real de la rejilla",
              v_formula.get(3) == 500.00, f"03={v_formula.get(3)}")
    comprobar("la 06 de la formula no inventa un valor donde el impreso esta en blanco",
              6 not in v_formula, f"06={v_formula.get(6)}")
    comprobar("la 09 se sigue encontrando aunque la formula la cite antes",
              v_formula.get(9) == 2099.99, f"09={v_formula.get(9)}")

    # Y si NINGUNA aparicion lleva numero detras (la casilla esta realmente
    # en blanco, aunque su etiqueta salga citada varias veces), sigue sin
    # inventarse nada -- localizar_valor_casilla devuelve None, no un 0.
    comprobar("si ninguna aparicion tiene numero detras, no se inventa nada",
              localizar_valor_casilla("07 08 2025, casilla 07 sin dato", 7) is None)

    print()
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. Las casillas se leen de la rejilla, las vacias se "
          "quedan vacias, y ningun digito de dentro de un importe pasa por "
          "etiqueta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
