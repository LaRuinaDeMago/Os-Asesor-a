#!/usr/bin/env python3
"""audit_estados.py — ¿el veredicto ESCUCHA todo lo que los guards saben decir?

POR QUE HACE FALTA, Y NO LO CUBRE NINGUNO DE LOS OTROS DOS AUDITORES
--------------------------------------------------------------------
Hay tres preguntas distintas y cada una tapa un agujero que las otras no ven:

    audit_project.py     ¿el guard existe y alguien lo llama?      (HUERFANO)
    cobertura_guards.py  ¿ha llegado alguna vez a decir que no?    (NO PROBADO)
    audit_estados.py     ¿lo que dice cambia el veredicto?         (MUDO / MUERTO)

El 21-08-2026 aparecio la tercera clase por las malas. `guard_cuenta_gasto_
coherente` estaba cableado (audit_project en verde) y su rama FALLO -> AMBAR
llevaba escrita en el veredicto desde el primer dia. Pero el guard NO PODIA
devolver FALLO: no comparaba nada. Una rama del veredicto inalcanzable, en pie
durante semanas, con el auditor y la suite en verde.

Este script caza esa clase entera, no ese caso:

  RAMA MUERTA   el veredicto pregunta por un estado que ese guard no sabe
                producir. La proteccion parece existir y no existe.

  GUARD MUDO    el guard sabe producir un estado NO benigno y el veredicto
                sale VERDE igual. Es un falso verde estructural: la peor
                especie, porque no depende de los datos de ninguna factura.

COMO LO COMPRUEBA — importa, porque no es leyendo el codigo
-----------------------------------------------------------
El VOCABULARIO de cada guard se saca del AST: que literales aparecen en la
primera posicion de sus `return`. Eso es lo que el guard SABE decir.

El CONSUMO no se lee, se PRUEBA: se parte de un cuadro de guards todo benigno
que da VERDE, se pone UN guard en UN estado, y se mira si el veredicto se
mueve. Si no se mueve, ese estado no lo escucha nadie. Leer el codigo del
veredicto habria repetido el error original —la rama estaba escrita, parecia
correcta, y era inalcanzable—; ejecutarlo, no.

Uso:  python3 audit_estados.py
"""
import ast
import sys

import motor_veredicto as mv

#: Estados que significan "he mirado y no hay nada que decir".
BENIGNOS = frozenset({"OK", "NO_APLICA", "ALTA"})

#: Ramas del veredicto que HOY son inalcanzables A PROPOSITO, con el motivo.
#: No se borran de `criticos`: la lista es una especificacion —"si esto llega a
#: decir FALLO, es ROJO"— y vale la pena conservarla para el dia que el guard
#: aprenda a decirlo. Lo que no vale es que este escrita y nadie sepa que hoy no
#: dispara. El auditor tambien avisa si una de estas declaraciones se queda
#: OBSOLETA (la rama vuelve a estar viva), para que no se pudra aqui.
RAMA_MUERTA_DECLARADA = {
    ("integridad_datos", "FALLO"):
        "por diseno: un importe ilegible no es un error contable, es un dato que "
        "falta. Devuelve NO_COMPROBADO -> AMBAR. Un ROJO diria 'he encontrado un "
        "fallo' cuando lo cierto es 'no he podido mirar'.",
    ("nif_casa_historico", "FALLO"):
        "desde el 20-08-2026: un proveedor nuevo dejo de ser un error y pasa a "
        "NO_COMPROBADO -> AMBAR [CRITERIO], que es un alta que decidir. El NIF "
        "matematicamente imposible lo sigue cazando nif_digito_control, que si "
        "devuelve FALLO y si esta en criticos: no se ha perdido cobertura.",
}

#: Guards cuyo NO_COMPROBADO esta declarado como estructural en el veredicto
#: (lista `exentos` de calcular_veredicto_v4). Que sean mudos en ese estado es
#: la decision correcta, ya razonada ahi, no un hallazgo.
MUDEZ_DECLARADA = {
    ("vencimiento_coherente", "NO_COMPROBADO"),
    ("importe_atipico", "NO_COMPROBADO"),
    ("secuencia_documental_proveedor", "NO_COMPROBADO"),
    ("estructura_reconocida", "NO_COMPROBADO"),
    ("patron_cartera", "NO_COMPROBADO"),
    ("tipo_producto_iva_semantico", "NO_COMPROBADO"),
}


