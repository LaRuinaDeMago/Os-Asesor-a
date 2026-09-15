#!/usr/bin/env python3
"""
fase0_inventario.py — El mapa del historico. Que hay, de quien, y hasta cuando.

Responde, para cada cliente y cada ejercicio de 2016 a 2026:
    .tengo copia?  .cuantas?  .hasta que fecha llega?  .esta entera o cortada?
    .cuantos asientos trae?

Junta las piezas medidas en las sondas anteriores:
  - identidad del cliente -> grupo de huella (fase0_huella_LOCAL.json)
  - ejercicio y cobertura -> rango de fechas del propio Diario.dbf
  - fecha de corte declarada -> el "AL dd.mm.aaaa" del nombre de la subcarpeta
  - volumen -> recuento de lineas y asientos

CRUCE QUE IMPORTA: la fecha del nombre de carpeta y la ultima fecha de asiento
deberian coincidir. Si no coinciden, es informacion: o la carpeta esta mal
etiquetada, o la copia no llega donde dice.

DOS SALIDAS, patron de los dos planos
-------------------------------------
  inventario_LOCAL.csv    -> con rutas reales. NUNCA sube, nunca lo lee Claude.
  inventario_agregado.json -> solo cobertura y recuentos. Ese si.

REGLA DURA: el agregado no lleva rutas, ni nombres, ni fechas de dia — solo
grupo anonimo, ejercicio, mes de corte y recuentos. Errores por TIPO de
excepcion, nunca por mensaje. No aborta: recorre todo y reporta al final.

Uso:
    python fase0_inventario.py "RUTA"
"""

import os
import re
import sys
import csv
import json
import zipfile
import struct
import argparse
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
MAPA_HUELLA = os.path.join(BASE, "fase0_huella_LOCAL.json")
SALIDA = os.path.join(BASE, "inventario_agregado.json")
SALIDA_LOCAL = os.path.join(BASE, "inventario_LOCAL.csv")

TOPE_CABECERA = 65535
# "AL 16.06.2021", "AL 05-04-2021", "al 31.01.22"
RE_FECHA_CARPETA = re.compile(r"\bAL\s+(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})", re.I)


def parse_cabecera(stream):
    cab = stream.read(32)
    if len(cab) < 32:
        raise ValueError("cabecera corta")
    len_cab = struct.unpack("<H", cab[8:10])[0]
    len_reg = struct.unpack("<H", cab[10:12])[0]
    if len_cab <= 32 or len_cab > TOPE_CABECERA:
        raise ValueError("cabecera implausible")
    resto = stream.read(len_cab - 32)
    campos, off, pos = [], 0, 1
    while off + 32 <= len(resto):
        if resto[off] == 0x0D:
            break
        b = resto[off:off + 32]
        campos.append({"nombre": b[0:11].split(b"\x00")[0].decode("ascii", "replace"),
                       "tipo": chr(b[11]), "ini": pos, "long": b[16]})
        pos += b[16]
        off += 32
    return len_reg, campos


