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

#: Toda suite que esta auditoria EJECUTA DE VERDAD queda anotada aqui, por la
#: unica puerta por la que se ejecutan (`ejecutar_suite`). No es una lista que
#: se mantenga a mano: es el registro de lo que ha corrido en ESTA pasada, y es
#: lo que lee check_suites_sin_cablear() al final.
#:
#: POR QUE NO SE MIRA SI EL NOMBRE APARECE EN ESTE FICHERO: aparece. Este
#: fichero esta lleno de nombres `.py` dentro de comentarios que explican por
#: que tal ensayo cubre lo que tal otro no. Un `grep` daria por cableada
#: cualquier suite NOMBRADA, incluida una nombrada precisamente para explicar
#: que se deja fuera. Seria la barrera por nombre que `.claude/rules/datos.md`
#: llama "de conveniencia", y el falso verde que el motor tiene prohibido dar.
SUITES_EJECUTADAS = set()


#: Los mismos tres estados que usa el motor. La auditoria no puede permitirse
#: menos precision que lo que audita: hasta el 09-09-2026 solo tenia ✅ y ❌, y
#: eso obligaba a pintar de rojo cosas que nadie habia llegado a comprobar
#: (una dependencia ausente), indistinguibles de un defecto real. El resultado
#: practico era peor que el bug: `EMPEZAR_AQUI.md` documentaba la salida
#: esperada de la auditoria CON un ❌ dentro y la anotaba "NORMAL". Un rojo que
#: se enseña a ignorar deja de ser un rojo, y el siguiente rojo de verdad se
#: va con el.
OK = "OK"
FALLO = "FALLO"
NO_COMPROBADO = "NO_COMPROBADO"

MARCA = {OK: "✅", FALLO: "❌", NO_COMPROBADO: "⚠️"}


def check(nombre, ok, detalle="", estado=None):
    """`ok` sigue aceptando un booleano para no tocar las diez llamadas que ya
    existen. `estado=NO_COMPROBADO` es la tercera via: ni afirma que esta bien
    ni acusa de estar mal — dice que no se ha podido mirar, que es la verdad y
    no aparecia por ningun sitio."""
    if estado is None:
        estado = OK if ok else FALLO
    RESULTADO["checks"][nombre] = {
        # Se conserva `ok` booleano: `.audit_historico.json` de ejecuciones
        # anteriores lo tiene, y comparar_con_anterior() lo lee.
        "ok": estado == OK,
        "estado": estado,
        "detalle": detalle,
    }
    print(f"{MARCA[estado]} {nombre}: {detalle}")


