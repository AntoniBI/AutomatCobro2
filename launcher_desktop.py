#!/usr/bin/env python3
"""
Desktop Launcher for Sistema de Cobro Musical
Launches the CustomTkinter desktop application
"""

import sys
import os
import subprocess

def install_requirements():
    """Install required packages if not present"""
    try:
        import customtkinter
        import pandas
        import matplotlib
        import seaborn
        print("✅ All required packages are already installed")
        return True
    except ImportError as e:
        print(f"📦 Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print("✅ Packages installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Error installing packages")
            return False

def main():
    """Main launcher function"""
    print("🎵 Sistema de Cobro Musical - Desktop Version")
    print("=" * 50)
    
    # Check and install requirements
    if not install_requirements():
        input("Press Enter to exit...")
        return
    
    # Launch the desktop application
    try:
        print("🚀 Launching desktop application...")
        
        # Import and run the desktop app
        from app_desktop import main as run_desktop_app
        run_desktop_app()
        
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()