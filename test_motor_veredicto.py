"""
SUITE DE PRUEBAS DE REGRESION — motor_veredicto.py
Usa casos REALES ya verificados esta noche (clientes piloto, anonimizados), no datos inventados.
Objetivo: si alguien (Claude Code incluido) modifica el motor en el futuro, estas
pruebas fallan en el momento si se rompe algo que ya funcionaba - no se descubre
semanas despues con una factura real mal clasificada.

Ejecutar con: python3 -m pytest test_motor_veredicto.py -v
(o simplemente: python3 test_motor_veredicto.py  - corre sin pytest tambien)
"""

import sys

# Sin esto, una consola de Windows en cp1252 revienta al imprimir el banner
# final (✅/❌), DESPUES de que las 24 comprobaciones ya hayan corrido y
# pasado — un test que revienta al anunciar que paso se lee como que fallo,
# que es exactamente la trampa MISSING/ZERO que este proyecto existe para
# cazar. Mismo patron que scripts/privacy_scan.py.
#
# hasattr() es imprescindible aqui y no en todas partes: cobertura_guards.py
# IMPORTA este modulo con sys.stdout redirigido a un io.StringIO (para leerlo
# en silencio), y StringIO no tiene .reconfigure() — solo los flujos de
# consola reales. Sin el hasattr, ese caso concreto revienta con
# AttributeError. Lo mismo puede pasar bajo pytest, que tambien captura la
# salida con su propio objeto.
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from motor_veredicto import (
    guard_aritmetica_base_tipo, guard_cuadre_total, guard_nif_digito_control,
    guard_suma_tramos, guard_retencion_vs_error, guard_signo_efectivo,
    guard_sentido_compra_venta, guard_estructura_reconocida,
    guard_secuencia_documental_proveedor, guard_importe_atipico,
    guard_nif_casa_historico, guard_cuenta_gasto_coherente,
    guard_tipo_producto_iva_semantico, guard_tipo_operacion_especial,
    evaluar_fila_v4, calcular_veredicto_v4,
    construir_mapeo_cuenta_gasto, aprender_cuenta_gasto, reevaluar_tras_correccion,
    actualizar_caches_historicas, actualizar_mapeo_cuenta_gasto,
)
from nif_check import valida_nif

FALLOS = []


def check(cond, nombre):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


print("=== Nivel 1: Aritmetica (casos reales de esta noche) ===")
# Caso piloto C.382 (cliente anonimizado): base 132.90, 10%, cuota 13.29
check(guard_aritmetica_base_tipo(132.90, 0, 0, 13.29)[0] == "OK", "Caso piloto C.382 aritmetica")
# Caso piloto 11501 doble tipo: base10=40.29(10%), base21=162.38(21%), iva declarado 38.13 (4.03+34.10)
check(guard_aritmetica_base_tipo(40.29, 0, 162.38, 38.13)[0] == "OK", "Caso piloto 11501 doble tipo")
# Caso roto a proposito: base no cuadra
check(guard_aritmetica_base_tipo(100, 0, 0, 50)[0] == "FALLO", "Aritmetica rota detectada")

print("\n=== Nivel 1: NIF checksum (reales, anonimizados con checksum valido inventado) ===")
check(valida_nif("B12345674")[0] == True, "Proveedor piloto NIF valido")
check(valida_nif("12345678Z")[0] == True, "DNI piloto valido")
check(valida_nif("12345678Y")[0] == False, "NIF con letra incorrecta detectado (Z real vs Y puesta a proposito)")

