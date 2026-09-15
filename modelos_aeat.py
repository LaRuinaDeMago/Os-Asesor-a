#!/usr/bin/env python3
"""modelos_aeat.py — que Orden del BOE aprueba cada modelo, y si ha cambiado.

POR QUE EXISTE, Y QUE PROBLEMA REAL RESUELVE
--------------------------------------------
Creado el 15-09-2026. El proyecto lee modelos 303 presentados y los cuadra
contra la contabilidad (`extraer_303_pdf.py`, 1.023 documentos, 99,8%). Ese
lector esta construido sobre la FORMA del impreso: donde cae cada casilla, que
etiquetas lleva, que aritmetica imprime al lado de los totales.

Y la forma del impreso no es eterna: la fija una Orden ministerial, en su ANEXO.
Cuando esa Orden se modifica, el impreso cambia -- y un extractor construido
sobre el anterior no da error: da numeros. Ese es el peor fallo posible en este
proyecto, y es justo el que ningun test puede ver, porque los tests usan el
impreso viejo.

LO QUE SE ENCONTRO AL MONTAR ESTO (medido, no supuesto)
--------------------------------------------------------
    modelo 303  ANEXO I  -> en vigor desde 20260127 (BOE-A-2026-1761)
    modelo 347  ANEXO    -> en vigor desde 20251213 (BOE-A-2025-25390)

Los dos impresos cambiaron en los ultimos nueve meses y el proyecto no tenia
ninguna alarma. No se ha comprobado todavia si el cambio afecta a lo que el
lector del 303 usa -- eso lo mira un asesor, no un programa. Pero hasta hoy no
habia forma de ENTERARSE, que es lo que este fichero arregla.

LA LINEA QUE NO CRUZA, la misma que `boe_normativa.py`
-------------------------------------------------------
Esto NO interpreta el cambio ni intenta leer el formulario. Compara la huella
del texto en vigor con la guardada y avisa. El anexo del BOE apenas trae texto
(el impreso de verdad es una imagen), asi que lo util aqui es exactamente eso:
la fecha de vigencia y la huella. Detectar es automatico; entender, no.

COMO SE AMPLIA
--------------
1. Buscar en boe.es la Orden que aprueba el modelo y quedarse con su BOE-A-...
2. Ver que bloques tiene y como se llaman sus anexos -- OJO, el nombre NO es
   uniforme entre Ordenes: el 303 usa `ani`/`anii`, el 130 usa `ai`/`ai-2`.
       python -c "import modelos_aeat; modelos_aeat.indice('BOE-A-...')"
3. Sacar vigencia y huella:
       python boe_normativa.py --norma BOE-A-... --ver ani
4. Anadir la linea aqui. `boe_normativa.py --comprobar` lo coge solo.
"""
import sys
import urllib.request
import xml.etree.ElementTree as ET

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_IDX = ("https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
        "id/{}/texto/indice")


class ModeloAEAT:
    """Un modelo AEAT, la Orden que lo aprueba, y el bloque que hay que vigilar.

    Mismos atributos que `fuentes_externas.Fuente` y `autoridad_guards.Autoridad`
    a proposito: `boe_normativa.comprobar()` acepta cualquier objeto con
    .clave/.norma_boe/.bloque_boe/.vigencia_boe/.huella_boe, asi que este
    registro entra en la vigilancia sin tocar el comprobador.
    """

    def __init__(self, modelo, orden, norma_boe, bloque_boe, vigencia_boe,
                 huella_boe, nota=""):
        self.modelo = modelo
        self.orden = orden
        self.norma_boe = norma_boe
        self.bloque_boe = bloque_boe
        self.vigencia_boe = vigencia_boe
        self.huella_boe = huella_boe
        self.nota = nota

    @property
    def clave(self):
        return f"modelo {self.modelo} ({self.orden}, {self.bloque_boe})"


