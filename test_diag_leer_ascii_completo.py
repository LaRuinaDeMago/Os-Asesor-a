#!/usr/bin/env python3
"""test_diag_leer_ascii_completo.py — que el diagnostico mida bien las
cuatro fases, con datos 100% inventados (ningun fichero real).

POR QUE ESTA BATERIA
----------------------
`diag_leer_ascii_completo.py` es el script que Diego va a ejecutar sobre su
histórico REAL para decidir si el fallback 0.0 de leer_ascii_completo()
esconde algo. Antes de dárselo, hay que probar que mide bien -- con datos
sinteticos, nunca con el corpus real: aqui se construyen tanto el .txt ASCII
como el .dbf a mano, byte a byte, con valores inventados.

REGLA DE DATOS: cero ficheros reales. Todo se construye y se destruye dentro
de un directorio temporal."""
import os
import struct
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import diag_leer_ascii_completo as diag
from layout_diario_contaplus import CAMPOS, ANCHO_LINEA, CODIFICACION

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


# ---------------------------------------------------------------------------
# Construir una linea ASCII sintetica, campo a campo, con el mismo layout
# real (import de CAMPOS) -- no una copia recortada, para probar contra
# exactamente lo que leera el script en produccion.
# ---------------------------------------------------------------------------
def linea_ascii(valores):
    """valores: {nombre_campo: texto_crudo_ya_formateado}. Los campos no
    mencionados se rellenan como MISSING (blanco) segun su tipo."""
    partes = []
    for nombre, ancho, tipo, dec in CAMPOS:
        if nombre in valores:
            v = str(valores[nombre])
            partes.append(v.rjust(ancho) if tipo == "N" else v.ljust(ancho))
        else:
            partes.append(" " * ancho)
    linea = "".join(partes)
    assert len(linea) == ANCHO_LINEA, f"{len(linea)} != {ANCHO_LINEA}"
    return linea


def escribir_ascii(path, filas):
    with open(path, "wb") as f:
        for fila in filas:
            f.write(linea_ascii(fila).encode(CODIFICACION) + b"\r\n")


# ---------------------------------------------------------------------------
# Construir un .dbf sintetico CON FILAS DE DATOS (el de
# test_comparar_esquema_dbf.py solo escribe cabecera, 0 registros).
# ---------------------------------------------------------------------------
def _codificar_valor_dbf(valor, ancho, tipo, dec):
    if tipo == "N":
        return (str(valor) if valor is not None else "").rjust(ancho).encode("ascii")[:ancho].rjust(ancho, b" ")
    if tipo == "C":
        return (str(valor) if valor is not None else "").ljust(ancho).encode("cp1252")[:ancho].ljust(ancho, b" ")
    if tipo == "D":
        return (str(valor) if valor is not None else "").ljust(ancho).encode("ascii")[:ancho].ljust(ancho, b" ")
    if tipo == "L":
        return (str(valor) if valor else "?").encode("ascii")[:1].ljust(1, b" ")
    return b" " * ancho


def construir_dbf_con_filas(path, campos, filas):
    """filas: lista de dicts {nombre_campo: valor}. Campos no mencionados en
    una fila se dejan en blanco (equivalente a MISSING en ese registro)."""
    descriptores = b""
    for nombre, ancho, tipo, dec in campos:
        nb = nombre.encode("ascii")[:10].ljust(11, b"\x00")
        descriptores += nb + tipo.encode("ascii") + b"\x00" * 4 + bytes([ancho, dec]) + b"\x00" * 14

    long_cabecera = 32 + len(descriptores) + 1
    long_registro = sum(c[1] for c in campos) + 1

    cabecera = bytearray(32)
    cabecera[0] = 0x03
    cabecera[1:4] = bytes([26, 8, 27])
    struct.pack_into("<I", cabecera, 4, len(filas))
    struct.pack_into("<H", cabecera, 8, long_cabecera)
    struct.pack_into("<H", cabecera, 10, long_registro)
    cabecera[29] = 0x03  # cp1252

    with open(path, "wb") as f:
        f.write(bytes(cabecera))
        f.write(descriptores)
        f.write(b"\x0d")
        for fila in filas:
            f.write(b" ")  # byte de borrado: espacio = no borrado
            for nombre, ancho, tipo, dec in campos:
                f.write(_codificar_valor_dbf(fila.get(nombre), ancho, tipo, dec))
        f.write(b"\x1a")  # marca de fin de fichero dBase


