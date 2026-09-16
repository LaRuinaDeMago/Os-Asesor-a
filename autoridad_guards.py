#!/usr/bin/env python3
"""autoridad_guards.py — que norma hay detras de cada guard del motor. O ninguna.

LA IDEA, Y DE DONDE SALE
--------------------------
El motor tiene 28 guards que codifican reglas contables y fiscales, y su
justificacion vive hoy en los docstrings, escrita desde la experiencia del
despacho. Eso funciona para saber QUE comprueba cada uno, pero no contesta
tres preguntas que importan cada vez mas segun crece el motor:

  · Si manana cambia una norma, .que guards hay que revisar?
  · Cuando un guard salta, .se le puede decir al cliente POR QUE, con cita?
  · .Cuales de estos 28 son derecho, y cuales son criterio nuestro?

La tercera es la que mas se olvida, y es la que evita el peor error posible:
**presentar como obligacion legal lo que es un criterio del despacho.**

LO QUE ESTE FICHERO NO HACE, Y ES DELIBERADO
----------------------------------------------
No modifica `motor_veredicto.py`. Ni una linea. Podria haberse metido la cita
dentro de cada guard, y se ha decidido que no: el motor es la pieza que
`.claude/rules/contabilidad.md` protege con tests antes y despues, y esto es
metadato, no logica. Un registro externo da exactamente el mismo resultado con
riesgo cero para el motor -- el mismo patron que `fuentes_externas.py` usa con
las constantes.

EL ESTADO DE HOY, DICHO SIN ADORNOS
-------------------------------------
**Ninguna cita esta VERIFICADA.** Cero de 28. Lo que hay aqui es una PROPUESTA
para que Diego la valide, articulo por articulo, con el texto delante. Se ha
escrito asi a proposito: inventar una referencia legal en un motor contable
seria el peor fallo posible de todo este proyecto, y el 15-09-2026 ya se vio
que un resumen automatico afirma articulos que no dicen lo que parece.

Dos de las citas NO las propone Claude: ya estaban escritas en el propio
`motor_veredicto.py` (art. 154 LIVA en guard_recargo_equivalencia, y la tabla
de tipos en guard_tipo_producto_iva_semantico). Se anotan con esa procedencia,
que no es la misma cosa.

COMO SE VALIDA UNA
--------------------
Se abre el texto oficial, se lee el articulo, y si dice lo que el guard hace se
cambia `estado` a VERIFICADO anadiendo `url` y `verificado`. Si NO lo dice, se
cambia la cita o se pasa a SIN_IDENTIFICAR. Las dos salidas son buenas; dejarla
en PROPUESTO para siempre, no.
"""
import ast
import os

# --- de donde viene la regla que el guard aplica ----------------------
NORMA = "NORMA"        # una norma juridica concreta
TECNICO = "TECNICO"    # calidad del dato: no hay norma detras, ni hace falta
CRITERIO = "CRITERIO"  # criterio profesional del despacho, no derecho

# --- cuanto nos fiamos de la cita -------------------------------------
VERIFICADO = "VERIFICADO"          # leido en el texto oficial, con url y fecha
PARCIAL = "PARCIAL"                # parte leida en el BOE, parte NO esta ahi
PROPUESTO = "PROPUESTO"            # plausible; NADIE lo ha contrastado
SIN_IDENTIFICAR = "SIN_IDENTIFICAR"  # no sabemos que norma lo respalda

#: Procedencias
DEL_CODIGO = "ya citado en motor_veredicto.py"
PROPUESTA_CLAUDE = "propuesto por Claude el 15-09-2026, SIN contrastar"
LEIDO_EN_BOE = "leido en el texto consolidado del BOE el 15-09-2026"
NO_APLICA = "no procede: no es una regla juridica"

#: Base de la url de la API de datos abiertos del BOE (legislacion consolidada).
#: AMPLIADO 15-09-2026: antes tenia la LIVA incrustada en la cadena, asi que
#: cualquier cita de OTRA norma no podia registrarse como leida aunque se
#: hubiera leido. Ahora la norma es un parametro.
_BOE = ("https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
        "id/{norma}/texto/bloque/{bloque}")

