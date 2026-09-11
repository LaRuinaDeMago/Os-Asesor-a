#!/usr/bin/env python3
"""ensayo_suites_cableadas.py — ensayo de `check_suites_sin_cablear()`, el
auditor que comprueba que ninguna suite del repositorio se quede sin ejecutar.

POR QUE EXISTE ESTE ENSAYO
----------------------------
El 11-09-2026 habia SIETE suites en el repositorio que `audit_project.py` no
ejecutaba nunca. Todas en verde, todas escritas para fijar una regresion
concreta -- entre ellas la unica que protege el bug P0 del 21-08 ("0.0% miente"
cuando el separador del CSV no se reconoce), sobre el script que produce el
unico numero del proyecto con umbral acordado por adelantado.

Se comprobo POR SABOTAJE antes de arreglarlo: con ese ensayo roto a proposito,
`audit_project.py` imprimio la MISMA salida que con el repositorio sano y salio
con el mismo codigo 2. Ni un rojo, ni una mencion.

`check_suites_sin_cablear()` cierra ese agujero. Pero un auditor que se apaga en
silencio deja el agujero peor que antes, porque ademas se firma como revisado:
es exactamente lo que le paso al 11o auditor de este proyecto, dos semanas
apagado sin que la auditoria supiera decirlo (PROJECT_STATUS.md, 09-09-2026).
Los seis escenarios de abajo se probaron a mano el dia que se escribio; este
ensayo existe para que sigan probados el dia que alguien los toque.

POR QUE NO EJECUTA audit_project.py
-------------------------------------
Seria lo natural, y es una trampa: `audit_project.py` ejecuta este ensayo. Si
este ensayo ejecutara `audit_project.py`, la auditoria no terminaria nunca. Por
eso importa el modulo y llama a la funcion directamente, con un directorio
temporal por escenario.
"""
import ast
import io
import os
import sys
import contextlib
import tempfile
from pathlib import Path

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import audit_project

FALLOS = []


def comprobar(descripcion, condicion, detalle=""):
    if condicion:
        print(f"  ✅ {descripcion}")
    else:
        print(f"  ❌ {descripcion}" + (f"\n       {detalle}" if detalle else ""))
        FALLOS.append(descripcion)


def evaluar(suites_en_disco, ejecutadas, excepciones=None):
    """Monta un repositorio de mentira con `suites_en_disco` (rutas relativas),
    declara `ejecutadas` como lo que ha corrido, y devuelve el resultado del
    check: (estado, detalle). No imprime nada por consola."""
    previo_cwd = os.getcwd()
    previo_ejecutadas = set(audit_project.SUITES_EJECUTADAS)
    previo_excepciones = dict(audit_project.EXCEPCIONES_SUITES)
    previo_resultado = audit_project.RESULTADO["checks"]
    with tempfile.TemporaryDirectory() as tmp:
        try:
            for rel in suites_en_disco:
                destino = Path(tmp) / rel
                destino.parent.mkdir(parents=True, exist_ok=True)
                destino.write_text("if __name__ == '__main__':\n    print('ok')\n",
                                   encoding="utf-8")
            os.chdir(tmp)
            audit_project.SUITES_EJECUTADAS.clear()
            audit_project.SUITES_EJECUTADAS.update(ejecutadas)
            audit_project.EXCEPCIONES_SUITES.clear()
            audit_project.EXCEPCIONES_SUITES.update(excepciones or {})
            audit_project.RESULTADO["checks"] = {}
            with contextlib.redirect_stdout(io.StringIO()):
                audit_project.check_suites_sin_cablear()
            (entrada,) = audit_project.RESULTADO["checks"].values()
            return entrada["estado"], entrada["detalle"]
        finally:
            os.chdir(previo_cwd)
            audit_project.SUITES_EJECUTADAS.clear()
            audit_project.SUITES_EJECUTADAS.update(previo_ejecutadas)
            audit_project.EXCEPCIONES_SUITES.clear()
            audit_project.EXCEPCIONES_SUITES.update(previo_excepciones)
            audit_project.RESULTADO["checks"] = previo_resultado


