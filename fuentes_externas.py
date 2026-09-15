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
                 fuente, url, verificado, estado, nota=""):
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
        url="https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
        verificado="2026-09-15", estado=PARCIAL,
        nota="PARCIAL a proposito: el 4, el 10 y el 21 se leyeron PREIMPRESOS en "
             "el formulario oficial (casillas 02, 05 y 08). El 0 y el 5 NO se han "
             "leido en ninguna fuente: el 5% fue un tipo temporal y hay que "
             "comprobar si sigue vigente y desde/hasta cuando. Primer sitio donde "
             "mirar si aparecen tramos marcados como tipo ilegal."),
    Fuente(
        clave="iva.productos_al_4",
        descripcion="Productos que tributan al tipo superreducido del 4%",
        modulo="motor_veredicto", atributo="TABLA_IVA_4",
        valor={"pan", "harina panificable", "leche", "queso", "huevos", "fruta",
               "verdura", "hortaliza", "legumbre", "tuberculo", "cereal",
               "aceite de oliva"},
        fuente="Ley 37/1992 del IVA, art. 91.Dos.1.1o",
        url="https://www.boe.es/buscar/act.php?id=BOE-A-1992-28740",
        verificado="2026-09-15", estado=SIN_VERIFICAR,
        nota="SIN_VERIFICAR, y es la mas delicada del registro: la lista sale "
             "directamente de la ley y de ella depende guard_tipo_producto_iva_"
             "semantico, que decide si un 4% esta bien puesto. El aceite de oliva "
             "paso al 4% por una medida TEMPORAL (antes 10%), asi que hay dos "
             "preguntas abiertas: si sigue ahi, y si la lista esta completa. "
             "Encontrada el 15-09-2026 al registrar la autoridad de los guards; "
             "llevaba sin registrar desde que se escribio."),
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
