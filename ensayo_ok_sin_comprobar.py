#!/usr/bin/env python3
"""ensayo_ok_sin_comprobar.py — ensayo en seco de audit_ok_sin_comprobar.py.

POR QUE HACE FALTA, Y POR QUE LOS CONTROLES SON LA MITAD DEL ENSAYO
--------------------------------------------------------------------
Un auditor que dijera "hallazgo" en todo pasaria cualquier prueba que solo
compruebe "¿lo detecta?". Por eso este ensayo tiene las dos mitades:

  1. Reproduce los DOS bugs REALES del 27-08-2026, con la forma exacta que
     tenian en el codigo, y exige que los detecte.
  2. Le da codigo CORRECTO —incluidos los dos guards ya arreglados— y exige
     que se calle. Es la misma leccion que la FAMILIA G de test_adversarial.py:
     una bateria que solo comprueba "no debe dar verde" la aprueba entera un
     motor que diga siempre ROJO.

REGLA DE DATOS: todo el codigo de prueba es inventado y vive en cadenas de
texto dentro de este fichero. No se toca ningun fichero del proyecto ni hay
ningun dato real en ninguna parte.

Uso:
    python ensayo_ok_sin_comprobar.py
"""
import os
import subprocess
import sys
import tempfile

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from audit_ok_sin_comprobar import analizar

AQUI = os.path.dirname(os.path.abspath(__file__))
FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK   {titulo}")
    else:
        print(f"  FALLA {titulo}   {detalle}")
        FALLOS.append(titulo)


# --- Los dos bugs REALES, con la forma que tenian el 27-08-2026 -------------
BUG_IMPORTE_ATIPICO = '''
def guard_importe_atipico(proveedor, total, historico, nif=None):
    entry = historico.get(nif)
    if not entry:
        return "NO_COMPROBADO", "sin historico"
    media, desv = entry["media"], entry["desv"]
    if desv > 0 and abs(total - media) > desv:
        return "FALLO", "importe fuera de patron"
    return "OK", "dentro de patron"
'''

BUG_SECUENCIA = '''
def guard_secuencia_documental_proveedor(prov, doc, cache, nif=None):
    previos = cache.get(nif, [])
    if len(previos) < 2:
        return "NO_APLICA", "pocos previos"
    salto_medio = (max(previos) - min(previos)) / (len(previos) - 1)
    dist_min = min(abs(int(doc) - p) for p in previos)
    if salto_medio > 0 and dist_min > salto_medio * 20:
        return "FALLO", "muy alejado"
    return "OK", "coherente con la secuencia"
'''

# --- Codigo CORRECTO que NO debe hacer saltar nada -------------------------
ARREGLADO_CON_SUELO = '''
def guard_importe_atipico(proveedor, total, historico, nif=None):
    entry = historico.get(nif)
    if not entry:
        return "NO_COMPROBADO", "sin historico"
    media, desv = entry["media"], entry["desv"]
    desv_efectiva = max(desv, media * 0.05)
    if abs(total - media) > 3 * desv_efectiva:
        return "FALLO", "importe fuera de patron"
    return "OK", "dentro de patron"
'''

ARREGLADO_CON_NO_COMPROBADO = '''
def guard_secuencia_documental_proveedor(prov, doc, cache, nif=None):
    previos = cache.get(nif, [])
    salto_medio = 0 if len(previos) < 2 else (max(previos) - min(previos)) / (len(previos) - 1)
    if salto_medio <= 0:
        return "NO_COMPROBADO", "los previos no varian: no hay secuencia"
    if abs(int(doc) - previos[0]) > salto_medio * 20:
        return "FALLO", "muy alejado"
    return "OK", "coherente"
'''

SENTIDO_CONTRARIO = '''
def guard_algo(x, y):
    """El `and` con un `> 0` existe, pero el cuerpo AFIRMA, no niega:
    no es el patron. Si esto saltara, el auditor gritaria de mas."""
    if y > 0 and x == y:
        return "OK", "coinciden"
    return "FALLO", "no coinciden"
'''

NUNCA_DICE_OK = '''
def guard_solo_avisa(x, margen):
    """Un guard que nunca dice OK no puede dar un falso verde, por definicion."""
    if margen > 0 and x > margen:
        return "FALLO", "fuera"
    return "NO_COMPROBADO", "sin margen con el que comparar"
'''

NO_ES_GUARD = '''
def calcular_algo(total, desv):
    """Misma forma, pero no es un guard: no emite veredicto y no puede
    producir un falso verde en el motor."""
    if desv > 0 and total > desv:
        return "FALLO", "x"
    return "OK", "y"
'''


