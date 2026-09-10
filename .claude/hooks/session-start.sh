#!/bin/sh
# Hook de arranque de sesion — La Fabrica.
#
# QUE HACE: ejecuta `arranque.py` y su salida entra en el contexto de la sesion
# antes de que el modelo haga nada. Asi el estado del proyecto, la lista de
# pendientes y los avisos de privacidad NO dependen de que alguien se acuerde de
# leer un documento de 49 KB.
#
# QUE NO HACE, Y ES DELIBERADO: **no instala nada.** `.claude/rules/seguridad.md`
# prohibe instalar software sin aprobacion explicita para esa instalacion
# concreta, y eso incluye un `pip install` automatico al abrir la sesion. El
# hook DICE que falta y para que hace falta; instalarlo es una decision de
# Diego, cada vez.
#
# Corre en TODA superficie (local, Cloud, web), no solo en remoto: el PC de la
# asesoria es justo donde mas importa no saltarse nada.
#
# Nunca corta la sesion: si algo falla aqui, se avisa y se sigue. Un hook que
# impide arrancar es peor que un hook que no informa.

RAIZ="${CLAUDE_PROJECT_DIR:-$(dirname "$(dirname "$(dirname "$0")")")}"

# En el PC de la asesoria el interprete se llama `python`, no `python3`
# (comprobado el 26-08-2026: `python3` da command not found).
PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python
command -v "$PYTHON" >/dev/null 2>&1 || {
    echo "AVISO: no encuentro un interprete de Python. Lee EMPEZAR_AQUI.md a mano."
    exit 0
}

if [ ! -f "$RAIZ/arranque.py" ]; then
    echo "AVISO: no encuentro arranque.py en $RAIZ. Lee EMPEZAR_AQUI.md a mano."
    exit 0
fi

"$PYTHON" "$RAIZ/arranque.py" 2>&1 || \
    echo "AVISO: arranque.py ha fallado. Lee EMPEZAR_AQUI.md a mano antes de tocar nada."

exit 0
