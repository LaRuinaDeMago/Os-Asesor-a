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
                              extraer_numero_tras, TIPOS_LEGALES, TOL_TIPO,
                              cuadre_interno, veredicto_lectura)

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
