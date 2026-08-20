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

RESULTADO = {"fecha": datetime.now().isoformat(timespec="seconds"), "checks": {}}


def check(nombre, ok, detalle=""):
    RESULTADO["checks"][nombre] = {"ok": ok, "detalle": detalle}
    marca = "✅" if ok else "❌"
    print(f"{marca} {nombre}: {detalle}")


def check_sintaxis():
    archivos = [f for f in os.listdir(".") if f.endswith(".py")]
    fallos = []
    for f in archivos:
        try:
            ast.parse(open(f, encoding="utf-8").read())
        except SyntaxError as e:
            fallos.append(f"{f}: {e}")
    check("Sintaxis de todos los .py", len(fallos) == 0,
          f"{len(archivos)} archivos revisados" if not fallos else "; ".join(fallos))


def check_cableado():
    """Verifica que todos los guards asignados en evaluar_fila_v4 se consultan
    de verdad en calcular_veredicto_v4 - el tipo de bug real que ya encontramos
    una vez esta noche (funciones huerfanas, guards fantasma)."""
    if not os.path.exists("motor_veredicto.py"):
        check("Cableado de guards", False, "motor_veredicto.py no encontrado")
        return
    import re
    codigo = open("motor_veredicto.py", encoding="utf-8").read()
    m = re.search(r'def evaluar_fila_v4.*?(?=\ndef |\Z)', codigo, re.DOTALL)
    if not m:
        check("Cableado de guards", False, "no se encontró evaluar_fila_v4")
        return
    asignados = set(re.findall(r'guards\["(\w+)"\]', m.group()))
    m2 = re.search(r'def calcular_veredicto_v4.*?(?=\ndef |\Z)', codigo, re.DOTALL)
    cv = m2.group() if m2 else ""
    crit_match = re.search(r'criticos = \[(.*?)\]', cv, re.DOTALL)
    crit = set(re.findall(r'"(\w+)"', crit_match.group(1))) if crit_match else set()
    sueltas = set(re.findall(r'guards\.get\("(\w+)"', cv)) - crit
    consultados = crit | sueltas
    huerfanos = asignados - consultados
    check("Cableado de guards (sin huérfanos)", len(huerfanos) == 0,
          f"{len(asignados)} guards, todos consultados" if not huerfanos
          else f"HUÉRFANOS: {huerfanos}")


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
    resultado = subprocess.run([sys.executable, "test_motor_veredicto.py"],
                                capture_output=True, text=True)
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
                                capture_output=True, text=True)
    ok = resultado.returncode == 0
    linea = next((l for l in resultado.stdout.splitlines() if l.startswith("Pruebas:")), "")
    check("Bateria adversarial (test_adversarial.py)", ok,
          linea or resultado.stdout[-300:])


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
    comparar_con_anterior()

    todos_ok = all(c["ok"] for c in RESULTADO["checks"].values())
    print(f"\n{'='*40}")
    print("✅ TODO CORRECTO" if todos_ok else "❌ HAY PROBLEMAS QUE REVISAR")
    sys.exit(0 if todos_ok else 1)
