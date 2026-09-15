#!/usr/bin/env python3
"""ensayo_modelos_aeat.py — el registro de modelos AEAT no miente ni se cuela.

NO TOCA LA RED, a proposito y por el mismo motivo que `ensayo_boe_normativa.py`:
`audit_project.py` tiene que correr sin conexion, rapido y determinista. Aqui se
comprueba la FORMA del registro -- que cada entrada trae lo que
`boe_normativa.comprobar()` necesita, que no hay huellas repetidas por
copiar-pegar, que un modelo no puede estar a la vez registrado y "pendiente de
identificar", y que la vigilancia lo recoge de verdad. La descarga real es
`python boe_normativa.py --comprobar`, a mano o desde la tarea programada.
"""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import modelos_aeat as ma

FALLOS = []


def comprobar(desc, cond, detalle=""):
    if cond:
        print(f"  OK   {desc}")
    else:
        print(f"  FALLA {desc}   {detalle}")
        FALLOS.append(desc)


def main():
    print("=== A. Cada entrada sirve para lo unico que existe: ser vigilada ===")
    for m in ma.MODELOS:
        etq = f"modelo {m.modelo}/{m.bloque_boe}"
        comprobar(f"{etq}: norma con forma BOE-A-",
                  m.norma_boe.startswith("BOE-A-"), m.norma_boe)
        comprobar(f"{etq}: vigencia de 8 digitos",
                  len(m.vigencia_boe) == 8 and m.vigencia_boe.isdigit(),
                  m.vigencia_boe)
        comprobar(f"{etq}: huella de 16 hex",
                  len(m.huella_boe) == 16
                  and all(c in "0123456789abcdef" for c in m.huella_boe),
                  m.huella_boe)

    print()
    print("=== B. Los atributos que comprobar() usa, sin excepcion ===")
    # Si alguien anade una entrada y se deja un campo, esto lo caza aqui --
    # en vez de que --comprobar la declare "no comprobada" sin decir por que.
    for m in ma.MODELOS:
        for attr in ("clave", "norma_boe", "bloque_boe", "vigencia_boe",
                     "huella_boe"):
            comprobar(f"{m.clave}: tiene .{attr}", bool(getattr(m, attr, "")))

    print()
    print("=== C. Ni duplicados silenciosos ni huellas copiadas ===")
    pares = [(m.norma_boe, m.bloque_boe) for m in ma.MODELOS]
    comprobar("ningun (norma, bloque) repetido", len(pares) == len(set(pares)),
              f"{len(pares)} entradas, {len(set(pares))} distintas")
    huellas = [m.huella_boe for m in ma.MODELOS]
    comprobar("ninguna huella repetida (senal de copiar-pegar)",
              len(huellas) == len(set(huellas)),
              f"{len(huellas)} huellas, {len(set(huellas))} distintas")

    print()
    print("=== D. Lo que NO esta verificado se declara, no se deja en blanco ===")
    comprobar("hay lista explicita de modelos sin identificar",
              isinstance(ma.PENDIENTES_DE_IDENTIFICAR, dict)
              and len(ma.PENDIENTES_DE_IDENTIFICAR) > 0)
    comprobar("cada pendiente dice QUE le falta, no solo que existe",
              all(v.strip() for v in ma.PENDIENTES_DE_IDENTIFICAR.values()))
    solapan = {m.modelo for m in ma.MODELOS} & set(ma.PENDIENTES_DE_IDENTIFICAR)
    comprobar("ningun modelo a la vez registrado y 'pendiente de identificar'",
              not solapan, f"solapan: {sorted(solapan)}")

    print()
    print("=== E. El registro entra de verdad en la vigilancia del BOE ===")
    # Lo que de verdad importa: que --comprobar los recoja. Se lee el codigo
    # como TEXTO, sin ejecutarlo, para no tocar la red.
    fuente = open("boe_normativa.py", encoding="utf-8", errors="replace").read()
    comprobar("boe_normativa.py importa modelos_aeat",
              "import modelos_aeat" in fuente)
    comprobar("y mete sus MODELOS en los registros que comprueba",
              "ma.MODELOS" in fuente)

    print()
    print("=== F. El 303 esta, porque es sobre el que se apoya todo el cuadre ===")
    comprobar("el modelo 303 esta vigilado",
              any(m.modelo == "303" for m in ma.MODELOS))

    print()
    print("=" * 60)
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones")
        return 1
    print("El ensayo pasa. El registro de modelos trae lo que la vigilancia "
          "necesita, no repite huellas, y declara lo que aun no ha "
          "identificado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