print("\n=== Nivel 1: NIE y NIF-IVA UE (arreglo 25-08-2026, ver diag_nif.py) ===")
# Antes de este arreglo, un NIE caia en la rama de CIF (misma forma
# estructural: letra + 7 digitos + control) y se validaba con el algoritmo
# equivocado. NIE valido inventado, checksum matematicamente correcto
# (X -> 0, 01234567 % 23 = 19 -> letra 'L').
check(valida_nif("X1234567L")[0] == True, "NIE valido reconocido con su propio algoritmo")
check(valida_nif("X1234567M")[0] == False, "NIE con letra incorrecta detectado (L real vs M puesta a proposito)")
# NIF-IVA extranjero: formato reconocido, digito de control NO verificable
# sin VIES -> NO_COMPROBADO, nunca OK ni FALLO (ok=None).
check(valida_nif("DE123456789")[0] is None, "NIF-IVA UE: formato reconocido, NO_COMPROBADO (no OK ni FALLO)")
check(valida_nif("DE123456789")[1] == "NIF_IVA_UE", "NIF-IVA UE clasificado como tal")
# Campo con contenido pero demasiado corto para ser cualquier formato real
# (caso real anonimizado: 196 asientos con TERNIF de 1 caracter en el corpus,
# con la linea de acreedor tambien vacia -- dato nunca capturado, no un NIF
# invalido). SIN_DATO -> NO_COMPROBADO, no FALLO.
check(valida_nif("1")[0] is None, "Campo de 1 caracter: SIN_DATO, no FALLO (dato nunca capturado)")
check(valida_nif("1")[1] == "SIN_DATO", "Campo de 1 caracter clasificado como SIN_DATO")
# NIF/CIF incompleto (arreglo 25-08-2026, ver diag_nif_otro_residual.py):
# longitud 8 con forma de DNI o CIF a los que falta solo el ultimo caracter
# (el digito de control) -> SIN_DATO, no FALLO: no hay forma de comprobarlo,
# no es que este mal.
check(valida_nif("12345678")[0] is None, "8 digitos (DNI sin letra): SIN_DATO, no FALLO")
check(valida_nif("B1234567")[0] is None, "letra+7 digitos (CIF sin control): SIN_DATO, no FALLO")
# Control: 7 digitos NO encaja en esta forma (falta demasiado, no solo el
# digito de control) y sigue cayendo en DESCONOCIDO -> FALLO, sin ampliarse
# de mas.
check(valida_nif("1234567")[0] == False, "7 digitos sigue siendo FALLO (no se ha ampliado de mas)")

print("\n=== Nivel 1: DNI con el 0 inicial perdido (27-08-2026, sesion Cloud) ===")
# Distinto de los dos SIN_DATO de arriba: ahi falta el UNICO caracter que
# permite comprobar (el digito de control), aqui no falta nada -- el cero
# inicial no cambia el valor de num % 23, asi que SI se puede verificar
# del todo. DNI sintetico: '01234567' -> letra 'L' (checksum matematicamente
# valido, nunca un dato real). '1234567L' es lo que llega si algo leyo el
# campo como numero y se comio el cero inicial.
check(valida_nif("1234567L")[0] == True,
      "7 digitos + letra (DNI con el 0 inicial perdido): recuperable, se verifica de verdad")
check(valida_nif("1234567L")[1] == "DNI",
      "se clasifica como DNI, no como SIN_DATO -- no falta informacion, solo se escribio distinto")
check(valida_nif("1234567M")[0] == False,
      "7 digitos + letra incorrecta: sigue detectandose como FALLO (L real vs M puesta a proposito)")

print("\n=== Nivel 4: retencion_vs_error (caso real anonimizado) ===")
# base 661.15, iva 138.84, irpf -125.62, total 674.37 -> retencion 19%
r = guard_retencion_vs_error(661.15, 138.84, -125.62, 674.37)
check(r[0] == "OK", f"Caso piloto retencion 19% reconocida ({r[1]})")

print("\n=== Nivel 4: signo_efectivo (casos reales de proveedor piloto, abonos) ===")
check(guard_signo_efectivo("A010000531", "", -18.90, -22.87, "ABONO")[0] == "OK", "Abono proveedor piloto coherente")
check(guard_signo_efectivo("11501", "", 202.67, 240.80, None)[0] == "NO_APLICA",
      "Caso piloto 11501 NO marca FALLO (regresion del falso positivo ya corregido)")

print("\n=== Nivel PGC: cuenta_gasto (caso real anonimizado) ===")
# ACTUALIZADO 21-08-2026. Estas dos comprobaciones esperaban OK llamando al guard
# SIN cuenta propuesta, y por eso el guard podia limitarse a mirar si existia
# patron historico sin comparar nunca nada. El test estaba fijando el falso verde,
# no cazandolo. Ahora se le pasa la cuenta que se propone para la factura, que es
# el dato sobre el que el guard tiene que pronunciarse.
mapeo_test = {"410014": {"cuenta_gasto": "621000", "grupo_pgc": "Arrendamientos y cánones",
                         "confianza": "ALTA", "n_asientos": 47, "n_esta": 47}}
