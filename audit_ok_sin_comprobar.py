#!/usr/bin/env python3
"""audit_ok_sin_comprobar.py — caza una FORMA de falso verde, no un caso.

QUE BUSCA, Y POR QUE EXISTE
-----------------------------
El 27-08-2026, al despertar cuatro guards que llevaban meses dormidos (les
llegaba la cache vacia), aparecieron cuatro defectos de decision. **Dos eran
literalmente el mismo**, en guards distintos y escritos en momentos distintos:

    guard_importe_atipico:
        if desv > 0 and abs(total - media) > desv:
            return "FALLO", ...
        return "OK", ...                  # <- desv == 0 cae aqui

    guard_secuencia_documental_proveedor:
        if salto_medio > 0 and dist_min > salto_medio * 20:
            return "FALLO", ...
        return "OK", ...                  # <- salto_medio == 0 cae aqui

La condicion `x > 0` se pone con buena intencion (no dividir por cero, no
comparar contra una dispersion que no existe). El efecto es el contrario del
buscado: cuando NO hay con que comparar, el guard no se calla — **afirma que
todo esta bien**. Medido en el primero: un proveedor de cuota fija que de
pronto factura 825 veces mas devolvia `OK, dentro de patron`.

    Un `if x > 0 and <comprobacion>` seguido de `return "OK"` es un falso
    verde esperando. La ausencia de dispersion no es "todo correcto": es
    "no he podido comprobar nada", y eso se llama NO_COMPROBADO.

Los dos se arreglaron a mano. Este auditor existe porque una leccion escrita
en un documento no impide que el patron vuelva a aparecer dentro de tres
meses en el guard numero 27 — y porque de 26 guards solo cinco se auditaron a
mano. Es la misma razon por la que existe `audit_estados.py`.

COMO DECIDE, Y POR QUE POR AST
--------------------------------
Sobre el arbol de sintaxis, no con expresiones regulares. Es la leccion ya
pagada en `check_cableado` (21-08-2026): una regex declaro siete huerfanos
que no lo eran porque solo reconocia el cableado escrito de UNA forma. La
forma no debe importar.

EXCEPCIONES: se declaran, con su motivo verificado, y CADUCAN
--------------------------------------------------------------
Un patron detectado no es siempre un bug: puede ser inalcanzable porque algo
anterior ya lo intercepta. Esos casos se declaran abajo, uno a uno, con el
motivo y como se comprobo. Y la lista se audita a si misma: si una excepcion
declarada ya no aparece en el codigo, este script lo dice — una lista blanca
que conserva entradas muertas acaba tapando un caso real.

Uso:
    python audit_ok_sin_comprobar.py            # sobre motor_veredicto.py
    python audit_ok_sin_comprobar.py otro.py
"""
import argparse
import ast
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Veredictos que significan "no doy por bueno esto". Si el cuerpo del `if`
#: devuelve uno de estos, el `return "OK"` de mas abajo es la rama que se
#: alcanza cuando la comprobacion NO se ha podido hacer.
VEREDICTOS_NEGATIVOS = ("FALLO", "NO_COMPROBADO", "NO_APLICA", "AMBAR")

#: Excepciones verificadas a mano. Clave: (fichero, funcion, variable).
#: El valor NO es "esto vale": es POR QUE se comprobo que no es alcanzable.
#:
#: Van indexadas por FICHERO, y no es un detalle: la primera version las tenia
#: solo por (funcion, variable) y comprobaba la caducidad contra el fichero que
#: le tocara analizar. Resultado, cazado por su propio ensayo antes de subirlo:
#: al analizar cualquier OTRO fichero, todas las excepciones salian "caducadas"
#: y el auditor terminaba en rojo sin motivo. Es exactamente el fallo que este
#: proyecto ya pago con check_cableado ("un auditor que grita cuando no toca
#: acaba ignorandose"), cometido dentro del auditor escrito para evitarlo.
EXCEPCIONES_VERIFICADAS = {
    ("motor_veredicto.py", "guard_suma_tramos", "suma"): (
        "Verificado 27-08-2026 leyendo contrato_datos.tramos(): en la rama "
        "legada solo se anade un tramo `if d.valor` (truthy), asi que un cero "
        "NUNCA genera tramo. Y evaluar_fila_v4 solo llama a este guard cuando "
        "`tramos` es truthy, luego suma != 0 siempre que se le llama. El caso "
        "suma==0 y base_total==0 no es alcanzable. Comprobado ademas que una "
        "factura con tramo pero SIN base_total no revienta: guard_integridad_"
        "datos la para antes (da NO_COMPROBADO, no una excepcion)."
    ),
}


def _veredicto_de_return(nodo):
    """El literal de veredicto de un `return`, si devuelve uno."""
    valor = nodo.value
    if isinstance(valor, ast.Tuple) and valor.elts:
        valor = valor.elts[0]
    if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
        return valor.value
    return None


