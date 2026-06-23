@echo off
REM Crea el acceso directo "Cobro Musical" en el Escritorio.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_acceso_directo.ps1"
echo.
echo Listo. Ya puedes lanzar la app desde el icono "Cobro Musical" del Escritorio.
pause
