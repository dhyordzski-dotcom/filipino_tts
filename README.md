# Filipino Text-to-Speech (Windows desktop app)

A small Python desktop app: paste Filipino (Tagalog) text, choose a voice,
then **play** it or **save it as an MP3**. It uses Microsoft Edge's neural
voices through the [`edge-tts`](https://github.com/rany2/edge-tts) library.

## Features
- Paste or type Filipino text (right-click menu: cut / copy / paste / select all)
- Filipino voices: **Blessica** (female) and **Angelo** (male), plus an option
  to show every Edge voice in other languages
- **Natural reading** (on by default): before speaking, it tidies the text so
  the voice doesn't sound robotic:
  - joins lines that were broken in the middle of a sentence (common when
    copying from PDFs, chats or websites), and adds pauses after headings and
    list items
  - expands abbreviations: Gng. → Ginang, Bb. → Binibini, Dr. → Doktor,
    Brgy. → Barangay, Sta. → Santa, atbp. → at iba pa, Blg. → Bilang, …
  - ₱1,500 → "1,500 piso", 20% → "20 porsiyento", & → "at", at/o → "at o"
  - removes emojis, links, email addresses, bullet symbols and `#`, and
    collapses "!!!" or "??" into a single mark
  - **Preview text** puts the tidied text in the box so you can see exactly
    what will be read (Ctrl+Z restores the original)
- Speed (default −5%, a little slower and more conversational), pitch and
  volume sliders
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

## Tips for the most natural Filipino
- **Blessica** (female) usually sounds smoother; **Angelo** (male) is a bit
  more formal. Try both on your text.
- Punctuation controls the pauses: use commas and periods the way you'd
  breathe when reading aloud.
- Write numbers the way they should be said if it matters, e.g. "dalawampung
  piso" vs "twenty pesos". Digits are read by the voice's own rules.
- Taglish is fine: the Filipino voices handle common English words.
- Speeds between −10% and 0% tend to sound the most natural. Leave pitch at 0
  unless you want a different character.

## Troubleshooting
- **"Hindi nagawa ang audio" / connection error**: check your internet
  connection. A firewall or proxy might be blocking `speech.platform.bing.com`.
- **The voice list shows only two voices**: the full list couldn't be
  downloaded, but the built-in Filipino voices still work.
