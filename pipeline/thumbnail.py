"""Hidden Ledger house-style thumbnail.

Layout (1280x720): real photo of the subject on the right, near-black panel on the left that fades
into the photo, 3–6 huge Anton words (highlight words in ledger gold), gold rule, HIDDEN LEDGER wordmark.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

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
    d.text((56, 46), "HIDDEN LEDGER", font=wm, fill=GOLD)
    d.rectangle([56, 76, 56 + d.textlength("HIDDEN LEDGER", font=wm), 79], fill=GOLD)
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
