# Instala o actualiza Mírame en Windows con un solo comando (en PowerShell o en cmd):
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/jacomv/mirame/main/instalar.ps1 | iex"
#
# Qué hace: instala uv (si falta), que a su vez trae Python; instala Mírame con su
# ffmpeg y todo lo demás; descarga el navegador de las capturas; deja un acceso directo
# en el escritorio y abre la app. Volver a ejecutarlo actualiza a la última versión.
# No pide permisos de administrador.
#
# Variables para pruebas: MIRAME_FUENTE (de dónde instalar), MIRAME_SIN_ABRIR (no abrir la app).
# Este archivo va en UTF-8 con BOM para que Windows PowerShell lea bien los acentos.
$ErrorActionPreference = 'Stop'

$Fuente = if ($env:MIRAME_FUENTE) { $env:MIRAME_FUENTE } else { 'https://github.com/jacomv/mirame/archive/refs/heads/main.zip' }
$Ayuda = 'https://github.com/jacomv/mirame/blob/main/docs/instalar.md#si-algo-sale-mal'

function Paso($n, $titulo, $detalle) {
    Write-Host ''
    Write-Host "Paso $n de 4 · $titulo" -ForegroundColor Cyan
    Write-Host $detalle
}

try {
    Write-Host ''
    Write-Host 'Instalador de Mírame' -ForegroundColor Cyan
    Write-Host 'Son cuatro pasos. Tarda unos minutos según tu conexión y ocupa cerca de 1 GB.'
    Write-Host 'No cierres esta ventana hasta que veas «Mírame quedó instalada».'

    Paso 1 'Preparar uv' 'uv es el programa que instala Python y Mírame sin tocar el resto de tu computadora.'
    $uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
    if ($uv) {
        Write-Host 'Ya lo tienes.'
    } else {
        $uv = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
        if (Test-Path $uv) {
            Write-Host 'Ya lo tienes.'
        } else {
            powershell -ExecutionPolicy ByPass -c 'irm https://astral.sh/uv/install.ps1 | iex' | Out-Null
            if (-not (Test-Path $uv)) { throw 'No se pudo instalar uv.' }
            Write-Host 'Listo.'
        }
    }

    Paso 2 'Instalar Mírame' 'Descarga Python, Mírame y lo que necesita para leer el video. Es el paso más largo.'
    & $uv tool install --force --refresh --python 3.12 "mirame[capturas] @ $Fuente"
    if ($LASTEXITCODE) { throw 'No se pudo instalar Mírame.' }
    try { & $uv tool update-shell | Out-Null } catch { }
    $mirame = Join-Path (& $uv tool dir --bin) 'mirame.exe'

    Paso 3 'Descargar el navegador de las capturas' 'Lo usa el botón «Capturar» para guardar imágenes del reporte (unos 200 MB).'
    & $mirame instalar-capturas
    if ($LASTEXITCODE) { Write-Host 'No se pudo. Las capturas quedan desactivadas; todo lo demás funciona.' }

    Paso 4 'Crear el acceso directo' 'Para abrir Mírame con doble clic.'
    & $mirame acceso
    if ($LASTEXITCODE) { Write-Host 'No se pudo crear. Puedes abrir Mírame escribiendo «mirame» en una ventana nueva de PowerShell.' }

    $version = (& $mirame --version) -replace '^mirame ', ''
} catch {
    Write-Host ''
    Write-Host 'La instalación no terminó.' -ForegroundColor Red
    Write-Host $_
    Write-Host 'Casi siempre es la conexión: vuelve a pegar el mismo comando y continúa donde quedó.'
    Write-Host "Si se repite, mira la guía: $Ayuda"
    if ($env:MIRAME_SIN_ABRIR) { exit 1 }
    return
}

Write-Host ''
Write-Host "Mírame $version quedó instalada." -ForegroundColor Green
Write-Host ''
Write-Host '  · Para abrirla: doble clic en «Mírame» en el escritorio.'
Write-Host '  · Mientras la usas, queda abierta una ventana negra. Para cerrar Mírame, ciérrala.'
Write-Host '  · Para actualizar más adelante: vuelve a pegar el mismo comando.'
if ($env:MIRAME_SIN_ABRIR) { return }
Write-Host ''
Write-Host 'Abriendo Mírame en tu navegador...'
& $mirame
