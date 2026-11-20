"""Claves y modelos de IA opcionales.

Sin claves, Mírame mide igual la mirada. Con ellas, además transcribe el audio y
separa la lectura bíblica y las oraciones, lo que hace el resultado más preciso.

Dos pasos, cada uno con su proveedor (cualquier API compatible con OpenAI):
- Transcripción (Whisper): Groq por defecto; o p. ej. OpenAI con `whisper-1`.
- Análisis de la transcripción (marcar lecturas): Groq por defecto; o cualquier modelo de chat.

Se guardan en `<carpeta de datos>/configuracion.json` con permisos solo para el
usuario (0600). Las variables de entorno tienen prioridad sobre el archivo.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields

from . import rutas

GROQ_URL = "https://api.groq.com/openai/v1"
WHISPER_POR_DEFECTO = "whisper-large-v3-turbo"
LLM_POR_DEFECTO = "openai/gpt-oss-120b"

# campo → variable de entorno que lo reemplaza
ENTORNO = {
    "groq_clave": "GROQ_API_KEY",
    "whisper_url": "MIRAME_WHISPER_URL",
    "whisper_clave": "MIRAME_WHISPER_KEY",
    "whisper_modelo": "MIRAME_WHISPER_MODELO",
    "llm_url": "MIRAME_LLM_URL",
    "llm_clave": "MIRAME_LLM_KEY",
    "llm_modelo": "MIRAME_LLM_MODELO",
}
SECRETOS = ("groq_clave", "whisper_clave", "llm_clave")


@dataclass
class Configuracion:
    groq_clave: str = ""        # transcripción (Whisper) y, si no hay otro, el modelo de lecturas
    whisper_url: str = ""       # otro servicio de Whisper compatible con OpenAI; vacío = Groq
    whisper_clave: str = ""
    whisper_modelo: str = ""    # vacío = whisper-large-v3-turbo (Groq)
    llm_url: str = ""           # API compatible con OpenAI para marcar lecturas; vacío = Groq
    llm_clave: str = ""
    llm_modelo: str = ""        # vacío = openai/gpt-oss-120b en Groq

    # ---- valores efectivos
    @property
    def whisper(self) -> str:
        return self.whisper_modelo or WHISPER_POR_DEFECTO

    def transcripcion(self) -> tuple[str, str, str] | None:
        """(url, clave, modelo) para transcribir, o None si no hay con qué."""
        if self.whisper_url:
            if not self.whisper_clave or not self.whisper_modelo:
                return None
            return self.whisper_url.rstrip("/"), self.whisper_clave, self.whisper_modelo
        if self.groq_clave:
            return GROQ_URL, self.groq_clave, self.whisper
        return None

    def modelo_lecturas(self) -> tuple[str, str, str] | None:
        """(url, clave, modelo) para marcar lecturas, o None si no hay con qué."""
        if self.llm_url:
            if not self.llm_clave or not self.llm_modelo:
                return None
            return self.llm_url.rstrip("/"), self.llm_clave, self.llm_modelo
        if self.groq_clave:
            return GROQ_URL, self.groq_clave, self.llm_modelo or LLM_POR_DEFECTO
        return None

    @property
    def puede_transcribir(self) -> bool:
        return self.transcripcion() is not None

    @property
    def puede_separar_lecturas(self) -> bool:
        return self.puede_transcribir and self.modelo_lecturas() is not None

    def publica(self) -> dict:
        """Para mostrar en la interfaz: las claves enmascaradas."""
        d = asdict(self)
        for k in SECRETOS:
            d[k] = _enmascarar(d[k])
        d["desde_entorno"] = [k for k, v in ENTORNO.items() if os.environ.get(v)]
        d["puede_transcribir"] = self.puede_transcribir
        d["puede_separar_lecturas"] = self.puede_separar_lecturas
        return d


def _enmascarar(v: str) -> str:
    if not v:
        return ""
    return v[:4] + "…" + v[-4:] if len(v) > 12 else "…"


def _archivo() -> dict:
    ruta = rutas.configuracion()
    if not ruta.exists():
        return {}
    try:
        return json.loads(ruta.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def cargar() -> Configuracion:
    datos = _archivo()
    valores = {}
    for f in fields(Configuracion):
        valores[f.name] = os.environ.get(ENTORNO[f.name], "").strip() or str(datos.get(f.name, "")).strip()
    return Configuracion(**valores)


def guardar(cambios: dict) -> Configuracion:
    """Actualiza solo los campos recibidos. Una clave enmascarada («abcd…wxyz») se
    ignora: significa que el usuario no la cambió."""
    datos = _archivo()
    for f in fields(Configuracion):
        if f.name not in cambios:
            continue
        v = str(cambios[f.name] or "").strip()
        if f.name in SECRETOS and "…" in v:
            continue
        datos[f.name] = v
    ruta = rutas.configuracion()
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps(datos, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(ruta)
    return cargar()
