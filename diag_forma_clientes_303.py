#!/usr/bin/env python3
"""diag_forma_clientes_303.py — que forma tiene la fragmentacion de "clientes"
en reconstruir_303.py, sin mirar ningun nombre de carpeta ni codigo real.

Pregunta que contesta: de los cubos (carpeta+codigo) que produce clave_cliente(),
?cuantos contenedores .DAT mapean a cada uno, y que rango de anios cubre cada
cubo? Si la mayoria de cubos tienen 1 solo contenedor y cubren 1 solo anio, eso
confirma que la fragmentacion es "una copia de seguridad = un cubo nuevo", que
es exactamente lo que hay que enlazar.

El identificador de cliente se hashea ANTES de agruparlo -- nunca se guarda ni
se imprime el valor real. Solo se cuenta: cuantos contenedores por cubo, y que
anios cubre cada cubo (los anios SI son seguros: son metadatos de fecha, no
identidad).

Uso:
    python diag_forma_clientes_303.py "RUTA_DEL_CORPUS"
"""
import hashlib
import os
import sys
import zipfile
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retro_semaforo import parse_cabecera, txt
from reconstruir_303 import clave_cliente, trimestre_de


def main():
    raiz = os.path.abspath(sys.argv[1])
    dats = sorted(os.path.join(dp, n)
                  for dp, _, fns in os.walk(raiz) for n in fns
                  if os.path.splitext(n)[1].lower() == ".dat")
    print(f"{len(dats)} contenedores.")

    contenedores_por_cubo = Counter()
    anios_por_cubo = defaultdict(set)
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
                    cFEC = idx.get("FECHA")
                    if not cFEC:
                        continue

                    cubo_h = hashlib.blake2b(
                        clave_cliente(ruta).encode("utf-8"), digest_size=8).digest()
                    contenedores_por_cubo[cubo_h] += 1

                    # Un vistazo rapido a los primeros 300 registros basta para
                    # saber que anios cubre este contenedor -- no hace falta
                    # leerlo entero para esta pregunta concreta.
                    for _ in range(300):
                        rec = fh.read(len_reg)
                        if len(rec) < len_reg or rec[:1] == b"\x1a":
                            break
                        if rec[:1] == b"*":
                            continue
                        tri = trimestre_de(txt(rec, cFEC))
                        if tri:
                            anios_por_cubo[cubo_h].add(tri[0])
        except Exception as e:
            errores[type(e).__name__] += 1

    print("")
    print("=" * 66)
    print(f"  cubos (carpeta+codigo) distintos: {len(contenedores_por_cubo):,}")
    print("=" * 66)
    print("")
    print("CONTENEDORES POR CUBO (cuantos .DAT distintos caen en el mismo cubo):")
    dist = Counter(contenedores_por_cubo.values())
    for n_contenedores, n_cubos in sorted(dist.items()):
        print(f"    {n_contenedores:>3} contenedor(es)  ->  {n_cubos:>4,} cubos")

    print("")
    print("ANIOS DISTINTOS CUBIERTOS POR CUBO (de los primeros ~300 registros):")
    dist_anios = Counter(len(a) for a in anios_por_cubo.values())
    for n_anios, n_cubos in sorted(dist_anios.items()):
        print(f"    {n_anios:>3} anio(s)  ->  {n_cubos:>4,} cubos")

    todos_los_anios = set()
    for a in anios_por_cubo.values():
        todos_los_anios.update(a)
    if todos_los_anios:
        print("")
        print(f"  rango de anios visto en TODO el corpus: {min(todos_los_anios)}-{max(todos_los_anios)}")

    if errores:
        print(f"\nErrores: {dict(errores)}")


if __name__ == "__main__":
    main()
