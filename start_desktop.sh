#!/bin/bash

echo "🎵 Sistema de Cobro Musical - Desktop Version"
echo "================================================"
echo
echo "Starting desktop application..."
echo

# Change to script directory
cd "$(dirname "$0")"

# Run the desktop launcher
python3 launcher_desktop.py

echo
echo "Application closed."
read -p "Press Enter to exit..."