check(guard_cuenta_gasto_coherente("410014", mapeo_test, "621000")[0] == "OK", "Proveedor piloto -> 621000")
check(guard_cuenta_gasto_coherente("410014", mapeo_test, "600000")[0] == "FALLO",
      "Proveedor piloto contabilizado a 600000 -> FALLO (no casa con 47 asientos)")
check(guard_cuenta_gasto_coherente("410014", mapeo_test)[0] == "NO_APLICA",
      "Sin cuenta propuesta no hay nada que comparar -> NO_APLICA, nunca OK")
check(guard_cuenta_gasto_coherente("999999", mapeo_test, "621000")[0] == "NO_APLICA", "Proveedor nuevo -> NO_APLICA")

print("\n=== Aprendizaje: ciclo NO_APLICA -> decision asesor -> persistencia ===")
mapeo2 = {}
antes = guard_cuenta_gasto_coherente("410099", mapeo2, "625000")
mapeo2 = aprender_cuenta_gasto(mapeo2, "410099", "625000")
despues = guard_cuenta_gasto_coherente("410099", mapeo2, "625000")
check(antes[0] == "NO_APLICA" and despues[0] == "OK", "Ciclo de aprendizaje completo")
# Y lo que el ciclo de aprendizaje tiene que servir PARA: una vez el asesor lo
# decide una vez, la siguiente factura a otra cuenta se frena. Antes no podia.
check(guard_cuenta_gasto_coherente("410099", mapeo2, "600000")[0] == "FALLO",
      "Lo confirmado por el asesor SI frena la siguiente factura que se desvia")

print("\n=== IVA semantico (tabla oficial 2026) ===")
check(guard_tipo_producto_iva_semantico("aceite de oliva", 4)[0] == "OK", "Aceite oliva 4% correcto")
check(guard_tipo_producto_iva_semantico("aceite de oliva", 10)[0] == "FALLO", "Aceite oliva al 10% detectado como error")

print("\n=== Veredicto integrado (fila real completa: caso piloto C.382) ===")
fila_piloto = {
    'fecha_expedicion': '2026-06-25', 'nº_documento': 'C.382', 'proveedor': 'PROVEEDOR PILOTO EJEMPLO',
    'nif': '12345678Z', 'base_10': '132.90', 'base_4': '0', 'base_21': '0', 'base_total': '132.90',
    'iva_total': '13.29', 'irpf_retencion': '0', 'total_factura': '146.19', 'verificacion': 'OK',
}
v, motivo, guards = evaluar_fila_v4(fila_piloto, set(), {}, {}, {}, {}, 2025, None, None)
check(v == "VERDE", f"Caso piloto C.382 -> VERDE (dio {v}: {motivo})")

print("\n=== REGRESION del bug real (revision externa, 28-07-2026): ===")
print("=== reevaluar_tras_correccion debe usar evaluar_fila_v4 (16 guards), no v2 (8) ===")
# fila con un NIF que NO existe en el maestro -> si usa v4, nif_casa_historico
# debe evaluarse y dar FALLO -> ROJO. Si usara v2 (el bug ya corregido), ese
# guard ni se calcula y podria colarse como VERDE (corregido) indebidamente.
fila_test = {
    'fecha_expedicion': '2026-06-01', 'nº_documento': 'TEST-001', 'proveedor': 'PROVEEDOR FALSO SL',
    'nif': 'B12345678', 'base_10': '100.00', 'base_4': '0', 'base_21': '0', 'base_total': '100.00',
    'iva_total': '10.00', 'irpf_retencion': '0', 'total_factura': '110.00', 'verificacion': 'OK',
}
maestro_sin_este_nif = {"B99999999": {"titulo": "OTRO PROVEEDOR"}}
v, motivo, guards = reevaluar_tras_correccion(
    fila_test, set(), {}, {}, {}, maestro_sin_este_nif, 2025, None, None, {})
check("nif_casa_historico" in guards, "reevaluar_tras_correccion SI calcula nif_casa_historico (prueba que usa v4, no v2)")
check(v == "ROJO", f"NIF no encontrado en maestro -> ROJO incluso tras 'correccion' (dio {v})")

