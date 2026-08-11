#!/usr/bin/env python3
"""
fase0_sonda_formatos.py — Iteracion 2 del reconocimiento.

Responde DOS preguntas, en una sola ejecucion:

  A) Los PDF, .tienen capa de texto o son escaneados?
     -> decide si la extraccion es gratis (pymupdf local) o cuesta dinero (OCR).

  B) Que formato tienen los .DAT?
     -> agrupa por firma de cabecera y busca longitud de registro POR GRUPO
        (el error de la iteracion 1 fue intersecar todos los .dat a la vez).

NO necesita instalar nada: solo biblioteca estandar (zlib va incluido).

REGLA DURA DE ESTE SCRIPT
-------------------------
Incapaz de imprimir contenido. Las funciones de analisis devuelven SOLO
enteros y banderas. La firma de cabecera se reporta ENMASCARADA: los bytes
imprimibles salen como '.', solo se muestran en hexadecimal los no
imprimibles. Asi una cabecera que contenga un nombre no puede escaparse.

Uso:
    python fase0_sonda_formatos.py "RUTA\\A\\LA\\CARPETA"
"""

import sys
import os
import json
import zlib
import argparse
from collections import Counter, defaultdict

SALIDA = "fase0_sonda_formatos.json"

N_PDF_PROFUNDO = 40      # PDFs a los que se les descomprimen los streams
N_DAT_PROFUNDO = 120     # .DAT a los que se les busca longitud de registro
CABECERA = 16            # bytes de firma


def enmascarar(bs):
    """Firma segura: los bytes imprimibles se ocultan como '.', el resto en hex.

    Un nombre de empresa en la cabecera saldria como '............' y nunca
    como texto legible.
    """
    out = []
    for b in bs:
        if 0x20 <= b <= 0x7E:
            out.append("..")
        else:
            out.append(f"{b:02X}")
    return " ".join(out)


def divisores(tam, minimo=16, maximo=4096):
    if tam <= 0:
        return []
    return [n for n in range(minimo, maximo + 1) if tam % n == 0]


# ----------------------------- PDF -----------------------------------

def analizar_pdf(ruta, profundo):
    """Devuelve SOLO enteros/booleanos sobre la estructura del PDF."""
    with open(ruta, "rb") as f:
        raw = f.read()

    r = {
        "tam": len(raw),
        "n_font": raw.count(b"/Font"),
        "n_image": raw.count(b"/Image"),
        "n_paginas": raw.count(b"/Type/Page") + raw.count(b"/Type /Page"),
        "dct": raw.count(b"/DCTDecode"),        # JPEG embebido (escaneo)
        "ccitt": raw.count(b"/CCITTFaxDecode"), # fax/TIFF (escaneo)
        "jbig2": raw.count(b"/JBIG2Decode"),    # escaneo comprimido
        "jpx": raw.count(b"/JPXDecode"),        # JPEG2000 (escaneo)
        "n_ops_texto": None,
        "streams_leidos": 0,
    }

    if profundo:
        ops = 0
        leidos = 0
        pos = 0
        # Recorre los streams y cuenta operadores de texto tras descomprimir.
        # Nunca se guarda ni se imprime el contenido descomprimido.
        while leidos < 60:
            i = raw.find(b"stream", pos)
            if i == -1:
                break
            j = raw.find(b"endstream", i)
            if j == -1:
                break
            cuerpo = raw[i + 6:j].lstrip(b"\r\n")
            pos = j + 9
            try:
                datos = zlib.decompress(cuerpo)
            except Exception:
                datos = cuerpo  # sin comprimir, o con otro filtro
            ops += datos.count(b"Tj") + datos.count(b"TJ")
            leidos += 1
            del datos
        r["n_ops_texto"] = ops
        r["streams_leidos"] = leidos

    return r


def clasificar_pdf(r):
    """TEXTO / ESCANEADO / MIXTO / INDETERMINADO."""
    escaneo = r["dct"] + r["ccitt"] + r["jbig2"] + r["jpx"]
    ops = r["n_ops_texto"]
    if ops is None:
        if r["n_font"] > 0 and escaneo == 0:
            return "TEXTO_probable"
        if escaneo > 0 and r["n_font"] == 0:
            return "ESCANEADO_probable"
        return "INDETERMINADO"
    if ops >= 50 and escaneo == 0:
        return "TEXTO"
    if ops >= 50 and escaneo > 0:
        return "MIXTO"
    if ops < 50 and escaneo > 0:
        return "ESCANEADO"
    return "INDETERMINADO"


# ----------------------------- DAT -----------------------------------

def analizar_dat(ruta, profundo):
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as f:
        cab = f.read(CABECERA)
    r = {"tam": tam, "firma": enmascarar(cab)}
    if profundo:
        cands = divisores(tam)
        r["n_cands"] = len(cands)
        r["cands"] = cands[:10]
        # .Es un fichero paginado (Btrieve/Pervasive suelen serlo)?
        r["paginas"] = {str(p): (tam % p == 0) for p in (512, 1024, 2048, 4096)}
    return r


