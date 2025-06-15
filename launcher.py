import streamlit.web.cli as stcli
import sys
import os

if __name__ == "__main__":
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, "app.py")
    
    # Configure Streamlit to run the app
    sys.argv = ["streamlit", "run", app_path, "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    stcli.main()
