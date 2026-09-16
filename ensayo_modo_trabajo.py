#!/usr/bin/env python3
"""ensayo_modo_trabajo.py — que el informe de modo diga la verdad y no filtre.

LO QUE MAS IMPORTA AQUI
-------------------------
Este modulo existe para IMPRIMIR el estado, y el estado incluye si hay claves
puestas. Un informe que, queriendo ser util, imprima el VALOR de una clave
seria una fuga de credenciales por la puerta de servicio -- y ademas en una
sesion de Remote Control la consola acaba en la transcripcion. Por eso la
comprobacion central es con una clave TRAMPA en el entorno: tiene que decir
que esta puesta, y no puede aparecer ni un caracter de su valor.

Lo segundo que vigila es mas sutil: que ninguna tarea pida una capacidad que no
existe. Un nombre mal escrito en `necesita` no rompe nada -- simplemente esa
tarea sale bloqueada PARA SIEMPRE, con un "falta: clave_geminy" que nadie
entiende. Es un falso rojo permanente, y un auditor que grita cuando no toca
acaba ignorandose (leccion del 21-08-2026 con check_cableado).
"""
import io
import os
import sys
from contextlib import redirect_stdout

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import modo_trabajo as mt

#: Valor trampa. Ni es una clave real ni lo parece: lo que importa es que sea
#: una cadena inconfundible que no pueda aparecer por casualidad.
CLAVE_TRAMPA = "VALOR_DE_CLAVE_QUE_NO_DEBE_IMPRIMIRSE_NUNCA"

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, condicion, detalle, severidad))
    print(f"  [{'OK  ' if condicion else 'FALLA'}] {nombre}"
          + (f"\n           {detalle}" if not condicion and detalle else ""))


def main():
    print("=" * 70)
    print("ENSAYO: modo de trabajo")
    print("=" * 70)

    print("\nA. Mide el entorno, no lo recuerda")
    cerrado = mt.medir(entorno={})
    comprobar("con el entorno vacio, ninguna llave esta abierta",
              not cerrado["clave_gemini"] and not cerrado["clave_anthropic"]
              and not cerrado["puerta_cloud"] and not cerrado["puerta_datos_reales"])
    abierto = mt.medir(entorno={
        "GEMINI_API_KEY": CLAVE_TRAMPA,
        "ANTHROPIC_API_KEY": CLAVE_TRAMPA,
        mt.puerta_cloud.ENV_CLOUD: "1",
        mt.puerta_cloud.ENV_DATOS_REALES: "1"})
    comprobar("con las llaves puestas, las cuatro se ven",
              all(abierto[k] for k in ("clave_gemini", "clave_anthropic",
                                       "puerta_cloud", "puerta_datos_reales")))
    comprobar("una clave presente se reduce a un booleano, no se guarda",
              abierto["clave_gemini"] is True,
              f"guardo {type(abierto['clave_gemini']).__name__}", "P0")
    comprobar("un corpus que no existe no se da por bueno",
              not mt.medir(entorno={}, ruta_corpus="/ruta/que/no/existe")["corpus"],
              severidad="P0")

    print("\nB. LO QUE NO PUEDE PASAR: que el valor de una clave se imprima")
    os.environ["GEMINI_API_KEY"] = CLAVE_TRAMPA
    os.environ["ANTHROPIC_API_KEY"] = CLAVE_TRAMPA
    try:
        buf = io.StringIO()
        with redirect_stdout(buf):
            mt.main()
        salida = buf.getvalue()
    finally:
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
    comprobar("el informe dice que la clave esta puesta",
              "GEMINI_API_KEY           SI" in salida, salida[:200])
    comprobar("...y NO imprime ni un caracter de su valor",
              CLAVE_TRAMPA not in salida, severidad="P0")
    comprobar("tampoco un trozo reconocible del valor",
              "VALOR_DE_CLAVE" not in salida, severidad="P0")

    print("\nC. Ninguna tarea pide una capacidad que no existe")
    # Un nombre mal escrito deja la tarea bloqueada para siempre, con un motivo
    # que nadie entiende: falso rojo permanente.
    conocidas = set(mt.medir(entorno={}))
    for t in mt.TAREAS:
        desconocidas = [n for n in t.necesita if n not in conocidas]
        comprobar(f"'{t.nombre[:44]}' pide capacidades reales",
                  not desconocidas, str(desconocidas), "P0")

    print("\nD. Lo que Claude puede ver se DERIVA de lo medido")
    _, ve_real = mt.que_puede_ver_claude(mt.medir(entorno={}))
    comprobar("sin clave y sin sesion local, NO puede ver el documento original",
              ve_real is False, severidad="P0")
    lineas, _ = mt.que_puede_ver_claude(mt.medir(entorno={}))
    comprobar("y lo dice explicitamente, no por omision",
              any("documento original: NO" in l for l in lineas), severidad="P0")
    comprobar("la ruta 3 se declara como NO construida mientras no exista",
              any("no esta construida" in l for l in lineas)
              or os.path.exists("proyeccion_minima.py"))

    print("\nE. No toca ningun dato")
    fuente = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "modo_trabajo.py"), encoding="utf-8").read()
    comprobar("no abre ningun fichero para leerlo", "open(" not in fuente,
              severidad="P0")
    comprobar("no menciona ningun fichero _LOCAL", "_LOCAL" not in fuente,
              severidad="P0")

    print("\nF. Las cuatro rutas estan completas")
    comprobar("hay exactamente cuatro rutas declaradas", len(mt.RUTAS) == 4)
    comprobar("cada una dice que necesita y cuanto cuesta",
              all(len(r) == 4 and all(str(c).strip() for c in r) for r in mt.RUTAS))
    comprobar("la ruta mas barata es la primera (tres roles)",
              "TRES ROLES" in mt.RUTAS[0][0])
    comprobar("y la de Claude viendo el documento es la ultima",
              "CLAUDE VE EL DOCUMENTO" in mt.RUTAS[-1][0])

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print("\n" + "=" * 70)
    print(f"Pruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\nEl informe de modo mide de verdad, no filtra el valor de ninguna")
    print("clave, y ninguna tarea pide una capacidad inexistente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
