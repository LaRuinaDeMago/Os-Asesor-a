#!/usr/bin/env python3
"""fuentes_externas.py — de donde sale cada numero que este proyecto NO decide.

QUE ES, Y QUE NO ES
---------------------
Hay constantes en este codigo que no son una decision nuestra: los tipos de
IVA los fija la ley, las casillas del 303 las fija la AEAT, el plan de
cuentas lo fija el PGC. Si una de esas cambia y aqui no, el motor empieza a
medir contra un mundo que ya no existe -- y no falla: acierta menos, en
silencio, que es peor.

Este fichero es el REGISTRO de esas constantes: que valor tienen, de donde
sale, quien lo verifico y CUANDO. `audit_project.py` comprueba dos cosas en
cada pasada:

  1. que el valor anotado aqui sigue siendo el que tiene el codigo
     (si alguien edita la constante, salta),
  2. y que la verificacion no ha caducado
     (si nadie la ha vuelto a mirar en N meses -> NO_COMPROBADO, que NO es
     un aprobado; misma regla que el motor).

NO ES UN MODULO DE NORMATIVA, y la diferencia importa. Esto no lee el BOE,
no interpreta la ley y no contesta preguntas. Dice una sola cosa, que es la
unica que un programa puede decir con honestidad: **"este numero se copio de
aqui, tal dia, y nadie lo ha vuelto a comprobar desde entonces"**.

Lo contrario -- un sistema que resume normativa y te dice lo que significa --
es justo lo que este proyecto tiene prohibido: el 15-09-2026, una consulta
resumida automaticamente afirmo que la ISP soportada del 303 va a "las
casillas 40-43", que en el impreso son rectificacion de deducciones,
compensaciones REAGP y regularizacion de bienes de inversion. Se descarto
porque estaba corroborada contra el impreso. Sin esa corroboracion habria
entrado en el repositorio como un hecho.

COMO SE ANOTA UNA FUENTE NUEVA
--------------------------------
Solo si respalda una constante que ya existe en el codigo, y solo con una
fuente que se haya LEIDO (no un resumen). `estado` dice la verdad sobre esa
lectura, y "PARCIAL" es una respuesta legitima y frecuente.
"""
import datetime
import importlib

#: Estados de una verificacion. Los mismos tres del motor, y por el mismo
#: motivo: "no lo he comprobado" no puede confundirse con "esta bien".
VERIFICADO = "VERIFICADO"   # leido en la fuente oficial, entero
PARCIAL = "PARCIAL"         # leido en parte; el resto viene de otro sitio
SIN_VERIFICAR = "SIN_VERIFICAR"

#: Cuando se considera que una verificacion ha envejecido. No significa que
#: la norma haya cambiado -- significa que nadie lo ha mirado. Doce meses es
#: el ciclo natural: los modelos de la AEAT se publican por ejercicio.
MESES_HASTA_CADUCAR = 12


class Fuente:
    def __init__(self, clave, descripcion, modulo, atributo, valor,
                 fuente, url, verificado, estado, nota="",
                 norma_boe="", bloque_boe="", vigencia_boe="", huella_boe=""):
        self.clave = clave
        self.descripcion = descripcion
        self.modulo = modulo
        self.atributo = atributo
        self.valor = valor
        self.fuente = fuente
        self.url = url
        self.verificado = verificado          # "AAAA-MM-DD"
        self.estado = estado
        self.nota = nota
        # Enganche con boe_normativa.py. Si `bloque_boe` esta puesto,
        # `python boe_normativa.py --comprobar` descarga ese articulo del texto
        # consolidado y avisa si ha cambiado desde `vigencia_boe`/`huella_boe`.
        # La auditoria NO descarga nada: mira lo guardado. La red es explicita.
        self.norma_boe = norma_boe
        self.bloque_boe = bloque_boe
        self.vigencia_boe = vigencia_boe
        self.huella_boe = huella_boe

    def valor_en_codigo(self):
        """Lo que la constante vale AHORA, importando el modulo de verdad.
        No se lee el fichero como texto: se importa, para que un cambio de
        nombre o una reasignacion tambien salten."""
        mod = importlib.import_module(self.modulo)
        return getattr(mod, self.atributo)

    def coincide(self):
        try:
            actual = self.valor_en_codigo()
        except (ImportError, AttributeError) as e:
            return False, f"no se puede leer {self.modulo}.{self.atributo} ({type(e).__name__})"
        # Las tuplas de casillas se comparan como CONJUNTO: el orden en el
        # impreso no es el orden en que nos convenga escribirlas, y exigir
        # el orden daria rojos que no significan nada.
        if (isinstance(actual, (tuple, list, set, frozenset))
                and isinstance(self.valor, (tuple, list, set, frozenset))):
            if set(actual) != set(self.valor):
                return False, (f"el codigo tiene {sorted(set(actual))} y aqui esta "
                               f"anotado {sorted(set(self.valor))}")
            return True, ""
        if actual != self.valor:
            return False, f"el codigo tiene {actual!r} y aqui esta anotado {self.valor!r}"
        return True, ""

    def meses_desde_verificacion(self, hoy=None):
        hoy = hoy or datetime.date.today()
        d = datetime.date.fromisoformat(self.verificado)
        return (hoy.year - d.year) * 12 + (hoy.month - d.month)

    def caducada(self, hoy=None):
        return self.meses_desde_verificacion(hoy) >= MESES_HASTA_CADUCAR


