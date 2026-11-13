"""English voiceover for the Reel. Primary: Microsoft Edge neural voices (edge-tts, free, no key).
Fallback: Google TTS (gTTS, Indian English). If both fail, the Reel is rendered with music only."""
import asyncio, logging, subprocess
from pathlib import Path
import numpy as np

log = logging.getLogger("feedbot")
SR = 44100


def _edge(text, voice, path):
    import edge_tts
    asyncio.run(edge_tts.Communicate(text, voice, rate="+4%").save(str(path)))


def _gtts(text, path):
    from gtts import gTTS
    gTTS(text, lang="en", tld="co.in").save(str(path))


def synth(text, voice, path):
    """Write an MP3 for `text`; returns a mono float32 array at 44.1 kHz, or None."""
    if not text or voice == "none":
        return None
    path = Path(path)
    for name, fn in (("edge-tts", lambda: _edge(text, voice, path)), ("gTTS", lambda: _gtts(text, path))):
        try:
            fn()
            raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", str(path), "-f", "s16le", "-ac", "1", "-ar", str(SR), "-"],
                                 capture_output=True, check=True).stdout
            a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
            if len(a) > SR * 0.3:
                return a
        except Exception as ex:
            log.warning("voice %s failed: %s", name, ex)
    return None
