@echo off
REM Installs the dependency (first run only) and starts the app.
cd /d "%~dp0"
python -m pip install --quiet -r requirements.txt
pythonw filipino_tts_app.py
