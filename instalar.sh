#!/bin/sh
# Instala o actualiza Mírame en macOS y Linux con un solo comando:
#
#   curl -LsSf https://raw.githubusercontent.com/jacomv/mirame/main/instalar.sh | sh
#
# Qué hace: instala uv (si falta), que a su vez trae Python; instala Mírame con su
# ffmpeg y todo lo demás; descarga el navegador de las capturas; deja un acceso directo
# en el escritorio y abre la app. Volver a ejecutarlo actualiza a la última versión.
# No pide contraseña de administrador ni toca nada fuera de tu usuario.
set -eu

FUENTE="${MIRAME_FUENTE:-https://github.com/jacomv/mirame/archive/refs/heads/main.zip}"

paso() { printf '\n\033[1m%s\033[0m\n' "$1"; }

paso "1/4 · Preparando uv (instala Python y Mírame)"
if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
else
  curl -LsSf https://astral.sh/uv/install.sh | sh
  UV="$HOME/.local/bin/uv"
fi

paso "2/4 · Instalando Mírame (la primera vez tarda unos minutos)"
"$UV" tool install --force --refresh --python 3.12 "mirame[capturas] @ $FUENTE"
"$UV" tool update-shell >/dev/null 2>&1 || true
MIRAME="$("$UV" tool dir --bin)/mirame"

paso "3/4 · Descargando el navegador para las capturas (unos 150 MB)"
"$MIRAME" instalar-capturas || echo "No se pudo; las capturas quedan desactivadas. Lo demás funciona."

paso "4/4 · Creando el acceso directo"
"$MIRAME" acceso || true

printf '\n\033[1;32mMírame %s quedó instalada.\033[0m\n' "$("$MIRAME" --version | cut -d' ' -f2)"
echo "La próxima vez ábrela con el acceso directo del escritorio, o escribe: mirame"
[ -n "${MIRAME_SIN_ABRIR:-}" ] && exit 0
echo "Abriendo la app..."
exec "$MIRAME"
