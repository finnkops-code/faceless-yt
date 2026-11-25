"""Price Tag Physics house style: animated charts, stat callouts, chapter labels and the intro ident.

One design system everywhere:
  - colours: ink on near-black panels, one accent (ledger gold), one secondary (steel blue)
  - type: Anton for numbers/headlines, Inter for labels
  - every graphic carries the small PRICE TAG PHYSICS wordmark + a thin gold rule
"""
import math
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1920, 1080, 30
FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
BRAND = "Price Tag Physics"
BRAND_WORD = "PRICE TAG PHYSICS"
GOLD = (245, 183, 0)
STEEL = (63, 167, 214)
INK = (242, 244, 247)
MUTED = (150, 158, 172)
PANEL = (12, 15, 20)


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def anton(s):
    return font("Anton-Regular.ttf", s)


def inter(s):
    return font("Inter-Bold.otf", s)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------------------------------------------------------------- value formatting
def fmt_value(v, spec):
    """'$5.9 billion', '92.3%', '84.1 million'. Uses prefix/suffix; falls back to legacy unit."""
    dec = spec.get("decimals", 1 if abs(v) < 100 and v != int(v) else 0)
    num = f"{v:,.{dec}f}"
    if "prefix" in spec or "suffix" in spec:
        return f"{spec.get('prefix', '')}{num}{spec.get('suffix', '')}"
    unit = spec.get("unit", "")
    scale = ""
    sub = (spec.get("subtitle", "") or "").lower()
    for word in ("trillion", "billion", "million", "thousand"):
        if word in sub:
            scale = f" {word}"
            break
    if unit == "%":
        return f"{num}%"
    if unit.startswith("$"):
        return f"${num}{scale}"
    if unit in ("M",):
        return f"{num} million"
    return f"{num}{scale}{(' ' + unit) if unit else ''}"


def wordmark(d, x, y, size=26):
    d.text((x, y), BRAND_WORD, font=inter(size), fill=GOLD)
    w = d.textlength(BRAND_WORD, font=inter(size))
    d.rectangle([x, y + size + 8, x + w, y + size + 11], fill=GOLD)


def _panel(img, box, alpha=232, radius=28):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rounded_rectangle(box, radius, fill=PANEL + (alpha,), outline=(255, 255, 255, 26), width=2)
    img.alpha_composite(ov)


# ---------------------------------------------------------------- charts
def chart_frames(spec, outdir: Path, anim_frames=27):
    """Writes outdir/f%03d.png (RGBA). Bars grow / line draws, values count up."""
    outdir.mkdir(parents=True, exist_ok=True)
    labels, values = spec["labels"], [float(v) for v in spec["values"]]
    kind = spec.get("type", "bar")
    hl = spec.get("highlight")
    vmax = max(values) if values else 1
    for f in range(anim_frames + 1):
        p = ease(f / anim_frames)
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _panel(img, (90, 70, W - 90, H - 70))
        d = ImageDraw.Draw(img)
        wordmark(d, 150, 115)
        d.text((150, 175), spec["title"], font=inter(54), fill=INK)
        if spec.get("subtitle"):
            d.text((150, 245), spec["subtitle"], font=inter(30), fill=MUTED)
        if spec.get("source"):
            d.text((150, H - 125), f"Source: {spec['source']}", font=inter(22), fill=MUTED)
        area = (150, 320, W - 150, H - 170)          # x0, y0, x1, y1 plotting area
        col = lambda i, l: GOLD if (hl is None or l == hl or i == hl) else STEEL
        if kind == "hbar":
            n = len(values)
            lab_f = inter(34)
            lab_w = max(d.textlength(l, font=lab_f) for l in labels) + 40
            val_f = anton(64 if n <= 3 else 48)
            val_w = max(d.textlength(fmt_value(v, spec), font=val_f) for v in values) + 40
            x0 = area[0] + lab_w
            x1 = area[2] - val_w
            row_h = (area[3] - area[1]) / n
            bar_h = min(110, row_h * 0.62)
            for i, (l, v) in enumerate(zip(labels, values)):
                cy = area[1] + row_h * (i + 0.5)
                d.text((x0 - 25, cy), l, font=lab_f, fill=INK, anchor="rm")
                wpx = max(6, (x1 - x0) * (v / vmax) * p)
                d.rounded_rectangle([x0, cy - bar_h / 2, x0 + wpx, cy + bar_h / 2], 10, fill=col(i, l))
                d.text((x0 + wpx + 22, cy), fmt_value(v * p, spec), font=val_f, fill=INK, anchor="lm")
        elif kind == "line":
            n = len(values)
            vmin = min(values)
            lo, hi = vmin - (vmax - vmin) * 0.25, vmax + (vmax - vmin) * 0.25 or vmax + 1
            xs = [area[0] + 120 + (area[2] - area[0] - 360) * i / max(1, n - 1) for i in range(n)]
            ys = [area[3] - 60 - (area[3] - area[1] - 140) * (v - lo) / (hi - lo) for v in values]
            for i, l in enumerate(labels):
                d.text((xs[i], area[3] - 10), str(l), font=inter(30), fill=MUTED, anchor="mm")
            upto = p * (n - 1)
            pts = []
            for i in range(n):
                if i <= upto:
                    pts.append((xs[i], ys[i]))
                elif i - 1 < upto:
                    t = upto - (i - 1)
                    pts.append((xs[i - 1] + (xs[i] - xs[i - 1]) * t, ys[i - 1] + (ys[i] - ys[i - 1]) * t))
            if len(pts) > 1:
                d.line(pts, fill=GOLD, width=9, joint="curve")
            for i in range(n):
                if i <= upto + 1e-6:
                    d.ellipse([xs[i] - 13, ys[i] - 13, xs[i] + 13, ys[i] + 13], fill=GOLD)
                    d.text((xs[i], ys[i] - 42), fmt_value(values[i], spec), font=anton(52), fill=INK, anchor="ms")
        else:  # vertical bars
            n = len(values)
            slot = (area[2] - area[0]) / n
            bar_w = min(260, slot * 0.55)
            val_f = anton(72 if n <= 3 else 52)
            top_pad = 110
            for i, (l, v) in enumerate(zip(labels, values)):
                cx = area[0] + slot * (i + 0.5)
                hpx = max(6, (area[3] - area[1] - top_pad - 50) * (v / vmax) * p)
                base = area[3] - 50
                d.rounded_rectangle([cx - bar_w / 2, base - hpx, cx + bar_w / 2, base], 10, fill=col(i, l))
                d.text((cx, base - hpx - 18), fmt_value(v * p, spec), font=val_f, fill=INK, anchor="ms")
                d.text((cx, base + 38), l, font=inter(32), fill=INK, anchor="mm")
        img.save(outdir / f"f{f:03d}.png")
    return anim_frames + 1


