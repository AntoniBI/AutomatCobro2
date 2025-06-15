"""
Setup script for desktop application
This script helps convert the Streamlit app to a desktop application
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install all required packages"""
    print("Installing required packages...")
    
    # Base requirements
    requirements = [
        "streamlit==1.28.1",
        "pandas==2.1.3", 
        "openpyxl==3.1.2",
        "xlsxwriter==3.1.9",
        "numpy==1.25.2",
        "plotly==5.17.0",
        "pyinstaller==6.2.0",
        "auto-py-to-exe==2.41.0"
    ]
    
    for requirement in requirements:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", requirement])
            print(f"✅ Installed: {requirement}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {requirement}: {e}")
            return False
    
    return True

def create_launcher_script():
    """Create a launcher script for the desktop app"""
    launcher_content = '''import streamlit.web.cli as stcli
import sys
import os

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    # Configure Streamlit to run the app
    sys.argv = ["streamlit", "run", app_path, "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    stcli.main()
'''
    
    with open("launcher.py", "w", encoding="utf-8") as f:
        f.write(launcher_content)
    
    print("✅ Created launcher.py")

def create_batch_file():
    """Create a simple batch file to run the application"""
    batch_content = '''@echo off
echo Starting Musical Payment System...
echo Open your browser and go to: http://localhost:8501
echo Press Ctrl+C to stop the application
python launcher.py
pause
'''
    
    with open("start_app.bat", "w", encoding="utf-8") as f:
        f.write(batch_content)
    
    print("✅ Created start_app.bat")

def create_instructions():
    """Create instructions for users"""
    instructions = '''# INSTRUCCIONES PARA APLICACIÓN DE ESCRITORIO

## Opción 1: Ejecutar con Python (Recomendado)
1. Haz doble clic en "start_app.bat"
2. Se abrirá una ventana de comando
3. Abre tu navegador web y ve a: http://localhost:8501
4. ¡La aplicación estará funcionando!

## Opción 2: Crear ejecutable independiente
1. Instala Python 3.8+ en tu computadora
2. Ejecuta: python setup_desktop.py
3. Sigue las instrucciones en pantalla

## Requisitos
- Python 3.8 o superior
- Conexión a internet (para la primera instalación)
- Navegador web (Chrome, Firefox, Edge, etc.)

## Archivos importantes
- app.py: Aplicación principal
- Data/Actes.xlsx: Datos de ejemplo
- requirements.txt: Dependencias
- launcher.py: Lanzador de la aplicación

## Compartir con otros usuarios
Para que otros usuarios puedan usar la aplicación:
1. Copia toda la carpeta a su computadora
2. Instala Python en su computadora
3. Ejecuta "start_app.bat"

## Soporte
Si tienes problemas, verifica que:
1. Python esté instalado correctamente
2. Todas las dependencias estén instaladas
3. El archivo Data/Actes.xlsx exista en la carpeta correcta
'''
    
    with open("INSTRUCCIONES.md", "w", encoding="utf-8") as f:
        f.write(instructions)
    
    print("✅ Created INSTRUCCIONES.md")

def create_desktop_shortcut():
    """Create desktop shortcut (Windows only)"""
    try:
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, "Sistema Cobro Musical.lnk")
        target = os.path.join(os.getcwd(), "start_app.bat")
        wdir = os.getcwd()
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = wdir
        shortcut.WindowStyle = 1
        shortcut.save()
        
        print("✅ Acceso directo creado en el escritorio")
        
    except ImportError:
        print("⚠️  No se pudo crear acceso directo (requiere pywin32)")
    except Exception as e:
        print(f"⚠️  Error creando acceso directo: {e}")

def detect_os():
    """Detect operating system"""
    import platform
    os_name = platform.system().lower()
    if os_name == "windows":
        return "windows"
    elif os_name == "darwin":
        return "macos"
    elif os_name == "linux":
        return "linux"
    else:
        return "unknown"

def main():
    """Main setup function"""
    print("🎵 Configurando Sistema de Cobro Musical para Escritorio")
    print("=" * 70)
    
    # Detect OS
    current_os = detect_os()
    print(f"🖥️  Sistema operativo detectado: {current_os.upper()}")
    
    # Check if Python is available
    try:
        python_version = sys.version
        print(f"✅ Python detectado: {python_version}")
    except:
        print("❌ Python no encontrado. Por favor instala Python primero.")
        return
    
    # Install requirements
    print("\n📦 Instalando dependencias...")
    if not install_requirements():
        print("❌ Error instalando dependencias")
        return
    
    # Create necessary files
    print("\n📁 Creando archivos de configuración...")
    create_launcher_script()
    create_batch_file()
    create_instructions()
    
    # OS-specific setup
    if current_os == "windows":
        print("\n🖥️  Configuración específica para Windows...")
        create_desktop_shortcut()
        startup_file = "start_app.bat"
    elif current_os in ["macos", "linux"]:
        print(f"\n🖥️  Configuración específica para {current_os.upper()}...")
        # Make shell script executable
        try:
            os.chmod("start_app.sh", 0o755)
            print("✅ Permisos de ejecución configurados para start_app.sh")
        except:
            print("⚠️  No se pudieron configurar permisos para start_app.sh")
        startup_file = "start_app.sh"
    else:
        startup_file = "launcher.py"
    
    print("\n" + "=" * 70)
    print("🎉 ¡Configuración completada exitosamente!")
    print("\n📋 PRÓXIMOS PASOS:")
    print("=" * 40)
    
    if current_os == "windows":
        print("1. Haz doble clic en 'start_app.bat' o en el acceso directo del escritorio")
        print("2. La aplicación se abrirá automáticamente en tu navegador")
    elif current_os in ["macos", "linux"]:
        print("1. Ejecuta './start_app.sh' desde la terminal")
        print("   O haz doble clic en start_app.sh (si tu sistema lo permite)")
        print("2. La aplicación se abrirá automáticamente en tu navegador")
    else:
        print("1. Ejecuta 'python launcher.py' desde la terminal")
        print("2. Abre tu navegador en: http://localhost:8501")
    
    print("\n💡 RECURSOS ADICIONALES:")
    print("• Lee 'INSTRUCCIONES.md' para guía detallada")
    print("• Consulta 'CLAUDE.md' para información técnica")
    print("• El archivo 'Data/Actes.xlsx' contiene datos de ejemplo")
    
    print("\n🚀 ¡La aplicación está lista para usar!")
    print("=" * 70)

if __name__ == "__main__":
    main()