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

1. El audio del recorte se envía a Whisper (`whisper-large-v3-turbo` en Groq, o `whisper-1` en OpenAI si no hay clave de Groq o si en Ajustes se eligió «Solo OpenAI») en tramos de 20 minutos. Vuelve con el tiempo de cada frase y de cada palabra.
   Sobre silencio o música Whisper a veces inventa una frase («Subtítulos realizados por la comunidad de Amara.org») o se queda repitiendo las últimas palabras («y la humanidad, y la humanidad…»), y puede seguir así varios minutos tapando lo que de verdad se dijo. Mírame busca, palabra por palabra, un grupo de hasta 8 palabras repetido al menos cuatro veces seguidas; una repetición retórica («santo, santo, santo») no llega a eso. Cuando lo encuentra vuelve a pedir solo la parte dañada, en pedazos cada vez más cortos (hasta 40 segundos), y descarta las frases inventadas. El daño queda encerrado en el silencio donde empezó y lo demás se recupera.
2. Whisper a veces junta en una sola frase de 25 segundos el final de una lectura y el comentario que sigue. Por eso las frases largas se parten en pedazos de 8 segundos como máximo, usando el tiempo de cada palabra.
3. Un modelo de lenguaje recibe la transcripción en ventanas de 8 minutos y marca qué frases son **texto bíblico leído** (en cualquier versión) y cuáles son **oración**. No cuentan el anuncio («abramos en Romanos 11»), la paráfrasis ni el comentario.
4. Los segundos «abajo» dentro de una lectura pasan a **Biblia**. Las oraciones se excluyen del cálculo porque los ojos cerrados se ven igual que mirar abajo.

Solo cuenta como oración el momento en que el predicador le habla a Dios: invitar a orar, contar lo que alguien oró o nombrar mucho a Dios al explicar el texto no lo son. Un modelo pequeño puede confundirlos y dejar minutos de predicación fuera de la medición, como huecos en la línea de tiempo. Por eso, si más del 15 % del sermón queda marcado como oración, el reporte lo avisa con los minutos para revisarlos.

Se compara con un modelo de lenguaje y no con el texto bíblico literal porque los predicadores citan de varias versiones. Las marcas quedan en `lecturas.json`: si algo salió mal, se corrige a mano y se aplica con `mirame lecturas <análisis> --solo-recalcular`. El modelo no responde siempre igual: entre dos corridas pueden cambiar uno o dos tramos y las cifras unas décimas.

## 6. Estructura del sermón (opcional)

Con una clave de IA, `mirame estructura` (o el botón «Analizar estructura» de la app) toma la misma transcripción y hace tres tipos de consulta a un modelo de lenguaje:

1. **Estructura, argumento y clímax**, con el sermón completo: el tema, las partes y la frase en que el predicador hace la transición a cada una, si la estructura es clara, si anunció sus puntos en voz alta (con el minuto y las palabras de cada anuncio), si la introducción (vaya antes o después de la oración inicial) prepara el argumento principal o habla de otra cosa, los pasos del argumento y el clímax.
2. **Evangelio y aplicaciones**, con el sermón completo: cada momento en que habla de la persona o la obra de Cristo, con el aspecto que toca (encarnación, vida, muerte, resurrección, ascensión, reinado, segunda venida…), y cada llamado concreto a los oyentes, con la parte del pasaje en que se apoya. Las menciones de paso («en el nombre de Jesús» al orar) no cuentan.
3. **Pasajes citados**, en ventanas de 8 minutos para no dejar ninguno: cada referencia y si fue leída, citada de memoria, mencionada o aludida. La misma referencia repetida en menos de 45 segundos cuenta una vez.

«Anunció sus puntos» se refiere a los puntos principales del sermón. Una lista dentro de un punto («fueron tres cosas…», «número dos…») se muestra con su minuto, marcada como «lista dentro de un punto», pero no cuenta como anunciar los puntos.

El modelo no da minutos: señala el **número de frase** de la transcripción, y el tiempo sale de ahí. Así un minuto del reporte siempre corresponde a algo que se dijo, aunque el modelo se equivoque al interpretarlo. Lo que apunta a una frase que no existe se descarta.

El resultado queda en `estructura.json` (lo que muestra la pestaña «Sermón» del reporte) y en `estructura.md` (el mismo contenido como texto). Este paso no toca las cifras de la mirada. El reporte cruza las dos cosas en un punto: en cada parte del sermón dice qué porcentaje del tiempo el predicador miró a la congregación.

Conviene leerlo como la opinión de un oyente atento, no como un veredicto:

- Es un juicio de un modelo de lenguaje sobre una transcripción automática. Puede dividir el sermón distinto a como lo pensó el predicador, o tomar por clímax un momento que solo fue enfático.
- No oye el tono, las pausas ni el volumen: el clímax lo deduce de las palabras.
- No responde siempre igual: dos corridas pueden nombrar las partes distinto o mover una transición una o dos frases.
- Si el recorte no cubre el sermón entero, la estructura describe solo lo que quedó dentro.

## 7. Límites conocidos

- **Parpadeos largos y ojos entrecerrados** pueden contarse como mirar abajo. El umbral de ojos (0,45) se eligió revisando muestras a ojo, no con un etiquetado sistemático.
- **Sin rostro, sin medida.** Si la transmisión muestra la congregación, diapositivas o el texto en pantalla, esos segundos quedan «sin dato». Pasado el 30 %, el reporte avisa que el resultado es poco confiable.
- **Mirar abajo no siempre es leer.** Bajar la vista para pensar, mirar a la primera fila o a un niño cuenta igual. La herramienta mide la dirección de la mirada, no la intención.
- **La cámara cuenta.** Una cámara muy alta o muy baja cambia el ángulo aparente. Como la referencia es la postura habitual de cada sermón, comparar sermones grabados con cámaras distintas es razonable; comparar la cifra exacta con otra herramienta, no.
- **Falta validar contra un etiquetado humano.** El comando `mirame validar` compara el resultado con un CSV etiquetado a mano (`t,clase` por segundo, o `inicio,fin,clase` por tramos; clase `c`, `a` o `s`). El objetivo es al menos 90 % de coincidencia. Si haces esa validación con tus sermones, compartir el resultado ayuda a todos.

## 8. Qué hay en cada archivo

| Archivo | Contenido |
|---|---|
| `fotogramas.csv` | Por fotograma: tiempo, rostro, pitch, yaw, roll, caja del rostro, puntajes de ojos y clase |
| `segundos.csv` | Por segundo: clase, pitch medio, ojos, fotogramas válidos y si cae en una lectura bíblica |
| `resumen.json` | Parámetros usados, porcentajes, episodios, miradas, lecturas y advertencias |
| `transcripcion.json` | Frases con inicio y fin (si se usó IA) |
| `lecturas.json` | Tramos de lectura bíblica (con referencia) y de oración (si se usó IA) |
| `estructura.json` | Estructura y contenido del sermón: partes, argumento, clímax, evangelio, aplicaciones y pasajes, con sus tiempos (si se usó IA) |
| `estructura.md` | Lo mismo, como texto |

Con `mirame recalcular` se reclasifica desde `fotogramas.csv` con otros umbrales sin volver a procesar el video.
