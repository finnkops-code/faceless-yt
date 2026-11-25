"""Vertical Shorts (1080x1920, <60s) cut from the same script as the long video.

Each short is its own mini-script in spec["shorts"] (max 3):
  {"title": "...", "narration": "...", "visuals": [...], "images": [...],
   "callouts": [{"at": "phrase", "text": "$5.9 billion", "label": "membership fees"}],
   "chart": {...optional, same schema as long-form...}, "tags": [...]}

House style: footage fills the frame, PRICE TAG PHYSICS wordmark + headline at the top,
big burned-in captions (Shorts are mostly watched muted), numbers in gold,
centred stat cards, and a closing card that points to the full video.
"""
import json
import math
import random
import re
from pathlib import Path

from PIL import Image, ImageDraw

from . import brand, tts
from .brand import GOLD, INK, MUTED, PANEL, anton, inter, ease

VW, VH = 1080, 1920
FPS = 30
SHOT = 2.8           # shorts cut faster than long-form
END_CARD = 2.4
NUMERIC = (r"\d|\$|%|\b(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|TWENTY|THIRTY|"
           r"FORTY|FIFTY|SIXTY|SEVENTY|EIGHTY|NINETY|HUNDRED|THOUSAND|MILLION|BILLION|TRILLION|PERCENT|"
           r"DOLLARS?|HALF|DOUBLE|TRIPLE)\b")


def _wrap(d, text, fnt, maxw):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def frame_png(title, out: Path):
    """Static top band: wordmark + headline over a soft dark gradient; bottom gradient for captions."""
    img = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    grad = Image.new("L", (1, VH))
    for y in range(VH):
        a = 0
        if y < 520:
            a = int(215 * (1 - y / 520) ** 1.4)
        elif y > VH - 760:
            a = int(170 * ((y - (VH - 760)) / 760) ** 1.6)
        grad.putpixel((0, y), a)
    shade = Image.new("RGBA", (VW, VH), (8, 10, 14, 255))
    shade.putalpha(grad.resize((VW, VH)))
    img.alpha_composite(shade)
    d = ImageDraw.Draw(img)
    wm = inter(30)
    d.text((VW / 2, 120), brand.BRAND_WORD, font=wm, fill=INK, anchor="mm")
    tw = d.textlength(brand.BRAND_WORD, font=wm)
    d.rectangle([VW / 2 - tw / 2, 146, VW / 2 + tw / 2, 151], fill=GOLD)
    f = anton(84)
    lines = _wrap(d, title.upper(), f, VW - 140)
    while len(lines) > 3 and f.size > 56:
        f = anton(f.size - 6)
        lines = _wrap(d, title.upper(), f, VW - 140)
    y = 215
    for ln in lines[:3]:
        d.text((VW / 2, y), ln, font=f, fill=INK, anchor="ma", stroke_width=2, stroke_fill=(0, 0, 0))
        y += f.size + 12
    img.save(out)
    return out


def callout_v(text, label, out: Path):
    """Centred stat card for the vertical frame (sits above the caption zone)."""
    img = Image.new("RGBA", (VW, VH), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = anton(150)
    while d.textlength(text, font=big) > VW - 220 and big.size > 64:
        big = anton(big.size - 6)
    lab = inter(36)
    llines = _wrap(d, label.upper(), lab, VW - 260)[:2]
    w = max(d.textlength(text, font=big), *(d.textlength(l, font=lab) for l in llines or [""])) + 120
    h = big.size + 70 + 50 * len(llines) + 40
    x0, y0 = (VW - w) / 2, 640
    brand._panel(img, (int(x0), y0, int(x0 + w), y0 + h), alpha=230, radius=26)
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + w, y0 + 10], fill=GOLD)
    d.text((VW / 2, y0 + 40), text, font=big, fill=INK, anchor="ma")
    yy = y0 + big.size + 80
    for l in llines:
        d.text((VW / 2, yy), l, font=lab, fill=GOLD, anchor="ma")
        yy += 50
    img.save(out)
    return out


