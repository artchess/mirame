# Guía de instalación

Esta guía es para quien nunca ha abierto una terminal. Vas a copiar una línea, pegarla y esperar. Toma entre cinco y quince minutos, casi todos de descarga.

**Lo que necesitas:**

- Una computadora con macOS, Windows 10 u 11, o Linux.
- Conexión a internet.
- Cerca de 1 GB libre en el disco.

No necesitas permisos de administrador ni instalar nada antes. El instalador trae todo lo que Mírame usa.

**Elige tu sistema:** [Mac](#en-mac) · [Windows](#en-windows) · [Linux](#en-linux)

---

## En Mac

### 1. Abre la Terminal

Pulsa <kbd>⌘ Cmd</kbd> + <kbd>Espacio</kbd>, escribe **Terminal** y pulsa <kbd>Enter</kbd>.

Se abre una ventana con un poco de texto y un cursor parpadeando. Ahí se escriben (o se pegan) instrucciones para la computadora.

### 2. Copia el comando

```bash
curl -LsSf https://raw.githubusercontent.com/jacomv/mirame/main/instalar.sh | sh
```

En GitHub, al pasar el mouse sobre el recuadro aparece a la derecha un botón para copiar. También puedes seleccionarlo con el mouse y pulsar <kbd>⌘ Cmd</kbd> + <kbd>C</kbd>.

### 3. Pégalo en la Terminal

Haz clic dentro de la ventana de la Terminal, pulsa <kbd>⌘ Cmd</kbd> + <kbd>V</kbd> y luego <kbd>Enter</kbd>.

### 4. Espera

Verás avanzar cuatro pasos ([cómo se ve](#qué-verás-mientras-se-instala)). El segundo es el más largo. No cierres la ventana hasta que aparezca **«Mírame quedó instalada»** en verde.

### 5. Listo

Mírame se abre sola en tu navegador y queda un acceso directo **Mírame** en el escritorio.

Sigue en [Usar Mírame después de instalarla](#usar-mírame-después-de-instalarla).

---

## En Windows

### 1. Abre PowerShell

Pulsa la tecla <kbd>⊞ Windows</kbd>, escribe **PowerShell** y pulsa <kbd>Enter</kbd>.

Se abre una ventana azul o negra con un cursor. No hace falta abrirla «como administrador».

### 2. Copia el comando

```powershell
irm https://raw.githubusercontent.com/jacomv/mirame/main/instalar.ps1 | iex
```

En GitHub, al pasar el mouse sobre el recuadro aparece a la derecha un botón para copiar. También puedes seleccionarlo y pulsar <kbd>Ctrl</kbd> + <kbd>C</kbd>.

### 3. Pégalo en PowerShell

Haz clic dentro de la ventana y pulsa <kbd>Ctrl</kbd> + <kbd>V</kbd> (o clic derecho), y luego <kbd>Enter</kbd>.

No hace falta cambiar la configuración de seguridad de Windows. Sirve cualquier PowerShell: el que trae Windows o PowerShell 7.

> Si en vez de PowerShell abriste el **Símbolo del sistema** (cmd), pega esta otra línea:
>
> ```bat
> powershell -c "irm https://raw.githubusercontent.com/jacomv/mirame/main/instalar.ps1 | iex"
> ```

### 4. Espera

Verás avanzar cuatro pasos ([cómo se ve](#qué-verás-mientras-se-instala)). El segundo es el más largo. No cierres la ventana hasta que aparezca **«Mírame quedó instalada»** en verde.

### 5. Listo

Mírame se abre sola en tu navegador y queda un acceso directo **Mírame** en el escritorio.

---

## En Linux

Abre una terminal y pega:

```bash
curl -LsSf https://raw.githubusercontent.com/jacomv/mirame/main/instalar.sh | sh
```

Al terminar, Mírame aparece en el menú de aplicaciones. Si las capturas no funcionan, Playwright puede necesitar bibliotecas del sistema: `sudo ~/.local/share/uv/tools/mirame/bin/python -m playwright install-deps chromium`.

---

## Qué verás mientras se instala

Algo así (en tu pantalla habrá más líneas de descarga entre un paso y otro):

```text
Instalador de Mírame
Son cuatro pasos. Tarda unos minutos según tu conexión y ocupa cerca de 1 GB.
No cierres esta ventana hasta que veas «Mírame quedó instalada».

Paso 1 de 4 · Preparar uv
uv es el programa que instala Python y Mírame sin tocar el resto de tu computadora.
Listo.

Paso 2 de 4 · Instalar Mírame
Descarga Python, Mírame y lo que necesita para leer el video. Es el paso más largo.
Installed 1 executable: mirame

Paso 3 de 4 · Descargar el navegador de las capturas
Lo usa el botón «Capturar» para guardar imágenes del reporte (unos 200 MB).

Paso 4 de 4 · Crear el acceso directo
Para abrir Mírame con doble clic.
Acceso directo creado: /Users/tu-usuario/Desktop/Mírame.command

Mírame 0.5.1 quedó instalada.

  · Para abrirla: doble clic en «Mírame» en el escritorio.
  · Mientras la usas, queda abierta una ventana como esta. Para cerrar Mírame, ciérrala.
  · Para actualizar más adelante: vuelve a pegar el mismo comando.

Abriendo Mírame en tu navegador...
```

Los textos en inglés que aparecen en el paso 2 son de las herramientas que descargan; es normal.

---

## Usar Mírame después de instalarla

1. **Ábrela** con doble clic en **Mírame** en el escritorio.
2. Se abre una **ventana de terminal** y, enseguida, Mírame en tu navegador. Esa ventana es la app funcionando: déjala abierta mientras la uses (puedes minimizarla).
3. **Para cerrar Mírame**, cierra esa ventana. Tus análisis quedan guardados.

Si das doble clic con Mírame ya abierta, te lleva a la misma app en vez de abrir otra.

La primera vez que analices un sermón, Mírame descarga un modelo pequeño (3,6 MB) para reconocer rostros.

## Actualizar

Cierra Mírame y vuelve a pegar **el mismo comando de instalación**. Instala la versión nueva encima de la anterior y no toca tus análisis, videos ni claves. Puedes ver qué versión tienes en el pie de la app.

## Si algo sale mal

**El instalador dice «La instalación no terminó».** Casi siempre es una conexión que se cortó. Vuelve a pegar el mismo comando: lo que ya se descargó no se repite.

**«No se pudo» en el paso 3 (capturas).** Mírame funciona igual; solo el botón **Capturar** queda desactivado. Para intentarlo de nuevo, abre una terminal nueva y escribe `mirame instalar-capturas`.

**`mirame` no se reconoce como comando.** La terminal que tenías abierta no conoce todavía el programa nuevo. Ciérrala y abre otra, o usa el acceso directo del escritorio.

**En Windows: «irm no se reconoce como comando».** Abriste el Símbolo del sistema (cmd), no PowerShell. Usa la línea para cmd que aparece en el paso 3, o abre PowerShell.

**En Windows: «No se pudo ejecutar el programa "powershell.exe"… UseShellExecute».** Pegaste el comando de una versión anterior de esta guía, que fallaba en PowerShell 7. Usa el comando actual, que empieza por `irm`.

**En Mac: el acceso directo abre la Terminal y se cierra enseguida.** Abre la Terminal, escribe `mirame` y pulsa Enter para ver el mensaje de error.

**Nada de lo anterior.** Abre un [reporte de error](https://github.com/jacomv/mirame/issues/new?template=error.yml) y pega el texto que aparece en la ventana.

## Qué instala y dónde

Todo queda dentro de tu usuario:

| Qué | Dónde |
|---|---|
| uv, el instalador de Python | `~/.local/bin` (en Windows, `%USERPROFILE%\.local\bin`) |
| Python y Mírame | la carpeta de herramientas de uv (`uv tool dir` la muestra) |
| Navegador de las capturas | la caché de Playwright (`~/Library/Caches/ms-playwright` en Mac, `%LOCALAPPDATA%\ms-playwright` en Windows, `~/.cache/ms-playwright` en Linux) |
| Tus análisis, videos y claves | `~/Mirame` |

Para desinstalar: `uv tool uninstall mirame`, y borra el acceso directo del escritorio. La carpeta `~/Mirame` con tus análisis se queda; bórrala a mano si ya no la quieres.
