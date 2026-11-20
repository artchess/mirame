# Cómo funciona Mírame

Este documento explica qué mide la herramienta, con qué reglas y dónde puede equivocarse. Sirve para interpretar los números y para quien quiera mejorar el método.

## 1. Del video a los fotogramas

- Un enlace de YouTube se descarga con [yt-dlp](https://github.com/yt-dlp/yt-dlp) a 720p como máximo, en H.264, y queda en caché en `~/Mirame/descargas/`.
- `ffmpeg` recorta el tramo del sermón (`--inicio`, `--fin`) con corte exacto y lo guarda como `video.mp4` en la carpeta del análisis. Los tiempos del análisis empiezan en 0 en ese recorte.
- Del recorte se leen **4 fotogramas por segundo** (`--fps`). En un sermón de Romanos 11, analizar a 12,5 fotogramas por segundo dio el 93 % de los segundos con la misma clase y unos 3 puntos más de «abajo». Tardó unas cinco veces más. Para comparar sermones entre sí, lo importante es usar la misma velocidad en todos.

## 2. Encontrar el rostro

[MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker) entrega 478 puntos de la cara, una matriz de pose de la cabeza y 52 «blendshapes» (gestos como ojos hacia abajo o párpado cerrado).

En muchas transmisiones la cámara está lejos y la cara mide unos 80 píxeles, demasiado poco para el detector sobre el cuadro completo. Por eso la búsqueda se hace sobre recortes ampliados a 512 px: primero alrededor de donde estaba la cara en el fotograma anterior y, si se perdió, sobre una rejilla que cubre el cuadro. Si aparecen varias caras, gana la más grande y centrada, y se prefiere la misma persona del fotograma anterior.

Todo corre en modo imagen, sin seguimiento entre fotogramas ni azar: el mismo video con los mismos parámetros da los mismos números.

## 3. Hacia dónde mira

De la matriz de pose sale el **pitch**, la inclinación de la cabeza hacia arriba o abajo (positivo = abajo). De los blendshapes sale un **puntaje de ojos** entre 0 y 1: el promedio de «mirada hacia abajo» y «párpado caído».

Cada predicador tiene su postura. Mírame toma como «mirando a la congregación» la **mediana del pitch** del sermón y clasifica cada fotograma así:

| Clase | Regla |
|---|---|
| **abajo** | cabeza más de 15° por debajo de la postura habitual (`--umbral`), **o** puntaje de ojos ≥ 0,45 (`--umbral-ojos`) |
| **congregación** | hay rostro y no cumple lo anterior |
| **sin dato** | no se encontró el rostro (otra toma, plano lejano, diapositivas) |
| **excluido** | tramos que se piden dejar fuera (`--excluir`) y las oraciones marcadas por la IA |

Los ojos importan: hay predicadores que leen el manuscrito casi sin mover la cabeza. En un sermón, el método que solo miraba la cabeza dio 0,7 % abajo; con los ojos, 50 %, y a simple vista el predicador leía buena parte del tiempo.

Si la postura habitual no es la mediana (por ejemplo, un sermón leído casi entero), se puede fijar a mano con `--base` o calcular desde un tramo con `--calibrar mm:ss-mm:ss`.

## 4. Por segundo, episodios y miradas

- **Por segundo:** cada segundo toma la clase mayoritaria de sus fotogramas. Los porcentajes se calculan sobre los segundos con rostro visible.
- **Episodio de lectura:** una racha de fotogramas «abajo» de 1 segundo o más. Las de menos de 1 segundo se cuentan aparte como **vistazos** e incluyen parpadeos.
- **Mirada a la congregación:** el tiempo seguido mirando a la gente. Se corta solo cuando el predicador baja a sus notas 1 segundo o más, o cuando el rostro se pierde 1 segundo o más; los parpadeos y vistazos cortos no la cortan. El reporte da la media, la mediana y la más larga. La media sube por unas pocas miradas muy largas, así que la mediana describe mejor la mirada típica.

## 5. Lectura bíblica y oración (opcional)

Con una clave de IA:

1. El audio del recorte se envía a Whisper (`whisper-large-v3-turbo` en Groq) en tramos de 20 minutos. Vuelve con el tiempo de cada frase y de cada palabra.
2. Whisper a veces junta en una sola frase de 25 segundos el final de una lectura y el comentario que sigue. Por eso las frases largas se parten en pedazos de 8 segundos como máximo, usando el tiempo de cada palabra.
3. Un modelo de lenguaje recibe la transcripción en ventanas de 8 minutos y marca qué frases son **texto bíblico leído** (en cualquier versión) y cuáles son **oración**. No cuentan el anuncio («abramos en Romanos 11»), la paráfrasis ni el comentario.
4. Los segundos «abajo» dentro de una lectura pasan a **Biblia**. Las oraciones se excluyen del cálculo porque los ojos cerrados se ven igual que mirar abajo.

Se compara con un modelo de lenguaje y no con el texto bíblico literal porque los predicadores citan de varias versiones. Las marcas quedan en `lecturas.json`: si algo salió mal, se corrige a mano y se aplica con `mirame lecturas <análisis> --solo-recalcular`. El modelo no responde siempre igual: entre dos corridas pueden cambiar uno o dos tramos y las cifras unas décimas.

## 6. Límites conocidos

- **Parpadeos largos y ojos entrecerrados** pueden contarse como mirar abajo. El umbral de ojos (0,45) se eligió revisando muestras a ojo, no con un etiquetado sistemático.
- **Sin rostro, sin medida.** Si la transmisión muestra la congregación, diapositivas o el texto en pantalla, esos segundos quedan «sin dato». Pasado el 30 %, el reporte avisa que el resultado es poco confiable.
- **Mirar abajo no siempre es leer.** Bajar la vista para pensar, mirar a la primera fila o a un niño cuenta igual. La herramienta mide la dirección de la mirada, no la intención.
- **La cámara cuenta.** Una cámara muy alta o muy baja cambia el ángulo aparente. Como la referencia es la postura habitual de cada sermón, comparar sermones grabados con cámaras distintas es razonable; comparar la cifra exacta con otra herramienta, no.
- **Falta validar contra un etiquetado humano.** El comando `mirame validar` compara el resultado con un CSV etiquetado a mano (`t,clase` por segundo, o `inicio,fin,clase` por tramos; clase `c`, `a` o `s`). El objetivo es al menos 90 % de coincidencia. Si haces esa validación con tus sermones, compartir el resultado ayuda a todos.

## 7. Qué hay en cada archivo

| Archivo | Contenido |
|---|---|
| `fotogramas.csv` | Por fotograma: tiempo, rostro, pitch, yaw, roll, caja del rostro, puntajes de ojos y clase |
| `segundos.csv` | Por segundo: clase, pitch medio, ojos, fotogramas válidos y si cae en una lectura bíblica |
| `resumen.json` | Parámetros usados, porcentajes, episodios, miradas, lecturas y advertencias |
| `transcripcion.json` | Frases con inicio y fin (si se usó IA) |
| `lecturas.json` | Tramos de lectura bíblica (con referencia) y de oración (si se usó IA) |

Con `mirame recalcular` se reclasifica desde `fotogramas.csv` con otros umbrales sin volver a procesar el video.
