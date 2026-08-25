#!/usr/bin/env python3
"""diag_campos_criticos.py — por que casi todo sale NO_COMPROBADO.

99,9% de aritmetica_base_tipo/cuadre_total/suma_tramos salen NO_COMPROBADO
sobre el corpus real deduplicado. Leido el codigo: eso pasa cuando
`datos_integros` es False, que a su vez exige los seis CAMPOS_CRITICOS de
contrato_datos.py: nif, fecha_expedicion, nº_documento, base_total, iva_total,
total_factura.

Este script reutiliza reconstruir_compra() (la funcion REAL de
retro_semaforo.py) y mide, por cada asiento con patron de compra ya
deduplicado, cuales de esos seis campos quedan poblados. Solo cuenta
presente/ausente. Nunca lee ni imprime un valor.

Uso:
    python diag_campos_criticos.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import (parse_cabecera, num, txt, cuenta,
                            reconstruir_compra, numero_documento)

CRITICOS = ('nif', 'fecha_expedicion', 'nº_documento',
            'base_total', 'iva_total', 'total_factura')


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
    n_compras = 0
    presente = Counter()
    combinaciones_ausentes = Counter()
    todos_presentes = 0
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

                    for _, lineas in grupos.items():
                        huella = hashlib.blake2b(
                            b"".join(sorted(l[9] for l in lineas)),
                            digest_size=16).digest()
                        if huella in vistos_contenido:
                            continue
                        vistos_contenido.add(huella)

                        fila = reconstruir_compra(lineas)
                        if fila is None or fila in ("SIN_IVA", "ISP"):
                            continue
                        n_compras += 1
                        ausentes = []
                        for campo in CRITICOS:
                            if fila.get(campo) not in (None, ""):
                                presente[campo] += 1
                            else:
                                ausentes.append(campo)
                        if not ausentes:
                            todos_presentes += 1
                        else:
                            combinaciones_ausentes["+".join(ausentes)] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 66)
    print(f"  Asientos de compra (deduplicados): {n_compras:,}")
    print("=" * 66)
    print("")
    print("PRESENCIA DE CADA CAMPO CRITICO:")
    for c in CRITICOS:
        n = presente.get(c, 0)
        pct = round(n / n_compras * 100, 2) if n_compras else 0
        print(f"   {c:<18} {n:>8,} / {n_compras:,}   ({pct}%)")
    print("")
    print(f"CON LOS SEIS PRESENTES (datos_integros=OK esperado): {todos_presentes:,}"
          f"  ({round(todos_presentes/n_compras*100,2) if n_compras else 0}%)")
    print("")
    print("COMBINACIONES DE CAMPOS AUSENTES MAS FRECUENTES:")
    for combo, n in combinaciones_ausentes.most_common(10):
        print(f"   {n:>8,}   falta: {combo}")
    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
