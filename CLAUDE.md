# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Sistema de Cobro Musical - A Streamlit application for automating payment calculations for musicians in Valencian musical societies based on event attendance data.

## Development Setup

### Requirements
```bash
pip install -r requirements.txt
```

### Running the Application

#### Development Mode
```bash
streamlit run app.py
```

#### Desktop Application Mode (New CustomTkinter Version)
```bash
python launcher_desktop.py
# or double-click start_desktop.bat (Windows)
# or ./start_desktop.sh (Mac/Linux)
```

#### Legacy Streamlit Web Mode
```bash
python launcher.py
# or double-click start_app.bat (Windows)
```

#### Setup Desktop Environment
```bash
python setup_desktop.py
```

### Key Technologies
- **Backend**: Python with pandas for data processing
- **Frontend**: CustomTkinter for native desktop interface (NEW) / Streamlit for web interface (Legacy)
- **Data**: Excel files (openpyxl for reading, xlsxwriter for export)
- **Visualization**: Matplotlib & Seaborn for desktop charts / Plotly for web charts

## Data Structure

The application works with an Excel file (`Data/Actes.xlsx`) containing three sheets:

1. **Asistencia**: Attendance data (214 musicians x 33 events) with binary attendance values
2. **Presupuesto**: Budget information per event (COBRAT, LLOGATS, TRANSPORT, A REPARTIR)
3. **Configuracion_Precios**: Payment weights by category (A, B, C, D, E) per event

## Architecture

### Main Components
- `MusicianPaymentSystem`: Core class handling data loading and payment calculations
- Multi-page Streamlit interface with navigation sidebar
- Real-time budget vs distributed amount calculations
- Excel export functionality with multiple sheets

### Key Features
1. **Dashboard**: Overview with key metrics and data visualization
2. **Weight Editor**: Edit payment weights (ponderaciones) by category per event
3. **Event Analysis**: Detailed analysis per event with musician counts by category
4. **Processing & Export**: Complete payment calculation and Excel download

### Payment Calculation Process
The system follows a 17-step process:
1. Transform attendance to long format
2. Normalize names and values
3. Join with budget and weights
4. Filter attendees and calculate weighted payments
5. Generate summaries and pivot tables
6. Handle official events and export results

## File Structure
- `app_desktop.py`: NEW CustomTkinter desktop application
- `launcher_desktop.py`: NEW Desktop application launcher
- `start_desktop.bat`: NEW Windows batch file for desktop app
- `start_desktop.sh`: NEW Mac/Linux shell script for desktop app
- `app.py`: Legacy Streamlit web application
- `launcher.py`: Legacy web launcher
- `start_app.bat`: Legacy Windows batch file for web app
- `setup_desktop.py`: Desktop environment setup script
- `analyze_data.py`: Data structure analysis utility
- `Data/Actes.xlsx`: Source data file
- `requirements.txt`: Python dependencies (updated for CustomTkinter)
- `INSTRUCCIONES.md`: User instructions

## Key Improvements Made
1. **NEW Desktop Application**: Complete native desktop interface using CustomTkinter
   - No browser dependency
   - Faster performance
   - Better user experience
   - Professional desktop appearance
   - Native file dialogs and menus
2. **Excel Upload**: Easy file loading with visual feedback
3. **Number Formatting**: Fixed Excel export formatting (€209.38 instead of 20938698828310200)
4. **Summary Sheet**: Added comprehensive RESUMEN_GENERAL sheet with:
   - Key metrics (total budget, distributed, difference)
   - Budget vs distributed by event
   - Earnings by category summary
5. **Multi-Platform Support**: Works on Windows, Mac, and Linux
   - Platform-specific launchers
   - Easy installation and setup

## Payment Formula
The system uses the correct formula: `(A_REPARTIR / total_asistentes) * ponderacion`