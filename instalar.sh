#!/bin/sh
# Instala o actualiza Mírame en macOS y Linux con un solo comando:
#
#   curl -LsSf https://raw.githubusercontent.com/jacomv/mirame/main/instalar.sh | sh
#
# Qué hace: instala uv (si falta), que a su vez trae Python; instala Mírame con su
# ffmpeg y todo lo demás; descarga el navegador de las capturas; deja un acceso directo
# en el escritorio y abre la app. Volver a ejecutarlo actualiza a la última versión.
# No pide contraseña de administrador ni toca nada fuera de tu usuario.
#
# Variables para pruebas: MIRAME_FUENTE (de dónde instalar), MIRAME_SIN_ABRIR (no abrir la app).
set -eu

FUENTE="${MIRAME_FUENTE:-https://github.com/jacomv/mirame/archive/refs/heads/main.zip}"
AYUDA="https://github.com/jacomv/mirame/blob/main/docs/instalar.md#si-algo-sale-mal"

negrita() { printf '\033[1m%s\033[0m\n' "$1"; }
paso() { printf '\n'; negrita "Paso $1 de 4 · $2"; printf '%s\n' "$3"; }

al_salir() {
  codigo=$?
  if [ "$codigo" -ne 0 ]; then
    printf '\n\033[1;31m%s\033[0m\n' "La instalación no terminó."
    echo "Casi siempre es la conexión: vuelve a pegar el mismo comando y continúa donde quedó."
    echo "Si se repite, mira la guía: $AYUDA"
  fi
}
trap al_salir EXIT

echo
negrita "Instalador de Mírame"
echo "Son cuatro pasos. Tarda unos minutos según tu conexión y ocupa cerca de 1 GB."
echo "No cierres esta ventana hasta que veas «Mírame quedó instalada»."

paso 1 "Preparar uv" "uv es el programa que instala Python y Mírame sin tocar el resto de tu computadora."
if command -v uv >/dev/null 2>&1; then
  UV="$(command -v uv)"
  echo "Ya lo tienes."
elif [ -x "$HOME/.local/bin/uv" ]; then
  UV="$HOME/.local/bin/uv"
  echo "Ya lo tienes."
else
  curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
  UV="$HOME/.local/bin/uv"
  echo "Listo."
fi

paso 2 "Instalar Mírame" "Descarga Python, Mírame y lo que necesita para leer el video. Es el paso más largo."
"$UV" tool install --force --refresh --python 3.12 "mirame[capturas] @ $FUENTE"
"$UV" tool update-shell >/dev/null 2>&1 || true
MIRAME="$("$UV" tool dir --bin)/mirame"

paso 3 "Descargar el navegador de las capturas" "Lo usa el botón «Capturar» para guardar imágenes del reporte (unos 200 MB)."
"$MIRAME" instalar-capturas || echo "No se pudo. Las capturas quedan desactivadas; todo lo demás funciona."

paso 4 "Crear el acceso directo" "Para abrir Mírame con doble clic."
"$MIRAME" acceso || echo "No se pudo crear. Puedes abrir Mírame escribiendo «mirame» en una terminal nueva."

VERSION="$("$MIRAME" --version | cut -d' ' -f2)"
printf '\n\033[1;32m%s\033[0m\n' "Mírame $VERSION quedó instalada."
echo
if [ "$(uname)" = "Darwin" ]; then
  echo "  · Para abrirla: doble clic en «Mírame» en el escritorio."
else
  echo "  · Para abrirla: busca «Mírame» en el menú de aplicaciones."
fi
echo "  · Mientras la usas, queda abierta una ventana como esta. Para cerrar Mírame, ciérrala."
echo "  · Para actualizar más adelante: vuelve a pegar el mismo comando."
[ -n "${MIRAME_SIN_ABRIR:-}" ] && exit 0
echo
echo "Abriendo Mírame en tu navegador..."
exec "$MIRAME"
