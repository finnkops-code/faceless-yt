"""Thumbnail: frame from the video + dark gradient + 2–4 huge words, one highlighted."""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 720
ACCENT = (245, 183, 0)
INK = (255, 255, 255)


def _frame(src: Path, dest: Path):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1.0", "-i", str(src),
                    "-frames:v", "1", "-vf", f"scale={W}:{H}", str(dest)], check=True)


def make_thumbnail(spec: dict, clip: Path, out: Path, fonts: Path):
    text = (spec.get("text") or "WATCH THIS").upper()
    highlight = (spec.get("highlight") or "").upper()
    frame = out.with_suffix(".frame.png")
    try:
        if Path(clip).suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            img = Image.open(clip).convert("RGB")
            r = max(W / img.width, H / img.height)
            img = img.resize((int(img.width * r) + 1, int(img.height * r) + 1))
            l, t = (img.width - W) // 2, (img.height - H) // 2
            img = img.crop((l, t, l + W, t + H))
        else:
            _frame(clip, frame)
            img = Image.open(frame).convert("RGB")
    except Exception:
        img = Image.new("RGB", (W, H), (14, 17, 22))
    img = img.filter(ImageFilter.GaussianBlur(1.2))
    # left-to-right dark gradient for legibility
    grad = Image.new("L", (W, 1))
    for x in range(W):
        grad.putpixel((x, 0), int(235 * max(0.0, 1 - x / (W * 0.85))))
    shade = Image.new("RGB", (W, H), (0, 0, 0))
    img = Image.composite(shade, img, grad.resize((W, H)))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), 150)
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= W * 0.62:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    while len(lines) * 160 > H - 80 and font.size > 80:
        font = ImageFont.truetype(str(fonts / "Anton-Regular.ttf"), font.size - 10)
    lh = int(font.size * 1.07)
    y = (H - lh * len(lines)) // 2
    for ln in lines:
        x = 60
        for w in ln.split():
            color = ACCENT if highlight and w.strip("?!.,") in highlight.split() else INK
            d.text((x + 5, y + 5), w, font=font, fill=(0, 0, 0))
            d.text((x, y), w, font=font, fill=color)
            x += d.textlength(w + " ", font=font)
        y += lh
    img.save(out, quality=92)
    frame.unlink(missing_ok=True)
