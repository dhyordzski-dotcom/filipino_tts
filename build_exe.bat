@echo off
REM Builds a standalone Windows executable in the "dist" folder.
cd /d "%~dp0"
python -m pip install --quiet -r requirements.txt pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name FilipinoTTS filipino_tts_app.py
echo.
echo Done. Your app is at dist\FilipinoTTS.exe
pause
