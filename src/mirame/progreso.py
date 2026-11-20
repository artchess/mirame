"""Avance de una tarea larga: lo mismo para la terminal que para la app web."""

from __future__ import annotations

import threading
import time


class Cancelado(Exception):
    """El usuario detuvo la tarea."""


class Progreso:
    """Por defecto imprime en la terminal. La app web usa una subclase que guarda el
    estado para mostrarlo en la página."""

    def __init__(self):
        self._cancelar = threading.Event()
        self.etapa = ""
        self.fraccion: float | None = None
        self.mensaje = ""
        self.carpeta = None   # carpeta del análisis, en cuanto se conoce

    def etapa_nueva(self, nombre: str) -> None:
        self.etapa, self.fraccion, self.mensaje = nombre, None, ""
        self._mostrar(nombre)

    def aviso(self, mensaje: str, fraccion: float | None = None) -> None:
        self.mensaje, self.fraccion = mensaje, fraccion
        self._mostrar(f"  {mensaje}")
        self.revisar()

    def _mostrar(self, texto: str) -> None:
        print(texto, flush=True)

    # ---- cancelación
    def cancelar(self) -> None:
        self._cancelar.set()

    @property
    def cancelado(self) -> bool:
        return self._cancelar.is_set()

    def revisar(self) -> None:
        if self._cancelar.is_set():
            raise Cancelado()


class Cronometro:
    """Estimación de tiempo restante para bucles largos."""

    def __init__(self):
        self.t0 = time.time()

    def restante(self, hecho: float) -> float:
        if hecho <= 0:
            return 0.0
        return (time.time() - self.t0) / hecho * (1 - hecho)
