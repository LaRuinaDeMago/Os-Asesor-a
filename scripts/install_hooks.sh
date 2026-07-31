#!/bin/sh
# Instala el hook de pre-commit local. Los hooks de .git/hooks/ NO se
# versionan con git (git no los copia al clonar), así que este paso hay que
# ejecutarlo una vez tras cada clon nuevo del repositorio.
#
# Uso: sh scripts/install_hooks.sh

set -e
RAIZ="$(git rev-parse --show-toplevel)"
cp "$RAIZ/scripts/pre-commit" "$RAIZ/.git/hooks/pre-commit"
chmod +x "$RAIZ/.git/hooks/pre-commit"
echo "Hook de pre-commit instalado en .git/hooks/pre-commit"
