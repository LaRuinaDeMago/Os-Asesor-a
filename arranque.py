#!/usr/bin/env python3
"""arranque.py — lo primero que se ejecuta en cualquier sesion, en cualquier setup.

POR QUE EXISTE
---------------
Hasta el 10-09-2026, `CLAUDE.md` —el unico fichero que Claude Code carga
siempre y obedece— ordenaba "Lee PROJECT_STATUS.md completo antes de hacer
ningun cambio". Ese fichero tiene 140 KB y 2.379 lineas, y en su propia linea 3
dice: "Para ARRANCAR una sesion, lee EMPEZAR_AQUI.md. Este fichero sirve para
consultar, no para empezar."

Es decir: la instruccion que se lee siempre mandaba al sitio equivocado, y a un
fichero tan grande que solo caben dos desenlaces, los dos malos — o se lee
entero y se gasta media sesion en historia, o se salta y se pierde el estado.

QUE HACE ESTE FICHERO Y POR QUE NO ES OTRO DOCUMENTO MAS
---------------------------------------------------------
Un documento afirma; este script COMPRUEBA. Todo lo que imprime lo mide en el
momento: la rama, si el trabajo esta donde alguien lo va a encontrar, que
dependencias faltan y que bloquea cada una, si el hook de privacidad esta
puesto. Un texto se queda desfasado sin avisar; esto no puede.

Lo unico que lee de un fichero es la lista de pendientes (`PENDIENTE.md`), que
es la unica parte que un humano tiene que mantener a mano — y esta en UN sitio,
no repartida por tres documentos como estaba.

REGLA DE DATOS
---------------
No abre ningun fichero `_LOCAL`, ningun `.DAT`, ningun CSV de facturas. Solo
mira el repositorio y el entorno. Es seguro ejecutarlo en cualquier superficie.

Uso:
    python arranque.py              # rapido (segundos)
    python arranque.py --completo   # ademas corre audit_project.py entero
"""
import os
import subprocess
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))

#: Que bloquea cada dependencia si falta. Sin esto, "falta X" no dice si
#: importa o no — y la respuesta es distinta para cada una.
DEPENDENCIAS = {
    "dbfread": "leer los .dbf del corpus de ContaPlus (sesion LOCAL)",
    "pdfplumber": "leer los PDF de los modelos 303 presentados (sesion LOCAL)",
    "PIL": "dibujar las muestras sinteticas (crear_muestras_sinteticas.py)",
    "anthropic": "captura por IA — BLOQUEADA sin DPA, ver .claude/rules/datos.md",
    "google.genai": "captura por IA — BLOQUEADA sin DPA, ver .claude/rules/datos.md",
}


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=AQUI)
    return r.returncode, r.stdout.strip()


def titulo(texto):
    print()
    print("=" * 70)
    print(texto)
    print("=" * 70)


def seccion(texto):
    print()
    print(f"--- {texto} " + "-" * max(0, 66 - len(texto)))