def fecha_de_carpeta(ruta, raiz):
    rel = os.path.relpath(ruta, raiz)
    primero = rel.split(os.sep)[0] if os.sep in rel else ""
    m = RE_FECHA_CARPETA.search(primero)
    if not m:
        return None
    d, mth, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if y < 100:
        y += 2000
    if not (1 <= mth <= 12 and 1 <= d <= 31 and 2000 <= y <= 2100):
        return None
    return y * 10000 + mth * 100 + d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("carpeta")
    ap.add_argument("--mapa", default=MAPA_HUELLA,
                    help="Fichero _LOCAL con la correspondencia contenedor->grupo. "
                         "Por defecto el de fase0_huella_cliente.py; usar el de "
                         "fase0_reagrupa.py para la agrupacion corregida.")
    args = ap.parse_args()
    raiz = os.path.abspath(args.carpeta)
    if not os.path.isdir(raiz):
        print("ERROR: la ruta no existe o no es una carpeta.")
        return 1

    mapa_path = args.mapa
    grupo_de = {}
    if os.path.exists(mapa_path):
        with open(mapa_path, encoding="utf-8") as f:
            grupo_de = {k: int(v) for k, v in json.load(f)["contenedor_a_grupo"].items()}
        print(f"Huellas cargadas: {len(grupo_de)} contenedores con cliente asignado.")
    else:
        print("AVISO: no encuentro fase0_huella_LOCAL.json.")
        print("       El inventario saldra sin agrupar por cliente.")

    dats = []
    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() == ".dat":
                dats.append(os.path.join(dp, n))
    dats.sort()
    print(f"{len(dats)} contenedores. Construyendo el inventario...")

    filas = []
    errores = Counter()
    sin_diario = 0
    sin_grupo = 0

    for ruta in dats:
        try:
            if not zipfile.is_zipfile(ruta):
                continue
            with zipfile.ZipFile(ruta) as z:
                interno = None
                for i in z.infolist():
                    if not i.is_dir() and os.path.basename(i.filename).lower() == "diario.dbf":
                        interno = i.filename
                        break
                if interno is None:
                    sin_diario += 1
                    continue
                with z.open(interno) as f:
                    len_reg, campos = parse_cabecera(f)
                    cF = next((c for c in campos if c["nombre"] == "FECHA"), None)
                    cA = next((c for c in campos if c["nombre"] == "ASIEN"), None)
                    fmin, fmax = None, None
                    anios = Counter()
                    asientos = set()
                    n_lin = 0
                    while True:
                        rec = f.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        n_lin += 1
                        if cF:
                            s = rec[cF["ini"]:cF["ini"] + cF["long"]].strip(b" \x00")
                            if len(s) == 8 and s.isdigit():
                                v = int(s)
                                if 19900101 <= v <= 21001231:
                                    fmin = v if fmin is None else min(fmin, v)
                                    fmax = v if fmax is None else max(fmax, v)
                                    anios[v // 10000] += 1
                        if cA:
                            a = rec[cA["ini"]:cA["ini"] + cA["long"]].strip(b" \x00")
                            if a:
                                asientos.add(a)
                        del rec

            g = grupo_de.get(ruta)
            if g is None:
                sin_grupo += 1
            ejercicio = anios.most_common(1)[0][0] if anios else None
            fcarp = fecha_de_carpeta(ruta, raiz)
            rel = os.path.relpath(ruta, raiz)
            filas.append({
                "grupo": g if g is not None else -1,
                "ejercicio": ejercicio,
                "n_lineas": n_lin,
                "n_asientos": len(asientos),
                "fecha_min": fmin,
                "fecha_max": fmax,
                "fecha_carpeta": fcarp,
                "subcarpeta": rel.split(os.sep)[0] if os.sep in rel else "(raiz)",
                "ruta": ruta,
            })
        except Exception as e:
            errores[type(e).__name__] += 1

    # ---------------- LOCAL: el mapa para el titular ----------------
    with open(SALIDA_LOCAL, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["cliente_grupo", "ejercicio", "n_lineas", "n_asientos",
                    "primer_asiento", "ultimo_asiento", "fecha_en_carpeta",
                    "mes_de_corte", "subcarpeta", "ruta"])
        for r in sorted(filas, key=lambda x: (x["grupo"], x["ejercicio"] or 0,
                                              x["fecha_max"] or 0)):
            mes = (r["fecha_max"] // 100) % 100 if r["fecha_max"] else ""
            w.writerow([r["grupo"], r["ejercicio"] or "", r["n_lineas"], r["n_asientos"],
                        r["fecha_min"] or "", r["fecha_max"] or "",
                        r["fecha_carpeta"] or "", mes, r["subcarpeta"], r["ruta"]])

    # ---------------- AGREGADO: solo cobertura ----------------
    # Por (cliente, ejercicio) nos quedamos con la copia que MAS LEJOS llega.
    mejor = {}
    for r in filas:
        if r["grupo"] < 0 or not r["ejercicio"]:
            continue
        k = (r["grupo"], r["ejercicio"])
        if k not in mejor or (r["fecha_max"] or 0) > (mejor[k]["fecha_max"] or 0):
            mejor[k] = r

    cobertura = defaultdict(dict)
    for (g, ej), r in mejor.items():
        mes = (r["fecha_max"] // 100) % 100 if r["fecha_max"] else 0
        cobertura[g][ej] = mes

    ejercicios = sorted({ej for _, ej in mejor})
    clientes = sorted(cobertura)

    meses_corte = Counter()
    completos = 0
    for k, r in mejor.items():
        mes = (r["fecha_max"] // 100) % 100 if r["fecha_max"] else 0
        meses_corte[mes] += 1
        if mes == 12:
            completos += 1

    # .Cuadra la fecha del nombre de carpeta con el ultimo asiento?
    cuadra, no_cuadra, sin_fecha_carp = 0, 0, 0
    for r in filas:
        if not r["fecha_carpeta"]:
            sin_fecha_carp += 1
        elif r["fecha_max"] and r["fecha_max"] <= r["fecha_carpeta"]:
            cuadra += 1
        else:
            no_cuadra += 1

    agregado = {
        "version": "inventario_v1",
        "contenedores_totales": len(dats),
        "con_diario": len(filas),
        "sin_diario": sin_diario,
        "sin_cliente_asignado": sin_grupo,
        "clientes_detectados": len(clientes),
        "ejercicios_cubiertos": ejercicios,
        "pares_cliente_ejercicio": len(mejor),
        "celdas_posibles": len(clientes) * len(ejercicios) if ejercicios else 0,
        "pct_cobertura": round(len(mejor) / (len(clientes) * len(ejercicios)) * 100, 1)
                         if clientes and ejercicios else 0,
        "ejercicios_completos_hasta_diciembre": completos,
        "pct_completos": round(completos / len(mejor) * 100, 1) if mejor else 0,
        "distribucion_mes_de_corte": {str(k): v for k, v in sorted(meses_corte.items())},
        "coherencia_fecha_carpeta": {
            "coincide_o_anterior": cuadra,
            "el_diario_va_mas_alla_que_la_carpeta": no_cuadra,
            "carpeta_sin_fecha_declarada": sin_fecha_carp,
        },
        "copias_por_par_cliente_ejercicio": dict(Counter(
            Counter((r["grupo"], r["ejercicio"]) for r in filas
                    if r["grupo"] >= 0 and r["ejercicio"]).values())),
        "errores": dict(errores),
        "nota": "Solo recuentos, grupos anonimos y meses. Sin rutas ni nombres.",
    }
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(agregado, f, indent=2, ensure_ascii=False)

    # ---------------- pantalla ----------------
    print("")
    print("=" * 72)
    print(f"  contenedores con diario   : {len(filas)}")
    print(f"  sin diario                : {sin_diario}")
    print(f"  sin cliente asignado      : {sin_grupo}")
    print(f"  CLIENTES DETECTADOS       : {len(clientes)}")
    print(f"  ejercicios                : {ejercicios[0] if ejercicios else '-'}"
          f" - {ejercicios[-1] if ejercicios else '-'}")
    print(f"  pares cliente-ejercicio   : {len(mejor)} de "
          f"{agregado['celdas_posibles']} posibles  ({agregado['pct_cobertura']}%)")
    print("=" * 72)
    print("")
    print("MAPA DE COBERTURA — mes hasta el que llega la mejor copia")
    print("  (12 = ejercicio entero, '.' = sin copia)")
    print("")
    cab = "  cli " + "".join(f"{e % 100:>4}" for e in ejercicios)
    print(cab)
    print("  " + "-" * (len(cab) - 2))
    for g in clientes:
        fila = f"  {g:>3} "
        for e in ejercicios:
            m = cobertura[g].get(e)
            fila += f"{m:>4}" if m else "   ."
        print(fila)
    print("")
    print("DISTRIBUCION DEL MES DE CORTE:")
    for m, n in sorted(meses_corte.items()):
        barra = "#" * int(n / max(meses_corte.values()) * 40)
        print(f"   mes {m:>2}: {n:>4}  {barra}")
    print("")
    print(f"  Ejercicios completos (hasta diciembre): {completos} de {len(mejor)}"
          f"  ({agregado['pct_completos']}%)")
    print("")
    c = agregado["coherencia_fecha_carpeta"]
    print("COHERENCIA con la fecha declarada en el nombre de carpeta:")
    print(f"   el diario no pasa de esa fecha : {c['coincide_o_anterior']}")
    print(f"   el diario VA MAS ALLA          : {c['el_diario_va_mas_alla_que_la_carpeta']}")
    print(f"   carpeta sin fecha en el nombre : {c['carpeta_sin_fecha_declarada']}")
    if errores:
        print(f"\nErrores: {dict(errores)}")
    print("")
    print(f"Escrito: {SALIDA}")
    print(f"Escrito: {SALIDA_LOCAL}   <- tu mapa, con rutas. NO compartir")
    return 0


if __name__ == "__main__":
    sys.exit(main())