def ejecutar_suite(script):
    """Unica puerta por la que esta auditoria lanza una suite. Anota el nombre
    en SUITES_EJECUTADAS ANTES de lanzarla, para que una suite que reviente,
    cuelgue o salga en rojo siga contando como ejecutada: lo que
    check_suites_sin_cablear() persigue es la suite que NADIE mira, no la que
    falla (esa ya sale en rojo por su propio check)."""
    # Se anota la RUTA relativa tal cual, no el nombre a secas: dos suites con
    # el mismo nombre en directorios distintos (ensayo_x.py y sub/ensayo_x.py)
    # se taparian la una a la otra, y ejecutar una daria la otra por cubierta.
    # Un falso verde por colision de nombres es un falso verde igual.
    SUITES_EJECUTADAS.add(Path(script).as_posix())
    return subprocess.run([sys.executable, script], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


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
    # Pasa por ejecutar_suite() para quedar anotada en SUITES_EJECUTADAS.
    resultado = ejecutar_suite("test_motor_veredicto.py")
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
    resultado = ejecutar_suite("test_adversarial.py")
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
                             # validar_captura_historica.py produce el UNICO
                             # numero del proyecto con umbral duro acordado por
                             # adelantado: un solo falso verde para la
                             # automatizacion (SIGUIENTES_PASOS.md §4). Hasta el
                             # 09-09-2026 sus unicas dos comprobaciones vivian
                             # dentro de ensayo_retro_semaforo.py y solo
                             # verificaban que ARRANCA: las 12 filas que se le
                             # daban eran todas VERDE/VERDE y no se comprobaba
                             # ni un numero de la salida. Si contara mal los
                             # falsos verdes, aquel ensayo seguiria en verde.
                             ("ensayo_validar_captura.py", "Falsos verdes: los cuenta, no los inventa"),
                             # cuadre_303_ficha.py es la via de REVISION HUMANA
                             # al cuadre contra el 303 presentado, que es "la
                             # unica verdad externa que este proyecto va a tener
                             # nunca" (SIGUIENTES_PASOS.md §3.3). Construido el
                             # 26-08, declarado "lo primero de manana" el 27-08,
                             # y sin un solo ensayo hasta el 09-09. Lo que se
                             # vigila sobre todo: que el numero que se elige en
                             # el paso 2 sea la MISMA carpeta que la lista del
                             # paso 1 prometia — si se descoloca, se compara la
                             # contabilidad de un cliente contra el 303 de otro.
                             ("ensayo_cuadre_ficha.py", "Ficha de cuadre 303: el numero elegido es la carpeta prometida"),
                             # arranque.py esta en el camino de arranque de TODA
                             # sesion desde el 10-09-2026 (hook SessionStart).
                             # Eso cambia lo que significa que falle: no es un
                             # script que da error cuando lo llamas, es que
                             # TODAS las sesiones empiezan con un error. Y corre
                             # en la maquina que tiene los datos reales delante,
                             # asi que tampoco puede abrir un _LOCAL ni por
                             # descuido (se comprueba sobre el AST, no buscando
                             # la palabra en el texto).
                             ("ensayo_arranque.py", "Arranque de sesion: no revienta, no toca datos, avisa de lo que importa"),
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
                             ("ensayo_ok_sin_comprobar.py", "Falso verde estructural: ningun OK que signifique 'no lo he comprobado'"),
                             # ---------------------------------------------------
                             # CABLEADAS EL 11-09-2026. Las siete existian en el
                             # repositorio, en verde, y esta auditoria NO las
                             # ejecutaba: la tupla se mantiene a mano y se habia
                             # quedado atras. Demostrado por sabotaje antes de
                             # arreglarlo: con ensayo_validar_captura_historica.py
                             # roto a proposito, la auditoria completa salia
                             # IDENTICA a la del repositorio sano, codigo 2, sin
                             # un solo ❌. check_suites_sin_cablear(), al final de
                             # este fichero, impide que la lista vuelva a
                             # quedarse atras sin que nadie se entere.
                             # ---------------------------------------------------
                             # La que mas urgia: valida el script que produce el
                             # UNICO numero con umbral acordado por adelantado, y
                             # es la unica que fija la regresion del bug P0 del
                             # 21-08 ("0.0% miente" con separador roto). Su
                             # hermana ensayo_validar_captura.py SI estaba
                             # cableada, pero cubre otra cosa: que CUENTE bien.
                             # Esta cubre que no MIENTA cuando no puede contar,
                             # mas la acumulacion incremental del historico y su
                             # orden cronologico. Ninguna de las tres regresiones
                             # estaba protegida por la auditoria hasta hoy.
                             ("ensayo_validar_captura_historica.py", "Captura historica: ni miente con 0.0% ni pierde el orden"),
                             # Los tres scripts de identidad se refactorizaron el
                             # 27-08 para exponer funcion reutilizable. Sus
                             # ensayos se escribieron ese mismo dia; nadie los
                             # volvio a correr salvo a mano.
                             ("ensayo_enlazador_clientes_303.py", "Enlazador 303: agrupa por proveedor compartido sin cambiar el resultado"),
                             ("ensayo_diag_carpetas_multiempresa.py", "Carpetas multiempresa: distingue mezcla de sana sin falsos positivos"),
                             ("ensayo_diag_calibracion_sospechosa.py", "Calibracion SOSPECHOSA: separa mezcla real de artefacto temporal"),
                             # Cruza las tres senales anteriores. Es la unica que
                             # prueba el caso que ninguna de ellas ve por separado.
                             ("ensayo_consolidar_identidad.py", "Consolidar identidad: ve lo que ninguna senal suelta puede ver"),
                             # comparar_esquema_dbf.py ya se ejecuto contra el
                             # ContaPlus real de la asesoria (09-09, salio
                             # IDENTICO). Es lo que avisara si ContaSOL cambia el
                             # layout del DBF: si se rompe en silencio, el aviso
                             # no llega el dia que importa.
                             ("test_comparar_esquema_dbf.py", "Esquema DBF: la comparacion contra ContaPlus/ContaSOL sigue en pie"),
                             # Primera pieza del modulo de facturas EMITIDAS. Su
                             # invariante (correlatividad sin huecos) es
                             # requisito de VeriFactu, no una comodidad.
                             ("test_numeracion_correlativa.py", "Numeracion correlativa: sin huecos, sin duplicados, sin retrocesos"),
                             # El ensayo del auditor que cerro este agujero. Un
                             # auditor que se apaga en silencio deja el agujero
                             # PEOR que antes, porque ademas lo firma como
                             # revisado (11o auditor, dos semanas apagado,
                             # PROJECT_STATUS.md 09-09-2026). Prueba propia de
                             # que funciona: en cuanto se escribio, y antes de
                             # anadir esta linea, check_suites_sin_cablear()
                             # puso la auditoria en rojo por ELLA MISMA.
                             ("ensayo_suites_cableadas.py", "Suites cableadas: el auditor que caza la prueba que nadie ejecuta"),
                             # verificar_303_pdf.py (11-09-2026): compara la
                             # reconstruccion contra el PDF real SIN adivinar
                             # identidad -- eso lo resuelve Diego a mano, este
                             # script solo hace la resta. Ensayo sabotea el
                             # umbral de redondeo y el mapeo de casillas del
                             # 303; las dos veces cae solo la comprobacion
                             # exacta que tocaba.
                             ("ensayo_verificar_303_pdf.py", "Verificacion 303 vs PDF: compara sin adivinar identidad"),
                             # Hallazgo real 14-09-2026: el "tipo 0" que aparece
                             # en casi toda ficha no es una venta o compra --
                             # es el asiento de liquidacion/cierre de IVA
                             # (diag_patron_cierre_iva.py mide el ratio de
                             # cancelacion sobre 303_LOCAL.json; diag_contra-
                             # partida_tipo0.py confirma la cuenta contraria en
                             # el Diario.dbf real). Arreglo consecuente en
                             # cuadre_303_ficha.py: el tipo "0" ya no se suma
                             # al TOTAL.
                             ("ensayo_diag_patron_cierre_iva.py", "Patron de liquidacion IVA: ratio de cancelacion, no ruido"),
                             ("ensayo_diag_contrapartida_tipo0.py", "Contrapartida del tipo 0: distingue liquidacion de caso ambiguo"),
                             # extraer_303_pdf.py sostiene TODO el cuadre contra
                             # el 303 -- verificar_303_pdf.py importa su lectura
                             # de casillas en vez de reescribirla, justo para que
                             # no puedan divergir -- y no tenia ni una prueba. Su
                             # propio comentario decia que los patrones eran
                             # "variantes razonables porque NO SE HA VISTO NI UN
                             # SOLO DOCUMENTO REAL". El 14-09-2026 se vio: la
                             # etiqueta es un recuadro de dos digitos pegado a su
                             # valor, y el patron adivinado casaba con el "9." de
                             # DENTRO de "9.999,99".
                             ("ensayo_extraer_casillas.py", "Casillas del 303: se leen de la rejilla, no de dentro de un importe"),
                             # El registro de constantes externas es un auditor
                             # mas, y uno apagado en silencio deja el agujero
                             # PEOR que antes porque ademas lo firma como
                             # revisado. Lo que prueba no es que los numeros
                             # sean correctos --eso lo dice la fuente oficial,
                             # no un test-- sino que el mecanismo sabe darse
                             # cuenta de que uno cambio o de que la
                             # verificacion envejecio.
                             ("ensayo_fuentes_externas.py", "Fuentes externas: el registro sabe darse cuenta"),
                             # Lo que prueba NO es que las citas legales sean
                             # correctas -- eso lo dice el texto oficial, no un
                             # test. Prueba que una cita PROPUESTA no pueda pasar
                             # por verificada por el paso del tiempo, que es el
                             # riesgo real de un registro de autoridad.
                             ("ensayo_autoridad_guards.py", "Autoridad de los guards: una propuesta no es un hecho"),
                             # El detector de cambios del BOE. No toca la red en
                             # el ensayo, a proposito: descargar lo haria fallar
                             # sin salida a internet, tardar en cada auditoria y
                             # --lo peor-- dejar de ser determinista. Lo que
                             # prueba es que elige la redaccion EN VIGOR (el
                             # consolidado trae las historicas Y las reformas de
                             # entrada en vigor futura) y que un fallo de red no
                             # se confunde con "no ha cambiado".
                             ("ensayo_boe_normativa.py", "BOE: elige la redaccion en vigor, y no aprueba lo que no ha podido leer"),
                             # El registro de modelos AEAT. Tampoco toca la red,
                             # por lo mismo. Lo que prueba es la FORMA: que cada
                             # entrada trae lo que la vigilancia necesita, que no
                             # hay huellas repetidas (senal de copiar-pegar), que
                             # un modelo no puede estar a la vez registrado y
                             # "pendiente de identificar", y que boe_normativa
                             # los recoge de verdad -- leyendo su codigo como
                             # texto, no ejecutandolo.
                             ("ensayo_modelos_aeat.py", "Modelos AEAT: el impreso que cambia sin avisar"),
                             # La puerta por la que sale (o no) un documento
                             # hacia una IA. No toca la red ni abre ningun
                             # fichero: ejercita la DECISION. Va aqui porque es
                             # la frontera de datos del proyecto convertida en
                             # mecanismo, y una barrera que nadie intenta forzar
                             # no es una barrera, es una intencion -- por eso la
                             # bateria incluye sus propios controles negativos.
                             ("test_puerta_cloud.py", "Puerta cloud: cerrada por defecto, y lo no declarado es real"),
                             # El informe de modo. Lo que vigila por encima de
                             # todo es que, existiendo para IMPRIMIR el estado
                             # —y el estado incluye si hay claves puestas—, no
                             # imprima NUNCA el valor de una. Se comprueba con
                             # una clave trampa en el entorno.
                             ("ensayo_modo_trabajo.py", "Modo de trabajo: mide el estado sin filtrar ninguna clave"),
                             # La cadena entera captura -> CSV -> motor, sin
                             # API. Es la costura que ensayo_contrato_captura
                             # NO cubre: aquel compara los NOMBRES de campo
                             # entre dos ficheros; este EJECUTA el viaje. Al
                             # escribirlo aparecio un defecto real y dormido
                             # (los campos anidados del prompt v2 no sobrevivian
                             # a la serializacion del CSV).
                             ("ensayo_cadena_captura.py", "Cadena captura->CSV->motor: los campos anidados sobreviven"),
                             # crear_muestras_sinteticas.py (16-09-2026): los
                             # documentos contra los que se mide el OCR. Una
                             # regla de medida torcida es peor que no tener
                             # regla -- un fallo en la muestra se lee como "el
                             # modelo no sabe leer" y se persigue al sitio
                             # equivocado. La bateria sabotea el dibujo (texto
                             # en blanco sobre blanco, el defecto que de verdad
                             # ocurrio) y comprueba que el guard de tinta se
                             # pone rojo en las tres recetas.
                             ("test_muestras_sinteticas.py", "Muestras sinteticas: la regla de medir no esta torcida"),
                             # comparar_captura_vs_verdad.py (16-09-2026): la
                             # herramienta que decide si la cadena foto->IA->motor
                             # funciona. Si se equivoca, se equivoca hacia el lado
                             # peor -- dando por bueno lo que no lo es. Y ademas
                             # IMPRIME valores, asi que lleva una barrera: lo que
                             # no esta declarado SINTETICO se trata como REAL y no
                             # se imprime ni un valor, ni un nombre, ni una ruta.
                             # La bateria la sabotea de dos formas y exige que se
                             # ponga roja las dos veces.
                             ("test_comparar_captura.py", "Comparador captura/verdad: mide, y no filtra"),
                             # comparar_dos_lecturas_reales.py (17-09-2026): compara
                             # DOS lecturas reales entre si (misma foto, dos llamadas
                             # a Gemini). A diferencia del anterior, aqui NINGUNA de
                             # las dos entradas puede ser sintetica -- no hay "es_
                             # sintetico" que autorice imprimir nada. La bateria
                             # planta un senuelo en un campo que DIFIERE a proposito
                             # y exige que nunca llegue a la salida.
                             ("test_comparar_dos_lecturas.py", "Comparador de dos lecturas reales: nunca imprime un valor")):
        if not os.path.exists(script):
            check(etiqueta, False, f"{script} no encontrado")
            continue
        r = ejecutar_suite(script)
        salida = r.stdout or ""
        linea = next((l.strip() for l in reversed(salida.splitlines())
                      if "cobertura util" in l or "✗" in l), "")
        check(etiqueta, r.returncode == 0, linea or salida.strip().splitlines()[-1:][0] if salida.strip() else "")


