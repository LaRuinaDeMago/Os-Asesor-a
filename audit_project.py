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
    check_dependencias()
    check_tests()
    comparar_con_anterior()

    todos_ok = all(c["ok"] for c in RESULTADO["checks"].values())
    print(f"\n{'='*40}")
    print("✅ TODO CORRECTO" if todos_ok else "❌ HAY PROBLEMAS QUE REVISAR")
    sys.exit(0 if todos_ok else 1)