print("\n=== REGRESION (auditoria externa verificada, 26-08-2026): ===")
print("=== una correccion NO puede marcar la factura como duplicada de si misma ===")
# Reproduce el flujo real: la factura entra con un dato dudoso (AMBAR), y el
# MISMO set 'vistos_duplicado' de esa primera pasada se reutiliza al reevaluar
# tras la correccion -- exactamente como lo haria un orquestador real que
# procesa una tanda entera y va corrigiendo AMBAR sobre la marcha.
fila_ambar = {
    'fecha_expedicion': '2026-01-15', 'nº_documento': 'F-900', 'proveedor': 'PROVEEDOR PILOTO EJEMPLO',
    'nif': '12345678Z', 'base_10': '0', 'base_4': '0', 'base_21': '100.00', 'base_total': '100.00',
    'iva_total': '21.00', 'irpf_retencion': '0', 'total_factura': '121.00', 'verificacion': 'DUDA',
}
vistos_tanda = set()
v_antes, _, _ = evaluar_fila_v4(fila_ambar, vistos_tanda, {}, {}, {}, {}, 2020, None, None)
check(v_antes == "AMBAR", f"la factura de partida es AMBAR (confianza de captura en duda), dio {v_antes}")
fila_corregida_no_cambia_identidad = dict(fila_ambar)
fila_corregida_no_cambia_identidad['categoria_producto'] = 'oficina'  # corriges un campo que NO es la identidad
v_despues, motivo_despues, guards_despues = reevaluar_tras_correccion(
    fila_corregida_no_cambia_identidad, vistos_tanda, {}, {}, {}, {}, 2020, None, None, {})
check(guards_despues["anti_duplicado"][0] == "OK",
      f"la reevaluacion tras corregir un campo NO IDENTIFICATIVO no se marca duplicada de si misma "
      f"(anti_duplicado dio {guards_despues['anti_duplicado']}, veredicto {v_despues})")
check(v_despues == "VERDE (corregido)",
      f"y por tanto la factura SI llega a VERDE (corregido) (dio {v_despues}: {motivo_despues})")

print("\n=== tipo_operacion_especial (guard nuevo, casos SINTETICOS - sin caso real todavia) ===")
check(guard_tipo_operacion_especial('Fra C.382', '600000', '12345678Z')[0] == "NO_APLICA",
      "compra normal real (caso piloto) -> NO_APLICA, sin falso positivo")
check(guard_tipo_operacion_especial('Compra furgoneta', '218000', 'B12345678')[0] == "AMBAR",
      "cuenta de inmovilizado (218000) -> AMBAR")
check(guard_tipo_operacion_especial('Amortizacion anual furgoneta', '600000', 'B12345678')[0] == "AMBAR",
      "palabra 'amortizacion' en concepto -> AMBAR")
check(guard_tipo_operacion_especial('Fra compra material', '600000', 'DE123456789')[0] == "AMBAR",
      "NIF con prefijo de pais (DE) -> AMBAR, posible intracomunitario")

print("\n=== actualizar_caches_historicas (27-08-2026, hallazgo verificado de Diego) ===")
# retro_semaforo.py y validar_captura_historica.py pasaban {}, {}, {} para
# historico_proveedor/formato_cache/secuencia_cache EN CADA FACTURA -- nunca
# se acumulaban entre facturas, a diferencia del maestro de proveedores. Con
# las caches vacias, guard_importe_atipico/estructura_reconocida/secuencia_
# documental_proveedor no pueden devolver FALLO nunca (verificado leyendo
# cada uno): quedaban dormidos en las dos mediciones con corpus real de este
# proyecto. Esta prueba no solo comprueba la funcion nueva -- reproduce la
# secuencia EXACTA que los dos scripts ya ejecutan (evaluar, luego acumular)
# y demuestra el ANTES y el DESPUES lado a lado, sobre el mismo caso.
_NIF_HIST = "B12345674"
_PROV_HIST = "PROVEEDOR PILOTO SL"


def _fila_hist(total, doc):
    base = round(total / 1.21, 2)
    iva = round(total - base, 2)
    return {
        'nif': _NIF_HIST, 'proveedor': _PROV_HIST, 'nº_documento': doc,
        'fecha_expedicion': '2026-03-15', 'verificacion': 'OK',
        'base_21': str(base), 'base_total': str(base),
        'iva_total': str(iva), 'total_factura': str(total),
    }


# 4 facturas normales del mismo proveedor, importe estable (~121, poca
# desviacion) y numero de documento con la MISMA forma (FAC-2026-00N).
_normales = [_fila_hist(t, f"FAC-2026-{n:03d}")
             for n, t in enumerate([121.00, 123.42, 118.58, 122.21], start=1)]