def check_fuentes_externas():
    """ANADIDO 15-09-2026. Hay numeros en este codigo que no decidimos
    nosotros: los tipos de IVA los fija la ley, las casillas del 303 la AEAT.
    Si una cambia y aqui no, el motor no falla -- acierta menos, en silencio,
    que es peor.

    `fuentes_externas.py` anota de donde sale cada uno y cuando se verifico.
    Esto comprueba las dos cosas que se pueden comprobar sin leer el BOE:

      - que el valor anotado sigue siendo el que tiene el codigo,
      - y que la verificacion no ha envejecido.

    Una verificacion caducada NO dice que la norma haya cambiado: dice que
    nadie lo ha vuelto a mirar. Por eso sale NO_COMPROBADO y no FALLO -- es
    la misma distincion que el motor hace entre "esto esta mal" y "esto no lo
    he podido comprobar".
    """
    try:
        import fuentes_externas as fx
    except ImportError as e:
        check("Fuentes externas", False, f"no se puede importar ({type(e).__name__})")
        return
    disc, cad, sinver = fx.revisar()
    partes = [f"{len(fx.FUENTES)} constantes registradas"]
    if disc:
        partes.append("NO COINCIDEN CON EL CODIGO: "
                      + "; ".join(f"{k} ({d})" for k, d in disc))
    if cad:
        partes.append("verificacion envejecida (nadie lo ha mirado, no es que haya "
                      "cambiado): " + ", ".join(f"{k} desde {f} ({m} meses)"
                                                 for k, f, m in cad))
    if sinver and not disc and not cad:
        partes.append("sin verificar del todo: "
                      + ", ".join(f"{k} [{e}]" for k, e in sinver))
    check("Fuentes externas: los numeros que no decidimos nosotros",
          not disc and not cad, " | ".join(partes),
          estado=(FALLO if disc else (NO_COMPROBADO if cad else OK)))