def _nombre_comparado_con_cero(nodo):
    """`x > 0`, `x >= 0`, `x != 0` -> 'x'. Cualquier otra cosa -> None.

    Se aceptan las tres formas a proposito: las tres expresan la misma idea
    ("solo comparo si hay algo con que comparar") y las tres dejan el mismo
    agujero cuando no lo hay."""
    if not isinstance(nodo, ast.Compare) or len(nodo.ops) != 1:
        return None
    if not isinstance(nodo.ops[0], (ast.Gt, ast.GtE, ast.NotEq)):
        return None
    izq, der = nodo.left, nodo.comparators[0]
    if (isinstance(izq, ast.Name) and isinstance(der, ast.Constant)
            and der.value == 0 and not isinstance(der.value, bool)):
        return izq.id
    return None


def analizar(codigo, nombre_fichero="<codigo>"):
    """Devuelve la lista de hallazgos: [(funcion, variable, linea)].

    Acepta el codigo como texto para que el ensayo pueda alimentarlo con
    casos construidos, sin tocar ningun fichero del proyecto."""
    hallazgos = []
    arbol = ast.parse(codigo, filename=nombre_fichero)
    funciones = [n for n in ast.walk(arbol)
                 if isinstance(n, ast.FunctionDef) and n.name.startswith("guard_")]
    for fn in funciones:
        # Solo interesa si la funcion puede llegar a decir OK: si nunca lo
        # dice, no hay falso verde posible por definicion.
        dice_ok = any(
            (_veredicto_de_return(r) or "").startswith("OK")
            for r in ast.walk(fn) if isinstance(r, ast.Return))
        if not dice_ok:
            continue
        for nodo in ast.walk(fn):
            if not (isinstance(nodo, ast.If)
                    and isinstance(nodo.test, ast.BoolOp)
                    and isinstance(nodo.test.op, ast.And)):
                continue
            variables = [v for v in (_nombre_comparado_con_cero(x)
                                     for x in nodo.test.values) if v]
            if not variables:
                continue
            # El cuerpo del `if` tiene que negar algo: si devuelve OK, el
            # sentido es el contrario y no es este patron.
            niega = any((_veredicto_de_return(r) or "") in VEREDICTOS_NEGATIVOS
                        for r in ast.walk(nodo) if isinstance(r, ast.Return))
            if niega:
                hallazgos.append((fn.name, variables[0], nodo.lineno))
    return hallazgos


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fichero", nargs="?", default="motor_veredicto.py")
    args = ap.parse_args()

    if not os.path.isfile(args.fichero):
        print(f"ERROR: no existe {args.fichero}", file=sys.stderr)
        sys.exit(2)

    with open(args.fichero, encoding="utf-8") as f:
        hallazgos = analizar(f.read(), args.fichero)

    base = os.path.basename(args.fichero)
    sin_declarar = [h for h in hallazgos
                    if (base, h[0], h[1]) not in EXCEPCIONES_VERIFICADAS]
    encontrados = {(base, h[0], h[1]) for h in hallazgos}
    # La caducidad solo se juzga sobre las excepciones escritas PARA ESTE
    # fichero: una excepcion de motor_veredicto.py no esta caducada porque
    # estemos analizando otra cosa.
    caducadas = [k for k in EXCEPCIONES_VERIFICADAS
                 if k[0] == base and k not in encontrados]

    print("=" * 70)
    print("AUDITORIA: un OK que en realidad significa 'no lo he comprobado'")
    print("=" * 70)
    print(f"  Fichero analizado : {args.fichero}")
    print(f"  Patrones hallados : {len(hallazgos)}")
    print(f"  Ya verificados    : {len(hallazgos) - len(sin_declarar)}")
    print()

    if sin_declarar:
        print("❌ PATRON SIN VERIFICAR — cada uno es un falso verde hasta que se")
        print("   demuestre lo contrario:")
        for fn, var, linea in sin_declarar:
            print(f"     {args.fichero}:{linea}  {fn}()")
            print(f"        `{var} > 0 and ...` seguido de un return OK:")
            print(f"        si {var} vale 0, el guard afirma que todo esta bien")
            print(f"        sin haber comparado nada. Debe ser NO_COMPROBADO.")
    else:
        print("✅ Ningun guard afirma OK por no haber podido comprobar.")

    if caducadas:
        print()
        print("⚠️  EXCEPCIONES CADUCADAS — declaradas aqui y ya no en el codigo.")
        print("   Se quitan: una lista blanca con entradas muertas acaba tapando")
        print("   un caso real (misma trampa que la lista `criticos` del motor).")
        for fichero, fn, var in caducadas:
            print(f"     {fichero} :: {fn}() / {var}")

    print()
    if sin_declarar or caducadas:
        print("❌ HAY QUE REVISARLO")
        sys.exit(1)
    print("✅ CORRECTO")


if __name__ == "__main__":
    main()