def main():
    completo = "--completo" in sys.argv

    titulo("LA FABRICA — arranque de sesion")
    print("Esto no es documentacion: cada linea se ha medido ahora mismo.")

    # --- 1. Entorno ---------------------------------------------------------
    seccion("1. Entorno")
    print(f"  interprete   : {sys.executable}")
    print(f"  version      : {sys.version.split()[0]}")
    if sys.platform == "win32":
        print("  sistema      : Windows — en el PC de la asesoria el interprete se")
        print("                 llama `python`, NO `python3`. Los comandos de la")
        print("                 documentacion antigua traen `python3`: sustituir.")
    else:
        print(f"  sistema      : {sys.platform}")
    print(f"  carpeta      : {AQUI}")
    print("  Los scripts se ejecutan SIEMPRE desde aqui, con la carpeta de datos")
    print("  como ARGUMENTO. Nunca al reves.")

    # --- 2. Donde vive el trabajo ------------------------------------------
    # La pregunta que mas caro sale de no hacerse: el repositorio ya tuvo una
    # vez todas las correcciones en ramas claude/* sin fusionar, y quien
    # clonaba master se llevaba la version vieja sin enterarse.
    seccion("2. Donde vive el trabajo (git)")
    codigo, rama = git("rev-parse", "--abbrev-ref", "HEAD")
    if codigo != 0 or not rama:
        # No decir "arbol limpio" aqui seria dar una tranquilidad falsa: no hay
        # arbol. Misma regla que el motor — lo que no se ha podido comprobar no
        # se declara en verde.
        print("  ⚠ ESTA CARPETA NO ES UN REPOSITORIO GIT.")
        print("    No se puede comprobar si el trabajo esta guardado ni si esta")
        print("    donde alguien lo va a encontrar. Nada de lo que hagas aqui")
        print("    tiene copia. Comprueba que estas en la carpeta correcta.")
        hay_git = False
    else:
        hay_git = True
        print(f"  rama actual  : {rama}")
    _, sucio = git("status", "--porcelain") if hay_git else (1, "")
    if hay_git and sucio:
        n = len(sucio.splitlines())
        print(f"  ⚠ arbol      : {n} fichero(s) sin guardar")
    elif hay_git:
        print("  arbol        : limpio")

    _, ramas = git("branch", "-r") if hay_git else (1, "")
    if hay_git and "origin/master" in ramas:
        _, delante = git("log", "--oneline", "origin/master..HEAD")
        _, detras = git("log", "--oneline", "HEAD..origin/master")
        n_delante = len(delante.splitlines()) if delante else 0
        n_detras = len(detras.splitlines()) if detras else 0
        if n_delante:
            print(f"  ⚠ ESTA RAMA VA {n_delante} COMMIT(S) POR DELANTE DE origin/master.")
            print("    Quien clone la rama por defecto NO recibe ese trabajo.")
            print("    Ya paso una vez en este proyecto (ver PROJECT_STATUS.md,")
            print("    entradas del 26-08-2026). Fusionar antes de darlo por cerrado.")
        if n_detras:
            print(f"  ⚠ y va {n_detras} commit(s) POR DETRAS: falta hacer pull.")
        if not n_delante and not n_detras:
            print("  master       : sincronizado, nada se queda atras")

    # --- 2-bis. Las OTRAS ramas, medidas ahora ------------------------------
    # ANADIDO 16-09-2026. Hasta hoy el estado de las ramas se leia de un parrafo
    # escrito a mano en PENDIENTE.md que empezaba por "Medido, no recordado" y
    # daba una rama por vaciada. Era cierto el dia que se escribio y dejo de
    # serlo EL MISMO DIA, en cuanto master avanzo tres commits. Un texto que se
    # presenta como medicion y se recita de memoria es la forma mas cara de
    # equivocarse: se lee al principio de cada sesion y se cree.
    #
    # Asi que se mide. Es la misma regla de siempre en este proyecto -- y el
    # mismo fallo que ya le paso al parrafo de CLAUDE.md que citaba el tamano de
    # PROJECT_STATUS.md ("140 KB" cuando ya iba por 257 KB).
    if hay_git:
        _, otras = git("for-each-ref", "--format=%(refname:short)",
                       "refs/remotes/origin")
        sobrantes, con_trabajo = [], []
        for ref in (otras or "").splitlines():
            ref = ref.strip()
            if not ref or ref.endswith("/HEAD") or ref == "origin/master":
                continue
            _, propios = git("log", "--oneline", f"origin/master..{ref}")
            n_propios = len(propios.splitlines()) if propios else 0
            (con_trabajo if n_propios else sobrantes).append((ref, n_propios))
        if sobrantes or con_trabajo:
            print()
            print("  otras ramas en el remoto (medido ahora, no recordado):")
            for ref, _ in sobrantes:
                print(f"    · {ref}")
                print(f"      no tiene NADA que master no tenga. Es un resto:")
                print(f"      git push origin --delete {ref.split('/', 1)[1]}")
            for ref, n in con_trabajo:
                print(f"    ⚠ {ref}")
                print(f"      tiene {n} commit(s) que master NO tiene. Si esa rama")
                print(f"      se queda ahi, ese trabajo no lo ve nadie.")
        elif rama != "master":
            print("  otras ramas   : ninguna suelta en el remoto")
        print("  Regla permanente (CLAUDE.md, 11-09-2026, con incidente real")
        print("  detras): cada sesion crea su rama, la fusiona a master al")
        print("  terminar y la borra. master es el unico punto de encuentro.")

    # --- 3. Barrera de privacidad ------------------------------------------
    seccion("3. Barrera de privacidad")
    hook = os.path.join(AQUI, ".git", "hooks", "pre-commit")
    if os.path.exists(hook):
        print("  hook pre-commit instalado: el escaner corre en cada commit")
    else:
        print("  ⚠ HOOK NO INSTALADO. Los hooks no se clonan con git.")
        print("    Ponlo AHORA, antes de tocar nada:   sh scripts/install_hooks.sh")
    print("  Recordatorio que manda sobre todo lo demas (.claude/rules/datos.md):")
    print("    - Ningun NIF ni nombre real, en el chat, NUNCA. Tampoco en local.")
    print("    - Ningun fichero *_LOCAL.* se abre jamas.")
    print("    - `FLUJO_CONTINUO_PLAN_DEFINITIVO.md` se cita en CLAUDE.md pero NO")
    print("      esta en el repositorio y no puede estar: vive solo en el PC de")
    print("      la asesoria porque contiene apellidos reales. No lo busques.")

    # --- 4. Dependencias ----------------------------------------------------
    seccion("4. Dependencias — y que bloquea cada una que falte")
    faltan = []
    for modulo, para_que in DEPENDENCIAS.items():
        try:
            __import__(modulo)
            print(f"  OK    {modulo}")
        except ImportError:
            faltan.append(modulo)
            print(f"  falta {modulo:<14} -> {para_que}")
    if faltan:
        print()
        print("  Que falte NO es un defecto del codigo: es el entorno. En el PC de")
        print("  la asesoria hacen falta dbfread y pdfplumber:")
        print("      pip install -r requirements.txt")

    # --- 5. Estado del motor ------------------------------------------------
    seccion("5. Estado del motor")
    if completo:
        print("  Corriendo audit_project.py entero (tarda ~1-2 min)...")
        r = subprocess.run([sys.executable, os.path.join(AQUI, "audit_project.py")],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=AQUI)
        for linea in r.stdout.splitlines():
            if linea.startswith(("✅", "❌", "⚠️")):
                print("   ", linea)
        print()
        print(f"  codigo de salida: {r.returncode}", end="  ")
        print({0: "TODO comprobado y en verde",
               1: ">> HAY UN DEFECTO REAL. Esto manda sobre todo lo demas.",
               2: "nada falla, pero algo no se ha podido comprobar (no es un aprobado)"}
              .get(r.returncode, "desconocido"))
    else:
        print("  No se ha comprobado en esta pasada (tarda ~1-2 min).")
        print("  Antes de tocar el motor, es OBLIGATORIO:")
        print("      python audit_project.py")
        print("  Codigos: 0 = verde | 1 = hay un defecto | 2 = algo sin comprobar")
        print("  (o `python arranque.py --completo` para hacerlo todo de una vez)")

    # --- 5-bis. En que modo estamos ----------------------------------------
    # ANADIDO 16-09-2026 (peticion de Diego). Mientras trabajamos hay que saber
    # SIN preguntar: que puede salir hacia una IA, que puedo ver yo, y para lo
    # que venga a continuacion, que hay que encender. Vivia en la cabeza y en
    # `.claude/rules/datos.md`; ahora se mide y se imprime en cada arranque.
    seccion("5-bis. Modo de trabajo — que puede salir y que puedo ver")
    try:
        import modo_trabajo
        cap = modo_trabajo.medir()
        puerta = ("CERRADA: no sale nada" if not cap["puerta_cloud"] else
                  ("ABIERTA para documentos SINTETICOS declarados"
                   if not cap["puerta_datos_reales"] else
                   "ABIERTA para documentos REALES (con confirmacion por lote)"))
        print(f"  puerta cloud : {puerta}")
        print(f"  claves puestas: GEMINI {'SI' if cap['clave_gemini'] else 'no'}"
              f"   ANTHROPIC {'SI' if cap['clave_anthropic'] else 'no'}"
              f"   (solo presencia, nunca el valor)")
        ve_original = cap["sesion_local"] and cap["clave_anthropic"]
        print(f"  Claude puede ver el documento original: "
              f"{'SI, si hay DPA' if ve_original else 'NO'}")
        listas = [t.nombre for t in modo_trabajo.TAREAS
                  if all(cap.get(n) for n in t.necesita)]
        print(f"  tareas posibles AHORA MISMO: {len(listas)} de {len(modo_trabajo.TAREAS)}")
        for nombre in listas:
            print(f"      · {nombre}")
        print("  El detalle completo, con que falta para cada tarea:")
        print("      python modo_trabajo.py")
    except Exception as e:                       # nunca corta el arranque
        print(f"  No se ha podido medir el modo ({type(e).__name__}).")
        print("  Comprobar a mano:  python modo_trabajo.py")

    # --- 6. Que toca hacer --------------------------------------------------
    seccion("6. Que toca hacer ahora")
    pendiente = os.path.join(AQUI, "PENDIENTE.md")
    if os.path.exists(pendiente):
        # Se salta el bloque de comentario HTML ENTERO, no solo su primera
        # linea: la cabecera de PENDIENTE.md explica como mantenerlo y eso es
        # para quien lo edita, no para quien arranca la sesion.
        with open(pendiente, encoding="utf-8") as f:
            dentro_comentario = False
            for linea in f:
                if not dentro_comentario and linea.lstrip().startswith("<!--"):
                    dentro_comentario = "-->" not in linea
                    continue
                if dentro_comentario:
                    dentro_comentario = "-->" not in linea
                    continue
                print("  " + linea.rstrip())
    else:
        print("  ⚠ No encuentro PENDIENTE.md. Mira EMPEZAR_AQUI.md.")

    titulo("Y AHORA: lee EMPEZAR_AQUI.md")
    print("Es el punto de entrada narrativo: por que las cosas son como son.")
    status_path = os.path.join(AQUI, "PROJECT_STATUS.md")
    if os.path.exists(status_path):
        kb = os.path.getsize(status_path) / 1024
        print(f"PROJECT_STATUS.md ({kb:.0f} KB) es la referencia detallada — se CONSULTA")
    else:
        print("PROJECT_STATUS.md es la referencia detallada — se CONSULTA")
    print("buscando una fecha concreta, no se lee entero al empezar.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