def check_autoridad_guards():
    """ANADIDO 15-09-2026. El motor tiene 28 guards que codifican reglas
    contables y fiscales. `autoridad_guards.py` anota, para cada uno, si lo que
    aplica es una NORMA, es CALIDAD DEL DATO, o es CRITERIO del despacho.

    Esto comprueba que ninguno se quede sin esa decision -- misma idea que
    check_cableado y que check_suites_sin_cablear: un guard nuevo nace con la
    pregunta contestada, o la auditoria se pone roja.

    NO comprueba que las citas sean correctas: eso no lo puede decir un
    programa, lo dice el texto oficial. Por eso el recuento de VERIFICADAS se
    imprime aparte y hoy es CERO de 16 -- todo son propuestas para validar.
    Imprimirlo en cada pasada es lo que impide que una propuesta se convierta
    en un hecho por el simple paso del tiempo.
    """
    try:
        import autoridad_guards as ag
    except ImportError as e:
        check("Autoridad de los guards", False, f"no se puede importar ({type(e).__name__})")
        return
    sin_autoridad, sobran, por_estado, por_origen = ag.revisar()
    verificadas = por_estado.get(ag.VERIFICADO, 0)
    total_norma = por_origen.get(ag.NORMA, 0)
    partes = [f"{sum(por_origen.values())} guards anotados "
              f"({total_norma} norma, {por_origen.get(ag.TECNICO, 0)} tecnicos, "
              f"{por_origen.get(ag.CRITERIO, 0)} criterio)",
              f"citas verificadas contra el texto oficial: {verificadas}/{total_norma}"]
    if sin_autoridad:
        partes.append("SIN ANOTAR: " + ", ".join(sin_autoridad)
                      + " - un guard sin decidir si aplica norma o criterio")
    if sobran:
        partes.append(f"anotaciones que sobran (ese guard ya no existe): {sobran}")
    check("Autoridad de los guards: norma, dato o criterio",
          not sin_autoridad and not sobran, " | ".join(partes))


