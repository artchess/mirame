# Cambios

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
