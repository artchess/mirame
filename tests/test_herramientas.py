"""ffmpeg incluido, lectura de duración y tamaño sin ffprobe, y acceso directo."""

import subprocess
import sys

import pytest

from mirame import herramientas, video

SALIDA_HORIZONTAL = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'video.mp4':
  Duration: 00:56:12.34, start: 0.000000, bitrate: 1200 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 1280x720 [SAR 1:1 DAR 16:9], 1000 kb/s, 25 fps
  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 128 kb/s
"""

SALIDA_CELULAR = """  Duration: 00:00:09.50, start: 0.000000, bitrate: 9000 kb/s
  Stream #0:0[0x1](und): Video: hevc (Main) (hvc1 / 0x31637668), yuv420p(tv), 1920x1080, 8000 kb/s, 30 fps
    Side data:
      displaymatrix: rotation of -90.00 degrees
"""


def test_leer_sondeo_horizontal():
    d = herramientas.leer_sondeo(SALIDA_HORIZONTAL)
    assert d == {"duracion": pytest.approx(3372.34), "ancho": 1280, "alto": 720}


def test_leer_sondeo_girado():
    d = herramientas.leer_sondeo(SALIDA_CELULAR)
    assert (d["ancho"], d["alto"]) == (1080, 1920)
    assert d["duracion"] == pytest.approx(9.5)


def test_ffmpeg_incluido_lee_un_video(tmp_path):
    archivo = tmp_path / "prueba.mp4"
    subprocess.run([herramientas.ffmpeg(), "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
                    "-t", "2", "-c:v", "mpeg4", str(archivo)], check=True)
    assert video.duracion(archivo) == pytest.approx(2.0, abs=0.1)
    assert video.dimensiones(archivo) == (320, 240)
    cuadros = list(video.fotogramas(archivo, 2))
    assert len(cuadros) == 4 and cuadros[0][2].shape == (240, 320, 3)


def test_video_ilegible(tmp_path):
    malo = tmp_path / "malo.mp4"
    malo.write_bytes(b"no es un video")
    with pytest.raises(RuntimeError, match="No pude leer"):
        video.duracion(malo)


def test_ytdlp_encuentra_deno():
    from yt_dlp.utils._jsruntime import DenoJsRuntime

    assert DenoJsRuntime().info is not None, "falta deno: yt-dlp no podrá descargar de YouTube"


@pytest.mark.skipif(sys.platform == "win32", reason="en Windows el acceso es un .lnk")
def test_crear_acceso(tmp_path, monkeypatch):
    monkeypatch.setattr(herramientas.Path, "home", lambda: tmp_path)
    (tmp_path / "Desktop").mkdir()
    destino = herramientas.crear_acceso()
    assert destino.exists() and destino.is_relative_to(tmp_path)
    assert "mirame" in destino.read_text()


def test_video_de_celular_girado(tmp_path):
    """El tamaño leído coincide con los fotogramas que entrega ffmpeg (que los gira)."""
    plano, girado = tmp_path / "h.mp4", tmp_path / "v.mp4"
    ff = herramientas.ffmpeg()
    subprocess.run([ff, "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
                    "-t", "1", "-c:v", "mpeg4", str(plano)], check=True)
    r = subprocess.run([ff, "-v", "error", "-display_rotation", "90", "-i", str(plano), "-c", "copy", str(girado)])
    if r.returncode:
        pytest.skip("este ffmpeg no sabe escribir la rotación")
    assert video.dimensiones(girado) == (240, 320)
    assert next(video.fotogramas(girado, 2))[2].shape == (320, 240, 3)
