#!/usr/bin/env python3
"""test_comparar_captura.py — que el comparador mida, y que no filtre.

POR QUE ESTA BATERIA
----------------------
`comparar_captura_vs_verdad.py` es la herramienta que decide si la cadena
foto -> IA -> motor funciona. Si se equivoca, se equivoca hacia el lado peor:
dando por bueno lo que no lo es, que es como se cierra un Paso 1 creyendo que
salio bien.

Y ademas IMPRIME VALORES DE CAMPOS. Sobre una muestra sintetica da igual; sobre
una factura real serian un NIF y una razon social en la terminal. La barrera que
lo impide -- lo que no esta declarado SINTETICO se trata como REAL -- no vale
nada si nadie la intenta forzar. Aqui se intenta.

La barrera tenia DOS FUGAS que solo aparecieron al escribir esta bateria: en
modo censurado seguia imprimiendo el nombre de la muestra y la RUTA del fichero
de verdad. Las dos las elige una persona y las dos pueden llevar el nombre de un
cliente (`ACME_SL_verdad.json`). Es la misma regla que `puerta_cloud.py` ya
tiene escrita para su registro: huellas y recuentos, nunca una ruta ni un nombre.

REGLA DE DATOS
----------------
Ni un dato real. Las verdades y capturas de prueba se fabrican aqui a partir de
las muestras sinteticas del repositorio, y los cebos que se buscan en la salida
son valores sinteticos conocidos.
"""
import io
import json
import contextlib
import os
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import comparar_captura_vs_verdad as cmp
import crear_muestras_sinteticas as m
from crear_factura_sintetica import nif_sintetico

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


def verdad_de(nombre_receta):
    """La verdad conocida de una receta, sin pasar por el disco ni por Pillow."""
    receta = next(r for r in m.RECETAS if r["nombre"] == nombre_receta)
    cifras = m.calcular(receta)
    nif = nif_sintetico(receta["nif_digitos"], receta["nif_letra"])
    return m.verdad_conocida(receta, cifras, nif, m.nif_del_pie(receta, nif))


def captura_de(verdad, **cambios):
    """Una captura simulada: la verdad + lo que anade la lectura + los cambios."""
    cap = {k: v for k, v in verdad.items() if not k.startswith("_")}
    cap["verificacion"] = "OK"
    for k, v in cambios.items():
        if v is cmp.NO_VINO:          # centinela: este campo NO viene
            cap.pop(k, None)
        else:
            cap[k] = v
    return cap


def ejecutar(captura, verdad, extra=()):
    """Corre el comparador de punta a punta y devuelve (codigo, salida)."""
    with tempfile.TemporaryDirectory() as tmp:
        rc = os.path.join(tmp, "captura.json")
        rv = os.path.join(tmp, "ACME_EJEMPLO_SL_verdad.json")
        json.dump(captura, open(rc, "w", encoding="utf-8"), ensure_ascii=False)
        json.dump(verdad, open(rv, "w", encoding="utf-8"), ensure_ascii=False)
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = cmp.main([rc, "--verdad", rv, "--sin-motor"])
        return codigo, salida.getvalue()


# ---------------------------------------------------------------------------
# 1. Los tres codigos de salida, que son tres cosas distintas
# ---------------------------------------------------------------------------
def pruebas_codigos():
    v_desc = verdad_de("doble_lectura_descuadre")
    v_let = verdad_de("doble_lectura_letras")

    casos = (
        ("lectura perfecta -> 0", v_desc, captura_de(v_desc), 0),
        ("ESPEJO: copia el total del cuadro en el del pie -> 1", v_desc,
         captura_de(v_desc, total_factura_2=v_desc["total_factura"]), 1),
        ("pierde el tramo del 5% (y los totales siguen cuadrando) -> 1", v_let,
         captura_de(v_let, tramos_iva=[t for t in v_let["tramos_iva"]
                                       if t["tipo"] != 5]), 1),
        ("copia el NIF de la cabecera en el margen -> 1", v_let,
         captura_de(v_let, nif_margen=v_let["nif"]), 1),
        ("un campo NO viene -> 2, que no es un aprobado", v_desc,
         captura_de(v_desc, total_factura_2=cmp.NO_VINO), 2),
        ("importe en formato espanol y fecha dd/mm/aaaa -> 0", v_let,
         captura_de(v_let, total_factura="1.420,00",
                    base_total="1.200,00 EUR",
                    fecha_expedicion="26/03/2026"), 0),
    )
    for etiqueta, verdad, captura, esperado in casos:
        codigo, _salida = ejecutar(captura, verdad)
        comprobar(etiqueta, codigo == esperado, f"devolvio {codigo}", "P0")

    # Un importe distinto por UN CENTIMO es una diferencia, no un redondeo.
    codigo, _ = ejecutar(captura_de(v_desc,
                                    total_factura=v_desc["total_factura"] + 0.01),
                         v_desc)
    comprobar("una diferencia de 0,01 EUR se caza", codigo == 1,
              f"devolvio {codigo}", "P0")


