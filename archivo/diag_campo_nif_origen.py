#!/usr/bin/env python3
"""diag_campo_nif_origen.py — el NIF de 1 caracter, ¿de que LINEA sale?

reconstruir_compra() toma `nif = next((l[4] for l in lineas if l[4]), "")` --
el primer TERNIF no vacio entre TODAS las lineas del asiento, en el orden en
que ContaPlus las escribio (tipicamente gasto primero, acreedor al final).
Si una linea de GASTO lleva basura de 1 caracter en TERNIF (un campo que solo
tiene sentido para la contraparte real), esa basura gana por orden de lectura
aunque la linea de ACREEDOR tenga el NIF bueno.

Este script NO cambia nada: para cada asiento de compra donde el NIF elegido
hoy tiene longitud 1, mira SOLO la longitud del TERNIF de la(s) linea(s) de
acreedor de ese mismo asiento (nunca el valor). Si esas lineas tienen una
longitud plausible (8-9, DNI/CIF; o mas, UE), confirma que el reconstructor
esta mirando la linea equivocada.

Nunca imprime un NIF real -- solo longitudes y cuentas.

Uso:
    python diag_campo_nif_origen.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import (parse_cabecera, num, txt, cuenta, numero_documento,
                             reconstruir_compra, CTAS_ACREEDOR, CTA_IVA_SOPORTADO)
import contrato_datos


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
    n_nif_longitud_1 = 0

    long_en_acreedor = Counter()     # longitud del TERNIF en lineas de acreedor, cuando fila['nif'] tiene longitud 1
    n_acreedor_vacio_tambien = 0
    long_en_iva = Counter()

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
                        nif_elegido = fila.get("nif", "") or ""
                        if len(nif_elegido) != 1:
                            continue
                        n_nif_longitud_1 += 1

                        lineas_acree = [l for l in lineas if l[0] in CTAS_ACREEDOR]
                        lineas_iva = [l for l in lineas if l[0] == CTA_IVA_SOPORTADO]
                        mejor_acree = max((len(l[4]) for l in lineas_acree if l[4]), default=0)
                        mejor_iva = max((len(l[4]) for l in lineas_iva if l[4]), default=0)
                        if mejor_acree == 0:
                            n_acreedor_vacio_tambien += 1
                        else:
                            long_en_acreedor[mejor_acree] += 1
                        if mejor_iva:
                            long_en_iva[mejor_iva] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 70)
    print(f"  compras evaluadas: {n_compras:,}")
    print(f"  con NIF elegido de longitud 1: {n_nif_longitud_1:,}")
    print("=" * 70)
    print("")
    print("De esos, longitud del TERNIF en la(s) linea(s) de ACREEDOR"
          " del MISMO asiento:")
    for long_, n in long_en_acreedor.most_common():
        print(f"    longitud {long_:>3}: {n:,}")
    print(f"    (el acreedor TAMBIEN esta vacio en estos): {n_acreedor_vacio_tambien:,}")
    print("")
    print("De esos, longitud del TERNIF en la(s) linea(s) de IVA soportado (472):")
    for long_, n in long_en_iva.most_common():
        print(f"    longitud {long_:>3}: {n:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