#: Verificados contra la API del BOE el 15-09-2026: los cuatro devuelven indice
#: y anexos. Vigencias y huellas medidas ese dia.
MODELOS = (
    ModeloAEAT("303", "Orden EHA/3786/2008", "BOE-A-2008-20953", "ani",
               "20260127", "6b5fd8aeada2eb58",
               "EL MAS IMPORTANTE del proyecto: es el impreso sobre el que esta "
               "construido extraer_303_pdf.py. Su anexo cambio el 27-01-2026 "
               "(Orden HAC/27/2026) y nadie lo habia mirado."),
    ModeloAEAT("130", "Orden EHA/672/2007", "BOE-A-2007-6032", "ai",
               "20150220", "5a9ae17c78b3f6fd",
               "Pago fraccionado de IRPF en estimacion directa. Es el candidato "
               "con mas volumen en PC1 despues del 303 (535 PDF frente a 256 "
               "del 390), asi que es el siguiente si se extrapola el metodo."),
    ModeloAEAT("347", "Orden EHA/3012/2008", "BOE-A-2008-16973", "an",
               "20251213", "4a2ddb9f15ed3df4",
               "Operaciones con terceras personas. Su ANEXO cambio el "
               "13-12-2025, hace nueve meses."),
    ModeloAEAT("347", "Orden EHA/3012/2008", "BOE-A-2008-16973", "ani",
               "20220103", "a15d8350739d17d8",
               "Segundo anexo del mismo modelo: los disenos fisicos y logicos."),
    ModeloAEAT("349", "Orden EHA/769/2010", "BOE-A-2010-5098", "ai",
               "20201231", "8690e35b811bfe6f",
               "Declaracion recapitulativa de operaciones intracomunitarias. "
               "Tiene relacion directa con la ISP que ya aparecio en el cuadre "
               "del 303 (caso real de un cliente, 15-09-2026)."),
)

#: Modelos que Diego presenta y que AUN NO estan aqui, con lo que falta para
#: cerrarlos. No se han registrado a ojo: hace falta confirmar el identificador
#: BOE de su Orden contra la fuente oficial, igual que se hizo con estos cinco
#: -- un primer intento a ojo con la Orden del NIF devolvio, el mismo dia, una
#: resolucion sobre equipos termosifon. Adivinar un BOE-A no es barato.
PENDIENTES_DE_IDENTIFICAR = {
    "111": "Retenciones e ingresos a cuenta (trabajo/actividades). Falta el BOE-A.",
    "115": "Retenciones por arrendamiento de inmuebles urbanos. Falta el BOE-A.",
    "190": "Resumen anual de retenciones. Falta el BOE-A.",
    "390": "Resumen anual de IVA. Falta el BOE-A (Orden EHA/3111/2009).",
    "036/037": "Declaracion censal. Falta el BOE-A (Orden EHA/1274/2007).",
    "180": "Resumen anual de retenciones por arrendamientos. Falta el BOE-A.",
}


def indice(norma_boe, timeout=60):
    """Lista los bloques de una Orden. Sirve para encontrar como se llaman sus
    anexos antes de registrarlos, porque el nombre NO es uniforme entre Ordenes
    (el 303 usa `ani`, el 130 usa `ai`)."""
    d = urllib.request.urlopen(
        urllib.request.Request(_IDX.format(norma_boe),
                               headers={"Accept": "application/xml"}),
        timeout=timeout).read()
    r = ET.fromstring(d)
    return [((b.findtext("id") or "").strip(),
             (b.findtext("titulo") or "").strip(),
             (b.findtext("fecha_actualizacion") or "").strip())
            for b in r.iter("bloque")]


def main():
    print("=" * 70)
    print("MODELOS AEAT VIGILADOS — la Orden que aprueba cada impreso")
    print("=" * 70)
    print("Esto NO descarga nada. Para comprobar contra el BOE:")
    print("    python boe_normativa.py --comprobar")
    print()
    for m in MODELOS:
        print(f"  modelo {m.modelo:<8} {m.orden:<22} {m.bloque_boe:<6} "
              f"en vigor desde {m.vigencia_boe}")
        if m.nota:
            for linea in _envolver(m.nota, 64):
                print(f"        {linea}")
    print()
    print(f"  vigilados: {len(MODELOS)} bloques de "
          f"{len({m.norma_boe for m in MODELOS})} Ordenes")
    print()
    print("--- Modelos SIN identificar todavia (no es un aprobado) ---")
    for modelo, que_falta in PENDIENTES_DE_IDENTIFICAR.items():
        print(f"  {modelo:<10} {que_falta}")
    return 0


def _envolver(texto, ancho):
    palabras, linea, salida = texto.split(), "", []
    for p in palabras:
        if len(linea) + len(p) + 1 > ancho:
            salida.append(linea)
            linea = p
        else:
            linea = f"{linea} {p}".strip()
    if linea:
        salida.append(linea)
    return salida


if __name__ == "__main__":
    sys.exit(main())