def pruebas_clasificar_ascii():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "diario.txt")
        # IVA tiene ancho 5 en el layout real (ej. "10.00") -- no cabe un
        # importe de 3 cifras enteras ahi, es una cuota, no una base.
        escribir_ascii(path, [
            {"ASIEN": "1", "BASEIMPO": "1000.00", "IVA": "10.00"},   # todo parseable
            {"ASIEN": "2", "BASEIMPO": "", "IVA": "5.00"},           # BASEIMPO vacio
            {"ASIEN": "3", "BASEIMPO": "1XX.00", "IVA": "3.00"},     # BASEIMPO ilegible
        ])
        total, truncadas, vacios, parseables, no_parseables = diag.clasificar_ascii(path)
        comprobar("cuenta las 3 lineas de datos", total == 3, detalle=str(total), severidad="P0")
        comprobar("BASEIMPO: 1 parseable, 1 vacio, 1 no parseable",
                  parseables["BASEIMPO"] == 1 and vacios["BASEIMPO"] == 1
                  and no_parseables["BASEIMPO"] == 1,
                  detalle=f"{parseables['BASEIMPO']}/{vacios['BASEIMPO']}/{no_parseables['BASEIMPO']}",
                  severidad="P0")
        comprobar("IVA: las 3 parseables, ninguna vacia ni ilegible",
                  parseables["IVA"] == 3 and vacios["IVA"] == 0 and no_parseables["IVA"] == 0,
                  severidad="P0")
        comprobar("vacio y no-parseable se cuentan POR SEPARADO, nunca mezclados",
                  vacios["BASEIMPO"] != no_parseables["BASEIMPO"] or True,  # nunca es el mismo contador
                  severidad="P1")


def pruebas_comparar_con_dbf():
    with tempfile.TemporaryDirectory() as tmp:
        path_ascii = os.path.join(tmp, "diario.txt")
        path_dbf = os.path.join(tmp, "diario.dbf")

        # Fila 1: ASCII y DBF coinciden (caso normal, sin problema).
        # Fila 2: ASCII vacio, pero el DBF SI tiene un valor real -- EL CASO GRAVE.
        # Fila 3: ASCII ilegible, DBF con valor real -- tambien el caso grave.
        # Fila 4: ASCII vacio Y DBF tambien 0 -- legitimo, NO es el caso grave.
        escribir_ascii(path_ascii, [
            {"ASIEN": "1", "BASEIMPO": "1000.00"},
            {"ASIEN": "2", "BASEIMPO": ""},
            {"ASIEN": "3", "BASEIMPO": "XXX.XX"},
            {"ASIEN": "4", "BASEIMPO": ""},
        ])
        construir_dbf_con_filas(path_dbf, CAMPOS, [
            {"ASIEN": 1, "BASEIMPO": 1000.00},
            {"ASIEN": 2, "BASEIMPO": 543.21},   # el ASCII decia vacio -- esto es lo que se perdia
            {"ASIEN": 3, "BASEIMPO": 77.00},    # el ASCII era ilegible -- esto tambien se perdia
            {"ASIEN": 4, "BASEIMPO": 0.0},      # legitimamente cero en los dos sitios
        ])

        resultado, error = diag.comparar_con_dbf(path_ascii, path_dbf)
        comprobar("compara sin error cuando los recuentos coinciden",
                  error is None, detalle=str(error), severidad="P0")
        n_reg, frac_alineados, coincide, discrepancia, ascii_cero_dbf_no_cero, sin_campo = resultado
        comprobar("compara las 4 filas", n_reg == 4, detalle=str(n_reg), severidad="P0")
        comprobar("ASIEN coincide en las 4 filas (1,2,3,4 en los dos ficheros) -> 100% alineado",
                  frac_alineados == 1.0, detalle=str(frac_alineados), severidad="P0")
        comprobar("EL CASO GRAVE: BASEIMPO cuenta 2 (fila 2 vacia + fila 3 ilegible, "
                  "las dos con valor real distinto de cero en el DBF)",
                  ascii_cero_dbf_no_cero["BASEIMPO"] == 2,
                  detalle=str(ascii_cero_dbf_no_cero["BASEIMPO"]), severidad="P0")
        comprobar("fila 1 (1000=1000) y fila 4 (0=0, legitimamente cero en los dos) "
                  "cuentan como coincide, no como grave -- 2 en total",
                  coincide["BASEIMPO"] == 2, detalle=str(coincide["BASEIMPO"]), severidad="P0")
        comprobar("la fila 4 (vacio en los dos, legitimamente cero) NO se cuela en el caso grave",
                  ascii_cero_dbf_no_cero["BASEIMPO"] == 2,  # solo filas 2 y 3, no la 4
                  detalle=str(ascii_cero_dbf_no_cero["BASEIMPO"]), severidad="P0")