#: URLs de los impresos oficiales leidos el 15-09-2026. Se leyeron los BYTES
#: del PDF, no un resumen de la pagina.
_U22 = ("https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/"
        "Manual/Practicos/IVA/IVA_2022/Imagenes/C7-mod303-4T_es_es.pdf")
_U24 = ("https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/"
        "Manual/Practicos/IVA/IVA_2024/Imagenes/Cap_9_303_es_es.pdf")

FUENTES = (
    Fuente(
        clave="303.casilla_27",
        descripcion="Casillas que suma el Total cuota devengada (casilla 27)",
        modulo="extraer_303_pdf", atributo="SUMANDOS_TOTAL_DEVENGADO",
        valor=(152, 167, 3, 155, 6, 9, 11, 13, 15, 158, 170, 18, 21, 24, 26),
        fuente="Modelo 303, formula impresa junto al total. Ejercicios 2022, "
               "2023, 2024 y 2026",
        url=_U24, verificado="2026-09-15", estado=VERIFICADO,
        nota="La formula solo CRECE con los anios (tipos reducidos temporales). "
             "Se anota el superconjunto de 2024/2026: un impreso anterior no "
             "trae esas casillas, cuentan 0, y la suma da igual. Verificado "
             "ejercicio a ejercicio en FORMULAS_IMPRESAS_VERIFICADAS."),
    Fuente(
        clave="303.casilla_45",
        descripcion="Casillas que suma el Total a deducir (casilla 45)",
        modulo="extraer_303_pdf", atributo="SUMANDOS_TOTAL_A_DEDUCIR",
        valor=(29, 31, 33, 35, 37, 39, 41, 42, 43, 44),
        fuente="Modelo 303, formula impresa. IDENTICA en 2022, 2023, 2024 y 2026",
        url=_U22, verificado="2026-09-15", estado=VERIFICADO),
    Fuente(
        clave="303.columna_bases_devengado",
        descripcion="Columna de bases del IVA devengado",
        modulo="extraer_303_pdf", atributo="BASES_DEVENGADO",
        valor=(150, 165, 1, 153, 4, 7, 10, 12, 14, 156, 168, 16, 19, 22, 25),
        fuente="Modelo 303: el PDF agrupa las casillas por columna",
        url=_U22, verificado="2026-09-15", estado=VERIFICADO,
        nota="OJO: el 303 no imprime ningun TOTAL de bases. Esto es la columna, "
             "no una formula citada. Menos respaldo que la 27 y la 45."),
    Fuente(
        clave="303.columna_bases_deducible",
        descripcion="Columna de bases del IVA deducible",
        modulo="extraer_303_pdf", atributo="BASES_DEDUCIBLE",
        valor=(28, 30, 32, 34, 36, 38, 40),
        fuente="Modelo 303: columna del impreso. 42, 43 y 44 no llevan base",
        url=_U22, verificado="2026-09-15", estado=VERIFICADO),
    Fuente(
        clave="303.columna_tipos",
        descripcion="Casillas que llevan un PORCENTAJE, no euros",
        modulo="extraer_303_pdf", atributo="CASILLAS_DE_TIPO",
        valor=(2, 5, 8, 17, 20, 23, 151, 154, 157, 166, 169),
        fuente="Modelo 303: columna 'Tipo %'. Varias vienen preimpresas",
        url=_U22, verificado="2026-09-15", estado=VERIFICADO,
        nota="Tratar una de estas como importe se equivoca en los 1.168 PDF a la vez."),
    Fuente(
        clave="iva.tipos_legales",
        descripcion="Tipos de IVA que el extractor considera legales",
        modulo="extraer_303_pdf", atributo="TIPOS_LEGALES",
        valor=(0, 4, 5, 10, 21),
        fuente="Ley 37/1992 del IVA, arts. 90 y 91",
        url="https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
            "id/BOE-A-1992-28740/texto/bloque/a91",
        verificado="2026-09-15", estado=PARCIAL,
        norma_boe="BOE-A-1992-28740", bloque_boe="a91",
        vigencia_boe="20250101", huella_boe="fa5e6f111bf2dd98",
        nota="LEIDO EN EL TEXTO CONSOLIDADO DEL BOE el 15-09-2026, articulo por "
             "articulo. CUATRO de los cinco quedan confirmados: 21% (art. 90.Uno, "
             "en vigor desde 2012), 10% (art. 91.Uno), 4% (art. 91.Dos) y 0% "
             "(art. 91.Cuatro, entregas en concepto de donativo -- existe y es "
             "permanente, no era una errata). EL 5% NO APARECE ni en el 90 ni en "
             "el 91: fue un tipo temporal de los RD-ley de la crisis de precios. "
             "SIGUE COMO PARCIAL POR ESO, y la decision es de Diego, no mia: "
             "TIPOS_LEGALES lo usa el LECTOR DE PDF para validar su propia "
             "lectura sobre un archivo de 2016 a 2026, y en parte de ese periodo "
             "el 5% SI estuvo vigente. Para ese uso, aceptarlo es correcto. "
             "Seria incorrecto reutilizar esta tupla para validar el tipo de una "
             "factura de hoy."),
    Fuente(
        clave="iva.productos_al_4",
        descripcion="Productos que tributan al tipo superreducido del 4%",
        modulo="motor_veredicto", atributo="TABLA_IVA_4",
        valor={"pan", "harina panificable", "leche", "queso", "huevos", "fruta",
               "verdura", "hortaliza", "legumbre", "tuberculo", "cereal",
               "aceite de oliva", "libro", "periodico", "revista",
               "medicamento humano", "vehiculo movilidad reducida", "protesis"},
        fuente="Ley 37/1992 del IVA, art. 91.Dos.1o-5o",
        url="https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
        verificado="2026-09-15", estado=PARCIAL,
        norma_boe="BOE-A-1992-28740", bloque_boe="a91",
        vigencia_boe="20250101", huella_boe="fa5e6f111bf2dd98",
        nota="LEIDO EN EL BOE el 15-09-2026 (art. 91.Dos.1o-5o, en vigor desde el "
             "1-1-2025, redaccion dada por el RD-ley 4/2024). Tres resultados, y "
             "una decision tomada el mismo dia sobre dos de los tres:\n"
             " (1) BUENA NOTICIA: el ACEITE DE OLIVA ya no es temporal. El RD-ley "
             "     4/2024 lo incorporo al 4% de forma permanente ('g) Los aceites "
             "     de oliva'). La alarma que se anoto queda resuelta.\n"
             " (2) LA LISTA ESTABA INCOMPLETA por el lado de 2o-5o: libros, "
             "     periodicos y revistas, medicamentos de uso humano, vehiculos "
             "     para movilidad reducida y protesis. ARREGLADO el 15-09-2026: "
             "     anadidos los seis terminos que faltaban. Antes, una factura "
             "     de libros al 4% salia NO_COMPROBADO en vez de aprobarse.\n"
             " (3) PERO 'pan' SIGUE SIENDO DEMASIADO AMPLIO, sin tocar a "
             "     proposito. La ley dice 'el pan COMUN'. Un pan especial o de "
             "     molde tributa al 10%, y esta tabla lo aprobaria al 4%. Mismo "
             "     problema en 'fruta/verdura/hortaliza/legumbre/tuberculo/"
             "     cereal': la ley exige 'la condicion de productos naturales "
             "     de acuerdo con el Codigo Alimentario'. Riesgo declarado, no "
             "     resuelto: exigiria que la captura distinga 'pan comun' de "
             "     un pan especial, campo que no existe todavia. Y no afecta a "
             "     ninguna factura real hoy: `guard_tipo_producto_iva_"
             "     semantico` esta dormido en produccion (nada en el pipeline "
             "     real produce `categoria_producto` todavia, confirmado por "
             "     grep el 15-09-2026)."),
)


