#!/usr/bin/env python3
"""
AUDITORÍA COMPLETA DEL PROYECTO — un solo comando, toda la batería de pruebas.

Uso: python3 audit_project.py

Pensado para pedirlo desde el móvil en una frase: "Ejecuta la auditoría completa
y dime qué ha cambiado respecto a la última ejecución" — Claude Code lee la salida
de esto y te lo resume, no hace falta que tú interpretes la salida cruda.
"""
import ast
import subprocess
import sys
import json
import os
from datetime import datetime
from pathlib import Path

# Sin esto, una consola de Windows en cp1252 revienta con UnicodeEncodeError en
# el primer ✅/❌ y la auditoría no llega a imprimir ni un resultado. Mismo
# patrón que ya usa scripts/privacy_scan.py. hasattr() porque sys.stdout no
# siempre es un TextIOWrapper real (p.ej. bajo pytest o si algo lo redirige a
# un StringIO, que no tiene .reconfigure() — ver test_motor_veredicto.py).
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RESULTADO = {"fecha": datetime.now().isoformat(timespec="seconds"), "checks": {}}


def check(nombre, ok, detalle=""):
    RESULTADO["checks"][nombre] = {"ok": ok, "detalle": detalle}
    marca = "✅" if ok else "❌"
    print(f"{marca} {nombre}: {detalle}")


def check_sintaxis():
    # CORREGIDO 26-08-2026 (auditoria externa verificada): os.listdir(".") solo
    # mira la raiz del repo. scripts/privacy_scan.py y scripts/*.py nunca habian
    # pasado por este chequeo. Recursivo, excluyendo .git.
    archivos = [str(p) for p in Path(".").rglob("*.py") if ".git" not in p.parts]
    fallos = []
    for f in archivos:
        try:
            ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError as e:
            fallos.append(f"{f}: {e}")
    check("Sintaxis de todos los .py", len(fallos) == 0,
          f"{len(archivos)} archivos revisados (recursivo)" if not fallos else "; ".join(fallos))