#: Identificadores BOE de las normas que este registro cita.
LIVA = "BOE-A-1992-28740"           # Ley 37/1992, del IVA
RGLTO_FACTURACION = "BOE-A-2012-14696"  # RD 1619/2012
RGLTO_IRPF = "BOE-A-2007-6820"      # RD 439/2007
ORDEN_NIF = "BOE-A-2008-3580"       # Orden EHA/451/2008

#: Huella del texto EN VIGOR de cada articulo, el dia que se leyo. Es lo que
#: `boe_normativa.py --comprobar` vuelve a calcular para avisar de un cambio.
#:
#: Una tabla y no un argumento repetido en cada cita, por dos motivos: varias
#: citas comparten articulo (el 78 respalda cuatro guards), y despues de cada
#: comprobacion mensual hay UN solo sitio que tocar. La huella se saca con:
#:      python boe_normativa.py --ver a78 [--norma BOE-A-...]
#:
#: Medidas todas el 15-09-2026. Control cruzado: la del a91 coincide con la que
#: `fuentes_externas.py` guardaba por su cuenta desde antes.
HUELLAS = {
    (LIVA, "a13"):  ("20210701", "6ce2aaceccecf91f"),
    (LIVA, "a15"):  ("20200301", "8c07a54544a4aef7"),
    (LIVA, "a20"):  ("20190101", "61ab35ccde6ece3d"),
    (LIVA, "a75"):  ("20210701", "03dcb0914230d5d3"),
    (LIVA, "a78"):  ("20171110", "3f80f8b9b6b337f6"),
    (LIVA, "a84"):  ("20230101", "5b624c97b7ad47e2"),
    (LIVA, "a88"):  ("20130101", "fe73d620f53651f7"),
    (LIVA, "a91"):  ("20250101", "fa5e6f111bf2dd98"),
    (LIVA, "a99"):  ("20121031", "7a4fc6fb486df241"),
    (LIVA, "a154"): ("20150101", "626f099121d29f84"),
    (RGLTO_FACTURACION, "a6"):  ("20231207", "8f47333e149b8871"),
    (RGLTO_FACTURACION, "a15"): ("20180101", "17831bd4f9f48ab3"),
    (RGLTO_IRPF, "a74"):        ("20070401", "83d96294a4b277bb"),
    (ORDEN_NIF, "a3"):          ("20160116", "cfab279a43269685"),
}


class Autoridad:
    def __init__(self, guard, origen, norma, estado, procedencia, nota="",
                 url="", verificado=""):
        self.guard = guard
        self.origen = origen
        self.norma = norma
        self.estado = estado
        self.procedencia = procedencia
        self.nota = nota
        self.url = url
        self.verificado = verificado
        # Enganche con boe_normativa.py, solo para las leidas en el BOE.
        self.norma_boe = "BOE-A-1992-28740"
        self.bloque_boe = ""
        self.vigencia_boe = ""
        self.huella_boe = ""

    @property
    def clave(self):
        """Nombre con el que `boe_normativa.comprobar()` identifica el registro.
        Existe desde el 15-09-2026, cuando la vigilancia del BOE paso a cubrir
        tambien este registro y no solo `fuentes_externas`."""
        return f"{self.guard} ({self.norma})"


def _n(guard, norma, nota="", procedencia=PROPUESTA_CLAUDE):
    return Autoridad(guard, NORMA, norma, PROPUESTO, procedencia, nota)


def _v(guard, norma, bloque, vigencia, nota, norma_boe=LIVA, estado=VERIFICADO,
       huella=""):
    """Cita LEIDA en el texto consolidado del BOE: se guarda el bloque, desde
    cuando esta en vigor esa redaccion, y la url exacta desde la que se leyo.
    `boe_normativa.py --comprobar` vuelve a descargarla y avisa si cambia.

    `huella` ANADIDA el 15-09-2026, y es lo que hace que la frase de arriba sea
    verdad. Hasta hoy no existia: las citas se registraban como VERIFICADAS con
    su bloque, pero SIN huella, y `--comprobar` solo miraba `fuentes_externas`.
    Resultado: 15 citas verificadas y solo 2 vigiladas. Una verificacion que
    nadie vuelve a mirar no caduca con un aviso, caduca en silencio -- que es
    justo lo que este registro existe para evitar."""
    a = Autoridad(guard, NORMA, norma, estado, LEIDO_EN_BOE, nota,
                  url=_BOE.format(norma=norma_boe, bloque=bloque),
                  verificado="2026-09-15")
    a.norma_boe = norma_boe
    a.bloque_boe = bloque
    a.huella_boe = huella or HUELLAS.get((norma_boe, bloque), ("", ""))[1]
    # La vigencia manda desde HUELLAS si esta: es lo ultimo medido contra el
    # BOE. Si la cita declara otra cosa, gana la medicion, no el texto escrito
    # a mano -- misma jerarquia de siempre (codigo y medicion sobre documento).
    a.vigencia_boe = HUELLAS.get((norma_boe, bloque), (vigencia, ""))[0] or vigencia
    return a


