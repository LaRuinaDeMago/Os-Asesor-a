#!/usr/bin/env python3
"""ensayo_cruce_303.py — ensayo en seco de cruzar_303_importes.py.

POR QUE HACE FALTA
-------------------
`cruzar_303_importes.py` solo se puede ejecutar de verdad contra el archivo de
documentos reales del despacho, en la maquina del titular. Aqui no hay ni un
PDF real, y no puede haberlo. Sin un ensayo, ese script llegaria a su unica
ejecucion real sin haberse ejecutado NUNCA — que es exactamente la situacion
que el 21-08-2026 produjo tres defectos en la primera ejecucion de los tres
comandos de la sesion LOCAL (`--emitir-cartera` no escribia nada, el CSV con
separador equivocado que declaraba "0 falsos verdes", y el ambar universal).

QUE COMPRUEBA
--------------
Fabrica un archivo de documentos falso (nombres de fichero con la forma real,
importes inventados) y una contabilidad falsa, y verifica de punta a punta:

  1. Que el cubo cuyos importes estan en una carpeta CASA con esa carpeta.
  2. Que casa por VARIOS trimestres, que es la defensa contra la casualidad.
  3. Que un cubo cuyos importes no estan en ninguna parte NO casa con nada
     (el equivalente aqui del "nunca OK por omision" del motor).
  4. Que una carpeta senuelo con importes parecidos pero distintos no gana.
  5. Que un importe presente en TODAS las carpetas se descarta por difuso.
  6. Que el trimestre se lee bien del nombre del fichero.

No se lee ni un PDF: `importes_del_pdf` se sustituye por una funcion que
devuelve importes inventados. Lo que se prueba es la LOGICA DEL CRUCE, que es
la parte nueva; la lectura de PDF ya esta medida en extraer_303_pdf.py
(98-99% sobre 1.168 documentos reales).

Uso:
    python ensayo_cruce_303.py
"""
import io
import json
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cruzar_303_importes as cruce

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


#: Importes inventados. Cada carpeta tiene los suyos, sin solaparse con las
#: demas, salvo el "comun" que se pone en todas a proposito para comprobar
#: que el filtro de difusion lo tira.
COMUN = 1000.00

IMPORTES = {
    "ALFA": {
        "2021T1": [12345.67, 2592.59, 2222.22, 222.22, 14567.89, 2814.81],
        "2021T2": [23456.78, 4925.92, 3333.33, 333.33, 26790.11, 5259.25],
        "2021T3": [34567.89, 7259.26, 4444.44, 444.44, 39012.33, 7703.70],
    },
    "BETA": {
        "2021T1": [55555.11, 11666.57, 6666.66, 666.67, 62221.77, 12333.24],
        "2021T2": [66666.22, 14000.01, 7777.77, 777.78, 74444.00, 14777.79],
        "2021T3": [77777.33, 16333.24, 8888.88, 888.89, 86666.21, 17222.13],
    },
    # Senuelo: importes CERCANOS a los de ALFA pero distintos. Si el cruce
    # comparase "parecido" en vez de exacto, esta carpeta competiria.
    "SENUELO": {
        "2021T1": [12345.68, 2592.60, 2222.23, 222.23, 14567.90, 2814.82],
        "2021T2": [23456.79, 4925.93, 3333.34, 333.34, 26790.12, 5259.26],
    },
    "DELTA": {
        "2021T1": [98765.43, 20740.74, 1111.11, 111.11, 99876.54, 20851.85],
    },
}


def celdas_de_contabilidad(valores):
    """Construye la forma que produce reconstruir_303.py a partir de los seis
    importes de la lista: base y cuota de dos tipos. Los dos totales salen
    solos de sumarlos, igual que en el fichero real."""
    b21, c21, b10, c10 = valores[0], valores[1], valores[2], valores[3]
    return {
        "devengado": {
            "21": {"base": b21, "cuota": c21, "apuntes": 9},
            "10": {"base": b10, "cuota": c10, "apuntes": 3},
        },
        "deducible": {},
    }


