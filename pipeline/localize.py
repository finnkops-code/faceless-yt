"""Apply translated titles/descriptions (YouTube 'localizations') to published videos.

Input: content/localize/*.json  ->  {"video_id": "...", "items": {"es": {"title": "...", "summary": "..."}, ...}}
The localized description = translated summary + the original description minus its first paragraph
(chapters, sources and credits stay as they are). Needs the youtube.force-ssl scope.
"""
import json
import shutil
from pathlib import Path

from .upload import client

ROOT = Path(__file__).resolve().parent.parent


def apply(spec: dict, yt):
    vid = spec["video_id"]
    v = yt.videos().list(part="snippet,localizations", id=vid).execute()["items"][0]
    sn = v["snippet"]
    rest = sn["description"].split("\n\n", 1)[1] if "\n\n" in sn["description"] else ""
    loc = v.get("localizations", {})
    for lang, it in spec["items"].items():
        loc[lang] = {"title": it["title"][:100], "description": (it["summary"].strip() + "\n\n" + rest)[:4900]}
    sn.setdefault("defaultLanguage", "en")
    body = {"id": vid, "snippet": {k: sn[k] for k in ("title", "description", "categoryId", "defaultLanguage", "tags")
                                   if k in sn}, "localizations": loc}
    yt.videos().update(part="snippet,localizations", body=body).execute()
    print(f"localized {vid}: {', '.join(spec['items'])}")


def main():
    files = sorted((ROOT / "content" / "localize").glob("*.json"))
    if not files:
        return
    yt = client()
    done = ROOT / "content" / "localize" / "done"
    done.mkdir(exist_ok=True)
    for f in files:
        try:
            apply(json.loads(f.read_text()), yt)
            shutil.move(str(f), done / f.name)
        except Exception as e:
            print(f"localize failed for {f.name}: {e}")


if __name__ == "__main__":
    main()
