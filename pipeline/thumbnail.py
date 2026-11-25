"""Price Tag Physics house-style thumbnail.

Layout (1280x720): real photo of the subject on the right, near-black panel on the left that fades
into the photo, 3–6 huge Anton words (highlight words in ledger gold), gold rule, PRICE TAG PHYSICS wordmark.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

from .brand import BRAND_WORD

W, H = 1280, 720
GOLD = (245, 183, 0)
INK = (246, 247, 249)
PANEL = (12, 15, 20)


def _frame(src: Path, dest: Path, at="1.0"):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", at, "-i", str(src),
                    "-frames:v", "1", str(dest)], check=True)


def _load(clip):
    clip = Path(clip)
    if clip.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        return Image.open(clip).convert("RGB")
    tmp = clip.with_suffix(".thumbframe.png")
    _frame(clip, tmp)
    img = Image.open(tmp).convert("RGB")
    tmp.unlink(missing_ok=True)
    return img


def _cover(img, w, h, anchor_x=0.5):
    r = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1), Image.LANCZOS)
    left = int((img.width - w) * anchor_x)
    top = (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def make_thumbnail(spec: dict, clip, out: Path, fonts: Path):
    text = (spec.get("text") or "WATCH THIS").upper()
    hl = {w.strip("?!.,").upper() for w in (spec.get("highlight") or "").split()}
    try:
        photo = _load(clip)
    except Exception:
        photo = Image.new("RGB", (W, H), (40, 46, 56))
    photo = ImageEnhance.Color(photo).enhance(0.92)
    photo = ImageEnhance.Contrast(photo).enhance(1.08)
    pw = int(W * 0.60)
    canvas = Image.new("RGB", (W, H), PANEL)
    canvas.paste(_cover(photo, pw, H, anchor_x=float(spec.get("photo_anchor", 0.5))), (W - pw, 0))
    grad = Image.new("L", (W, 1))
    x0, x1 = W - pw, W - pw + int(W * 0.16)
    for x in range(W):
        grad.putpixel((x, 0), int(255 * max(0.0, min(1.0, (x1 - x) / (x1 - x0)))))
    canvas = Image.composite(Image.new("RGB", (W, H), PANEL), canvas, grad.resize((W, H)))
    d = ImageDraw.Draw(canvas)
    wm = ImageFont.truetype(str(fonts / "Inter-Bold.otf"), 22)
    d.text((56, 46), BRAND_WORD, font=wm, fill=GOLD)
    d.rectangle([56, 76, 56 + d.textlength(BRAND_WORD, font=wm), 79], fill=GOLD)
    size, maxw = 120, W - pw + 40
    while True:
        f = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), size)
        lines, cur = [], ""
        for w in text.split():
            t = (cur + " " + w).strip()
            if d.textlength(t, font=f) <= maxw:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        lh = int(size * 1.04)
        if lh * len(lines) <= H - 240 or size <= 70:
            break
        size -= 6
    y = (H - lh * len(lines)) // 2 + 10
    for ln in lines:
        x = 56
        for w in ln.split():
            col = GOLD if w.strip("?!.,") in hl else INK
            d.text((x + 4, y + 5), w, font=f, fill=(0, 0, 0))
            d.text((x, y), w, font=f, fill=col)
            x += d.textlength(w + " ", font=f)
        y += lh
    d.rectangle([56, y + 30, 56 + 170, y + 42], fill=GOLD)
    canvas.save(out, quality=93)
    return out


# ---------------------------------------------------------------- A/B/C variants for "Test & compare"
def _shadow_text(d, xy, text, font, fill, anchor="la", off=5):
    d.text((xy[0] + off, xy[1] + off), text, font=font, fill=(0, 0, 0), anchor=anchor)
    d.text(xy, text, font=font, fill=fill, anchor=anchor)


def _full_bleed(clip, dark=0.55, anchor_x=0.5):
    try:
        photo = _load(clip)
    except Exception:
        photo = Image.new("RGB", (W, H), (40, 46, 56))
    photo = ImageEnhance.Contrast(ImageEnhance.Color(photo).enhance(0.9)).enhance(1.1)
    img = _cover(photo, W, H, anchor_x)
    return Image.blend(img, Image.new("RGB", (W, H), PANEL), dark)


def _wordmark(d, fonts, x=56, y=46):
    wm = ImageFont.truetype(str(fonts / "Inter-Bold.otf"), 22)
    d.rectangle([x - 14, y - 12, x + d.textlength(BRAND_WORD, font=wm) + 14, y + 44], fill=PANEL)
    d.text((x, y), BRAND_WORD, font=wm, fill=GOLD)
    d.rectangle([x, y + 30, x + d.textlength(BRAND_WORD, font=wm), y + 33], fill=GOLD)


def thumb_number(v: dict, clip, out: Path, fonts: Path):
    """Variant B: one giant number dominates (tests 'number' curiosity)."""
    img = _full_bleed(clip, 0.58, float(v.get("photo_anchor", 0.5)))
    d = ImageDraw.Draw(img)
    _wordmark(d, fonts)
    num, label = v.get("number", "?"), (v.get("label") or "").upper()
    size = 330
    while True:
        f = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), size)
        if d.textlength(num, font=f) <= W - 160 or size <= 120:
            break
        size -= 10
    _shadow_text(d, (W // 2, H // 2 - 40), num, f, GOLD, anchor="mm", off=8)
    if label:
        fl = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), 78)
        while d.textlength(label, font=fl) > W - 140 and fl.size > 44:
            fl = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), fl.size - 4)
        _shadow_text(d, (W // 2, H // 2 + size // 2 + 10), label, fl, INK, anchor="mm")
    img.save(out, quality=93)
    return out


def thumb_band(v: dict, clip, out: Path, fonts: Path):
    """Variant C: full photo, bold statement on a dark band at the bottom (tests photo-first)."""
    img = _full_bleed(clip, 0.12, float(v.get("photo_anchor", 0.5)))
    band = Image.new("RGBA", (W, 250), PANEL + (235,))
    img = img.convert("RGBA")
    img.alpha_composite(band, (0, H - 250))
    img = img.convert("RGB")
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 250, W, H - 242], fill=GOLD)
    _wordmark(d, fonts)
    text = (v.get("text") or "HOW DO THEY MAKE MONEY?").upper()
    hl = {w.strip("?!.,").upper() for w in (v.get("highlight") or "").split()}
    size = 120
    while True:
        f = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), size)
        if d.textlength(text, font=f) <= W - 100 or size <= 60:
            break
        size -= 4
    x = (W - d.textlength(text, font=f)) / 2
    y = H - 125
    for w in text.split():
        col = GOLD if w.strip("?!.,") in hl else INK
        _shadow_text(d, (x, y), w, f, col, anchor="lm")
        x += d.textlength(w + " ", font=f)
    img.save(out, quality=93)
    return out


def make_variants(spec: dict, photos: list, out_dir: Path, fonts: Path, callouts=()):
    """thumbnail.jpg (A: split), thumbnail_b.jpg (B: big number), thumbnail_c.jpg (C: photo + band).
    Each variant uses a different photo where possible so the test also compares images."""
    photos = list(photos) or [None]
    pick = lambda k: photos[k % len(photos)]
    vs = {v.get("style"): v for v in spec.get("variants", [])}
    a = make_thumbnail(spec, pick(spec.get("photo", 0)), out_dir / "thumbnail.jpg", fonts)
    b = vs.get("number") or {}
    if not b.get("number") and callouts:
        b = {"number": callouts[0].get("text", ""), "label": callouts[0].get("label", "")}
    c = vs.get("band") or {"text": spec.get("text", ""), "highlight": spec.get("highlight", "")}
    out = [a]
    if b.get("number"):
        out.append(thumb_number(b, pick(b.get("photo", 1)), out_dir / "thumbnail_b.jpg", fonts))
    out.append(thumb_band(c, pick(c.get("photo", 2)), out_dir / "thumbnail_c.jpg", fonts))
    return out


def contact_sheet(photos, out: Path):
    """Numbered overview of candidate photos, so a variant's "photo" index can be chosen."""
    ims = []
    for p in photos:
        try:
            ims.append(_cover(_load(p), 384, 216))
        except Exception:
            pass
    if not ims:
        return None
    cols = 4
    sheet = Image.new("RGB", (384 * cols, 216 * ((len(ims) + cols - 1) // cols)), PANEL)
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x, y = 384 * (i % cols), 216 * (i // cols)
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + 44, y + 34], fill=GOLD)
        d.text((x + 12, y + 6), str(i), fill=PANEL)
    sheet.save(out, quality=88)
    return out
