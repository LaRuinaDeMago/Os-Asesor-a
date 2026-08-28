#!/usr/bin/env python3
"""ensayo_validar_captura_historica.py — ensayo en seco de
validar_captura_historica.py.

POR QUE HACE FALTA, Y POR QUE AHORA
---------------------------------------
Esta herramienta calcula "el numero que decide el proyecto" (EMPEZAR_AQUI.md
§2): la tasa de acierto y los falsos verdes contra facturas reales. Pese a
eso, hasta hoy **no tenia ningun ensayo propio en el repositorio** -- solo
comentarios en su cabecera documentando dos bugs P0/P1 ya corregidos a mano
(el "0.0% miente" del separador, la deteccion de columnas). Un instrumento
sin ensayo, que ademas ya demostro dos veces que puede mentir en silencio,
no deberia ejecutarse contra el corpus real por primera vez sin uno.

QUE PRUEBA
------------
1. REGRESION del bug P0 (21-08-2026): un CSV con separador incorrecto (o
   ilegible) no debe imprimir "0.0%" ni "FALSOS VERDES: 0" -- debe declarar
   que no puede calcular nada.
2. La acumulacion incremental de historico_proveedor A TRAVES DE ESTE SCRIPT
   (arreglo de Diego del 27-08-2026, `motor_veredicto.actualizar_caches_
   historicas()` -- probado en `test_motor_veredicto.py` a nivel de funcion,
   pero nunca de punta a punta contra este script en concreto). Cuatro
   facturas normales del mismo proveedor + una quinta con un importe
   disparatado deben producir AMBAR (importe_atipico=FALLO) en la quinta,
   nunca en las cuatro primeras.
3. NUEVO (28-08-2026): ORDEN CRONOLOGICO, no de fichero. El arreglo del
   27-08 acumula en el orden en que llegan las filas -- correcto para
   retro_semaforo.py (los asientos de ContaPlus vienen en orden de ASIEN,
   cronologico por construccion), pero un CSV de captura no tiene esa
   garantia. Aqui la factura disparatada se coloca la PRIMERA en el CSV
   (fila 0) pero con la fecha MAS TARDIA. Si el script acumulase por orden
   de fichero en vez de por fecha, la fila 0 se evaluaria SIN historico (no
   se detectaria) y las demas nunca verian la disparatada (fecha posterior).
   El resultado correcto es el contrario: la fila 0 (disparatada, mas
   tardia) SI se detecta; las 4 anteriores en el tiempo, NO.

REGLA DE DATOS: todo inventado -- el NIF y el nombre de proveedor son el
mismo caso piloto ya usado en test_motor_veredicto.py, con checksum valido
pero ficticio. CSV en directorio temporal, borrado al terminar. Las dos
salidas que el script real escribe en la raiz del proyecto
(validacion_captura_agregado.json, validacion_captura_LOCAL.csv) se limpian
al terminar -- estan protegidas por .gitignore, pero no hace falta dejarlas.

Uso:
    python ensayo_validar_captura_historica.py
"""
import csv
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
SALIDA_AGREGADA = os.path.join(AQUI, "validacion_captura_agregado.json")
SALIDA_LOCAL = os.path.join(AQUI, "validacion_captura_LOCAL.csv")

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def ejecutar(ruta_csv, *args):
    r = subprocess.run(
        [sys.executable, os.path.join(AQUI, "validar_captura_historica.py"),
         ruta_csv, *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r


def limpiar_salidas():
    for ruta in (SALIDA_AGREGADA, SALIDA_LOCAL):
        if os.path.exists(ruta):
            os.remove(ruta)


NIF = "12345678Z"          # caso piloto, checksum valido, ya usado en test_motor_veredicto.py
PROVEEDOR = "PROVEEDOR PILOTO EJEMPLO"


def fila(total, fecha, doc):
    """Factura limpia (VERDE por si sola, sin proveedor nuevo/tipo raro):
    misma proporcion base/iva que el caso piloto ya validado (10%). Lleva
    'base_total' ademas de 'base_10' -- sin ella, integridad_datos la marca
    ausente y arrastra a NO_COMPROBADO todo lo que depende de ella (leccion
    de la primera version de este ensayo, que se equivocaba en esto mismo)."""
    base = round(total / 1.10, 2)
    iva = round(total - base, 2)
    return {"nif": NIF, "proveedor": PROVEEDOR, "fecha_expedicion": fecha,
            "nº_documento": doc, "base_10": f"{base:.2f}", "base_4": "0",
            "base_21": "0", "base_total": f"{base:.2f}",
            "iva_total": f"{iva:.2f}", "irpf_retencion": "0",
            "total_factura": f"{total:.2f}", "verificacion": "OK"}


def main():
    print("ENSAYO EN SECO: validar_captura_historica.py")
    print("=" * 70)

    tmp = tempfile.mkdtemp(prefix="ensayo_captura_hist_")
    try:
        # --- Caso 1: REGRESION del bug P0 (separador / CSV ilegible) --------
        # Cabecera y filas de una sola columna de verdad (sin ';', ',', tab
        # ni '|' en ningun sitio) -- el patron real: un CSV exportado con un
        # separador que este script no reconoce, o con una sola columna de
        # texto libre. csv.DictReader no revienta: produce UNA columna con
        # la linea entera dentro, y el bug original seguia adelante hasta
        # imprimir "TASA DE ACIERTO: 0.0%".
        csv_roto = os.path.join(tmp, "roto.csv")
        with open(csv_roto, "w", encoding="utf-8") as f:
            f.write("notas libres\n")
            f.write("factura de tal proveedor por tal importe sin estructura\n")
            f.write("otra linea de texto igual de libre que la anterior\n")
        try:
            limpiar_salidas()
            r = ejecutar(csv_roto)
            comprobar("caso 1 (REGRESION P0): CSV de una sola columna NO "
                      "imprime '0.0%'",
                      "0.0%" not in r.stdout, r.stdout)
            comprobar("caso 1: y lo dice explicitamente, no se queda callado",
                      "una sola columna" in r.stdout.lower(), r.stdout[:400])
            comprobar("caso 1: termina con codigo de error, no con exito",
                      r.returncode != 0, r.returncode)
        finally:
            limpiar_salidas()

        # --- Caso 2: acumulacion incremental + orden cronologico ------------
        # Fila 0 del FICHERO es la disparatada, con la fecha MAS TARDIA.
        # Filas 1-4 son normales, con fechas ANTERIORES, en orden.
        filas = [
            fila(5000.00, "2026-01-05", "F0005"),   # disparatada, ultima en el tiempo
            fila(146.19, "2026-01-01", "F0001"),
            fila(150.00, "2026-01-02", "F0002"),
            fila(140.00, "2026-01-03", "F0003"),
            fila(148.50, "2026-01-04", "F0004"),
        ]
        csv_normal = os.path.join(tmp, "normal.csv")
        with open(csv_normal, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)

        try:
            limpiar_salidas()
            r = ejecutar(csv_normal)
            comprobar("caso 2: el script corre sin error", r.returncode == 0,
                      r.stderr[-500:])
            salida = r.stdout
            comprobar("caso 2: 5 filas leidas", "filas leidas             : 5" in salida,
                      salida[:400])

            # El importe disparatado (5.000 frente a ~140-150 habituales) debe
            # marcar importe_atipico=FALLO EXACTAMENTE UNA VEZ -- la fila
            # cronologicamente ultima, nunca ninguna de las 4 anteriores.
            comprobar("caso 2 (clave): importe_atipico=FALLO aparece "
                      "EXACTAMENTE 1 vez (la disparatada, evaluada con "
                      "historico de las 4 normales -- prueba que la "
                      "acumulacion incremental SI funciona)",
                      "importe_atipico=FALLO" in salida
                      and salida.count("importe_atipico=FALLO") == 1, salida)
            comprobar("caso 2: exactamente 1 factura sale AMBAR (la "
                      "disparatada); las 4 normales, VERDE",
                      "AMBAR        1" in salida and "VERDE        4" in salida,
                      salida)
        finally:
            limpiar_salidas()

        # --- Caso 3: sin la disparatada, 4 facturas normales no se marcan ---
        # (control negativo: sin el importe atipico, importe_atipico nunca
        # deberia dar FALLO -- confirma que el caso 2 detecta algo real, no
        # ruido de otro guard).
        filas_control = [
            fila(146.19, "2026-01-01", "F0001"),
            fila(150.00, "2026-01-02", "F0002"),
            fila(140.00, "2026-01-03", "F0003"),
            fila(148.50, "2026-01-04", "F0004"),
        ]
        csv_control = os.path.join(tmp, "control.csv")
        with open(csv_control, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(filas_control[0].keys()))
            w.writeheader()
            w.writerows(filas_control)
        try:
            limpiar_salidas()
            r = ejecutar(csv_control)
            comprobar("caso 3 (control negativo): SIN la factura disparatada, "
                      "importe_atipico NUNCA da FALLO",
                      "importe_atipico=FALLO" not in r.stdout, r.stdout)
        finally:
            limpiar_salidas()

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        limpiar_salidas()

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. El separador roto se declara, no se miente con "
          "0.0%, y el historico se acumula por fecha, nunca por orden de "
          "fichero ni viendose una factura a si misma.")


if __name__ == "__main__":
    main()