# La 5a es un total 10 VECES el habitual -- un atipico real, no sutil.
_atipica_importe = _fila_hist(1210.00, "FAC-2026-005")
# Y una 5a distinta, mismo importe normal pero con el documento en una forma
# que no se parece a nada visto antes.
_atipica_forma = _fila_hist(121.00, "77/XYZ")

# --- ANTES del arreglo: exactamente el patron que tenian los dos scripts ---
_v_antes = None
for f in _normales + [_atipica_importe]:
    _v_antes, _, _g_antes = evaluar_fila_v4(f, set(), {}, {}, {}, {}, 2020, None, 2026)
    # {} en cada vuelta: nunca se acumula nada, exactamente el bug real.
check(_v_antes == "VERDE",
      f"ANTES del arreglo (caches vacias en cada vuelta): la factura con "
      f"10x el importe habitual sigue dando VERDE ({_v_antes}) -- el bug real, reproducido")

# --- DESPUES del arreglo: el patron que ya usan retro_semaforo.py y
# validar_captura_historica.py tras la correccion de hoy ---
_hist, _fmt, _sec = {}, {}, {}
for f in _normales:
    evaluar_fila_v4(f, set(), _hist, _fmt, _sec, {}, 2020, None, 2026)
    actualizar_caches_historicas(_hist, _fmt, _sec, f)
check(_hist.get(_NIF_HIST, {}).get('n_facturas_normales') == 4,
      f"tras 4 facturas normales, el historico acumulado tiene n=4 "
      f"(tiene {_hist.get(_NIF_HIST, {}).get('n_facturas_normales')})")

_v_despues, _mot_despues, _g_despues = evaluar_fila_v4(
    _atipica_importe, set(), _hist, _fmt, _sec, {}, 2020, None, 2026)
check(_g_despues['importe_atipico'][0] == "FALLO",
      f"DESPUES del arreglo: guard_importe_atipico SI detecta el 10x "
      f"(dio {_g_despues['importe_atipico']})")
check(_v_despues == "AMBAR",
      f"y la factura ya no es VERDE: es {_v_despues} (antes del arreglo era VERDE con el mismo caso)")

# --- Mismo patron, ahora aislando estructura_reconocida ---
_hist2, _fmt2, _sec2 = {}, {}, {}
for f in _normales:
    evaluar_fila_v4(f, set(), _hist2, _fmt2, _sec2, {}, 2020, None, 2026)
    actualizar_caches_historicas(_hist2, _fmt2, _sec2, f)
_v_forma, _mot_forma, _g_forma = evaluar_fila_v4(
    _atipica_forma, set(), _hist2, _fmt2, _sec2, {}, 2020, None, 2026)
check(_g_forma['estructura_reconocida'][0] == "FALLO",
      f"un numero de documento con forma nunca vista SI se detecta "
      f"(dio {_g_forma['estructura_reconocida']})")
check(_v_forma == "AMBAR",
      f"y baja el veredicto a AMBAR ({_v_forma}), con importe normal -- "
      f"aislado de importe_atipico")

# secuencia_documental_proveedor no se aisla en un tercer caso aparte: usa el
# MISMO bloque `if doc:` de actualizar_caches_historicas() que ya prueban los
# dos casos de arriba (secuencia_cache se rellena en la misma pasada que
# formato_cache) -- su logica propia ya tiene cobertura unitaria en la
# FAMILIA O de test_adversarial.py con caches construidas a mano.

print("\n=== actualizar_mapeo_cuenta_gasto (cuarto candidato, 27-08-2026) ===")
# guard_cuenta_gasto_coherente se indexa por CODIGO DE CUENTA (400015), no
# por NIF -- y el codigo de cuenta NO es identidad estable entre clientes
# distintos (FASE0_RESULTADOS.md §10.1). Esta prueba demuestra las dos
# mitades: (1) el mapeo incremental funciona igual que las caches de arriba,
# y (2) RESETEARLO al cambiar de cliente evita mezclar el patron de dos
# clientes distintos bajo el mismo codigo -- que es la razon por la que este
# arreglo no es identico al de las tres caches anteriores.
_CTA_PROV = "400015"  # mismo codigo, DOS clientes distintos abajo