def check_dependencias():
    if not os.path.exists("requirements.txt"):
        check("requirements.txt", False, "no encontrado")
        return
    faltan = []
    for linea in open("requirements.txt"):
        paquete = linea.split(">=")[0].split("#")[0].strip()
        if not paquete:
            continue
        # El nombre del PAQUETE que se instala no siempre es el del MODULO que
        # se importa. Pillow se instala como "Pillow" y se importa como "PIL":
        # sin esta linea la auditoria intentaria `import Pillow`, fallaria, y
        # declararia que falta una dependencia que SI esta instalada -- un aviso
        # falso, que es tan malo como un verde falso porque ensena a ignorarlos.
        modulo = {"google-genai": "google.genai", "dbfread": "dbfread",
                  "anthropic": "anthropic", "Pillow": "PIL"}.get(paquete, paquete)
        try:
            __import__(modulo)
        except ImportError:
            faltan.append(paquete)
    # Una dependencia que no esta instalada NO es un defecto del proyecto: es
    # una condicion del entorno. Marcarla ❌ ponia la auditoria entera en rojo
    # permanente en cualquier maquina sin los SDK de captura (que ademas no se
    # pueden usar sin DPA, ver .claude/rules/datos.md), y de paso hacia que el
    # codigo de salida no distinguiera "hay un defecto" de "falta un pip
    # install". Ahora es NO_COMPROBADO y sale por su propia puerta.
    check("Dependencias instaladas", not faltan,
          "todas presentes" if not faltan else
          f"sin instalar (no es un defecto del codigo, es el entorno): {faltan}",
          estado=None if not faltan else NO_COMPROBADO)


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


def check_salida_al_importar():
    """ANADIDO 09-09-2026. Ningun modulo que otro fichero importe puede
    llamar a sys.exit() al ser importado.

    POR QUE ES UN AUDITOR Y NO UN ARREGLO PUNTUAL: `cruzar_303_importes.py`
    tenia un `sys.exit(1)` en el cuerpo del modulo, dentro del `except
    ImportError` de pdfplumber. Consecuencia: `ensayo_cruce_303.py` —el 11o
    auditor, el unico que prueba la logica del cruce— moria en su linea de
    import en TODO clon sin pdfplumber, sin llegar a ejecutar ni una de sus 22
    comprobaciones. Y ese ensayo, por diseno explicito, no abre ni un PDF:
    sustituye `importes_del_pdf` por una funcion que devuelve importes
    inventados. Estaba apagado por una dependencia que su camino no toca.

    Lo grave no es el fallo, es la forma que tomaba: la auditoria lo mostraba
    como un ❌ rojo indistinguible de "el ensayo ha encontrado un defecto".
    Es el mismo error que el escaner de privacidad cometio el 19-08 con el
    color cambiado — alli un OK que significaba "no lo he mirado", aqui un
    FALLO que significa lo mismo. En un motor cuyo principio es que un estado
    nunca puede afirmar lo que no ha comprobado, la auditoria tampoco.

    Solo se acusa a los modulos que ALGUIEN IMPORTA. Un script suelto como
    `test_adversarial.py` termina con `sys.exit(0/1)` a nivel de modulo a
    proposito y eso es correcto: nadie lo importa, se ejecuta. Acusarlo seria
    repetir la leccion del 21-08 con check_cableado — un auditor que mira la
    FORMA acusa a inocentes.
    """
    ficheros = [p for p in Path(".").rglob("*.py") if ".git" not in p.parts]

    # 1. Que modulos del proyecto importa alguien. Es un hecho del AST, no una
    #    lista escrita a mano que se quede desfasada.
    importados = set()
    arboles = {}
    for f in ficheros:
        try:
            arboles[f] = ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError:
            continue                       # ya lo reporta check_sintaxis()
    for f, arbol in arboles.items():
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    importados.add(alias.name.split(".")[0])
            elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                importados.add(nodo.module.split(".")[0])

    # 2. Sentencias que se ejecutan DE VERDAD al importar: el cuerpo del modulo
    #    y lo anidado dentro de try/if/for, pero nunca el interior de una
    #    funcion o clase (eso no corre hasta que se llama) ni el bloque
    #    `if __name__ == "__main__"` (eso no corre al importar, por definicion).
    def sentencias_de_import(cuerpo):
        for nodo in cuerpo:
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(nodo, ast.If) and "__main__" in ast.dump(nodo.test):
                continue
            yield nodo
            for campo in ("body", "orelse", "finalbody"):
                sub = getattr(nodo, campo, None)
                if isinstance(sub, list):
                    yield from sentencias_de_import(sub)
            for manejador in getattr(nodo, "handlers", []) or []:
                yield from sentencias_de_import(manejador.body)

    fallos = []
    revisados = 0
    for f, arbol in arboles.items():
        if f.stem not in importados:
            continue                       # nadie lo importa: es un script
        revisados += 1
        vistos = set()
        for nodo in sentencias_de_import(arbol.body):
            for sub in ast.walk(nodo):
                if (isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute)
                        and sub.func.attr == "exit"
                        and isinstance(sub.func.value, ast.Name)
                        and sub.func.value.id == "sys"
                        and sub.lineno not in vistos):
                    vistos.add(sub.lineno)
                    fallos.append(f"{f.name}:{sub.lineno}")

    check("Modulos importables: ninguno se sale al importarse", not fallos,
          f"{revisados} modulos importados por alguien, ninguno llama a sys.exit() al cargarse"
          if not fallos else
          f"matan a quien los importe (y apagan su ensayo en silencio): {', '.join(sorted(fallos))}")


