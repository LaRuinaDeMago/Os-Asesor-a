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
PROPUESTO = "PROPUESTO"            # plausible; NADIE lo ha contrastado
SIN_IDENTIFICAR = "SIN_IDENTIFICAR"  # no sabemos que norma lo respalda

#: Procedencias
DEL_CODIGO = "ya citado en motor_veredicto.py"
PROPUESTA_CLAUDE = "propuesto por Claude el 15-09-2026, SIN contrastar"
LEIDO_EN_BOE = "leido en el texto consolidado del BOE el 15-09-2026"
NO_APLICA = "no procede: no es una regla juridica"

#: Base de la url de la API de datos abiertos del BOE (legislacion consolidada)
_BOE = ("https://www.boe.es/datosabiertos/api/legislacion-consolidada/"
        "id/BOE-A-1992-28740/texto/bloque/{}")


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


def _n(guard, norma, nota="", procedencia=PROPUESTA_CLAUDE):
    return Autoridad(guard, NORMA, norma, PROPUESTO, procedencia, nota)


def _v(guard, norma, bloque, vigencia, nota):
    """Cita LEIDA en el texto consolidado del BOE: se guarda el bloque, desde
    cuando esta en vigor esa redaccion, y la url exacta desde la que se leyo.
    `boe_normativa.py --comprobar` vuelve a descargarla y avisa si cambia."""
    a = Autoridad(guard, NORMA, norma, VERIFICADO, LEIDO_EN_BOE, nota,
                  url=_BOE.format(bloque), verificado="2026-09-15")
    a.bloque_boe = bloque
    a.vigencia_boe = vigencia
    return a


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
    _n("guard_nif_digito_control", "Orden EHA/451/2008 (composicion del NIF)",
       "PENDIENTE de comprobar que sigue vigente y que es la norma que fija el "
       "algoritmo del digito de control, no solo el formato."),
    _n("guard_retencion_vs_error", "RD 439/2007 (Reglamento IRPF), retenciones",
       "El guard reconoce porcentajes tipicos de retencion (arrendamiento, "
       "profesionales). Hay que fijar los articulos y, sobre todo, LOS "
       "PORCENTAJES VIGENTES: son lo que mas cambia de todo este fichero."),
    _n("guard_signo_efectivo", "RD 1619/2012 (Reglamento de facturacion), art. 15",
       "Facturas rectificativas. Confirmar que el 15 es el de rectificativas."),
    _n("guard_secuencia_documental_proveedor",
       "RD 1619/2012 (Reglamento de facturacion), art. 6.1.a)",
       "Numeracion correlativa. El mismo articulo respalda el modulo de facturas "
       "EMITIDAS (numeracion_correlativa.py): si se verifica una, vale para las dos."),
    _n("guard_estructura_reconocida",
       "RD 1619/2012 (Reglamento de facturacion), art. 6",
       "OJO: este guard no comprueba la norma, comprueba el PARECIDO con lo ya "
       "visto de ese proveedor. La norma explica por que la forma es estable, no "
       "obliga a ninguna forma concreta. Candidato serio a reclasificarse como "
       "TECNICO al validarlo."),
    _v("guard_sentido_compra_venta", "Ley 37/1992 (LIVA), art. 84", "a84", "20230101",
       "CONFIRMADA: el art. 84 se titula 'Sujetos pasivos' y su apartado Uno.1o "
       "los define por quien realiza la entrega o presta el servicio. El sentido "
       "lo da eso, no el titulo del papel. Su apartado Uno.2o es ademas el de la "
       "inversion del sujeto pasivo, que aparece en el cuadre del 303."),
    _n("guard_ejercicio_coherente", "Ley 37/1992 (LIVA), arts. 75 y 99",
       "Devengo e imputacion temporal de las deducciones. Cual de los dos manda "
       "aqui es justo lo que hay que decidir leyendolos."),
    _n("guard_tipo_operacion_especial",
       "Varias: LIVA art. 84.Uno.2 (ISP), arts. 13 y 15 (intracomunitarias), "
       "RD 1514/2007 PGC (inmovilizado)",
       "Este guard detecta VARIOS supuestos distintos de una vez. Al validarlo "
       "habra que partirlo en una cita por supuesto, o dejarlo como TECNICO de "
       "deteccion: hoy no decide nada, solo frena a AMBAR."),
    _n("guard_naturaleza_operacion", "Ley 37/1992 (LIVA), arts. 20 y 90",
       "Coherencia entre el IVA aplicado y la naturaleza declarada: exenciones "
       "(art. 20) frente a tipo general. Contrastar."),

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
