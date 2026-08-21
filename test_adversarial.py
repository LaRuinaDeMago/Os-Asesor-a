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
