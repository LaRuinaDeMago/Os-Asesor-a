#!/usr/bin/env python3
"""diag_tres_guards.py — confirma el octavo arreglo Y que no ha movido nada
de los dos anteriores, en una sola pasada del corpus.

Comprueba juntos, por numero de tramos, los tres guards que ha tocado hoy
la derivacion de bases/cuotas:
    cuadre_total          (arreglo 6: base_total = suma del gasto, siempre)
    suma_tramos_general   (arreglo 7: por_tipo reescalado para sumar base_total)
    aritmetica_base_tipo  (arreglo 8: cuota_por_tipo directa, no derivada)

Solo cuenta y desglosa por numero de tramos. Nunca imprime NIF, importes, ni
ningun valor de una factura concreta.

Uso:
    python diag_tres_guards.py "RUTA_DEL_CORPUS"
"""
import os
import sys
import zipfile
import hashlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, num, txt, cuenta, numero_documento, reconstruir_compra
import motor_veredicto as mv
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

    por_ntramos = Counter()
    fallo = {"cuadre_total": Counter(), "suma_tramos": Counter(), "aritmetica_base_tipo": Counter()}
    contradice_alguna = Counter()   # al menos uno de los tres en FALLO
    contradice_todas_juntas = Counter()  # los tres a la vez FALLO (mismo asiento)

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
                        tramos = fila.get("tramos_iva") or []
                        n_tramos = len(tramos)
                        por_ntramos[n_tramos] += 1

                        base_10 = fila.get("base_10", 0.0) or 0.0
                        base_4 = fila.get("base_4", 0.0) or 0.0
                        base_21 = fila.get("base_21", 0.0) or 0.0
                        # cuadre_total real usa canonizar(); aqui basta con la
                        # misma cuenta que hace guard_cuadre_total, sin IRPF
                        # (el diario no lo trae en este reconstructor) ni
                        # recargo salvo el que ya va en la fila.
                        e_ct, _ = mv.guard_cuadre_total(
                            base_10, base_4, base_21, fila.get("iva_total", 0.0), 0.0,
                            fila.get("total_factura", 0.0),
                            fila.get("recargo_equivalencia", 0.0))
                        e_st, _ = mv.guard_suma_tramos_general(tramos, fila.get("base_total"))
                        e_at, _ = mv.guard_aritmetica_tramos(tramos, fila.get("iva_total"))

                        es_fallo = {"cuadre_total": e_ct == "FALLO",
                                    "suma_tramos": e_st == "FALLO",
                                    "aritmetica_base_tipo": e_at == "FALLO"}
                        for k, v in es_fallo.items():
                            if v:
                                fallo[k][n_tramos] += 1
                        if any(es_fallo.values()):
                            contradice_alguna[n_tramos] += 1
                        if all(es_fallo.values()):
                            contradice_todas_juntas[n_tramos] += 1
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 78)
    print(f"  compras evaluadas: {n_compras:,}")
    print("=" * 78)
    print(f"   {'tramos':>7}  {'n':>8}  {'cuadre_tot':>11}  {'suma_tramos':>12}  "
          f"{'aritm_tipo':>11}  {'alguna':>8}  {'las_3_juntas':>13}")
    for n_t in sorted(por_ntramos):
        n = por_ntramos[n_t]
        print(f"   {n_t:>7}  {n:>8,}  {fallo['cuadre_total'].get(n_t,0):>11,}  "
              f"{fallo['suma_tramos'].get(n_t,0):>12,}  "
              f"{fallo['aritmetica_base_tipo'].get(n_t,0):>11,}  "
              f"{contradice_alguna.get(n_t,0):>8,}  {contradice_todas_juntas.get(n_t,0):>13,}")

    print("")
    for k in ("cuadre_total", "suma_tramos", "aritmetica_base_tipo"):
        t = sum(fallo[k].values())
        print(f"  TOTAL {k:<24}: {t:,} / {n_compras:,} ({round(t*100.0/n_compras,2) if n_compras else 0}%)")
    print(f"  TOTAL con AL MENOS UNO en FALLO : {sum(contradice_alguna.values()):,}")
    print(f"  TOTAL con LOS TRES en FALLO     : {sum(contradice_todas_juntas.values()):,}")
    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