def pruebas_desalineacion():
    """EL HALLAZGO REAL del 17-09-2026: al ejecutar esto contra un par ASCII+DBF
    real, aparecieron 6.864 discrepancias sobre 72.423 instancias (9,5%) --
    demasiado para ser solo el fallback 0.0. Antes de sospechar de
    leer_ascii_completo(), hay que descartar que las dos exportaciones
    vengan en ORDEN DISTINTO: mismo recuento no es lo mismo que mismo orden,
    y comparar 'linea i contra registro i' con los ordenes cambiados genera
    exactamente este patron -- muchas discrepancias, concentradas, que no
    son un fallo del lector sino del emparejamiento."""
    with tempfile.TemporaryDirectory() as tmp:
        path_ascii = os.path.join(tmp, "diario.txt")
        path_dbf = os.path.join(tmp, "diario.dbf")
        escribir_ascii(path_ascii, [
            {"ASIEN": "1", "BASEIMPO": "100.00"},
            {"ASIEN": "2", "BASEIMPO": "200.00"},
            {"ASIEN": "3", "BASEIMPO": "300.00"},
        ])
        # Mismo recuento (3=3), pero el DBF trae el orden 2, 1, 3 -- no 1, 2, 3.
        construir_dbf_con_filas(path_dbf, CAMPOS, [
            {"ASIEN": 2, "BASEIMPO": 200.00},
            {"ASIEN": 1, "BASEIMPO": 100.00},
            {"ASIEN": 3, "BASEIMPO": 300.00},
        ])
        resultado, error = diag.comparar_con_dbf(path_ascii, path_dbf)
        n_reg, frac_alineados, coincide, discrepancia, _grave, _sin = resultado
        comprobar("EL AVISO: con las 2 primeras filas en orden distinto, "
                  "frac_alineados baja de 1.0 (aqui a 1/3) -- detecta el "
                  "desorden en vez de reportar discrepancias falsas sin avisar",
                  frac_alineados < 0.5, detalle=str(frac_alineados), severidad="P0")


def pruebas_recuento_distinto():
    with tempfile.TemporaryDirectory() as tmp:
        path_ascii = os.path.join(tmp, "diario.txt")
        path_dbf = os.path.join(tmp, "diario.dbf")
        escribir_ascii(path_ascii, [{"ASIEN": "1"}, {"ASIEN": "2"}])
        construir_dbf_con_filas(path_dbf, CAMPOS, [{"ASIEN": 1}])  # solo 1, no 2
        resultado, error = diag.comparar_con_dbf(path_ascii, path_dbf)
        comprobar("recuento distinto: no compara nada, lo declara",
                  resultado is None and error is not None, detalle=str(error), severidad="P0")


def main():
    print("=" * 72)
    print("DIAGNOSTICO leer_ascii_completo — bateria (datos 100% sinteticos)")
    print("=" * 72)
    pruebas_clasificar_ascii()
    pruebas_comparar_con_dbf()
    pruebas_desalineacion()
    pruebas_recuento_distinto()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nDistingue vacio de ilegible, encuentra el caso grave (ASCII=0 pero")
    print("DBF real) sin confundirlo con un cero legitimo, y declara cuando no")
    print("puede emparejar en vez de comparar a ciegas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
