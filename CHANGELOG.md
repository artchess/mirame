# Cambios

## Sin publicar

- **Estructura del sermón** con IA (opcional): pestaña «Sermón» en el reporte con las partes y sus transiciones, si la estructura es clara, si se anunciaron los puntos y si la introducción va acorde con el argumento, el argumento y el clímax, la conexión con el evangelio, las aplicaciones y los pasajes citados. Cada cosa con su minuto, y un clic lleva el video ahí. Comando `mirame estructura`, botón «Analizar estructura» en la Biblioteca y casilla en «Nuevo análisis». Guarda `estructura.json` y `estructura.md`.
- **Clave de OpenAI** como alternativa o complemento a la de Groq: transcribe con `whisper-1` y analiza el texto con los modelos de OpenAI.
- La transcripción detecta cuando Whisper se queda repitiendo una frase o unas palabras sobre silencio o música, vuelve a pedir solo esa parte en pedazos más cortos y descarta las frases inventadas.
- Lecturas y oración: instrucciones más estrictas sobre qué es una oración, y un aviso en el reporte si más del 15 % del sermón quedó excluido por estar marcado como oración.
- «Anunció sus puntos» muestra cada anuncio con su minuto y sus palabras, y distingue los puntos del sermón de una lista dentro de un punto, que ya no cuenta como anunciar los puntos.
- **Qué API usar** (Ajustes, campo `api` de la configuración o `MIRAME_API`): «Solo OpenAI» o «Solo Groq» hacen la transcripción y el análisis con esa API aunque haya otras claves. Sin elegir, sigue lo automático: Groq transcribe y OpenAI analiza. Ajustes muestra quién hace cada paso.
- Con Groq, las consultas al modelo de lenguaje piden una respuesta más larga (hasta 16 000 tokens). Antes Groq la cortaba en unos 3000, razonamiento incluido, y la estructura del sermón fallaba con un error 400 (`json_validate_failed`).
- Documentación: costos de ejemplo de un sermón con OpenAI y con Groq (`docs/costos-openai.md`, `docs/costos-groq.md`).
- `mirame recalcular`: `--ojos-seguidos` (filtra parpadeos) y `--zona-ojos` / `--ojos-arriba` (cabeza apenas inclinada con los ojos arriba cuenta como congregación).

## 0.3.0

- **App local** en el navegador (`mirame`): nuevo análisis desde un enlace de YouTube o un video de la computadora, biblioteca de análisis (abrir, separar lecturas, borrar) y ajustes para las claves de IA, con avance en vivo y cancelación.
- **Lectura bíblica y oración** con IA (opcional): transcripción con Whisper en Groq y marcas con cualquier modelo compatible con OpenAI. La lectura bíblica se separa de la lectura de notas y la oración se excluye del cálculo.
- **Miradas a la congregación:** duración media, mediana y la más larga.
- Reporte rediseñado: cabe en una pantalla sin scroll, con el video como protagonista.
- Los datos pasan a `~/Mirame` (configurable con `MIRAME_DATOS`), fuera del código.
- Comandos nuevos: `lista`, `borrar`, `lecturas`, `instalar-capturas`. Las capturas pasan a ser una instalación opcional (`mirame[capturas]`).
- Pruebas automáticas, licencia MIT, documentación del método.

## 0.2.0

- Detecta la lectura con los ojos (blendshapes de MediaPipe), no solo con la inclinación de la cabeza.

## 0.1.0

- Primera versión: análisis por línea de comandos, reporte HTML y capturas.
