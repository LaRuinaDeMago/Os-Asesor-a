#!/usr/bin/env python3
"""diag_nif.py — cuanto del FALLO de nif_digito_control es NIE o NIF-IVA UE
mal cubiertos por nif_check.py, no un NIF realmente invalido.

HIPOTESIS (25-08-2026, revision de RUN 9 tras el arreglo 9): nif_check.py
-- el validador que de verdad usa guard_nif_digito_control, via
`from nif_check import valida_nif` en motor_veredicto.py -- solo reconoce dos
formatos: DNI (8 digitos + letra) y CIF (letra + 7 digitos + control). Un NIE
(X/Y/Z + 7 digitos + letra, el NIF de un extranjero residente) tiene la MISMA
forma estructural que el patron CIF (`nif[0].isalpha() and nif[1:8].isdigit()`
es cierto para "X1234567L" igual que para un CIF real), asi que un NIE NO cae
en "formato no reconocido": cae en la rama CIF y se valida con el algoritmo
DE CIF, que no es el suyo. Un NIF-IVA extranjero (proveedor intracomunitario,
prefijo de pais + alfanumerico) no tiene ninguna rama: siempre "DESCONOCIDO".

Existe una SEGUNDA implementacion en el repo, triangulacion_identidad_v0.py
(un prototipo de triangulacion de identidad, no conectado al motor), que SI
reconoce NIE con el algoritmo correcto (sustituir X/Y/Z por 0/1/2 y aplicar
el mismo modulo 23 que el DNI) y NIF-IVA UE por formato. Este script usa esa
implementacion como REFERENCIA para medir cuanto explica, sin cambiar nada
todavia.

Solo cuenta y clasifica por PATRON ESTRUCTURAL (longitud, si empieza por
X/Y/Z, si encaja con un prefijo de pais UE). Nunca imprime un NIF real.

Uso:
    python diag_nif.py "RUTA_DEL_CORPUS"
"""
import os
import re
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta, numero_documento, reconstruir_compra
import contrato_datos
from nif_check import valida_nif as valida_nif_actual
from triangulacion_identidad_v0 import valida_nif as valida_nif_candidato

RE_NIE = re.compile(r'^[XYZ]\d{7}[A-Z]$')
RE_UE = re.compile(r'^(DE|FR|IT|PT|NL|BE|PL|IE|AT|SE|DK|FI|EL|CZ|RO|HU|BG|HR|SK|SI|LT|LV|EE|LU|MT|CY|GB|CH)[0-9A-Z]{2,12}$')
RE_UE_GENERICO = re.compile(r'^[A-Z]{2}[0-9A-Z]{2,12}$')  # cualquier prefijo de 2 letras, sin lista cerrada


def clasifica(nif_limpio):
    if RE_NIE.match(nif_limpio):
        return "NIE"
    if RE_UE.match(nif_limpio):
        return "NIF_IVA_UE"
    if len(nif_limpio) == 9 and nif_limpio[:8].isdigit() and nif_limpio[8:9].isalpha():
        return "DNI_forma"
    if len(nif_limpio) == 9 and nif_limpio[0:1].isalpha() and nif_limpio[1:8].isdigit():
        return "CIF_forma"
    return "OTRO"


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

    fallo_actual_por_patron = Counter()
    candidato_ok_por_patron = Counter()
    longitudes_otro = Counter()
    genericos_por_longitud = Counter()

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
                        nif = fila.get("nif", "") or ""
                        if not nif:
                            continue
                        limpio = nif.upper().replace(" ", "").replace("-", "").replace(".", "")

                        ok_actual, _, _ = valida_nif_actual(nif)
                        if ok_actual is not False:
                            continue  # solo nos interesa el FALLO actual (ok_actual == False)

                        patron = clasifica(limpio)
                        fallo_actual_por_patron[patron] += 1
                        if patron == "OTRO":
                            longitudes_otro[len(limpio)] += 1
                            if RE_UE_GENERICO.match(limpio):
                                genericos_por_longitud[len(limpio)] += 1

                        ok_cand, tipo_cand, _ = valida_nif_candidato(nif)
                        if ok_cand is True:
                            candidato_ok_por_patron[patron] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 74)
    print(f"  compras evaluadas: {n_compras:,}")
    total_fallo = sum(fallo_actual_por_patron.values())
    print(f"  nif_digito_control=FALLO con el validador ACTUAL (nif_check.py): {total_fallo:,}")
    print("=" * 74)
    print("")
    print(f"  {'patron':<14} {'FALLO hoy':>10}  {'candidato dice OK':>18}")
    for patron, n in fallo_actual_por_patron.most_common():
        ok_c = candidato_ok_por_patron.get(patron, 0)
        print(f"  {patron:<14} {n:>10,}  {ok_c:>18,}")

    explicado = candidato_ok_por_patron.get("NIE", 0) + candidato_ok_por_patron.get("NIF_IVA_UE", 0)
    print("")
    print(f"  >> Explicado por NIE + NIF-IVA UE (candidato dice OK): {explicado:,} "
          f"/ {total_fallo:,} ({round(explicado*100.0/total_fallo,2) if total_fallo else 0}%)")

    if longitudes_otro:
        print("")
        print("  longitudes de los 'OTRO' (ni NIE ni UE ni forma DNI/CIF) -- para ver")
        print("  si son basura o un patron mas por identificar:")
        for long_, n in longitudes_otro.most_common(10):
            print(f"    longitud {long_:>3}: {n:,}")

    print("")
    print("  de los 'OTRO', cuantos encajan con 2 LETRAS + alfanumerico")
    print("  (prefijo de pais generico, sin lista cerrada) por longitud:")
    for long_, n in genericos_por_longitud.most_common(10):
        print(f"    longitud {long_:>3}: {n:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
