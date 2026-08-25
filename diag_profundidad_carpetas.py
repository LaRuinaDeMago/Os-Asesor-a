#!/usr/bin/env python3
"""diag_profundidad_carpetas.py — a que nivel de profundidad hay ~33 carpetas
distintas, sin mostrar NUNCA un nombre de carpeta real.

Pregunta que contesta: clave_cliente() usa la carpeta INMEDIATA del .DAT
(un nivel). Si el corpus esta organizado como

    RAIZ/Cliente/Copia_fecha/SP_C_04A.DAT

el nivel correcto de "cliente" es DOS carpetas arriba del fichero, no una.
Si en cambio es

    RAIZ/Copia_fecha/SP_C_04A.DAT

no hay nivel de cliente que rescatar por aqui -- el codigo es la unica pista
y hace falta enlazarlo de otra forma.

Cada nombre de carpeta se hashea nada mas leerlo. Nunca se guarda ni se
imprime el texto real de una carpeta, en ningun momento del script.

Uso:
    python diag_profundidad_carpetas.py "RUTA_DEL_CORPUS"
"""
import hashlib
import os
import sys
from collections import defaultdict


def _h(valor):
    return hashlib.blake2b(valor.encode("utf-8", "replace"), digest_size=10).digest()


def main():
    raiz = os.path.abspath(sys.argv[1])

    distintos_por_nivel = defaultdict(set)   # nivel -> {hash(prefijo_de_carpetas), ...}
    n_dats = 0

    for dp, _, fns in os.walk(raiz):
        for n in fns:
            if os.path.splitext(n)[1].lower() != ".dat":
                continue
            n_dats += 1
            ruta = os.path.join(dp, n)
            rel = os.path.relpath(ruta, raiz)
            partes = rel.split(os.sep)[:-1]   # solo las carpetas, no el fichero
            prefijo_acum = ""
            for nivel, parte in enumerate(partes, start=1):
                prefijo_acum = prefijo_acum + "/" + parte if prefijo_acum else parte
                distintos_por_nivel[nivel].add(_h(prefijo_acum))

    print(f"{n_dats:,} ficheros .DAT encontrados.")
    print("")
    print("=" * 60)
    print("CARPETAS DISTINTAS POR NIVEL DE PROFUNDIDAD (desde la raiz):")
    print("=" * 60)
    print("  (el numero real de clientes conocido es 33 -- buscar ese nivel)")
    print("")
    for nivel in sorted(distintos_por_nivel):
        n = len(distintos_por_nivel[nivel])
        marca = "  <-- cerca de 33" if 20 <= n <= 50 else ""
        print(f"    nivel {nivel}: {n:>5,} carpetas distintas{marca}")


if __name__ == "__main__":
    main()