def _primer_literal(nodo):
    if isinstance(nodo, ast.Tuple) and nodo.elts:
        primero = nodo.elts[0]
        if isinstance(primero, ast.Constant) and isinstance(primero.value, str):
            return primero.value
    return None


def vocabulario_por_guard(path="motor_veredicto.py"):
    """Que estados sabe producir cada guard, sacado del AST y no de la memoria.

    Dos fuentes, y la segunda hizo falta al estrenar esto: no todo estado sale
    de un `return` dentro del guard. `aritmetica_base_tipo` y `cuadre_total`
    reciben su NO_COMPROBADO por asignacion directa en evaluar_fila_v4 cuando
    la factura no trae desglose. Contar solo los `return` los daba por incapaces
    de un estado que producen a diario."""
    arbol = ast.parse(open(path, encoding="utf-8").read())
    vocab = {}
    for nodo in arbol.body:
        if not isinstance(nodo, ast.FunctionDef) or not nodo.name.startswith("guard_"):
            continue
        estados = set()
        for sub in ast.walk(nodo):
            if isinstance(sub, ast.Return):
                e = _primer_literal(sub.value)
                if e:
                    estados.add(e)
        if estados:
            vocab[nodo.name[len("guard_"):]] = estados

    # Segunda fuente: guards["X"] = (...) escrito a mano en el orquestador del
    # veredicto, directamente o a traves de una tupla con nombre.
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.FunctionDef):
            continue
        locales = {}
        for sub in ast.walk(nodo):
            if isinstance(sub, ast.Assign) and len(sub.targets) == 1:
                destino = sub.targets[0]
                if isinstance(destino, ast.Name):
                    e = _primer_literal(sub.value)
                    if e:
                        locales[destino.id] = e
        for sub in ast.walk(nodo):
            if not (isinstance(sub, ast.Assign) and len(sub.targets) == 1):
                continue
            destino = sub.targets[0]
            if not (isinstance(destino, ast.Subscript)
                    and isinstance(destino.value, ast.Name)
                    and destino.value.id == "guards"
                    and isinstance(destino.slice, ast.Constant)):
                continue
            nombre = destino.slice.value
            e = _primer_literal(sub.value)
            if e is None and isinstance(sub.value, ast.Name):
                e = locales.get(sub.value.id)
            if e:
                vocab.setdefault(nombre, set()).add(e)
    return vocab


def cuadro_benigno(nombres):
    base = {n: ("OK", "-") for n in nombres}
    base["confianza_captura"] = ("ALTA", "-")
    return base


