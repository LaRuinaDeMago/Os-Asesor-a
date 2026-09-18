#!/usr/bin/env python3
"""cierre_sesion.py -- si una clave de IA sigue puesta al cerrar, que no
dependa de que alguien se acuerde de mirarlo.

POR QUE EXISTE (18-09-2026, a partir de un aviso externo que Diego trajo a la
sesion y que se verifico antes de construir nada)
--------------------------------------------------
`arranque.py` ya avisa AL EMPEZAR si `ANTHROPIC_API_KEY` esta puesta (ver su
aviso de la seccion 5-bis). No existia el mismo aviso AL TERMINAR -- y una
clave puesta "para una tarea de hoy" que sigue puesta manana es exactamente
el tipo de deriva silenciosa que este proyecto ya ha cazado dos veces (el CI
apuntando a la rama equivocada tres semanas, el `.DAT` sin bloquear ocho
dias). `.claude/rules/datos.md` ya dice que la clave puesta no autoriza nada
por si sola -- pero nada comprobaba hasta hoy si seguia puesta cuando ya no
hacia falta.

LO QUE HACE, Y LO QUE NO PUEDE HACER
--------------------------------------
Mide (nunca imprime el VALOR, solo si la variable existe) y deja constancia
en un log local, igual que `vigilancia_boe.log`. Un hook de Windows/Claude
Code (`SessionEnd`, ver `.claude/settings.json`) lo ejecuta solo -- pero un
hook no puede sostener una conversacion: no hay forma de que este script
"pregunte y espere la respuesta" como hace `puerta_cloud.abrir_lote()` con el
recuento exacto de un lote, porque para cuando corre ya no hay nadie del otro
lado del hook esperando teclear algo. Por eso NO finge una pregunta
interactiva -- dice, con la mayor claridad posible, que la clave sigue
puesta, y deja la decision (desactivarla o no) donde siempre estuvo: en
Diego, tarea por tarea, la proxima vez que abra una sesion.

Se puede ejecutar tambien a mano, en cualquier momento, para ver el estado
sin esperar a que cierre nada:

    python cierre_sesion.py
"""
import datetime
import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUTA_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cierre_sesion.log")

#: Mismo par que ya vigila arranque.py/modo_trabajo.py. Si se ana de una
#: tercera clave al proyecto, se ana de aqui tambien -- un solo sitio.
CLAVES_VIGILADAS = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY")


def claves_activas(entorno=None):
    """Devuelve la lista de nombres (nunca valores) de las claves vigiladas
    que estan puestas en `entorno` (por defecto, el entorno real)."""
    entorno = os.environ if entorno is None else entorno
    return [nombre for nombre in CLAVES_VIGILADAS if entorno.get(nombre)]


def registrar(activas, ruta_log=RUTA_LOG):
    """Anade una linea al log local (nunca versionado -- ver .gitignore),
    igual que vigilancia_boe.log: fecha, y que se comprobo, nunca un valor."""
    marca = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ruta_log, "a", encoding="utf-8") as fh:
        if activas:
            fh.write(f"{marca} -- SIGUEN PUESTAS: {', '.join(activas)}\n")
        else:
            fh.write(f"{marca} -- ninguna clave de IA puesta\n")


def imprimir_aviso(activas):
    if not activas:
        print("cierre_sesion: ninguna clave de IA (Anthropic/Gemini) esta puesta. Nada que avisar.")
        return
    print("=" * 70)
    print("  AVISO DE CIERRE -- sigue puesta al menos una clave de IA:")
    for nombre in activas:
        print(f"    - {nombre}")
    print("  Esto NO autoriza nada por si solo (.claude/rules/datos.md) --")
    print("  pero si la tarea de hoy ya termino, valora desactivarla ahora,")
    print("  para no depender de acordarte la proxima vez que abras una sesion.")
    print("=" * 70)


def main():
    activas = claves_activas()
    imprimir_aviso(activas)
    registrar(activas)
    return 0


if __name__ == "__main__":
    sys.exit(main())
