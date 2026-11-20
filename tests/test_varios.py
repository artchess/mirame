import json
import os
import stat

import pytest

from mirame import biblioteca, config, lecturas, rutas
from mirame.video import es_url, formato_tiempo, leer_tiempo


@pytest.mark.parametrize("texto, seg", [("90", 90), ("1:30", 90), ("1:02:03", 3723), (None, None)])
def test_leer_tiempo(texto, seg):
    assert leer_tiempo(texto) == seg


def test_formato_tiempo():
    assert formato_tiempo(59.6) == "1:00"
    assert formato_tiempo(3723) == "1:02:03"


def test_es_url():
    assert es_url("https://youtu.be/abc")
    assert es_url("youtube.com/watch?v=abc")
    assert not es_url("/videos/sermon.mp4")


# ---------------------------------------------------------------- configuración
def test_sin_claves_no_separa_lecturas():
    c = config.cargar()
    assert not c.puede_transcribir and not c.puede_separar_lecturas
    assert c.modelo_lecturas() is None


def test_guardar_claves_con_permisos_privados():
    c = config.guardar({"groq_clave": "gsk_1234567890abcdef"})
    assert c.puede_separar_lecturas
    assert c.modelo_lecturas() == (config.GROQ_URL, "gsk_1234567890abcdef", config.LLM_POR_DEFECTO)
    ruta = rutas.configuracion()
    if os.name == "posix":
        assert stat.S_IMODE(ruta.stat().st_mode) == 0o600
    pub = c.publica()
    assert "1234567890" not in pub["groq_clave"]


def test_clave_enmascarada_no_reemplaza_la_guardada():
    config.guardar({"groq_clave": "gsk_1234567890abcdef"})
    c = config.guardar({"groq_clave": "gsk_…cdef"})
    assert c.groq_clave == "gsk_1234567890abcdef"


def test_otro_proveedor_requiere_url_clave_y_modelo():
    c = config.guardar({"groq_clave": "g" * 20, "llm_url": "https://x/v1/", "llm_clave": "k"})
    assert c.modelo_lecturas() is None
    c = config.guardar({"llm_modelo": "m"})
    assert c.modelo_lecturas() == ("https://x/v1", "k", "m")


def test_el_entorno_tiene_prioridad(monkeypatch):
    config.guardar({"groq_clave": "del-archivo-123456"})
    monkeypatch.setenv("GROQ_API_KEY", "del-entorno-123456")
    c = config.cargar()
    assert c.groq_clave == "del-entorno-123456"
    assert "groq_clave" in c.publica()["desde_entorno"]


# ---------------------------------------------------------------- transcripción
def test_partir_frases_largas_por_palabra():
    seg = [{"start": 0.0, "end": 20.0, "text": "Así todo Israel será salvo. Esto describe un misterio"}]
    palabras = [{"start": i * 0.5, "end": i * 0.5 + 0.4, "word": w} for i, w in
                enumerate(["Así", "todo", "Israel", "será", "salvo."])]
    palabras += [{"start": 10 + i * 0.5, "end": 10.4 + i * 0.5, "word": w} for i, w in
                 enumerate(["Esto", "describe", "un", "misterio"])]
    frases = lecturas._partir(seg, palabras, desfase=100)
    assert [f["texto"] for f in frases] == ["Así todo Israel será salvo.", "Esto describe un misterio"]
    assert frases[0]["inicio"] == 100.0 and frases[1]["inicio"] == 110.0


def test_unir_lecturas_cercanas():
    frases = [{"inicio": 0, "fin": 4, "texto": "a"}, {"inicio": 5, "fin": 9, "texto": "b"},
              {"inicio": 30, "fin": 33, "texto": "c"}]
    tramos = lecturas._unir_lecturas(frases, {0: "Ro 11:25", 1: "Ro 11:26", 2: ""}, unir=3)
    assert [(t["inicio"], t["fin"]) for t in tramos] == [(0, 9), (30, 33)]
    assert tramos[0]["referencia"] == "Ro 11:25; Ro 11:26"


def test_transcribir_sin_clave_avisa(tmp_path):
    with pytest.raises(lecturas.FaltaLlave):
        lecturas.transcribir(tmp_path)


# ---------------------------------------------------------------- biblioteca
def _analisis_falso(nombre, pct=60.0):
    c = rutas.analisis() / nombre
    c.mkdir()
    (c / "resumen.json").write_text(json.dumps({
        "video": {"titulo": f"Sermón {nombre}", "duracion_analizada": 60},
        "pct_congregacion": pct, "pct_abajo": 100 - pct}))
    return c


def test_listar_y_borrar():
    _analisis_falso("2026-01-01_a")
    _analisis_falso("2026-02-01_b", 70)
    fichas = biblioteca.listar()
    assert [f["id"] for f in fichas] == ["2026-02-01_b", "2026-01-01_a"]
    assert fichas[0]["pct_congregacion"] == 70 and fichas[0]["estado"] == "listo"
    biblioteca.borrar("2026-01-01_a")
    assert [f["id"] for f in biblioteca.listar()] == ["2026-02-01_b"]


@pytest.mark.parametrize("malo", ["..", "../x", "a/b", "", ".oculto", "x" * 200])
def test_carpeta_de_rechaza_rutas_raras(malo):
    with pytest.raises(biblioteca.NoExiste):
        biblioteca.carpeta_de(malo)


def test_analisis_sin_resumen_es_incompleto():
    (rutas.analisis() / "2026-03-01_c").mkdir()
    assert biblioteca.listar()[0]["estado"] == "incompleto"


# ---------------------------------------------------------------- 0.4.0
def test_whisper_de_otro_proveedor():
    from mirame import config
    c = config.guardar({"whisper_url": "https://api.openai.com/v1/", "whisper_clave": "sk-x", "whisper_modelo": "whisper-1"})
    assert c.transcripcion() == ("https://api.openai.com/v1", "sk-x", "whisper-1")
    assert c.puede_transcribir and not c.puede_separar_lecturas      # falta el modelo de análisis
    c = config.guardar({"llm_url": "https://x/v1", "llm_clave": "k", "llm_modelo": "m"})
    assert c.puede_separar_lecturas


def test_advertencias_antes_de_procesar():
    from mirame import proceso
    assert any("dura 1:32:00" in a for a in proceso.advertencias(92 * 60, None, None))
    assert proceso.advertencias(92 * 60, 10 * 60, 50 * 60) == []
    assert any("menos de 5 minutos" in a for a in proceso.advertencias(3600, 60, 180))


def test_estimacion_crece_con_el_video_y_las_lecturas():
    from mirame import proceso
    corto, largo = proceso.estimar(600), proceso.estimar(3600)
    assert 0 < corto["segundos"] < largo["segundos"]
    assert proceso.estimar(3600, lecturas=True)["segundos"] > largo["segundos"]


def test_avance_general_pondera_las_etapas():
    from mirame.progreso import Progreso

    class Mudo(Progreso):
        def _mostrar(self, texto):
            pass

    p = Mudo()
    p.plan = ["Obteniendo el video", "Recortando el sermón", "Midiendo la mirada"]
    p.etapa_nueva("Obteniendo el video")
    p.etapa_nueva("Recortando el sermón")
    p.etapa_nueva("Midiendo la mirada")
    p.fraccion = 0.5
    assert 0.55 < p.general() < 0.65      # 20 de 85 hechos + la mitad de 65
