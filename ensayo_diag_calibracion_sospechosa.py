#!/usr/bin/env python3
"""ensayo_diag_calibracion_sospechosa.py — ensayo en seco de
diag_calibracion_sospechosa.py.

QUE PRUEBA
------------
Fabrica un corpus donde la hipotesis "B" (mezcla real, correlacionada con
nombres de equipo/copia) es cierta por construccion: dos carpetas con
nombre de equipo mezclan proveedores sin solape (sospechosas de verdad), dos
carpetas con nombre de cliente concreto tienen proveedores compartidos entre
sus codigos (sanas de verdad). La tabla de contingencia debe reflejarlo
exactamente: 100% de sospechosas entre las de nombre-equipo, 0% entre las
de nombre-cliente.

REGLA DE DATOS: todo inventado, directorio temporal, borrado al terminar.

Uso:
    python ensayo_diag_calibracion_sospechosa.py
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
from diag_carpetas_multiempresa import calcular_sospechosas
from cuadre_303_ficha import suena_a_equipo

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def crear_codigo(carpeta_dir, nombre_dat, nifs, fecha="20200115"):
    os.makedirs(carpeta_dir, exist_ok=True)
    filas = [{"ASIEN": i + 1, "SUBCTA": "600000", "EURODEBE": 100,
              "EUROHABER": 0, "IVA": 21, "TERNIF": nif, "BASEIMPO": 0,
              "RECEQUIV": 0, "FECHA": fecha, "DOCUMENTO": f"F{i:04d}"}
             for i, nif in enumerate(nifs)]
    dbf = os.path.join(carpeta_dir, "Diario.dbf")
    escribir_dbf(dbf, filas)
    with zipfile.ZipFile(os.path.join(carpeta_dir, nombre_dat), "w") as z:
        z.write(dbf, "Diario.dbf")
    os.remove(dbf)


def main():
    print("ENSAYO EN SECO: diag_calibracion_sospechosa.py")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_calibracion_")
    try:
        raiz = os.path.join(tmp, "contaplus")

        # --- Dos carpetas de "equipo": mezcla real (sin solape) -------------
        for i in range(2):
            carpeta = os.path.join(raiz, f"Contabilidad Ordenador Equipo{i}")
            crear_codigo(carpeta, "CODA0001.DAT",
                         [cif_valido("B", 1000000 + i * 100 + k) for k in range(6)],
                         "20190101")
            crear_codigo(carpeta, "CODB0001.DAT",
                         [dni_valido(2000000 + i * 100 + k) for k in range(6)],
                         "20220601")

        # --- Dos carpetas de "cliente": sanas (mismo proveedor) --------------
        for i in range(2):
            carpeta = os.path.join(raiz, f"CLIENTE CONCRETO {i}")
            proveedores = [cif_valido("B", 5000000 + i * 100 + k) for k in range(6)]
            crear_codigo(carpeta, "CODC0001.DAT", proveedores, "20180101")
            crear_codigo(carpeta, "CODD0001.DAT", proveedores, "20230101")

        r = calcular_sospechosas(raiz, min_nifs=3, max_difusion=0.30)
        detalle = r["n_grupos_por_carpeta_real"]

        comprobar("4 carpetas con senal suficiente", len(detalle) == 4, detalle)

        n_equipo_sosp = sum(1 for n, g in detalle.items()
                            if suena_a_equipo(n) and g >= 2)
        n_equipo_total = sum(1 for n in detalle if suena_a_equipo(n))
        n_cliente_sosp = sum(1 for n, g in detalle.items()
                             if not suena_a_equipo(n) and g >= 2)
        n_cliente_total = sum(1 for n in detalle if not suena_a_equipo(n))

        comprobar("2 carpetas suenan a equipo, las 2 sospechosas (100%)",
                  n_equipo_total == 2 and n_equipo_sosp == 2,
                  (n_equipo_total, n_equipo_sosp))
        comprobar("2 carpetas suenan a cliente concreto, ninguna sospechosa (0%)",
                  n_cliente_total == 2 and n_cliente_sosp == 0,
                  (n_cliente_total, n_cliente_sosp))
        comprobar("la tabla de contingencia distingue las dos hipotesis con "
                  "datos donde la hipotesis 'mezcla real' es cierta por "
                  "construccion",
                  n_equipo_sosp == n_equipo_total and n_cliente_sosp == 0)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. La tabla de contingencia distingue mezcla real de "
          "artefacto cuando la diferencia existe de verdad en los datos.")


if __name__ == "__main__":
    main()
