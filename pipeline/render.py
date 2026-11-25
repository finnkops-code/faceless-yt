"""Render one video from a script JSON into output/<slug>/.

Usage: python -m pipeline.render content/queue/<slug>.json
"""
import json
import math
import random
import re
import subprocess
import sys
from pathlib import Path

from . import tts, visuals
from .thumbnail import make_thumbnail

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
PAUSE = 0.35          # silence after each section
SHOT = 4.0            # target seconds per shot (keeps it moving)
GRAPHIC_MIN = 6.5     # seconds a chart/card stays on screen


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *map(str, args)], check=True)


def ts(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 \
        else f"{sec // 60}:{sec % 60:02d}"


def ass_time(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def caption_chunks(words, offset):
    """Group word timings into short on-screen captions."""
    chunks, cur = [], []
    for s, e, w in words:
        cur.append((s, e, w))
        if len(cur) >= 5 or re.search(r"[.,!?;:]$", w):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    out = []
    for c in chunks:
        text = " ".join(w for _, _, w in c)
        out.append((offset + c[0][0], offset + c[-1][1] + 0.08, text))
    return out


def write_ass(cues, path: Path):
    head = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,4,1,2,160,160,95,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for i, (s, e, t) in enumerate(cues):
        if i + 1 < len(cues):
            e = min(e, cues[i + 1][0])
        t = t.replace("{", "(").replace("}", ")")
        lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{t}")
    path.write_text(head + "\n".join(lines) + "\n", encoding="utf-8")


def _shots(sec, n, work, used, credits, slug, i):
    """Footage pool for a section: stock video + photos, interleaved."""
    vids = visuals.fetch_broll(sec.get("visuals", []), ROOT / "cache", used, n)
    imgs = visuals.fetch_photos(sec.get("images", []), ROOT / "cache", used,
                                max(1, n // 2) if sec.get("images") else 0, credits)
    pool = []
    for k in range(max(len(vids), len(imgs))):
        if k < len(imgs):
            pool.append(("img", imgs[k]))
        if k < len(vids):
            pool.append(("vid", vids[k]))
    return pool


def _render_shot(kind, src, dest, dur, rnd, key, reuse=False):
    if kind == "img":
        visuals.ken_burns(src, dest, dur, key)
        return
    length = visuals.probe(src)
    start = rnd.uniform(0, max(0, length - dur - 0.5)) if reuse and length > dur + 1 else 0.0
    if length and length < dur:
        tmp = dest.with_name("slow_" + dest.name)
        ff("-i", src, "-an", "-vf", f"setpts={dur / length + 0.05:.3f}*PTS", "-c:v", "libx264",
           "-preset", "veryfast", tmp)
        src = tmp
    visuals.normalize_clip(src, dest, dur, start)


def section_visuals(sec, i, seg, work, used, credits, slug):
    """Always moving imagery. Charts/cards are overlaid on blurred footage, never on a flat screen."""
    rnd = random.Random(f"{slug}{i}")
    graphic = None
    if sec.get("chart"):
        graphic = work / f"chart{i:02d}.png"
        visuals.render_chart(sec["chart"], graphic)
    elif sec.get("title_card"):
        graphic = work / f"card{i:02d}.png"
        visuals.render_title_card(sec["title_card"], graphic, sec.get("kicker", ""))

    g_dur = min(seg, max(GRAPHIC_MIN, seg * 0.6)) if graphic else 0
    lead = seg - g_dur                       # footage before the graphic appears
    n = max(1, math.ceil(lead / SHOT)) if lead > 1.5 else 0
    if lead and n == 0:                      # too short for a separate shot → graphic gets it all
        g_dur, lead = seg, 0
    pool = _shots(sec, n + (1 if graphic else 0), work, used, credits, slug, i)
    if not pool:                             # nothing found → abstract background
        png = work / f"bg{i:02d}.png"
        visuals.fallback_background(png, f"{slug}{i}")
        pool = [("img", png)]

    out = []
    for k in range(n):
        kind, src = pool[k % len(pool)]
        c = work / f"v{i:02d}_{k}.mp4"
        _render_shot(kind, src, c, lead / n, rnd, f"{slug}{i}{k}", reuse=k >= len(pool))
        out.append(c)
    if graphic:
        kind, src = pool[n % len(pool)]
        bg = work / f"g{i:02d}_bg.mp4"
        _render_shot(kind, src, bg, g_dur, rnd, f"{slug}{i}g", reuse=n >= len(pool))
        c = work / f"v{i:02d}_g.mp4"
        visuals.overlay_on(bg, graphic, c, g_dur)
        out.append(c)
    return out


def build(script_path: Path, out_root: Path = ROOT / "output"):
    spec = json.loads(Path(script_path).read_text())
    slug = spec["slug"]
    out = out_root / slug
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    voice = spec.get("voice", tts.DEFAULT_VOICE)
    used, clips, audio_parts, cues, chapters, credits = set(), [], [], [], [], []
    t = 0.0
    rnd = random.Random(slug)

    for i, sec in enumerate(spec["sections"]):
        print(f"[{slug}] section {i + 1}/{len(spec['sections'])}")
        mp3 = work / f"s{i:02d}.mp3"
        dur, words = tts.synthesize(sec["narration"], mp3, voice=voice)
        seg = dur + PAUSE
        wav = work / f"s{i:02d}.wav"
        ff("-i", mp3, "-af", f"apad=pad_dur={PAUSE}", "-ar", "48000", "-ac", "2", wav)
        audio_parts.append(wav)
        cues += caption_chunks(words, t)
        if sec.get("chapter"):
            chapters.append((t, sec["chapter"]))

        clips += section_visuals(sec, i, seg, work, used, credits, slug)
        t += seg

    # --- concat video
    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    silent = work / "video_silent.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", silent)

    # --- narration track
    alst = work / "audio.txt"
    alst.write_text("".join(f"file '{a.resolve()}'\n" for a in audio_parts))
    narr = work / "narration.wav"
    ff("-f", "concat", "-safe", "0", "-i", alst, "-af", "loudnorm=I=-15:TP=-1.5:LRA=11", narr)

    ass = out / "captions.ass"
    write_ass(cues, ass)
    srt = out / "captions.srt"
    srt.write_text("".join(
        f"{n + 1}\n{_srt(s)} --> {_srt(e)}\n{txt}\n\n" for n, (s, e, txt) in enumerate(cues)))

    music = sorted((ROOT / "assets" / "music").glob("*.mp3")) if (ROOT / "assets" / "music").exists() else []
    final = out / "video.mp4"
    vf = f"ass={ass}:fontsdir={FONTS}" if spec.get("burn_captions", True) else "null"
    if music:
        track = rnd.choice(music)
        ff("-i", silent, "-i", narr, "-stream_loop", "-1", "-i", track,
           "-filter_complex",
           f"[0:v]{vf}[v];[2:a]volume=0.07,afade=t=in:d=2[m];"
           f"[1:a][m]amix=inputs=2:duration=first:dropout_transition=0[a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", final)
    else:
        ff("-i", silent, "-i", narr, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", final)

    # --- thumbnail + metadata
    thumb_src = next((c for c in clips if "_0" in c.name), clips[0])
    make_thumbnail(spec.get("thumbnail", {}), thumb_src, out / "thumbnail.jpg", FONTS)

    desc = spec["description"].strip()
    if len(chapters) >= 3 and chapters[0][0] == 0:
        desc += "\n\nChapters\n" + "\n".join(f"{ts(s)} {name}" for s, name in chapters)
    if credits:
        desc += "\n\nImage credits\n" + "\n".join(f"- {c}" for c in dict.fromkeys(credits))
    if spec.get("sources"):
        desc += "\n\nSources\n" + "\n".join(f"- {s}" for s in spec["sources"])
    desc += "\n\nNarration uses a synthetic voice. Research, script and data visuals are produced for this channel."
    meta = {
        "title": spec["title"][:100],
        "description": desc[:4900],
        "tags": spec.get("tags", [])[:30],
        "category_id": spec.get("category_id", "27"),
        "publish_at": spec.get("publish_at"),
        "duration": round(t, 1),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"[{slug}] done → {final} ({t / 60:.1f} min)")
    return out


def _srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


if __name__ == "__main__":
    build(Path(sys.argv[1]))
