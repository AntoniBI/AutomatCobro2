# Crea un acceso directo "Cobro Musical" en el Escritorio que arranca la app.
$ErrorActionPreference = "Stop"

$root    = Split-Path -Parent $MyInvocation.MyCommand.Definition
$desktop = [Environment]::GetFolderPath("Desktop")
$lnkPath = Join-Path $desktop "Cobro Musical.lnk"

$ws  = New-Object -ComObject WScript.Shell
$lnk = $ws.CreateShortcut($lnkPath)
$lnk.TargetPath       = Join-Path $root "start_web.bat"
$lnk.WorkingDirectory = $root
$lnk.IconLocation     = Join-Path $root "frontend\assets\escudo.ico"
$lnk.Description       = "Sistema de Cobro Musical"
$lnk.Save()

Write-Host "Acceso directo creado en el Escritorio: $lnkPath"
