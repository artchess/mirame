"""Rostro y pose de la cabeza con MediaPipe Face Landmarker."""

from __future__ import annotations

import contextlib
import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks.python import BaseOptions, vision

from . import rutas

MODELO_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)


@dataclass
class Pose:
    rostro: bool
    confianza: float = 0.0
    pitch: float | None = None   # positivo = cabeza hacia abajo
    yaw: float | None = None     # positivo = gira a su izquierda (derecha de la imagen)
    roll: float | None = None
    ancho_rostro: int = 0        # píxeles
    x: float | None = None       # caja del rostro, normalizada 0–1
    y: float | None = None
    w: float | None = None
    h: float | None = None
    # Ojos (0–1 los de MediaPipe; apertura = alto/ancho del ojo)
    ojos_abajo: float | None = None   # media de eyeLookDownLeft/Right
    parpado: float | None = None      # media de eyeBlinkLeft/Right (párpado caído)
    apertura: float | None = None


# Puntos del contorno del ojo en la malla de MediaPipe: (arriba, abajo, esquina, esquina)
OJOS = ((159, 145, 33, 133), (386, 374, 362, 263))


def asegurar_modelo(ruta: Path | None = None) -> Path:
    ruta = ruta or rutas.modelos() / "face_landmarker.task"
    if not ruta.exists():
        import urllib.request

        ruta.parent.mkdir(parents=True, exist_ok=True)
        print("Descargando el modelo de MediaPipe (3,6 MB, solo la primera vez)…", flush=True)
        tmp = ruta.with_suffix(".tmp")
        urllib.request.urlretrieve(MODELO_URL, tmp)
        tmp.replace(ruta)
    return ruta


def angulos(matriz: np.ndarray) -> tuple[float, float, float]:
    """Matriz de transformación facial (4x4) → (pitch, yaw, roll) en grados.

    En el modelo canónico de MediaPipe, y apunta hacia arriba y z sale de la cara
    hacia la cámara. Al bajar la cabeza la cara rota alrededor de x y la nariz
    apunta hacia abajo; aquí ese giro sale positivo.
    """
    r = matriz[:3, :3]
    sy = math.hypot(r[0, 0], r[1, 0])
    rx = math.degrees(math.atan2(r[2, 1], r[2, 2]))
    ry = math.degrees(math.atan2(-r[2, 0], sy))
    rz = math.degrees(math.atan2(r[1, 0], r[0, 0]))
    return rx, ry, rz


@contextlib.contextmanager
def _silencio():
    """Silencia stderr a nivel de descriptor (los avisos vienen de C++)."""
    sys.stderr.flush()
    copia = os.dup(2)
    nulo = os.open(os.devnull, os.O_WRONLY)
    os.dup2(nulo, 2)
    try:
        yield
    finally:
        os.dup2(copia, 2)
        os.close(nulo)
        os.close(copia)


