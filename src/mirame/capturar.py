"""Capturas PNG 1920×1080 del reporte con Playwright (Chromium sin interfaz).

El video no se reproduce en la captura: se extrae con ffmpeg el fotograma exacto del
momento y el reporte lo muestra como imagen fija. Así la captura es instantánea y no
depende de los códecs del Chromium de Playwright.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd

from .analisis import leer_fotogramas, leer_resumen
from .reporte import generar as generar_reporte
from .video import fotograma_en


def momentos_por_defecto(carpeta: Path) -> list[tuple[str, float, str]]:
    """(nombre, t, modo) de las cuatro capturas por defecto."""
    resumen = leer_resumen(carpeta)
    seg = pd.read_csv(carpeta / "segundos.csv")
    fot = leer_fotogramas(carpeta)
    dur = resumen["video"]["duracion_analizada"]
    base = resumen["parametros"]["pitch_calibracion"]

    # Contacto visual típico: el centro del tramo más largo de segundos en congregación,
    # tomando el fotograma con pitch más cercano a la calibración.
    mejor, actual = (0, 0), None
    for t, c in zip(seg.t, seg.clase, strict=True):
        if c == "congregacion":
            actual = t if actual is None else actual
            if t - actual + 1 > mejor[1]:
                mejor = (actual, t - actual + 1)
        else:
            actual = None
    a, n = mejor
    tramo = fot[(fot.t >= a) & (fot.t < a + n) & (fot.clase == "congregacion")]
    if len(tramo):
        centro = a + n / 2
        tramo = tramo.assign(d=(tramo.pitch - base).abs() + (tramo.t - centro).abs() / max(n, 1))
        t_contacto = float(tramo.sort_values(["d", "t"]).iloc[0].t)
    else:
        t_contacto = dur * 0.25

    mayor = resumen.get("episodio_mas_largo")
    # Un poco dentro del episodio: al principio la cabeza todavía va bajando.
    t_lectura = (mayor["inicio"] + min(1.5, mayor["duracion"] / 3)) if mayor else dur * 0.5

    return [
        ("1-contacto-visual", t_contacto, "momento"),
        ("2-lectura-mas-larga", t_lectura, "momento"),
        ("3-punto-medio", round(dur / 2, 2), "momento"),
        ("4-resumen", round(dur / 2, 2), "resumen"),
    ]


class SinNavegador(RuntimeError):
    """Playwright o su Chromium no están instalados (las capturas son opcionales)."""


INSTALAR = ("Las capturas necesitan Playwright con Chromium. Instálalos una vez con:\n"
            "  uv tool install --force 'mirame[capturas] @ git+https://github.com/jacomv/mirame'\n"
            "  mirame instalar-capturas\n"
            "(desde el código fuente: uv sync --extra capturas && uv run mirame instalar-capturas)")


def disponible() -> bool:
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False
    return True


def capturar(carpeta: Path, momentos: list[tuple[str, float, str]], ancho=1920, alto=1080) -> list[Path]:
    try:
        from playwright.sync_api import Error as ErrorPlaywright
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SinNavegador(INSTALAR) from None

    carpeta = carpeta.resolve()
    reporte = carpeta / "reporte.html"
    if not reporte.exists():
        generar_reporte(carpeta)
    destino = carpeta / "capturas"
    destino.mkdir(exist_ok=True)
    video = carpeta / "video.mp4"
    salidas = []
    with tempfile.TemporaryDirectory(dir=carpeta) as tmp, sync_playwright() as pw:
        try:
            navegador = pw.chromium.launch()
        except ErrorPlaywright as e:
            if "Executable doesn't exist" in str(e) or "playwright install" in str(e):
                raise SinNavegador(INSTALAR) from None
            raise
        pagina = navegador.new_page(viewport={"width": ancho, "height": alto}, device_scale_factor=1)
        for nombre, t, modo in momentos:
            consulta = {"captura": 1, "t": f"{t:.2f}", "modo": modo}
            if modo == "momento":
                jpg = Path(tmp) / f"{nombre}.jpg"
                fotograma_en(video, t, jpg)
                consulta["img"] = f"{Path(tmp).name}/{jpg.name}"
            pagina.goto(f"{reporte.as_uri()}?{urlencode(consulta)}")
            pagina.wait_for_function("window.__listo === true", timeout=20000)
            pagina.wait_for_timeout(100)
            png = destino / f"{nombre}.png"
            pagina.screenshot(path=str(png), full_page=False)
            salidas.append(png)
        navegador.close()
    return salidas


def nombre_en(t: float, modo: str = "momento") -> str:
    base = "resumen" if modo == "resumen" else "momento"
    t = int(round(t))
    return f"{base}-{t // 60:02d}m{t % 60:02d}s"
