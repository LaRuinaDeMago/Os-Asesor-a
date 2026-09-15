#!/usr/bin/env python3
"""ensayo_boe_normativa.py — ensayo del detector de cambios en el BOE.

NO TOCA LA RED, Y ES DELIBERADO
---------------------------------
Un ensayo que descargara del BOE fallaria en un contenedor sin salida, tardaria
segundos en cada auditoria, y --lo peor-- dejaria de ser determinista: pasaria o
no segun lo que hubiera publicado el BOE esa manana. Se prueba contra XML
sinteticos que imitan la estructura real de la API, con articulos y fechas
inventados.

QUE PRUEBA, Y POR QUE CADA COSA
---------------------------------
La pieza tiene UNA responsabilidad y un riesgo claro en cada mitad:

  · elegir la version EN VIGOR. El consolidado del BOE trae TODAS las
    historicas, y ademas publica reformas con entrada en vigor FUTURA. Coger
    "la ultima del fichero" daria por vigente una norma que aun no lo esta.
  · calcular una huella ESTABLE. Si cambia porque el BOE reformatea un
    espacio, el aviso se vuelve ruido y se deja de mirar -- el mismo final que
    el ❌ que se enseño a ignorar.
"""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import boe_normativa as bn

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK   {titulo}")
    else:
        print(f"  FALLA  {titulo}" + (f"   {detalle}" if detalle else ""))
        FALLOS.append(titulo)


def xml(versiones):
    """Monta un XML con la forma real de la API. `versiones` es una lista de
    (fecha_vigencia, norma, [(clase, texto), ...])."""
    trozos = ['<?xml version="1.0" encoding="utf-8"?><response><status><code>200'
              '</code></status><data><bloque id="aX" tipo="precepto" '
              'titulo="Articulo de prueba">']
    for fecha, norma, parrafos in versiones:
        trozos.append(f'<version id_norma="{norma}" fecha_vigencia="{fecha}">')
        for clase, texto in parrafos:
            trozos.append(f'<p class="{clase}">{texto}</p>')
        trozos.append("</version>")
    trozos.append("</bloque></data></response>")
    return "".join(trozos).encode("utf-8")