#: El UNICO fichero de produccion autorizado a hablar con una API de IA. No es
#: una preferencia de estilo: es la frontera de datos del proyecto, y esta
#: escrita aqui para que anadir una segunda salida sea imposible EN SILENCIO.
SALIDA_CLOUD_AUTORIZADA = "captura_orquestador.py"


def _llamadas_api_ia(nodo):
    """Nodos Call que son una llamada a una API de IA, por AST y no por texto.

    Por AST a proposito (leccion de check_cableado, 21-08-2026): un auditor que
    mira la FORMA acusa a inocentes en cuanto alguien reformatea una linea, y
    ademas se traga cualquier variante que no imagino. Aqui se reconoce la
    LLAMADA, escrita como se escriba."""
    for n in ast.walk(nodo):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        if n.func.attr == "generate_content":          # Gemini
            yield n
        elif (n.func.attr == "create"                   # Anthropic
              and isinstance(n.func.value, ast.Attribute)
              and n.func.value.attr == "messages"):
            yield n


def _importa_sdk_ia(arbol):
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            if any(a.name.split(".")[0] == "anthropic" or a.name == "google.genai"
                   for a in n.names):
                return True
        elif isinstance(n, ast.ImportFrom):
            if n.module == "google" and any(a.name == "genai" for a in n.names):
                return True
            if (n.module or "").split(".")[0] == "anthropic":
                return True
    return False


