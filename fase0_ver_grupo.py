#!/usr/bin/env python3
"""
fase0_ver_grupo.py — HERRAMIENTA LOCAL. Para los ojos del titular, no de Claude.

Sirve para validar a mano la agrupacion de fase0_huella_cliente.py. Muestra,
para un grupo dado, los nombres de contraparte mas frecuentes — que es lo unico
que permite reconocer de un vistazo de que cliente se trata.

  *** ESTA SALIDA CONTIENE NOMBRES REALES DE PROVEEDORES Y CLIENTES. ***
  *** NO SE PEGA EN EL CHAT. Se mira, se saca la conclusion, y se        ***
  *** responde solo la conclusion: "es un cliente" / "son tres".         ***

Es la excepcion deliberada a la regla del proyecto: aqui el dato real SI se
imprime, porque el juicio humano es el unico que puede cerrar esta pregunta.
Por eso se imprime en pantalla y no se escribe a ningun fichero.

Uso:
    python fase0_ver_grupo.py                 -> lista los grupos por tamano
    python fase0_ver_grupo.py 7               -> detalle del grupo 7
    python fase0_ver_grupo.py 7 --top 40      -> mas nombres
"""

import os
import sys
import json
import zipfile
import struct
import argparse
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
MAPA = os.path.join(BASE, "fase0_huella_LOCAL.json")
TOPE_CABECERA = 65535
TOPE_REGISTROS = 5000


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


def titulos_de(ruta):
    """Nombres de contraparte de un contenedor. Solo se usan en pantalla."""
    out = Counter()
    with zipfile.ZipFile(ruta) as z:
        interno = None
        for i in z.infolist():
            if not i.is_dir() and os.path.basename(i.filename).lower() == "subcta.dbf":
                interno = i.filename
                break
        if interno is None:
            return out
        with z.open(interno) as f:
            len_reg, campos = parse_cabecera(f)
            cT = next((c for c in campos if c["nombre"] == "TITULO"), None)
            cC = next((c for c in campos if c["nombre"] == "COD"), None)
            if cT is None:
                return out
            leidos = 0
            while leidos < TOPE_REGISTROS:
                rec = f.read(len_reg)
                if len(rec) < len_reg or rec[:1] == b"\x1a":
                    break
                if rec[:1] == b"*":
                    continue
                leidos += 1
                cod = rec[cC["ini"]:cC["ini"] + cC["long"]].strip(b" \x00") if cC else b""
                # Solo cuentas de tercero: proveedores (400/401/410) y
                # clientes (430/431/440). El resto son cuentas de estructura.
                if not cod[:3] in (b"400", b"401", b"410", b"430", b"431", b"440"):
                    continue
                t = rec[cT["ini"]:cT["ini"] + cT["long"]].strip(b" \x00")
                if t:
                    out[t.decode("cp1252", "replace").strip()] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("grupo", nargs="?", type=int, default=None)
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    if not os.path.exists(MAPA):
        print("No encuentro fase0_huella_LOCAL.json.")
        print("Ejecuta antes fase0_huella_cliente.py.")
        return 1

    with open(MAPA, encoding="utf-8") as f:
        d = json.load(f)
    mapa = d["contenedor_a_grupo"]

    por_grupo = defaultdict(list)
    for ruta, g in mapa.items():
        por_grupo[int(g)].append(ruta)

    if args.grupo is None:
        print("GRUPOS DETECTADOS (ordenados por tamano)")
        print(f"  umbral usado: {d.get('umbral')}")
        print("")
        print(f"  {'grupo':>7}{'copias':>9}   subcarpetas")
        print("  " + "-" * 40)
        for g, rutas in sorted(por_grupo.items(), key=lambda kv: -len(kv[1])):
            subs = len({r.split(os.sep)[-2] for r in rutas if os.sep in r})
            print(f"  {g:>7}{len(rutas):>9}   {subs}")
        print("")
        print("Para ver quien es un grupo:  python fase0_ver_grupo.py <numero>")
        return 0

    rutas = por_grupo.get(args.grupo)
    if not rutas:
        print(f"El grupo {args.grupo} no existe.")
        return 1

    print("=" * 70)
    print("  *** SALIDA CON NOMBRES REALES — NO PEGAR EN EL CHAT ***")
    print("=" * 70)
    print(f"  Grupo {args.grupo}: {len(rutas)} copias")
    print("")

    # Se muestrean copias repartidas, no las primeras: si el grupo estuviera
    # fusionando dos clientes, mirar solo las primeras lo ocultaria.
    paso = max(1, len(rutas) // 12)
    muestra = sorted(rutas)[::paso][:12]

    total = Counter()
    por_copia = []
    for r in muestra:
        try:
            t = titulos_de(r)
            total.update(t)
            por_copia.append((r, t))
        except Exception as e:
            print(f"  (no se pudo leer una copia: {type(e).__name__})")

    print(f"  CONTRAPARTES MAS FRECUENTES (sobre {len(por_copia)} copias del grupo):")
    print("  " + "-" * 60)
    for nom, n in total.most_common(args.top):
        print(f"   {n:>4}x  {nom}")

    print("")
    print("  REPARTO POR COPIA — .son todas del mismo cliente?")
    print("  (si dos copias no comparten casi ningun nombre, el grupo esta")
    print("   fusionando clientes distintos)")
    print("  " + "-" * 60)
    base = None
    for r, t in por_copia:
        nombres = set(t)
        if base is None:
            base = nombres
            sol = 100.0
        else:
            sol = len(base & nombres) / len(base | nombres) * 100 if (base | nombres) else 0
        etiqueta = os.sep.join(r.split(os.sep)[-2:])
        print(f"   {sol:>5.1f}% en comun con la 1a   {etiqueta}")

    print("")
    print("  QUE RESPONDER EN EL CHAT: solo la conclusion.")
    print("  \"el grupo N es un solo cliente\"  o  \"son 2 clientes distintos\".")
    print("  Ningun nombre.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
