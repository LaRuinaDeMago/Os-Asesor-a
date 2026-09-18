"""
SUITE DE PRUEBAS -- cierre_sesion.py
Entorno sintetico via diccionarios a mano, log en un fichero temporal --
nunca toca el .log real ni el entorno real del proceso.

Ejecutar con: python3 test_cierre_sesion.py
"""
import os
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from cierre_sesion import claves_activas, registrar, CLAVES_VIGILADAS

FALLOS = []


def check(cond, nombre):
    if cond:
        print(f"  OK   {nombre}")
    else:
        print(f"  FALLO {nombre}")
        FALLOS.append(nombre)


check(claves_activas({}) == [],
      "Entorno sin ninguna clave puesta: no reporta ninguna")

check(claves_activas({"ANTHROPIC_API_KEY": "sk-ant-lo-que-sea"}) == ["ANTHROPIC_API_KEY"],
      "Detecta ANTHROPIC_API_KEY puesta, por presencia, no por valor")

check(claves_activas({"GEMINI_API_KEY": "cualquier-cosa"}) == ["GEMINI_API_KEY"],
      "Detecta GEMINI_API_KEY puesta")

check(claves_activas({"ANTHROPIC_API_KEY": "x", "GEMINI_API_KEY": "y"}) == list(CLAVES_VIGILADAS),
      "Detecta las dos a la vez, en el orden vigilado")

check(claves_activas({"ANTHROPIC_API_KEY": ""}) == [],
      "Una variable puesta pero VACIA no cuenta como activa (mismo criterio "
      "que arranque.py/modo_trabajo.py)")

check(claves_activas({"OTRA_COSA": "x"}) == [],
      "Una variable de entorno cualquiera, no vigilada, no dispara nada")


# El log nunca imprime el VALOR de la clave -- solo su nombre.
with tempfile.TemporaryDirectory() as tmp:
    ruta_log = os.path.join(tmp, "prueba.log")
    registrar(["ANTHROPIC_API_KEY"], ruta_log=ruta_log)
    contenido = open(ruta_log, encoding="utf-8").read()
    check("ANTHROPIC_API_KEY" in contenido,
          "El log registra el NOMBRE de la clave activa")
    check("SIGUEN PUESTAS" in contenido,
          "El log deja claro que la clave seguia puesta al cerrar")

with tempfile.TemporaryDirectory() as tmp:
    ruta_log = os.path.join(tmp, "prueba2.log")
    registrar([], ruta_log=ruta_log)
    contenido = open(ruta_log, encoding="utf-8").read()
    check("ninguna clave" in contenido,
          "Con ninguna clave activa, el log lo dice explicitamente (no deja "
          "un silencio ambiguo entre 'no se comprobo' y 'comprobado y limpio')")

with tempfile.TemporaryDirectory() as tmp:
    ruta_log = os.path.join(tmp, "prueba3.log")
    registrar(["ANTHROPIC_API_KEY"], ruta_log=ruta_log)
    registrar([], ruta_log=ruta_log)
    lineas = open(ruta_log, encoding="utf-8").read().splitlines()
    check(len(lineas) == 2,
          "Cada ejecucion ANADE una linea al log, no lo sobrescribe (igual "
          "que vigilancia_boe.log)")


if FALLOS:
    print(f"\n{len(FALLOS)} fallo(s): {', '.join(FALLOS)}")
    sys.exit(1)
print("\nTodas las pruebas de cierre_sesion pasaron.")
sys.exit(0)
