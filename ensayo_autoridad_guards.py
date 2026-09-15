#!/usr/bin/env python3
"""ensayo_autoridad_guards.py — ensayo del registro de autoridad de los guards.

QUE PRUEBA, Y QUE NO PUEDE PROBAR
------------------------------------
NO prueba que las citas legales sean correctas. Eso no lo puede decir un test:
lo dice el texto oficial. Lo que prueba es que el MECANISMO no miente:

  · que ningun guard del motor se quede sin la decision norma/dato/criterio,
  · que una anotacion que apunta a un guard borrado salte,
  · y --lo mas importante-- que una cita PROPUESTA no pueda pasar por
    verificada por el simple paso del tiempo.

Ese ultimo punto es el que justifica el fichero entero. El riesgo real de un
registro de autoridad no es equivocarse en un articulo: es que dentro de seis
meses alguien lea `guard_recargo_equivalencia -> art. 154 LIVA` y lo de por
comprobado porque lleva ahi mucho tiempo. Por eso el recuento de verificadas se
imprime en cada pasada de la auditoria, y por eso hoy dice CERO.
"""
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import autoridad_guards as ag

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK   {titulo}")
    else:
        print(f"  FALLA  {titulo}" + (f"   {detalle}" if detalle else ""))
        FALLOS.append(titulo)


def main():
    print("=== ENSAYO: autoridad de los guards ===\n")

    print("A. Ningun guard del motor se queda sin decidir")
    sin_autoridad, sobran, por_estado, por_origen = ag.revisar()
    comprobar("todos los guards del motor estan anotados", not sin_autoridad,
              str(sin_autoridad))
    comprobar("ninguna anotacion apunta a un guard que ya no existe", not sobran,
              str(sobran))
    reales = ag.guards_del_motor()
    comprobar("los guards se leen del AST del motor, y hay unos cuantos",
              len(reales) >= 20, f"{len(reales)}")
    comprobar("tantas anotaciones como guards, ni una de mas",
              len(ag.AUTORIDADES) == len(reales),
              f"anotadas={len(ag.AUTORIDADES)} reales={len(reales)}")

    print("\nB. Un guard nuevo nace con la pregunta sin contestar, y se nota")
    # Es el patron de check_cableado y del 19o auditor: lo que no puede pasar
    # es que un guard entre sin que nadie decida si aplica norma o criterio.
    originales = ag.AUTORIDADES
    try:
        ag.AUTORIDADES = tuple(a for a in originales
                               if a.guard != "guard_cuadre_total")
        sin2, _, _, _ = ag.revisar()
        comprobar("quitar una anotacion deja el guard SIN ANOTAR y salta",
                  "guard_cuadre_total" in sin2, str(sin2))
    finally:
        ag.AUTORIDADES = originales
    comprobar("y al devolverla vuelve a estar limpio", not ag.revisar()[0])

    try:
        ag.AUTORIDADES = originales + (
            ag.Autoridad("guard_que_ya_no_existe", ag.NORMA, "inventada",
                         ag.PROPUESTO, "sintetica"),)
        _, sobran2, _, _ = ag.revisar()
        comprobar("una anotacion de un guard borrado sale como sobrante",
                  "guard_que_ya_no_existe" in sobran2, str(sobran2))
    finally:
        ag.AUTORIDADES = originales

    print("\nC. Lo que de verdad importa: una PROPUESTA no es un hecho")
    verificadas = por_estado.get(ag.VERIFICADO, 0)
    normas = por_origen.get(ag.NORMA, 0)
    comprobar("hay citas de norma registradas", normas >= 10, str(normas))
    comprobar("el registro sabe cuantas estan verificadas de verdad",
              isinstance(verificadas, int))
    comprobar("HOY no hay ninguna verificada, y el registro lo dice",
              verificadas == 0,
              "si esto cambia sin haber leido los textos, alguien se ha "
              "auto-aprobado")
    comprobar("toda cita de norma declara de donde sale la PROPUESTA",
              all(a.procedencia for a in ag.AUTORIDADES if a.origen == ag.NORMA))
    comprobar("una cita VERIFICADA tendria que traer url y fecha, y ninguna las trae",
              all(not (a.estado == ag.VERIFICADO and not (a.url and a.verificado))
                  for a in ag.AUTORIDADES))

    print("\nD. Los tres origenes dicen cosas distintas, y eso es el punto")
    # Presentar como obligacion legal lo que es criterio del despacho seria el
    # peor error posible de cara a un cliente. Por eso CRITERIO existe.
    tecnicos = [a for a in ag.AUTORIDADES if a.origen == ag.TECNICO]
    criterios = [a for a in ag.AUTORIDADES if a.origen == ag.CRITERIO]
    comprobar("hay guards marcados como TECNICO (calidad del dato)", tecnicos)
    comprobar("y ninguno de ellos finge una norma detras",
              all(a.norma == "—" and a.estado == ag.SIN_IDENTIFICAR for a in tecnicos),
              str([a.guard for a in tecnicos if a.norma != "—"]))
    comprobar("hay al menos un guard marcado como CRITERIO del despacho", criterios)
    comprobar("y tampoco finge una norma",
              all(a.norma == "—" for a in criterios))
    comprobar("cada guard tiene UN solo origen, no dos",
              len({a.guard for a in ag.AUTORIDADES}) == len(ag.AUTORIDADES))
    comprobar("todo guard anotado lleva nota explicando por que esta donde esta",
              all(a.nota for a in ag.AUTORIDADES),
              str([a.guard for a in ag.AUTORIDADES if not a.nota]))

    print("\nE. El registro no toca el motor")
    # Decision de diseno: la cita vive fuera de motor_veredicto.py, que es la
    # pieza que .claude/rules/contabilidad.md protege. Si alguien mete esto
    # dentro del motor algun dia, que sea una decision, no un descuido.
    fuente = open("autoridad_guards.py", encoding="utf-8").read()
    comprobar("autoridad_guards.py no importa motor_veredicto",
              "import motor_veredicto" not in fuente)
    comprobar("y lee el motor solo como TEXTO, para el AST",
              "ast.parse" in fuente)

    print()
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. Ningun guard se queda sin decidir si aplica norma, "
          "dato o criterio, y ninguna cita propuesta se presenta como verificada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
