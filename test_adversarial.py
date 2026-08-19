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
