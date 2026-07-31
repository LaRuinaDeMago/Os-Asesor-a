"""
SUITE DE PRUEBAS DE REGRESION — motor_veredicto.py
Usa casos REALES ya verificados esta noche (clientes piloto, anonimizados), no datos inventados.
Objetivo: si alguien (Claude Code incluido) modifica el motor en el futuro, estas
pruebas fallan en el momento si se rompe algo que ya funcionaba - no se descubre
semanas despues con una factura real mal clasificada.

Ejecutar con: python3 -m pytest test_motor_veredicto.py -v
(o simplemente: python3 test_motor_veredicto.py  - corre sin pytest tambien)
"""

from motor_veredicto import (
    guard_aritmetica_base_tipo, guard_cuadre_total, guard_nif_digito_control,
    guard_suma_tramos, guard_retencion_vs_error, guard_signo_efectivo,
    guard_sentido_compra_venta, guard_estructura_reconocida,
    guard_secuencia_documental_proveedor, guard_importe_atipico,
    guard_nif_casa_historico, guard_cuenta_gasto_coherente,
    guard_tipo_producto_iva_semantico, guard_tipo_operacion_especial,
    evaluar_fila_v4, calcular_veredicto_v4,
    construir_mapeo_cuenta_gasto, aprender_cuenta_gasto, reevaluar_tras_correccion,
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

print("\n=== Nivel 4: retencion_vs_error (caso real anonimizado) ===")
# base 661.15, iva 138.84, irpf -125.62, total 674.37 -> retencion 19%
r = guard_retencion_vs_error(661.15, 138.84, -125.62, 674.37)
check(r[0] == "OK", f"Caso piloto retencion 19% reconocida ({r[1]})")

print("\n=== Nivel 4: signo_efectivo (casos reales de proveedor piloto, abonos) ===")
check(guard_signo_efectivo("A010000531", "", -18.90, -22.87, "ABONO")[0] == "OK", "Abono proveedor piloto coherente")
check(guard_signo_efectivo("11501", "", 202.67, 240.80, None)[0] == "NO_APLICA",
      "Caso piloto 11501 NO marca FALLO (regresion del falso positivo ya corregido)")

print("\n=== Nivel PGC: cuenta_gasto (caso real anonimizado) ===")
mapeo_test = {"410014": {"cuenta_gasto": "621000", "grupo_pgc": "Arrendamientos y cánones", "confianza": "ALTA"}}
check(guard_cuenta_gasto_coherente("410014", mapeo_test)[0] == "OK", "Proveedor piloto -> 621000")
check(guard_cuenta_gasto_coherente("999999", mapeo_test)[0] == "NO_APLICA", "Proveedor nuevo -> NO_APLICA")

print("\n=== Aprendizaje: ciclo NO_APLICA -> decision asesor -> persistencia ===")
mapeo2 = {}
antes = guard_cuenta_gasto_coherente("410099", mapeo2)
mapeo2 = aprender_cuenta_gasto(mapeo2, "410099", "625000")
despues = guard_cuenta_gasto_coherente("410099", mapeo2)
check(antes[0] == "NO_APLICA" and despues[0] == "OK", "Ciclo de aprendizaje completo")

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

print("\n=== tipo_operacion_especial (guard nuevo, casos SINTETICOS - sin caso real todavia) ===")
check(guard_tipo_operacion_especial('Fra C.382', '600000', '12345678Z')[0] == "NO_APLICA",
      "compra normal real (caso piloto) -> NO_APLICA, sin falso positivo")
check(guard_tipo_operacion_especial('Compra furgoneta', '218000', 'B12345678')[0] == "AMBAR",
      "cuenta de inmovilizado (218000) -> AMBAR")
check(guard_tipo_operacion_especial('Amortizacion anual furgoneta', '600000', 'B12345678')[0] == "AMBAR",
      "palabra 'amortizacion' en concepto -> AMBAR")
check(guard_tipo_operacion_especial('Fra compra material', '600000', 'DE123456789')[0] == "AMBAR",
      "NIF con prefijo de pais (DE) -> AMBAR, posible intracomunitario")

print(f"\n{'='*50}")
if FALLOS:
    print(f"❌ {len(FALLOS)} PRUEBA(S) FALLIDA(S): {FALLOS}")
    exit(1)
else:
    print("✅ TODAS LAS PRUEBAS PASAN")
