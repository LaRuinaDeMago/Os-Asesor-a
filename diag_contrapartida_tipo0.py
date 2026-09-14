#!/usr/bin/env python3
"""diag_contrapartida_tipo0.py -- ¿que cuenta hay al OTRO lado del asiento
cuando una linea 477/472 no trae tipo de IVA (tipo "0")?

DE DONDE SALE ESTA PREGUNTA
-----------------------------
`diag_patron_cierre_iva.py` (14-09-2026) midio, sobre 303_LOCAL.json, que el
"tipo 0" que aparece en casi toda ficha de `cuadre_303_ficha.py` cancela casi
exacto (91,3% de las celdas con ratio entre 0,999 y 1,001, mediana 1,0000) el
resto del lado -- eso descarta que sea ruido, pero no dice QUE es. La
hipotesis: es el asiento de liquidacion/cierre trimestral de IVA (el que
traspasa el saldo de 477/472 a la cuenta de Hacienda al presentar el 303),
que toca la misma cuenta que una venta o compra real pero no es una.

Esta pregunta no se puede contestar desde 303_LOCAL.json (ya esta agregado
por tipo, la cuenta contrapartida no viaja ahi). Hace falta volver al
Diario.dbf y mirar, para cada asiento con una linea 477/472 sin tipo de IVA,
que cuenta hay en las OTRAS lineas del mismo asiento.

COMO SE MIDE, SIN VER NINGUN NOMBRE NI IMPORTE DE UN CLIENTE CONCRETO
-------------------------------------------------------------------
Solo se cuenta el PREFIJO de la cuenta contrapartida (4 digitos: son grupos
del Plan General Contable -- 4750, 4700, 5720... -- nunca la subcuenta
completa, que podria distinguir a un tercero concreto dentro del grupo).
Y si el importe de esa contrapartida coincide, en valor absoluto, con la
cuota de la linea "tipo 0" -- lo que se espera de un traspaso contable
limpio (lo que sale de un lado entra entero en el otro).

Uso:
    python diag_contrapartida_tipo0.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import MAX_REGISTROS_POR_FICHERO, parse_cabecera, num, txt

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PREF_REPERCUTIDO = "477"
PREF_SOPORTADO = "472"
TOL_IMPORTE = 0.02  # 2 centimos, margen de redondeo


def cuenta_prefijo(rec, c, n=4):
    return txt(rec, c)[:n]


def analizar_contenedor(ruta, contador_prefijos, stats, vistos_contenido):
    with zipfile.ZipFile(ruta) as z:
        nombre = next((i.filename for i in z.infolist()
                       if not i.is_dir()
                       and os.path.basename(i.filename).lower() == "diario.dbf"), None)
        if nombre is None:
            return
        with z.open(nombre) as fh:
            len_reg, campos = parse_cabecera(fh)
            idx = {c["nombre"]: c for c in campos}
            cS, cED, cEH = idx.get("SUBCTA"), idx.get("EURODEBE"), idx.get("EUROHABER")
            cIVA, cA = idx.get("IVA"), idx.get("ASIEN")
            if not (cS and cA):
                return

            lineas_por_asiento = {}
            leidos_aqui = 0
            while True:
                rec = fh.read(len_reg)
                if len(rec) < len_reg or rec[:1] == b"\x1a":
                    break
                leidos_aqui += 1
                if leidos_aqui > MAX_REGISTROS_POR_FICHERO:
                    raise ValueError("demasiados registros: fichero corrupto")
                if rec[:1] == b"*":
                    continue
                asien = int(num(rec, cA))
                lineas_por_asiento.setdefault(asien, []).append(rec)

            for _asien, lineas in lineas_por_asiento.items():
                huella = hashlib_blake2b_lineas(lineas)
                if huella in vistos_contenido:
                    continue
                vistos_contenido.add(huella)

                for i, rec in enumerate(lineas):
                    pref3 = txt(rec, cS)[:3]
                    if pref3 not in (PREF_REPERCUTIDO, PREF_SOPORTADO):
                        continue
                    tipo_iva = num(rec, cIVA) if cIVA else 0.0
                    if tipo_iva != 0.0:
                        continue
                    debe, haber = num(rec, cED), num(rec, cEH)
                    cuota_linea = haber - debe if pref3 == PREF_REPERCUTIDO else debe - haber
                    if cuota_linea == 0.0:
                        continue

                    stats["asientos_tipo0_examinados"] += 1
                    if len(lineas) == 1:
                        stats["asientos_de_una_sola_linea"] += 1
                        continue

                    for j, otra in enumerate(lineas):
                        if j == i:
                            continue
                        pref_otra = cuenta_prefijo(otra, cS)
                        if not pref_otra:
                            continue
                        contador_prefijos[pref_otra] += 1
                        debe_o, haber_o = num(otra, cED), num(otra, cEH)
                        importe_otra = max(debe_o, haber_o)
                        if abs(importe_otra - abs(cuota_linea)) <= TOL_IMPORTE:
                            stats["contrapartida_importe_coincide"] += 1
                        stats["contrapartidas_totales"] += 1


def hashlib_blake2b_lineas(lineas):
    import hashlib
    return hashlib.blake2b(b"".join(sorted(lineas)), digest_size=16).digest()


def main():
    raiz = os.path.abspath(sys.argv[1])
    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")
    print(f"{len(dats):,} contenedores encontrados.")

    contador_prefijos = Counter()
    stats = Counter()
    vistos_contenido = set()
    incidencias = Counter()

    for i, ruta in enumerate(dats, 1):
        try:
            if not zipfile.is_zipfile(ruta):
                incidencias["no es contenedor"] += 1
                continue
            analizar_contenedor(ruta, contador_prefijos, stats, vistos_contenido)
        except Exception as e:
            incidencias["contenedor:" + type(e).__name__] += 1
        if i % 200 == 0:
            print(f"  ... {i:,}/{len(dats):,} contenedores")

    print()
    print("=" * 68)
    print("CONTRAPARTIDA DE LAS LINEAS 477/472 SIN TIPO DE IVA -- solo recuentos")
    print("=" * 68)
    print(f"  asientos con una linea 477/472 de tipo '0' (deduplicados): "
          f"{stats['asientos_tipo0_examinados']:,}")
    print(f"    de una sola linea (sin contrapartida que mirar): "
          f"{stats['asientos_de_una_sola_linea']:,}")
    print()
    print("PREFIJOS DE CUENTA (4 digitos, grupo del Plan General Contable) "
          "vistos como contrapartida:")
    for pref, n in contador_prefijos.most_common(20):
        print(f"    {pref:<6} {n:>6,} veces")
    print()
    total_contra = stats["contrapartidas_totales"]
    coincide = stats["contrapartida_importe_coincide"]
    if total_contra:
        print(f"  contrapartidas cuyo importe coincide (±2 centimos) con la "
              f"cuota de la linea tipo '0': {coincide:,} de {total_contra:,} "
              f"({100*coincide/total_contra:.1f}%)")
    if incidencias:
        print()
        print("INCIDENCIAS (por tipo, nunca por mensaje):")
        for k, c in incidencias.most_common():
            print(f"    {k:<40} {c:>6,}")

    print()
    print("COMO SE LEE:")
    print("  - Si un prefijo como 4750/4700/4709 (Hacienda Publica, IVA)")
    print("    domina, y el importe coincide casi siempre -> confirma que es")
    print("    el asiento de liquidacion/cierre trimestral, no una venta o")
    print("    compra real. Se puede excluir con seguridad de la reconstruccion.")
    print("  - Si los prefijos estan repartidos entre cuentas de proveedores")
    print("    o clientes normales (400-43x) -> la hipotesis no es tan simple,")
    print("    y hace falta mirar caso a caso antes de excluir nada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