def main():
    print("ENSAYO EN SECO: audit_ok_sin_comprobar.py")
    print("=" * 70)

    print("\n--- Mitad 1: ¿detecta los DOS bugs reales? ---")
    h = analizar(BUG_IMPORTE_ATIPICO)
    comprobar("detecta el bug real de guard_importe_atipico (`desv > 0`)",
              len(h) == 1 and h[0][0] == "guard_importe_atipico" and h[0][1] == "desv",
              str(h))
    h = analizar(BUG_SECUENCIA)
    comprobar("detecta el bug real de secuencia_documental (`salto_medio > 0`)",
              len(h) == 1 and h[0][1] == "salto_medio", str(h))
    h = analizar(BUG_IMPORTE_ATIPICO + BUG_SECUENCIA)
    comprobar("con los dos en el mismo fichero, encuentra los DOS (no para en el primero)",
              len(h) == 2, str(h))

    print("\n--- Mitad 2: ¿se calla con codigo correcto? ---")
    comprobar("el arreglo con suelo de dispersion NO salta",
              analizar(ARREGLADO_CON_SUELO) == [], str(analizar(ARREGLADO_CON_SUELO)))
    comprobar("el arreglo con NO_COMPROBADO NO salta",
              analizar(ARREGLADO_CON_NO_COMPROBADO) == [],
              str(analizar(ARREGLADO_CON_NO_COMPROBADO)))
    comprobar("un `and` con `> 0` cuyo cuerpo AFIRMA no es el patron",
              analizar(SENTIDO_CONTRARIO) == [], str(analizar(SENTIDO_CONTRARIO)))
    comprobar("un guard que nunca dice OK no puede dar falso verde",
              analizar(NUNCA_DICE_OK) == [], str(analizar(NUNCA_DICE_OK)))
    comprobar("una funcion que no es guard_* queda fuera del alcance",
              analizar(NO_ES_GUARD) == [], str(analizar(NO_ES_GUARD)))

    print("\n--- Las tres formas de escribir la misma condicion ---")
    for op in (">", ">=", "!="):
        codigo = BUG_IMPORTE_ATIPICO.replace("desv > 0", f"desv {op} 0")
        comprobar(f"reconoce `desv {op} 0` (la forma no debe importar)",
                  len(analizar(codigo)) == 1)

    print("\n--- De punta a punta: el script real, con sus codigos de salida ---")
    tmp = tempfile.mkdtemp(prefix="ensayo_okc_")
    try:
        # Un fichero con el bug real: debe salir con codigo 1
        ruta_mala = os.path.join(tmp, "con_bug.py")
        with open(ruta_mala, "w", encoding="utf-8") as f:
            f.write(BUG_IMPORTE_ATIPICO)
        r = subprocess.run([sys.executable, os.path.join(AQUI, "audit_ok_sin_comprobar.py"),
                            ruta_mala], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        comprobar("con un bug real, el script termina en ERROR (codigo 1)",
                  r.returncode == 1, f"codigo={r.returncode}")
        comprobar("y explica el patron, no solo el nombre del guard",
                  "sin haber comparado nada" in r.stdout, r.stdout[-200:])

        # Un fichero limpio con OTRO nombre: codigo 0 y ni una palabra de
        # caducidad. Es la REGRESION del fallo que este mismo ensayo cazo
        # antes de subir el auditor: con las excepciones indexadas solo por
        # (funcion, variable), analizar cualquier fichero que no fuera
        # motor_veredicto.py las declaraba todas caducadas y salia en rojo.
        ruta_buena = os.path.join(tmp, "sin_bug.py")
        with open(ruta_buena, "w", encoding="utf-8") as f:
            f.write(ARREGLADO_CON_SUELO + ARREGLADO_CON_NO_COMPROBADO)
        r = subprocess.run([sys.executable, os.path.join(AQUI, "audit_ok_sin_comprobar.py"),
                            ruta_buena], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        comprobar("con codigo correcto, termina OK (codigo 0)",
                  r.returncode == 0, f"codigo={r.returncode}: {r.stdout[-200:]}")
        comprobar("REGRESION: analizar OTRO fichero no declara caducadas las "
                  "excepciones de motor_veredicto.py",
                  "CADUCADA" not in r.stdout.upper(), r.stdout[-200:])

        # Excepcion CADUCADA de verdad: un fichero que SI se llama
        # motor_veredicto.py pero donde el caso declarado ya no esta.
        dir_mv = os.path.join(tmp, "otra_version")
        os.makedirs(dir_mv, exist_ok=True)
        ruta_mv = os.path.join(dir_mv, "motor_veredicto.py")
        with open(ruta_mv, "w", encoding="utf-8") as f:
            f.write(ARREGLADO_CON_SUELO)     # sin guard_suma_tramos
        r = subprocess.run([sys.executable, os.path.join(AQUI, "audit_ok_sin_comprobar.py"),
                            ruta_mv], capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        comprobar("si el caso declarado desaparece del fichero, avisa de que "
                  "la excepcion ha caducado",
                  "CADUCADA" in r.stdout.upper(), r.stdout[-300:])
        comprobar("y por eso termina en ERROR: una lista blanca con entradas "
                  "muertas acaba tapando un caso real",
                  r.returncode == 1, f"codigo={r.returncode}")
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n--- Y sobre el motor de verdad ---")
    r = subprocess.run([sys.executable, os.path.join(AQUI, "audit_ok_sin_comprobar.py"),
                        os.path.join(AQUI, "motor_veredicto.py")],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    comprobar("motor_veredicto.py pasa la auditoria hoy",
              r.returncode == 0, r.stdout[-300:])

    print("=" * 70)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)}:")
        for f in FALLOS:
            print(f"  - {f}")
        sys.exit(1)
    print("El ensayo pasa. El auditor caza los dos bugs reales y se calla con "
          "el codigo correcto.")


if __name__ == "__main__":
    main()