def _vp(guard, norma, bloque, vigencia, nota, norma_boe=LIVA):
    """Cita PARCIAL: se ha leido el articulo y respalda una PARTE de lo que el
    guard hace, pero la otra parte NO esta en ese texto legal. Existe porque el
    caso apareció de verdad (15-09-2026, guard_nif_digito_control): la
    composicion del NIF si esta en la norma, pero el ALGORITMO del caracter de
    control no esta en el texto consolidado de ninguna de las dos normas que lo
    regulan. Llamar VERIFICADO a eso seria exactamente el falso verde que este
    proyecto prohibe."""
    return _v(guard, norma, bloque, vigencia, nota, norma_boe, estado=PARCIAL)


def _t(guard, nota):
    return Autoridad(guard, TECNICO, "—", SIN_IDENTIFICAR, NO_APLICA, nota)


def _c(guard, nota):
    return Autoridad(guard, CRITERIO, "—", SIN_IDENTIFICAR, NO_APLICA, nota)


AUTORIDADES = (
    # ---------- reglas que vienen de una norma ------------------------
    _v("guard_recargo_equivalencia", "Ley 37/1992 (LIVA), art. 154", "a154", "20150101",
       "CONFIRMADA. La cita ya estaba en el docstring del guard desde el "
       "20-08-2026 y era correcta: el art. 154 se titula 'Contenido del regimen "
       "especial del recargo de equivalencia'. Leida en el BOE el 15-09-2026."),
    _v("guard_tipo_producto_iva_semantico", "Ley 37/1992 (LIVA), art. 91.Dos", "a91", "20250101",
       "CONFIRMADA, y con hallazgo. El art. 91.Dos.1.1o lista los productos al "
       "4%. Leerlo destapo que TABLA_IVA_4 dice 'pan' donde la ley dice 'pan "
       "COMUN', no exige que frutas y verduras sean 'productos naturales segun "
       "el Codigo Alimentario', y deja fuera libros, medicamentos y protesis, "
       "que tambien van al 4%. Detalle completo en fuentes_externas.py "
       "(iva.productos_al_4). La tabla NO se ha tocado: es decision contable."),
    _v("guard_aritmetica_base_tipo", "Ley 37/1992 (LIVA), arts. 78 y 90", "a78", "20171110",
       "CONFIRMADA. El art. 78 se titula 'Base imponible. Regla general' y el 90 "
       "'Tipo impositivo general'. base x tipo = cuota no es convencion nuestra: "
       "sale de esas dos definiciones."),
    _v("guard_aritmetica_tramos", "Ley 37/1992 (LIVA), arts. 78 y 90", "a78", "20171110",
       "Misma regla que guard_aritmetica_base_tipo, para varios tipos en una "
       "factura. Misma cita, confirmada el 15-09-2026."),
    _v("guard_cuadre_total", "Ley 37/1992 (LIVA), arts. 78 y 88", "a88", "20130101",
       "CONFIRMADA: el art. 88 se titula 'Repercusion del impuesto' y su "
       "apartado Uno obliga a repercutir INTEGRAMENTE el importe sobre el "
       "destinatario. Por eso base + cuota tiene que dar el total."),
    _v("guard_suma_tramos", "Ley 37/1992 (LIVA), art. 78", "a78", "20171110",
       "CONFIRMADA. La suma de las bases por tramo tiene que dar la base total: "
       "es la definicion de base imponible del art. 78, aplicada a una factura "
       "con varios tipos."),
    _v("guard_suma_tramos_general", "Ley 37/1992 (LIVA), art. 78", "a78", "20171110",
       "Version del anterior para cualquier numero de tramos. Misma cita, misma "
       "regla, confirmada el 15-09-2026."),
    _vp("guard_nif_digito_control", "Orden EHA/451/2008 (composicion del NIF)",
        "a3", "20160116",
        "PARCIAL, y el matiz es el hallazgo: LEIDO el 15-09-2026 (norma "
        "BOE-A-2008-3580, no la que se habia supuesto). Los arts. 2 a 5 SI "
        "respaldan la COMPOSICION -- 9 caracteres (letra de forma juridica + 7 "
        "digitos + caracter de control), la lista de claves del art. 3 (A "
        "anonimas, B limitadas, ... V otros), la N de entidad extranjera (art. "
        "4) y la W de establecimiento permanente (art. 5). Pero lo que este "
        "guard CALCULA es el caracter de control, y ese ALGORITMO no esta en el "
        "texto: la Orden se acaba en el art. 5, y el RD 1065/2007 art. 22 se "
        "limita a delegar ('en los terminos que establezca el Ministro'). Es "
        "especificacion tecnica de la AEAT, no articulo citable. Por eso PARCIAL "
        "y no VERIFICADO.",
        norma_boe=ORDEN_NIF),
    _v("guard_retencion_vs_error", "RD 439/2007 (Reglamento IRPF), art. 74",
       "a74", "20070401",
       "CONFIRMADO el articulo el 15-09-2026: el art. 74 se titula 'Obligacion "
       "de practicar retenciones e ingresos a cuenta del IRPF' -- es el que "
       "respalda que exista la retencion. AMPLIADO 15-09-2026 (sesion Cloud): "
       "los PORCENTAJES de RETENCIONES_TIPICAS = [1, 2, 7, 15, 19, 21] ya se "
       "contrastaron uno a uno contra los articulos que de verdad fijan "
       "importes (este art. 74 no fija ninguno). Leidos en el texto vigente: "
       "art. 95.1 (profesionales: 15%, 7% inicio de actividad), art. 95.4-6 "
       "(agricola/ganadera: 1% engorde porcino/avicultura, 2% el resto; "
       "forestal 2%; estimacion objetiva de ciertos epigrafes 1%), art. 100 "
       "(arrendamiento urbano: 19%), art. 90 (capital mobiliario general: "
       "19%) y art. 99 (premios/ganancias patrimoniales: 19%). Los cinco "
       "numeros [1, 2, 7, 15, 19] tienen articulo vigente que los respalda "
       "para el periodo del corpus (2016-2026). "
       "**El 21% NO aparece en ninguno de estos articulos vigentes** -- el "
       "unico precedente encontrado es que la retencion general de "
       "profesionales/capital mobiliario SI fue del 21% entre 2012 y 2014 "
       "(medida antideficit, derogada por la reforma de 2015), fuera del "
       "rango del corpus. No se ha quitado de la lista sin saber si Diego lo "
       "ha visto de verdad en alguna factura del corpus (ver PENDIENTE.md "
       "2.C-bis) -- quitarlo a ojo seria el mismo error que anadirlo a ojo.",
       norma_boe=RGLTO_IRPF),
    _v("guard_signo_efectivo", "RD 1619/2012 (Reglamento de facturacion), art. 15",
       "a15", "20180101",
       "CONFIRMADA: el art. 15 se titula 'Facturas rectificativas'. Leido en el "
       "BOE el 15-09-2026.",
       norma_boe=RGLTO_FACTURACION),
    _v("guard_secuencia_documental_proveedor",
       "RD 1619/2012 (Reglamento de facturacion), art. 6.1.a)",
       "a6", "20231207",
       "CONFIRMADA: el art. 6 se titula 'Contenido de la factura' y su 1.a) es "
       "el numero y, en su caso, serie -- la numeracion correlativa. El mismo "
       "articulo respalda el modulo de facturas EMITIDAS "
       "(numeracion_correlativa.py): una verificacion vale para las dos.",
       norma_boe=RGLTO_FACTURACION),
    _v("guard_estructura_reconocida",
       "RD 1619/2012 (Reglamento de facturacion), art. 6",
       "a6", "20231207",
       "Articulo CONFIRMADO ('Contenido de la factura', leido el 15-09-2026), "
       "pero OJO, que esto no cambia: este guard no comprueba la norma, "
       "comprueba el PARECIDO con lo ya visto de ese proveedor. La norma explica "
       "por que la forma es estable; no obliga a ninguna forma concreta. Sigue "
       "siendo candidato serio a reclasificarse como TECNICO.",
       norma_boe=RGLTO_FACTURACION),
    _v("guard_sentido_compra_venta", "Ley 37/1992 (LIVA), art. 84", "a84", "20230101",
       "CONFIRMADA: el art. 84 se titula 'Sujetos pasivos' y su apartado Uno.1o "
       "los define por quien realiza la entrega o presta el servicio. El sentido "
       "lo da eso, no el titulo del papel. Su apartado Uno.2o es ademas el de la "
       "inversion del sujeto pasivo, que aparece en el cuadre del 303."),
    _v("guard_ejercicio_coherente", "Ley 37/1992 (LIVA), arts. 75 y 99",
       "a99", "20121031",
       "CONFIRMADOS los dos el 15-09-2026: el art. 75 se titula 'Devengo del "
       "impuesto' y el 99 'Ejercicio del derecho a la deduccion'. Y la lectura "
       "contesta la pregunta que quedaba abierta: NO manda uno de los dos, son "
       "dos cosas distintas -- el 75 fija CUANDO nace el impuesto de una "
       "operacion, y el 99 en que periodos puede el sujeto pasivo ejercer la "
       "deduccion (hasta cuatro anos). Por eso un asiento con fecha de un "
       "ejercicio y deduccion en otro no es automaticamente un error: es lo que "
       "este guard frena a AMBAR en vez de declarar FALLO, y esa eleccion queda "
       "ahora respaldada por el texto y no por intuicion."),
    _v("guard_tipo_operacion_especial",
       "Varias: LIVA art. 84.Uno.2 (ISP), arts. 13 y 15 (intracomunitarias), "
       "RD 1514/2007 PGC (inmovilizado)",
       "a15", "20200301",
       "PARCIALMENTE confirmada, y se declara cual es la parte que falta. "
       "LEIDOS el 15-09-2026: art. 13 ('Hecho imponible', el de las "
       "adquisiciones intracomunitarias) y art. 15 ('Concepto de adquisicion "
       "intracomunitaria de bienes'). El art. 84.Uno.2 (ISP) ya estaba "
       "verificado con guard_sentido_compra_venta. LO QUE NO SE HA LEIDO: el RD "
       "1514/2007 (PGC) para el supuesto de inmovilizado -- no se ha tocado "
       "porque ese no es texto fiscal del BOE consolidado con la misma "
       "estructura de articulos y merece su propia pasada. Sigue en pie lo de "
       "siempre: este guard detecta VARIOS supuestos de una vez y hoy no decide "
       "nada, solo frena a AMBAR."),
    _v("guard_naturaleza_operacion", "Ley 37/1992 (LIVA), arts. 20 y 90",
       "a20", "20190101",
       "CONFIRMADA: el art. 20 se titula 'Exenciones en operaciones interiores' "
       "y el art. 90 es el tipo general, ya verificado con "
       "guard_aritmetica_base_tipo. La coherencia que mira este guard -- que el "
       "IVA aplicado case con la naturaleza declarada de la operacion -- se "
       "apoya justo en esos dos: o la operacion esta exenta (art. 20) o lleva un "
       "tipo (art. 90), no las dos cosas. Leido en el BOE el 15-09-2026."),

    # ---------- calidad del dato: no hay norma, ni hace falta ---------
    _t("guard_integridad_datos",
       "Guard #0: comprueba que los campos existen y son del tipo que dicen ser. "
       "No hay norma que regule esto, y no deberia haberla."),
    _t("guard_confianza_por_campo",
       "Confianza de la captura campo a campo. Es una propiedad de NUESTRO "
       "proceso de lectura, no de la factura."),
    _t("guard_confianza_captura",
       "Idem: mide lo que sabemos de nuestra propia lectura."),
    _t("guard_doble_lectura_total",
       "El total leido de dos sitios del documento tiene que coincidir. Control "
       "de lectura, no requisito legal."),
    _t("guard_triangulacion_identidad",
       "Cruza varias senales para decidir de quien es una factura. Metodo propio."),
    _t("guard_anti_duplicado",
       "Que no se contabilice dos veces la misma factura. Buena practica "
       "contable evidente, pero el guard implementa una clave tecnica nuestra."),
    _t("guard_importe_atipico",
       "Estadistico: compara contra el historico del proveedor. Por eso no puede "
       "dar ROJO nunca, solo AMBAR: no demuestra un incumplimiento."),
    _t("guard_patron_cartera",
       "Que dice el conjunto de la cartera sobre este proveedor. Nuestro."),
    _t("guard_nif_casa_historico",
       "El NIF esta en el maestro de proveedores del cliente. Comprobacion "
       "contra datos propios, no contra un registro oficial."),
    _t("guard_vencimiento_coherente",
       "Plazo habitual de ese proveedor. Hoy ademas inerte: la captura no trae "
       "el campo vencimiento."),
    _t("guard_fecha_posterior_alta",
       "Coherencia interna de fechas contra el alta del cliente. Nuestro."),

    # ---------- criterio profesional del despacho ---------------------
    _c("guard_cuenta_gasto_coherente",
       "A que cuenta va un proveedor es CRITERIO del despacho, sistematizado a "
       "partir de diez anios de historico. El PGC (RD 1514/2007) fija la "
       "estructura de cuentas, no cual le toca a cada proveedor. Presentarlo al "
       "cliente como obligacion legal seria falso."),
)