# ---------------------------------------------------------------------------
# 2. La barrera de datos. Lo que no se declara SINTETICO se trata como REAL
# ---------------------------------------------------------------------------
#: Cebos: valores sinteticos que SI aparecen si la censura falla.
def pruebas_barrera():
    for etiqueta, procedencia in (("REAL declarado", "REAL"),
                                  ("sin declarar", None),
                                  ("con un typo", "SINTETIC0"),
                                  ("en minusculas mal escrito", "sintetic")):
        verdad = dict(verdad_de("doble_lectura_descuadre"))
        if procedencia is None:
            verdad.pop("_procedencia", None)
        else:
            verdad["_procedencia"] = procedencia
        verdad["_muestra"] = "CLIENTE_EJEMPLO_SL"

        # Un NIF DISTINTO del de la muestra, para que el campo difiera. Se
        # COMPONE, no se escribe: un literal con forma de NIF en el codigo hace
        # saltar scripts/privacy_scan.py -- y con razon, porque el escaner no
        # puede distinguir uno inventado de uno real. Paso de verdad al escribir
        # esta bateria: el hook bloqueo el commit, que es justo su trabajo.
        nif_mal_leido = nif_sintetico("1111111", "B")
        captura = captura_de(verdad,
                             total_factura_2=verdad["total_factura"],
                             nif=nif_mal_leido)
        captura.pop("base_21", None)
        codigo, salida = ejecutar(captura, verdad)

        cebos = [str(verdad["nif"]), str(verdad["proveedor"]),
                 str(verdad["nif_margen"]), "1210", "1120", nif_mal_leido,
                 "CLIENTE_EJEMPLO_SL", "ACME_EJEMPLO_SL"]
        filtrados = [c for c in cebos if c in salida]
        comprobar(f"barrera ({etiqueta}): no se filtra ningun valor, nombre "
                  f"ni ruta", not filtrados,
                  f"aparecen: {filtrados}", "P0")
        # Y lo importante: el veredicto NO se pierde por censurar.
        comprobar(f"barrera ({etiqueta}): el veredicto se conserva (codigo 1)",
                  codigo == 1, f"devolvio {codigo}", "P0")
        comprobar(f"barrera ({etiqueta}): y se avisa de que esta censurado",
                  "NO esta declarado SINTETICO" in salida, severidad="P0")

    # Y que en SINTETICO si se vean los valores: una censura permanente
    # convertiria la herramienta en inutil sin que nadie se diera cuenta.
    verdad = verdad_de("doble_lectura_descuadre")
    captura = captura_de(verdad, total_factura_2=verdad["total_factura"])
    _codigo, salida = ejecutar(captura, verdad)
    comprobar("con SINTETICO declarado, los valores SI se imprimen",
              str(verdad["total_factura_2"]) in salida
              or "1120" in salida, severidad="P0")


def pruebas_es_sintetico():
    for valor, esperado in (("SINTETICO", True), ("sintetico", True),
                            ("  SINTETICO  ", True), ("REAL", False),
                            ("", False), (None, False), ("SINTETIC0", False),
                            ("SINTETICO REAL", False), (0, False)):
        comprobar(f"es_sintetico({valor!r}) = {esperado}",
                  cmp.es_sintetico({"_procedencia": valor}) is esperado,
                  severidad="P0")
    comprobar("sin la clave _procedencia se trata como REAL",
              cmp.es_sintetico({}) is False, severidad="P0")