class Detector:
    LADO_RECORTE = 512

    def __init__(self, max_rostros: int = 4, confianza_minima: float = 0.4):
        opciones = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(asegurar_modelo())),
            running_mode=vision.RunningMode.IMAGE,  # sin seguimiento entre fotogramas: repetible
            num_faces=max_rostros,
            min_face_detection_confidence=confianza_minima,
            min_face_presence_confidence=confianza_minima,
            output_facial_transformation_matrixes=True,
            output_face_blendshapes=True,
        )
        with _silencio():
            # Crear el modelo y una primera inferencia en vacío: es cuando MediaPipe
            # imprime sus avisos internos en stderr.
            self._lm = vision.FaceLandmarker.create_from_options(opciones)
            vacio = np.zeros((256, 256, 3), np.uint8)
            self._lm.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=vacio))
        self._previa = None

    def cerrar(self):
        self._lm.close()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.cerrar()

    def analizar(self, rgb: np.ndarray) -> Pose:
        """Busca al predicador. En planos lejanos el rostro es demasiado pequeño para el
        detector de MediaPipe, así que se trabaja sobre recortes cuadrados ampliados:
        primero alrededor del rostro del fotograma anterior y, si se pierde, sobre una
        rejilla que cubre todo el cuadro. Todo es secuencial y sin azar: repetible."""
        alto, ancho = rgb.shape[:2]
        candidatos = []
        if self._previa is not None:
            candidatos = self._detectar_en(rgb, self._recorte_alrededor(self._previa, ancho, alto))
        if not candidatos:
            candidatos = self._detectar_en(rgb, (0, 0, ancho, alto))
            for caja in self._rejilla(ancho, alto):
                candidatos += self._detectar_en(rgb, caja)
        if not candidatos:
            self._previa = None
            return Pose(rostro=False)

        mejor = max(candidatos, key=lambda c: _puntaje(c, ancho, alto, self._previa))
        self._previa = mejor["caja_px"]
        x0, y0, w, h = mejor["caja_px"]
        pitch, yaw, roll = angulos(mejor["matriz"])
        return Pose(
            rostro=True,
            confianza=mejor["confianza"],
            pitch=pitch, yaw=yaw, roll=roll,
            ancho_rostro=int(round(w)),
            x=x0 / ancho, y=y0 / alto, w=w / ancho, h=h / alto,
            ojos_abajo=mejor["ojos_abajo"], parpado=mejor["parpado"], apertura=mejor["apertura"],
        )

    def _recorte_alrededor(self, caja, ancho, alto):
        x0, y0, w, h = caja
        lado = min(max(w, h) * 5, alto, ancho)
        lado = max(lado, min(256, alto, ancho))
        cx, cy = x0 + w / 2, y0 + h / 2
        rx = int(round(min(max(cx - lado / 2, 0), ancho - lado)))
        ry = int(round(min(max(cy - lado / 2, 0), alto - lado)))
        return rx, ry, int(round(lado)), int(round(lado))

    @staticmethod
    def _rejilla(ancho, alto):
        lado = max(min(alto, ancho) // 2, 128)
        paso = lado // 2
        xs = list(range(0, max(ancho - lado, 0) + 1, paso))
        ys = list(range(0, max(alto - lado, 0) + 1, paso))
        if xs[-1] != ancho - lado:
            xs.append(ancho - lado)
        if ys[-1] != alto - lado:
            ys.append(alto - lado)
        return [(x, y, lado, lado) for y in ys for x in xs]

    def _detectar_en(self, rgb, caja):
        rx, ry, rw, rh = caja
        recorte = rgb[ry:ry + rh, rx:rx + rw]
        escala = 1.0
        if max(rw, rh) < self.LADO_RECORTE:
            escala = self.LADO_RECORTE / max(rw, rh)
            recorte = cv2.resize(recorte, (int(round(rw * escala)), int(round(rh * escala))),
                                 interpolation=cv2.INTER_CUBIC)
        imagen = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(recorte))
        res = self._lm.detect(imagen)
        salida = []
        for i, puntos in enumerate(res.face_landmarks):
            xs = np.fromiter((p.x for p in puntos), float) * rw + rx
            ys = np.fromiter((p.y for p in puntos), float) * rh + ry
            x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
            bs = {c.category_name: c.score for c in res.face_blendshapes[i]} if res.face_blendshapes else {}
            aperturas = []
            for a, b, c, d in OJOS:
                ancho_ojo = math.hypot(xs[c] - xs[d], ys[c] - ys[d])
                if ancho_ojo > 0:
                    aperturas.append(math.hypot(xs[a] - xs[b], ys[a] - ys[b]) / ancho_ojo)
            salida.append({
                "ojos_abajo": round((bs.get("eyeLookDownLeft", 0) + bs.get("eyeLookDownRight", 0)) / 2, 4) if bs else None,
                "parpado": round((bs.get("eyeBlinkLeft", 0) + bs.get("eyeBlinkRight", 0)) / 2, 4) if bs else None,
                "apertura": round(float(np.mean(aperturas)), 4) if aperturas else None,
                "caja_px": (float(x0), float(y0), float(x1 - x0), float(y1 - y0)),
                "matriz": np.array(res.facial_transformation_matrixes[i]),
                "confianza": _confianza(res, i),
            })
        return salida


def _puntaje(c, ancho, alto, previa):
    """Rostro grande y centrado; si veníamos siguiendo a alguien, preferir al mismo."""
    x0, y0, w, h = c["caja_px"]
    cx, cy = (x0 + w / 2) / ancho, (y0 + h / 2) / alto
    dist = math.hypot(cx - 0.5, cy - 0.5) / math.hypot(0.5, 0.5)
    puntaje = (w * h) / (ancho * alto) * (1 - 0.5 * dist)
    if previa is not None:
        px, py, pw, ph = previa
        d = math.hypot(x0 + w / 2 - (px + pw / 2), y0 + h / 2 - (py + ph / 2))
        if d < max(pw, ph):
            puntaje *= 2
    return puntaje


def _confianza(res, i: int) -> float:
    """Face Landmarker no expone el puntaje del detector; usamos la presencia media
    de los puntos cuando viene, y si no, 1.0 (pasó los umbrales mínimos)."""
    puntos = res.face_landmarks[i]
    pres = [p.presence for p in puntos if getattr(p, "presence", None)]
    if pres:
        return float(np.mean(pres))
    return 1.0
