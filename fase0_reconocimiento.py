#!/usr/bin/env python3
"""
fase0_reconocimiento.py — Paso previo a la Fase 0.

NO parsea contabilidad. NO calcula consistencia. Solo responde:
"¿qué hay exactamente en esa carpeta y en qué formato?"

REGLA DURA DE ESTE SCRIPT
-------------------------
Este script es INCAPAZ de imprimir contenido real. Nunca escribe en la salida
estandar ni en el agregado: nombres de fichero, nombres de carpeta, ni texto
extraido de los ficheros. Solo recuentos, tamaños, extensiones y histogramas
de valores de byte.

Emite DOS ficheros (patron de los dos planos):
  - fase0_reconocimiento.json    -> solo numeros. Seguro para compartir.
  - fase0_reconocimiento_LOCAL.json -> incluye rutas reales, para que las mires
                                        tu. NUNCA se comparte ni se versiona.

Uso:
    python fase0_reconocimiento.py "RUTA\\A\\LA\\CARPETA"
    python fase0_reconocimiento.py "RUTA" --max-ficheros 5000

No aborta nunca: captura los errores por fichero y los reporta al final
agrupados por tipo de error, con recuento.
"""

import sys
import os
import json
import argparse
from collections import Counter, defaultdict

SALIDA_AGREGADO = "fase0_reconocimiento.json"
SALIDA_LOCAL = "fase0_reconocimiento_LOCAL.json"

# Bytes que distinguen codificaciones. En CP850/CP437 las vocales acentuadas y
# la enye viven en 0xA0-0xA5; en CP1252/Latin-1 viven en 0xE0-0xFC; en UTF-8
# aparecen siempre precedidas de 0xC3. Contar CUANTOS de cada uno hay basta
# para deducir la codificacion sin leer ni una palabra.
FIRMA_CP850 = {0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0x82, 0xA9, 0x87}
FIRMA_CP1252 = {0xE1, 0xE9, 0xED, 0xF3, 0xFA, 0xF1, 0xC1, 0xC9, 0xD1}
FIRMA_UTF8 = {0xC3}

MUESTRA_BYTES = 65536  # cuanto se lee de cada fichero para el histograma


def clasificar_error(exc):
    """Nombre de la clase de error, sin el mensaje (puede llevar una ruta)."""
    return type(exc).__name__


def divisores_plausibles(tam, minimo=16, maximo=4096):
    """Longitudes de registro candidatas para un fichero de ancho fijo."""
    if tam <= 0:
        return []
    return [n for n in range(minimo, maximo + 1) if tam % n == 0]


def analizar_fichero(ruta):
    """Devuelve metricas de un fichero. Nunca devuelve contenido."""
    tam = os.path.getsize(ruta)
    with open(ruta, "rb") as f:
        muestra = f.read(MUESTRA_BYTES)

    hist = Counter(muestra)
    altos = {b: c for b, c in hist.items() if b >= 0x80}

    votos = {
        "cp850_cp437": sum(c for b, c in altos.items() if b in FIRMA_CP850),
        "cp1252_latin1": sum(c for b, c in altos.items() if b in FIRMA_CP1252),
        "utf8": sum(c for b, c in altos.items() if b in FIRMA_UTF8),
    }

    # Un fichero de texto tiene pocos bytes de control; uno binario, muchos.
    control = sum(c for b, c in hist.items() if b < 0x09 or 0x0E <= b < 0x20)
    ratio_control = round(control / len(muestra), 4) if muestra else 0.0

    cands = divisores_plausibles(tam)
    return {
        "tam_bytes": tam,
        "bytes_altos_distintos": len(altos),
        "votos_codificacion": votos,
        "ratio_bytes_control": ratio_control,
        "tiene_saltos_linea": (0x0A in hist),
        "n_longitudes_registro_candidatas": len(cands),
        "longitudes_registro_candidatas": cands[:12],
    }


