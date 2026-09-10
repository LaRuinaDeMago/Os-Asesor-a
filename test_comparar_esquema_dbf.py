"""
SUITE DE PRUEBAS — comparar_esquema_dbf.py
Cabeceras dBase construidas a mano, cero registros, cero datos de cliente.
Objetivo: que Diego pueda confiar en la comparacion sin que Claude tenga
que ver ni un fichero real para escribirla ni para probarla.

Ejecutar con: python3 test_comparar_esquema_dbf.py
"""
import os
import struct
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from comparar_esquema_dbf import leer_esquema_dbf_suelto, comparar_contra_contaplus
from layout_diario_contaplus import CAMPOS as CAMPOS_CONTAPLUS

FALLOS = []


def check(cond, nombre):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


def construir_dbf_sintetico(path, campos, n_registros=0):
    """campos: lista de (nombre, ancho, tipo, decimales) -- el MISMO orden de
    tupla que usa CAMPOS en layout_diario_contaplus.py. Escribe SOLO la
    cabecera + terminador -- cero filas, cero bytes de datos, a proposito:
    lo unico que este script necesita leer es la cabecera."""
    descriptores = b""
    for nombre, ancho, tipo, dec in campos:
        nb = nombre.encode('ascii')[:10].ljust(11, b'\x00')
        descriptores += nb + tipo.encode('ascii') + b'\x00' * 4 + bytes([ancho, dec]) + b'\x00' * 14

    long_cabecera = 32 + len(descriptores) + 1  # +1 del terminador 0x0D
    long_registro = sum(c[1] for c in campos) + 1  # +1 byte de borrado

    cabecera = bytearray(32)
    cabecera[0] = 0x03  # dBase III sin memo
    cabecera[1:4] = bytes([26, 8, 27])  # fecha arbitraria, no es un dato de cliente
    struct.pack_into("<I", cabecera, 4, n_registros)
    struct.pack_into("<H", cabecera, 8, long_cabecera)
    struct.pack_into("<H", cabecera, 10, long_registro)
    cabecera[29] = 0x03  # cp1252

    with open(path, 'wb') as f:
        f.write(bytes(cabecera))
        f.write(descriptores)
        f.write(b'\x0d')  # terminador de la lista de campos


print("=== leer_esquema_dbf_suelto: lee la cabecera de un .dbf independiente ===")
tmp = tempfile.mkdtemp(prefix="ensayo_dbf_")
try:
    ruta_identico = os.path.join(tmp, "identico.dbf")
    construir_dbf_sintetico(ruta_identico, CAMPOS_CONTAPLUS, n_registros=999)
    esquema = leer_esquema_dbf_suelto(ruta_identico)
    check(esquema["n_campos"] == len(CAMPOS_CONTAPLUS),
          f"lee los {len(CAMPOS_CONTAPLUS)} campos, ni uno de mas ni de menos")
    check(esquema["n_registros"] == 999,
          "el numero de registros se lee de la cabecera (no hace falta leer ninguna fila)")
    check(esquema["cuadra_long_registro"] is True,
          "la suma de anchos cuadra con la longitud de registro declarada")

    print("\n=== comparar_contra_contaplus: caso IDENTICO ===")
    identico, diffs = comparar_contra_contaplus(esquema["campos"])
    check(identico is True, "un .dbf con exactamente los mismos campos -> IDENTICO")
    check(diffs == [], "sin diferencias que listar")

    print("\n=== comparar_contra_contaplus: caso DIFERENTE (un campo con otro ancho) ===")
    campos_modificados = list(CAMPOS_CONTAPLUS)
    # Cambia el ancho del primer campo (ASIEN, 6 -> 8) -- simula una version
    # de ContaSOL que usara un correlativo mas largo, sin inventarse un caso
    # real: es exactamente el tipo de diferencia que este script existe para
    # detectar.
    nombre0, _ancho0, tipo0, dec0 = campos_modificados[0]
    campos_modificados[0] = (nombre0, 8, tipo0, dec0)
    ruta_diferente = os.path.join(tmp, "diferente.dbf")
    construir_dbf_sintetico(ruta_diferente, campos_modificados)
    esquema_dif = leer_esquema_dbf_suelto(ruta_diferente)
    identico2, diffs2 = comparar_contra_contaplus(esquema_dif["campos"])
    check(identico2 is False, "un campo con distinto ancho -> NO identico")
    check(len(diffs2) == 1, "se reporta exactamente 1 diferencia, la que se cambio")
    check(nombre0 in diffs2[0] and "6" in diffs2[0] and "8" in diffs2[0],
          "la diferencia reportada nombra el campo y los dos anchos (6 vs 8)")

    print("\n=== comparar_contra_contaplus: caso con un campo de MENOS ===")
    campos_recortados = list(CAMPOS_CONTAPLUS)[:-1]  # quita el ultimo campo
    ruta_recortado = os.path.join(tmp, "recortado.dbf")
    construir_dbf_sintetico(ruta_recortado, campos_recortados)
    esquema_rec = leer_esquema_dbf_suelto(ruta_recortado)
    identico3, diffs3 = comparar_contra_contaplus(esquema_rec["campos"])
    check(identico3 is False, "un fichero con un campo de menos -> NO identico")
    check(any("None" in d for d in diffs3),
          "la diferencia del campo que falta se reporta como None, no se oculta")

finally:
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

print("\n=== Ningun fichero de prueba escribe ni una fila de datos ===")
# Control de diseno: construir_dbf_sintetico() nunca escribe bytes despues
# del terminador de campos -- el .dbf resultante mide EXACTAMENTE long_cabecera.
tmp2 = tempfile.mkdtemp(prefix="ensayo_dbf_tamano_")
try:
    ruta = os.path.join(tmp2, "solo_cabecera.dbf")
    construir_dbf_sintetico(ruta, CAMPOS_CONTAPLUS[:5])
    tam = os.path.getsize(ruta)
    esquema = leer_esquema_dbf_suelto(ruta)
    check(tam == esquema["long_cabecera"],
          "el fichero de prueba mide exactamente lo que su cabecera declara -- "
          "cero bytes de fila, ni por accidente")
finally:
    import shutil
    shutil.rmtree(tmp2, ignore_errors=True)

print("\n" + "=" * 50)
if FALLOS:
    print(f"❌ {len(FALLOS)} PRUEBA(S) FALLIDA(S): {FALLOS}")
    sys.exit(1)
print("✅ TODAS LAS PRUEBAS PASAN")
