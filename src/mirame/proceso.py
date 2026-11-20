"""El flujo completo de un análisis, de la URL al reporte.

Lo usan la línea de comandos (`mirame analizar`) y la app web (`mirame app`).
"""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

from . import analisis, config, lecturas, reporte, rutas, video
from .progreso import Cancelado, Cronometro, Progreso
from .video import formato_tiempo


@dataclass
class Opciones:
    origen: str                                   # enlace de YouTube o ruta de un video
    inicio: float | None = None                   # s donde empieza el sermón
    fin: float | None = None                      # s donde termina
    titulo: str | None = None
    fps: float = 4.0
    umbral: float = 15.0
    base: float | None = None
    calibrar: tuple[float, float] | None = None
    excluir: list[tuple[float, float]] = field(default_factory=list)
    ancho_minimo: int = 0
    umbral_ojos: float | None = 0.45              # None = solo la cabeza
    separar_lecturas: bool | None = None          # None = sí, si hay claves configuradas
    salida: Path | None = None                    # carpeta del análisis; por defecto una nueva

    def parametros(self) -> analisis.Parametros:
        return analisis.Parametros(
            fps=self.fps, umbral=self.umbral, base=self.base, calibrar=self.calibrar,
            excluir=list(self.excluir), ancho_minimo=self.ancho_minimo, umbral_ojos=self.umbral_ojos)


def carpeta_nueva(id_video: str) -> Path:
    """analisis/<fecha>_<id>, con sufijo si ya existe."""
    base = f"{date.today().isoformat()}_{re.sub(r'[^A-Za-z0-9_-]+', '-', id_video)[:60]}"
    raiz = rutas.analisis()
    carpeta, n = raiz / base, 2
    while carpeta.exists():
        carpeta, n = raiz / f"{base}-{n}", n + 1
    return carpeta


def analizar(op: Opciones, progreso: Progreso | None = None) -> tuple[Path, dict]:
    """Descarga, recorta, mide la mirada fotograma a fotograma y genera el reporte.
    Si hay claves de IA, además separa la lectura bíblica y la oración."""
    progreso = progreso or Progreso()

    progreso.etapa_nueva("Obteniendo el video")
    fuente = video.obtener(op.origen, progreso)
    carpeta = (op.salida or carpeta_nueva(fuente.id)).expanduser().resolve()
    nueva = not carpeta.exists()
    carpeta.mkdir(parents=True, exist_ok=True)
    _estado(carpeta, "en_proceso", origen=op.origen, titulo=op.titulo or fuente.titulo)
    progreso.carpeta = carpeta
    try:
        return _analizar(op, fuente, carpeta, progreso)
    except Cancelado:
        # Un análisis cancelado a medias no sirve: se borra si la carpeta era nueva.
        if nueva and not (carpeta / "resumen.json").exists():
            shutil.rmtree(carpeta, ignore_errors=True)
        raise


def _analizar(op: Opciones, fuente: video.Fuente, carpeta: Path, progreso: Progreso) -> tuple[Path, dict]:

    progreso.etapa_nueva("Recortando el sermón")
    clip = carpeta / "video.mp4"
    recorte = {"archivo": str(fuente.archivo), "inicio": op.inicio, "fin": op.fin}
    marca = carpeta / ".recorte.json"
    if clip.exists() and marca.exists() and json.loads(marca.read_text()) == recorte:
        progreso.aviso("El video recortado ya existe; se reutiliza")
    else:
        progreso.aviso(f"{formato_tiempo(op.inicio or 0)} → "
                       f"{formato_tiempo(op.fin) if op.fin else 'final'} (H.264, 720p)")
        video.recortar(fuente.archivo, clip, op.inicio, op.fin)
        marca.write_text(json.dumps(recorte))

    progreso.etapa_nueva("Midiendo la mirada")
    df = medir(clip, op.fps, progreso)
    ancho, alto = video.dimensiones(clip)
    info = {
        "origen": fuente.origen, "titulo": op.titulo or fuente.titulo,
        "inicio": op.inicio, "fin": op.fin, "duracion_analizada": round(video.duracion(clip), 2),
        "ancho": ancho, "alto": alto,
    }
    resumen = analisis.guardar(carpeta, df, op.parametros(), info)
    reporte.generar(carpeta)
    _estado(carpeta, "listo")

    separar = op.separar_lecturas
    if separar is None:
        separar = config.cargar().puede_separar_lecturas
    if separar:
        try:
            resumen = separar_lecturas(carpeta, progreso)
        except lecturas.FaltaLlave as e:
            progreso.aviso(f"No se separó la lectura bíblica: {e}")
        except Exception as e:  # noqa: BLE001 — el análisis de la mirada ya quedó guardado
            progreso.aviso(f"No se separó la lectura bíblica: {e}")
    return carpeta, resumen


