"""Obtener el video, recortarlo y leer sus fotogramas con ffmpeg."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import rutas
from .herramientas import ffmpeg, sondear
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
        "ffmpeg_location": ffmpeg(),  # para unir video y audio
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


def info(origen: str) -> dict:
    """Título, duración y miniatura sin descargar el video (para elegir el tramo)."""
    if not es_url(origen):
        ruta = Path(origen).expanduser()
        if not ruta.exists():
            raise FileNotFoundError(f"No existe el archivo: {ruta}")
        return {"titulo": ruta.stem, "duracion": duracion(ruta), "youtube_id": None, "miniatura": None, "canal": None}
    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        d = ydl.extract_info(origen, download=False)
    return {
        "titulo": d.get("title") or d.get("id"),
        "duracion": float(d.get("duration") or 0) or None,
        "youtube_id": d.get("id") if d.get("extractor_key") == "Youtube" else None,
        "miniatura": d.get("thumbnail"),
        "canal": d.get("channel") or d.get("uploader"),
        "descargado": (rutas.descargas() / f"{d.get('id')}.mp4").exists(),
    }


def _slug(texto: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", texto).strip("-")[:60] or "video"


def duracion(archivo: Path) -> float:
    return sondear(archivo)["duracion"]


def dimensiones(archivo: Path) -> tuple[int, int]:
    datos = sondear(archivo)
    if datos["ancho"] is None:
        raise RuntimeError(f"{archivo.name} no tiene imagen de video.")
    return datos["ancho"], datos["alto"]


def recortar(archivo: Path, destino: Path, inicio: float | None, fin: float | None,
             progreso: Progreso | None = None) -> None:
    """Corte exacto (recodifica) a H.264 de máximo 720 de alto, con audio AAC."""
    total = (fin if fin is not None else duracion(archivo)) - (inicio or 0)
    cmd = [ffmpeg(), "-v", "error", "-y", "-nostats", "-progress", "pipe:1"]
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
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        for linea in proc.stdout:
            if progreso and linea.startswith("out_time_us=") and total > 0:
                try:
                    hecho = min(int(linea.split("=", 1)[1]) / 1e6 / total, 1.0)
                except ValueError:
                    continue
                progreso.fraccion = hecho
                progreso.mensaje = f"Recortando… {hecho * 100:.0f} %"
                progreso.revisar()
    except BaseException:
        proc.kill()
        raise
    finally:
        proc.wait()
    if proc.returncode:
        raise RuntimeError(f"ffmpeg no pudo recortar el video: {proc.stderr.read()[-400:]}")


def fotogramas(archivo: Path, fps: float):
    """Genera (indice, t, imagen RGB) a `fps` fotogramas por segundo. t = indice / fps."""
    ancho, alto = dimensiones(archivo)
    cmd = [
        ffmpeg(), "-v", "error", "-i", str(archivo),
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
        [ffmpeg(), "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(archivo),
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