def check_cableado():
    """Verifica que todos los guards asignados en evaluar_fila_v4 se consultan de
    verdad en calcular_veredicto_v4 — el bug de los guards fantasma.

    REESCRITO 21-08-2026. La version anterior buscaba `guards.get("X"` con una
    expresion regular, asi que solo veia el cableado escrito de UNA forma. En
    cuanto los AMBAR con rama dedicada pasaron de ocho `if` seguidos a una tabla
    de pares (guard, estado), declaro siete huerfanos que no lo eran: no habia
    cambiado el cableado, habia cambiado su forma.

    Es el mismo error que ya esta documentado en .claude/rules/datos.md sobre el
    escaner de privacidad —decidir por el NOMBRE en vez de por el CONTENIDO— y
    aqui se paga igual de caro, pero al reves: alli dejaba pasar lo peligroso,
    aqui acusa a lo inocente. Un auditor que grita cuando no toca acaba
    ignorandose, y entonces no avisa cuando si toca.

    Ahora recorre el AST y da por consultado cualquier guard cuyo nombre aparezca
    como literal de cadena dentro de calcular_veredicto_v4, venga en una lista,
    en una tabla, en un `if` o en un set. La forma deja de importar.

    Que esto sea mas laxo no afloja la red: audit_estados.py comprueba lo mismo
    por la via dura —moviendo el guard de estado y mirando si el veredicto se
    entera— y ahi no vale mencionar un nombre, hay que reaccionar a el."""
    if not os.path.exists("motor_veredicto.py"):
        check("Cableado de guards", False, "motor_veredicto.py no encontrado")
        return
    arbol = ast.parse(open("motor_veredicto.py", encoding="utf-8").read())
    funcs = {n.name: n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)}
    if "evaluar_fila_v4" not in funcs or "calcular_veredicto_v4" not in funcs:
        check("Cableado de guards", False, "no se encontró evaluar_fila_v4 / calcular_veredicto_v4")
        return

    asignados = set()
    for nodo in ast.walk(funcs["evaluar_fila_v4"]):
        if (isinstance(nodo, ast.Subscript) and isinstance(nodo.value, ast.Name)
                and nodo.value.id == "guards" and isinstance(nodo.slice, ast.Constant)
                and isinstance(nodo.slice.value, str)):
            asignados.add(nodo.slice.value)

    citados = {n.value for n in ast.walk(funcs["calcular_veredicto_v4"])
               if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    huerfanos = asignados - citados
    check("Cableado de guards (sin huérfanos)", len(huerfanos) == 0,
          f"{len(asignados)} guards, todos consultados" if not huerfanos
          else f"HUÉRFANOS: {sorted(huerfanos)}")


def check_modulos_huerfanos():
    """ANADIDO 20-08-2026. El fallo que MAS se repite en este proyecto: construir
    una pieza, probarla aislada, y no conectarla nunca a nada.

    Ya ha pasado tres veces: los tres guards que existian con test propio y
    evaluar_fila_v4 no llamaba (19-08), triangulacion_identidad_v0 que nadie
    importa (20-08), y guard_g7_ledger. check_cableado() solo mira dentro del
    motor; esto mira el repositorio entero.

    Un modulo huerfano no es siempre un error (un script suelto se ejecuta a
    mano), asi que esto AVISA con la lista, no bloquea: lo que no puede pasar es
    que nadie se entere.
    """
    import ast
    py = sorted(f for f in os.listdir(".") if f.endswith(".py"))
    locales = {f[:-3] for f in py}
    importado_por = {f: set() for f in py}
    for f in py:
        try:
            arbol = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue
        for n in ast.walk(arbol):
            mods = []
            if isinstance(n, ast.Import):
                mods = [a.name.split(".")[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.module:
                mods = [n.module.split(".")[0]]
            for m in mods:
                if m in locales and m + ".py" != f:
                    importado_por[m + ".py"].add(f)

    # Los que SE EJECUTAN a mano son legitimos: se reconocen por tener __main__.
    huerfanos = []
    for f in py:
        if importado_por[f]:
            continue
        texto = open(f, encoding="utf-8", errors="ignore").read()
        if "__main__" in texto or f.startswith("test_"):
            continue          # script ejecutable o suite: correcto que nadie lo importe
        huerfanos.append(f)

    check("Modulos sin conectar (ni importados ni ejecutables)", len(huerfanos) == 0,
          "ninguno" if not huerfanos
          else f"{huerfanos} - nadie los importa y no son ejecutables: codigo que no protege de nada")


def check_tests():
    if not os.path.exists("test_motor_veredicto.py"):
        check("Suite de pruebas", False, "test_motor_veredicto.py no encontrado")
        return
    # BUG REAL cazado el 26-08-2026 al ejecutar por primera vez este auditor en
    # el PC de la asesoria (Windows, consola cp1252) en vez de en Cloud (UTF-8).
    # `text=True` sin `encoding` decodifica la salida del proceso hijo con la
    # codificacion del SISTEMA. Los scripts hijos imprimen UTF-8 (⚠️, acentos),
    # asi que en cp1252 el hilo lector muere con UnicodeDecodeError, `stdout`
    # se queda en None y el auditor entero revienta con AttributeError.
    #
    # Lo grave no es el fallo: es DONDE estaba. audit_project.py es el primer
    # comando que EMPEZAR_AQUI.md manda ejecutar, y en la unica maquina donde
    # importa de verdad no llegaba al final. Verde en Cloud, roto en el PC real
    # — la misma familia de "costura" que los dos bugs del 26-08: la pieza de
    # despues no entendia el formato que la de antes si emitia.
    #
    # Los tres subprocess.run de este fichero llevan ya encoding explicito.
    resultado = subprocess.run([sys.executable, "test_motor_veredicto.py"],
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    ok = "TODAS LAS PRUEBAS PASAN" in resultado.stdout
    # CORREGIDO 19-08-2026 (auditoria externa): aqui habia un "21/21 OK" escrito
    # a mano como cadena. No contaba nada: si se anadia o quitaba un check,
    # seguiria imprimiendo "21/21" indefinidamente aunque fuera mentira.
    # Es la misma clase de fallo que el motor existe para evitar — un informe que
    # declara exito sin haberlo medido. Ahora se cuentan las lineas de resultado.
    n_pasan = sum(1 for l in resultado.stdout.splitlines() if l.strip().startswith("OK "))
    n_declarados = 0
    try:
        with open("test_motor_veredicto.py", encoding="utf-8") as f:
            n_declarados = sum(1 for l in f if l.startswith("check("))
    except OSError:
        pass
    detalle = f"{n_pasan}/{n_declarados} checks en verde"
    if ok and n_declarados and n_pasan != n_declarados:
        # La suite dice que pasa todo pero no salen las cuentas: no se da por bueno.
        ok = False
        detalle = (f"la suite declara exito pero solo {n_pasan} de {n_declarados} "
                   f"checks han reportado OK - revisar")
    check("Suite de pruebas (test_motor_veredicto.py)", ok,
          detalle if ok else f"{detalle}\n{resultado.stdout[-500:]}")


def check_adversarial():
    """ANADIDO 19-08-2026. La suite de regresion comprueba que lo que funcionaba
    sigue funcionando; esta comprueba que el motor no puede dar un VERDE por
    falta de informacion. Son preguntas distintas y hacen falta las dos: el
    19-08-2026 la regresion estaba 21/21 en verde mientras el motor daba VERDE a
    una factura sin un solo importe legible."""
    if not os.path.exists("test_adversarial.py"):
        check("Bateria adversarial", False, "test_adversarial.py no encontrado")
        return
    resultado = subprocess.run([sys.executable, "test_adversarial.py"],
                                capture_output=True, text=True,
                                encoding="utf-8", errors="replace")
    ok = resultado.returncode == 0
    linea = next((l for l in resultado.stdout.splitlines() if l.startswith("Pruebas:")), "")
    check("Bateria adversarial (test_adversarial.py)", ok,
          linea or resultado.stdout[-300:])


def check_estados_y_cobertura():
    """ANADIDO 21-08-2026. La tercera pregunta, la que faltaba.

    check_cableado()  ->  ¿el guard existe y alguien lo llama?
    cobertura_guards  ->  ¿ha llegado alguna vez a decir que no?
    audit_estados     ->  ¿lo que dice cambia el veredicto?

    La tercera aparecio por las malas: guard_cuenta_gasto_coherente estaba
    cableado, su rama FALLO -> AMBAR llevaba semanas escrita en el veredicto, y
    era inalcanzable porque el guard no comparaba nada. Las otras dos preguntas
    daban verde. Se cablea aqui para que no dependa de que alguien se acuerde.
    """
    for script, etiqueta in (("audit_estados.py", "Estados: sin ramas muertas ni guards mudos"),
                             ("cobertura_guards.py", "Cobertura: guards probados de verdad"),
                             # Ensayo en seco de la cadena que se ejecuta en LOCAL.
                             # Corre en 0,4 s y en su PRIMERA ejecucion destapo que
                             # --emitir-cartera no escribia nada, nunca: el ultimo
                             # eslabon de "el criterio sale de los diez anos" estaba
                             # roto con las dos puntas hechas.
                             ("ensayo_retro_semaforo.py", "Ensayo en seco: retro_semaforo + orquestador"),
                             # construir_historico_y_secuencia() no tenia ningun
                             # ensayo propio. Encontro un bug real el 26-08-2026
                             # (auditoria propia): con importes en formato
                             # espanol, el historico que alimenta importe_atipico
                             # se quedaba vacio en silencio.
                             ("ensayo_orquestador.py", "Historico del orquestador: no pierde facturas por formato"),
                             # No elige los ataques: los enumera. En su primera
                             # pasada encontro tres defectos que ninguno de los
                             # 87 ataques escritos a mano habia tocado.
                             ("barrido_falsos_verdes.py", "Barrido: ningun falso verde sin explicar"),
                             # La barrera mas importante del proyecto no tenia
                             # ni una prueba, y ya fallo una vez de la peor
                             # forma posible: declarando limpio lo que no habia
                             # mirado. Aquella comprobacion a mano corre sola.
                             ("test_privacidad.py", "Barrera de privacidad: bloquea lo que debe"),
                             # El ultimo paso: el fichero que entra en ContaPlus.
                             # Un fallo aqui no cuesta tiempo, cuesta
                             # contabilidad — y se encontro uno de verdad: la
                             # factura de camara generaba un asiento de una sola
                             # linea, descuadrado.
                             ("ensayo_xdiario.py", "xDiario: ningun asiento descuadrado"),
                             # La costura entre lo que la captura PIDE y lo que
                             # el motor USA. Son dos listas en ficheros distintos
                             # y nada comprobaba que coincidieran: si dejan de
                             # hacerlo no salta nada, el campo llega con otro
                             # nombre y la factura sale AMBAR "por la captura".
                             ("ensayo_contrato_captura.py", "Captura <-> motor: los campos cuadran"),
                             # Un fichero corrupto entre 1.287 no puede parar la
                             # medicion. Y colgaba: cabecera con len_reg=0 ->
                             # bucle infinito, sin error y sin acabar.
                             ("ensayo_corpus_roto.py", "Corpus roto: no cuelga ni contamina"),
                             # cruzar_303_importes.py solo puede ejecutarse de
                             # verdad contra el archivo real del despacho, en la
                             # maquina del titular. Sin ensayo, llegaria a su
                             # unica ejecucion real sin haberse ejecutado nunca
                             # — la situacion exacta que el 21-08 produjo tres
                             # defectos en la primera pasada de los comandos
                             # LOCAL. Aqui se prueba la logica del cruce con
                             # importes inventados, sin abrir un solo PDF.
                             ("ensayo_cruce_303.py", "Cruce 303: identifica sin inventar"),
                             # reconstruir_303.py se reescribio el 27-08-2026 para
                             # derivar la base del asiento en vez de leer BASEIMPO
                             # a pelo (BASEIMPO es un cero literal en el 99,4% de
                             # los apuntes reales, medido con diag_baseimpo.py).
                             # Este ensayo prueba lo que ensayo_retro_semaforo.py
                             # no ejercita: multi-tipo en un mismo asiento,
                             # BASEIMPO genuinamente relleno (el 0,6% restante,
                             # que tiene que GANAR sobre lo derivado), y que un
                             # asiento repetido entre copias se deduplique
                             # completo, no linea a linea.
                             ("ensayo_reconstruir_303.py", "Reconstruir 303: deriva la base, no la inventa"),
                             # emparejar_carpetas.py (27-08-2026) tuvo un
                             # defecto real, encontrado contra el corpus real:
                             # un filtro de "carpetas genericas" por palabra
                             # clave hizo caer las coincidencias de confianza
                             # ALTA de 14 a 0, porque un negocio real puede
                             # llamarse "Ferreteria General". Retirado el
                             # mismo dia; este ensayo evita que vuelva.
                             ("ensayo_emparejar_carpetas.py", "Emparejar carpetas: por nombre, sin adivinar por palabra"),
                             # Auditor nuevo (27-08-2026). No caza un caso: caza
                             # una FORMA de falso verde. `if x > 0 and <comp>:
                             # return FALLO` seguido de `return OK` convierte
                             # "no he podido comprobar" en "todo correcto".
                             # Aparecio DOS veces, en guards distintos escritos
                             # en momentos distintos (guard_importe_atipico y
                             # guard_secuencia_documental_proveedor), y solo se
                             # vio al despertarlos. Una leccion escrita en un
                             # documento no impide que vuelva dentro de tres
                             # meses en el guard numero 27.
                             ("ensayo_ok_sin_comprobar.py", "Falso verde estructural: ningun OK que signifique 'no lo he comprobado'")):
        if not os.path.exists(script):
            check(etiqueta, False, f"{script} no encontrado")
            continue
        r = subprocess.run([sys.executable, script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        salida = r.stdout or ""
        linea = next((l.strip() for l in reversed(salida.splitlines())
                      if "cobertura util" in l or "✗" in l), "")
        check(etiqueta, r.returncode == 0, linea or salida.strip().splitlines()[-1:][0] if salida.strip() else "")


def check_dependencias():
    if not os.path.exists("requirements.txt"):
        check("requirements.txt", False, "no encontrado")
        return
    faltan = []
    for linea in open("requirements.txt"):
        paquete = linea.split(">=")[0].split("#")[0].strip()
        if not paquete:
            continue
        modulo = {"google-genai": "google.genai", "dbfread": "dbfread",
                  "anthropic": "anthropic"}.get(paquete, paquete)
        try:
            __import__(modulo)
        except ImportError:
            faltan.append(paquete)
    check("Dependencias instaladas", len(faltan) == 0,
          "todas presentes" if not faltan else f"faltan: {faltan}")


def check_subprocess_encoding():
    """ANADIDO 26-08-2026. Toda llamada a subprocess.run con text=True tiene
    que declarar `encoding`.

    POR QUE ES UN AUDITOR Y NO UN ARREGLO PUNTUAL: sin `encoding`, Python
    decodifica la salida del proceso hijo con la codificacion del SISTEMA
    (cp1252 en un Windows espanol). Un solo byte UTF-8 sin equivalente mata el
    hilo lector, `stdout` se queda en None, y el script revienta con un
    AttributeError que no dice nada del problema real.

    Lo peor: NO se nota en Cloud, donde la consola es UTF-8. Solo aparece en
    el PC de la asesoria, que es justo la maquina donde el proyecto importa.
    Este fichero lo sufrio (audit_project.py no llegaba al final) y ademas
    estaba latente, sin haber saltado todavia, en ensayo_corpus_roto.py y en
    las cuatro llamadas de test_privacidad.py.

    Se comprueba sobre el AST, no sobre el texto: la leccion del 21-08-2026
    con check_cableado fue que un auditor que mira la FORMA acusa a inocentes
    en cuanto alguien reformatea una linea."""
    fallos = []
    revisadas = 0
    # Misma recorrida recursiva que check_sintaxis(): si un fichero de
    # scripts/ queda fuera del barrido, el agujero vuelve por ahi.
    for f in [str(p) for p in Path(".").rglob("*.py") if ".git" not in p.parts]:
        try:
            arbol = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue                       # ya lo reporta check_sintaxis()
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            fn = nodo.func
            nombre = ""
            if isinstance(fn, ast.Attribute):
                nombre = fn.attr
                if isinstance(fn.value, ast.Name):
                    nombre = f"{fn.value.id}.{fn.attr}"
            if nombre not in ("subprocess.run", "run"):
                continue
            claves = {k.arg for k in nodo.keywords if k.arg}
            # Sin text=True devuelve bytes: no hay decodificacion que fallar.
            if not claves & {"text", "universal_newlines"}:
                continue
            revisadas += 1
            if "encoding" not in claves:
                fallos.append(f"{os.path.basename(f)}:{nodo.lineno}")
    check("subprocess.run: encoding explicito", not fallos,
          f"{revisadas} llamadas con text=True, todas declaran encoding"
          if not fallos else
          f"sin encoding (revientan en consola cp1252): {', '.join(fallos)}")


def comparar_con_anterior():
    path_historico = ".audit_historico.json"
    anterior = None
    if os.path.exists(path_historico):
        anterior = json.load(open(path_historico))
    if anterior:
        print("\n--- Comparación con la ejecución anterior ---")
        for nombre, actual in RESULTADO["checks"].items():
            previo = anterior.get("checks", {}).get(nombre)
            if previo and previo["ok"] != actual["ok"]:
                cambio = "MEJORÓ" if actual["ok"] else "EMPEORÓ"
                print(f"  ⚠️  {nombre}: {cambio} desde la última ejecución ({anterior['fecha']})")
    with open(path_historico, "w") as f:
        json.dump(RESULTADO, f, indent=2)


if __name__ == "__main__":
    print("=== AUDITORÍA COMPLETA DEL PROYECTO ===\n")
    check_sintaxis()
    check_cableado()
    check_modulos_huerfanos()
    check_dependencias()
    check_tests()
    check_adversarial()
    check_estados_y_cobertura()
    check_subprocess_encoding()
    comparar_con_anterior()

    todos_ok = all(c["ok"] for c in RESULTADO["checks"].values())
    print(f"\n{'='*40}")
    print("✅ TODO CORRECTO" if todos_ok else "❌ HAY PROBLEMAS QUE REVISAR")
    sys.exit(0 if todos_ok else 1)