def _fila_gasto(cuenta_debe, total=121.00, doc_n=1):
    return {**_fila_hist(total, f"FAC-2026-{doc_n:03d}"),
            'cuenta_proveedor': _CTA_PROV, 'cuenta_debe': cuenta_debe}


# --- Cliente A: 3 facturas a 621000 (arrendamientos), luego una a 600000 ---
_mapeo_a = {}
for f in [_fila_gasto("621000", doc_n=n) for n in range(1, 4)]:
    evaluar_fila_v4(f, set(), {}, {}, {}, {}, 2020, None, 2026, mapeo_cuenta_gasto=_mapeo_a)
    actualizar_mapeo_cuenta_gasto(_mapeo_a, f)
check(_mapeo_a[_CTA_PROV]['cuenta_gasto'] == "621000" and _mapeo_a[_CTA_PROV]['n_asientos'] == 3,
      f"tras 3 facturas a 621000, el mapeo del cliente A dice 621000/n=3 "
      f"(dice {_mapeo_a[_CTA_PROV]['cuenta_gasto']}/{_mapeo_a[_CTA_PROV]['n_asientos']})")

_v_a, _mot_a, _g_a = evaluar_fila_v4(
    _fila_gasto("600000", doc_n=4), set(), {}, {}, {}, {}, 2020, None, 2026,
    mapeo_cuenta_gasto=_mapeo_a)
check(_g_a['cuenta_gasto_coherente'][0] == "FALLO",
      f"una 4a factura del mismo proveedor a una cuenta DISTINTA (600000) "
      f"SI se detecta (dio {_g_a['cuenta_gasto_coherente']})")
check(_v_a == "AMBAR", f"y baja el veredicto a AMBAR (dio {_v_a})")

# --- Cliente B, MISMO codigo de cuenta 400015, patron distinto: 600000 ---
# SIN resetear (el bug que este reseteo evita): reutilizar _mapeo_a mezclaria
# el 621000 de A con el 600000 de B bajo la misma clave "400015". CON
# resetear (lo que hace retro_semaforo.py ahora, un dict nuevo por cliente):
# el patron de B se juzga solo contra B.
_mapeo_b = {}   # dict NUEVO -- esto es literalmente el reseteo por cliente
for f in [_fila_gasto("600000", doc_n=n) for n in range(1, 4)]:
    evaluar_fila_v4(f, set(), {}, {}, {}, {}, 2020, None, 2026, mapeo_cuenta_gasto=_mapeo_b)
    actualizar_mapeo_cuenta_gasto(_mapeo_b, f)

_v_b, _mot_b, _g_b = evaluar_fila_v4(
    _fila_gasto("600000", doc_n=4), set(), {}, {}, {}, {}, 2020, None, 2026,
    mapeo_cuenta_gasto=_mapeo_b)
check(_g_b['cuenta_gasto_coherente'][0] == "OK",
      f"con el mapeo reseteado, la 4a factura de B (tambien a 600000, "
      f"coherente con SU propio patron) da OK (dio {_g_b['cuenta_gasto_coherente']})")
check(_v_b == "VERDE" or (_v_b == "AMBAR" and "cuenta_gasto_coherente" not in _mot_b),
      f"y no se contamina con el patron de A -- veredicto {_v_b}, motivo {_mot_b[:60]}")

# --- Y la prueba de que el reseteo es lo que lo salva: SIN resetear ---
# Fresco de verdad (no una copia superficial de _mapeo_a, que compartiria el
# diccionario interno y corromperia las comprobaciones de arriba): se
# reconstruye desde cero, A y B en el MISMO diccionario, para simular
# exactamente lo que pasaria si retro_semaforo.py no reseteara entre clientes.
_mapeo_sin_resetear = {}
for f in [_fila_gasto("621000", doc_n=n) for n in range(1, 4)]:
    actualizar_mapeo_cuenta_gasto(_mapeo_sin_resetear, f)
for f in [_fila_gasto("600000", doc_n=n) for n in range(4, 7)]:
    actualizar_mapeo_cuenta_gasto(_mapeo_sin_resetear, f)
_v_mezcla, _mot_mezcla, _g_mezcla = evaluar_fila_v4(
    _fila_gasto("600000", doc_n=7), set(), {}, {}, {}, {}, 2020, None, 2026,
    mapeo_cuenta_gasto=_mapeo_sin_resetear)
