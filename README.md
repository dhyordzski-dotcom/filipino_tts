# Filipino Text-to-Speech (Windows desktop app)

A small Python desktop app: paste Filipino (Tagalog) text, choose a voice,
then **play** it or **save it as an MP3**. It uses Microsoft Edge's neural
voices through the [`edge-tts`](https://github.com/rany2/edge-tts) library.

## Features
- Paste or type Filipino text (right-click menu: cut / copy / paste / select all)
- Filipino voices: **Blessica** (female) and **Angelo** (male), plus an option
  to show every Edge voice in other languages
- Speed, pitch and volume sliders
- Play and stop inside the app (uses Windows' built-in MCI, so you don't need
  an extra audio library)
- Save as MP3 (if you just played the same text with the same settings, it
  reuses that audio instead of generating it again)
- Shortcuts: `Ctrl+Enter` play, `Ctrl+S` save, `Esc` stop

## Requirements
- Windows 10/11
- Python 3.9+ from [python.org](https://www.python.org/downloads/) (tick
  "Add Python to PATH" during install; Tkinter comes with it)
- An internet connection, because the voices are generated online

## Run
Double-click **`run.bat`**, or from a terminal:

```bat
pip install -r requirements.txt
python filipino_tts_app.py
```

## Build a standalone .exe (optional)
Double-click **`build_exe.bat`**. It installs PyInstaller and creates
`dist\FilipinoTTS.exe`, which you can copy to another PC that doesn't have Python.

## Troubleshooting
- **"Hindi nagawa ang audio" / connection error**: check your internet
  connection. A firewall or proxy might be blocking `speech.platform.bing.com`.
- **The voice list shows only two voices**: the full list couldn't be
  downloaded, but the built-in Filipino voices still work.