def revisar(hoy=None):
    """Devuelve (discrepancias, caducadas, sin_verificar). Solo recuentos y
    nombres de constante: aqui no hay ningun dato de cliente."""
    discrepancias, caducadas, sin_verificar = [], [], []
    for f in FUENTES:
        ok, detalle = f.coincide()
        if not ok:
            discrepancias.append((f.clave, detalle))
        if f.caducada(hoy):
            caducadas.append((f.clave, f.verificado, f.meses_desde_verificacion(hoy)))
        if f.estado != VERIFICADO:
            sin_verificar.append((f.clave, f.estado))
    return discrepancias, caducadas, sin_verificar


def main():
    disc, cad, sinver = revisar()
    print("=" * 68)
    print(f"FUENTES EXTERNAS — {len(FUENTES)} constantes registradas")
    print("=" * 68)
    for f in FUENTES:
        ok, detalle = f.coincide()
        marca = "OK " if ok else "MAL"
        meses = f.meses_desde_verificacion()
        print(f"  [{marca}] {f.clave:34s} {f.estado:13s} "
              f"verificado {f.verificado} ({meses} meses)")
        if not ok:
            print(f"        -> {detalle}")
        if f.nota:
            print(f"        nota: {f.nota.splitlines()[0][:90]}")
    print()
    if disc:
        print(f"{len(disc)} constante(s) NO coinciden con el codigo.")
    if cad:
        print(f"{len(cad)} verificacion(es) con mas de {MESES_HASTA_CADUCAR} meses: "
              "no significa que la norma haya cambiado, significa que nadie lo ha mirado.")
    if sinver:
        print(f"{len(sinver)} sin verificar del todo: " + ", ".join(k for k, _ in sinver))
    if not disc and not cad:
        print("Todas las constantes coinciden con el codigo y ninguna ha caducado.")
    return 1 if disc else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
