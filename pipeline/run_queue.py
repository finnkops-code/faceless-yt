"""Render every script in content/queue/, optionally upload, then move it to published/.

Run by GitHub Actions. Max N videos per run (default 1) to stay well inside quotas.
"""
import json
import os
import shutil
from pathlib import Path

from .render import build

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "content" / "queue"
DONE = ROOT / "content" / "published"


def main():
    limit = int(os.environ.get("MAX_PER_RUN", "1"))
    mode = os.environ.get("UPLOAD_MODE", "release")  # release | api
    if not (os.environ.get("PEXELS_API_KEY") or os.environ.get("PIXABAY_API_KEY")):
        print("No stock footage key configured (PEXELS_API_KEY) - skipping render, queue untouched.")
        return
    items = sorted(QUEUE.glob("*.json"))[:limit]
    results = []
    for p in items:
        out = build(p)
        rec = {"slug": out.name, "dir": str(out.relative_to(ROOT)), "mode": mode}
        if mode == "api":
            from .upload import upload
            rec["video_id"] = upload(out)
        DONE.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), DONE / p.name)
        results.append(rec)
    (ROOT / "output" / "run.json").parent.mkdir(exist_ok=True)
    (ROOT / "output" / "run.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
