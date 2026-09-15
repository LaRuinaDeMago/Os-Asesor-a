#!/usr/bin/env python3
"""diag_retencion.py — ¿cuadre_total=FALLO es en realidad retencion sin capturar?

HIPOTESIS (25-08-2026, revision de RUN 8): reconstruir_compra() solo mira tres
cuentas (gasto 6xx, IVA soportado 472, acreedor 400/401/410/411). Una compra
con retencion de IRPF (servicios profesionales, alquileres...) tiene una CUARTA
pata en el asiento -- la cuenta de Hacienda acreedora por la retencion
practicada-- que hoy no se recoge. Sin ella, irpf_retencion nunca se rellena,
"irpf or 0.0" cae siempre a 0.0, y guard_cuadre_total exige base+iva=total
en facturas donde eso NUNCA fue cierto: el total pagado es neto de retencion
por diseño de la factura, no por un error del proveedor.

Este script NO reimplementa el guard: importa guard_cuadre_total y
guard_retencion_vs_error tal cual. Para cada compra donde cuadre_total
fallaria hoy (con irpf=0.0, que es el comportamiento real de retro_semaforo),
mira que OTRAS cuentas aparecen en el mismo asiento aparte de gasto/iva/
acreedor, y si la cuenta candidata (prefijo 475) explica la diferencia.

Solo cuenta PREFIJOS de cuenta (3 digitos del PGC) y sumas agregadas -- nunca
un NIF, un nombre, ni el importe de una factura suelta.

Uso:
    python diag_retencion.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import (parse_cabecera, num, txt, cuenta, numero_documento,
                             reconstruir_compra, PREF_GASTO, CTA_IVA_SOPORTADO, CTAS_ACREEDOR)
import motor_veredicto as mv
import contrato_datos

TOL = 0.02


def main():
    raiz = os.path.abspath(sys.argv[1])
    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores.")

    vistos_contenido = set()
    vistos_clave_documental = set()
    n_compras = 0
    n_cuadre_fallo = 0

    prefijos_extra = Counter()          # prefijo de cuenta -> en cuantos asientos-FALLO aparece
    con_475 = 0
    con_475_y_explica = 0               # la suma de esa(s) linea(s) SI explica la diferencia
    desvio_tras_475 = []                # |diferencia - suma_475| cuando hay 475 (para ver si son centimos)

    # SEGUNDA HIPOTESIS (25-08-2026): 477 aparece en el 29% de los FALLO. En el
    # PGC estandar 477 es "Hacienda Publica, IVA repercutido" -- ventas, no
    # compras. Si aparece dentro de un asiento clasificado como compra, el
    # asiento puede estar MEZCLANDO una venta con la compra bajo el mismo
    # numero de asiento (asiento por lotes), contaminando total_factura. Se
    # comprueba con el mismo rigor que 475: prueba DEBE y HABER por separado,
    # y se mide el solape con 475 (no se puede asumir que sean conjuntos
    # disjuntos sin comprobarlo).
    con_477 = 0
    con_477_y_explica_haber = 0
    con_477_y_explica_debe = 0
    desvio_tras_477_haber = []
    desvio_tras_477_debe = []
    con_475_y_477 = 0
    con_477_sin_475 = 0
    con_477_sin_475_y_explica = 0

    errores = Counter()

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                nombre = next((i.filename for i in z.infolist()
                               if not i.is_dir()
                               and os.path.basename(i.filename).lower() == "diario.dbf"), None)
                if nombre is None:
                    continue
                with z.open(nombre) as fh:
                    len_reg, campos = parse_cabecera(fh)
                    idx = {c["nombre"]: c for c in campos}
                    cA, cS = idx.get("ASIEN"), idx.get("SUBCTA")
                    cED, cEH = idx.get("EURODEBE"), idx.get("EUROHABER")
                    cIVA, cNIF = idx.get("IVA"), idx.get("TERNIF")
                    cREC = idx.get("RECEQUIV")
                    cBASE, cFEC = idx.get("BASEIMPO"), idx.get("FECHA")
                    cNFACTICK = idx.get("NFACTICK")
                    cDOCUMENTO = idx.get("DOCUMENTO")
                    cFACTURA = idx.get("FACTURA")
                    if not (cA and cS):
                        continue

                    grupos = {}
                    while True:
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        h_linea = hashlib.blake2b(rec, digest_size=8).digest()
                        grupos.setdefault(int(num(rec, cA)), []).append((
                            cuenta(rec, cS), num(rec, cED), num(rec, cEH),
                            num(rec, cIVA), txt(rec, cNIF), num(rec, cBASE),
                            txt(rec, cFEC),
                            numero_documento(rec, cNFACTICK, cDOCUMENTO, cFACTURA),
                            num(rec, cREC),
                            h_linea,
                        ))
                        del rec

                    for _, lineas in sorted(grupos.items()):
                        huella = hashlib.blake2b(
                            b"".join(sorted(l[9] for l in lineas)),
                            digest_size=16).digest()
                        if huella in vistos_contenido:
                            continue
                        vistos_contenido.add(huella)

                        fila = reconstruir_compra(lineas)
                        if fila is None or fila in ("SIN_IVA", "ISP"):
                            continue

                        clave_doc = contrato_datos.canonizar(fila).clave_documental()
                        clave_h = hashlib.blake2b(
                            repr(clave_doc).encode("utf-8"), digest_size=12).digest()
                        if clave_h in vistos_clave_documental:
                            continue
                        vistos_clave_documental.add(clave_h)

                        n_compras += 1
                        base_total = fila.get("base_total", 0.0) or 0.0
                        iva_total = fila.get("iva_total", 0.0) or 0.0
                        recargo = fila.get("recargo_equivalencia", 0.0) or 0.0
                        total = fila.get("total_factura", 0.0) or 0.0

                        irpf_real = fila.get("irpf_retencion") or 0.0
                        estado, _ = mv.guard_cuadre_total(base_total, 0.0, 0.0, iva_total, irpf_real, total, recargo)
                        if estado != "FALLO":
                            continue
                        n_cuadre_fallo += 1

                        diferencia = round(base_total + iva_total + recargo - total, 2)

                        # Cuentas de esta linea que NO son gasto/iva/acreedor.
                        otras = [l for l in lineas
                                 if not l[0].startswith(PREF_GASTO)
                                 and l[0] != CTA_IVA_SOPORTADO
                                 and l[0] not in CTAS_ACREEDOR]
                        vistos_prefijo_este_asiento = set()
                        for l in otras:
                            pref = l[0][:3]
                            if pref and pref not in vistos_prefijo_este_asiento:
                                prefijos_extra[pref] += 1
                                vistos_prefijo_este_asiento.add(pref)

                        lineas_475 = [l for l in otras if l[0].startswith("475")]
                        tiene_475 = bool(lineas_475)
                        if lineas_475:
                            con_475 += 1
                            suma_475 = round(sum(l[2] for l in lineas_475), 2)  # HABER
                            desvio = round(abs(diferencia - suma_475), 2)
                            desvio_tras_475.append(desvio)
                            if desvio < TOL:
                                con_475_y_explica += 1

                        lineas_477 = [l for l in otras if l[0].startswith("477")]
                        if lineas_477:
                            con_477 += 1
                            if tiene_475:
                                con_475_y_477 += 1
                            else:
                                con_477_sin_475 += 1
                            suma_477_haber = round(sum(l[2] for l in lineas_477), 2)
                            suma_477_debe = round(sum(l[1] for l in lineas_477), 2)
                            dh = round(abs(diferencia - suma_477_haber), 2)
                            dd = round(abs(diferencia - suma_477_debe), 2)
                            desvio_tras_477_haber.append(dh)
                            desvio_tras_477_debe.append(dd)
                            if dh < TOL:
                                con_477_y_explica_haber += 1
                            if dd < TOL:
                                con_477_y_explica_debe += 1
                            if not tiene_475 and (dh < TOL or dd < TOL):
                                con_477_sin_475_y_explica += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 70)
    print(f"  compras evaluadas: {n_compras:,}")
    print(f"  cuadre_total=FALLO (con irpf=0.0, comportamiento real hoy): {n_cuadre_fallo:,}")
    print("=" * 70)
    print("")
    print("PREFIJOS DE CUENTA (3 digitos PGC) presentes en esos asientos,")
    print("aparte de gasto/IVA soportado/acreedor -- top 15:")
    for pref, n in prefijos_extra.most_common(15):
        print(f"    {pref:<6} {n:>8,}  ({round(n*100.0/n_cuadre_fallo,2) if n_cuadre_fallo else 0}% de los FALLO)")
    print("")
    print(f"  asientos FALLO con alguna linea 475xxx : {con_475:,} "
          f"({round(con_475*100.0/n_cuadre_fallo,2) if n_cuadre_fallo else 0}%)")
    print(f"  de esos, la(s) linea(s) 475 EXPLICAN la diferencia"
          f" (|diferencia-suma475|<0.02) : {con_475_y_explica:,} "
          f"({round(con_475_y_explica*100.0/con_475,2) if con_475 else 0}%)")
    if desvio_tras_475:
        ordenado = sorted(desvio_tras_475)
        mediana = ordenado[len(ordenado)//2]
        print(f"  desvio mediano tras restar 475 (de los que SI tienen 475): {mediana}")

    print("")
    print(f"  asientos FALLO con alguna linea 477xxx : {con_477:,} "
          f"({round(con_477*100.0/n_cuadre_fallo,2) if n_cuadre_fallo else 0}%)")
    print(f"    de esos, tambien tienen 475           : {con_475_y_477:,}")
    print(f"    de esos, 477 SIN 475                  : {con_477_sin_475:,}")
    print(f"  477 explica la diferencia por el HABER (|dif-suma_haber477|<0.02): "
          f"{con_477_y_explica_haber:,} ({round(con_477_y_explica_haber*100.0/con_477,2) if con_477 else 0}%)")
    print(f"  477 explica la diferencia por el DEBE   (|dif-suma_debe477|<0.02): "
          f"{con_477_y_explica_debe:,} ({round(con_477_y_explica_debe*100.0/con_477,2) if con_477 else 0}%)")
    if desvio_tras_477_haber:
        oh = sorted(desvio_tras_477_haber)
        od = sorted(desvio_tras_477_debe)
        print(f"  desvio mediano 477 por HABER: {oh[len(oh)//2]}   por DEBE: {od[len(od)//2]}")
    print(f"  de los 477 SIN 475, cuantos quedan explicados solo por 477: "
          f"{con_477_sin_475_y_explica:,} / {con_477_sin_475:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
