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

from . import brand, tts, visuals
from .thumbnail import make_thumbnail, make_variants

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


def srt_cues(words, offset, max_chars=84, max_dur=6.0):
    """Readable subtitles: up to 2 lines of ~42 chars, broken at sentence/clause ends."""
    out, cur = [], []
    def flush():
        if cur:
            from .numfmt import digits
            txt = digits(" ".join(w for _, _, w in cur))
            out.append((offset + cur[0][0], offset + cur[-1][1] + 0.1, _two_lines(txt)))
            cur.clear()
    for s_, e_, w in words:
        if cur and (len(" ".join(x for _, _, x in cur)) + len(w) + 1 > max_chars or e_ - cur[0][0] > max_dur):
            flush()
        cur.append((s_, e_, w))
        if re.search(r"[.!?]$", w) or (re.search(r"[,;:]$", w) and len(" ".join(x for _, _, x in cur)) > 40):
            flush()
    flush()
    return out


def _two_lines(txt, width=42):
    if len(txt) <= width:
        return txt
    mid = len(txt) // 2
    cut = min((i for i, c in enumerate(txt) if c == " "), key=lambda i: abs(i - mid), default=mid)
    return txt[:cut] + "\n" + txt[cut + 1:]


def write_srt(cues, path: Path):
    lines = []
    for n, (s_, e_, txt) in enumerate(cues):
        if n + 1 < len(cues):
            e_ = min(e_, cues[n + 1][0] - 0.02)
        lines.append(f"{n + 1}\n{_srt(s_)} --> {_srt(e_)}\n{txt}\n")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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


FALLBACK_IMAGES = []


