#!/usr/bin/env python3
"""
ORQUESTADOR — el eslabón que faltaba (Bloqueador 1, revision externa 28-07-2026).

Une, en un solo ejecutable, piezas que ya estaban construidas y probadas por
separado esta noche: leer_ascii_completo() (o dbfread para .dbf), 
construir_mapeo_cuenta_gasto(), y evaluar_fila_v4() en bucle sobre un CSV de
facturas ya capturadas (por vision, por OCR, o a mano).

NO lee fotos. Lee datos ya estructurados (CSV) y los valida. La captura sigue
siendo un problema aparte, sin resolver aqui (ver PENDIENTE_DE_FABRICACION.md).

Uso:
    python3 orquestador.py --config config.json --facturas facturas.csv \
        --diario cliente_2025_diario_ASCII_por_asientos.txt \
        --subcuentas cliente_2025_subcuentas_ASCII_por_asientos.txt \
        --salida veredicto.csv
"""
import argparse
import csv
import json
import os
import statistics
import sys
import time
from collections import defaultdict

from motor_veredicto import evaluar_fila_v4, cargar_cache_json


def cargar_config(path):
    if not os.path.exists(path):
        print(f"AVISO: no existe {path}, usando valores por defecto (nada persiste entre ejecuciones)")
        return {}
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def cargar_diario_y_subcuentas(path_diario, path_subcuentas):
    """Acepta .txt (ASCII ancho fijo) o .dbf (Xbase) indistintamente - detecta
    por extension. Devuelve (diario_recs, maestro_proveedores)."""
    ext_diario = os.path.splitext(path_diario)[1].lower()
    if ext_diario == '.txt':
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from layout_diario_contaplus import leer_ascii_completo
        diario_recs = leer_ascii_completo(path_diario)
    else:
        from dbfread import DBF
        diario_recs = list(DBF(path_diario, encoding='latin1'))

    maestro = {}
    if path_subcuentas:
        ext_sub = os.path.splitext(path_subcuentas)[1].lower()
        if ext_sub == '.dbf':
            from dbfread import DBF
            subcta_recs = list(DBF(path_subcuentas, encoding='latin1'))
            for r in subcta_recs:
                nif = (r.get('NIF') or '').strip()
                cod = r.get('COD', '')
                if nif and (cod.startswith('400') or cod.startswith('410')):
                    maestro[nif] = {'titulo': r.get('TITULO', '').strip(), 'cuenta': cod}
        else:
            print(f"AVISO: maestro de subcuentas en formato {ext_sub} no soportado directamente "
                  f"por este orquestador todavia - maestro_proveedores quedara vacio (NO_APLICA)")
    return diario_recs, maestro


def construir_historico_y_secuencia(filas_csv):
    tot, nums = defaultdict(list), defaultdict(list)
    for r in filas_csv:
        try:
            t = float(r.get('total_factura', 0) or 0)
        except ValueError:
            t = 0
        if t > 0:
            tot[r['proveedor']].append(t)
        nums[r['proveedor']].append(r.get('nº_documento', ''))
    hist = {p: {'n_facturas_normales': len(v), 'media': round(statistics.mean(v), 2),
                'desv': round(statistics.stdev(v), 2) if len(v) > 1 else 0}
            for p, v in tot.items()}
    secuencia = {p: {'numeros_vistos': n} for p, n in nums.items()}
    return hist, secuencia


