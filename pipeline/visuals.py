"""B-roll and charts.

Stock footage: Pexels API (free key, commercial use allowed, no attribution required),
with Pixabay as a second free source. Charts are drawn from researched data with
matplotlib — this is the channel's original visual layer.
"""
import json
import os
import random
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

W, H, FPS = 1920, 1080, 30
UA = {"User-Agent": "faceless-yt-pipeline/1.0"}

# Brand palette
BG = "#0E1116"
INK = "#F2F4F7"
MUTED = "#8B93A1"
ACCENT = "#F5B700"
SECOND = "#3FA7D6"


def _get_json(url, headers=None):
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def _download(url, dest: Path):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)


def _pexels(query, n=6):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    q = urllib.parse.quote(query)
    data = _get_json(f"https://api.pexels.com/videos/search?query={q}&orientation=landscape"
                     f"&size=medium&per_page={n}", {"Authorization": key})
    urls = []
    for v in data.get("videos", []):
        files = [f for f in v["video_files"] if f.get("width") and f["width"] >= 1280
                 and f.get("file_type") == "video/mp4"]
        if files:
            best = min(files, key=lambda f: abs(f["width"] - 1920))
            urls.append((f"pexels-{v['id']}", best["link"]))
    return urls


def _pixabay(query, n=6):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    q = urllib.parse.quote(query)
    data = _get_json(f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page={max(n, 3)}")
    out = []
    for h in data.get("hits", []):
        vid = h["videos"].get("large") or h["videos"].get("medium")
        if vid and vid.get("url"):
            out.append((f"pixabay-{h['id']}", vid["url"]))
    return out


def fetch_broll(queries, cache: Path, used: set, need: int):
    """Download up to `need` distinct clips for the given queries."""
    cache.mkdir(parents=True, exist_ok=True)
    clips = []
    for q in queries:
        try:
            cands = _pexels(q) or _pixabay(q)
        except Exception as e:
            print(f"  stock search failed for '{q}': {e}")
            cands = []
        for cid, url in cands:
            if cid in used:
                continue
            dest = cache / f"{cid}.mp4"
            if not dest.exists():
                try:
                    _download(url, dest)
                except Exception as e:
                    print(f"  download failed {cid}: {e}")
                    continue
            used.add(cid)
            clips.append(dest)
            break  # one per query per pass → variety
        if len(clips) >= need:
            break
    # second pass: more results per query if still short
    if len(clips) < need:
        for q in queries:
            try:
                cands = _pexels(q, 12) or _pixabay(q, 12)
            except Exception:
                cands = []
            for cid, url in cands:
                if len(clips) >= need:
                    break
                if cid in used:
                    continue
                dest = cache / f"{cid}.mp4"
                try:
                    if not dest.exists():
                        _download(url, dest)
                    used.add(cid)
                    clips.append(dest)
                except Exception:
                    continue
    return clips


def normalize_clip(src: Path, dest: Path, duration: float, start: float = 0.0):
    vf = (f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
          f"fps={FPS},setsar=1,eq=contrast=1.04:saturation=1.08")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.2f}", "-i", str(src),
                    "-t", f"{duration:.3f}", "-an", "-vf", vf, "-c:v", "libx264",
                    "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(dest)],
                   check=True)


def probe(src: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", str(src)], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def still_to_clip(png: Path, dest: Path, duration: float, zoom=True):
    frames = max(1, int(duration * FPS))
    if zoom:
        vf = (f"scale={W*2}:{H*2},zoompan=z='min(zoom+0.0004,1.08)':d={frames}"
              f":x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={W}x{H}:fps={FPS},setsar=1")
    else:
        vf = f"scale={W}:{H},fps={FPS},setsar=1"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png),
                    "-t", f"{duration:.3f}", "-vf", vf, "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "18", "-pix_fmt", "yuv420p", str(dest)], check=True)


def _fonts():
    from matplotlib import font_manager
    here = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    for f in here.glob("*.[ot]tf"):
        font_manager.fontManager.addfont(str(f))
    return here