def main():
    vocab = vocabulario_por_guard()

    # Los nombres tal y como los registra el veredicto (clave del dict guards),
    # tomados de una evaluacion real: es la unica fuente fiable de la lista.
    _, _, guards_reales = mv.evaluar_fila_v4(
        {'nif': 'B99999999', 'proveedor': 'X', 'nº_documento': 'F1',
         'fecha_expedicion': '2026-03-15', 'base_total': '100',
         'base_21': '100', 'iva_total': '21', 'total_factura': '121'},
        set(), {}, {}, {}, {}, 2020, None, 2026)
    nombres = sorted(guards_reales)

    base = cuadro_benigno(nombres)
    v_base, _ = mv.calcular_veredicto_v4(base)
    if v_base != "VERDE":
        print(f"El cuadro todo-benigno no da VERDE, da {v_base}. "
              f"Sin linea de salida no se puede medir nada.")
        return 2

    # Que estados los caza una regla GENERAL (el barrido de NO_COMPROBADO, el
    # `confianza != ALTA`) y no una rama dedicada a un guard concreto. Sin esto,
    # el auditor acusaba de "rama muerta" a los 26 guards por el mero hecho de
    # existir el barrido. Se mide con una sonda que NO es ningun guard real: si
    # un nombre inventado en ese estado ya mueve el veredicto, es la red general
    # quien lo caza, y la reaccion de cualquier guard concreto no demuestra que
    # exista una rama dedicada a el.
    red_general = set()
    for estado in ("FALLO", "NO_COMPROBADO", "AMBAR", "BAJA", "MEDIA"):
        cuadro = dict(base)
        cuadro["__sonda_que_no_es_ningun_guard__"] = (estado, "sonda")
        if mv.calcular_veredicto_v4(cuadro)[0] != "VERDE":
            red_general.add(estado)

    muertas, mudos, sin_vocabulario, obsoletas = [], [], [], []
    for nombre in nombres:
        conocidos = vocab.get(nombre)
        if not conocidos:
            sin_vocabulario.append(nombre)
            continue
        # 1. lo que el guard sabe decir, ¿se escucha?
        for estado in sorted(conocidos - BENIGNOS):
            cuadro = dict(base)
            cuadro[nombre] = (estado, "sonda")
            v, _ = mv.calcular_veredicto_v4(cuadro)
            if v == "VERDE" and (nombre, estado) not in MUDEZ_DECLARADA:
                mudos.append((nombre, estado))
        # 2. lo que el veredicto escucha, ¿lo sabe decir el guard?
        # ...y su propia red: `confianza_captura` se consulta como
        # `!= "ALTA"`, asi que reacciona a CUALQUIER cosa. Un guard bajo una red
        # asi tampoco puede tener ramas muertas, por definicion. Se detecta
        # metiendole un estado que no existe en ningun sitio.
        sonda = dict(base)
        sonda[nombre] = ("__ESTADO_QUE_NO_EXISTE__", "sonda")
        bajo_red_propia = mv.calcular_veredicto_v4(sonda)[0] != "VERDE"

        for estado in ("FALLO", "NO_COMPROBADO", "AMBAR"):
            if estado in conocidos or estado in red_general or bajo_red_propia:
                continue
            cuadro = dict(base)
            cuadro[nombre] = (estado, "sonda")
            v, _ = mv.calcular_veredicto_v4(cuadro)
            if v != "VERDE":
                muertas.append((nombre, estado))
        # Declaracion obsoleta: se dijo que esta rama estaba muerta y ya no lo esta.
        for estado in sorted(conocidos):
            if (nombre, estado) in RAMA_MUERTA_DECLARADA:
                obsoletas.append((nombre, estado))

    print("=" * 70)
    print("AUDITORIA DE ESTADOS: lo que los guards dicen vs lo que el veredicto oye")
    print("=" * 70)
    print(f"  guards en el veredicto     : {len(nombres)}")
    print(f"  con vocabulario leido      : {len(nombres) - len(sin_vocabulario)}")
    print(f"  mudez declarada y razonada : {len(MUDEZ_DECLARADA)}")
    print(f"  ramas muertas declaradas   : {len(RAMA_MUERTA_DECLARADA)}")
    print(f"  estados con red general    : {', '.join(sorted(red_general)) or 'ninguno'}")
    print()

    declaradas = [x for x in muertas if x in RAMA_MUERTA_DECLARADA]
    muertas = [x for x in muertas if x not in RAMA_MUERTA_DECLARADA]

    if muertas:
        print("RAMAS MUERTAS — el veredicto pregunta algo que el guard no sabe decir:")
        for n, e in muertas:
            print(f"  ✗ {n:<32} el veredicto reacciona a {e}, y el guard nunca lo devuelve")
        print("    La proteccion PARECE existir. No existe. Es el fallo del 21-08.")
        print()
    if obsoletas:
        print("DECLARACIONES OBSOLETAS — se dieron por muertas y han revivido:")
        for n, e in obsoletas:
            print(f"  ! {n:<32} ya sabe devolver {e}; quitar de RAMA_MUERTA_DECLARADA")
        print()
    if declaradas:
        print("Inalcanzables A PROPOSITO (declaradas y razonadas):")
        for n, e in declaradas:
            print(f"  · {n} / {e}")
            print(f"      {RAMA_MUERTA_DECLARADA[(n, e)]}")
        print()
    if mudos:
        print("GUARDS MUDOS — saben decir que no, y el veredicto sale VERDE igual:")
        for n, e in mudos:
            print(f"  ✗ {n:<32} devuelve {e} y el veredicto no se entera")
        print("    Falso verde ESTRUCTURAL: no depende de los datos de la factura.")
        print()
    if sin_vocabulario:
        print("Sin vocabulario legible en el AST (revisar a mano):")
        for n in sin_vocabulario:
            print(f"  · {n}")
        print()

    if muertas or mudos or obsoletas:
        print("HAY HALLAZGOS. Cada linea de arriba es una proteccion que no protege.")
        return 1
    print("Todo lo que un guard sabe decir mueve el veredicto, y el veredicto no")
    print("pregunta por nada que ningun guard sepa contestar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
