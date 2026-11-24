# Instala o actualiza Mírame en Windows con un solo comando (en PowerShell):
#
#   powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/jacomv/mirame/main/instalar.ps1 | iex"
#
# Qué hace: instala uv (si falta), que a su vez trae Python; instala Mírame con su
# ffmpeg y todo lo demás; descarga el navegador de las capturas; deja un acceso directo
# en el escritorio y abre la app. Volver a ejecutarlo actualiza a la última versión.
# No pide permisos de administrador.
$ErrorActionPreference = 'Stop'

$Fuente = if ($env:MIRAME_FUENTE) { $env:MIRAME_FUENTE } else { 'https://github.com/jacomv/mirame/archive/refs/heads/main.zip' }

function Paso($texto) { Write-Host "`n$texto" -ForegroundColor Cyan }

Paso '1/4 · Preparando uv (instala Python y Mírame)'
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
    $local = Join-Path $env:USERPROFILE '.local\bin\uv.exe'
    if (-not (Test-Path $local)) {
        powershell -ExecutionPolicy ByPass -c 'irm https://astral.sh/uv/install.ps1 | iex'
    }
    $uv = $local
}

Paso '2/4 · Instalando Mírame (la primera vez tarda unos minutos)'
& $uv tool install --force --refresh --python 3.12 "mirame[capturas] @ $Fuente"
if ($LASTEXITCODE) { throw 'No se pudo instalar Mírame.' }
try { & $uv tool update-shell | Out-Null } catch { }
$mirame = Join-Path (& $uv tool dir --bin) 'mirame.exe'

Paso '3/4 · Descargando el navegador para las capturas (unos 150 MB)'
& $mirame instalar-capturas
if ($LASTEXITCODE) { Write-Host 'No se pudo; las capturas quedan desactivadas. Lo demás funciona.' }

Paso '4/4 · Creando el acceso directo'
& $mirame acceso

Write-Host "`nMírame quedó instalada." -ForegroundColor Green
Write-Host 'La próxima vez ábrela con el acceso directo «Mírame» del escritorio.'
if ($env:MIRAME_SIN_ABRIR) { return }
Write-Host 'Abriendo la app...'
& $mirame