def main():
    print("=== ENSAYO: ninguna suite del repositorio se queda sin ejecutar ===\n")

    # ---------------------------------------------------------------- A
    print("A. Repositorio sano: todas las suites se ejecutan")
    estado, _ = evaluar(["test_uno.py", "ensayo_dos.py"],
                        {"test_uno.py", "ensayo_dos.py"})
    comprobar("dice OK cuando de verdad se ejecutan todas", estado == audit_project.OK, estado)

    # ---------------------------------------------------------------- B
    print("\nB. EL AGUJERO: una suite existe y nadie la ejecuta")
    estado, detalle = evaluar(["test_uno.py", "ensayo_dos.py"], {"test_uno.py"})
    comprobar("sale en rojo", estado == audit_project.FALLO, estado)
    comprobar("NOMBRA la que nadie ejecuta", "ensayo_dos.py" in detalle, detalle)
    comprobar("no acusa a la que si se ejecuta",
              "NADIE EJECUTA" in detalle and "test_uno.py" not in detalle.split("NADIE EJECUTA")[1],
              detalle)

    # ---------------------------------------------------------------- C
    print("\nC. LA TRAMPA DEL GREP: el veredicto no puede depender del NOMBRE")
    # `ensayo_retro_semaforo.py` aparece TEXTUALMENTE varias veces dentro de
    # audit_project.py, en comentarios que explican que cubre y que no. Un
    # auditor que comprobara "¿se menciona el nombre?" lo daria por cableado.
    fuente = Path(audit_project.__file__).read_text(encoding="utf-8")
    comprobar("el nombre de prueba aparece de verdad en audit_project.py",
              fuente.count("ensayo_retro_semaforo.py") >= 2,
              "si dejara de aparecer, este escenario dejaria de probar nada")
    estado, detalle = evaluar(["ensayo_retro_semaforo.py"], set())
    comprobar("una suite NOMBRADA pero no ejecutada sigue saliendo en rojo",
              estado == audit_project.FALLO and "ensayo_retro_semaforo.py" in detalle,
              f"{estado} | {detalle}")

    # ---------------------------------------------------------------- D
    print("\nD. Una suite que se EJECUTA y sale en ROJO no es asunto de este auditor")
    # Su propio check ya la pinta de rojo. Este mira quien no la mira, no quien
    # falla: por eso ejecutar_suite() anota ANTES de lanzar.
    estado, _ = evaluar(["test_uno.py"], {"test_uno.py"})
    comprobar("no la acusa por partida doble", estado == audit_project.OK, estado)

    # ---------------------------------------------------------------- E
    print("\nE. Excepciones: la legitima pasa y se VE; la fantasma no cuela")
    estado, detalle = evaluar(["test_uno.py", "ensayo_dos.py"], {"test_uno.py"},
                              {"ensayo_dos.py": "motivo concreto — 11-09-2026"})
    comprobar("una exclusion declarada con motivo no bloquea", estado == audit_project.OK, estado)
    comprobar("pero se imprime en cada pasada, nunca en silencio",
              "ensayo_dos.py" in detalle and "motivo concreto" in detalle, detalle)

    estado, detalle = evaluar(["test_uno.py"], {"test_uno.py"},
                              {"ensayo_que_ya_no_existe.py": "motivo viejo — 01-01-2026"})
    comprobar("una excepcion cuya suite ya no existe sale en rojo",
              estado == audit_project.FALLO, estado)
    comprobar("y dice cual sobra", "ensayo_que_ya_no_existe.py" in detalle, detalle)

    # ---------------------------------------------------------------- F
    print("\nF. Donde mira: subdirectorios si, directorios ocultos no")
    estado, detalle = evaluar(["sub/carpeta/ensayo_hondo.py"], set())
    comprobar("encuentra una suite metida en un subdirectorio",
              estado == audit_project.FALLO and "ensayo_hondo.py" in detalle,
              f"{estado} | {detalle}")
    estado, _ = evaluar([".venv/lib/ensayo_de_una_dependencia.py", "test_uno.py"],
                        {"test_uno.py"})
    comprobar("no acusa a lo que vive en un directorio oculto (.git, .venv)",
              estado == audit_project.OK, estado)

    estado, detalle = evaluar(["sub/ensayo_hondo.py"], {"sub/ensayo_hondo.py"})
    comprobar("y la da por cubierta cuando se ejecuta con su ruta",
              estado == audit_project.OK, f"{estado} | {detalle}")

    print("\nF-bis. CERO suites encontradas no es un aprobado")
    # Pasa si la auditoria se lanza desde otro directorio. Sin esto, el unico
    # check que no se daria cuenta seria precisamente este, y diria que va bien
    # sin haber abierto nada — el falso verde del escaner de privacidad con un
    # .DAT, otra vez.
    estado, detalle = evaluar([], set())
    comprobar("un directorio sin suites sale NO_COMPROBADO, no OK",
              estado == audit_project.NO_COMPROBADO, estado)
    comprobar("y lo dice con esas palabras", "no se ha mirado nada" in detalle, detalle)

    # ---------------------------------------------------------------- G
    print("\nG. COLISION DE NOMBRES: dos suites homonimas no se tapan")
    # La primera version comparaba por NOMBRE de fichero. Con eso, ejecutar
    # `ensayo_x.py` daba por cubierta tambien `sub/ensayo_x.py`, que nadie
    # ejecutaba. Un falso verde por colision de nombres es un falso verde igual.
    estado, detalle = evaluar(["ensayo_x.py", "sub/ensayo_x.py"], {"ensayo_x.py"})
    comprobar("la homonima no ejecutada sigue saliendo en rojo",
              estado == audit_project.FALLO and "sub/ensayo_x.py" in detalle,
              f"{estado} | {detalle}")

    # ---------------------------------------------------------------- H
    print("\nH. INVARIANTE: ejecutar_suite() es la UNICA puerta")
    # Sin esto, el arreglo se deshace solo: bastaria con que alguien anadiera
    # una suite con un subprocess.run suelto para que volviera a correr sin
    # quedar anotada, y el auditor la daria por no ejecutada (falso rojo) o,
    # peor, alguien la anadiria tambien a EXCEPCIONES_SUITES para callarlo.
    arbol = ast.parse(fuente)
    sueltas = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        nombre = ""
        if isinstance(nodo.func, ast.Attribute):
            nombre = nodo.func.attr
        if nombre != "run" or not nodo.args:
            continue
        for literal in ast.walk(nodo.args[0]):
            if isinstance(literal, ast.Constant) and isinstance(literal.value, str):
                v = literal.value
                if v.startswith(("test_", "ensayo_")) and v.endswith(".py"):
                    sueltas.append(v)
    comprobar("ninguna suite se lanza con un subprocess.run suelto",
              not sueltas, f"se lanzan fuera de ejecutar_suite(): {sueltas}")

    origen_ejecutar = fuente.split("def ejecutar_suite(", 1)[1].split("\ndef ", 1)[0]
    comprobar("ejecutar_suite() anota ANTES de lanzar",
              origen_ejecutar.index("SUITES_EJECUTADAS.add") < origen_ejecutar.index("subprocess.run"),
              "si anotara despues, una suite que reviente contaria como no ejecutada")

    print()
    if FALLOS:
        print(f"❌ FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"   · {f}")
        return 1
    print("El ensayo pasa. El auditor caza la suite que nadie ejecuta, "
          "no se deja engañar por el nombre, y no puede rodearse.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