# ---------------------------------------------------------------- stat callout
def callout_png(text, label, out: Path):
    """Big number + label card, lower-left third."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    big = anton(150)
    while d.textlength(text, font=big) > 1100 and big.size > 70:
        big = anton(big.size - 8)
    lab = inter(38)
    tw = max(d.textlength(text, font=big), d.textlength(label, font=lab)) + 120
    x0, y1 = 110, H - 120
    y0 = y1 - big.size - 150
    # soft shadow + panel
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([x0 + 8, y0 + 12, x0 + tw + 8, y1 + 12], 24, fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    _panel(img, (x0, y0, x0 + tw, y1), alpha=225, radius=24)
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x0 + 12, y1], fill=GOLD)
    d.text((x0 + 60, y0 + 28), text, font=big, fill=INK)
    d.text((x0 + 62, y1 - 70), label.upper(), font=lab, fill=GOLD)
    img.save(out)
    return out


def chapter_png(number, title, out: Path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f1, f2 = anton(54), inter(34)
    num = f"{number:02d}"
    w = d.textlength(num, font=f1) + 30 + d.textlength(title.upper(), font=f2) + 90
    _panel(img, (80, 70, 80 + w, 170), alpha=215, radius=18)
    d = ImageDraw.Draw(img)
    d.text((115, 120), num, font=f1, fill=GOLD, anchor="lm")
    x = 115 + d.textlength(num, font=f1) + 30
    d.text((x, 122), title.upper(), font=f2, fill=INK, anchor="lm")
    img.save(out)
    return out


# ---------------------------------------------------------------- ident
def ident_clip(out: Path, seconds=2.6, tagline="The hidden forces behind every price tag"):
    tmp = out.parent / "ident_frames"
    tmp.mkdir(parents=True, exist_ok=True)
    n = int(seconds * FPS)
    for f in range(n):
        t = f / FPS
        img = Image.new("RGB", (W, H), PANEL)
        d = ImageDraw.Draw(img)
        # faint ledger lines
        for k in range(14):
            y = 140 + k * 60
            d.line([(0, y), (W, y)], fill=(22, 27, 34), width=2)
        a = ease(t / 0.7)
        word = BRAND_WORD
        ft = anton(170)
        tw = d.textlength(word, font=ft)
        x = (W - tw) / 2
        col = tuple(int(PANEL[i] + (INK[i] - PANEL[i]) * a) for i in range(3))
        d.text((x, H / 2 - 40 + (1 - a) * 30), word, font=ft, fill=col, anchor="lm")
        rule = ease((t - 0.4) / 0.8) * tw
        d.rectangle([x, H / 2 + 75, x + rule, H / 2 + 83], fill=GOLD)
        b = ease((t - 1.0) / 0.6)
        tcol = tuple(int(PANEL[i] + (MUTED[i] - PANEL[i]) * b) for i in range(3))
        d.text((W / 2, H / 2 + 140), tagline, font=inter(40), fill=tcol, anchor="mm")
        fade = min(1.0, (seconds - t) / 0.35)
        if fade < 1:
            img = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), img, max(0, fade))
        img.save(tmp / f"i{f:03d}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "i%03d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)],
                   check=True)
    return out
