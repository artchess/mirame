"""Obtener el video, recortarlo y leer sus fotogramas con ffmpeg."""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import rutas
from .progreso import Progreso

YOUTUBE_RE = re.compile(r"(youtube\.com|youtu\.be)", re.I)


@dataclass
class Fuente:
    origen: str          # URL o ruta tal como la dio el usuario
    archivo: Path        # mp4 completo en disco
    id: str              # id de YouTube o nombre del archivo
    titulo: str


def es_url(texto: str) -> bool:
    return texto.startswith("http") or bool(YOUTUBE_RE.search(texto))


def obtener(origen: str, progreso: Progreso | None = None) -> Fuente:
    """Descarga de YouTube a 720p (con caché en la carpeta de descargas) o toma un archivo local."""
    progreso = progreso or Progreso()
    if not es_url(origen):
        ruta = Path(origen).expanduser().resolve()
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo: {ruta}")
        return Fuente(origen=str(ruta), archivo=ruta, id=_slug(ruta.stem), titulo=ruta.stem)

    import yt_dlp

    descargas = rutas.descargas()

    def gancho(d):
        progreso.revisar()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            if total:
                hecho = d.get("downloaded_bytes", 0) / total
                progreso.fraccion = hecho
                progreso.mensaje = f"Descargando… {hecho * 100:.0f} %"

    opciones = {
        # H.264 primero: lo reproduce cualquier navegador y Chromium sin códecs propietarios.
        "format": "bv*[height<=720][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b",
        "merge_output_format": "mp4",
        "outtmpl": str(descargas / "%(id)s.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "progress_hooks": [gancho],
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        info = ydl.extract_info(origen, download=False)
        destino = descargas / f"{info['id']}.mp4"
        if not destino.exists():
            progreso.aviso(f"Descargando «{info.get('title')}»")
            ydl.download([origen])
        else:
            progreso.aviso("Usando la descarga guardada")
    return Fuente(origen=origen, archivo=destino, id=info["id"], titulo=info.get("title") or info["id"])


def _slug(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", texto).strip("-")[:60] or "video"


def duracion(archivo: Path) -> float:
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(archivo)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(salida)["format"]["duration"])


def dimensiones(archivo: Path) -> tuple[int, int]:
    salida = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "json", str(archivo)],
        capture_output=True, text=True, check=True,
    ).stdout
    s = json.loads(salida)["streams"][0]
    return int(s["width"]), int(s["height"])


def recortar(archivo: Path, destino: Path, inicio: float | None, fin: float | None) -> None:
    """Corte exacto (recodifica) a H.264 de máximo 720 de alto, con audio AAC."""
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if inicio:
        cmd += ["-ss", f"{inicio:.3f}"]
    cmd += ["-i", str(archivo)]
    if fin is not None:
        cmd += ["-t", f"{fin - (inicio or 0):.3f}"]
    cmd += [
        "-vf", "scale=-2:'min(720,ih)'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-g", "50",  # keyframes frecuentes: saltos rápidos en el reporte
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        str(destino),
    ]
    subprocess.run(cmd, check=True)


def fotogramas(archivo: Path, fps: float):
    """Genera (indice, t, imagen RGB) a `fps` fotogramas por segundo. t = indice / fps."""
    ancho, alto = dimensiones(archivo)
    cmd = [
        "ffmpeg", "-v", "error", "-i", str(archivo),
        "-vf", f"fps={fps}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ]
    tam = ancho * alto * 3
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=tam * 4)
    try:
        i = 0
        while True:
            datos = proc.stdout.read(tam)
            if len(datos) < tam:
                break
            img = np.frombuffer(datos, np.uint8).reshape(alto, ancho, 3)
            yield i, round(i / fps, 3), img
            i += 1
    finally:
        proc.stdout.close()
        proc.wait()


def fotograma_en(archivo: Path, t: float, destino: Path) -> None:
    """Guarda como JPEG el fotograma del segundo t (corte exacto)."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(archivo),
         "-frames:v", "1", "-q:v", "2", str(destino)],
        check=True,
    )


def leer_tiempo(texto: str | None) -> float | None:
    """'mm:ss', 'hh:mm:ss' o segundos → segundos."""
    if texto is None:
        return None
    partes = [float(p) for p in texto.strip().split(":")]
    total = 0.0
    for p in partes:
        total = total * 60 + p
    return total


def formato_tiempo(seg: float) -> str:
    seg = int(round(seg))
    h, resto = divmod(seg, 3600)
    m, s = divmod(resto, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
