#!/bin/sh
# Automatiza el "preparar" del guardado — nunca el "publicar".
#
# Qué hace, en este orden:
#   1. Lista los archivos modificados/nuevos que git detecta (respeta
#      .gitignore, así que nunca toca lo de NUNCA_SUBE_FILENAMES.txt).
#   2. Corre el escáner de privacidad (scripts/privacy_scan.py) sobre
#      exactamente esos archivos, antes de tocar nada.
#   3. Si el escáner encuentra algo, PARA aquí sin hacer git add ni commit.
#   4. Si está limpio, hace `git add` de esa lista concreta (nunca `-A` a
#      ciegas) y crea el commit con el mensaje que se le pase.
#   5. Se PARA ahí. Nunca hace `git push` — eso sigue siendo siempre una
#      decisión y una acción aparte, aprobada explícitamente cada vez.
#
# Uso: sh scripts/guardar_avance.sh "mensaje del commit"

set -e
RAIZ="$(git rev-parse --show-toplevel)"
cd "$RAIZ"

MENSAJE="$1"
if [ -z "$MENSAJE" ]; then
    echo "Uso: sh scripts/guardar_avance.sh \"mensaje del commit\""
    exit 1
fi

PYTHON=python3
command -v python3 >/dev/null 2>&1 || PYTHON=python

ARCHIVOS=$(git status --porcelain | grep -v '^D ' | sed 's/^...//')

if [ -z "$ARCHIVOS" ]; then
    echo "Nada que guardar — no hay cambios detectados."
    exit 0
fi

echo "=== Archivos que se van a añadir (respetando .gitignore) ==="
echo "$ARCHIVOS"
echo ""

echo "=== Escaneando en busca de datos sensibles antes de tocar nada ==="
$PYTHON "$RAIZ/scripts/privacy_scan.py" $ARCHIVOS
RESULTADO=$?

if [ $RESULTADO -ne 0 ]; then
    echo ""
    echo "PARADO: el escáner encontró algo. No se ha hecho git add ni commit."
    echo "Revisa lo de arriba antes de continuar."
    exit 1
fi

git add $ARCHIVOS
git commit -m "$MENSAJE"

echo ""
echo "=== Commit local creado. FALTA EL PUSH — es una decisión aparte, ==="
echo "=== pídelo explícitamente cuando quieras subirlo de verdad.       ==="