def end_card(long_title, out: Path, work: Path):
    frames = work / "end_frames"
    frames.mkdir(parents=True, exist_ok=True)
    n = int(END_CARD * FPS)
    for k in range(n):
        t = k / FPS
        img = Image.new("RGB", (VW, VH), PANEL)
        d = ImageDraw.Draw(img)
        for j in range(26):
            d.line([(0, 200 + j * 64), (VW, 200 + j * 64)], fill=(22, 27, 34), width=2)
        a = ease(t / 0.5)
        col = lambda c: tuple(int(PANEL[i] + (c[i] - PANEL[i]) * a) for i in range(3))
        d.text((VW / 2, 640), "FULL BREAKDOWN", font=inter(44), fill=col(GOLD), anchor="mm")
        f = anton(96)
        lines = _wrap(d, long_title.upper(), f, VW - 160)
        while len(lines) > 4 and f.size > 60:
            f = anton(f.size - 6)
            lines = _wrap(d, long_title.upper(), f, VW - 160)
        y = 720
        for ln in lines[:4]:
            d.text((VW / 2, y + (1 - a) * 20), ln, font=f, fill=col(INK), anchor="ma")
            y += f.size + 14
        b = ease((t - 0.5) / 0.5)
        col2 = tuple(int(PANEL[i] + (MUTED[i] - PANEL[i]) * b) for i in range(3))
        d.text((VW / 2, y + 60), f"on the {brand.BRAND} channel", font=inter(42), fill=col2, anchor="mm")
        rule = ease((t - 0.3) / 0.7) * 360
        d.rectangle([VW / 2 - rule / 2, y + 110, VW / 2 + rule / 2, y + 118], fill=GOLD)
        img.save(frames / f"e{k:03d}.png")
    from .render import ff
    ff("-framerate", FPS, "-i", frames / "e%03d.png", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "18", "-pix_fmt", "yuv420p", out)
    return out


