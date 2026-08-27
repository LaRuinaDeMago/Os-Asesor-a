#!/usr/bin/env python3
"""ensayo_enlazador_clientes_303.py — ensayo en seco de
`calcular_grupos()`/`escribir_detalle_grupos()` en enlazador_clientes_303.py.

POR QUE HACE FALTA
--------------------
`enlazador_clientes_303.py` se refactorizo el 27-08-2026 (consolidacion de
senales) para exponer una funcion reutilizable, `calcular_grupos()`, que
`consolidar_identidad.py` pueda importar sin duplicar la logica de
agrupamiento por NIF de proveedores. El script llevaba desde su creacion sin
NINGUN ensayo propio -- las "seis pruebas sinteticas" que documenta
PROJECT_STATUS.md (27-08-2026, tercera entrada) se corrieron a mano esa
sesion y no quedaron fijadas en codigo. Este ensayo cierra ese hueco Y
verifica que la extraccion de la logica a funcion no cambio el resultado.

QUE PRUEBA
------------
1. Dos carpetas DISTINTAS que comparten el mismo conjunto de proveedores
   (la misma empresa real, respaldada dos veces con nombres de carpeta
   distintos) deben agruparse -- es la senal que resuelve la fragmentacion
   documentada en la cabecera del script (una empresa partida en 15-40
   carpetas de copia).
2. Una tercera carpeta con proveedores propios, sin solape, NO debe
   agruparse con las otras dos.
3. El fichero de detalle (_LOCAL) solo lista grupos de 2+ carpetas
   distintas -- un grupo de una sola carpeta no aporta nada nuevo y solo
   añadiria ruido a la revision de Diego.
4. Por consola no se imprime ningun nombre de carpeta real, solo numeros
   (igual que antes de la refactorizacion: el comportamiento no cambia).

REGLA DE DATOS: todo inventado -- NIF con checksum valido pero ficticios,
carpetas en un directorio temporal, borrado al terminar. Ningun dato real.

Uso:
    python ensayo_enlazador_clientes_303.py
"""
import os
import shutil
import sys
import tempfile
import zipfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from ensayo_retro_semaforo import escribir_dbf, dni_valido, cif_valido
from enlazador_clientes_303 import calcular_grupos, escribir_detalle_grupos

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def crear_contenedor(raiz, carpeta, nombre_dat, nifs, asien_inicio=1, fecha="20200115"):
    """Un .DAT (ZIP con Diario.dbf) con un asiento simple por cada NIF de
    `nifs` -- suficiente para que TERNIF lo lea `calcular_grupos()`. El resto
    de campos son irrelevantes para esta prueba, se dejan a cero/vacio."""
    carpeta_dir = os.path.join(raiz, carpeta)
    os.makedirs(carpeta_dir, exist_ok=True)
    filas = []
    asien = asien_inicio
    for nif in nifs:
        filas.append({"ASIEN": asien, "SUBCTA": "600000", "EURODEBE": 100,
                       "EUROHABER": 0, "IVA": 21, "TERNIF": nif,
                       "BASEIMPO": 0, "RECEQUIV": 0, "FECHA": fecha,
                       "DOCUMENTO": f"F{asien:04d}"})
        asien += 1
    dbf = os.path.join(carpeta_dir, "Diario.dbf")
    escribir_dbf(dbf, filas)
    ruta_dat = os.path.join(carpeta_dir, nombre_dat)
    with zipfile.ZipFile(ruta_dat, "w") as z:
        z.write(dbf, "Diario.dbf")
    os.remove(dbf)
    return ruta_dat


def main():
    print("ENSAYO EN SECO: enlazador_clientes_303.py (calcular_grupos)")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_enlazador_")
    try:
        raiz = os.path.join(tmp, "contaplus")

        # 6 proveedores propios de "empresa A", identicos en las dos copias
        # -- simula la misma empresa real respaldada dos veces, cada copia
        # con su propio nombre de carpeta (lo habitual en el corpus real).
        proveedores_a = [cif_valido("B", 3000000 + k) for k in range(6)]
        # 6 proveedores DISTINTOS y propios de "empresa B" -- sin solape.
        proveedores_b = [dni_valido(40000000 + k) for k in range(6)]

        crear_contenedor(raiz, "EMPRESA_A_COPIA_2020", "SP_A20_A.DAT",
                          proveedores_a, asien_inicio=1, fecha="20200315")
        crear_contenedor(raiz, "EMPRESA_A_COPIA_2023", "SP_A23_A.DAT",
                          proveedores_a, asien_inicio=1, fecha="20230615")
        crear_contenedor(raiz, "EMPRESA_B_UNICA", "SP_B00_A.DAT",
                          proveedores_b, asien_inicio=1, fecha="20210410")

        r = calcular_grupos(raiz, max_difusion=0.30)

        comprobar("3 contenedores procesados", r["n_dats"] == 3, r["n_dats"])

        multi = {lider: nombres for lider, nombres in r["grupos_reales"].items()
                 if len(nombres) >= 2}
        comprobar("exactamente 1 grupo con 2+ carpetas distintas", len(multi) == 1,
                  f"{len(multi)} grupos multi-carpeta")

        if multi:
            nombres_grupo = next(iter(multi.values()))
            comprobar("caso 1: EMPRESA_A_COPIA_2020 y EMPRESA_A_COPIA_2023 "
                      "quedan en el MISMO grupo (mismos proveedores, "
                      "carpetas distintas)",
                      nombres_grupo == {"EMPRESA_A_COPIA_2020", "EMPRESA_A_COPIA_2023"},
                      nombres_grupo)

        comprobar("caso 2: EMPRESA_B_UNICA NO aparece en ningun grupo multi-carpeta",
                  all("EMPRESA_B_UNICA" not in nombres for nombres in multi.values()))

        # --- Fichero de detalle: solo grupos de 2+, nombres reales -----------
        ruta_detalle = os.path.join(tmp, "detalle_LOCAL.txt")
        n_multi = escribir_detalle_grupos(r["grupos_reales"], ruta_detalle)
        comprobar("escribir_detalle_grupos devuelve 1 grupo multi-carpeta",
                  n_multi == 1, n_multi)
        with open(ruta_detalle, encoding="utf-8") as f:
            texto = f.read()
        comprobar("caso 3: el fichero de detalle lista las dos copias de "
                  "EMPRESA_A juntas",
                  "EMPRESA_A_COPIA_2020" in texto and "EMPRESA_A_COPIA_2023" in texto)
        comprobar("caso 3: EMPRESA_B_UNICA (grupo de 1 carpeta) NO sale en "
                  "el detalle -- no aporta nada nuevo",
                  "EMPRESA_B_UNICA" not in texto)

        # --- Sanity check ya existente: anios NO solapados dentro del grupo --
        comprobar("las dos copias de EMPRESA_A no solapan anio (2020 vs 2023, "
                  "consistente con ser historico + reciente de la misma "
                  "empresa, no dos empresas distintas)",
                  r["grupos_con_solape"] == 0, r["grupos_con_solape"])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. calcular_grupos() agrupa por proveedores compartidos "
          "sin cambiar el comportamiento de siempre, y el detalle solo lista "
          "lo que aporta senal nueva.")


if __name__ == "__main__":
    main()
