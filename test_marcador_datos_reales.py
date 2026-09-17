#!/usr/bin/env python3
"""test_marcador_datos_reales.py — que `*_LOCAL*`/`*_local*` protejan TODAS
las variantes del marcador, no solo cuando va justo antes de la extension.

(Nombrado a proposito SIN la subcadena "_local": ese mismo patron amplio la
atraparia a ella misma -- paso justo al escribir este fichero por primera
vez, con el nombre `test_gitignore_local.py`. Efecto colateral real de la
correccion, no solo teorico.)

POR QUE ESTA BATERIA
----------------------
Encontrado el 17-09-2026 al terminar el primer ensayo con datos reales: el
patron de `.gitignore` era `*_LOCAL.*`, que solo protege si "_LOCAL" va
JUSTO antes del punto de la extension. `facturas_reales_LOCAL_run2.csv` y
`facturas_reales_LOCAL_factura2.csv` (las dos capturas de la primera factura
real, comprobada dos veces por Gemini) llevan algo DESPUES de "_LOCAL"
(`_run2`, `_factura2`) y por tanto NO estaban protegidos -- aparecian como
"sin seguimiento" en `git status` en vez de ignorados. Mismo tipo de agujero
que el `.DAT` (19-08-2026): decidir por una FORMA concreta del nombre en vez
de por lo que el nombre declara.

Prueba contra el `.gitignore` REAL del repositorio, con `git check-ignore`,
no con una reimplementacion propia del glob -- la misma disciplina que ya
sigue `test_privacidad.py` con `scripts/privacy_scan.py`.

REGLA DE DATOS: solo nombres de fichero, ningun contenido ni fichero real
creado en disco -- `git check-ignore` no necesita que el fichero exista."""
import os
import subprocess
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AQUI = os.path.dirname(os.path.abspath(__file__))

resultados = []


def comprobar(nombre, condicion, detalle="", severidad="P1"):
    resultados.append((nombre, bool(condicion), detalle, severidad))


def ignorado(nombre_fichero):
    """True si git ignoraria ese nombre en la raiz del repositorio."""
    r = subprocess.run(["git", "check-ignore", "-q", nombre_fichero],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=AQUI)
    return r.returncode == 0


def pruebas_variantes_con_sufijo():
    """EL BUG REAL: algo DESPUES de _LOCAL, antes de la extension."""
    casos = ["facturas_reales_LOCAL_run2.csv",
             "facturas_reales_LOCAL_factura2.csv",
             "veredicto_real_LOCAL_factura2.csv",
             "cualquier_cosa_LOCAL_otra_mas.json"]
    for nombre in casos:
        comprobar(f"{nombre} esta ignorado", ignorado(nombre),
                  severidad="P0")


def pruebas_forma_original_sigue_protegida():
    """No regresion: la forma de siempre (_LOCAL justo antes de la extension)
    sigue funcionando."""
    casos = ["facturas_reales_LOCAL.csv", "config_LOCAL.json",
             "algo_local.txt"]
    for nombre in casos:
        comprobar(f"{nombre} sigue ignorado (forma original)", ignorado(nombre),
                  severidad="P0")


def pruebas_no_ignora_de_mas():
    """El marcador es "_LOCAL"/"_local" con guion bajo -- una palabra que
    solo CONTIENE 'local' sin el guion bajo no deberia caer aqui por error
    (aunque no haya hoy ningun fichero versionado con ese patron, ver commit
    de este arreglo -- comprobado con `git ls-files`)."""
    comprobar("un nombre que contiene 'local' sin guion bajo no se ignora "
              "por este patron (localizar_algo.py)",
              not ignorado("localizar_algo.py"), severidad="P1")


def main():
    print("=" * 72)
    print("GITIGNORE _LOCAL — bateria")
    print("=" * 72)
    pruebas_variantes_con_sufijo()
    pruebas_forma_original_sigue_protegida()
    pruebas_no_ignora_de_mas()

    fallan = [r for r in resultados if not r[1]]
    p0 = [r for r in fallan if r[3] == "P0"]
    print(f"\nPruebas: {len(resultados)}   en verde: {len(resultados) - len(fallan)}   "
          f"FALLAN: {len(fallan)}  (de ellas P0: {len(p0)})")
    if fallan:
        print("\nLo que falla:")
        for nombre, _, detalle, sev in fallan:
            print(f"  [{sev}] {nombre}" + (f" — {detalle}" if detalle else ""))
        return 1
    print("\n*_LOCAL*/*_local* protege el marcador lleve lo que lleve detras,")
    print("sin ignorar de mas nombres que solo se parecen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