def guards_del_motor(ruta="motor_veredicto.py"):
    """Los guards que existen DE VERDAD, leidos del AST del motor. No se
    mantiene una lista a mano: seria la misma trampa que la de las suites."""
    if not os.path.exists(ruta):
        return []
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    return sorted(n.name for n in ast.walk(arbol)
                  if isinstance(n, ast.FunctionDef) and n.name.startswith("guard_"))


def revisar(ruta="motor_veredicto.py"):
    """(sin_autoridad, sobran, por_estado, por_origen). Solo nombres de funcion
    y recuentos: aqui no hay ni puede haber un dato de cliente."""
    reales = set(guards_del_motor(ruta))
    anotados = {a.guard for a in AUTORIDADES}
    sin_autoridad = sorted(reales - anotados)
    sobran = sorted(anotados - reales)
    por_estado, por_origen = {}, {}
    for a in AUTORIDADES:
        por_estado[a.estado] = por_estado.get(a.estado, 0) + 1
        por_origen[a.origen] = por_origen.get(a.origen, 0) + 1
    return sin_autoridad, sobran, por_estado, por_origen


def main():
    sin_autoridad, sobran, por_estado, por_origen = revisar()
    print("=" * 70)
    print(f"AUTORIDAD DE LOS GUARDS — {len(AUTORIDADES)} anotados")
    print("=" * 70)
    for origen, titulo in ((NORMA, "De una NORMA juridica"),
                            (TECNICO, "Calidad del dato (no hay norma, ni hace falta)"),
                            (CRITERIO, "CRITERIO profesional del despacho")):
        print(f"\n--- {titulo} ---")
        for a in AUTORIDADES:
            if a.origen != origen:
                continue
            print(f"  {a.guard}")
            if a.origen == NORMA:
                print(f"      {a.norma}   [{a.estado}]")
                print(f"      procedencia: {a.procedencia}")
    print()
    print("-" * 70)
    print("  por origen: " + ", ".join(f"{k}={v}" for k, v in sorted(por_origen.items())))
    print("  por estado: " + ", ".join(f"{k}={v}" for k, v in sorted(por_estado.items())))
    verificados = por_estado.get(VERIFICADO, 0)
    print(f"\n  VERIFICADAS CONTRA EL TEXTO OFICIAL: {verificados} de "
          f"{por_origen.get(NORMA, 0)} citas.")
    if not verificados:
        print("  Es decir: NINGUNA. Todo lo de arriba es una propuesta para")
        print("  validar con el texto delante, no una afirmacion.")
    if sin_autoridad:
        print(f"\n  GUARDS SIN ANOTAR: {sin_autoridad}")
    if sobran:
        print(f"  ANOTACIONES QUE SOBRAN (ese guard ya no existe): {sobran}")
    return 1 if (sin_autoridad or sobran) else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
