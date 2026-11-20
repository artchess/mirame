"""Fotogramas al azar de cada clase, con el pitch dibujado, para revisar a ojo."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .analisis import ABAJO, CONGREGACION, SIN_DATO, leer_fotogramas, leer_resumen
from .video import formato_tiempo, fotograma_en

COLORES = {CONGREGACION: (74, 163, 22), ABAJO: (11, 158, 245), SIN_DATO: (150, 150, 150)}  # BGR
TAM = 360


def generar(carpeta: Path, n: int = 20, semilla: int = 7) -> Path:
    df = leer_fotogramas(carpeta)
    resumen = leer_resumen(carpeta)
    base = resumen["parametros"]["pitch_calibracion"]
    umbral = resumen["parametros"]["umbral"]
    video = carpeta / "video.mp4"
    destino = carpeta / "muestras"
    if destino.exists():
        shutil.rmtree(destino)
    rng = np.random.default_rng(semilla)

    with tempfile.TemporaryDirectory() as tmp:
        for clase in (CONGREGACION, ABAJO, SIN_DATO):
            filas = df[df.clase == clase]
            if not len(filas):
                continue
            elegidas = filas.iloc[np.sort(rng.choice(len(filas), min(n, len(filas)), replace=False))]
            (destino / clase).mkdir(parents=True, exist_ok=True)
            mosaico = []
            for _, f in elegidas.iterrows():
                jpg = Path(tmp) / "f.jpg"
                fotograma_en(video, f.t, jpg)
                img = cv2.imread(str(jpg))
                tarjeta = _tarjeta(img, f, clase, base, umbral)
                cv2.imwrite(str(destino / clase / f"t{f.t:08.2f}.jpg"), tarjeta)
                mosaico.append(tarjeta)
            cv2.imwrite(str(destino / f"{clase}.jpg"), _mosaico(mosaico))
    return destino


def _tarjeta(img, f, clase, base, umbral):
    alto, ancho = img.shape[:2]
    color = COLORES[clase]
    if f.rostro:
        x, y, w, h = f.x * ancho, f.y * alto, f.w * ancho, f.h * alto
        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), color, 2)
        # Zoom alrededor del rostro: en planos lejanos la cabeza mide pocos píxeles.
        lado = int(min(max(w, h) * 4, alto))
        cx, cy = x + w / 2, y + h / 2
        x0 = int(min(max(cx - lado / 2, 0), ancho - lado))
        y0 = int(min(max(cy - lado / 2, 0), alto - lado))
        vista = img[y0:y0 + lado, x0:x0 + lado]
    else:
        lado = min(alto, ancho)
        x0 = (ancho - lado) // 2
        vista = img[:, x0:x0 + lado]
    vista = cv2.resize(vista, (TAM, TAM), interpolation=cv2.INTER_AREA)
    barra = np.full((64, TAM, 3), 255, np.uint8)
    cv2.rectangle(barra, (0, 0), (8, 64), color, -1)
    texto1 = f"{formato_tiempo(f.t)}  ({f.t:.2f} s)  {clase}"
    ojos = f"  ojos {f.ojos:.2f}" if "ojos" in f and f.ojos == f.ojos else ""
    texto2 = (f"cabeza {f.pitch - base:+.0f} (>{umbral:.0f}){ojos}" if f.rostro else "sin rostro")
    cv2.putText(barra, texto1, (16, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 30, 30), 1, cv2.LINE_AA)
    cv2.putText(barra, texto2, (16, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)
    return np.vstack([vista, barra])


def _mosaico(tarjetas, columnas=5):
    filas = []
    for i in range(0, len(tarjetas), columnas):
        fila = tarjetas[i:i + columnas]
        while len(fila) < columnas:
            fila.append(np.full_like(tarjetas[0], 255))
        filas.append(np.hstack(fila))
    return np.vstack(filas)
