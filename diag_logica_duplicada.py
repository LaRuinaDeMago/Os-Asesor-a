#!/usr/bin/env python3
"""diag_logica_duplicada.py — busca la FORMA del bug del "tipo 0".

POR QUE EXISTE
--------------
Creado el 15-09-2026. El 15-09 aparecieron, con un dia de diferencia, dos bugs
con la MISMA forma:

  · `verificar_303_pdf.py` tenia su propia suma de la contabilidad y nunca
    recibio el arreglo del "tipo 0" que `cuadre_303_ficha.py` si tenia.
  · `triangulacion_identidad_v0.py` tenia su propia `valida_nif` de DOS estados,
    mientras el motor usaba la de `nif_check` con TRES, corregida el 25-08.
    Resultado: la misma factura podia recibir SIN_DATO de un guard y FALLO de
    otro.

La forma es siempre la misma: **la misma logica escrita en dos ficheros,
arreglada en uno solo**. El segundo se encontro buscando esa forma con este
barrido, despues de que TRES repasos manuales no la vieran. De ahi la regla:

    Ante un "repasalo todo", no releer ficheros -- escribir el barrido.
    Un repaso a ojo encuentra lo que ya sospechas; un barrido encuentra lo
    que no.

QUE MIRA, Y QUE NO
------------------
  1. Funciones de DOMINIO con el mismo nombre en mas de un fichero de
     PRODUCCION. Excluye ensayo_*/test_*/audit_*/diff_*/barrido_*/cobertura_*
     (los helpers de prueba se llaman igual a proposito) y los nombres de
     andamiaje (`main`, `check`, `comprobar`...). Sin ese filtro salen ~30
     falsos positivos y la senal se pierde.
  2. Constantes de modulo con el mismo nombre y DISTINTO valor. Asi salio
     `MIN_NIFS`, que vale 5, 3, 3 y 1 en cuatro ficheros -- y el 3 de
     produccion descarta datos sin que nadie lo haya medido (PENDIENTE 1.E).

NO decide nada: **lista candidatos para que los mire una persona.** Cuerpos
distintos no es un defecto por si mismo (dos funciones pueden llamarse igual
con razon); es el sitio donde mirar.

NO TOCA NINGUN DATO REAL: solo lee el codigo fuente del propio repositorio.

Uso:
    python diag_logica_duplicada.py
"""
import ast
import os
import sys
from collections import defaultdict

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Nombres de andamiaje: se repiten a proposito en todo el repositorio y
#: ahogarian la senal. No son logica de dominio.
GENERICOS = {
    "main", "check", "comprobar", "correr", "ejecutar", "analizar", "cuenta",
    "_h", "clasifica", "crear_codigo", "run", "parse", "fmt", "pct", "linea",
    "cabecera", "resumen", "uso", "arg", "args", "norm", "normalizar",
}

#: Prefijos de ficheros que NO son produccion: sus funciones auxiliares se
#: llaman igual de un ensayo a otro, y eso es correcto.
NO_PRODUCCION = ("ensayo_", "test_", "audit_", "diff_", "barrido_", "cobertura_")


def es_produccion(ruta):
    return not os.path.basename(ruta).startswith(NO_PRODUCCION)


def recorrer(raiz="."):
    funcs, consts = defaultdict(list), defaultdict(list)
    for r, _, fs in os.walk(raiz):
        if ".git" in r:
            continue
        for f in fs:
            if not f.endswith(".py"):
                continue
            ruta = os.path.join(r, f).replace("\\", "/")
            try:
                arbol = ast.parse(open(ruta, encoding="utf-8",
                                       errors="replace").read())
            except SyntaxError:
                continue
            for n in arbol.body:
                if isinstance(n, ast.FunctionDef) and es_produccion(ruta):
                    if n.name in GENERICOS:
                        continue
                    cuerpo = ast.dump(ast.Module(body=n.body, type_ignores=[]))
                    funcs[n.name].append((ruta, len(n.body), hash(cuerpo)))
                elif isinstance(n, ast.Assign):
                    for t in n.targets:
                        if isinstance(t, ast.Name) and t.id.isupper() and len(t.id) > 3:
                            try:
                                v = ast.literal_eval(n.value)
                            except Exception:
                                continue
                            consts[t.id].append((ruta, repr(v)))
    return funcs, consts


def main():
    funcs, consts = recorrer()

    print("=" * 70)
    print("1. LOGICA DE DOMINIO DUPLICADA ENTRE FICHEROS DE PRODUCCION")
    print("=" * 70)
    print("   'CUERPOS DISTINTOS' = candidato a 'arreglado en uno y no en el otro'.")
    print("   No es un veredicto: es donde mirar.")
    print()
    n_div = 0
    for nombre, sitios in sorted(funcs.items()):
        if len(sitios) < 2:
            continue
        distintos = len({h for _, _, h in sitios}) > 1
        if distintos:
            n_div += 1
        estado = ">>> CUERPOS DISTINTOS <<<" if distintos else "identicas (copia)"
        print(f"  {nombre}()  -- {len(sitios)} definiciones  {estado}")
        for ruta, nl, _ in sitios:
            print(f"      {ruta:<46} {nl} sentencias")
    if not funcs:
        print("  (nada)")
    print(f"\n  con cuerpos divergentes: {n_div}")

    print()
    print("=" * 70)
    print("2. CONSTANTES CON EL MISMO NOMBRE Y DISTINTO VALOR")
    print("=" * 70)
    n_c = 0
    for nombre, sitios in sorted(consts.items()):
        vals = {v for _, v in sitios}
        if len(sitios) < 2 or len(vals) == 1:
            continue
        n_c += 1
        print(f"  {nombre} -- {len(vals)} valores distintos:")
        for ruta, v in sitios:
            print(f"      {ruta:<44} = {v[:70]}")
    if n_c == 0:
        print("  ninguna divergente.")
    print(f"\n  constantes divergentes: {n_c}")

    print()
    print("Recordatorio (PENDIENTE.md, criterio de cierre): el dia que un")
    print("repaso completo no encuentre nada, esa es la senal de dejar de")
    print("reforzar y empezar a entregar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
