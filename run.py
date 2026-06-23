"""
run.py — Lanzador del Sistema de Cobro Musical (web app FastAPI).

Arranca el servidor uvicorn y abre el navegador automáticamente.

Uso:
    python run.py
    # o doble clic en start_web.bat (Windows)
"""

import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    # Abrir el navegador poco después de arrancar el servidor
    threading.Timer(1.2, open_browser).start()
    uvicorn.run("backend.server:app", host=HOST, port=PORT, reload=False)
