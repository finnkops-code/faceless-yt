"""Text-to-speech with word timings.

Engines (in order):
  kokoro — Kokoro-82M (Apache-2.0, open source, runs on CPU). Natural, documentary-style voice.
  edge   — Microsoft Edge neural voices via edge-tts (free, needs network).
  espeak — robotic, offline test fallback only.
Pick with env TTS_ENGINE (default: kokoro).
"""
import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = Path(os.environ.get("KOKORO_DIR", ROOT / "models"))
DEFAULT_VOICE = os.environ.get("TTS_VOICE", "bm_fable")
SENTENCE_GAP = 0.14
_kokoro = None


def _probe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(path)],
                         capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _estimate_words(text, start, dur):
    tokens = text.split()
    weights = [len(t) + 2 for t in tokens]
    total = sum(weights) or 1
    t, words = start, []
    for tok, w in zip(tokens, weights):
        d = dur * w / total
        words.append((t, t + d, tok))
        t += d
    return words


def _sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


# ---------------- Kokoro ----------------
def _kokoro_engine():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        _kokoro = Kokoro(str(MODELS / "kokoro-v1.0.onnx"), str(MODELS / "voices-v1.0.bin"))
    return _kokoro


def _kokoro_tts(text, voice, out_mp3: Path, speed=float(os.environ.get('TTS_SPEED', '0.94'))):
    import numpy as np
    import soundfile as sf
    k = _kokoro_engine()
    lang = "en-gb" if voice.startswith("b") else "en-us"
    chunks, words, t, sr = [], [], 0.0, 24000
    for s in _sentences(text):
        audio, sr = k.create(s, voice=voice, speed=speed, lang=lang)
        d = len(audio) / sr
        words += _estimate_words(s, t, d)
        gap = np.zeros(int(SENTENCE_GAP * sr), dtype=audio.dtype)
        chunks += [audio, gap]
        t += d + SENTENCE_GAP
    wav = out_mp3.with_suffix(".k.wav")
    sf.write(wav, np.concatenate(chunks), sr)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-b:a", "192k",
                    str(out_mp3)], check=True)
    wav.unlink()
    return words


# ---------------- Edge ----------------
async def _edge(text, voice, out_mp3: Path):
    import edge_tts
    words = []
    comm = edge_tts.Communicate(text, voice, boundary="WordBoundary")
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                s = chunk["offset"] / 1e7
                words.append((s, s + chunk["duration"] / 1e7, chunk["text"]))
    return words


def _espeak(text, out_mp3: Path):
    wav = out_mp3.with_suffix(".e.wav")
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "160", "-w", str(wav), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), str(out_mp3)], check=True)
    wav.unlink()
    return _estimate_words(text, 0, _probe_duration(out_mp3))


def synthesize(text: str, out_mp3: Path, voice: str = DEFAULT_VOICE):
    """Return (duration_seconds, [(start, end, word), ...])."""
    engine = os.environ.get("TTS_ENGINE", "kokoro")
    order = {"kokoro": ["kokoro", "edge", "espeak"], "edge": ["edge", "kokoro", "espeak"]}.get(
        engine, ["kokoro", "edge", "espeak"])
    for eng in order:
        try:
            if eng == "kokoro" and (MODELS / "kokoro-v1.0.onnx").exists():
                v = voice if "_" in voice else DEFAULT_VOICE
                words = _kokoro_tts(text, v, out_mp3)
            elif eng == "edge":
                v = voice if "Neural" in voice else "en-US-AndrewMultilingualNeural"
                words = asyncio.run(_edge(text, v, out_mp3))
            elif eng == "espeak" and shutil.which("espeak-ng"):
                print("  ! espeak fallback (test quality only)")
                words = _espeak(text, out_mp3)
            else:
                continue
            if out_mp3.exists() and out_mp3.stat().st_size > 1000 and words:
                return _probe_duration(out_mp3), words
        except Exception as e:
            print(f"  {eng} failed: {e.__class__.__name__}: {str(e)[:120]}")
    raise RuntimeError("No TTS engine succeeded")
