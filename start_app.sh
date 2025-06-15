#!/bin/bash

# Script para ejecutar Sistema de Cobro Musical en MacOS/Linux
# Make sure this script is executable: chmod +x start_app.sh

echo "================================================================"
echo "              🎵 SISTEMA DE COBRO MUSICAL 🎵"
echo "================================================================"
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ ERROR: Python no está instalado"
    echo
    echo "💡 SOLUCIÓN:"
    echo "   MacOS: brew install python3"
    echo "   Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "   Fedora/RHEL: sudo dnf install python3 python3-pip"
    echo
    echo "================================================================"
    read -p "Presiona Enter para salir..."
    exit 1
fi

# Determine Python command
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

echo "✅ Python detectado: $($PYTHON_CMD --version)"
echo

# Check if launcher.py exists
if [ ! -f "launcher.py" ]; then
    echo "❌ ERROR: No se encuentra el archivo launcher.py"
    echo "   Asegúrate de estar ejecutando este archivo desde la carpeta correcta"
    echo
    read -p "Presiona Enter para salir..."
    exit 1
fi

echo "🚀 Iniciando aplicación..."
echo
echo "================================================================"
echo "  INFORMACIÓN IMPORTANTE:"
echo "  • La aplicación se abrirá automáticamente en tu navegador"
echo "  • Si no se abre, ve manualmente a la URL que aparezca"
echo "  • Para cerrar la aplicación, presiona Ctrl+C en esta terminal"
echo "  • Mantén esta terminal abierta mientras uses la aplicación"
echo "================================================================"
echo

# Run the launcher
$PYTHON_CMD launcher.py

echo
echo "================================================================"
echo "🛑 Aplicación cerrada"

if [ $? -eq 0 ]; then
    echo "✅ Aplicación cerrada correctamente"
else
    echo "❌ La aplicación se cerró con errores"
    echo "💡 Consejos:"
    echo "   1. Revisa los mensajes de error arriba"
    echo "   2. Consulta el archivo INSTRUCCIONES.md"
    echo "   3. Verifica que todos los archivos estén presentes"
fi

echo
read -p "Presiona Enter para salir..."