def check_salida_unica_cloud():
    """ANADIDO 16-09-2026. Ningun dato sale hacia una IA sin pasar por la puerta.

    POR QUE ES UN AUDITOR Y NO UNA REGLA ESCRITA: hasta hoy, "el modelo solo ve
    lo que necesita" vivia en `.claude/rules/datos.md`, es decir, dependia de
    que quien escribe el proximo fichero se acuerde. Este proyecto ya sabe como
    acaba eso: la regla de los .zip estaba escrita sobre la EXTENSION y los
    contenedores de ContaPlus, que son ZIP con extension .DAT, pasaron por
    delante ocho dias — y el escaner ademas los declaraba limpios.

    Comprueba tres cosas, y las tres son la misma idea:

      1. Solo `SALIDA_CLOUD_AUTORIZADA` importa un SDK de IA o llama a su API.
         Un segundo punto de salida en cualquier otro fichero es un ❌.
      2. Ese fichero importa `puerta_cloud`.
      3. TODA funcion suya que llame a una API llama tambien a
         `exigir_permiso`. Este es el punto fuerte: la garantia no depende del
         grafo de llamadas ni de que nadie use por dentro la funcion de bajo
         nivel, sino de una invariante LOCAL y comprobable en la propia funcion
         que toca la API.

    Probado con el defecto reintroducido a proposito (una llamada a
    generate_content en otro fichero, y la linea de exigir_permiso borrada): se
    pone rojo y dice fichero y linea."""
    fuera, sin_permiso = [], []
    autorizado_ok = False
    revisados = 0
    for f in [str(p) for p in Path(".").rglob("*.py") if ".git" not in p.parts]:
        try:
            arbol = ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError:
            continue                       # ya lo reporta check_sintaxis()
        llamadas = list(_llamadas_api_ia(arbol))
        if not llamadas and not _importa_sdk_ia(arbol):
            continue
        revisados += 1
        if os.path.basename(f) != SALIDA_CLOUD_AUTORIZADA:
            fuera.append(f"{os.path.basename(f)}:{llamadas[0].lineno if llamadas else 1}")
            continue
        autorizado_ok = any(
            isinstance(n, (ast.Import, ast.ImportFrom))
            and "puerta_cloud" in ast.dump(n) for n in ast.walk(arbol))
        # La invariante local: la funcion que envia, pide permiso.
        for fn in ast.walk(arbol):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            envia = list(_llamadas_api_ia(fn))
            if not envia:
                continue
            pide = any(isinstance(n, ast.Call)
                       and isinstance(n.func, ast.Attribute)
                       and n.func.attr == "exigir_permiso"
                       for n in ast.walk(fn))
            if not pide:
                sin_permiso.append(f"{os.path.basename(f)}:{fn.name}:{envia[0].lineno}")

    problemas = []
    if fuera:
        problemas.append(f"llaman a una IA fuera de la puerta: {', '.join(sorted(fuera))}")
    if revisados and not autorizado_ok:
        problemas.append(f"{SALIDA_CLOUD_AUTORIZADA} no importa puerta_cloud")
    if sin_permiso:
        problemas.append(f"envian sin exigir_permiso: {', '.join(sorted(sin_permiso))}")
    check("Salida a IA: una sola puerta, y pide permiso", not problemas,
          f"un unico punto de salida ({SALIDA_CLOUD_AUTORIZADA}), pasa por "
          f"puerta_cloud y ninguna funcion envia sin exigir permiso"
          if not problemas else " | ".join(problemas))


#: Una suite puede quedar legitimamente fuera de la auditoria, pero NUNCA en
#: silencio: se anota aqui con motivo y fecha, y check_suites_sin_cablear() la
#: imprime en cada pasada. Hoy esta vacio a proposito — las siete que estaban
#: fuera el 11-09-2026 se cablearon en vez de excluirse, porque las siete corren
#: en 0,57 s entre todas, sin dependencias externas y sin tocar ningun dato.
#:
#: Formato:  "ruta/relativa.py": "motivo concreto — DD-MM-AAAA"
#: (ruta relativa a la raiz del repositorio, con "/", igual que la clave que
#: anota ejecutar_suite() — en la raiz es simplemente "fichero.py")
EXCEPCIONES_SUITES = {}


