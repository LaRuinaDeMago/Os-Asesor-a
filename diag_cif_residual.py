#!/usr/bin/env python3
"""diag_cif_residual.py — los 46 CIF con forma valida que fallan el digito
de control: ?son errores reales de tecleo historico, o un problema de
limpieza en nif_check.py?

Hipotesis a descartar ANTES de aceptar "son errores reales": si el NIF
crudo (antes de .upper()/.replace()) trae algo que la limpieza actual no
quita -- un caracter invisible, un espacio no estandar, una coma en vez de
un punto -- podria hacer que un CIF genuinamente valido parezca invalido.

Solo mide LONGITUDES y estructura (isalpha/isdigit por posicion), nunca
imprime el NIF crudo ni limpio. Reutiliza valida_nif() real, no reimplementa
el checksum.

Uso:
    python diag_cif_residual.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta, numero_documento, reconstruir_compra
import contrato_datos
from nif_check import valida_nif


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

    n_cif_fallo = 0
    longitud_cruda = Counter()          # longitud del NIF TAL COMO llega de fila['nif']
    tiene_espacio_extra = 0
    tiene_caracter_no_ascii = 0
    primera_letra_organizacion = Counter()   # letra de organizacion del CIF (A/B/P/S/...)
    ultimo_caracter_es_letra = Counter()     # el digito de control: letra vs numero

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
                        if not (ok is False and tipo == "CIF"):
                            continue
                        n_cif_fallo += 1

                        longitud_cruda[len(nif)] += 1
                        if nif != nif.strip():
                            tiene_espacio_extra += 1
                        if not all(ord(c) < 128 for c in nif):
                            tiene_caracter_no_ascii += 1

                        limpio = nif.upper().replace(" ", "").replace("-", "").replace(".", "")
                        if len(limpio) == 9:
                            primera_letra_organizacion[limpio[0]] += 1
                            ultimo_caracter_es_letra["letra" if limpio[8].isalpha() else "digito"] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 66)
    print(f"  compras evaluadas: {n_compras:,}")
    print(f"  nif_digito_control=FALLO tipo CIF: {n_cif_fallo:,}")
    print("=" * 66)
    print("")
    print("LONGITUD DEL NIF TAL COMO LLEGA (antes de limpiar) -- si algo")
    print("distinto de 9 domina, hay ruido de formato, no error de tecleo:")
    for long_, n in longitud_cruda.most_common():
        print(f"    longitud {long_:>3}: {n:,}")
    print("")
    print(f"  con espacio al principio/final sin recortar: {tiene_espacio_extra:,}")
    print(f"  con algun caracter no-ASCII: {tiene_caracter_no_ascii:,}")
    print("")
    print("LETRA DE ORGANIZACION (primer caracter, solo si limpio da 9):")
    for letra, n in primera_letra_organizacion.most_common():
        print(f"    {letra}: {n:,}")
    print("")
    print("DIGITO DE CONTROL: letra vs numero (los dos son validos en CIF,")
    print("pero una proporcion extrana puede senalar un patron):")
    for tipo, n in ultimo_caracter_es_letra.most_common():
        print(f"    {tipo}: {n:,}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
