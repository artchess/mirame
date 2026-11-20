"""Dónde guarda Mírame sus datos.

Todo lo que produce la herramienta (videos descargados, análisis, el modelo de
MediaPipe y la configuración) vive en una sola carpeta de datos, fuera del código:

- `MIRAME_DATOS` si está definida;
- si no, `~/Mirame`.
"""

from __future__ import annotations

import os
from pathlib import Path


def datos() -> Path:
    ruta = os.environ.get("MIRAME_DATOS", "").strip()
    base = Path(ruta).expanduser() if ruta else Path.home() / "Mirame"
    base.mkdir(parents=True, exist_ok=True)
    return base.resolve()


def _sub(nombre: str) -> Path:
    ruta = datos() / nombre
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def analisis() -> Path:
    """Una subcarpeta por análisis."""
    return _sub("analisis")


def descargas() -> Path:
    """Caché de videos completos descargados de YouTube."""
    return _sub("descargas")


def modelos() -> Path:
    """Modelo de MediaPipe (se descarga la primera vez)."""
    return _sub("modelos")


def configuracion() -> Path:
    return datos() / "configuracion.json"
