"""Automatic visual quality control with an open-source CLIP model (runs free on the Actions CPU).

- ok(path, query): rejects stock clips/photos whose content matches an off-topic concept
  (dogs for "hot dog", lakes, cartoons, crypto charts, empty shelves...) better than the query itself.
- rank(paths, text): orders candidate photos by how well they show `text` (used for thumbnails).
- sheet(video, out): contact sheet of the final render for a quick human/agent review.
If the model can't be loaded, every check passes (the pipeline never blocks on QA).
"""
import os
import subprocess
import tempfile
from pathlib import Path

NEGATIVES = ["a dog", "a cat", "a wild animal", "a cartoon or drawing", "a 3D render or animation",
             "bitcoin or cryptocurrency coins", "a stock market trading chart", "a lake, river or pond",
             "empty store shelves", "a blank screen with only text", "a close-up portrait of a person's face",
             "a forest or mountains landscape", "food being cooked in a kitchen"]
LOG: list = []
_state = {}


def _model():
    if "m" in _state:
        return _state["m"]
    if os.environ.get("QA_DISABLED"):
        _state["m"] = None
        return None
    try:
        import open_clip
        import torch
        m, _, pre = open_clip.create_model_and_transforms("ViT-B-32", pretrained="laion2b_s34b_b79k")
        m.eval()
        tok = open_clip.get_tokenizer("ViT-B-32")
        _state["m"] = (m, pre, tok, torch)
        print("QA: CLIP model loaded")
    except Exception as e:
        print(f"QA: CLIP unavailable ({e}); visual QA skipped")
        _state["m"] = None
    return _state["m"]


def _frame(path: Path):
    path = Path(path)
    if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        return path
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "2", "-i", str(path), "-frames:v", "1",
                    str(tmp)], check=False)
    return tmp


def _sims(path, texts):
    mm = _model()
    if not mm:
        return None
    m, pre, tok, torch = mm
    from PIL import Image
    try:
        img = pre(Image.open(_frame(path)).convert("RGB")).unsqueeze(0)
    except Exception:
        return None
    with torch.no_grad():
        iv = m.encode_image(img)
        tv = m.encode_text(tok(texts))
        iv = iv / iv.norm(dim=-1, keepdim=True)
        tv = tv / tv.norm(dim=-1, keepdim=True)
        return (iv @ tv.T)[0].tolist()


def ok(path, query: str) -> bool:
    q = query.split(":", 1)[-1].strip()
    negs = [n for n in NEGATIVES if not any(w in q.lower() for w in n.lower().split()[-2:])]
    s = _sims(path, [f"a photo of {q}"] + negs)
    if s is None:
        return True
    pos, worst = s[0], max(range(1, len(s)), key=lambda i: s[i])
    good = pos >= s[worst] and pos >= 0.17
    if not good:
        LOG.append(f"REJECT {Path(path).name} for '{q}': looks like '{negs[worst - 1]}' "
                   f"({s[worst]:.3f} vs {pos:.3f})")
    return good


def rank(paths, text: str):
    scored = []
    for p in paths:
        s = _sims(p, [f"a photo of {text}"])
        scored.append((s[0] if s else 0.0, p))
    return [p for _, p in sorted(scored, key=lambda x: -x[0])]


def sheet(video: Path, out: Path, every=20):
    """Frame every `every` seconds of the final video, 5 per row, with timestamps."""
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-vf",
                    f"fps=1/{every},scale=384:-1,drawtext=text='%{{pts\\:hms}}':x=8:y=8:fontcolor=white:"
                    f"box=1:boxcolor=black@0.6:fontsize=18,tile=5x8", "-frames:v", "1", str(out)], check=False)
    return out if out.exists() else None
