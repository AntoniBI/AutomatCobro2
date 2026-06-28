@echo off
REM Lanzador del Sistema de Cobro Musical (web app FastAPI)
REM Siempre ejecuta el codigo de la rama main.
cd /d "%~dp0"

echo Cambiando a la rama main...
git checkout main
if errorlevel 1 (
    echo.
    echo [AVISO] No se pudo cambiar a la rama main.
    echo Puede que tengas cambios sin guardar en la rama actual.
    echo Guardalos o descartalos y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

echo Iniciando Sistema de Cobro Musical...
python run.py
pause