def main():
    parser = argparse.ArgumentParser(description="Orquestador del motor de veredicto")
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--facturas', required=True, help='CSV de facturas ya capturadas')
    parser.add_argument('--diario', help='Diario (.txt ASCII o .dbf) para historico real')
    parser.add_argument('--subcuentas', help='Subcuentas (.dbf) para maestro real')
    parser.add_argument('--maestro-json', help='Maestro historico completo ya construido '
                         '(ej. cliente_proveedores_cuentas.json) - se fusiona con --subcuentas si se dan ambos. '
                         'IMPORTANTE: un export de subcuentas de un solo ejercicio solo trae cuentas ACTIVAS '
                         'ese año - proveedores antiguos/poco frecuentes (caso real anonimizado) no '
                         'aparecen ahi aunque sean historicos validos. Usar el maestro completo cuando exista.')
    # ANADIDO 19-08-2026 (auditoria externa verificada): antes se pasaba None
    # como nif_cliente_titular, asi que guard_sentido_compra_venta NUNCA podia
    # disparar su rama critica ("el emisor es el propio cliente: esto es una
    # venta, no un gasto") en ninguna ejecucion real del orquestador. El guard
    # solo se habia probado en el test unitario.
    parser.add_argument('--nif-titular', help='NIF del cliente titular de la tanda. '
                        'Sin el, guard_sentido_compra_venta no puede detectar que una '
                        'factura la emitio el propio cliente (venta) en vez de un '
                        'proveedor (gasto): se declara NO_COMPROBADO, nunca OK.')
    parser.add_argument('--salida', default='veredicto_salida.csv')
    parser.add_argument('--xdiario', help='Ruta del xDiario.txt importable a ContaPlus. '
                        'OPT-IN: solo se genera si se pide. Incluye unicamente las '
                        'facturas VERDE con cuenta de proveedor resuelta en el maestro; '
                        'las demas se quedan fuera y se cuentan, nunca se les inventa cuenta.')
    args = parser.parse_args()

    config = cargar_config(args.config)

    from motor_veredicto import construir_mapeo_cuenta_gasto
    mapeo_gasto = {}
    maestro = {}
    if args.diario:
        t0 = time.perf_counter()
        diario_recs, maestro = cargar_diario_y_subcuentas(args.diario, args.subcuentas)
        mapeo_gasto = construir_mapeo_cuenta_gasto(diario_recs)
        t1 = time.perf_counter()
        print(f"Histórico real cargado: {len(diario_recs)} asientos, "
              f"{len(maestro)} proveedores en maestro (solo activos del export), {len(mapeo_gasto)} cuentas de gasto "
              f"({(t1-t0)*1000:.0f} ms)")

    if args.maestro_json:
        maestro_historico = cargar_cache_json(args.maestro_json)
        # maestro_historico viene como NIF -> {titulo, cuenta} directamente (formato cliente_proveedores_cuentas.json)
        antes = len(maestro)
        maestro = {**maestro_historico, **maestro}  # el de subcuentas.dbf (mas reciente) prevalece si hay choque
        print(f"Maestro histórico fusionado: {antes} activos + {len(maestro_historico)} históricos = "
              f"{len(maestro)} proveedores totales")

    formato_cache = cargar_cache_json(config.get('cache_formato_documentos', ''))
    secuencia_persistida = cargar_cache_json(config.get('cache_secuencia_documental', ''))

    with open(args.facturas, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    print(f"Facturas a procesar: {len(filas)}")

    hist_importes, secuencia_calculada = construir_historico_y_secuencia(filas)
    secuencia_final = {**secuencia_calculada, **secuencia_persistida}

    alta_cliente_anio = config.get('alta_cliente_anio')
    ejercicio_tanda = config.get('ejercicio_tanda')

    vistos_duplicado = set()
    resultados = []
    conteo = defaultdict(int)
    for fila in filas:
        veredicto, motivo, guards = evaluar_fila_v4(
            fila, vistos_duplicado, hist_importes, formato_cache, secuencia_final,
            maestro, alta_cliente_anio, args.nif_titular, ejercicio_tanda, {},
            mapeo_cuenta_gasto=mapeo_gasto)
        conteo[veredicto] += 1
        fila_salida = dict(fila)
        fila_salida['VEREDICTO'] = veredicto
        fila_salida['MOTIVO'] = motivo
        # ANADIDO 20-08-2026 (auditoria de inventario). El maestro y el mapeo ya
        # se construian aqui y no se unian nunca a la fila, asi que el ultimo
        # tramo del objetivo del producto —el fichero importable a ContaPlus—
        # quedaba imposible de generar. Resolver la cuenta NO es inventarsela:
        # si no esta en el maestro/mapeo, la fila se queda sin cuenta y
        # escribir_xdiario la descarta a proposito.
        entrada_maestro = maestro.get((fila.get('nif') or '').strip())
        if entrada_maestro:
            cuenta_prov = entrada_maestro.get('cuenta')
            if cuenta_prov:
                fila_salida['cuenta_haber'] = cuenta_prov
                mg = mapeo_gasto.get(cuenta_prov)
                if mg and mg.get('cuenta_gasto'):
                    fila_salida['cuenta_debe'] = mg['cuenta_gasto']
        resultados.append(fila_salida)

    campos = list(resultados[0].keys()) if resultados else []
    with open(args.salida, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(resultados)

    print(f"\nVeredicto: {dict(conteo)}")
    print(f"Escrito: {args.salida}")

    # --- Ultimo tramo: el fichero que ContaPlus importa -------------------
    # OPT-IN a proposito (--xdiario). Genera un artefacto contable real, asi que
    # no se produce por defecto ni sin que alguien lo pida.
    if args.xdiario:
        from layout_diario_contaplus import escribir_xdiario
        verdes = [r for r in resultados if r['VEREDICTO'] == 'VERDE']
        exportables = [r for r in verdes if r.get('cuenta_haber')]
        sin_cuenta = len(verdes) - len(exportables)
        n_lineas, n_asientos = escribir_xdiario(exportables, args.xdiario)
        print(f"xDiario: {n_asientos} asientos, {n_lineas} lineas -> {args.xdiario}")
        if sin_cuenta:
            print(f"  {sin_cuenta} facturas VERDE quedaron FUERA por no tener cuenta "
                  f"de proveedor resuelta en el maestro. No se inventa ninguna cuenta.")
        if not args.diario:
            print("  AVISO: sin --diario no hay maestro ni mapeo, asi que casi nada "
                  "sera exportable. Es el comportamiento correcto, no un fallo.")

    ruta_cache_gasto = config.get('cache_cuenta_gasto')
    if ruta_cache_gasto and mapeo_gasto:
        os.makedirs(os.path.dirname(ruta_cache_gasto), exist_ok=True)
        with open(ruta_cache_gasto, 'w', encoding='utf-8') as f:
            json.dump(mapeo_gasto, f, ensure_ascii=False, indent=2)
        print(f"Cache de cuenta_gasto persistida en: {ruta_cache_gasto}")


if __name__ == "__main__":
    main()
