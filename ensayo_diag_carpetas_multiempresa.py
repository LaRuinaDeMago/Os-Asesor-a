#!/usr/bin/env python3
"""ensayo_diag_carpetas_multiempresa.py — ensayo en seco de
`calcular_sospechosas()`/`escribir_detalle_multiempresa()` en
diag_carpetas_multiempresa.py.

POR QUE HACE FALTA
--------------------
Mismo motivo que `ensayo_enlazador_clientes_303.py`: el script se
refactorizo el 27-08-2026 para exponer `calcular_sospechosas()`, reutilizable
desde `consolidar_identidad.py`, y no tenia ningun ensayo propio en el
repositorio pese a llevar dos arreglos reales encontrados contra el corpus
real (el filtro de difusion, documentado en su propia cabecera).

QUE PRUEBA
------------
1. Una carpeta cuyos dos codigos internos tienen proveedores SIN solape
   (dos empresas reales compartiendo una carpeta, el caso ya confirmado a
   mano de "Contabilidad ordenador de Jose") se marca con 2+ grupos ->
   SOSPECHOSA.
2. Una carpeta cuyos dos codigos comparten los mismos proveedores (la MISMA
   empresa, dos copias) se marca con 1 grupo -> sana, nunca falso positivo.
3. `escribir_detalle_multiempresa()` escribe el nombre real de cada carpeta
   con senal suficiente, marcando SOSPECHOSA solo donde corresponde.
4. Por consola no se imprime ningun nombre real, solo indices/numeros (el
   comportamiento de siempre, sin cambios tras la refactorizacion).

REGLA DE DATOS: todo inventado, directorio temporal, borrado al terminar.

Uso:
    python ensayo_diag_carpetas_multiempresa.py
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
from diag_carpetas_multiempresa import calcular_sospechosas, escribir_detalle_multiempresa

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def crear_codigo(carpeta_dir, nombre_dat, nifs, fecha="20200115"):
    """Un .DAT (codigo) dentro de una carpeta ya existente, con un asiento
    simple por NIF -- suficiente para que TERNIF lo lea calcular_sospechosas."""
    os.makedirs(carpeta_dir, exist_ok=True)
    filas = [{"ASIEN": i + 1, "SUBCTA": "600000", "EURODEBE": 100,
              "EUROHABER": 0, "IVA": 21, "TERNIF": nif, "BASEIMPO": 0,
              "RECEQUIV": 0, "FECHA": fecha, "DOCUMENTO": f"F{i:04d}"}
             for i, nif in enumerate(nifs)]
    dbf = os.path.join(carpeta_dir, "Diario.dbf")
    escribir_dbf(dbf, filas)
    ruta_dat = os.path.join(carpeta_dir, nombre_dat)
    with zipfile.ZipFile(ruta_dat, "w") as z:
        z.write(dbf, "Diario.dbf")
    os.remove(dbf)


def main():
    print("ENSAYO EN SECO: diag_carpetas_multiempresa.py (calcular_sospechosas)")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_multiempresa_")
    try:
        raiz = os.path.join(tmp, "contaplus")

        # --- Carpeta MEZCLA: dos codigos, proveedores SIN solape -------------
        proveedores_x = [cif_valido("B", 5000000 + k) for k in range(6)]
        proveedores_y = [dni_valido(60000000 + k) for k in range(6)]
        carpeta_mezcla = os.path.join(raiz, "EMPRESA_MEZCLA")
        crear_codigo(carpeta_mezcla, "COD0001A.DAT", proveedores_x, "20200115")
        crear_codigo(carpeta_mezcla, "COD0002A.DAT", proveedores_y, "20210220")

        # --- Carpeta SANA: dos codigos, MISMOS proveedores (misma empresa) --
        proveedores_z = [cif_valido("B", 7000000 + k) for k in range(6)]
        carpeta_sana = os.path.join(raiz, "EMPRESA_SANA")
        crear_codigo(carpeta_sana, "COD0003A.DAT", proveedores_z, "20190510")
        crear_codigo(carpeta_sana, "COD0004A.DAT", proveedores_z, "20220815")

        r = calcular_sospechosas(raiz, min_nifs=3, max_difusion=0.30)

        comprobar("4 contenedores procesados", r["n_dats"] == 4, r["n_dats"])
        comprobar("2 carpetas analizadas", r["n_carpetas"] == 2, r["n_carpetas"])
        comprobar("2 carpetas con senal suficiente para medir",
                  r["n_carpetas_con_senal"] == 2, r["n_carpetas_con_senal"])

        detalle = r["n_grupos_por_carpeta_real"]
        comprobar("caso 1: EMPRESA_MEZCLA sale con 2 grupos (SOSPECHOSA)",
                  detalle.get("EMPRESA_MEZCLA") == 2, detalle.get("EMPRESA_MEZCLA"))
        comprobar("caso 2: EMPRESA_SANA sale con 1 grupo (sana, sin falso "
                  "positivo)",
                  detalle.get("EMPRESA_SANA") == 1, detalle.get("EMPRESA_SANA"))
        comprobar("el recuento agregado coincide: 1 carpeta sospechosa de 2",
                  r["sospechosas"] == 1, r["sospechosas"])

        # --- Fichero de detalle: nombres reales, marca correcta --------------
        ruta_detalle = os.path.join(tmp, "detalle_LOCAL.txt")
        n_sosp = escribir_detalle_multiempresa(detalle, ruta_detalle)
        comprobar("escribir_detalle_multiempresa devuelve 1 sospechosa",
                  n_sosp == 1, n_sosp)
        with open(ruta_detalle, encoding="utf-8") as f:
            texto = f.read()
        comprobar("caso 3: el detalle marca EMPRESA_MEZCLA como SOSPECHOSA",
                  "[SOSPECHOSA] 2 grupo(s)" in texto and "EMPRESA_MEZCLA" in texto)
        comprobar("caso 3: el detalle marca EMPRESA_SANA como sana, NO "
                  "sospechosa",
                  "EMPRESA_SANA" in texto
                  and "[sana      ] 1 grupo(s)" in texto)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. calcular_sospechosas() distingue mezcla de sana "
          "sin falsos positivos, y el detalle solo nombra lo que hace falta.")


if __name__ == "__main__":
    main()
