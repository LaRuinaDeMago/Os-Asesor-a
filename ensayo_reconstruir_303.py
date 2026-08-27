#!/usr/bin/env python3
"""ensayo_reconstruir_303.py — ensayo en seco de la derivacion de base por
asiento en reconstruir_303.py.

POR QUE HACE FALTA UN ENSAYO PROPIO, ADEMAS DEL DE ensayo_retro_semaforo.py
------------------------------------------------------------------------------
`ensayo_retro_semaforo.py` prueba que `reconstruir_303.py` corre de punta a
punta contra un corpus con UN asiento simple por factura (una linea de IVA,
un tipo). Eso basta para probar la fontaneria, pero NO ejercita los tres
casos que de verdad ponen a prueba la derivacion de base escrita el
27-08-2026:

  1. Varios tipos de IVA en el MISMO asiento (reparto proporcional
     reescalado, la parte mas delicada de `derivar_bases_por_tipo`).
  2. BASEIMPO genuinamente relleno (el 0,6% real): tiene que usarse tal
     cual, NO derivarse del gasto/ingreso.
  3. El mismo asiento repetido en dos "copias" (deduplicacion por asiento
     completo, no por linea suelta): tiene que contarse UNA sola vez.

Sin esto, un cambio futuro en `derivar_bases_por_tipo` podria romper
cualquiera de los tres casos y ningun ensayo lo notaria hasta la proxima
ejecucion real -- la misma leccion de "verde en el ensayo, roto en el mundo
real" que esta sesion lleva persiguiendo todo el dia.

REGLA DE DATOS: todo inventado, corpus en directorio temporal, borrado al
terminar. Ningun .DAT toca el repositorio.

Uso:
    python ensayo_reconstruir_303.py
"""
import os
import shutil
import sys
import tempfile
import zipfile
from collections import Counter

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ensayo_retro_semaforo import escribir_dbf
import reconstruir_303 as r303

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def empaquetar(carpeta, nombre_dat, filas):
    """Un Diario.dbf con `filas` dentro de un .DAT (ZIP), como ContaPlus."""
    os.makedirs(carpeta, exist_ok=True)
    dbf = os.path.join(carpeta, "Diario.dbf")
    escribir_dbf(dbf, filas)
    with zipfile.ZipFile(os.path.join(carpeta, nombre_dat), "w") as z:
        z.write(dbf, "Diario.dbf")
    os.remove(dbf)


def leer(raiz):
    acumulado = r303.nuevo_acumulado()
    incidencias = Counter()
    vistos = set()
    dats = sorted(os.path.join(dp, n) for dp, _, fns in os.walk(raiz)
                  for n in fns if n.lower().endswith(".dat"))
    for ruta in dats:
        r303.acumular(ruta, acumulado, incidencias, vistos)
    datos = r303.a_json(acumulado)
    return datos, incidencias


