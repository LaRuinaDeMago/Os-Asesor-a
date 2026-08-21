#!/usr/bin/env python3
"""test_adversarial.py — bateria de ataque al motor. NO es una suite de regresion.

DIFERENCIA CON test_motor_veredicto.py, y por que hacen falta las dos
---------------------------------------------------------------------
  test_motor_veredicto.py  -> casos reales anonimizados. Comprueba que lo que
                              ya funcionaba sigue funcionando. Debe estar SIEMPRE
                              en verde.
  test_adversarial.py      -> casos construidos a proposito para conseguir un
                              VERDE que no deberia existir. Hoy NO esta en verde,
                              y eso es el resultado, no un fallo de la suite.

Cada prueba de aqui afirma el comportamiento CORRECTO. Las que fallan son la
especificacion exacta de lo que hay que arreglar en el motor.

INVARIANTE QUE SE PONE A PRUEBA (declarada en el propio motor_veredicto.py):

    "si no hay dato para evaluar un guard, el estado es NO_COMPROBADO,
     nunca OK por omision."

    y su consecuencia:

    VERDE nunca puede obtenerse por FALTA de informacion.

ORIGEN: auditoria adversarial externa de los dias 12 y 13-08-2026, rondas 2 a 4.
Los hallazgos que esta suite confirma se verificaron ejecutando el motor real el
19-08-2026, no por lectura del codigo.

Todos los NIF/CIF de este fichero son inventados con checksum matematicamente
valido y ya estan declarados en el allowlist de scripts/privacy_scan.py. No
identifican a nadie.

Uso:  python3 test_adversarial.py
Salida: codigo 1 mientras queden defectos confirmados en pie. Es lo esperado.
"""
import sys
import warnings

import motor_veredicto as m

NIF_OK = "B12345674"          # CIF inventado, checksum valido
NIF_TITULAR = "B99999999"     # CIF inventado del cliente titular
MAESTRO = {NIF_OK: {'titulo': 'PROVEEDOR PILOTO SL', 'cuenta': '400001'}}

BASE_FILA = {
    'nif': NIF_OK,
    'proveedor': 'PROVEEDOR PILOTO SL',
    'nº_documento': 'FAC-2026-001',
    'fecha_expedicion': '2026-03-15',
    'verificacion': 'OK',
}

resultados = []