def montar_archivo(raiz):
    """Crea las carpetas y los ficheros .pdf vacios con el nombre real."""
    nombres_trim = {"T1": "1 trimestre", "T2": "2 trimestre", "T3": "3 trimestre"}
    for carpeta, trimestres in IMPORTES.items():
        destino = os.path.join(raiz, carpeta)
        os.makedirs(destino, exist_ok=True)
        for tri in trimestres:
            anio, t = tri[:4], tri[4:]
            nombre = f"Modelo 303 {nombres_trim[t]} {anio}.pdf"
            with open(os.path.join(destino, nombre), "w", encoding="utf-8") as f:
                f.write("no se lee: importes_del_pdf esta sustituido")


def falso_importes_del_pdf(ruta):
    """Sustituye la lectura real de PDF. Devuelve los importes inventados de
    la carpeta y trimestre que corresponden a esa ruta."""
    carpeta = os.path.basename(os.path.dirname(ruta))
    tri = cruce.trimestre_del_nombre(os.path.basename(ruta))
    valores = set(IMPORTES.get(carpeta, {}).get(tri, []))
    valores.add(COMUN)          # el importe difuso, en todas las carpetas
    valores.add(21.00)          # ruido por debajo de --min-importe
    return valores


def main():
    print("ENSAYO EN SECO: cruzar_303_importes.py")
    print("=" * 60)

    # 1. Lectura del trimestre desde el nombre, antes de nada.
    comprobar("lee el trimestre del nombre del fichero",
              cruce.trimestre_del_nombre("Modelo 303 3er trimestre 2021.pdf") == "2021T3",
              cruce.trimestre_del_nombre("Modelo 303 3er trimestre 2021.pdf"))
    comprobar("no inventa trimestre si el nombre no lo dice",
              cruce.trimestre_del_nombre("Modelo 111 enero.pdf") is None)
    comprobar("lee el formato real del despacho (MODELO 303-2º TRIMESTRE 2024)",
              cruce.trimestre_del_nombre("MODELO 303-2º TRIMESTRE 2024.pdf") == "2024T2",
              cruce.trimestre_del_nombre("MODELO 303-2º TRIMESTRE 2024.pdf"))
    comprobar("el patron de reserva recupera las abreviaturas (303 4T 2023)",
              cruce.trimestre_del_nombre("MODELO 303 4T 2023.pdf") == "2023T4",
              cruce.trimestre_del_nombre("MODELO 303 4T 2023.pdf"))
    comprobar("con ano pero sin trimestre NO se inventa uno",
              cruce.trimestre_del_nombre("MODELO 390 RESUMEN 2023.pdf") is None,
              cruce.trimestre_del_nombre("MODELO 390 RESUMEN 2023.pdf"))

    # REGRESION del bug del 26-08-2026 (heredado de extraer_303_pdf.py): el
    # patron exigia el punto de millar, asi que "12345,67" no fallaba -- daba
    # "345,67", un numero distinto, en silencio. Un importe mal leido no
    # produce un error: produce un cruce que no casa nunca y que parece decir
    # "la contabilidad no cuadra". Es un falso negativo fabricado por el
    # instrumento, y por eso lleva prueba propia.
    for texto, esperado in (("12.345,67", 12345.67),
                            ("12345,67", 12345.67),
                            ("1234567,89", 1234567.89),
                            ("345,67", 345.67),
                            ("1.234.567,89", 1234567.89)):
        hallados = cruce.NUM_ES.findall(texto)
        valor = cruce._num_es_a_float(hallados[0]) if hallados else None
        comprobar(f"lee {texto} como {esperado} (con y sin separador de millar)",
                  valor == esperado, f"leyo {valor}")

    tmp = tempfile.mkdtemp(prefix="ensayo_cruce_")
    try:
        raiz = os.path.join(tmp, "documentos")
        montar_archivo(raiz)

        # La contabilidad falsa: un cubo que ES alfa, otro que ES beta, y uno
        # cuyos importes no estan en ningun sitio.
        contabilidad = {}
        for cubo, carpeta in (("CUBO_QUE_ES_ALFA", "ALFA"),
                              ("CUBO_QUE_ES_BETA", "BETA")):
            contabilidad[cubo] = {tri: celdas_de_contabilidad(vals)
                                  for tri, vals in IMPORTES[carpeta].items()}
        contabilidad["CUBO_HUERFANO"] = {
            "2021T1": celdas_de_contabilidad([191919.19, 40302.83, 5151.51, 515.15]),
        }

        ruta_json = os.path.join(tmp, "contabilidad.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(contabilidad, f)

        ruta_detalle = os.path.join(tmp, "cruce_LOCAL.json")
        ruta_agregado = os.path.join(tmp, "agregado.json")

        # Sustituciones: ni se abre un PDF ni se escribe en el repositorio.
        original_lector = cruce.importes_del_pdf
        original_agregado = cruce.SALIDA_AGREGADA
        original_argv = sys.argv
        cruce.importes_del_pdf = falso_importes_del_pdf
        cruce.SALIDA_AGREGADA = ruta_agregado
        sys.argv = ["cruzar_303_importes.py", raiz,
                    "--json", ruta_json, "--detalle", ruta_detalle]
        salida = io.StringIO()
        try:
            with redirect_stdout(salida):
                cruce.main()
        except SystemExit as e:
            comprobar("termina sin abortar", e.code in (None, 0), f"code={e.code}")
        finally:
            cruce.importes_del_pdf = original_lector
            cruce.SALIDA_AGREGADA = original_agregado
            sys.argv = original_argv

        texto = salida.getvalue()

        with open(ruta_detalle, "r", encoding="utf-8") as f:
            resultado = json.load(f)
        with open(ruta_agregado, "r", encoding="utf-8") as f:
            agregado = json.load(f)

        # 2. Cada cubo casa con SU carpeta.
        comprobar("el cubo de ALFA casa con la carpeta ALFA",
                  resultado.get("CUBO_QUE_ES_ALFA", {}).get("carpeta") == "ALFA",
                  resultado.get("CUBO_QUE_ES_ALFA"))
        comprobar("el cubo de BETA casa con la carpeta BETA",
                  resultado.get("CUBO_QUE_ES_BETA", {}).get("carpeta") == "BETA",
                  resultado.get("CUBO_QUE_ES_BETA"))

        # 3. Corroboracion en varios trimestres, que es la defensa real.
        comprobar("ALFA casa en los 3 trimestres, no en uno suelto",
                  resultado.get("CUBO_QUE_ES_ALFA", {}).get("trimestres_casados") == 3,
                  resultado.get("CUBO_QUE_ES_ALFA"))

        # 4. El senuelo no gana pese a tener importes casi iguales.
        comprobar("la carpeta senuelo (importes a un centimo) NO gana",
                  resultado.get("CUBO_QUE_ES_ALFA", {}).get("carpeta") != "SENUELO")
        comprobar("y el segundo candidato de ALFA se queda a cero trimestres",
                  resultado.get("CUBO_QUE_ES_ALFA", {}).get("trimestres_del_segundo") == 0,
                  resultado.get("CUBO_QUE_ES_ALFA"))

        # 5. Lo que no esta, no se inventa. El equivalente del "nunca OK por
        #    omision" del motor: sin evidencia, no hay veredicto.
        huerfano = resultado.get("CUBO_HUERFANO", {})
        comprobar("un cubo sin correspondencia NO casa con nada",
                  huerfano.get("carpeta") is None, huerfano)

        # 6. El importe presente en todas las carpetas se descarta.
        comprobar("descarta importes difusos (presentes en todas las carpetas)",
                  agregado.get("cubos_solidos", 0) >= 2 and
                  "1,000" not in texto,
                  f"solidos={agregado.get('cubos_solidos')}")

        # 7. El informe no filtra datos: por pantalla solo recuentos.
        comprobar("no imprime nombres de carpeta por pantalla",
                  "ALFA" not in texto and "SENUELO" not in texto,
                  "aparece un nombre de carpeta en la salida")

        comprobar("cuenta 2 cubos solidos y ninguno ambiguo",
                  agregado.get("cubos_solidos") == 2
                  and agregado.get("cubos_ambiguos") == 0,
                  f"solidos={agregado.get('cubos_solidos')} "
                  f"ambiguos={agregado.get('cubos_ambiguos')}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 60)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. La logica del cruce hace lo que dice.")


if __name__ == "__main__":
    main()