def main():
    print("=== ENSAYO: detector de cambios en el texto consolidado del BOE ===\n")

    print("A. Elegir la version EN VIGOR, no la ultima del fichero")
    doc = xml([("20100101", "BOE-vieja", [("parrafo", "redaccion de 2010")]),
               ("20200101", "BOE-media", [("parrafo", "redaccion de 2020")]),
               ("20990101", "BOE-futura", [("parrafo", "redaccion que aun no rige")])])
    r = bn.version_en_vigor(doc, hoy="20260915")
    comprobar("se queda con la mas reciente YA en vigor", r[1] == "20200101", str(r[1]))
    comprobar("y con su norma modificadora", r[2] == "BOE-media", str(r[2]))
    comprobar("IGNORA la reforma con entrada en vigor futura",
              "aun no rige" not in r[3], r[3])
    comprobar("y no se queda con la vieja", "de 2010" not in r[3], r[3])

    # El dia que la reforma entra en vigor, pasa a ser la buena, sola.
    r2 = bn.version_en_vigor(doc, hoy="20990102")
    comprobar("al llegar su fecha, la reforma futura pasa a ser la vigente",
              r2[1] == "20990101", str(r2[1]))

    print("\nB. El texto DEROGADO que el BOE conserva no cuenta como vigente")
    # El consolidado guarda la redaccion anterior dentro de la version actual,
    # como nota. Meterla en el texto seria dar por vigente lo que ya no lo esta.
    doc2 = xml([("20200101", "BOE-x", [
        ("parrafo", "Se aplicara el tipo del 4 por ciento."),
        ("nota_pie", "Tengase en cuenta que esto cambio."),
        ("cita_con_pleca", "Se aplicara el tipo del 10 por ciento."),
    ])])
    r = bn.version_en_vigor(doc2, hoy="20260915")
    comprobar("el texto en vigor entra", "4 por ciento" in r[3])
    comprobar("la redaccion anterior NO entra", "10 por ciento" not in r[3], r[3])
    comprobar("ni la nota editorial", "Tengase en cuenta" not in r[3], r[3])

    print("\nC. La huella distingue una reforma de un reformateo")
    base = "Uno. El Impuesto se exigira al tipo del 21 por ciento."
    comprobar("misma redaccion, misma huella",
              bn.huella(base) == bn.huella(base))
    comprobar("espacios y saltos de linea NO cambian la huella",
              bn.huella(base) == bn.huella("Uno.  El Impuesto se exigira\n\n al "
                                            "tipo del  21 por ciento."))
    comprobar("cambiar el TIPO si cambia la huella",
              bn.huella(base) != bn.huella(base.replace("21", "23")))
    comprobar("y quitar una frase tambien",
              bn.huella(base) != bn.huella("Uno. El Impuesto se exigira."))
    comprobar("la huella es corta y estable, no un volcado",
              len(bn.huella(base)) == 16 and bn.huella(base).isalnum())

    print("\nD. Un bloque que no existe no revienta ni miente")
    vacio = ('<?xml version="1.0" encoding="utf-8"?><response><status><code>400'
             '</code></status><data/></response>').encode("utf-8")
    comprobar("un bloque inexistente devuelve None, no una version inventada",
              bn.version_en_vigor(vacio) is None)
    solo_futuras = xml([("20990101", "BOE-f", [("parrafo", "futura")])])
    comprobar("si TODAS las versiones son futuras, tampoco se inventa una",
              bn.version_en_vigor(solo_futuras, hoy="20260915") is None)

    print("\nE. comprobar() compara, no interpreta")
    class Reg:
        def __init__(self, clave, bloque, vigencia, h):
            self.clave, self.bloque_boe = clave, bloque
            self.norma_boe, self.vigencia_boe, self.huella_boe = "N", vigencia, h
    doc3 = xml([("20200101", "BOE-x", [("parrafo", "texto uno")])])
    r = bn.version_en_vigor(doc3, hoy="20260915")
    h_real = bn.huella(r[3])
    guardado = [Reg("igual", "aX", "20200101", h_real),
                Reg("cambiado", "aX", "20200101", "0000000000000000"),
                Reg("sin_bloque", "", "", "")]
    bn_descargar = bn.descargar
    try:
        bn.descargar = lambda norma, bloque, timeout=60: doc3
        iguales, cambiados, fallidos = bn.comprobar(guardado, hoy="20260915")
    finally:
        bn.descargar = bn_descargar
    comprobar("una huella que coincide sale como 'sin cambios'", iguales == ["igual"], str(iguales))
    comprobar("una que no coincide sale como CAMBIADA",
              [c[0] for c in cambiados] == ["cambiado"], str(cambiados))
    comprobar("y el aviso trae la vigencia nueva y la huella nueva",
              cambiados[0][2] == "20200101" and cambiados[0][4] == h_real, str(cambiados[0]))
    comprobar("un registro sin bloque BOE simplemente no se comprueba",
              "sin_bloque" not in iguales and
              all(c[0] != "sin_bloque" for c in cambiados) and
              all(f[0] != "sin_bloque" for f in fallidos))

    print("\nF. Un fallo de red NO se cuenta como 'sin cambios'")
    # Es la regla del motor: no poder comprobar no es aprobar.
    def peta(norma, bloque, timeout=60):
        raise OSError("sin salida a internet")
    try:
        bn.descargar = peta
        iguales, cambiados, fallidos = bn.comprobar([Reg("x", "aX", "20200101", "abc")])
    finally:
        bn.descargar = bn_descargar
    comprobar("un error de red sale como NO COMPROBADO, no como igual",
              not iguales and not cambiados and [f[0] for f in fallidos] == ["x"],
              f"{iguales} {cambiados} {fallidos}")
    comprobar("y se reporta solo el TIPO de excepcion, nunca su mensaje",
              fallidos[0][1] == "OSError", str(fallidos[0]))

    print()
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. Elige la redaccion en vigor, ignora la derogada y la "
          "futura, y un fallo de red no se confunde con 'no ha cambiado'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