def main():
    print("ENSAYO EN SECO: derivacion de base por asiento en reconstruir_303.py")
    print("=" * 72)

    tmp = tempfile.mkdtemp(prefix="ensayo_r303_")
    try:
        raiz = os.path.join(tmp, "corpus")

        # --- CASO 1: un solo tipo de IVA, BASEIMPO a 0 (el caso real, 99,4%) ---
        # base=1000, tipo 21% -> cuota=210. La base NO viene en BASEIMPO: debe
        # derivarse de la cuenta de gasto (600000, DEBE=1000).
        filas_1 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 1000.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 210.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 1210.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_UNO"), "COPIA_A.DAT", filas_1)

        # --- CASO 2: BASEIMPO genuinamente relleno (el 0,6% real) ---------------
        # Si BASEIMPO trae un valor y el gasto trae OTRO, tiene que ganar
        # BASEIMPO -- es el dato mas directo cuando existe de verdad.
        filas_2 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 999999.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220615", "DOCUMENTO": "F2"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 105.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 500.0, "FECHA": "20220615", "DOCUMENTO": "F2"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 999999.0 + 105,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220615", "DOCUMENTO": "F2"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_DOS"), "COPIA_A.DAT", filas_2)

        # --- CASO 3: multi-tipo en el MISMO asiento -----------------------------
        # Un asiento con dos tipos de IVA (21% y 10%). BASEIMPO a 0 en los dos.
        # gasto total = 1000 (600) + 500 (601) = 1500. La suma derivada tiene
        # que ser EXACTA (reescalada), no solo aproximada.
        filas_3 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 1000.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "601000", "EURODEBE": 500.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 210.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 50.0, "EUROHABER": 0,
             "IVA": 10, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 1760.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_TRES"), "COPIA_A.DAT", filas_3)

        # --- CASO 4: venta (repercutido, 477) desde el ingreso (7xx) ------------
        filas_4 = [
            {"ASIEN": 1, "SUBCTA": "430000", "EURODEBE": 1210.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "V1"},
            {"ASIEN": 1, "SUBCTA": "700000", "EURODEBE": 0, "EUROHABER": 1000.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "V1"},
            {"ASIEN": 1, "SUBCTA": "477021", "EURODEBE": 0, "EUROHABER": 210.0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "V1"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_CUATRO"), "COPIA_A.DAT", filas_4)

        # --- CASO 5: el asiento 1 de CLIENTE_UNO, REPETIDO en una "copia" -------
        # Misma carpeta de cliente, segundo contenedor con el MISMO asiento
        # (bytes identicos): tiene que deduplicarse y NO sumarse dos veces.
        empaquetar(os.path.join(raiz, "CLIENTE_UNO"), "COPIA_B.DAT", filas_1)

        datos, incidencias = leer(raiz)

        # --- Verificaciones ------------------------------------------------
        c1 = datos.get("CLIENTE_UNO", {}).get("2022T1", {}).get("deducible", {}).get("21", {})
        comprobar("caso 1 (BASEIMPO=0): base derivada del gasto = 1000,00",
                  c1.get("base") == 1000.0, c1)
        comprobar("caso 1: cuota = 210,00 (directa, nunca se deriva)",
                  c1.get("cuota") == 210.0, c1)
        comprobar("caso 1: 1 apunte (no 2, por la deduplicacion del caso 5)",
                  c1.get("apuntes") == 1, c1)

        c2 = datos.get("CLIENTE_DOS", {}).get("2022T2", {}).get("deducible", {}).get("21", {})
        comprobar("caso 2 (BASEIMPO=500 relleno): GANA BASEIMPO, no el gasto",
                  c2.get("base") == 500.0, c2)

        c3d = datos.get("CLIENTE_TRES", {}).get("2022T3", {}).get("deducible", {})
        b21, b10 = c3d.get("21", {}).get("base"), c3d.get("10", {}).get("base")
        comprobar("caso 3 (multi-tipo): la suma de las bases derivadas es EXACTA",
                  b21 is not None and b10 is not None
                  and round(b21 + b10, 2) == 1500.0,
                  f"21%={b21} 10%={b10} suma={round((b21 or 0) + (b10 or 0), 2)}")
        comprobar("caso 3: el tipo mayoritario (21%) se lleva el resto del redondeo",
                  b21 is not None and abs(b21 - 1000.0) < 1.0, b21)

        c4 = datos.get("CLIENTE_CUATRO", {}).get("2022T4", {}).get("devengado", {}).get("21", {})
        comprobar("caso 4 (venta, 477): base derivada del INGRESO (7xx) = 1000,00",
                  c4.get("base") == 1000.0, c4)

        comprobar("caso 5: el asiento duplicado SE CUENTA (no se pierde en silencio)",
                  incidencias.get("duplicado entre copias de seguridad", 0) >= 1,
                  dict(incidencias))

        # --- Coherencia global: cada celda cuadra base*tipo/100 = cuota --------
        descuadres = []
        for cli, tris in datos.items():
            for tri, lados in tris.items():
                for lado, celdas in lados.items():
                    for tipo, v in celdas.items():
                        if not tipo.isdigit() or int(tipo) == 0:
                            continue
                        esperada = round(v["base"] * int(tipo) / 100.0, 2)
                        if abs(esperada - v["cuota"]) > 0.02:
                            descuadres.append((cli, tri, lado, tipo, v["cuota"], esperada))
        comprobar("todas las celdas cuadran: base x tipo = cuota",
                  not descuadres, descuadres[:3])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 72)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. La derivacion de base por asiento hace lo que dice.")


if __name__ == "__main__":
    main()