def main():
    ap = argparse.ArgumentParser(description="Reconocimiento de una carpeta de copias de seguridad.")
    ap.add_argument("carpeta", help="Ruta de la carpeta a inspeccionar (se recorre recursivamente).")
    ap.add_argument("--max-ficheros", type=int, default=20000,
                    help="Tope de ficheros a analizar (por defecto 20000).")
    args = ap.parse_args()

    raiz = args.carpeta
    if not os.path.isdir(raiz):
        print("ERROR: esa ruta no existe o no es una carpeta.")
        print("       (no imprimo la ruta: revisala tu en el comando)")
        return 1

    print("Recorriendo la carpeta... (no se imprime ningun nombre de fichero)")

    por_ext = defaultdict(lambda: {
        "n": 0, "bytes": 0, "tam_min": None, "tam_max": None, "analizados": 0,
    })
    detalle_ext = defaultdict(list)   # ext -> [metricas]  (solo numeros)
    local_por_ext = defaultdict(list)  # ext -> [rutas]    (SOLO fichero LOCAL)

    errores = Counter()
    n_total = 0
    n_analizados = 0
    profundidad_max = 0
    n_carpetas = 0
    tope_alcanzado = False

    for dirpath, dirnames, filenames in os.walk(raiz):
        n_carpetas += 1
        prof = dirpath[len(raiz):].count(os.sep)
        profundidad_max = max(profundidad_max, prof)

        for nombre in filenames:
            n_total += 1
            if n_analizados >= args.max_ficheros:
                tope_alcanzado = True
                continue

            ruta = os.path.join(dirpath, nombre)
            ext = os.path.splitext(nombre)[1].lower() or "(sin extension)"

            try:
                tam = os.path.getsize(ruta)
            except Exception as e:
                errores[clasificar_error(e)] += 1
                continue

            e_ = por_ext[ext]
            e_["n"] += 1
            e_["bytes"] += tam
            e_["tam_min"] = tam if e_["tam_min"] is None else min(e_["tam_min"], tam)
            e_["tam_max"] = tam if e_["tam_max"] is None else max(e_["tam_max"], tam)

            # Analiza en profundidad solo los primeros 25 de cada extension:
            # basta para deducir formato y codificacion, y mantiene esto rapido.
            if e_["analizados"] < 25:
                try:
                    m = analizar_fichero(ruta)
                    detalle_ext[ext].append(m)
                    local_por_ext[ext].append(ruta)
                    e_["analizados"] += 1
                    n_analizados += 1
                except Exception as e:
                    errores[clasificar_error(e)] += 1

    # ---- Consolidar por extension, sin exponer nada identificable ----
    resumen_ext = {}
    for ext, e_ in sorted(por_ext.items(), key=lambda kv: -kv[1]["bytes"]):
        ms = detalle_ext.get(ext, [])
        bloque = {
            "n_ficheros": e_["n"],
            "bytes_totales": e_["bytes"],
            "tam_min": e_["tam_min"],
            "tam_max": e_["tam_max"],
            "n_analizados_a_fondo": len(ms),
        }
        if ms:
            votos = Counter()
            for m in ms:
                for k, v in m["votos_codificacion"].items():
                    votos[k] += v
            total_votos = sum(votos.values())
            bloque["codificacion"] = {
                "votos_absolutos": dict(votos),
                "veredicto": (max(votos, key=votos.get) if total_votos > 0
                              else "sin_acentos_en_la_muestra"),
            }
            bloque["ratio_bytes_control_medio"] = round(
                sum(m["ratio_bytes_control"] for m in ms) / len(ms), 4)
            bloque["con_saltos_de_linea"] = sum(1 for m in ms if m["tiene_saltos_linea"])
            # Longitudes de registro compatibles con TODOS los ficheros vistos:
            # si sale una lista corta, es ancho fijo y ahi esta la clave.
            comunes = None
            for m in ms:
                s = set(m["longitudes_registro_candidatas"])
                comunes = s if comunes is None else (comunes & s)
            bloque["longitudes_registro_comunes"] = sorted(comunes) if comunes else []
        resumen_ext[ext] = bloque

    agregado = {
        "version": "reconocimiento_v1",
        "n_ficheros_encontrados": n_total,
        "n_ficheros_analizados_a_fondo": n_analizados,
        "n_carpetas": n_carpetas,
        "profundidad_maxima_carpetas": profundidad_max,
        "tope_de_ficheros_alcanzado": tope_alcanzado,
        "bytes_totales": sum(e["bytes"] for e in por_ext.values()),
        "n_extensiones_distintas": len(por_ext),
        "por_extension": resumen_ext,
        "errores_por_tipo": dict(errores),
        "nota": "Solo numeros. Ningun nombre de fichero, carpeta ni contenido.",
    }

    with open(SALIDA_AGREGADO, "w", encoding="utf-8") as f:
        json.dump(agregado, f, indent=2, ensure_ascii=False)

    with open(SALIDA_LOCAL, "w", encoding="utf-8") as f:
        json.dump({
            "AVISO": "Contiene rutas reales. NUNCA compartir ni versionar.",
            "raiz": raiz,
            "ficheros_analizados_por_extension": {k: v for k, v in local_por_ext.items()},
        }, f, indent=2, ensure_ascii=False)

    # ---- Resumen por pantalla (solo numeros) ----
    print("")
    print("=" * 62)
    print(f"  Ficheros encontrados : {n_total}")
    print(f"  Analizados a fondo   : {n_analizados}")
    print(f"  Carpetas             : {n_carpetas}  (profundidad max {profundidad_max})")
    print(f"  Tamano total         : {agregado['bytes_totales'] / (1024*1024):.1f} MB")
    print(f"  Extensiones distintas: {len(por_ext)}")
    print("=" * 62)
    print("")
    print(f"{'ext':<16}{'n':>7}{'MB':>10}  {'codificacion':<22}{'long.reg':<12}")
    print("-" * 70)
    for ext, b in list(resumen_ext.items())[:20]:
        cod = b.get("codificacion", {}).get("veredicto", "-")
        lr = b.get("longitudes_registro_comunes", [])
        lr_s = ",".join(str(x) for x in lr[:3]) if lr else "-"
        print(f"{ext:<16}{b['n_ficheros']:>7}{b['bytes_totales']/(1024*1024):>10.1f}  {cod:<22}{lr_s:<12}")

    if errores:
        print("")
        print("Errores (agrupados por tipo, sin rutas):")
        for tipo, n in errores.most_common():
            print(f"   {tipo}: {n}")
    else:
        print("")
        print("Sin errores de lectura.")

    print("")
    print(f"Escrito: {SALIDA_AGREGADO}      <- solo numeros, se puede compartir")
    print(f"Escrito: {SALIDA_LOCAL}  <- lleva rutas, NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
