import re
import unicodedata

MAX_TEXT_CHARS = 100_000
MIN_TEXT_CHARS = 50  # fewer letters/digits than this = treated as "no text"

_BULLETS = "•▪●◦‣∙➢➤►▶■□◆◇✓✔"
_BULLET_AT_LINE_START = re.compile(rf"^[ \t]*[{_BULLETS}][ \t]*", re.MULTILINE)
_INVISIBLE = re.compile("[\u200b\u200c\u200d\u2060\ufeff]")
_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def clean_text(raw):
    """Normalizes raw extracted text so the NLP steps work on consistent input."""
    text = unicodedata.normalize("NFKC", raw or "")  # ligatures (fi), nbsp, full-width chars
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\x0b", "\n").replace("\x0c", "\n")
    text = _INVISIBLE.sub("", text)
    text = _CONTROL.sub("", text)
    text = _BULLET_AT_LINE_START.sub("- ", text)  # one bullet style
    text = re.sub(r"[ \t]+", " ", text)  # collapse spaces and tabs
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()  # max one blank line
    return text[:MAX_TEXT_CHARS]


def has_enough_text(text):
    return sum(ch.isalnum() for ch in text) >= MIN_TEXT_CHARS