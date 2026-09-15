#!/usr/bin/env python3
"""ensayo_fuentes_externas.py — ensayo del registro de constantes externas.

POR QUE, Y POR QUE ESTE EN CONCRETO
--------------------------------------
`fuentes_externas.py` existe para avisar de que un numero que copiamos de la
ley o de la AEAT ha dejado de coincidir con el codigo, o lleva demasiado sin
verificarse. Es decir: es un auditor. Y un auditor que se apaga en silencio
deja el agujero PEOR que antes, porque ademas lo firma como revisado -- lo
mismo que le paso al 11o auditor de este proyecto, dos semanas apagado
(PROJECT_STATUS.md, 09-09-2026), y a las siete suites del 11-09.

Lo que se prueba no es que los numeros sean correctos --eso lo dice la fuente
oficial, no un test-- sino que el MECANISMO sabe darse cuenta.
"""
import datetime
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fuentes_externas as fx

FALLOS = []


def comprobar(titulo, condicion, detalle=""):
    if condicion:
        print(f"  OK   {titulo}")
    else:
        print(f"  FALLA  {titulo}" + (f"   {detalle}" if detalle else ""))
        FALLOS.append(titulo)


def main():
    print("=== ENSAYO: el registro de constantes externas ===\n")

    print("A. El repositorio tal cual esta hoy")
    disc, cad, sinver = fx.revisar()
    comprobar("ninguna constante registrada discrepa del codigo", not disc, str(disc))
    comprobar("ninguna verificacion ha caducado todavia", not cad, str(cad))
    comprobar("hay constantes registradas (el registro no esta vacio)",
              len(fx.FUENTES) >= 5, f"{len(fx.FUENTES)}")

    print("\nB. Si alguien cambia una constante, TIENE que saltar")
    # Es el caso que motiva todo: el codigo se edita y el registro se queda
    # con el valor viejo, o al reves. Sin esto, el registro seria un adorno.
    una = fx.FUENTES[0]
    original = una.valor
    try:
        una.valor = tuple(list(original) + [999])
        disc2, _, _ = fx.revisar()
        comprobar("una constante que no coincide sale como discrepancia",
                  any(k == una.clave for k, _ in disc2), str(disc2))
        comprobar("y el detalle dice los dos valores, para poder decidir",
                  any("el codigo tiene" in d for k, d in disc2 if k == una.clave),
                  str(disc2))
    finally:
        una.valor = original
    comprobar("y al restaurarla vuelve a estar limpio", not fx.revisar()[0])

    print("\nC. El orden de las casillas no cuenta, el conjunto si")
    # El impreso no las lista en el orden que a nosotros nos convenga
    # escribirlas. Exigir el orden daria rojos que no significan nada.
    una2 = fx.FUENTES[1]
    orig2 = una2.valor
    try:
        una2.valor = tuple(reversed(orig2))
        comprobar("la misma tupla al reves NO se considera discrepancia",
                  not any(k == una2.clave for k, _ in fx.revisar()[0]))
    finally:
        una2.valor = orig2

    print("\nD. La caducidad: 'nadie lo ha mirado' NO es 'esta mal'")
    vieja = fx.Fuente(clave="prueba.vieja", descripcion="sintetica",
                      modulo="fuentes_externas", atributo="MESES_HASTA_CADUCAR",
                      valor=fx.MESES_HASTA_CADUCAR,
                      fuente="inventada", url="", verificado="2020-01-01",
                      estado=fx.VERIFICADO)
    comprobar("una verificacion de hace anios cuenta como caducada", vieja.caducada())
    comprobar("y el valor sigue coincidiendo: caducar no es discrepar",
              vieja.coincide()[0], str(vieja.coincide()))
    reciente = fx.Fuente(clave="prueba.nueva", descripcion="sintetica",
                         modulo="fuentes_externas", atributo="MESES_HASTA_CADUCAR",
                         valor=fx.MESES_HASTA_CADUCAR, fuente="inventada", url="",
                         verificado=datetime.date.today().isoformat(),
                         estado=fx.VERIFICADO)
    comprobar("una de hoy no esta caducada", not reciente.caducada())
    justo = datetime.date.today().replace(day=1)
    comprobar("el limite se mide en meses cumplidos, no en dias sueltos",
              reciente.meses_desde_verificacion(justo) <= 0,
              str(reciente.meses_desde_verificacion(justo)))

    # Y LO QUE DE VERDAD IMPORTA: que revisar() --el camino que usa
    # audit_project.py-- LA REPORTE. Encontrado saboteando este mismo ensayo
    # el 15-09-2026: desactivar la caducidad dentro de revisar() no hacia
    # fallar nada, porque la familia A comprueba "no hay caducadas" (cierto
    # de vacio) y la D probaba el metodo suelto. El auditor apagado en
    # silencio, en el ensayo escrito para impedirlo. Se prueba el camino
    # completo, no la pieza.
    fuentes_originales = fx.FUENTES
    try:
        fx.FUENTES = fuentes_originales + (vieja,)
        _, cad_inyectada, _ = fx.revisar()
        comprobar("revisar() REPORTA la caducada, no solo la sabe detectar",
                  any(k == "prueba.vieja" for k, _, _ in cad_inyectada),
                  str(cad_inyectada))
        comprobar("y dice desde cuando y cuantos meses lleva",
                  any(k == "prueba.vieja" and f == "2020-01-01" and m > 12
                      for k, f, m in cad_inyectada), str(cad_inyectada))
        comprobar("una caducada NO se cuenta ademas como discrepancia",
                  not any(k == "prueba.vieja" for k, _ in fx.revisar()[0]))
    finally:
        fx.FUENTES = fuentes_originales
    comprobar("y al quitarla, revisar() vuelve a estar limpio", not fx.revisar()[1])

    print("\nE. Una constante que desaparece del codigo no pasa en silencio")
    # Si alguien renombra o borra la constante, el registro apunta a nada. Eso
    # es una discrepancia, no un aprobado por ausencia.
    fantasma = fx.Fuente(clave="prueba.fantasma", descripcion="sintetica",
                         modulo="fuentes_externas", atributo="NO_EXISTE_ESTE_NOMBRE",
                         valor=1, fuente="inventada", url="",
                         verificado="2026-09-15", estado=fx.VERIFICADO)
    ok, detalle = fantasma.coincide()
    comprobar("apuntar a una constante que no existe es discrepancia", not ok, detalle)
    comprobar("y lo dice sin reventar", "AttributeError" in detalle, detalle)

    print("\nF. Se lee el CODIGO, no el fichero como texto")
    # Comparar el fichero como texto se dejaria enganiar por un comentario que
    # mencione el valor. Se importa el modulo y se lee el atributo de verdad:
    # misma leccion que la barrera de privacidad (contenido, no nombre).
    import extraer_303_pdf
    comprobar("el valor leido es el objeto real del modulo importado",
              fx.FUENTES[0].valor_en_codigo() is extraer_303_pdf.SUMANDOS_TOTAL_DEVENGADO)

    print("\nG. Lo que este registro NO promete")
    # Un registro que dijera VERIFICADO de todo seria mas comodo y mentiria.
    # PARCIAL tiene que ser un estado usable y visible.
    comprobar("PARCIAL y SIN_VERIFICAR existen como estados distintos de VERIFICADO",
              fx.PARCIAL != fx.VERIFICADO and fx.SIN_VERIFICAR != fx.VERIFICADO)
    comprobar("y hay alguna anotada honestamente como no verificada del todo",
              any(f.estado != fx.VERIFICADO for f in fx.FUENTES),
              "si todas dijeran VERIFICADO habria que sospechar")
    comprobar("toda fuente registrada declara su origen y su fecha",
              all(f.fuente and f.verificado for f in fx.FUENTES))

    print()
    if FALLOS:
        print(f"FALLAN {len(FALLOS)} comprobaciones:")
        for f in FALLOS:
            print(f"  - {f}")
        return 1
    print("El ensayo pasa. El registro sabe darse cuenta de que una constante "
          "cambio, de que una verificacion envejecio, y no llama verificado a "
          "lo que no lo esta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
