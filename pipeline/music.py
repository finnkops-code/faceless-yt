"""Background music bed: calm Kevin MacLeod tracks (CC BY) from Wikimedia Commons.

Tracks are cached in assets/music_cache/. Attribution is returned for the description.
Fails silently (no music) when nothing can be fetched.
"""
import json
import random
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "assets" / "music_cache"
UA = {"User-Agent": "HiddenLedgerPipeline/1.0 (github.com/finnkops-code/faceless-yt)"}
# calm, documentary-style pieces; searched by title on Commons
WANTED = ["Thinking Music", "Clean Soul", "Inspired", "Ambler", "Wallpaper", "Easy Lemon",
          "Lobby Time", "Backbay Lounge", "Daily Beetle", "Carefree", "Bright Wish"]
OK = ("cc by", "cc0", "public domain")


def _search(title):
    q = urllib.parse.quote(f'"{title}" Kevin MacLeod filetype:audio')
    url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search"
           f"&gsrnamespace=6&gsrsearch={q}&gsrlimit=5&prop=imageinfo&iiprop=url|extmetadata|mime")
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        data = json.loads(r.read())
    for p in data.get("query", {}).get("pages", {}).values():
        ii = (p.get("imageinfo") or [{}])[0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "")
        if title.lower() in p["title"].lower() and lic.lower().startswith(OK) and "nc" not in lic.lower():
            return ii["url"], f'Music: "{title}" by Kevin MacLeod (incompetech.com), {lic}, via Wikimedia Commons'
    return None


def pick_track(seed):
    CACHE.mkdir(parents=True, exist_ok=True)
    order = WANTED[:]
    random.Random(seed).shuffle(order)
    for title in order:
        dest = CACHE / (title.replace(" ", "_") + ".audio")
        meta = dest.with_suffix(".json")
        try:
            if not dest.exists():
                hit = _search(title)
                if not hit:
                    continue
                url, credit = hit
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
                    dest.write_bytes(r.read())
                meta.write_text(json.dumps({"credit": credit}))
            return dest, json.loads(meta.read_text())["credit"]
        except Exception as e:
            print(f"  music '{title}' unavailable: {e.__class__.__name__}")
    return None, None
