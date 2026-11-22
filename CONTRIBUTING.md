# Contribuir a Mírame

Gracias por querer mejorarlo. Las contribuciones se reciben como *pull requests* en GitHub; para cambios grandes, abre primero un *issue* y conversemos el enfoque.

## Preparar el entorno

```bash
git clone https://github.com/jacomv/mirame && cd mirame
uv sync --extra capturas
uv run mirame instalar-capturas
```

Para no mezclar tus pruebas con tus análisis reales, usa otra carpeta de datos:

```bash
MIRAME_DATOS=/tmp/mirame-dev uv run mirame
```

## Antes de enviar un cambio

```bash
uv run pytest                  # todas las pruebas deben pasar
uv run ruff check src tests    # sin avisos
```

Si cambias el método de medición, explica en el PR cómo cambian los números en al menos un sermón real y actualiza `docs/como-funciona.md`.

## Cómo está organizado el código

```
src/mirame/
├── cli.py          comandos de terminal (`mirame …`)
├── proceso.py      el flujo completo: video → mirada → reporte → lecturas
├── video.py        descargar (yt-dlp), recortar y leer fotogramas (ffmpeg)
├── pose.py         rostro, pose de la cabeza y ojos con MediaPipe
├── analisis.py     calibrar, clasificar, episodios, miradas y resumen
├── lecturas.py     transcripción y marcas de lectura bíblica y oración
├── estructura.py   estructura y contenido del sermón sobre la transcripción
├── reporte.py      arma el reporte HTML autocontenido
├── capturar.py     capturas PNG con Playwright
├── muestras.py     fotogramas de muestra para revisar a ojo
├── biblioteca.py   listar y borrar análisis guardados
├── config.py       claves de IA (archivo y variables de entorno)
├── rutas.py        carpeta de datos (~/Mirame)
├── progreso.py     avance y cancelación de tareas largas
├── web/            la app local: servidor (stdlib), cola de trabajos y página
└── assets/
    ├── reporte/    plantilla, CSS y JS del reporte
    └── vendor/     Chart.js
```

Algunas decisiones que conviene respetar:

- **Sin dependencias para la web.** El servidor usa `http.server` y la página es HTML, CSS y JS sin compilación. Así la instalación sigue siendo un solo comando.
- **El reporte es un solo archivo.** `reporte.py` incrusta CSS, JS, Chart.js y los datos, para que se abra sin conexión y se pueda enviar tal cual.
- **Todo se recalcula desde `fotogramas.csv`.** Lo caro (la pose) se guarda; la clasificación se puede repetir con otros umbrales.
- **Repetible.** Nada de azar en la medición: el mismo video con los mismos parámetros debe dar los mismos números.
- **Las claves nunca se escriben fuera de `configuracion.json`**, y ese archivo tiene permisos 0600.
- **Código y textos en español.** Nombres de funciones y variables incluidos.

## Atribución

Mírame se publica con licencia MIT. Si distribuyes una versión modificada, conserva el aviso de copyright de Jacobis Aldana y el archivo `LICENSE`.
