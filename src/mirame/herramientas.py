"""Programas externos y lo que toca el sistema: ffmpeg y el acceso directo del escritorio.

ffmpeg viene incluido (paquete imageio-ffmpeg), así que nadie tiene que instalarlo aparte.
Si la computadora ya tiene uno en el PATH, se usa ese.
"""

from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


@functools.cache
def ffmpeg() -> str:
    """Ruta del ffmpeg: el del sistema si existe; si no, el que trae imageio-ffmpeg."""
    propio = os.environ.get("MIRAME_FFMPEG") or shutil.which("ffmpeg")
    if propio:
        return propio
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


@functools.cache
def ffmpeg_disponible() -> bool:
    try:
        return bool(ffmpeg())
    except Exception:
        return False


_DURACION = re.compile(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)")
_VIDEO = re.compile(r"Stream #.*?Video:.*?[ ,](\d{2,5})x(\d{2,5})[ ,\n]")
_ROTACION = re.compile(r"rotation of (-?\d+(?:\.\d+)?) degrees|rotate\s*:\s*(-?\d+)")


def leer_sondeo(texto: str) -> dict:
    """Duración y tamaño a partir de lo que imprime `ffmpeg -i` (sin ffprobe).

    El tamaño ya viene girado si el video tiene rotación (los de celular en vertical),
    igual que los fotogramas que entrega ffmpeg al decodificar.
    """
    d = _DURACION.search(texto)
    v = _VIDEO.search(texto)
    resultado: dict = {"duracion": None, "ancho": None, "alto": None}
    if d:
        h, m, s = d.groups()
        resultado["duracion"] = int(h) * 3600 + int(m) * 60 + float(s)
    if v:
        ancho, alto = int(v.group(1)), int(v.group(2))
        r = _ROTACION.search(texto[v.start():])
        if r and round(abs(float(r.group(1) or r.group(2)))) % 180 == 90:
            ancho, alto = alto, ancho
        resultado["ancho"], resultado["alto"] = ancho, alto
    return resultado


def sondear(archivo: Path) -> dict:
    proc = subprocess.run([ffmpeg(), "-hide_banner", "-i", str(archivo)],
                          capture_output=True, text=True, errors="replace")
    datos = leer_sondeo(proc.stderr)
    if datos["duracion"] is None:
        raise RuntimeError(f"No pude leer el video {archivo.name}: {proc.stderr.strip()[-300:]}")
    return datos


# ---------------------------------------------------------------- acceso directo
def _ejecutable() -> str:
    """Ruta absoluta del comando `mirame` (la que deja `uv tool install`)."""
    return shutil.which("mirame") or str(Path(sys.argv[0]).absolute())


def crear_acceso() -> Path:
    """Crea en el escritorio (o en el menú de aplicaciones en Linux) un acceso que abre la app."""
    programa = _ejecutable()
    if sys.platform == "darwin":
        destino = Path.home() / "Desktop" / "Mírame.command"
        destino.write_text(
            "#!/bin/sh\n"
            "# Abre Mírame. Para cerrarla, cierra esta ventana.\n"
            "clear\n"
            f'exec "{programa}"\n',
            encoding="utf-8",
        )
        destino.chmod(0o755)
        return destino
    if sys.platform == "win32":
        programa = programa.replace("'", "''")  # comillas dentro de una cadena de PowerShell
        guion = (
            "$e = [Environment]::GetFolderPath('Desktop');"
            "$l = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $e 'Mírame.lnk'));"
            f"$l.TargetPath = '{programa}';"
            "$l.WorkingDirectory = $env:USERPROFILE;"
            "$l.Description = 'Abrir Mírame';"
            "$l.Save();"
            "Write-Output (Join-Path $e 'Mírame.lnk')"
        )
        salida = subprocess.run(["powershell", "-NoProfile", "-Command", guion],
                                capture_output=True, text=True, check=True)
        return Path(salida.stdout.strip())
    destino = Path.home() / ".local" / "share" / "applications" / "mirame.desktop"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Mírame\n"
        "Comment=Hacia dónde mira el predicador\n"
        f'Exec="{programa}"\n'
        "Terminal=true\n"
        "Categories=AudioVideo;Education;\n",
        encoding="utf-8",
    )
    return destino