def render_chart(spec: dict, out_png: Path):
    """spec: {type: bar|hbar|line, title, labels, values, unit, source, highlight?}"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _fonts()
    plt.rcParams["font.family"] = "Inter"
    fig = plt.figure(figsize=(19.2, 10.8), dpi=100, facecolor=(0, 0, 0, 0))
    from matplotlib.patches import FancyBboxPatch
    fig.patches.append(FancyBboxPatch((0.04, 0.05), 0.92, 0.9, boxstyle="round,pad=0,rounding_size=0.02",
                                      transform=fig.transFigure, facecolor=(0.055, 0.067, 0.086, 0.86),
                                      edgecolor=(1, 1, 1, 0.08), lw=2, zorder=-10))
    left = 0.27 if spec.get("type") == "hbar" else 0.08
    ax = fig.add_axes([left, 0.2, 0.92 - left, 0.58])
    ax.patch.set_alpha(0)
    labels, values = spec["labels"], spec["values"]
    unit = spec.get("unit", "")
    hl = spec.get("highlight")
    colors = [ACCENT if (hl is not None and (l == hl or i == hl)) else SECOND
              for i, l in enumerate(labels)] if hl is not None else [ACCENT] * len(labels)
    kind = spec.get("type", "bar")
    fmt = lambda v: f"{unit if unit.startswith('$') else ''}{v:,.{spec.get('decimals', 0)}f}" \
                    f"{'' if unit.startswith('$') else (unit if unit == '%' else (' ' + unit if unit else ''))}"
    if kind == "line":
        ax.plot(labels, values, color=ACCENT, lw=6, solid_capstyle="round")
        ax.scatter(labels, values, color=ACCENT, s=120, zorder=3)
        ax.annotate(fmt(values[-1]), (len(values) - 1, values[-1]), xytext=(12, 12),
                    textcoords="offset points", color=INK, fontsize=30, fontweight="bold")
        ax.annotate(fmt(values[0]), (0, values[0]), xytext=(12, -36),
                    textcoords="offset points", color=MUTED, fontsize=24)
    elif kind == "hbar":
        y = range(len(labels))[::-1]
        ax.barh(list(y), values, color=colors, height=0.62)
        ax.set_yticks(list(y), labels, color=INK, fontsize=26)
        for yi, v in zip(y, values):
            ax.text(v, yi, "  " + fmt(v), va="center", color=INK, fontsize=26, fontweight="bold")
        ax.set_xticks([])
    else:
        ax.bar(labels, values, color=colors, width=0.62)
        for i, v in enumerate(values):
            ax.text(i, v, fmt(v), ha="center", va="bottom", color=INK, fontsize=28,
                    fontweight="bold")
        ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=INK, labelsize=24, length=0)
    if kind == "line":
        ax.tick_params(axis="y", colors=MUTED)
        ax.grid(axis="y", color="#232933", lw=1)
    fig.text(0.08, 0.89, spec["title"], color=INK, fontsize=46, fontweight="bold")
    if spec.get("subtitle"):
        fig.text(0.08, 0.84, spec["subtitle"], color=MUTED, fontsize=26)
    if spec.get("source"):
        fig.text(0.92, 0.895, f"Source: {spec['source']}", color=MUTED, fontsize=18, ha="right")
    fig.savefig(out_png, transparent=True)
    plt.close(fig)


def render_title_card(text: str, out_png: Path, kicker: str = ""):
    from PIL import Image, ImageDraw, ImageFont
    fonts = _fonts()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, H], fill=(10, 12, 16, 150))
    big = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), 150)
    small = ImageFont.truetype(str(fonts / "Inter-Bold.otf"), 46)
    lines = _wrap(d, text.upper(), big, W - 300)
    total = len(lines) * 170
    y = (H - total) // 2
    if kicker:
        d.text((150, y - 90), kicker.upper(), font=small, fill=ACCENT)
    for ln in lines:
        d.text((150, y), ln, font=big, fill=INK)
        y += 170
    d.rectangle([150, y + 45, 390, y + 59], fill=ACCENT)
    img.save(out_png)


def _wrap(draw, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def fallback_background(out_png: Path, seed: str):
    """Abstract gradient used only when no stock footage is available."""
    from PIL import Image, ImageDraw, ImageFilter
    rnd = random.Random(seed)
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    for _ in range(6):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(200, 600)
        c = rnd.choice([(245, 183, 0), (63, 167, 214), (40, 48, 64)])
        d.ellipse([x - r, y - r, x + r, y + r], fill=tuple(int(v * 0.35) for v in c))
    img.filter(ImageFilter.GaussianBlur(120)).save(out_png)


# ---------------- photos ----------------
COMMONS_UA = {"User-Agent": "HiddenLedgerPipeline/1.0 (github.com/finnkops-code/faceless-yt)"}
OK_LICENSES = ("cc0", "public domain", "pd", "cc by 2", "cc by 3", "cc by 4", "cc by-sa")


def _strip_html(t):
    import re
    return re.sub(r"<[^>]+>", "", t or "").strip()


def _commons(query, n=8):
    q = urllib.parse.quote(query)
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
           f"&gsrnamespace=6&gsrsearch={q}%20filetype:bitmap&gsrlimit={n}&prop=imageinfo"
           "&iiprop=url|size|extmetadata&iiurlwidth=2560")
    req = urllib.request.Request(url, headers=COMMONS_UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
    pages = sorted(data.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    out = []
    for p in pages:
        ii = (p.get("imageinfo") or [{}])[0]
        meta = ii.get("extmetadata", {})
        lic = meta.get("LicenseShortName", {}).get("value", "").lower()
        title = p.get("title", "")
        if not any(lic.startswith(l) for l in OK_LICENSES) or "nc" in lic or "nd" in lic:
            continue
        if "logo" in title.lower() or ii.get("width", 0) < 1200 or ii.get("width", 0) < ii.get("height", 1):
            continue
        credit = f"{title.replace('File:', '')} by {_strip_html(meta.get('Artist', {}).get('value', 'unknown'))[:80]}, {meta.get('LicenseShortName', {}).get('value')}, via Wikimedia Commons"
        out.append((f"commons-{p['pageid']}", ii.get("thumburl") or ii["url"], credit))
    return out


def _pexels_photos(query, n=8):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    q = urllib.parse.quote(query)
    data = _get_json(f"https://api.pexels.com/v1/search?query={q}&orientation=landscape&per_page={n}",
                     {"Authorization": key})
    return [(f"pexelsimg-{p['id']}", p["src"]["large2x"], None) for p in data.get("photos", [])]


def _pixabay_photos(query, n=8):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    q = urllib.parse.quote(query)
    data = _get_json(f"https://pixabay.com/api/?key={key}&q={q}&image_type=photo"
                     f"&orientation=horizontal&min_width=1600&safesearch=true&per_page={max(n, 3)}")
    return [(f"pixabayimg-{h['id']}", h.get("largeImageURL") or h["webformatURL"], None)
            for h in data.get("hits", [])]


def fetch_photos(queries, cache: Path, used: set, need: int, credits: list):
    """Queries prefixed 'commons:' search Wikimedia Commons (real places/products/people-free);
    others search Pexels photos. Returns list of image paths; appends attributions to credits."""
    cache.mkdir(parents=True, exist_ok=True)
    out = []
    for q in queries:
        if len(out) >= need:
            break
        src = "commons" if q.lower().startswith("commons:") else "pexels"
        term = q.split(":", 1)[1].strip() if src == "commons" else q
        try:
            cands = _commons(term) if src == "commons" else (_pexels_photos(term) or _pixabay_photos(term))
        except Exception as e:
            print(f"  photo search failed '{q}': {e}")
            continue
        for cid, url, credit in cands:
            if cid in used:
                continue
            dest = cache / f"{cid}.jpg"
            try:
                if not dest.exists():
                    req = urllib.request.Request(url, headers=COMMONS_UA if src == "commons" else UA)
                    with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                        f.write(r.read())
            except Exception as e:
                print(f"  photo download failed {cid}: {e}")
                continue
            used.add(cid)
            out.append(dest)
            if credit and credit not in credits:
                credits.append(credit)
            break
    return out


def ken_burns(img: Path, dest: Path, duration: float, seed: str):
    """Slow zoom/pan over a still photo."""
    rnd = random.Random(seed)
    frames = max(1, int(duration * FPS))
    mode = rnd.choice(["in", "out", "left", "right"])
    z = {"in": "1.0+0.12*on/{f}", "out": "1.12-0.12*on/{f}"}.get(mode, "1.12").format(f=frames)
    if mode == "left":
        x = f"(iw-iw/zoom)*(1-on/{frames})"
    elif mode == "right":
        x = f"(iw-iw/zoom)*on/{frames}"
    else:
        x = "iw/2-(iw/zoom/2)"
    vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase,crop={W*2}:{H*2},"
          f"zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS},"
          f"setsar=1,eq=contrast=1.04:saturation=1.06")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(img), "-t", f"{duration:.3f}",
                    "-vf", vf, "-c:v", "libx264", "-preset", "veryfast", "-crf", "19",
                    "-pix_fmt", "yuv420p", str(dest)], check=True)


def overlay_on(bg_clip: Path, png: Path, dest: Path, duration: float):
    """Blur + darken a footage clip and fade a transparent graphic (chart/card) on top."""
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(bg_clip), "-loop", "1", "-i", str(png),
        "-filter_complex",
        f"[0:v]boxblur=18:2,eq=brightness=-0.12:saturation=0.8[bg];"
        f"[1:v]format=rgba,scale={W}:{H},fade=in:st=0:d=0.45:alpha=1[fg];"
        f"[bg][fg]overlay=0:0:shortest=1,fps={FPS},setsar=1[v]",
        "-map", "[v]", "-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "19", "-pix_fmt", "yuv420p", str(dest)], check=True)