def evaluar(fila):
    """Corre el motor. Devuelve (veredicto, motivo) o ('EXCEPCION', tipo)."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            v, motivo, _ = m.evaluar_fila_v4(
                fila, set(), {}, {}, {}, MAESTRO,
                alta_cliente_anio=2020, nif_cliente_titular=NIF_TITULAR,
                ejercicio_tanda=2026)
        return v, motivo
    except Exception as e:
        return "EXCEPCION", type(e).__name__


def comprobar(familia, nombre, condicion, obtenido, esperado, severidad):
    ok = bool(condicion)
    resultados.append((familia, nombre, ok, obtenido, esperado, severidad))
    marca = "OK  " if ok else "FALLA"
    print(f"  [{marca}] {nombre}")
    if not ok:
        print(f"           obtenido: {obtenido}")
        print(f"           esperado: {esperado}   [{severidad}]")


# ---------------------------------------------------------------------------
print("=== FAMILIA A — Integridad del dato: ausencia nunca es cero ===")

v, _ = evaluar({**BASE_FILA, 'base_10': '', 'base_4': '', 'base_21': '',
                'base_total': '', 'iva_total': '', 'irpf_retencion': '',
                'total_factura': ''})
comprobar("A", "importes todos ausentes ('') NO puede dar VERDE",
          v != "VERDE", f"veredicto={v}", "AMBAR o ROJO (falta evidencia)", "P0")

v, _ = evaluar({**BASE_FILA, 'base_10': None, 'base_4': None, 'base_21': None,
                'base_total': None, 'iva_total': None, 'irpf_retencion': None,
                'total_factura': ''})
comprobar("A", "importes a None NO puede dar VERDE",
          v != "VERDE", f"veredicto={v}", "AMBAR o ROJO (falta evidencia)", "P0")

v, _ = evaluar({**BASE_FILA, 'base_10': 'abc', 'base_4': 'abc', 'base_21': 'abc',
                'base_total': 'abc', 'iva_total': 'abc', 'irpf_retencion': 'abc',
                'total_factura': ''})
comprobar("A", "importes ilegibles ('abc') NO puede dar VERDE",
          v != "VERDE", f"veredicto={v}", "AMBAR o ROJO (dato invalido)", "P0")

v, _ = evaluar({**BASE_FILA, 'base_10': '', 'base_4': '', 'base_21': '',
                'base_total': '', 'iva_total': '', 'irpf_retencion': ''})
comprobar("A", "falta la clave 'total_factura': veredicto, nunca excepcion",
          v != "EXCEPCION", f"{v}", "un veredicto (AMBAR/ROJO), no un crash", "P0")

v, _ = evaluar({**BASE_FILA, 'base_10': 0, 'base_4': 0, 'base_21': 100.0,
                'base_total': 100.0, 'iva_total': 21.0, 'irpf_retencion': 0,
                'total_factura': 121.0})
comprobar("A", "importes como numero JSON (no cadena): veredicto, nunca excepcion",
          v != "EXCEPCION", f"{v}", "un veredicto, no un crash", "P0")


# ---------------------------------------------------------------------------
print("\n=== FAMILIA B — Aritmetica adversarial ===")

e, det = m.guard_retencion_vs_error(1000.0, 210.0, 0.0, 1060.0, None)
comprobar("B", "diferencia parece 15% pero irpf declarado = 0 -> no puede ser OK",
          e != "OK", f"{e}: {det}", "NO_COMPROBADO (hipotesis, no hecho)", "P1")

e, det = m.guard_retencion_vs_error(1000.0, 210.0, 999.0, 1060.0, None)
comprobar("B", "diferencia 150 pero irpf declarado 999 (contradictorio) -> FALLO",
          e == "FALLO", f"{e}: {det}", "FALLO (el dato declarado contradice)", "P1")

e, det = m.guard_signo_efectivo('FAC-001', '', -100.0, -121.0, None)
comprobar("B", "importe negativo sin tipo_documento -> no puede ser OK",
          e != "OK", f"{e}: {det}", "NO_COMPROBADO (el signo no identifica el documento)", "P1")


# ---------------------------------------------------------------------------
print("\n=== FAMILIA D — Temporalidad: la fecha tiene que ser una fecha ===")

for fecha in ('2026-99-99', '2026-02-30', '2026-13-01'):
    v, _ = evaluar({**BASE_FILA, 'fecha_expedicion': fecha,
                    'base_10': '', 'base_4': '', 'base_21': '100',
                    'base_total': '100', 'iva_total': '21',
                    'irpf_retencion': '', 'total_factura': '121'})
    comprobar("D", f"fecha imposible {fecha} NO puede dar VERDE",
              v != "VERDE", f"veredicto={v}", "AMBAR o ROJO (fecha invalida)", "P0")


# ---------------------------------------------------------------------------
print("\n=== FAMILIA E — Cableado: un guard que existe pero no corre no protege ===")

import inspect
src = inspect.getsource(m.evaluar_fila_v4)
for g in ('guard_cuenta_gasto_coherente',
          'guard_tipo_producto_iva_semantico',
          'guard_tipo_operacion_especial'):
    comprobar("E", f"{g} participa en el veredicto",
              g in src, "no aparece en evaluar_fila_v4",
              "llamado desde evaluar_fila_v4, o declarado fuera del motor de decision",
              "P1")


# ---------------------------------------------------------------------------
print("\n=== FAMILIA G — CONTROL POSITIVO (sin esto, la bateria no vale nada) ===")
# Una bateria que solo comprueba "no debe dar VERDE" se aprueba entera con un
# motor que diga siempre ROJO. Estas pruebas son la otra mitad: una factura
# correcta TIENE que salir VERDE. Si alguna vez fallan, el motor se ha vuelto
# inutil por exceso de celo, que es la otra forma de romperlo.
FACTURA_BUENA = {**BASE_FILA, 'base_10': '132.90', 'base_4': '0', 'base_21': '0',
                 'base_total': '132.90', 'iva_total': '13.29',
                 'irpf_retencion': '0', 'total_factura': '146.19'}
v, mot = evaluar(FACTURA_BUENA)
comprobar("G", "factura completa y correcta SI da VERDE",
          v == "VERDE", f"veredicto={v} ({mot})", "VERDE", "P0")

# La misma, con los importes escritos en formato espanol.
v, _ = evaluar({**FACTURA_BUENA, 'base_10': '1.328,90', 'base_total': '1.328,90',
                'iva_total': '132,89', 'total_factura': '1.461,79'})
comprobar("G", "misma factura en formato espanol (1.328,90) tambien da VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P0")

# Tramos de IVA ausentes que legitimamente son cero (no se declara el 4%).
v, _ = evaluar({**BASE_FILA, 'base_21': '100', 'base_total': '100',
                'iva_total': '21', 'total_factura': '121'})
comprobar("G", "tramos 4% y 10% ausentes (legitimo) no impiden el VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P1")


print("\n=== FAMILIA H — Que los guards sigan detectando lo que ya detectaban ===")
vistos = set()
f1 = {**FACTURA_BUENA}
f2 = {**FACTURA_BUENA, 'total_factura': '146,19', 'nº_documento': 'FAC 2026 001'}
try:
    m.evaluar_fila_v4(f1, vistos, {}, {}, {}, MAESTRO, 2020, NIF_TITULAR, 2026)
    v2, mot2, _ = m.evaluar_fila_v4(f2, vistos, {}, {}, {}, MAESTRO, 2020, NIF_TITULAR, 2026)
    dup_ok = v2 == "ROJO" and "duplicado" in mot2.lower()
except Exception as e:
    v2, dup_ok = type(e).__name__, False
comprobar("H", "duplicado escrito de otra forma SI se detecta",
          dup_ok, f"veredicto={v2}", "ROJO por duplicado", "P1")

e, det = m.guard_retencion_vs_error(661.15, 138.84, -125.62, 674.37)
comprobar("H", "retencion del 19% real y coherente sigue dando OK (no falso rojo)",
          e == "OK", f"{e}: {det}", "OK", "P0")

v, mot = evaluar({**FACTURA_BUENA, 'iva_total': '99.99'})
comprobar("H", "IVA que no cuadra con la base sigue dando ROJO",
          v == "ROJO", f"veredicto={v} ({mot})", "ROJO", "P0")

v, _ = evaluar({**FACTURA_BUENA, 'nif': '12345678Y'})
comprobar("H", "NIF con digito de control incorrecto sigue dando ROJO",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")


print("\n=== FAMILIA I — Auditoria propia del 19-08-2026 (fallos del arreglo) ===")
# Estos cuatro salieron de auditar el codigo escrito ESE MISMO DIA para cerrar
# los P0. Tres eran defectos nuevos introducidos al arreglar los viejos.

v, _ = evaluar(None)
comprobar("I", "una fila que no es un dict no revienta el proceso",
          not str(v).startswith("EXCEPCION"), f"{v}", "un veredicto, no una excepcion", "P1")

v, _ = evaluar({})
comprobar("I", "un dict vacio da veredicto (y no VERDE)",
          v not in ("VERDE",) and not str(v).startswith("EXCEPCION"), f"{v}",
          "AMBAR/ROJO", "P1")

# FALSO ROJO introducido al arreglar los P0: una factura coherente (base+IVA=total)
# a la que la captura no desgloso los tramos NO es un descuadre aritmetico.
v, mot = evaluar({**BASE_FILA, 'base_total': '100', 'iva_total': '21',
                  'total_factura': '121'})
comprobar("I", "base+IVA coherentes sin desglose de tramos NO es ROJO (falso rojo)",
          v != "ROJO", f"veredicto={v} ({mot})", "AMBAR: falta el desglose, no hay descuadre", "P1")

# Semantica del veredicto: ROJO significa "he encontrado un error en la factura".
# No poder leer los importes no es un error de la factura.
v, _ = evaluar({**BASE_FILA, 'base_total': '', 'iva_total': '', 'total_factura': ''})
comprobar("I", "importes ilegibles -> AMBAR (revision), no ROJO (error)",
          v == "AMBAR", f"veredicto={v}", "AMBAR", "P1")


# ---------------------------------------------------------------------------
print("\n=== FAMILIA J — El techo fiscal: facturas LEGALES que deben poder ser VERDE ===")
# Medido el 20-08-2026: seis categorias de facturas perfectamente legales no
# podian llegar NUNCA a VERDE porque el modelo de datos solo sabia 4/10/21.
# No era un falso verde (es seguro), pero condenaba esas facturas a revision
# manual permanente: un techo a CUANTO se puede automatizar.
for nombre, extra in (
    ("exenta art.20 LIVA", {'base_total': '1000', 'iva_total': '0', 'total_factura': '1000',
                            'naturaleza_operacion': 'EXENTA'}),
    ("intracomunitaria", {'base_total': '500', 'iva_total': '0', 'total_factura': '500',
                          'naturaleza_operacion': 'INTRACOMUNITARIA'}),
    ("inversion del sujeto pasivo", {'base_total': '2000', 'iva_total': '0', 'total_factura': '2000',
                                     'naturaleza_operacion': 'INVERSION_SUJETO_PASIVO'}),
    ("no sujeta", {'base_total': '300', 'iva_total': '0', 'total_factura': '300',
                   'naturaleza_operacion': 'NO_SUJETA'}),
    ("tipo 0% (pan, leche, fruta)", {'base_total': '80', 'iva_total': '0', 'total_factura': '80',
                                     'tramos_iva': [{'tipo': 0, 'base': 80, 'cuota': 0}]}),
    ("tipo 5% (electricidad)", {'base_total': '100', 'iva_total': '5', 'total_factura': '105',
                                'tramos_iva': [{'tipo': 5, 'base': 100, 'cuota': 5}]}),
    ("multi-tramo 21+10+4", {'base_total': '160', 'iva_total': '26.4', 'total_factura': '186.4',
                             'tramos_iva': [{'tipo': 21, 'base': 100, 'cuota': 21},
                                            {'tipo': 10, 'base': 50, 'cuota': 5},
                                            {'tipo': 4, 'base': 10, 'cuota': 0.4}]}),
):
    v, mot = evaluar({**BASE_FILA, **extra})
    comprobar("J", f"{nombre} PUEDE llegar a VERDE",
              v == "VERDE", f"veredicto={v} ({mot})", "VERDE", "P1")

# RECARGO DE EQUIVALENCIA (art. 154 LIVA): obligatorio para el comercio
# minorista persona fisica. Con 19 autonomos en cartera no es un caso raro, y
# antes salia ROJO SIEMPRE porque base+IVA no cuadraba con el total.
for nombre, extra in (
    ("recargo 5,2% (sobre tipo 21%)", {'base_21': '100', 'base_total': '100', 'iva_total': '21',
                                       'recargo_equivalencia': '5.2', 'total_factura': '126.20'}),
    ("recargo 1,4% (sobre tipo 10%)", {'base_10': '100', 'base_total': '100', 'iva_total': '10',
                                       'recargo_equivalencia': '1.4', 'total_factura': '111.40'}),
    ("recargo 0,5% (sobre tipo 4%)", {'base_4': '100', 'base_total': '100', 'iva_total': '4',
                                      'recargo_equivalencia': '0.5', 'total_factura': '104.50'}),
):
    v, mot = evaluar({**BASE_FILA, **extra})
    comprobar("J", f"{nombre} PUEDE llegar a VERDE",
              v == "VERDE", f"veredicto={v} ({mot})", "VERDE", "P1")

v, _ = evaluar({**BASE_FILA, 'base_21': '100', 'base_total': '100', 'iva_total': '21',
                'recargo_equivalencia': '99', 'total_factura': '220'})
comprobar("J", "recargo inventado -> ROJO (no es puerta trasera)",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")

v, _ = evaluar({**BASE_FILA, 'base_21': '100', 'base_total': '100', 'iva_total': '21',
                'recargo_equivalencia': '1.4', 'total_factura': '122.40'})
comprobar("J", "recargo del tipo que no toca (1,4 sobre 21%) -> ROJO",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")

# Y lo que la apertura NO puede haber roto: declarar una naturaleza no es una
# puerta trasera para saltarse las comprobaciones.
v, _ = evaluar({**BASE_FILA, 'base_total': '1000', 'iva_total': '210',
                'total_factura': '1210', 'naturaleza_operacion': 'EXENTA'})
comprobar("J", "exenta que SI repercute IVA -> ROJO (se contradice)",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")

v, _ = evaluar({**BASE_FILA, 'base_total': '100', 'iva_total': '21',
                'total_factura': '121', 'naturaleza_operacion': 'LOQUESEA'})
comprobar("J", "naturaleza inventada -> ROJO, nunca pasa por la de por defecto",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")

v, _ = evaluar({**BASE_FILA, 'base_total': '999', 'iva_total': '21', 'total_factura': '1020',
                'tramos_iva': [{'tipo': 21, 'base': 100, 'cuota': 21}]})
comprobar("J", "tramos que no suman la base total -> ROJO",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")


print("\n=== FAMILIA K — Los tres puntos del techo que dependian del prompt ===")
# Cerrados el 20-08-2026. Los tres son NO_APLICA mientras la captura no emita
# los campos nuevos, asi que no cambian nada de lo existente; se activan solos
# en cuanto el prompt v2 este en uso.
BUENA_K = {**BASE_FILA, 'base_21': '100', 'base_total': '100',
           'iva_total': '21', 'total_factura': '121'}

# 1 — DOBLE LECTURA DEL TOTAL. Ataca el error COHERENTE: el modelo lee un
# ticket con dos totales y coge el que no es. La aritmetica cuadra igual.
v, _ = evaluar({**BUENA_K, 'total_factura_2': '121'})
comprobar("K", "doble lectura: los dos totales coinciden -> VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P1")
v, _ = evaluar({**BUENA_K, 'total_factura_2': '999'})
comprobar("K", "doble lectura: los totales DIFIEREN -> ROJO",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")
v, _ = evaluar(BUENA_K)
comprobar("K", "sin segundo total, el comportamiento no cambia -> VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P0")

# 2 — CONFIANZA POR CAMPO. Solo puede BAJAR el veredicto: lo que el modelo diga
# de si mismo no es evidencia independiente.
v, _ = evaluar({**BUENA_K, 'confianza_campos': {'nif': 'ALTA', 'base_total': 'BAJA'}})
comprobar("K", "confianza por campo: un critico flojo -> AMBAR",
          v == "AMBAR", f"veredicto={v}", "AMBAR", "P1")
v, _ = evaluar({**BUENA_K, 'confianza_campos': {
    'nif': 'ALTA', 'fecha_expedicion': 'ALTA', 'nº_documento': 'ALTA',
    'base_total': 'ALTA', 'iva_total': 'ALTA', 'total_factura': 'ALTA'}})
comprobar("K", "confianza por campo: todos los criticos altos -> VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P1")

# 3 — TRIANGULACION DE IDENTIDAD. El peor error posible: un NIF mal leido que da
# checksum valido Y resulta ser el de OTRO proveedor real. No hay nada
# aritmetico que falle, asi que ningun guard de calculo lo puede ver.
v, _ = evaluar({**BUENA_K, 'nif_margen': NIF_OK, 'nombre_margen': 'PROVEEDOR PILOTO SL'})
comprobar("K", "triangulacion: cabecera y margen concuerdan -> VERDE",
          v == "VERDE", f"veredicto={v}", "VERDE", "P1")
v, _ = evaluar({**BUENA_K, 'nif_margen': 'B12345678', 'nombre_margen': 'PROVEEDOR PILOTO SL'})
comprobar("K", "triangulacion: el margen dice OTRO NIF -> no puede ser VERDE",
          v != "VERDE", f"veredicto={v}", "AMBAR o ROJO", "P0")
v, _ = evaluar({**BUENA_K, 'proveedor': 'EMPRESA DISTINTA SA',
                'nif_margen': NIF_OK, 'nombre_margen': 'EMPRESA DISTINTA SA'})
comprobar("K", "triangulacion: NIF casa pero el NOMBRE no (el peor caso) -> no VERDE",
          v != "VERDE", f"veredicto={v}", "AMBAR o ROJO", "P0")


print("\n=== FAMILIA L — El 5 confundido con un 8 (medido, no supuesto) ===")
# La preocupacion central del titular, convertida en prueba: se coge una factura
# correcta y se cambia UN digito. Exhaustivo, no muestreado.
FACT_OCR = {**BASE_FILA, 'nº_documento': 'FAC-2026-0158',
            'base_21': '458.00', 'base_total': '458.00',
            'iva_total': '96.18', 'total_factura': '554.18'}
_colados_euros, _n_euros = [], 0
for _campo in ('base_21', 'base_total', 'iva_total', 'total_factura'):
    _orig = FACT_OCR[_campo]
    _punto = _orig.rfind('.')
    for _i, _ch in enumerate(_orig):
        if not _ch.isdigit() or (_punto != -1 and _i > _punto):
            continue          # solo digitos de EUROS, no de centimos
        for _nuevo in '0123456789':
            if _nuevo == _ch:
                continue
            _n_euros += 1
            _f = dict(FACT_OCR)
            _f[_campo] = _orig[:_i] + _nuevo + _orig[_i + 1:]
            if evaluar(_f)[0] == "VERDE":
                _colados_euros.append(f"{_campo}:{_orig}->{_f[_campo]}")
comprobar("L", f"ningun error de 1 digito en los EUROS se cuela ({_n_euros} mutaciones)",
          not _colados_euros, f"{len(_colados_euros)} colados: {_colados_euros[:3]}",
          "0 colados", "P0")

# El NIF esta protegido por su digito de control: un digito cambiado no pasa.
_colados_nif = 0
_orig = FACT_OCR['nif']
for _i, _ch in enumerate(_orig):
    if not _ch.isdigit():
        continue
    for _nuevo in '0123456789':
        if _nuevo == _ch:
            continue
        _f = dict(FACT_OCR)
        _f['nif'] = _orig[:_i] + _nuevo + _orig[_i + 1:]
        if evaluar(_f)[0] == "VERDE":
            _colados_nif += 1
comprobar("L", "ningun error de 1 digito en el NIF se cuela (checksum)",
          _colados_nif == 0, f"{_colados_nif} colados", "0 colados", "P0")


print("\n=== FAMILIA M — Las dos clases de AMBAR y el proveedor nuevo ===")
BASE_M = {**BASE_FILA, 'base_21': '100', 'base_total': '100',
          'iva_total': '21', 'total_factura': '121'}

# Un proveedor NUEVO daba ROJO: factura impecable de alguien con quien no se
# habia trabajado. La auditoria lo senalo en la ronda 2 y llevaba abierto desde
# entonces. Que sea DESCONOCIDO no es que sea INVALIDO.
v, mot = evaluar({**BASE_M, 'nif': '12345678Z'})
comprobar("M", "proveedor nuevo con NIF valido NO es ROJO",
          v == "AMBAR", f"veredicto={v} ({mot[:70]})", "AMBAR", "P0")
comprobar("M", "proveedor nuevo se etiqueta [CRITERIO], no [FALTA DATO]",
          "[CRITERIO]" in mot, mot[:70], "[CRITERIO]", "P1")

# Lo invalido lo sigue cazando otro guard, y sigue siendo ROJO.
v, _ = evaluar({**BASE_M, 'nif': '12345678Y'})
comprobar("M", "NIF con checksum invalido sigue dando ROJO",
          v == "ROJO", f"veredicto={v}", "ROJO", "P0")

# Un dato ilegible es trabajo de BUSCAR, no de DECIDIR.
v, mot = evaluar({**BASE_M, 'base_total': 'abc', 'iva_total': 'abc', 'total_factura': 'abc'})
comprobar("M", "importes ilegibles se etiquetan [FALTA DATO]",
          "[FALTA DATO]" in mot, mot[:70], "[FALTA DATO]", "P1")

# Regla de mezcla: si falta un dato Y ademas hay que decidir, manda el dato.
v, mot = evaluar({**BASE_M, 'nif': '12345678Z', 'fecha_expedicion': ''})
comprobar("M", "criterio + falta de dato a la vez -> manda [FALTA DATO]",
          "[FALTA DATO]" in mot, mot[:70], "[FALTA DATO] (primero se consigue el dato)", "P1")


print("\n=== FAMILIA N — El criterio sale de los 10 anos: patron de cartera ===")
# El mapeo por cliente se indexa por CUENTA CONTABLE, que es distinta en cada
# cliente, asi que no se podia consultar entre clientes. Indexado por NIF si.
_NIF_CART = "12345678Z"
def _asiento(a, cta_prov, cta_gasto, nif):
    return [{'ASIEN': a, 'SUBCTA': cta_prov, 'TERNIF': nif},
            {'ASIEN': a, 'SUBCTA': cta_gasto, 'TERNIF': nif}]
_diarios = {'C01': [], 'C02': []}
for _i in range(25):
    _diarios['C01'] += _asiento(_i, '410009', '623001', _NIF_CART)
for _i in range(18):
    _diarios['C02'] += _asiento(_i, '400031', '623001', _NIF_CART)
_cartera = m.construir_mapeo_cartera(_diarios)

comprobar("N", "el patron de cartera se indexa por NIF, no por cuenta contable",
          _NIF_CART in _cartera, f"claves: {list(_cartera)[:3]}", f"{_NIF_CART} presente", "P1")
comprobar("N", "cuenta la fuerza en CLIENTES distintos, no solo en asientos",
          _cartera[_NIF_CART]['n_clientes'] == 2,
          f"n_clientes={_cartera[_NIF_CART]['n_clientes']}", "2", "P1")

_f = {**BASE_FILA, 'nif': _NIF_CART, 'base_21': '100', 'base_total': '100',
      'iva_total': '21', 'total_factura': '121'}
_v, _mot, _ = m.evaluar_fila_v4(_f, set(), {}, {}, {}, MAESTRO, 2020,
                                NIF_TITULAR, 2026, mapeo_cartera=_cartera)
comprobar("N", "un proveedor nuevo para el cliente llega con EVIDENCIA de cartera",
          "EVIDENCIA DE CARTERA" in _mot, _mot[:80],
          "el motivo incluye lo que dice la cartera", "P1")
comprobar("N", "la evidencia se presenta como HIPOTESIS, nunca como hecho",
          "hipotesis" in _mot.lower(), _mot[-80:],
          "el motivo dice explicitamente que es una hipotesis", "P0")

# Un patron NO puede convertir en VERDE lo que necesita criterio.
comprobar("N", "el patron de cartera NO sube el veredicto a VERDE",
          _v != "VERDE", f"veredicto={_v}", "AMBAR: sigue decidiendo el humano", "P0")


print("\n=== FAMILIA O — Los guards que nunca habian saltado (cobertura) ===")
# cobertura_guards.py destapo que 5 guards estaban CABLEADOS pero jamas habian
# llegado a un estado util en ninguna suite: la suite pasaba, el auditor daba
# verde, y nadie habia comprobado nunca que supieran decir FALLO cuando toca.
# "Cableado" no es "probado".
BASE_O = {**BASE_FILA, 'base_21': '100', 'base_total': '100',
          'iva_total': '21', 'total_factura': '121'}

def _ev(fila, **kw):
    v, mot, g = m.evaluar_fila_v4(fila, set(), kw.pop('hist', {}), kw.pop('fmt', {}),
                                  kw.pop('sec', {}), MAESTRO, 2020, NIF_TITULAR,
                                  2026, **kw)
    return v, mot, g

# 1 — confianza_captura: la captura declara DUDA
_v, _m2, _g = _ev({**BASE_O, 'verificacion': 'DUDA'})
comprobar("O", "confianza_captura baja el veredicto cuando la captura duda",
          _g['confianza_captura'][0] == "BAJA" and _v == "AMBAR",
          f"{_g['confianza_captura'][0]} / {_v}", "BAJA / AMBAR", "P1")

# 2 — cuenta_gasto_coherente. La primera version de esta prueba se conformaba
# con "distinto de OK" y pasaba en verde con NO_APLICA, tapando que la rama FALLO
# del guard era codigo muerto: no comparaba nada. Es el mismo fallo de metodo que
# caza la FAMILIA G. Ahora se le exige el FALLO concreto.
_mapeo = {'400001': {'cuenta_gasto': '621000', 'grupo_pgc': 'Arrendamientos',
                     'confianza': 'ALTA', 'n_asientos': 47, 'n_esta': 47}}
_v, _m2, _g = _ev({**BASE_O, 'cuenta_proveedor': '400001', 'cuenta_debe': '600000'},
                  mapeo_cuenta_gasto=_mapeo)
comprobar("O", "cuenta_gasto_coherente FALLA si la cuenta no casa con 10 anos",
          _g['cuenta_gasto_coherente'][0] == "FALLO" and _v == "AMBAR",
          f"{_g['cuenta_gasto_coherente'][0]} / {_v}", "FALLO / AMBAR", "P1")
comprobar("O", "y ese desvio de cuenta es [CRITERIO], no un error de dato",
          "[CRITERIO]" in _m2, _m2[:70], "[CRITERIO]", "P1")

# 2-bis — misma decision contable, distinto detalle: NO es senal
_v, _m2, _g = _ev({**BASE_O, 'cuenta_proveedor': '400001', 'cuenta_debe': '621001'},
                  mapeo_cuenta_gasto=_mapeo)
comprobar("O", "621001 vs 621000 no salta: mismo grupo del PGC, mismo criterio",
          _g['cuenta_gasto_coherente'][0] == "OK",
          _g['cuenta_gasto_coherente'][0], "OK", "P1")

# 2-ter — control negativo: un solo asiento no es un patron, es una anecdota
_flojo = {'400001': {'cuenta_gasto': '621000', 'grupo_pgc': 'Arrendamientos',
                     'confianza': 'ALTA', 'n_asientos': 1, 'n_esta': 1}}
_v, _m2, _g = _ev({**BASE_O, 'cuenta_proveedor': '400001', 'cuenta_debe': '600000'},
                  mapeo_cuenta_gasto=_flojo)
comprobar("O", "un historico de 1 asiento NO acusa a la factura nueva",
          _g['cuenta_gasto_coherente'][0] == "NO_APLICA",
          _g['cuenta_gasto_coherente'][0], "NO_APLICA", "P1")

# 2-quater — sin cuenta propuesta no hay nada que comparar, y eso NO es OK
_v, _m2, _g = _ev({**BASE_O, 'cuenta_proveedor': '400001'}, mapeo_cuenta_gasto=_mapeo)
comprobar("O", "sin cuenta propuesta el guard NO dice OK (falso verde por omision)",
          _g['cuenta_gasto_coherente'][0] == "NO_APLICA",
          _g['cuenta_gasto_coherente'][0], "NO_APLICA", "P1")

# 3 — estructura_reconocida: el formato del numero no casa con el del proveedor
_fmt = {'PROVEEDOR PILOTO SL': {
    'ejemplos': ['FAC-2026-001', 'FAC-2026-002', 'FAC-2025-317'],
    'n_facturas_vistas': 40}}
_v, _m2, _g = _ev({**BASE_O, 'nº_documento': 'XX/9999'}, fmt=_fmt)
comprobar("O", "estructura_reconocida salta con un formato de numero distinto",
          _g['estructura_reconocida'][0] != "NO_APLICA",
          _g['estructura_reconocida'][0], "distinto de NO_APLICA", "P1")

# 4 — secuencia_documental_proveedor: numero muy fuera de la serie
_sec = {'PROVEEDOR PILOTO SL': {'numeros_vistos': [str(n) for n in range(1000, 1040)]}}
_v, _m2, _g = _ev({**BASE_O, 'nº_documento': '999999'}, sec=_sec)
comprobar("O", "secuencia_documental salta con un numero fuera de serie",
          _g['secuencia_documental_proveedor'][0] != "NO_APLICA",
          _g['secuencia_documental_proveedor'][0], "distinto de NO_APLICA", "P1")

# 5 — tipo_operacion_especial: cuenta del grupo 2 (inmovilizado)
_v, _m2, _g = _ev({**BASE_O, 'cuenta_debe': '218000', 'concepto': 'compra furgoneta'})
comprobar("O", "tipo_operacion_especial frena un inmovilizado a AMBAR",
          _g['tipo_operacion_especial'][0] == "AMBAR" and _v == "AMBAR",
          f"{_g['tipo_operacion_especial'][0]} / {_v}", "AMBAR / AMBAR", "P1")
comprobar("O", "y ese AMBAR se etiqueta [CRITERIO], no [FALTA DATO]",
          "[CRITERIO]" in _m2, _m2[:70], "[CRITERIO]", "P1")



print("\n=== FAMILIA P — El motivo dice TODO lo que esta mal, no lo primero ===")
# Medido el 21-08-2026: una factura con seis defectos reales devolvia UN motivo.
# Quien revisa a mano arregla ese, vuelve a pasar el motor, y aparece el
# siguiente. Seis vueltas para una factura, y el AMBAR ya juntaba todos sus
# NO_COMPROBADO desde el principio: la asimetria no tenia razon de ser.
_seis = {'nif': 'B12345678',            # checksum invalido (inventado)
         'proveedor': 'PROVEEDOR PILOTO SL',
         'nº_documento': 'F1',
         'fecha_expedicion': '2019-03-15',   # antes del alta Y de otro ejercicio
         'base_total': '100', 'base_21': '100',
         'iva_total': '50',                  # no es el 21% de 100
         'total_factura': '999',             # no es base+iva
         'verificacion': 'OK'}
_v, _m2, _g = m.evaluar_fila_v4(_seis, set(), {}, {}, {}, MAESTRO, 2020, None, 2026)
_rotos = [n for n, (e, _) in _g.items() if e == "FALLO"]
comprobar("P", "seis defectos a la vez siguen dando ROJO", _v == "ROJO", _v, "ROJO", "P0")
comprobar("P", "el motivo los nombra TODOS, no solo el primero",
          all(n in _m2 for n in _rotos),
          f"{sum(n in _m2 for n in _rotos)}/{len(_rotos)} nombrados",
          f"{len(_rotos)}/{len(_rotos)}", "P1")
comprobar("P", "y el titular del motivo no cambia (nadie que lo lea se rompe)",
          _m2.startswith("aritmetica_base_tipo:"), _m2[:30], "aritmetica_base_tipo:", "P1")

# Lo mismo en AMBAR: dos senales dedicadas a la vez tienen que salir las dos.
_fmt_p = {'PROVEEDOR PILOTO SL': {'ejemplos': ['FAC-2026-001', 'FAC-2026-002'],
                                  'n_facturas_vistas': 40}}
_v, _m2, _g = _ev({**BASE_O, 'nº_documento': 'XX/9999', 'cuenta_debe': '218000',
                   'concepto': 'compra furgoneta'}, fmt=_fmt_p)
comprobar("P", "dos senales AMBAR a la vez se declaran las dos",
          "estructura_reconocida" in _m2 and "tipo_operacion_especial" in _m2,
          _m2[:90], "las dos nombradas", "P1")
comprobar("P", "mezcla de dato y criterio -> manda [FALTA DATO], primero el dato",
          "[FALTA DATO]" in _m2, _m2[:40], "[FALTA DATO]", "P1")

# Y la etiqueta que faltaba: secuencia_documental era el UNICO AMBAR sin clase.
_sec_p = {'PROVEEDOR PILOTO SL': {'numeros_vistos': [str(n) for n in range(1000, 1040)]}}
_v, _m2, _g = _ev({**BASE_O, 'nº_documento': '999999'}, sec=_sec_p)
comprobar("P", "secuencia_documental ya sale con clase, no suelta",
          _m2.startswith(("[CRITERIO]", "[FALTA DATO]")), _m2[:30],
          "[CRITERIO] o [FALTA DATO]", "P1")


print("\n=== FAMILIA Q — La factura de camara normal: base, IVA y total, sin desglose ===")
# Lo destapo el ensayo de la cadena LOCAL el 21-08-2026. Sin desglose por tipos,
# el motor daba NO_COMPROBADO y TODA factura salia AMBAR. Y una captura de camara
# corriente no trae desglose: trae base, IVA y total. Con eso, las 91 facturas de
# la prueba historica habrian salido las 91 en AMBAR y no se habria medido nada.
#
# El desglose no hace falta para comprobar lo que SI se puede comprobar.
_SIN = {k: v for k, v in BASE_FILA.items()}

def _sin_desglose(base, iva, total):
    return {**_SIN, 'base_total': base, 'iva_total': iva, 'total_factura': total}

# Solo los tipos EXTREMOS abren el VERDE, y no por prudencia: la primera version
# acepto CUALQUIER tipo legal, y la prueba de fuerza bruta de mas abajo encontro
# 16 formas de colarse. La mas realista: una factura de supermercado con 100 EUR
# al 0% y 100 EUR al 10% da un 5% efectivo CLAVADO, y el 5% es legal desde 2023.
# Habria salido VERDE afirmando una composicion fiscal falsa — y el modelo 303
# necesita las bases POR TIPO. La prueba caza el fallo que yo mismo introduje.
for _b, _i, _t, _tipo in (('100', '21', '121', '21%'),
                          ('1000', '210', '1210', '21%'),
                          ('50', '0', '50', '0%')):
    _v, _m2 = evaluar(_sin_desglose(_b, _i, _t))
    comprobar("Q", f"factura correcta al {_tipo} sin desglose llega a VERDE",
              _v == "VERDE", f"{_v}: {_m2[:60]}", "VERDE", "P1")

# Los tipos INTERMEDIOS no abren el VERDE aunque sean legales, justamente porque
# se pueden fabricar mezclando. No es un error de la factura: es que sin el
# desglose no se puede afirmar la composicion. AMBAR, nunca ROJO.
for _b, _i, _t, _caso in (('200', '20', '220', '10% legal pero intermedio'),
                          ('100', '4', '104', '4% legal pero intermedio'),
                          ('200', '10', '210', '5% que puede ser 0%+10%'),
                          ('100', '13', '113', '13% que no es legal'),
                          ('200', '31', '231', 'dos tipos mezclados')):
    _v, _m2 = evaluar(_sin_desglose(_b, _i, _t))
    comprobar("Q", f"sin desglose, {_caso} -> AMBAR", _v == "AMBAR", _v, "AMBAR", "P0")

# La demostracion, exhaustiva y no de palabra: ninguna mezcla de dos tipos
# legales distintos puede dar un 0% ni un 21% efectivos con las dos bases > 0.
#   21%  es el MAXIMO: cualquier mezcla con un tipo menor da menos de 21.
#   0%   es el MINIMO: cualquier tipo positivo suma cuota.
# Se comprueba con aritmetica exacta (Fraction), no en coma flotante, y sobre
# 200x200 repartos por pareja de tipos: 400.000 mezclas.
from fractions import Fraction as _F
_TIPOS = (0, 4, 5, 10, 21)
_colados = []
for _i1, _t1 in enumerate(_TIPOS):
    for _t2 in _TIPOS[_i1 + 1:]:
        for _b1 in range(1, 201):
            for _b2 in range(1, 201):
                if _F(_b1 * _t1 + _b2 * _t2, _b1 + _b2) in (_F(0), _F(21)):
                    _colados.append((_t1, _b1, _t2, _b2))
comprobar("Q", "ninguna mezcla de dos tipos finge un 0% ni un 21% (400.000 mezclas)",
          not _colados, f"{len(_colados)} se colarian", "0", "P0")

# Control positivo de esa misma prueba: con los tipos intermedios incluidos SI
# aparecen colados. Si no apareciera ninguno, la prueba de arriba no probaria
# nada (leccion de la FAMILIA G).
_con_intermedios = [1 for _b1 in range(1, 101) for _b2 in range(1, 101)
                    if _F(_b1 * 0 + _b2 * 10, _b1 + _b2) == _F(5)]
comprobar("Q", "control positivo: con tipos intermedios la prueba SI encuentra colados",
          len(_con_intermedios) > 0, f"{len(_con_intermedios)}", ">0", "P1")

# El limite DECLARADO, que sigue existiendo y conviene tenerlo escrito: un error
# de escala coherente en los tres campos a la vez (leer 100 donde ponia 1.000,
# 21 donde ponia 210, 121 donde ponia 1.210) es indistinguible de una factura
# correcta mas pequena. Ninguna redundancia interna puede cazar eso: haria falta
# el historico de importes del proveedor, que es otro guard.
_v, _m2 = evaluar(_sin_desglose('100', '21', '121'))
comprobar("Q", "LIMITE DECLARADO: un error de escala coherente en los 3 campos pasa",
          _v == "VERDE", _v, "VERDE (y esta bien que sea asi, ver comentario)", "P1")


print("\n=== FAMILIA R — Lo que destapo el barrido exhaustivo (21-08-2026) ===")
# barrido_falsos_verdes.py no elige los ataques: los enumera. Coge una factura
# VERDE y le aplica TODAS las mutaciones mecanicas de UN campo. De 1.351
# mutaciones salieron tres defectos que ninguno de los 87 ataques escritos a mano
# habia tocado. Aqui quedan fijados para que no vuelvan.

_NIF_R = "B12345674"
_M_R = {_NIF_R: {'titulo': 'PROVEEDOR PILOTO SL', 'cuenta': '400001'}}
_BASE_R = {'nif': _NIF_R, 'proveedor': 'PROVEEDOR PILOTO SL',
           'nº_documento': 'FAC-2026-0117', 'fecha_expedicion': '2026-03-15',
           'base_21': '1000.00', 'base_total': '1000.00',
           'iva_total': '210.00', 'total_factura': '1210.00', 'verificacion': 'OK'}

def _ev_r(fila, **kw):
    return m.evaluar_fila_v4(fila, set(), kw.pop('hist', {}), kw.pop('fmt', {}),
                             kw.pop('sec', {}), _M_R, 2015, None, 2026, **kw)

# --- R1: MISSING vs ZERO en el desglose, otra vez -------------------------
# base_total=1000, base_21=0, iva=210 salia VERDE afirmando "toda la base al
# 21%", mientras el propio desglose decia 0 EUR al 21%. tramos() descarta el cero
# ("un cero no es un tramo", correcto para sumar) y eso lo hacia indistinguible
# de una factura sin desglose, que si puede usar la comprobacion global.
_v, _m2, _g = _ev_r({**_BASE_R, 'base_21': '0.00'})
comprobar("R", "un desglose que se contradice con la base NO llega a VERDE",
          _v == "AMBAR", _v, "AMBAR", "P0")
comprobar("R", "y se declara como falta de dato, no como error de la factura",
          "[FALTA DATO]" in _m2 and "DECLARA desglose" in _m2, _m2[:70],
          "[FALTA DATO] ... DECLARA desglose", "P1")

# La distincion completa, que es donde vive el fallo:
for _valor, _esperado, _caso in ((None, "VERDE", "ausente: captura de camara, no dice nada"),
                                 ("", "VERDE", "columna vacia de un CSV: tampoco dice nada"),
                                 ("0.00", "AMBAR", "un cero ESCRITO: si dice algo, y se contradice"),
                                 ("abc", "AMBAR", "ilegible: dice algo que no se puede leer"),
                                 ("1000.00", "VERDE", "correcto: suma la base total")):
    _f = {k: v for k, v in _BASE_R.items() if not (k == 'base_21' and _valor is None)}
    if _valor is not None:
        _f['base_21'] = _valor
    _v, _m2, _g = _ev_r(_f)
    comprobar("R", f"base_21 {_caso} -> {_esperado}", _v == _esperado, _v, _esperado, "P0")

# --- R2: la fecha en formato espanol ---------------------------------------
# Los tres guards de fecha hacian int(cadena[:4]): daban por hecho el ISO. Con
# '15/03/2026' —el formato NORMAL en Espana, el que exporta Excel— eso da
# ValueError y la factura se iba a AMBAR. Y el contrato ya sabia parsearlo desde
# el primer dia: los guards se saltaban la frontera de datos.
for _fecha in ('2026-03-15', '15/03/2026', '15-03-2026', '2026/03/15'):
    _v, _m2, _g = _ev_r({**_BASE_R, 'fecha_expedicion': _fecha})
    comprobar("R", f"fecha valida en formato {_fecha!r} llega a VERDE",
              _v == "VERDE", f"{_v}: {_m2[:50]}", "VERDE", "P1")

# Y lo que NO puede pasar: que aceptar mas formatos deje pasar una fecha imposible.
for _fecha in ('2026-13-15', '2026-02-30', '32/03/2026', '30/02/2026'):
    _v, _m2, _g = _ev_r({**_BASE_R, 'fecha_expedicion': _fecha})
    comprobar("R", f"fecha imposible {_fecha!r} sigue sin llegar a VERDE",
              _v != "VERDE", _v, "AMBAR o ROJO", "P0")

# --- R3: cuatro guards apagados en silencio por el nombre -------------------
# Las cuatro caches del motor se consultaban SOLO por el nombre del proveedor, y
# el nombre no tiene digito de control. "PROVEEDOR PILOTO S.L." con puntos ya es
# otro proveedor para un diccionario: los guards se declaraban NO_APLICA
# —"primera vez que lo veo"— y la factura salia VERDE con cuatro protecciones
# apagadas, sin distinguirse de un alta de verdad.
_fmt_r = {_NIF_R: {'ejemplos': ['FAC-2026-001', 'FAC-2026-002'],
                   'n_facturas_vistas': 40}}
for _nombre, _caso in (('PROVEEDOR PILOTO SL', 'exacto'),
                       ('PROVEEDOR PILOTO S.L.', 'con puntos'),
                       ('proveedor piloto sl', 'en minusculas'),
                       ('', 'vacio'),
                       ('OTRA COSA', 'completamente distinto')):
    _v, _m2, _g = _ev_r({**_BASE_R, 'nº_documento': 'XX/9999', 'proveedor': _nombre},
                        fmt=_fmt_r)
    comprobar("R", f"cache por NIF: el guard sigue vivo con el nombre {_caso}",
              _g['estructura_reconocida'][0] == "FALLO",
              _g['estructura_reconocida'][0], "FALLO", "P0")

# Y la compatibilidad, que no es un detalle: las caches que ya estan en el disco
# del despacho estan indexadas por NOMBRE. Romperlas seria cambiar un fallo
# silencioso por otro.
_fmt_viejo = {'PROVEEDOR PILOTO SL': {'ejemplos': ['FAC-2026-001', 'FAC-2026-002'],
                                      'n_facturas_vistas': 40}}
_v, _m2, _g = _ev_r({**_BASE_R, 'nº_documento': 'XX/9999'}, fmt=_fmt_viejo)
comprobar("R", "una cache antigua indexada por nombre sigue funcionando",
          _g['estructura_reconocida'][0] == "FALLO",
          _g['estructura_reconocida'][0], "FALLO", "P0")

# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
fallos = [r for r in resultados if not r[2]]
p0 = [r for r in fallos if r[5] == "P0"]
print(f"Pruebas: {len(resultados)}   en verde: {len(resultados)-len(fallos)}   "
      f"FALLAN: {len(fallos)}  (de ellas P0: {len(p0)})")

if fallos:
    print("\nDEFECTOS CONFIRMADOS EN PIE (esta lista ES la especificacion del arreglo):")
    for fam, nombre, _, obtenido, esperado, sev in fallos:
        print(f"  [{sev}] ({fam}) {nombre}")
    print("\nEl codigo de salida 1 es el resultado correcto mientras esto siga asi.")
    print("Esta suite NO esta cableada al hook de pre-commit a proposito: documenta")
    print("un estado conocido, no bloquea el trabajo en curso.")
    sys.exit(1)

print("\nEl motor sobrevive a toda la bateria de ataque conocida.")
sys.exit(0)
