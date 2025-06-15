#!/bin/bash

echo "🎵 Sistema de Cobro Musical - Simple Desktop Version"
echo "====================================================="
echo
echo "Starting simple desktop application..."
echo

# Change to script directory
cd "$(dirname "$0")"

# Run the simple launcher
python3 launcher_simple.py

echo
echo "Application closed."
read -p "Press Enter to exit..."