# ----------------------------- main -----------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    args = ap.parse_args()
    raiz = args.carpeta

    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es carpeta. Revisala tu.")
        return 1

    pdfs, dats = [], []
    for dirpath, _, filenames in os.walk(raiz):
        for n in filenames:
            ext = os.path.splitext(n)[1].lower()
            if ext == ".pdf":
                pdfs.append(os.path.join(dirpath, n))
            elif ext == ".dat":
                dats.append(os.path.join(dirpath, n))

    print(f"Encontrados: {len(pdfs)} PDF, {len(dats)} DAT. Analizando...")

    # ---- A) PDFs ----
    clases = Counter()
    ops_muestra = []
    paginas_total = 0
    errores_pdf = Counter()
    for idx, p in enumerate(sorted(pdfs)):
        profundo = idx < N_PDF_PROFUNDO
        try:
            r = analizar_pdf(p, profundo)
            clases[clasificar_pdf(r)] += 1
            paginas_total += r["n_paginas"]
            if profundo and r["n_ops_texto"] is not None:
                ops_muestra.append(r["n_ops_texto"])
        except Exception as e:
            errores_pdf[type(e).__name__] += 1

    # ---- B) DATs ----
    por_firma = defaultdict(lambda: {"n": 0, "tam_min": None, "tam_max": None})
    cands_por_firma = defaultdict(list)
    pag_por_firma = defaultdict(Counter)
    errores_dat = Counter()
    for idx, d in enumerate(sorted(dats)):
        try:
            r = analizar_dat(d, idx < N_DAT_PROFUNDO)
            f_ = r["firma"]
            g = por_firma[f_]
            g["n"] += 1
            g["tam_min"] = r["tam"] if g["tam_min"] is None else min(g["tam_min"], r["tam"])
            g["tam_max"] = r["tam"] if g["tam_max"] is None else max(g["tam_max"], r["tam"])
            if "cands" in r:
                cands_por_firma[f_].append(set(r["cands"]))
                for p, ok in r["paginas"].items():
                    if ok:
                        pag_por_firma[f_][p] += 1
        except Exception as e:
            errores_dat[type(e).__name__] += 1

    firmas = {}
    for f_, g in sorted(por_firma.items(), key=lambda kv: -kv[1]["n"])[:15]:
        comunes = None
        for s in cands_por_firma.get(f_, []):
            comunes = s if comunes is None else (comunes & s)
        firmas[f_] = {
            "n_ficheros": g["n"],
            "tam_min": g["tam_min"],
            "tam_max": g["tam_max"],
            "long_registro_comunes_en_el_grupo": sorted(comunes) if comunes else [],
            "alineado_a_pagina": dict(pag_por_firma.get(f_, {})),
        }

    salida = {
        "version": "sonda_formatos_v1",
        "pdf": {
            "n_total": len(pdfs),
            "n_analizados_a_fondo": min(N_PDF_PROFUNDO, len(pdfs)),
            "clasificacion": dict(clases),
            "paginas_totales_estimadas": paginas_total,
            "ops_texto_muestra": {
                "min": min(ops_muestra) if ops_muestra else 0,
                "max": max(ops_muestra) if ops_muestra else 0,
                "media": round(sum(ops_muestra) / len(ops_muestra), 1) if ops_muestra else 0,
                "n_con_cero_ops": sum(1 for o in ops_muestra if o == 0),
            },
            "errores": dict(errores_pdf),
        },
        "dat": {
            "n_total": len(dats),
            "n_firmas_distintas": len(por_firma),
            "firmas_mas_frecuentes": firmas,
            "errores": dict(errores_dat),
        },
        "nota": "Solo numeros y firmas enmascaradas. Ningun contenido ni nombre.",
    }

    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    # ---- Pantalla ----
    print("")
    print("=" * 64)
    print("  A) PDF — .capa de texto o escaneado?")
    print("=" * 64)
    for k, v in clases.most_common():
        print(f"   {k:<22} {v:>5}")
    print(f"   paginas totales (aprox) : {paginas_total}")
    if ops_muestra:
        print(f"   operadores de texto     : min {min(ops_muestra)}  "
              f"media {sum(ops_muestra)/len(ops_muestra):.0f}  max {max(ops_muestra)}")
        print(f"   PDFs con CERO texto     : {sum(1 for o in ops_muestra if o == 0)} de {len(ops_muestra)}")
    if errores_pdf:
        print(f"   errores: {dict(errores_pdf)}")

    print("")
    print("=" * 64)
    print(f"  B) DAT — {len(por_firma)} firmas de cabecera distintas")
    print("=" * 64)
    print(f"{'n':>6}  {'tam_min':>10} {'tam_max':>11}  {'long.reg':<16} firma (hex, '..'=imprimible)")
    print("-" * 100)
    for f_, b in list(firmas.items())[:12]:
        lr = b["long_registro_comunes_en_el_grupo"]
        lr_s = ",".join(str(x) for x in lr[:4]) if lr else "-"
        print(f"{b['n_ficheros']:>6}  {b['tam_min']:>10} {b['tam_max']:>11}  {lr_s:<16} {f_[:47]}")
    if errores_dat:
        print(f"   errores: {dict(errores_dat)}")

    print("")
    print(f"Escrito: {SALIDA}   <- solo numeros, se puede compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
