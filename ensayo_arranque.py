#!/usr/bin/env python3
"""ensayo_arranque.py — ensayo de arranque.py y del hook de sesion.

POR QUE HACE FALTA
-------------------
`arranque.py` esta en el camino de arranque de TODA sesion, en toda superficie,
desde el 10-09-2026 (`.claude/hooks/session-start.sh`). Eso cambia lo que
significa que falle: no es un script que da error cuando lo llamas, es un script
que hace que **todas** las sesiones empiecen con un error, incluida la primera
del PC de la asesoria.

Y tiene una segunda condicion que no es negociable: **corre antes que nada, en
una maquina que tiene los datos reales delante.** Si alguna vez imprimiera el
contenido de un fichero `_LOCAL`, lo haria en el arranque de todas las sesiones
y sin que nadie se lo pidiera.

QUE PRUEBA
-----------
  A. Que no revienta NUNCA, ni en las situaciones raras: fuera de un
     repositorio git, sin PENDIENTE.md, con el hook en una carpeta vacia.
  B. Que no da tranquilidad falsa: fuera de git NO dice "arbol limpio".
  C. Que dice la verdad sobre donde vive el trabajo (la pregunta que ya salio
     cara una vez en este proyecto).
  D. Que no abre ni imprime ningun `_LOCAL`.
  E. Que el hook nunca corta la sesion, pase lo que pase.

Uso:
    python ensayo_arranque.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(AQUI, "arranque.py")
HOOK = os.path.join(AQUI, ".claude", "hooks", "session-start.sh")

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK  {titulo}")
    else:
        print(f"  FALLA  {titulo}   {detalle}")
        FALLOS.append(titulo)


def correr(cwd, *args):
    r = subprocess.run([sys.executable, os.path.join(cwd, "arranque.py"), *args],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def main():
    print("=" * 70)
    print("ENSAYO: arranque.py y el hook de sesion")
    print("=" * 70)

    # === FAMILIA A — en el repositorio de verdad ============================
    print("\n=== FAMILIA A — en este repositorio ===")
    rc, salida = correr(AQUI)
    comprobar("termina bien", rc == 0, f"rc={rc}")
    for trozo in ("Entorno", "Donde vive el trabajo", "Barrera de privacidad",
                  "Dependencias", "Estado del motor", "Que toca hacer"):
        comprobar(f"imprime la seccion '{trozo}'", trozo in salida, salida[:200])
    comprobar("dice cual es el siguiente comando real",
              "cuadre_303_ficha.py --listar" in salida
              or "emparejar_carpetas.py" in salida, salida[-400:])
    comprobar("remata mandando a EMPEZAR_AQUI.md",
              "EMPEZAR_AQUI.md" in salida, salida[-300:])

    # === FAMILIA B — no da tranquilidad falsa ==============================
    # Fuera de un repositorio git no hay arbol que pueda estar limpio. Decir
    # "limpio" ahi es la misma clase de falso verde que el motor tiene
    # prohibido: afirmar lo que no se ha podido comprobar.
    print("\n=== FAMILIA B — fuera de git no dice 'limpio', dice que no lo sabe ===")
    tmp = tempfile.mkdtemp(prefix="ensayo_arranque_")
    try:
        shutil.copy2(SCRIPT, os.path.join(tmp, "arranque.py"))
        rc, salida = correr(tmp)
        comprobar("no revienta fuera de un repositorio git", rc == 0, f"rc={rc}")
        comprobar("y avisa de que NO es un repositorio git",
                  "NO ES UN REPOSITORIO GIT" in salida, salida[:600])
        comprobar("sin declarar el arbol limpio (no hay arbol)",
                  "arbol        : limpio" not in salida, salida[:600])
        comprobar("y sin PENDIENTE.md avisa en vez de callarse",
                  "No encuentro PENDIENTE.md" in salida, salida[-400:])

        # === FAMILIA C — el hook nunca corta la sesion =====================
        print("\n=== FAMILIA C — el hook nunca corta la sesion ===")
        if os.path.exists(HOOK):
            hueco = os.path.join(tmp, "hueco")
            os.makedirs(os.path.join(hueco, ".claude", "hooks"), exist_ok=True)
            destino = os.path.join(hueco, ".claude", "hooks", "session-start.sh")
            shutil.copy2(HOOK, destino)
            entorno = dict(os.environ, CLAUDE_PROJECT_DIR=hueco)
            r = subprocess.run(["sh", destino], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=entorno)
            comprobar("sin arranque.py, el hook avisa y sale con 0",
                      r.returncode == 0 and "AVISO" in (r.stdout + r.stderr),
                      f"rc={r.returncode} {(r.stdout + r.stderr)[:200]}")

            entorno2 = dict(os.environ, CLAUDE_PROJECT_DIR=AQUI)
            r2 = subprocess.run(["sh", HOOK], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", env=entorno2)
            comprobar("y en el repositorio bueno sale con 0 e imprime el estado",
                      r2.returncode == 0 and "arranque de sesion" in r2.stdout,
                      f"rc={r2.returncode}")
            comprobar("el hook NO instala nada (.claude/rules/seguridad.md)",
                      "pip install" not in open(HOOK, encoding="utf-8").read()
                      .split("# QUE NO HACE")[0],
                      "el hook contiene un pip install fuera del comentario")
        else:
            comprobar("existe el hook de arranque", False, f"no encuentro {HOOK}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # === FAMILIA D — la barrera de datos ===================================
    # arranque.py corre solo, en la maquina que tiene los datos delante. No
    # puede abrir un _LOCAL ni por descuido.
    print("\n=== FAMILIA D — no toca ningun fichero de datos ===")
    # Se comprueba sobre el AST, no buscando cadenas en el texto. La primera
    # version de este ensayo hacia lo segundo y fallaba: `_LOCAL` y `.dbf`
    # aparecen en arranque.py dentro de MENSAJES que se imprimen ("ningun
    # fichero *_LOCAL.* se abre jamas", "leer los .dbf del corpus"), no en
    # codigo que abra nada. Es la leccion del 21-08-2026 con check_cableado:
    # un auditor que mira la FORMA acusa a inocentes. Lo que importa no es que
    # la palabra aparezca, es QUE FICHEROS SE ABREN.
    import ast
    arbol = ast.parse(open(SCRIPT, encoding="utf-8").read())
    aperturas = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) \
                and nodo.func.id == "open":
            arg = nodo.args[0] if nodo.args else None
            if isinstance(arg, ast.Constant):
                aperturas.append(repr(arg.value))
            elif isinstance(arg, ast.Name):
                aperturas.append(arg.id)
            else:
                aperturas.append(ast.dump(arg)[:60] if arg else "?")

    #: Lo unico que arranque.py tiene permitido abrir. Cualquier otra cosa es
    #: un fichero nuevo en el camino de arranque de todas las sesiones, y hay
    #: que mirarlo a mano antes de darlo por bueno.
    PERMITIDO = {"pendiente"}
    de_mas = [a for a in aperturas if a not in PERMITIDO]
    comprobar("solo abre PENDIENTE.md, ningun otro fichero",
              not de_mas, f"tambien abre: {de_mas}")
    comprobar("y no lee nada con ruta construida a partir de un argumento",
              all(a in PERMITIDO for a in aperturas), f"aperturas={aperturas}")
    rc, salida = correr(AQUI)
    comprobar("y su salida no contiene ningun patron de NIF/DNI",
              not __import__("re").search(r"\b\d{8}[A-Za-z]\b|\b[A-HJNPQRSUVW]\d{7}[0-9A-J]\b",
                                          salida),
              "hay algo con forma de NIF en la salida")

    # === FAMILIA E — el aviso que evita perder el trabajo ==================
    # ANADIDA tras un sabotaje que NO se cazaba: si arranque.py dejaba de
    # avisar de que la rama va por delante de master, la bateria seguia en
    # verde. Y ese aviso es lo mas consecuente que dice el script — es el que
    # impide repetir el incidente de las correcciones vivas en ramas claude/*
    # sin fusionar, con quien clonaba master llevandose la version vieja.
    print("\n=== FAMILIA E — avisa si el trabajo esta donde nadie lo va a encontrar ===")
    tmp2 = tempfile.mkdtemp(prefix="ensayo_arranque_git_")
    try:
        remoto = os.path.join(tmp2, "remoto.git")
        clon = os.path.join(tmp2, "clon")

        def g(cwd, *args):
            return subprocess.run(["git", *args], capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", cwd=cwd)

        subprocess.run(["git", "init", "--bare", "-b", "master", remoto],
                       capture_output=True)
        subprocess.run(["git", "init", "-b", "master", clon], capture_output=True)
        # Sin arroba a proposito: git acepta cualquier cadena como ident, y el
        # escaner de privacidad —con razon— marca cualquier cosa con forma de
        # correo. Cazo mi propio fichero al escribirlo: se arregla el fichero,
        # nunca la barrera.
        g(clon, "config", "user.email", "ensayo-sin-correo")
        g(clon, "config", "user.name", "Ensayo")
        shutil.copy2(SCRIPT, os.path.join(clon, "arranque.py"))
        g(clon, "add", "arranque.py")
        g(clon, "commit", "-m", "base")
        g(clon, "remote", "add", "origin", remoto)
        g(clon, "push", "-u", "origin", "master")

        # Una rama de trabajo con un commit que master NO tiene: la situacion
        # exacta que hay que cazar.
        g(clon, "checkout", "-b", "trabajo")
        with open(os.path.join(clon, "algo.txt"), "w", encoding="utf-8") as f:
            f.write("trabajo que master no tiene\n")
        g(clon, "add", "algo.txt")
        g(clon, "commit", "-m", "trabajo sin fusionar")

        rc, salida = correr(clon)
        comprobar("no revienta en un repositorio con rama de trabajo",
                  rc == 0, f"rc={rc}")
        comprobar("AVISA de que la rama va por delante de master",
                  "POR DELANTE DE origin/master" in salida, salida[:900])
        comprobar("y explica la consecuencia: quien clone master no lo recibe",
                  "NO recibe" in salida, salida[:900])

        # Y al reves: fusionado, no debe dar ese aviso, o dejaria de
        # significar algo por salir siempre.
        g(clon, "checkout", "master")
        g(clon, "merge", "trabajo", "--no-edit")
        g(clon, "push", "origin", "master")
        rc, salida2 = correr(clon)
        comprobar("y NO avisa cuando ya esta todo en master",
                  "POR DELANTE DE origin/master" not in salida2, salida2[:900])
        comprobar("sino que lo dice explicitamente",
                  "sincronizado" in salida2, salida2[:900])
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    print()
    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        print("\nEsto corre al arrancar TODA sesion: un fallo aqui es un error")
        print("en el arranque de todas, incluida la primera del PC de la asesoria.")
        return 1
    print("El ensayo pasa. El arranque no revienta, no da tranquilidad falsa,")
    print("no toca ningun dato, y el hook nunca corta la sesion.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
