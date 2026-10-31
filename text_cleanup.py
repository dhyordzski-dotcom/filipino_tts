"""
Prepare pasted Filipino text so the neural voice reads it more naturally.

The Edge fil-PH voices already sound good on clean prose. Most robotic-sounding
output comes from the *input*: line breaks in the middle of sentences (copied
from PDFs, chats or websites), abbreviations read letter by letter, symbols,
emojis, URLs and bullet characters. This module fixes those things and leaves
the wording alone.
"""

from __future__ import annotations

import re

# Abbreviations common in Filipino writing -> how they are spoken.
# Matched case-sensitively, as whole words followed by a period.
ABBREVIATIONS = {
    "Gng.": "Ginang",
    "Bb.": "Binibini",
    "Dr.": "Doktor",
    "Dra.": "Doktora",
    "Atty.": "Attorney",
    "Engr.": "Engineer",
    "Kgg.": "Kagalang-galang",
    "Pres.": "Presidente",
    "Sen.": "Senador",
    "Kon.": "Konsehal",
    "Gob.": "Gobernador",
    "Brgy.": "Barangay",
    "Bgy.": "Barangay",
    "Sto.": "Santo",
    "Sta.": "Santa",
    "Sr.": "Senior",
    "Jr.": "Junior",
    "atbp.": "at iba pa",
    "Atbp.": "At iba pa",
    "hal.": "halimbawa",
    "Hal.": "Halimbawa",
    "blg.": "bilang",
    "Blg.": "Bilang",
    "pp.": "pahina",
}

_ABBR_RE = re.compile(
    r"(?<![\w.])(" + "|".join(re.escape(a) for a in
                              sorted(ABBREVIATIONS, key=len, reverse=True)) + r")"
    r"(?=\s|$)"
)

_URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_HASHTAG_RE = re.compile(r"(?<!\w)#(\w+)")
_BULLET_RE = re.compile(r"^[ \t]*(?:[-*•●▪◦‣–—]+|\d+[.)])[ \t]+", re.MULTILINE)
_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "‍️]+"
)
_PESO_RE = re.compile(r"(?:₱|\bPHP\s?|\bPhp\s?)(\d[\d,]*(?:\.\d+)?)")
_ITEM = "\x00"
_SENTENCE_END = (".", "!", "?", ":", ";", "…", '"', "”", "'", ")")


def clean_filipino_text(text: str) -> str:
    """Return text that reads more naturally when spoken."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")

    # Symbols / web junk that would be read out literally.
    t = _URL_RE.sub("", t)
    t = _EMAIL_RE.sub("", t)
    t = _EMOJI_RE.sub("", t)
    t = _HASHTAG_RE.sub(r"\1", t)
    t = _BULLET_RE.sub(_ITEM, t)  # remember where list items start
    t = _PESO_RE.sub(lambda m: f"{m.group(1)} piso", t)
    t = re.sub(r"\s*&\s*", " at ", t)
    t = re.sub(r"(\d)\s*%", r"\1 porsiyento", t)
    t = re.sub(r"(?<=[A-Za-z])/(?=[A-Za-z])", " o ", t)  # at/o -> "at o"

    # Repeated punctuation ("Talaga!!!", "ano??", "hmm.....") -> one mark.
    t = re.sub(r"([!?])[!?]+", r"\1", t)
    t = re.sub(r"\.{4,}", "...", t)

    t = _ABBR_RE.sub(lambda m: ABBREVIATIONS[m.group(1)], t)

    # Paragraphs: blank lines separate them. Inside a paragraph, single line
    # breaks are usually just wrapping, so join them with a space. Lines that
    # don't end in punctuation but start a new paragraph get a period so the
    # voice pauses instead of running sentences together.
    paragraphs = []
    for para in re.split(r"\n\s*\n", t):
        lines = [ln.strip() for ln in para.split("\n") if ln.strip()]
        if not lines:
            continue
        joined = lines[0].lstrip(_ITEM)
        prev = joined
        for ln in lines[1:]:
            # A short line without end punctuation followed by a capitalised
            # line is probably a heading / list item: keep a pause.
            is_item = ln.startswith(_ITEM)
            ln = ln.lstrip(_ITEM)
            if not joined.endswith(_SENTENCE_END) and (
                    is_item or (ln[:1].isupper() and len(prev) < 60)):
                joined += "."
            joined += " " + ln
            prev = ln
        if not joined.endswith(_SENTENCE_END):
            joined += "."
        paragraphs.append(joined)

    t = "\n\n".join(paragraphs)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\s+([,.!?;:])", r"\1", t)
    t = re.sub(r"([,.!?;:])(?=[^\s\d.,!?;:\"'”)])", r"\1 ", t)
    return t.strip()
