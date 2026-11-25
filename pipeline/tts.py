"""Text-to-speech with word timings.

Primary: Microsoft Edge neural voices via `edge-tts` (free, no key).
Fallback: espeak-ng (robotic, only for offline testing) with estimated timings.
"""
import asyncio
import shutil
import subprocess
from pathlib import Path

DEFAULT_VOICE = "en-US-AndrewMultilingualNeural"


def _probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


async def _edge(text: str, voice: str, rate: str, out_mp3: Path):
    import edge_tts
    words = []
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return words


def _espeak(text: str, out_mp3: Path):
    wav = out_mp3.with_suffix(".wav")
    subprocess.run(["espeak-ng", "-v", "en-us", "-s", "165", "-w", str(wav), text], check=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ar", "24000",
                    "-ac", "1", str(out_mp3)], check=True)
    wav.unlink()
    dur = _probe_duration(out_mp3)
    tokens = text.split()
    weights = [len(t) + 2 for t in tokens]
    total = sum(weights)
    t, words = 0.0, []
    for tok, w in zip(tokens, weights):
        d = dur * w / total
        words.append((t, t + d, tok))
        t += d
    return words


def synthesize(text: str, out_mp3: Path, voice: str = DEFAULT_VOICE, rate: str = "+0%"):
    """Return (duration_seconds, [(start, end, word), ...])."""
    words = None
    for attempt in range(3):
        try:
            words = asyncio.run(_edge(text, voice, rate, out_mp3))
            if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                break
        except Exception as e:  # network hiccup → retry, then fallback
            print(f"  edge-tts attempt {attempt + 1} failed: {e.__class__.__name__}")
            words = None
    if not words:
        if not shutil.which("espeak-ng"):
            raise RuntimeError("No TTS engine available")
        print("  ! falling back to espeak-ng (test quality only)")
        words = _espeak(text, out_mp3)
    return _probe_duration(out_mp3), words
