"""
Filipino Text-to-Speech desktop app.

Paste Filipino (Tagalog) text, pick a voice, then play it or save it as an MP3.
Speech is generated with Microsoft Edge's online neural voices via `edge-tts`
(an internet connection is required).

Run:  python filipino_tts_app.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import threading
import uuid
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk

import edge_tts

APP_TITLE = "Filipino Text-to-Speech"

# Built-in Filipino voices (always shown, even if the voice list can't be fetched).
DEFAULT_VOICES = {
    "Blessica (Babae / Female) – fil-PH": "fil-PH-BlessicaNeural",
    "Angelo (Lalaki / Male) – fil-PH": "fil-PH-AngeloNeural",
}

SAMPLE_TEXT = (
    "Magandang araw sa inyong lahat! Ito ay isang halimbawa ng "
    "text-to-speech sa wikang Filipino. Salamat po!"
)


# --------------------------------------------------------------------------- #
# Audio playback
# --------------------------------------------------------------------------- #
class AudioPlayer:
    """Plays MP3 files.

    On Windows it uses the built-in MCI (winmm.dll) so no extra packages are
    needed. Elsewhere it falls back to pygame if installed, else the OS default
    player.
    """

    def __init__(self) -> None:
        self._alias: str | None = None
        self._is_windows = sys.platform.startswith("win")
        if self._is_windows:
            import ctypes

            self._winmm = ctypes.windll.winmm  # type: ignore[attr-defined]
            self._buf = ctypes.create_unicode_buffer(256)

    # -- Windows MCI helpers ------------------------------------------------ #
    def _mci(self, command: str) -> str:
        err = self._winmm.mciSendStringW(command, self._buf, 255, 0)
        if err:
            errbuf = type(self._buf)(256)  # same ctypes buffer type
            self._winmm.mciGetErrorStringW(err, errbuf, 255)
            raise RuntimeError(f"MCI error {err}: {errbuf.value}")
        return self._buf.value

    def play(self, path: str) -> None:
        self.stop()
        if self._is_windows:
            alias = f"tts_{uuid.uuid4().hex[:8]}"
            self._mci(f'open "{path}" type mpegvideo alias {alias}')
            self._mci(f"play {alias}")
            self._alias = alias
            return

        try:
            import pygame  # type: ignore

            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
        except ImportError:
            if sys.platform == "darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}" >/dev/null 2>&1 &')

    def is_playing(self) -> bool:
        if self._is_windows:
            if not self._alias:
                return False
            try:
                return self._mci(f"status {self._alias} mode") == "playing"
            except RuntimeError:
                return False
        try:
            import pygame  # type: ignore

            return bool(pygame.mixer.get_init() and pygame.mixer.music.get_busy())
        except ImportError:
            return False

    def stop(self) -> None:
        if self._is_windows:
            if self._alias:
                try:
                    self._mci(f"stop {self._alias}")
                    self._mci(f"close {self._alias}")
                except RuntimeError:
                    pass
                self._alias = None
            return
        try:
            import pygame  # type: ignore

            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
        except ImportError:
            pass


# --------------------------------------------------------------------------- #
# TTS helpers
# --------------------------------------------------------------------------- #
def _signed(value: int, unit: str) -> str:
    return f"{value:+d}{unit}"


async def _synthesize(text: str, voice: str, rate: int, pitch: int,
                      volume: int, out_path: str) -> None:
    communicate = edge_tts.Communicate(
        text,
        voice,
        rate=_signed(rate, "%"),
        pitch=_signed(pitch, "Hz"),
        volume=_signed(volume, "%"),
    )
    await communicate.save(out_path)


async def _fetch_voices() -> list[dict]:
    return await edge_tts.list_voices()


# --------------------------------------------------------------------------- #
# GUI
# --------------------------------------------------------------------------- #
class FilipinoTTSApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("760x560")
        self.minsize(620, 460)

        self.player = AudioPlayer()
        self.voices: dict[str, str] = dict(DEFAULT_VOICES)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="filipino_tts_"))
        self.last_audio: Path | None = None
        self.last_key: tuple | None = None  # settings used for last_audio
        self.busy = False

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._load_voices_async()

    # -- UI construction ---------------------------------------------------- #
    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        root = ttk.Frame(self, padding=12)
        root.pack(fill=tk.BOTH, expand=True)

        ttk.Label(root, text="Ilagay ang tekstong Filipino (Paste Filipino text):",
                  font=("Segoe UI", 10, "bold")).pack(anchor="w")

        self.text = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=12,
                                              font=("Segoe UI", 11), undo=True)
        self.text.pack(fill=tk.BOTH, expand=True, pady=(4, 10))
        self.text.insert("1.0", SAMPLE_TEXT)
        self._add_context_menu(self.text)

        # Voice row
        voice_row = ttk.Frame(root)
        voice_row.pack(fill=tk.X)
        ttk.Label(voice_row, text="Boses (Voice):").pack(side=tk.LEFT)
        self.voice_var = tk.StringVar(value=next(iter(self.voices)))
        self.voice_combo = ttk.Combobox(voice_row, textvariable=self.voice_var,
                                        values=list(self.voices), state="readonly",
                                        width=55)
        self.voice_combo.pack(side=tk.LEFT, padx=6, fill=tk.X, expand=True)
        self.all_langs_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(voice_row, text="Show all languages",
                        variable=self.all_langs_var,
                        command=self._refresh_voice_list).pack(side=tk.LEFT)

        # Sliders
        sliders = ttk.Frame(root)
        sliders.pack(fill=tk.X, pady=8)
        self.rate_var = self._slider(sliders, "Bilis / Speed (%)", -50, 100, 0, 0)
        self.pitch_var = self._slider(sliders, "Tono / Pitch (Hz)", -50, 50, 0, 1)
        self.volume_var = self._slider(sliders, "Lakas / Volume (%)", -50, 50, 0, 2)
        sliders.columnconfigure(1, weight=1)

        # Buttons
        btns = ttk.Frame(root)
        btns.pack(fill=tk.X, pady=(4, 6))
        self.play_btn = ttk.Button(btns, text="▶  Play", command=self.on_play)
        self.play_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(btns, text="■  Stop", command=self.on_stop)
        self.stop_btn.pack(side=tk.LEFT, padx=6)
        self.save_btn = ttk.Button(btns, text="💾  Save as MP3…", command=self.on_save)
        self.save_btn.pack(side=tk.LEFT)
        ttk.Button(btns, text="Clear", command=lambda: self.text.delete("1.0", tk.END)
                   ).pack(side=tk.RIGHT)

        # Status bar
        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(6, 2))
        self.status_var = tk.StringVar(value="Handa na (Ready).")
        ttk.Label(root, textvariable=self.status_var, foreground="#444").pack(anchor="w")

        self.bind("<Control-Return>", lambda e: self.on_play())
        self.bind("<Control-s>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.on_stop())

    def _slider(self, parent, label, lo, hi, init, row) -> tk.IntVar:
        var = tk.IntVar(value=init)
        ttk.Label(parent, text=label, width=20).grid(row=row, column=0, sticky="w")
        value_lbl = ttk.Label(parent, text=_signed(init, ""), width=5)
        scale = ttk.Scale(parent, from_=lo, to=hi, orient=tk.HORIZONTAL,
                          command=lambda v: (var.set(int(float(v))),
                                             value_lbl.config(text=_signed(var.get(), ""))))
        scale.set(init)
        scale.grid(row=row, column=1, sticky="ew", padx=6, pady=2)
        value_lbl.grid(row=row, column=2, sticky="e")
        ttk.Button(parent, text="Reset", width=6,
                   command=lambda: scale.set(init)).grid(row=row, column=3, padx=(6, 0))
        return var

    def _add_context_menu(self, widget: tk.Text) -> None:
        menu = tk.Menu(widget, tearoff=0)
        for label, seq in (("Cut", "<<Cut>>"), ("Copy", "<<Copy>>"), ("Paste", "<<Paste>>")):
            menu.add_command(label=label, command=lambda s=seq: widget.event_generate(s))
        menu.add_separator()
        menu.add_command(label="Select All",
                         command=lambda: widget.tag_add(tk.SEL, "1.0", tk.END))
        widget.bind("<Button-3>", lambda e: menu.tk_popup(e.x_root, e.y_root))

    # -- Voice list --------------------------------------------------------- #
    def _load_voices_async(self) -> None:
        def worker():
            try:
                voices = asyncio.run(_fetch_voices())
            except Exception:
                return  # keep the built-in Filipino voices
            self.after(0, lambda: self._store_voices(voices))

        threading.Thread(target=worker, daemon=True).start()

    def _store_voices(self, voices: list[dict]) -> None:
        self._all_voices = sorted(voices, key=lambda v: v["ShortName"])
        self._refresh_voice_list()

    def _refresh_voice_list(self) -> None:
        all_voices = getattr(self, "_all_voices", None)
        current_id = self.voices.get(self.voice_var.get())
        mapping: dict[str, str] = {}
        if all_voices:
            for v in all_voices:
                locale = v.get("Locale", "")
                if not self.all_langs_var.get() and not locale.startswith("fil"):
                    continue
                name = v["ShortName"].split("-")[-1].replace("Neural", "")
                label = f"{name} ({v.get('Gender', '?')}) – {locale}"
                mapping[label] = v["ShortName"]
        if not mapping:
            mapping = dict(DEFAULT_VOICES)
        self.voices = mapping
        self.voice_combo["values"] = list(mapping)
        # keep the previous selection if still available
        for label, vid in mapping.items():
            if vid == current_id:
                self.voice_var.set(label)
                break
        else:
            self.voice_var.set(next(iter(mapping)))

    # -- Actions ------------------------------------------------------------ #
    def _current_settings(self) -> tuple | None:
        text = self.text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning(APP_TITLE, "Walang teksto. Please paste some text first.")
            return None
        voice = self.voices.get(self.voice_var.get(), "fil-PH-BlessicaNeural")
        return (text, voice, self.rate_var.get(), self.pitch_var.get(),
                self.volume_var.get())

    def _set_busy(self, busy: bool, msg: str = "") -> None:
        self.busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        for b in (self.play_btn, self.save_btn):
            b.config(state=state)
        if busy:
            self.progress.start(12)
        else:
            self.progress.stop()
        if msg:
            self.status_var.set(msg)

    def _generate(self, settings: tuple, out_path: Path, on_done) -> None:
        """Synthesize in a background thread, then call on_done(path) on the UI thread."""
        if settings == self.last_key and self.last_audio and self.last_audio.exists():
            on_done(self.last_audio, reused=True)
            return

        self._set_busy(True, "Gumagawa ng audio… (Generating audio…)")

        def worker():
            try:
                asyncio.run(_synthesize(*settings, str(out_path)))
            except Exception as exc:  # network errors, bad voice, etc.
                self.after(0, lambda: self._on_error(exc))
                return
            self.after(0, lambda: self._after_generate(settings, out_path, on_done))

        threading.Thread(target=worker, daemon=True).start()

    def _after_generate(self, settings, out_path: Path, on_done) -> None:
        self._set_busy(False)
        self.last_key = settings
        self.last_audio = out_path
        on_done(out_path, reused=False)

    def _on_error(self, exc: Exception) -> None:
        self._set_busy(False, "May error (Error).")
        messagebox.showerror(
            APP_TITLE,
            "Hindi nagawa ang audio. Make sure you are connected to the internet.\n\n"
            f"Details: {exc}",
        )

    def on_play(self) -> None:
        if self.busy:
            return
        settings = self._current_settings()
        if not settings:
            return
        self.player.stop()
        out = self.temp_dir / f"tts_{uuid.uuid4().hex[:8]}.mp3"

        def done(path: Path, reused: bool) -> None:
            try:
                self.player.play(str(path))
            except Exception as exc:
                self._on_error(exc)
                return
            self.status_var.set("Nagpe-play… (Playing…)")
            self._watch_playback()

        self._generate(settings, out, done)

    def _watch_playback(self) -> None:
        if self.player.is_playing():
            self.after(300, self._watch_playback)
        elif not self.busy and self.status_var.get().startswith("Nagpe-play"):
            self.status_var.set("Tapos na (Finished).")

    def on_stop(self) -> None:
        self.player.stop()
        if not self.busy:
            self.status_var.set("Itinigil (Stopped).")

    def on_save(self) -> None:
        if self.busy:
            return
        settings = self._current_settings()
        if not settings:
            return
        target = filedialog.asksaveasfilename(
            title="Save MP3",
            defaultextension=".mp3",
            filetypes=[("MP3 audio", "*.mp3")],
            initialfile="filipino_tts.mp3",
        )
        if not target:
            return
        target_path = Path(target)
        tmp = self.temp_dir / f"tts_{uuid.uuid4().hex[:8]}.mp3"

        def done(path: Path, reused: bool) -> None:
            try:
                target_path.write_bytes(path.read_bytes())
            except OSError as exc:
                self._on_error(exc)
                return
            self.status_var.set(f"Na-save: {target_path}")
            messagebox.showinfo(APP_TITLE, f"Na-save ang MP3 (Saved):\n{target_path}")

        self._generate(settings, tmp, done)

    def _on_close(self) -> None:
        self.player.stop()
        for f in self.temp_dir.glob("*.mp3"):
            try:
                f.unlink()
            except OSError:
                pass
        try:
            self.temp_dir.rmdir()
        except OSError:
            pass
        self.destroy()


def main() -> None:
    if sys.platform.startswith("win"):
        try:  # crisp text on high-DPI screens
            import ctypes

            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
        except Exception:
            pass
    app = FilipinoTTSApp()
    app.mainloop()


if __name__ == "__main__":
    main()
