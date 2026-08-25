#!/usr/bin/env python3
"""diag_nif_otro_residual.py — los 48 "OTRO" del residuo de nif_digito_control
(ni NIE, ni UE, ni forma DNI/CIF): ?que forma tienen de verdad?

Hipotesis concreta a probar para longitud 8 (el grupo mas grande, 36 casos):
es UN CARACTER MENOS que cualquier formato espanol real (DNI/CIF/NIE son
siempre 9). Puede ser un DNI al que se le olvido teclear la letra de
control -- y si es asi, NO es un NIF invalido, es un NIF INCOMPLETO: el
mismo principio ya aplicado en el arreglo 10 a los campos de 1-2 caracteres
(SIN_DATO, no FALLO).

Se comprueba sin adivinar: si son 8 digitos (forma de "DNI sin letra"), se
CALCULA la letra que le correspondria (el algoritmo es determinista) y se
cuenta cuantos, con esa letra puesta, formarian un DNI de verdad valido --
sin que el valor completo se imprima nunca, solo el recuento de "si
encajaria" / "no encajaria".

Nunca se imprime un NIF real, completo ni parcial, en ningun momento.

Uso:
    python diag_nif_otro_residual.py "RUTA_DEL_CORPUS"
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
from nif_check import valida_nif

LETRAS_DNI = "TRWAGMYFPDXBNJZSQVHLCKE"
RE_NIE = re.compile(r'^[XYZ]\d{7}[A-Z]$')
RE_UE_GENERICO = re.compile(r'^[A-Z]{2}[0-9A-Z]{2,12}$')


def clasifica(nif_limpio):
    if RE_NIE.match(nif_limpio):
        return "NIE"
    if RE_UE_GENERICO.match(nif_limpio):
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

    forma_por_longitud = {}   # longitud -> Counter de forma (todo_digitos, letra+digitos, mixto)
    long8_encajaria_dni = 0
    long8_total = 0
    long10_forma = Counter()
    long7_forma = Counter()

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

                        ok, tipo, _ = valida_nif(nif)
                        if ok is not False or tipo != "DESCONOCIDO":
                            continue

                        limpio = nif.upper().replace(" ", "").replace("-", "").replace(".", "")
                        patron = clasifica(limpio)
                        if patron != "OTRO":
                            continue

                        L = len(limpio)
                        if L == 8:
                            long8_total += 1
                            if limpio.isdigit():
                                # Forma "DNI sin letra": se calcula la letra
                                # que le correspondería. Nunca se imprime el
                                # NIF completo, solo si ENCAJARIA.
                                letra_calc = LETRAS_DNI[int(limpio) % 23]
                                long8_encajaria_dni += 1
                            forma_por_longitud.setdefault(8, Counter())
                            if limpio.isdigit():
                                forma_por_longitud[8]["todo_digitos"] += 1
                            elif limpio[0].isalpha() and limpio[1:].isdigit():
                                forma_por_longitud[8]["letra+digitos"] += 1
                            else:
                                forma_por_longitud[8]["otra_mezcla"] += 1
                        elif L == 10:
                            if limpio.isdigit():
                                long10_forma["todo_digitos"] += 1
                            elif limpio[0].isalpha() and limpio[1:].isdigit():
                                long10_forma["letra+digitos"] += 1
                            elif limpio[:8].isdigit() and limpio[8:].isalpha():
                                long10_forma["8digitos+2letras"] += 1
                            else:
                                long10_forma["otra_mezcla"] += 1
                        elif L == 7:
                            if limpio.isdigit():
                                long7_forma["todo_digitos"] += 1
                            elif limpio[0].isalpha() and limpio[1:].isdigit():
                                long7_forma["letra+digitos"] += 1
                            else:
                                long7_forma["otra_mezcla"] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 66)
    print(f"  compras evaluadas: {n_compras:,}")
    print("=" * 66)
    print("")
    print(f"LONGITUD 8 (el grupo mayor) -- total: {long8_total:,}")
    if 8 in forma_por_longitud:
        for forma, n in forma_por_longitud[8].most_common():
            print(f"    {forma:<20} {n:,}")
    print(f"    de los que son TODO DIGITOS (forma 'DNI sin letra'): "
          f"{long8_encajaria_dni:,} -- a estos SI se les puede calcular")
    print(f"    la letra que faltaria (el algoritmo es determinista); "
          f"nunca impreso.")
    print("")
    print("LONGITUD 10 (un caracter de mas):")
    for forma, n in long10_forma.most_common():
        print(f"    {forma:<20} {n:,}")
    print("")
    print("LONGITUD 7 (dos caracteres de menos):")
    for forma, n in long7_forma.most_common():
        print(f"    {forma:<20} {n:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
