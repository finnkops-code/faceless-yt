"""Snapshot channel + per-video stats into data/stats.json (feeds the strategy loop)."""
import json
from datetime import datetime, timezone
from pathlib import Path

from .upload import client

ROOT = Path(__file__).resolve().parent.parent


def main():
    yt = client()
    ch = yt.channels().list(part="statistics,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, token = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50,
                                    pageToken=token).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        token = r.get("nextPageToken")
        if not token:
            break
    videos = []
    for k in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,statistics,contentDetails,status",
                             id=",".join(ids[k:k + 50])).execute()
        for v in r["items"]:
            videos.append({"id": v["id"], "title": v["snippet"]["title"],
                           "published": v["snippet"]["publishedAt"],
                           "privacy": v["status"]["privacyStatus"],
                           "duration": v["contentDetails"]["duration"],
                           **{k2: int(x) for k2, x in v["statistics"].items()}})
    snap = {"taken": datetime.now(timezone.utc).isoformat(), "channel": ch["statistics"],
            "videos": videos}
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "stats.json").write_text(json.dumps(snap, indent=2))
    print(f"{len(videos)} videos, subs={ch['statistics'].get('subscriberCount')}")


if __name__ == "__main__":
    main()