def check_suites_sin_cablear():
    """ANADIDO 11-09-2026. La cuarta pregunta, y la que faltaba desde el principio.

        check_cableado()          -> ¿el guard existe y alguien lo llama?
        cobertura_guards          -> ¿ha llegado alguna vez a decir que no?
        audit_estados             -> ¿lo que dice cambia el veredicto?
        check_suites_sin_cablear  -> ¿y quien ejecuta a los que preguntan eso?

    EL AGUJERO QUE CIERRA, medido antes de taparlo. El 11-09-2026 habia SIETE
    suites en el repositorio —todas en verde, todas escritas para proteger una
    regresion concreta— que esta auditoria no ejecutaba nunca. La lista de
    `check_estados_y_cobertura()` se mantiene A MANO, asi que escribir un ensayo
    y no acordarse de anadirlo ahi lo deja mirando a la pared.

    Y check_modulos_huerfanos(), que existe justo para cazar "una pieza probada
    en aislado y nunca conectada" —"el fallo que MAS se repite en este
    proyecto", dice su propio docstring—, no podia verlo: exime expresamente a
    todo lo que tenga `__main__` o empiece por `test_`. Toda suite cumple las
    dos cosas. El auditor de piezas desconectadas tenia su punto ciego
    exactamente en las piezas que auditan.

    COMPROBADO POR SABOTAJE, antes de escribir una linea del arreglo: con
    `ensayo_validar_captura_historica.py` roto a proposito —el unico que fija la
    regresion del P0 "0.0% miente"— `audit_project.py` imprimio la MISMA salida
    que con el repositorio sano y salio con el mismo codigo 2. Ni un ❌, ni una
    mencion.

    POR QUE MIRA LA EJECUCION Y NO EL NOMBRE. Lo facil seria comprobar si el
    nombre de la suite aparece en este fichero. No vale: este fichero esta lleno
    de nombres `.py` dentro de comentarios que explican que cubre cada ensayo y
    que deja fuera. Un `grep` daria por cableada una suite NOMBRADA —incluida
    una nombrada justo para explicar por que NO se ejecuta—. Esa es la "barrera
    de conveniencia" de `.claude/rules/datos.md`: la que decide por el nombre en
    vez de por el contenido. Aqui el contenido es el hecho de haber corrido, y
    lo aporta `ejecutar_suite()`, la unica puerta por la que sale una suite.

    Por eso tiene que llamarse LA ULTIMA en main(): compara contra lo que
    realmente ha corrido en esta pasada.
    """
    encontradas = set()
    for ruta in Path(".").rglob("*.py"):
        if any(parte.startswith(".") for parte in ruta.parts):
            continue          # .git, .venv y demas: no es codigo del proyecto
        if ruta.name.startswith("test_") or ruta.name.startswith("ensayo_"):
            # Misma clave que usa ejecutar_suite(): ruta relativa a la raiz.
            encontradas.add(ruta.as_posix())

    sin_cablear = sorted(encontradas - SUITES_EJECUTADAS - set(EXCEPCIONES_SUITES))
    excluidas = sorted(n for n in EXCEPCIONES_SUITES if n in encontradas)

    # Una excepcion escrita para una suite que ya no existe es basura que tapa:
    # manana ese nombre puede volver a usarse y entrar exento sin que nadie lo
    # decida. Se avisa aparte, no se cuela en el recuento de las que faltan.
    fantasmas = sorted(set(EXCEPCIONES_SUITES) - encontradas)

    # El recuento se hace sobre la INTERSECCION, no sobre len(SUITES_EJECUTADAS):
    # por ejecutar_suite() pasan tambien auditores que no son suites
    # (audit_estados.py, cobertura_guards.py, barrido_falsos_verdes.py), y
    # contarlos daba el absurdo "25 ejecutadas, 22 en el repositorio" — un
    # numero que nadie puede cuadrar de un vistazo es un numero que deja de
    # mirarse, igual que el ❌ que se enseño a ignorar (ver la nota de los tres
    # estados arriba).
    cubiertas = encontradas & SUITES_EJECUTADAS
    otros = sorted(SUITES_EJECUTADAS - encontradas)
    partes = [f"{len(cubiertas)}/{len(encontradas)} suites del repositorio ejecutadas"
              + (f" (+{len(otros)} auditores que no son suite: {', '.join(otros)})" if otros else "")]
    if excluidas:
        partes.append("excluidas a proposito: "
                      + "; ".join(f"{n} ({EXCEPCIONES_SUITES[n]})" for n in excluidas))
    if fantasmas:
        partes.append(f"excepciones que sobran (esa suite ya no existe): {fantasmas}")
    if sin_cablear:
        partes.append("NADIE EJECUTA: " + ", ".join(sin_cablear)
                      + " - existen, pueden estar en rojo, y esta auditoria diria que todo va bien")

    # CERO suites encontradas no es un aprobado: es que no se ha mirado nada.
    # Pasa si la auditoria se lanza desde otro directorio (`Path(".")` es el
    # directorio de trabajo, no el del fichero). El resto de la auditoria ya
    # saldria en rojo por su cuenta, pero ESTE check, y solo el, habria dicho
    # que va bien sin haber abierto nada — el mismo falso verde que el escaner
    # de privacidad daba con un .DAT (.claude/rules/datos.md): "sin hallazgos"
    # porque no habia mirado. Sale por la puerta de NO_COMPROBADO, que es la
    # verdad.
    if not encontradas:
        check("Suites: ninguna prueba mirando a la pared", False,
              "no se ha encontrado NINGUNA suite en este directorio: "
              f"esto no es un aprobado, es que no se ha mirado nada (cwd: {os.getcwd()})",
              estado=NO_COMPROBADO)
        return

    check("Suites: ninguna prueba mirando a la pared",
          not sin_cablear and not fantasmas, " | ".join(partes))


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
    check_fuentes_externas()
    check_autoridad_guards()
    check_tests()
    check_adversarial()
    check_estados_y_cobertura()
    check_subprocess_encoding()
    check_salida_al_importar()
    check_salida_unica_cloud()
    # LA ULTIMA a proposito: compara contra lo que de verdad ha corrido arriba.
    check_suites_sin_cablear()
    comparar_con_anterior()

    estados = [c.get("estado", OK if c["ok"] else FALLO)
               for c in RESULTADO["checks"].values()]
    fallos = [n for n, c in RESULTADO["checks"].items()
              if c.get("estado", OK if c["ok"] else FALLO) == FALLO]
    sin_comprobar = [n for n, c in RESULTADO["checks"].items()
                     if c.get("estado") == NO_COMPROBADO]

    print(f"\n{'='*40}")
    if fallos:
        print("❌ HAY PROBLEMAS QUE REVISAR")
        for n in fallos:
            print(f"   ❌ {n}")
    if sin_comprobar:
        print("⚠️  Y ESTO NO SE HA PODIDO COMPROBAR (no es un aprobado):")
        for n in sin_comprobar:
            print(f"   ⚠️  {n}")
    if not fallos and not sin_comprobar:
        print("✅ TODO CORRECTO")

    # 0 = todo comprobado y en verde · 1 = hay un defecto · 2 = nada falla,
    # pero queda algo sin comprobar. Tres desenlaces distintos porque son tres
    # cosas distintas, y hasta hoy 1 significaba las dos ultimas a la vez.
    sys.exit(1 if fallos else (2 if sin_comprobar else 0))
