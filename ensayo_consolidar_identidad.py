#!/usr/bin/env python3
"""ensayo_consolidar_identidad.py — ensayo en seco de consolidar_identidad.py.

QUE PRUEBA, Y POR QUE ES EL CASO QUE IMPORTA
-------------------------------------------------
El valor real de `consolidar_identidad.py` no es repetir lo que ya hacian
`emparejar_carpetas.py`, `enlazador_clientes_303.py` o
`diag_carpetas_multiempresa.py` por separado -- es ver algo que NINGUNO de
los tres, mirando solo su propia senal, puede ver:

  Dos carpetas de ContaPlus con NOMBRES distintos ("ALFA SERVICIOS SL" y
  "BETA MANTENIMIENTO SL") se agrupan como la MISMA empresa real porque
  comparten proveedores (senal de `enlazador_clientes_303.py`). Pero cada
  una, mirada solo por nombre, empareja con una carpeta de Documentos
  DISTINTA y con alta confianza cada una. `emparejar_carpetas.py` solo, sin
  saber de la agrupacion, nunca marcaria esto como sospechoso -- las dos
  parecen coincidencias limpias. Es exactamente el tipo de discrepancia que
  merece que Diego la mire dos veces, y este ensayo fija en codigo que el
  cruce la detecta.

Ademas prueba, con el mismo corpus, que una carpeta sin aviso ninguno
(nombre en confianza alta, sin hermanas, sin mezcla) no genera ruido, y que
una carpeta que mezcla dos empresas reales (`diag_carpetas_multiempresa.py`)
se marca SOSPECHOSA con independencia de lo bien que empareje por nombre.

REGLA DE DATOS: todo inventado -- razones sociales genericas, NIF con
checksum valido pero ficticios, directorio temporal borrado al terminar.

Uso:
    python ensayo_consolidar_identidad.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

from ensayo_retro_semaforo import escribir_dbf, dni_valido, cif_valido
from consolidar_identidad import consolidar, escribir_consolidado

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
    print("ENSAYO EN SECO: consolidar_identidad.py")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_consolidar_")
    try:
        cp = os.path.join(tmp, "contaplus")
        doc = os.path.join(tmp, "documentos")
        os.makedirs(doc, exist_ok=True)

        # --- ALFA / BETA: MISMA empresa por proveedor, nombres DISTINTOS ----
        # el caso que ninguna senal por separado puede ver.
        proveedores_alfa_beta = [cif_valido("B", 1000000 + k) for k in range(6)]
        crear_codigo(os.path.join(cp, "ALFA SERVICIOS SL"), "SPALFA_A.DAT",
                     proveedores_alfa_beta, "20190310")
        crear_codigo(os.path.join(cp, "BETA MANTENIMIENTO SL"), "SPBETA_A.DAT",
                     proveedores_alfa_beta, "20220715")

        # --- GAMMA: empresa normal, sin hermanas, sin mezcla, nombre claro --
        proveedores_gamma = [dni_valido(20000000 + k) for k in range(6)]
        crear_codigo(os.path.join(cp, "GAMMA CONSULTING SL"), "SPGAMA_A.DAT",
                     proveedores_gamma, "20210101")

        # --- DELTA: una sola carpeta, DOS codigos, proveedores SIN solape --
        # (mezcla dos empresas reales bajo la misma carpeta).
        proveedores_delta1 = [cif_valido("B", 3000000 + k) for k in range(6)]
        proveedores_delta2 = [dni_valido(40000000 + k) for k in range(6)]
        carpeta_delta = os.path.join(cp, "DELTA MIXTA")
        crear_codigo(carpeta_delta, "SPDEL1_A.DAT", proveedores_delta1, "20180505")
        crear_codigo(carpeta_delta, "SPDEL2_A.DAT", proveedores_delta2, "20230920")

        # --- EPSILON: nombre de EQUIPO/COPIA, tambien mezcla dos empresas --
        # (para probar la rama "corroborada por el nombre" de la calibracion).
        proveedores_eps1 = [cif_valido("B", 6000000 + k) for k in range(6)]
        proveedores_eps2 = [dni_valido(70000000 + k) for k in range(6)]
        carpeta_epsilon = os.path.join(cp, "COPIA BACKUP EQUIPO 3")
        crear_codigo(carpeta_epsilon, "SPEPS1_A.DAT", proveedores_eps1, "20170101")
        crear_codigo(carpeta_epsilon, "SPEPS2_A.DAT", proveedores_eps2, "20240101")

        # --- Documentos: un candidato claro para cada uno -------------------
        # NOTA: Windows recorta un punto final al crear una carpeta ("S.L."
        # se guarda como "S.L") -- por eso las comprobaciones de abajo leen
        # el nombre real ya creado en vez de dar por buena la cadena que se
        # pidio crear, para que el ensayo sea correcto en cualquier SO.
        for nombre in ("Alfa Servicios, S.L.", "Beta Mantenimiento, S.L.",
                       "Gamma Consulting, S.L.", "Otra Empresa Sin Relacion SL"):
            os.makedirs(os.path.join(doc, nombre), exist_ok=True)
        doc_real = {n.split(",")[0]: n for n in os.listdir(doc)}
        doc_alfa = doc_real["Alfa Servicios"]
        doc_beta = doc_real["Beta Mantenimiento"]
        doc_gamma = doc_real["Gamma Consulting"]

        stats, filas = consolidar(cp, doc, max_difusion=0.30, min_nifs=3)

        comprobar("5 carpetas de ContaPlus vistas (ALFA, BETA, GAMMA, DELTA, "
                  "EPSILON)", stats["n_carpetas_cp"] == 5, stats["n_carpetas_cp"])

        # --- El caso que importa: discrepancia entre hermanas ---------------
        comprobar("2 carpetas en grupo multi-carpeta (ALFA + BETA)",
                  stats["n_con_hermanas"] == 2, stats["n_con_hermanas"])
        comprobar("caso clave: las 2 carpetas del grupo se marcan con "
                  "DISCREPANCIA (candidato de nombre distinto entre "
                  "hermanas, pese a ser -segun proveedores- la misma "
                  "empresa)",
                  stats["n_discrepancia"] == 2, stats["n_discrepancia"])

        fila_alfa = next(f for f in filas if f["carpeta"] == "ALFA SERVICIOS SL")
        fila_beta = next(f for f in filas if f["carpeta"] == "BETA MANTENIMIENTO SL")
        comprobar("ALFA elige 'Alfa Servicios' por nombre",
                  fila_alfa["top3"][0][1] == doc_alfa, fila_alfa["top3"][0])
        comprobar("BETA elige 'Beta Mantenimiento' por nombre (candidato "
                  "DISTINTO al de su hermana ALFA)",
                  fila_beta["top3"][0][1] == doc_beta, fila_beta["top3"][0])
        comprobar("ambas quedan marcadas discrepancia=True",
                  fila_alfa["discrepancia"] and fila_beta["discrepancia"])

        # --- Carpeta sana, sin ningun aviso ----------------------------------
        fila_gamma = next(f for f in filas if f["carpeta"] == "GAMMA CONSULTING SL")
        comprobar("GAMMA no tiene hermanas ni esta marcada sospechosa",
                  not fila_gamma["hermanas"] and not fila_gamma["sospechosa"])
        comprobar("GAMMA elige su candidato correcto por nombre",
                  fila_gamma["top3"][0][1] == doc_gamma, fila_gamma["top3"][0])
        comprobar("GAMMA cuenta en 'confianza alta sin aviso'",
                  stats["n_alta_sin_aviso"] >= 1, stats["n_alta_sin_aviso"])

        # --- Carpeta que mezcla dos empresas ---------------------------------
        fila_delta = next(f for f in filas if f["carpeta"] == "DELTA MIXTA")
        comprobar("DELTA MIXTA se marca SOSPECHOSA (mezcla de empresas)",
                  fila_delta["sospechosa"], fila_delta)
        comprobar("DELTA MIXTA no suena a equipo por el nombre -> sospechosa "
                  "SIN corroborar (posible artefacto, no descartar la carpeta "
                  "sin mirarla)",
                  not fila_delta["nombre_sugiere_equipo"], fila_delta)

        fila_epsilon = next(f for f in filas if f["carpeta"] == "COPIA BACKUP EQUIPO 3")
        comprobar("EPSILON (nombre 'copia'/'backup'/'equipo') tambien se "
                  "marca sospechosa", fila_epsilon["sospechosa"], fila_epsilon)
        comprobar("EPSILON SI suena a equipo por el nombre -> sospechosa "
                  "CORROBORADA",
                  fila_epsilon["nombre_sugiere_equipo"], fila_epsilon)

        comprobar("el recuento agregado: 1 corroborada (EPSILON), 1 sin "
                  "corroborar (DELTA)",
                  stats["n_sospechosa_corroborada"] == 1
                  and stats["n_sospechosa_sin_corroborar"] == 1,
                  (stats["n_sospechosa_corroborada"], stats["n_sospechosa_sin_corroborar"]))

        # --- Fichero de detalle: orden de prioridad y marcas correctas ------
        ruta_detalle = os.path.join(tmp, "detalle_LOCAL.txt")
        escribir_consolidado(filas, ruta_detalle)
        with open(ruta_detalle, encoding="utf-8") as f:
            texto = f.read()
        comprobar("el detalle marca DISCREPANCIA en el bloque de ALFA",
                  "ALFA SERVICIOS SL'  <<< DISCREPANCIA" in texto
                  or ("'ALFA SERVICIOS SL'" in texto and "DISCREPANCIA" in
                      texto.split("'ALFA SERVICIOS SL'")[1].split("ContaPlus:")[0]))
        comprobar("el detalle marca SOSPECHOSA en el bloque de DELTA MIXTA",
                  "'DELTA MIXTA'" in texto and "SOSPECHOSA" in
                  texto.split("'DELTA MIXTA'")[1].split("ContaPlus:")[0])
        comprobar("GAMMA CONSULTING SL aparece en el detalle SIN ningun "
                  "aviso (<<<)",
                  "'GAMMA CONSULTING SL'" in texto and "<<<" not in
                  texto.split("'GAMMA CONSULTING SL'")[1].split("ContaPlus:")[0])

        # --- Console: main() vía subprocess -- solo numeros, nunca nombres --
        r = subprocess.run(
            [sys.executable, os.path.join(AQUI, "consolidar_identidad.py"),
             cp, doc, "--detalle", os.path.join(tmp, "detalle2_LOCAL.txt")],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        comprobar("el script corre sin error desde la linea de comandos",
                  r.returncode == 0, r.stderr[-500:])
        salida = r.stdout
        for fragmento in ("ALFA", "BETA", "GAMMA", "DELTA", "EPSILON", "Servicios",
                           "Mantenimiento", "Consulting"):
            comprobar(f"por consola NO aparece '{fragmento}'",
                      fragmento not in salida, salida)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. El cruce detecta lo que ninguna senal por "
          "separado podia ver, sin imprimir un solo nombre por consola.")


if __name__ == "__main__":
    main()
