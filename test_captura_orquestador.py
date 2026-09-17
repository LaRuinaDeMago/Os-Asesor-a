#!/usr/bin/env python3
"""test_captura_orquestador.py — que listar_documentos() reconoce lo que
procesar_carpeta() dice que sabe leer, PDF incluido.

POR QUE ESTA BATERIA
----------------------
Auditoria externa 17-09-2026: `procesar_carpeta()` solo buscaba
".jpg"/".jpeg"/".png" en la carpeta, aunque `leer_factura()` (via
leer_factura_gemini/leer_factura_claude) lleva semanas sabiendo leer un PDF.
Una carpeta llena de PDF pasaba con "Encontradas 0 imagenes" -- silencioso,
sin error, y facil de no notar.

No se prueba `procesar_carpeta()` directamente: llama a `puerta_cloud.
abrir_lote()` y a `leer_factura()`, que en el camino REAL contacta con la
API de Gemini/Claude. Este test prueba `listar_documentos()`, la funcion que
se separo de proposito para poder probar el filtrado de ficheros sin tocar
la puerta ni ninguna API.

REGLA DE DATOS: solo nombres de fichero vacios (0 bytes) en un directorio
temporal, ningun contenido ni dato real."""
import os
import tempfile
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import captura_orquestador as co

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


def _crear(tmp, *nombres):
    for n in nombres:
        with open(os.path.join(tmp, n), "w") as f:
            f.write("")


def pruebas_extensiones():
    with tempfile.TemporaryDirectory() as tmp:
        _crear(tmp, "a.jpg", "b.JPEG", "c.png", "d.pdf", "e.PDF",
               "f.txt", "g.docx", "h.gif", "sin_extension")
        docs = co.listar_documentos(tmp)
        comprobar("jpg/jpeg/png (mayus o minus) se reconocen",
                  {"a.jpg", "b.JPEG", "c.png"} <= set(docs), detalle=repr(docs),
                  severidad="P0")
        comprobar("EL BUG REAL: .pdf y .PDF se reconocen (antes: 'Encontradas "
                  "0 imagenes' con una carpeta llena de PDF)",
                  {"d.pdf", "e.PDF"} <= set(docs), detalle=repr(docs),
                  severidad="P0")
        comprobar("lo que no es documento reconocido NO se cuela (.txt/.docx/.gif/sin extension)",
                  not ({"f.txt", "g.docx", "h.gif", "sin_extension"} & set(docs)),
                  detalle=repr(docs), severidad="P0")
        comprobar("recuento exacto: 5 documentos de 9 ficheros en la carpeta",
                  len(docs) == 5, detalle=repr(docs), severidad="P0")


def pruebas_carpeta_vacia():
    with tempfile.TemporaryDirectory() as tmp:
        comprobar("carpeta vacia -> lista vacia, no revienta",
                  co.listar_documentos(tmp) == [], severidad="P0")


def main():
    print("=" * 72)
    print("CAPTURA_ORQUESTADOR — listar_documentos()")
    print("=" * 72)
    pruebas_extensiones()
    pruebas_carpeta_vacia()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nlistar_documentos() reconoce jpg/jpeg/png/pdf (con cualquier "
          "capitalizacion), nada mas, y no revienta con una carpeta vacia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