# ---------------------------------------------------------------------------
# 3. El criterio de cada campo
# ---------------------------------------------------------------------------
def pruebas_criterios():
    # nif_margen NO se normaliza: la puntuacion ES la medicion.
    # Los dos valores salen de la RECETA, no copiados aqui: asi esta prueba
    # sigue midiendo lo correcto si el formato del pie cambiara, y ademas no
    # hay ningun literal con forma de NIF en este fichero.
    receta_con_guiones = next(r for r in m.RECETAS if r["nif_pie_con_guiones"])
    nif_cabecera = nif_sintetico(receta_con_guiones["nif_digitos"],
                                 receta_con_guiones["nif_letra"])
    nif_del_pie = m.nif_del_pie(receta_con_guiones, nif_cabecera)
    estado, _d = cmp.comparar_campo("nif_margen", nif_del_pie, nif_cabecera)
    comprobar("nif_margen: quitar los guiones NO es una coincidencia "
              "(la puntuacion es el marcador del experimento)",
              estado == cmp.DIFIERE, f"dio {estado}", "P0")

    # El numero de documento si distingue puntuacion de lectura.
    estado, _d = cmp.comparar_campo("nº_documento", "A26/7.612", "A267612")
    comprobar("nº_documento: sin puntuacion se marca SOLO_PUNTUACION, "
              "no se aprueba ni se suspende", estado == cmp.SOLO_PUNTUACION,
              f"dio {estado}", "P0")
    estado, _d = cmp.comparar_campo("nº_documento", "A26/7.612", "A26/7.613")
    comprobar("nº_documento: un digito cambiado SI es DIFIERE",
              estado == cmp.DIFIERE, f"dio {estado}", "P0")

    # Importes: formato espanol, y el cero no es "no vino".
    for esperado, leido, quiere in ((1420.0, "1.420,00", cmp.COINCIDE),
                                    (1420.0, "1420.00", cmp.COINCIDE),
                                    (1420.0, 1420.004, cmp.COINCIDE),
                                    (1420.0, 1420.01, cmp.DIFIERE),
                                    (0.0, 0, cmp.COINCIDE),
                                    (1420.0, None, cmp.NO_VINO),
                                    (1420.0, "", cmp.NO_VINO)):
        estado, _d = cmp.comparar_campo("total_factura", esperado, leido)
        comprobar(f"importe {esperado} vs {leido!r} -> {quiere}",
                  estado == quiere, f"dio {estado}", "P0")

    # Fechas: el mismo dia escrito de dos maneras.
    estado, _d = cmp.comparar_campo("fecha_expedicion", "2026-03-26", "26/03/2026")
    comprobar("fecha: 2026-03-26 y 26/03/2026 son el mismo dia",
              estado == cmp.COINCIDE, f"dio {estado}", "P0")

    # Tramos: sin importar el orden, pero sin perdonar uno que falte.
    dos = [{"tipo": 21, "base": 1000.0, "cuota": 210.0},
           {"tipo": 5, "base": 200.0, "cuota": 10.0}]
    estado, _d = cmp.comparar_campo("tramos_iva", dos, list(reversed(dos)))
    comprobar("tramos_iva: el orden no importa", estado == cmp.COINCIDE,
              f"dio {estado}", "P0")
    estado, det = cmp.comparar_campo("tramos_iva", dos, dos[:1])
    comprobar("tramos_iva: si falta uno, DIFIERE y se dice cual",
              estado == cmp.DIFIERE and "5" in det, f"{estado}: {det}", "P0")
    estado, _d = cmp.comparar_campo("tramos_iva", dos, [])
    comprobar("tramos_iva: una lista vacia es NO_VINO, no una coincidencia",
              estado == cmp.NO_VINO, f"dio {estado}", "P0")
    # Un tramo llegado como TEXTO (lo que hace un CSV) se sigue leyendo.
    estado, _d = cmp.comparar_campo("tramos_iva", dos, json.dumps(dos))
    comprobar("tramos_iva: sobrevive a venir serializado como texto (CSV)",
              estado == cmp.COINCIDE, f"dio {estado}", "P0")


def pruebas_busqueda_verdad():
    """Que NO elija 'el que mas se parezca'."""
    comprobar("con un nombre desconocido no se inventa un fichero de verdad",
              cmp.buscar_verdad({}, "no_existe_esta_muestra.json") is None,
              severidad="P0")
    ruta = cmp.buscar_verdad({"_imagen": "doble_lectura_letras_degradada.jpg"}, "-")
    comprobar("encuentra la verdad de la degradada (comparte verdad con la "
              "limpia, que es el experimento)",
              ruta == os.path.join("muestras_sinteticas",
                                   "doble_lectura_letras_verdad.json"),
              f"devolvio {ruta}")


def main():
    print("=" * 72)
    print("COMPARADOR CAPTURA vs VERDAD — bateria")
    print("=" * 72)
    pruebas_codigos()
    pruebas_barrera()
    pruebas_es_sintetico()
    pruebas_criterios()
    pruebas_busqueda_verdad()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nEl comparador distingue las tres cosas (coincide / difiere / no")
    print("vino), no normaliza lo que es la medicion, y con un documento no")
    print("declarado SINTETICO no filtra ni un valor, ni un nombre, ni una ruta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