# La propia factura de B (600000, coherente con SU patron) se juzga contra un
# historico contaminado con las de A -- el riesgo real no es que el guard se
# quede callado, es que puede acusar de "no coherente" a una factura que SI
# lo es dentro de su propio cliente, solo porque comparte codigo de cuenta
# con otro cliente que tiene un patron distinto. Con 3+3 empatados, gana el
# primero insertado (621000, de A) como "habitual", y la de B (600000) no
# coincide con esa habitual ajena -- FALLO, pero un FALLO que acusa a la
# factura equivocada por la razon equivocada.
check(_g_mezcla['cuenta_gasto_coherente'][0] == "FALLO"
      and "621000" in _g_mezcla['cuenta_gasto_coherente'][1],
      f"SIN resetear: una factura de B, coherente con el patron DE B, sale "
      f"FALLO por comparar contra el patron de A que comparte el mismo "
      f"codigo de cuenta (dio {_g_mezcla['cuenta_gasto_coherente']}) -- "
      f"el riesgo real que el reseteo por cliente evita no es silencio, es "
      f"acusar a la factura correcta")

print("\n=== importe_atipico: los dos defectos opuestos (27-08-2026) ===")
# Encontrados al comprobar las COSTURAS del arreglo de las caches: los cuatro
# guards ya pueden disparar, asi que por primera vez importaba COMO deciden.
# Los dos defectos llevaban ahi desde siempre, invisibles porque el guard
# estaba dormido (cache vacia) en las dos mediciones con corpus real.

# DEFECTO 1 (falso verde, el grave): un proveedor de CUOTA FIJA tiene desv=0,
# y la condicion previa `desv > 0` hacia que CUALQUIER importe diera OK.
_hist_fijo = {'B1': {'n_facturas_normales': 4, 'media': 121.00, 'desv': 0}}
_est, _det = guard_importe_atipico('P', 99999.00, _hist_fijo, nif='B1')
check(_est == "FALLO",
      f"cuota fija de 121,00 x4 y llega una de 99.999,00 (825x): FALLO, no un "
      f"OK afirmativo (dio {_est}: {_det})")
check(guard_importe_atipico('P', 1210.00, _hist_fijo, nif='B1')[0] == "FALLO",
      "misma cuota fija, un 10x tambien se detecta")
# ...pero sin volverse quisquilloso: una subida de precio normal NO es anomalia.
check(guard_importe_atipico('P', 121.50, _hist_fijo, nif='B1')[0] == "OK",
      "la misma cuota fija con una subida de 0,50 EUR sigue siendo OK: "
      "una actualizacion de precio no es una anomalia")

# DEFECTO 2 (ruido, el que habria envenenado la re-medicion): el umbral era
# 1 sigma, que no es un umbral de atipicidad -- marcaba FALLO el 40,8% de
# facturas legitimas (medido por simulacion antes de tocar nada).
_hist_var = {'B2': {'n_facturas_normales': 4, 'media': 121.00, 'desv': 2.07}}
check(guard_importe_atipico('P', 124.00, _hist_var, nif='B2')[0] == "OK",
      "una desviacion del 2,5% sobre un historico con variacion normal ya NO "
      "es FALLO (con 1 sigma lo era, y con ella ~40% de las facturas legitimas)")
check(guard_importe_atipico('P', 1210.00, _hist_var, nif='B2')[0] == "FALLO",
      "pero un 10x sobre ese mismo historico se sigue detectando: se ha "
      "quitado ruido, no capacidad de deteccion")

# CONTROL: el guard sigue sin pronunciarse cuando no tiene con que.
check(guard_importe_atipico('P', 500.0, {}, nif='B3')[0] == "NO_COMPROBADO",
      "sin historico sigue siendo NO_COMPROBADO, nunca un OK por omision")
check(guard_importe_atipico('P', 500.0,
      {'B4': {'n_facturas_normales': 4, 'media': 0, 'desv': 0}}, nif='B4')[0] == "NO_COMPROBADO",
      "con media 0 (sin escala con la que comparar) tampoco se finge un OK")

print(f"\n{'='*50}")
if FALLOS:
    print(f"❌ {len(FALLOS)} PRUEBA(S) FALLIDA(S): {FALLOS}")
    exit(1)
else:
    print("✅ TODAS LAS PRUEBAS PASAN")
