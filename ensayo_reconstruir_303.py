#!/usr/bin/env python3
"""ensayo_reconstruir_303.py — ensayo en seco de la derivacion de base por
tipo en reconstruir_303.py.

POR QUE HACE FALTA UN ENSAYO PROPIO, ADEMAS DEL DE ensayo_retro_semaforo.py
------------------------------------------------------------------------------
`ensayo_retro_semaforo.py` prueba que `reconstruir_303.py` corre de punta a
punta contra un corpus con UN asiento simple por factura (una linea de IVA,
un tipo, sin ningun conflicto entre gasto y cuota). Eso basta para probar la
fontaneria, pero NO ejercita los casos que de verdad importan.

DOS VERSIONES EN UN MISMO DIA, Y POR QUE
-------------------------------------------
Primera version (mañana del 27-08): copiaba la logica de
`retro_semaforo.reconstruir_compra()` -- derivar la base del gasto/ingreso
contable del asiento. Mejoro el bug del 26-08 (BASEIMPO=0) pero, medido
contra el corpus real, dejo una coherencia (base*tipo=cuota) del 64,9% que
EMPEORABA con el tamaño de la celda -- sesgo sistematico, no ruido.
Investigado con `diag_rescalado_multitipo.py`: el reescalado multi-tipo no
era la causa (88,6% sin sesgo). La causa real: un 303 se rige por
`base = cuota / tipo`, no por lo contabilizado a gasto -- esa formula es
correcta para lo que hace retro_semaforo.py (comparar contra el patron
historico), no para reconstruir una casilla fiscal.

Los casos de aqui prueban la version DEFINITIVA (cuota/tipo, sin mirar
gasto/ingreso salvo para nada), y estan diseñados a proposito para que el
gasto/ingreso contable NO COINCIDA con lo que implica la cuota -- si algun
cambio futuro reintrodujera la derivacion desde el gasto, estos casos lo
cazarian inmediatamente, porque las cifras esperadas SOLO salen bien con la
formula correcta.

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
    print("ENSAYO EN SECO: derivacion de base por tipo en reconstruir_303.py")
    print("=" * 72)

    tmp = tempfile.mkdtemp(prefix="ensayo_r303_")
    try:
        raiz = os.path.join(tmp, "corpus")

        # --- CASO 1: BASEIMPO=0, y el GASTO NO COINCIDE con cuota/tipo -----
        # base=1000 al 21% -> cuota=210. Pero el gasto contabilizado es 1300
        # (300 de mas: un concepto no deducible mezclado en la misma cuenta,
        # el caso real que explico el 64,9%). Si el codigo mirase el gasto,
        # daria 1300; la formula correcta da 1000.
        filas_1 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 1300.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 210.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 1510.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220315", "DOCUMENTO": "F1"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_UNO"), "COPIA_A.DAT", filas_1)

        # --- CASO 2: BASEIMPO genuinamente relleno (el 0,6% real) ---------------
        # Tiene que GANAR sobre cuota/tipo Y sobre el gasto, los dos distintos.
        filas_2 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 999999.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220615", "DOCUMENTO": "F2"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 105.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 500.0, "FECHA": "20220615", "DOCUMENTO": "F2"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 999999.0 + 105,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220615", "DOCUMENTO": "F2"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_DOS"), "COPIA_A.DAT", filas_2)

        # --- CASO 3: multi-tipo, con gasto que NO coincide con la suma ----------
        # 21%: cuota=210 -> base=1000.  10%: cuota=50 -> base=500.  Suma=1500.
        # El gasto contabilizado es 1700 (200 de mas). Con la formula vieja
        # (reescalado a gasto), las bases habrian salido 1133,33 y 566,67.
        # Con la correcta, cada tipo sale EXACTO por separado: 1000 y 500,
        # SIN que la suma tenga que cuadrar con el gasto.
        filas_3 = [
            {"ASIEN": 1, "SUBCTA": "600000", "EURODEBE": 1700.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 210.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 50.0, "EUROHABER": 0,
             "IVA": 10, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 1960.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20220915", "DOCUMENTO": "F3"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_TRES"), "COPIA_A.DAT", filas_3)

        # --- CASO 4: ISP -- una linea 477 SIN ninguna venta (7xx) detras --------
        # Es la razon de fondo del segundo arreglo: una autorrepercusion es una
        # COMPRA, no lleva ingreso. Con la version que derivaba del ingreso,
        # esto daba base=0 con cuota real. Con cuota/tipo, se deriva igual que
        # cualquier otra linea, sin necesitar detectar el caso ISP.
        filas_4 = [
            {"ASIEN": 1, "SUBCTA": "621000", "EURODEBE": 2000.0, "EUROHABER": 0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "ISP1"},
            {"ASIEN": 1, "SUBCTA": "472000", "EURODEBE": 420.0, "EUROHABER": 0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "ISP1"},
            {"ASIEN": 1, "SUBCTA": "477000", "EURODEBE": 0, "EUROHABER": 420.0,
             "IVA": 21, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "ISP1"},
            {"ASIEN": 1, "SUBCTA": "400000", "EURODEBE": 0, "EUROHABER": 2000.0,
             "IVA": 0, "TERNIF": "", "BASEIMPO": 0, "FECHA": "20221215", "DOCUMENTO": "ISP1"},
        ]
        empaquetar(os.path.join(raiz, "CLIENTE_CUATRO"), "COPIA_A.DAT", filas_4)

        # --- CASO 5: el asiento 1 de CLIENTE_UNO, REPETIDO en una "copia" -------
        empaquetar(os.path.join(raiz, "CLIENTE_UNO"), "COPIA_B.DAT", filas_1)

        datos, incidencias = leer(raiz)

        # --- Verificaciones ------------------------------------------------
        # ANADIDO 28-08-2026: clave_cliente() ya no es solo el nombre de la
        # carpeta -- es "carpeta::codigo", donde el codigo son los 7 primeros
        # caracteres del nombre del fichero .DAT (hallazgo de Diego,
        # verificado contra FASE0_RESULTADOS.md §12). Cada caso sintetico de
        # aqui usa "COPIA_A.DAT" como unico contenedor de datos, asi que su
        # clave real es "<CARPETA>::COPIA_A".
        c1 = datos.get("CLIENTE_UNO::COPIA_A", {}).get("2022T1", {}).get("deducible", {}).get("21", {})
        comprobar("caso 1: base = cuota/tipo = 1000,00 (NO el gasto, que es 1300)",
                  c1.get("base") == 1000.0, c1)
        comprobar("caso 1: cuota = 210,00 (directa, nunca se deriva)",
                  c1.get("cuota") == 210.0, c1)
        comprobar("caso 1: 1 apunte (no 2, por la deduplicacion del caso 5)",
                  c1.get("apuntes") == 1, c1)

        c2 = datos.get("CLIENTE_DOS::COPIA_A", {}).get("2022T2", {}).get("deducible", {}).get("21", {})
        comprobar("caso 2 (BASEIMPO=500 relleno): GANA sobre cuota/tipo y sobre el gasto",
                  c2.get("base") == 500.0, c2)

        c3d = datos.get("CLIENTE_TRES::COPIA_A", {}).get("2022T3", {}).get("deducible", {})
        b21, b10 = c3d.get("21", {}).get("base"), c3d.get("10", {}).get("base")
        comprobar("caso 3 (multi-tipo): 21% = 1000,00 exacto, SIN reescalar al gasto (1700)",
                  b21 == 1000.0, b21)
        comprobar("caso 3 (multi-tipo): 10% = 500,00 exacto, SIN reescalar al gasto",
                  b10 == 500.0, b10)

        c4d = datos.get("CLIENTE_CUATRO::COPIA_A", {}).get("2022T4", {}).get("deducible", {}).get("21", {})
        c4v = datos.get("CLIENTE_CUATRO::COPIA_A", {}).get("2022T4", {}).get("devengado", {}).get("21", {})
        comprobar("caso 4 (ISP, lado deducible): base = 2000,00 desde cuota/tipo",
                  c4d.get("base") == 2000.0, c4d)
        comprobar("caso 4 (ISP, lado devengado, SIN venta 7xx detras): "
                  "base = 2000,00, NO cero",
                  c4v.get("base") == 2000.0, c4v)

        comprobar("caso 5: el asiento duplicado SE CUENTA (no se pierde en silencio)",
                  incidencias.get("duplicado entre copias de seguridad", 0) >= 1,
                  dict(incidencias))

        # --- Coherencia global: cada celda cuadra base*tipo/100 = cuota --------
        # Con la formula correcta, esto tiene que ser SIEMPRE exacto -- es la
        # comprobacion que demuestra que ya no hace falta ningun reescalado.
        descuadres = []
        for cli, tris in datos.items():
            for tri, lados in tris.items():
                for lado, celdas in lados.items():
                    for tipo, v in celdas.items():
                        if not tipo.isdigit() or int(tipo) == 0:
                            continue
                        esperada = round(v["base"] * int(tipo) / 100.0, 2)
                        if abs(esperada - v["cuota"]) > 0.01:
                            descuadres.append((cli, tri, lado, tipo, v["cuota"], esperada))
        comprobar("todas las celdas cuadran EXACTO: base x tipo = cuota",
                  not descuadres, descuadres[:3])

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("=" * 72)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. La derivacion de base por tipo hace lo que dice.")


if __name__ == "__main__":
    main()