def _shots(sec, n, work, used, credits, slug, i):
    """Footage pool for a section: on-topic stock video + photos, interleaved.
    If strict stock matching finds too little, fill with real topic photos (Commons) instead of filler."""
    vids = visuals.fetch_broll(sec.get("visuals", []), ROOT / "cache", used, n)
    imgs = visuals.fetch_photos(sec.get("images", []), ROOT / "cache", used,
                                max(1, n // 2) if sec.get("images") else 0, credits)
    short = n - len(vids) - len(imgs)
    if short > 0 and FALLBACK_IMAGES:
        imgs += visuals.fetch_photos(FALLBACK_IMAGES, ROOT / "cache", used, short, credits)
    pool = []
    for k in range(max(len(vids), len(imgs))):
        if k < len(imgs):
            pool.append(("img", imgs[k]))
        if k < len(vids):
            pool.append(("vid", vids[k]))
    return pool


def _render_shot(kind, src, dest, dur, rnd, key, reuse=False, size=(visuals.W, visuals.H)):
    if kind == "img":
        visuals.ken_burns(src, dest, dur, key, size=size)
        return
    length = visuals.probe(src)
    start = rnd.uniform(0, max(0, length - dur - 0.5)) if reuse and length > dur + 1 else 0.0
    if length and length < dur:
        tmp = dest.with_name("slow_" + dest.name)
        ff("-i", src, "-an", "-vf", f"setpts={dur / length + 0.05:.3f}*PTS", "-c:v", "libx264",
           "-preset", "veryfast", tmp)
        src = tmp
    visuals.normalize_clip(src, dest, dur, start, size=size)


def overlay_seq(bg_clip, frames_dir, dest, duration):
    """Blurred footage + animated RGBA frame sequence (last frame held)."""
    n = len(list(frames_dir.glob("f*.png")))
    hold = max(0.1, duration - n / visuals.FPS)
    ff("-i", bg_clip, "-framerate", visuals.FPS, "-i", frames_dir / "f%03d.png",
       "-filter_complex",
       f"[0:v]boxblur=22:2,eq=brightness=-0.10:saturation=0.7[bg];"
       f"[1:v]format=rgba,tpad=stop_mode=clone:stop_duration={hold:.3f}[fg];"
       f"[bg][fg]overlay=0:0:eof_action=repeat,fps={visuals.FPS},setsar=1[v]",
       "-map", "[v]", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "19", "-pix_fmt", "yuv420p", dest)


def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def phrase_time(words, phrase):
    """Start time of `phrase` in the section's word timings (None if not found)."""
    target = [_norm(x) for x in phrase.split() if _norm(x)]
    toks = [_norm(w) for _, _, w in words]
    k = min(3, len(target))
    for j in range(len(toks) - k + 1):
        if toks[j:j + k] == target[:k]:
            return words[j][0]
    return None


def finish_section(clips, sec, i, seg, words, work, chapter_no):
    """Concat shots, then layer chapter label + timed stat callouts on top."""
    lst = work / f"s{i:02d}_clips.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    base = work / f"s{i:02d}_base.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base)
    layers = []  # (png, start, end, slide)
    if sec.get("chapter") and chapter_no:
        png = work / f"chap{i:02d}.png"
        brand.chapter_png(chapter_no, sec["chapter"], png)
        layers.append((png, 0.25, min(seg - 0.2, 4.0), False))
    cos = sec.get("callouts", [])
    busy_until = 0.0
    for k, co in enumerate(cos):
        st = phrase_time(words, co.get("at", "")) if co.get("at") else None
        if st is None:
            st = seg * (k + 0.5) / (len(cos) + 0.5)
        st = max(st, busy_until + 0.15)
        en = min(seg - 0.15, st + float(co.get("hold", 3.6)))
        if en - st < 1.2:
            continue
        png = work / f"co{i:02d}_{k}.png"
        brand.callout_png(co["text"], co.get("label", ""), png)
        layers.append((png, st, en, True))
        busy_until = en
    final = work / f"sec{i:02d}.mp4"
    if not layers:
        base.rename(final)
        return final
    args, chains, prev = ["-i", base], [], "[0:v]"
    for n, (png, st, en, slide) in enumerate(layers, start=1):
        args += ["-loop", "1", "-t", f"{seg:.3f}", "-i", png]
        d = en - st
        chains.append(f"[{n}:v]format=rgba,fade=in:st={st:.2f}:d=0.35:alpha=1,"
                      f"fade=out:st={en - 0.35:.2f}:d=0.35:alpha=1[l{n}]")
        x = f"'if(lt(t,{st:.2f}+0.4),-60+60*(t-{st:.2f})/0.4,0)'" if slide else "0"
        chains.append(f"{prev}[l{n}]overlay=x={x}:y=0:enable='between(t,{st:.2f},{en:.2f})'[o{n}]")
        prev = f"[o{n}]"
    ff(*args, "-filter_complex", ";".join(chains), "-map", prev, "-t", f"{seg:.3f}",
       "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", final)
    return final


def section_visuals(sec, i, seg, work, used, credits, slug):
    """Always moving imagery. Charts/cards are overlaid on blurred footage, never on a flat screen."""
    rnd = random.Random(f"{slug}{i}")
    graphic = None
    chart_dir = None
    if sec.get("chart"):
        chart_dir = work / f"chart{i:02d}"
        brand.chart_frames(sec["chart"], chart_dir)
        graphic = chart_dir / "f000.png"
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
        if chart_dir:
            overlay_seq(bg, chart_dir, c, g_dur)
        else:
            visuals.overlay_on(bg, graphic, c, g_dur)
        out.append(c)
    raw = [(k, s_) for k, s_ in pool if k == "img"] + [(k, s_) for k, s_ in pool if k == "vid"]
    return out, raw


def build(script_path: Path, out_root: Path = ROOT / "output"):
    spec = json.loads(Path(script_path).read_text())
    slug = spec["slug"]
    out = out_root / slug
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)
    voice = spec.get("voice", tts.DEFAULT_VOICE)
    used, clips, audio_parts, cues, chapters, credits = set(), [], [], [], [], []
    subs = []
    t = 0.0
    rnd = random.Random(slug)

    chapter_no = 0
    thumb_pool = []
    FALLBACK_IMAGES[:] = spec.get("fallback_images", [])
    if spec.get("thumbs_only"):              # new A/B/C thumbnails for an already-published video
        photos = visuals.fetch_photos(spec.get("fallback_images", []), ROOT / "cache", set(), 10, [])
        from .thumbnail import contact_sheet
        contact_sheet(photos, out / "photos.jpg")
        make_variants(spec.get("thumbnail", {}), photos, out, FONTS)
        return out
    if spec.get("shorts_only"):              # Shorts for an already-published long video
        from .music import pick_track
        from .shorts import build_short
        track, mc = pick_track(slug + "shorts")
        for k, sh in enumerate(spec.get("shorts", [])[:3]):
            try:
                build_short(sh, k, spec, out, [mc] if mc else [], track)
            except Exception as e:
                print(f"[{slug}] short {k + 1} failed: {e}")
        return out
    for i, sec in enumerate(spec["sections"]):
        print(f"[{slug}] section {i + 1}/{len(spec['sections'])}")
        mp3 = work / f"s{i:02d}.mp3"
        dur, words = tts.synthesize(sec["narration"], mp3, voice=voice)
        seg = dur + PAUSE
        wav = work / f"s{i:02d}.wav"
        ff("-i", mp3, "-af", f"apad=pad_dur={PAUSE}", "-ar", "48000", "-ac", "2", wav)
        audio_parts.append(wav)
        cues += caption_chunks(words, t)
        subs += srt_cues(words, t)
        if sec.get("chapter"):
            chapters.append((t, sec["chapter"]))
            chapter_no += 1
        shots, raw = section_visuals(sec, i, seg, work, used, credits, slug)
        thumb_pool += raw
        clips.append(finish_section(shots, sec, i, seg, words, work,
                                    chapter_no if (sec.get("chapter") and i > 0) else 0))
        t += seg
        if i == 0 and spec.get("ident", True):
            idc = work / "ident.mp4"
            brand.ident_clip(idc, 2.6)
            sil = work / "ident.wav"
            ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "2.6", sil)
            clips.append(idc)
            audio_parts.append(sil)
            chapters = [(c0, n0) for c0, n0 in chapters]
            t += 2.6

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
    write_srt(subs, out / "captions.srt")

    from .music import pick_track
    track, music_credit = pick_track(slug)
    music = [track] if track else []
    if music_credit:
        credits.append(music_credit)
    final = out / "video.mp4"
    vf = f"ass={ass}:fontsdir={FONTS}" if spec.get("burn_captions", False) else "null"
    if music:
        ff("-i", silent, "-i", narr, "-stream_loop", "-1", "-i", track,
           "-filter_complex",
           f"[0:v]{vf}[v];[2:a]aresample=48000,volume=0.22,afade=t=in:d=2[m];"
           f"[1:a]asplit=2[n1][n2];[m][n2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
           f"[n1][md]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[a]",
           "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", final)
    else:
        ff("-i", silent, "-i", narr, "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
           "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", final)

    # --- thumbnail + metadata
    photos = [p for k, p in thumb_pool if k == "img"] + [p for k, p in thumb_pool if k == "vid"] or [clips[0]]
    all_callouts = [c for s in spec["sections"] for c in s.get("callouts", [])]
    big = sorted(all_callouts, key=lambda c: (("billion" in c.get("text", "")) + ("$" in c.get("text", ""))),
                 reverse=True)[:1]
    make_variants(spec.get("thumbnail", {}), photos, out, FONTS, callouts=big)

    desc = spec["description"].strip()
    if len(chapters) >= 3 and chapters[0][0] == 0:
        desc += "\n\nChapters\n" + "\n".join(f"{ts(s)} {name}" for s, name in chapters)
    if spec.get("sources"):
        desc += "\n\nSources\n" + "\n".join(f"- {s}" for s in spec["sources"])
    desc += compact_credits(credits)
    desc += "\n\nResearch, script and data visuals by Price Tag Physics. Narration uses a synthetic voice."
    meta = {
        "title": spec["title"][:100],
        "description": desc[:4900],
        "tags": spec.get("tags", [])[:30],
        "category_id": spec.get("category_id", "27"),
        "publish_at": spec.get("publish_at"),
        "duration": round(t, 1),
        "pinned_comment": spec.get("pinned_comment",
                                   "Which company should we break down next? Drop your pick below. We read every "
                                   "comment, and the most-requested companies get their own full breakdown."),
    }
    (out / "metadata.json").write_text(json.dumps(meta, indent=2))

    # --- vertical Shorts (max 3); a failing short never blocks the long video
    from .shorts import build_short
    for k, sh in enumerate(spec.get("shorts", [])[:3]):
        try:
            build_short(sh, k, spec, out, credits, track)
        except Exception as e:
            print(f"[{slug}] short {k + 1} failed: {e}")
    print(f"[{slug}] done → {final} ({t / 60:.1f} min)")
    return out


def compact_credits(credits):
    """Short attribution block: music line + photographers grouped by licence (YouTube 5000-char limit)."""
    import re as _re
    music = [c for c in credits if c.startswith("Music:")]
    by_lic = {}
    for c in dict.fromkeys(credits):
        if c.startswith("Music:"):
            continue
        m = _re.match(r".* by (.+?), ([^,]+), via Wikimedia Commons$", c)
        if m:
            by_lic.setdefault(m.group(2).strip(), []).append(m.group(1).strip()[:40])
    out = ""
    if music:
        out += "\n\n" + music[0]
    if by_lic:
        parts = [f"{lic}: " + ", ".join(dict.fromkeys(a)) for lic, a in by_lic.items()]
        out += "\n\nPhotos via Wikimedia Commons — " + "; ".join(parts)
    return out


def _srt(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


if __name__ == "__main__":
    build(Path(sys.argv[1]))
