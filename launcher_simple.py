#!/usr/bin/env python3
"""
Simple Launcher for Sistema de Cobro Musical
Uses pure tkinter for maximum compatibility
"""

import sys
import os
import subprocess

def install_requirements():
    """Install basic required packages"""
    try:
        import pandas
        import openpyxl
        import xlsxwriter
        print("✅ Required packages are installed")
        return True
    except ImportError:
        print("📦 Installing required packages...")
        try:
            # Install only essential packages
            packages = ['pandas', 'openpyxl', 'xlsxwriter', 'numpy']
            for package in packages:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print("✅ Packages installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Error installing packages")
            return False

def main():
    """Main launcher function"""
    print("🎵 Sistema de Cobro Musical - Simple Desktop Version")
    print("=" * 60)
    
    # Check and install requirements
    if not install_requirements():
        input("Press Enter to exit...")
        return
    
    # Launch the simple desktop application
    try:
        print("🚀 Launching simple desktop application...")
        
        # Import and run the simple app
        from app_simple import main as run_simple_app
        run_simple_app()
        
    except Exception as e:
        print(f"❌ Error launching application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()