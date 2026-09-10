#!/usr/bin/env python3
"""comparar_esquema_dbf.py — responde "¿es este .dbf el mismo layout que
ContaPlus?" sin que ningún dato real llegue nunca a Claude ni a la API.

DE DONDE SALE ESTO
--------------------
27-08-2026: al intentar confirmar si ContaSOL usa el mismo formato de
importación que ContaPlus, se adjuntaron ficheros reales a una conversación
Cloud pidiendo "no los leas" -- y el propio mecanismo de adjuntos los mostró
igualmente, antes de que hubiera ocasión de actuar. Incidente documentado en
PROJECT_STATUS.md y regla nueva en .claude/rules/datos.md: la barrera tiene
que estar ANTES de adjuntar nada, nunca dentro de la conversación.

Este script es esa barrera. Reutiliza leer_cabecera() de
fase0_esquema_dbf.py -- ya construida y ya verificada para leer SOLO la
cabecera de un .dbf (nombres de campo, tipos, anchos, nº de registros) y
PARARSE ahí, sin tocar jamás la zona de filas. Una cabecera dBase no
contiene ningún dato de cliente: es la definición de la estructura, igual
que el propio 'CAMPOS' de layout_diario_contaplus.py.

QUE HACE
----------
Lee la cabecera de un .dbf SUELTO (no dentro de un ZIP/.DAT, a diferencia
de fase0_esquema_dbf.py, pensado para el corpus histórico) y la compara
campo a campo contra el layout ya verificado de ContaPlus. Dice si son
IDÉNTICOS, o exactamente en qué difieren -- nombres de campo, orden, ancho.

Nunca imprime ni guarda ni una fila. Si el .dbf tiene un byte de más o de
menos en la cabecera, el límite duro ya heredado de fase0_esquema_dbf.py
para (65535 bytes) sigue aplicando.

USO (lo ejecuta Diego, en su máquina, ANTES de traer nada a ningún sitio):
    python comparar_esquema_dbf.py "ruta/al/fichero.dbf"

La salida son SOLO nombres de campo tecnicos (SUBCTA, TITULO, NIF...) y
numeros -- ni un nombre de cliente, ni un NIF, ni un importe. Es seguro
pegar la salida completa en el chat.
"""
import argparse
import os
import sys

from fase0_esquema_dbf import leer_cabecera
from layout_diario_contaplus import CAMPOS as CAMPOS_CONTAPLUS


def leer_esquema_dbf_suelto(path):
    """A diferencia de fase0_esquema_dbf.py (que abre un ZIP), este .dbf
    vive suelto en disco -- se abre directamente. leer_cabecera() sigue
    siendo la misma función, con la misma garantía: se para en el byte que
    la propia cabecera declara como su fin, nunca lee una fila."""
    with open(path, 'rb') as f:
        return leer_cabecera(f)


def comparar_contra_contaplus(campos_dbf):
    """Compara la lista de campos leída contra CAMPOS de
    layout_diario_contaplus.py (nombre, ancho -- no compara decimales/tipo
    porque el .dbf y el ASCII posicional codifican el tipo de forma distinta
    y no es lo que decide si el layout es 'el mismo').

    Devuelve (idéntico: bool, diferencias: list[str])."""
    nombres_cp = [(n, a) for n, a, _t, _d in CAMPOS_CONTAPLUS]
    nombres_dbf = [(c["nombre"], c["long"]) for c in campos_dbf]

    if nombres_cp == nombres_dbf:
        return True, []

    diferencias = []
    maxlen = max(len(nombres_cp), len(nombres_dbf))
    for i in range(maxlen):
        cp = nombres_cp[i] if i < len(nombres_cp) else None
        dbf = nombres_dbf[i] if i < len(nombres_dbf) else None
        if cp != dbf:
            diferencias.append(f"  posicion {i}: ContaPlus tiene {cp!r}, este fichero tiene {dbf!r}")
    return False, diferencias


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dbf", help="Ruta al fichero .dbf suelto (no dentro de un ZIP)")
    args = ap.parse_args()

    if not os.path.isfile(args.dbf):
        print(f"ERROR: no existe el fichero {args.dbf}", file=sys.stderr)
        sys.exit(2)

    esquema = leer_esquema_dbf_suelto(args.dbf)

    print("=" * 70)
    print("ESQUEMA DEL .DBF -- solo estructura, ningun dato de fila")
    print("=" * 70)
    print(f"  Version dBase:      {esquema['version']} ({esquema['version_byte']})")
    print(f"  Ultima actualiz.:   {esquema['ultima_actualizacion']}")
    print(f"  Numero de registros:{esquema['n_registros']}")
    print(f"  Longitud registro:  {esquema['long_registro']} bytes")
    print(f"  Codepage:           {esquema['codepage']}")
    print(f"  Numero de campos:   {esquema['n_campos']}")
    print(f"  Suma anchos cuadra: {esquema['cuadra_long_registro']}")
    print()
    print("  Campos (nombre, tipo, ancho, decimales):")
    for c in esquema["campos"]:
        print(f"    {c['nombre']:<12} {c['tipo']}  {c['long']:>4}  {c['dec']}")

    print()
    print("=" * 70)
    print("COMPARACION CONTRA EL LAYOUT YA VERIFICADO DE CONTAPLUS")
    print("=" * 70)
    identico, diferencias = comparar_contra_contaplus(esquema["campos"])
    if identico:
        print("  ✅ IDENTICO: mismos campos, mismo orden, mismos anchos que ContaPlus.")
        print("     El xDiario.txt que ya genera este proyecto deberia servir tal cual.")
    else:
        print(f"  ⚠️  DIFERENTE en {len(diferencias)} punto(s):")
        for d in diferencias:
            print(d)
        print("     No asumir que el xDiario de ContaPlus sirve sin mas -- hace falta")
        print("     adaptar el layout a esta diferencia concreta antes de exportar.")


if __name__ == "__main__":
    main()