def medir(clip: Path, fps: float, progreso: Progreso) -> pd.DataFrame:
    """Pose de la cabeza y de los ojos en cada fotograma."""
    from .pose import Detector

    dur = video.duracion(clip)
    total = max(int(dur * fps), 1)
    progreso.aviso(f"{formato_tiempo(dur)} de video, ~{total} fotogramas a {fps:g} por segundo", 0.0)
    filas = []
    reloj = Cronometro()
    with Detector() as det:
        for i, t, img in video.fotogramas(clip, fps):
            p = det.analizar(img)
            filas.append({
                "t": t, "rostro": p.rostro, "confianza": round(p.confianza, 3),
                "pitch": p.pitch, "yaw": p.yaw, "roll": p.roll, "ancho_rostro": p.ancho_rostro,
                "x": p.x, "y": p.y, "w": p.w, "h": p.h,
                "ojos_abajo": p.ojos_abajo, "parpado": p.parpado, "apertura": p.apertura,
            })
            if i % max(1, total // 100) == 0:
                hecho = min(i / total, 1.0)
                progreso.aviso(f"{formato_tiempo(t)} de {formato_tiempo(dur)} · faltan "
                               f"~{formato_tiempo(reloj.restante(hecho))}", hecho)
    df = pd.DataFrame(filas)
    # Redondeo antes de clasificar: lo guardado en el CSV es exactamente lo que se clasificó.
    for c in ("pitch", "yaw", "roll", "x", "y", "w", "h"):
        df[c] = df[c].astype(float).round(3 if c in "xywh" else 2)
    for c in ("ojos_abajo", "parpado", "apertura"):
        df[c] = df[c].astype(float).round(3)
    # Puntaje de ojos bajados: mirada hacia abajo + párpado caído (0–1).
    df["ojos"] = ((df.ojos_abajo + df.parpado) / 2).round(3)
    return df


def separar_lecturas(carpeta: Path, progreso: Progreso | None = None, retranscribir: bool = False,
                     solo_recalcular: bool = False) -> dict:
    """Transcribe (si hace falta), marca lectura bíblica y oración, y recalcula."""
    progreso = progreso or Progreso()
    if not solo_recalcular:
        if retranscribir or not (carpeta / "transcripcion.json").exists():
            progreso.etapa_nueva("Transcribiendo el audio")
            lecturas.transcribir(carpeta, progreso)
        progreso.etapa_nueva("Marcando lectura bíblica y oración")
        lecturas.marcar_lecturas(carpeta, progreso)
    return recalcular(carpeta)


def recalcular(carpeta: Path, cambios: dict | None = None) -> dict:
    """Reclasifica desde fotogramas.csv (sin tocar el video) y regenera el reporte."""
    resumen = analisis.leer_resumen(carpeta)
    p = analisis.parametros_de(resumen)
    for k, v in (cambios or {}).items():
        setattr(p, k, v)
    nuevo = analisis.guardar(carpeta, analisis.leer_fotogramas(carpeta), p, resumen["video"])
    reporte.generar(carpeta)
    _estado(carpeta, "listo")
    return nuevo


def _estado(carpeta: Path, estado: str, **extra) -> None:
    """estado.json: lo que la biblioteca necesita saber aunque el análisis no haya terminado."""
    ruta = carpeta / "estado.json"
    datos = json.loads(ruta.read_text()) if ruta.exists() else {}
    datos.update(extra, estado=estado)
    datos.setdefault("creado", date.today().isoformat())
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=1) + "\n")
