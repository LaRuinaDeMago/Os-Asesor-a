#!/usr/bin/env python3
"""ensayo_diag_calibracion_sospechosa.py — ensayo en seco de
diag_calibracion_sospechosa.py, incluido el veredicto automatico
`calcular_contingencia()['informativa']`.

QUE PRUEBA, Y POR QUE TRES ESCENARIOS
------------------------------------------
La primera version de este ensayo solo probaba el caso donde la hipotesis
"mezcla real" es cierta por construccion. Tras la primera ejecucion real
contra el corpus completo (Diego, 27-08-2026) salio el caso CONTRARIO: 100%
de sospechosas TAMBIEN entre las carpetas que no suenan a equipo (3 de 3) --
la firma exacta del artefacto de continuidad temporal, no de mezcla real.
`calcular_contingencia()` se amplio con un veredicto automatico
(`informativa`) para que la herramienta lo sepa por si sola, y este ensayo
fija los TRES resultados posibles en codigo:

  1. INFORMATIVA (True): la tasa entre "no suena a equipo" es baja -- la
     senal SOSPECHOSA distingue algo real.
  2. NO INFORMATIVA (False): la tasa entre "no suena a equipo" tambien es
     alta -- el caso real de hoy, reproducido aqui con datos sinteticos.
  3. NO_COMPROBADO (None): no hay ninguna carpeta de nombre "cliente
     concreto" con la que contrastar -- no se puede calibrar, y no se finge
     un veredicto que no se puede sostener (misma disciplina que
     motor_veredicto.py: nunca un OK ni un FALLO por omision).

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
from diag_calibracion_sospechosa import calcular_contingencia

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


def mezcla(carpeta_dir, semilla):
    """Dos codigos SIN solape de proveedores -- mezcla de verdad."""
    crear_codigo(carpeta_dir, "CODA0001.DAT",
                 [cif_valido("B", semilla + k) for k in range(6)], "20190101")
    crear_codigo(carpeta_dir, "CODB0001.DAT",
                 [dni_valido(semilla + 1000000 + k) for k in range(6)], "20220601")


def sana(carpeta_dir, semilla):
    """Dos codigos con los MISMOS proveedores -- una sola empresa."""
    proveedores = [cif_valido("B", semilla + k) for k in range(6)]
    crear_codigo(carpeta_dir, "CODC0001.DAT", proveedores, "20180101")
    crear_codigo(carpeta_dir, "CODD0001.DAT", proveedores, "20230101")


def calcular(raiz):
    r = calcular_sospechosas(raiz, min_nifs=3, max_difusion=0.30)
    return calcular_contingencia(r["n_grupos_por_carpeta_real"])


def main():
    print("ENSAYO EN SECO: diag_calibracion_sospechosa.py")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_calibracion_")
    try:
        # --- Escenario 1: la hipotesis "mezcla real" es cierta -----------
        raiz1 = os.path.join(tmp, "informativa")
        mezcla(os.path.join(raiz1, "Contabilidad Ordenador Equipo0"), 1000000)
        mezcla(os.path.join(raiz1, "Contabilidad Ordenador Equipo1"), 1100000)
        sana(os.path.join(raiz1, "CLIENTE CONCRETO 0"), 5000000)
        sana(os.path.join(raiz1, "CLIENTE CONCRETO 1"), 5100000)
        c1 = calcular(raiz1)
        comprobar("escenario 1: tasa 100% entre equipo, 0% entre cliente",
                  c1["tasa_equipo"] == 1.0 and c1["tasa_no_equipo"] == 0.0,
                  (c1["tasa_equipo"], c1["tasa_no_equipo"]))
        comprobar("escenario 1: veredicto INFORMATIVA (True)",
                  c1["informativa"] is True, c1["informativa"])

        # --- Escenario 2: el caso real de hoy -- saturado en los dos lados -
        raiz2 = os.path.join(tmp, "saturada")
        mezcla(os.path.join(raiz2, "Contabilidad Ordenador Equipo0"), 2000000)
        mezcla(os.path.join(raiz2, "Contabilidad Ordenador Equipo1"), 2100000)
        mezcla(os.path.join(raiz2, "CLIENTE CONCRETO 0"), 6000000)
        mezcla(os.path.join(raiz2, "CLIENTE CONCRETO 1"), 6100000)
        c2 = calcular(raiz2)
        comprobar("escenario 2: tasa 100% en los DOS lados (reproduce el "
                  "resultado real de hoy)",
                  c2["tasa_equipo"] == 1.0 and c2["tasa_no_equipo"] == 1.0,
                  (c2["tasa_equipo"], c2["tasa_no_equipo"]))
        comprobar("escenario 2: veredicto NO INFORMATIVA (False) -- no se "
                  "confunde una tasa alta con una senal real",
                  c2["informativa"] is False, c2["informativa"])

        # --- Escenario 3: sin carpetas "cliente" con las que contrastar ----
        raiz3 = os.path.join(tmp, "sin_contraste")
        mezcla(os.path.join(raiz3, "Contabilidad Ordenador Equipo0"), 3000000)
        mezcla(os.path.join(raiz3, "Copia Backup Equipo1"), 3100000)
        c3 = calcular(raiz3)
        comprobar("escenario 3: sin carpetas 'cliente concreto' con las que "
                  "contrastar", c3["tasa_no_equipo"] is None, c3["tasa_no_equipo"])
        comprobar("escenario 3: veredicto NO_COMPROBADO (None) -- no finge un "
                  "resultado que no se puede sostener",
                  c3["informativa"] is None, c3["informativa"])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. calcular_contingencia() distingue mezcla real de "
          "artefacto, y sabe decir NO_COMPROBADO cuando no puede calibrar.")


if __name__ == "__main__":
    main()
