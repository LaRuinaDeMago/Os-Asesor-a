#!/bin/sh
# Hook de cierre de sesion -- La Fabrica.
#
# QUE HACE: ejecuta `cierre_sesion.py`, que comprueba si ANTHROPIC_API_KEY o
# GEMINI_API_KEY siguen puestas al terminar la sesion y, si es asi, avisa y
# deja constancia en `cierre_sesion.log` (nunca versionado, nunca el valor de
# la clave). Simetrico al aviso que `arranque.py` ya da al EMPEZAR -- hasta
# el 18-09-2026 no habia el mismo aviso al terminar.
#
# QUE NO HACE, Y ES DELIBERADO: no desactiva ninguna clave por su cuenta, ni
# finge una pregunta interactiva -- un hook de cierre no tiene a nadie al
# otro lado esperando teclear una respuesta. Solo dice, con claridad, que
# sigue puesta; la decision de desactivarla sigue siendo de Diego.
#
# Nunca corta el cierre de la sesion: si algo falla aqui, se ignora.

RAIZ="${CLAUDE_PROJECT_DIR:-$(dirname "$(dirname "$(dirname "$0")")")}"

PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python
command -v "$PYTHON" >/dev/null 2>&1 || exit 0

[ -f "$RAIZ/cierre_sesion.py" ] || exit 0

"$PYTHON" "$RAIZ/cierre_sesion.py" 2>&1

exit 0