# ---------------------------------------------------------------- captions
def _ass_t(t):
    h, r = divmod(max(0, t), 3600)
    m, s = divmod(r, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def write_ass_v(words, path: Path):
    """Big, punchy 1-3 word captions; chunks with numbers in gold."""
    chunks, cur = [], []
    for s, e, w in words:
        cur.append((s, e, w))
        if len(cur) >= 3 or re.search(r"[.,!?;:]$", w):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    ev = []
    for n, c in enumerate(chunks):
        st = c[0][0]
        en = chunks[n + 1][0][0] if n + 1 < len(chunks) else c[-1][1] + 0.3
        en = min(en, c[-1][1] + 0.6)
        txt = " ".join(w for _, _, w in c).upper().replace("{", "").replace("}", "")
        colour = r"{\c&H00B7F5&}" if re.search(NUMERIC, txt) else ""
        ev.append(f"Dialogue: 0,{_ass_t(st)},{_ass_t(en)},Cap,,0,0,0,,{{\\fscx92\\fscy92\\t(0,90,\\fscx100\\fscy100)}}{colour}{txt}")
    path.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 0\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
        "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, "
        "Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Cap,Anton,104,&H00F7F4F2,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,1,0,1,"
        "7,3,2,90,90,470,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n" + "\n".join(ev) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------- build
def build_short(sh, k, spec, out: Path, credits_long, track):
    from .render import ff, _shots, _render_shot, phrase_time, FONTS, write_srt, srt_cues
    slug = spec["slug"]
    sdir = out / f"short_{k + 1}"
    work = sdir / "work"
    work.mkdir(parents=True, exist_ok=True)
    voice = spec.get("voice", tts.DEFAULT_VOICE)
    mp3 = work / "n.mp3"
    dur, words = tts.synthesize(sh["narration"], mp3, voice=voice)
    seg = dur + 0.25
    if seg + END_CARD > 59:
        print(f"[{slug}] short {k + 1} is {seg:.1f}s — longer than a Short should be; trim the narration")
    rnd = random.Random(f"{slug}short{k}")

    # footage
    n = max(1, math.ceil(seg / SHOT))
    photo_credits = []
    pool = _shots(sh, n, work, set(), photo_credits, slug, 100 + k)
    if not pool:
        raise RuntimeError("no footage for short")
    clips = []
    for j in range(n):
        kind, src = pool[j % len(pool)]
        c = work / f"c{j:02d}.mp4"
        _render_shot(kind, src, c, seg / n, rnd, f"{slug}s{k}{j}", reuse=j >= len(pool), size=(VW, VH))
        clips.append(c)
    lst = work / "clips.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    base = work / "base.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", base)

    # layers: frame (always), chart (window), callouts (timed)
    frame = frame_png(sh.get("headline") or sh["title"], work / "frame.png")
    args = ["-i", base, "-loop", "1", "-t", f"{seg:.3f}", "-i", frame]
    chains = ["[1:v]format=rgba[fr]", "[0:v][fr]overlay=0:0[o0]"]
    prev, idx, busy = "[o0]", 2, []
    if sh.get("chart"):
        cdir = work / "chart"
        brand.chart_frames(sh["chart"], cdir)
        nfr = len(list(cdir.glob("f*.png")))
        last = sorted(cdir.glob("f*.png"))[-1]
        bx = Image.open(last).getchannel("A").point(lambda a: 255 if a > 40 else 0).getbbox() or (0, 0, 1920, 1080)
        bx = (max(0, bx[0] - 10), max(0, bx[1] - 10), min(1920, bx[2] + 10), min(1080, bx[3] + 10))
        cw, chh = bx[2] - bx[0], bx[3] - bx[1]
        sh_h = int(chh * 1020 / cw)
        st = phrase_time(words, sh["chart"].get("at", "")) if sh["chart"].get("at") else seg * 0.35
        st = min(st or 0, max(0, seg - 4.8))
        en = min(seg - 0.1, st + 4.8)
        hold = max(0.1, en - st - nfr / FPS)
        args += ["-itsoffset", f"{st:.2f}", "-framerate", FPS, "-i", cdir / "f%03d.png"]
        cy = max(560, 1000 - sh_h // 2)
        chains.append(f"[{idx}:v]format=rgba,crop={cw}:{chh}:{bx[0]}:{bx[1]},scale=1020:-2,"
                      f"tpad=stop_mode=clone:stop_duration={hold:.2f}[ch]")
        chains.append(f"{prev}drawbox=x=0:y=470:w=1080:h=1450:color=black@0.45:t=fill:"
                      f"enable='between(t,{st:.2f},{en:.2f})'[db]")
        chains.append(f"[db][ch]overlay=30:{cy}:enable='between(t,{st:.2f},{en:.2f})'[o{idx}]")
        prev, idx = f"[o{idx}]", idx + 1
        busy.append((st, en))
    for j, co in enumerate(sh.get("callouts", [])):
        st = phrase_time(words, co.get("at", "")) if co.get("at") else None
        if st is None:
            st = seg * (j + 0.5) / (len(sh.get("callouts", [])) + 0.5)
        for a, b in busy:                      # never stack on a chart/earlier card: wait for it
            if a < st + 0.5 and st < b:
                st = b + 0.1
        en = min(seg - 0.1, st + float(co.get("hold", 3.0)))
        if en - st < 1.0:
            continue
        png = callout_v(co["text"], co.get("label", ""), work / f"co{j}.png")
        args += ["-loop", "1", "-t", f"{seg:.3f}", "-i", png]
        chains.append(f"[{idx}:v]format=rgba,fade=in:st={st:.2f}:d=0.25:alpha=1,"
                      f"fade=out:st={en - 0.25:.2f}:d=0.25:alpha=1[l{idx}]")
        y = f"'if(lt(t,{st:.2f}+0.3),40-40*(t-{st:.2f})/0.3,0)'"
        chains.append(f"{prev}[l{idx}]overlay=x=0:y={y}:enable='between(t,{st:.2f},{en:.2f})'[o{idx}]")
        prev, idx = f"[o{idx}]", idx + 1
        busy.append((st, en))
    ass = write_ass_v(words, work / "caps.ass")
    chains.append(f"{prev}ass={ass}:fontsdir={FONTS}[v]")
    body = work / "body.mp4"
    ff(*args, "-filter_complex", ";".join(chains), "-map", "[v]", "-t", f"{seg:.3f}",
       "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", body)

    endc = end_card(spec["title"], work / "end.mp4", work)
    lst2 = work / "all.txt"
    lst2.write_text(f"file '{body.resolve()}'\nfile '{endc.resolve()}'\n")
    silent = work / "silent.mp4"
    ff("-f", "concat", "-safe", "0", "-i", lst2, "-c", "copy", silent)

    total = seg + END_CARD
    narr = work / "n.wav"
    ff("-i", mp3, "-af", f"apad=whole_dur={total:.2f},loudnorm=I=-14:TP=-1.5:LRA=11",
       "-ar", "48000", "-ac", "2", narr)
    final = sdir / "video.mp4"
    if track:
        ff("-i", silent, "-i", narr, "-stream_loop", "-1", "-i", track, "-filter_complex",
           "[2:a]aresample=48000,volume=0.20[m];[1:a]asplit=2[n1][n2];"
           "[m][n2]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=300[md];"
           "[n1][md]amix=inputs=2:duration=first:normalize=0[a]",
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{total:.2f}", "-movflags", "+faststart", final)
    else:
        ff("-i", silent, "-i", narr, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
           "-b:a", "192k", "-t", f"{total:.2f}", "-movflags", "+faststart", final)
    write_srt(srt_cues(words, 0.0), sdir / "captions.srt")

    title = sh["title"].strip()
    if "#shorts" not in title.lower():
        title = f"{title[:90]} #Shorts"
    desc = (sh.get("description") or sh["narration"].split(". ")[0] + ".").strip()
    desc += f"\n\nFull breakdown: {spec['title']}\n{spec.get('long_url', '{LONG_URL}')}\n\n#Shorts #business #howtheymakemoney"
    from .render import compact_credits
    music = [c for c in credits_long if "Kevin MacLeod" in c][:1]
    desc += compact_credits(music + photo_credits)
    desc += "\nNarration uses a synthetic voice."
    meta = {"title": title[:100], "description": desc[:4900],
            "tags": (sh.get("tags") or spec.get("tags", []))[:20] + ["shorts"],
            "category_id": spec.get("category_id", "27"), "duration": round(total, 1),
            "short_of": slug, "index": k + 1}
    (sdir / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(f"[{slug}] short {k + 1} done → {final} ({total:.1f}s)")
    return sdir
