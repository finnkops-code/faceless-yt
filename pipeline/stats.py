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
    analytics = _analytics(videos)
    status = "error" if analytics is None else ("ok" if analytics else "no_data_yet")
    analytics = analytics or {}
    for v in videos:
        v.update(analytics.get(v["id"], {}))
        v["is_short"] = _secs(v["duration"]) <= 60
        age = max(1.0, (datetime.now(timezone.utc) - datetime.fromisoformat(
            v["published"].replace("Z", "+00:00"))).total_seconds() / 86400)
        v["views_per_day"] = round(v.get("viewCount", 0) / age, 1)
        if v.get("views"):
            v["subs_per_1k_views"] = round(1000 * v.get("subscribersGained", 0) / v["views"], 2)
    snap = {"taken": datetime.now(timezone.utc).isoformat(), "channel": ch["statistics"],
            "analytics_status": status, "videos": videos}
    _scoreboard(snap)
    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "stats.json").write_text(json.dumps(snap, indent=2))
    print(f"{len(videos)} videos, subs={ch['statistics'].get('subscriberCount')}")


def _secs(iso):
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (3600, 60, 1))) if m else 0


def _analytics(videos):
    """Per-video watch time, retention and subscribers (YouTube Analytics API).
    Needs the yt-analytics.readonly scope on the refresh token; returns {} without it."""
    try:
        from googleapiclient.discovery import build
        from .upload import creds
        ya = build("youtubeAnalytics", "v2", credentials=creds(), cache_discovery=False)
        start = min((v["published"][:10] for v in videos), default="2026-11-01")
        r = ya.reports().query(ids="channel==MINE", startDate=start,
                               endDate=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                               metrics="views,estimatedMinutesWatched,averageViewDuration,"
                                       "averageViewPercentage,subscribersGained,subscribersLost,likes,shares",
                               dimensions="video", sort="-views", maxResults=200).execute()
        cols = [c["name"] for c in r["columnHeaders"]]
        return {row[0]: dict(zip(cols[1:], row[1:])) for row in r.get("rows", [])}
    except Exception as e:
        print(f"analytics unavailable: {e}")
        return None


def _scoreboard(snap):
    """Compact human/agent-readable growth scoreboard: data/growth.md."""
    ch = snap["channel"]
    lines = ["# Growth scoreboard (auto-generated)", f"Taken: {snap['taken'][:16]} UTC", "",
             f"**Subscribers:** {ch.get('subscriberCount')}  |  **Total views:** {ch.get('viewCount')}  |  "
             f"**Videos:** {ch.get('videoCount')}", ""]
    if snap["analytics_status"] == "error":
        lines += ["_Analytics API error — see data/stats_error.txt or the Actions log._", ""]
    elif snap["analytics_status"] == "no_data_yet":
        lines += ["_Analytics connected; YouTube reports watch time/subscribers with a 1–2 day delay._", ""]
    for kind, short in (("Long-form", False), ("Shorts", True)):
        vs = sorted([v for v in snap["videos"] if v["is_short"] == short],
                    key=lambda v: -v.get("views_per_day", 0))
        if not vs:
            continue
        lines += [f"## {kind}", "| Title | Views/day | Views | Watch min | Avg view % | Subs + | Subs/1k |",
                  "|---|---|---|---|---|---|---|"]
        for v in vs:
            lines.append(f"| {v['title'][:60]} | {v.get('views_per_day', 0)} | {v.get('viewCount', 0)} | "
                         f"{v.get('estimatedMinutesWatched', '–')} | {v.get('averageViewPercentage', '–')} | "
                         f"{v.get('subscribersGained', '–')} | {v.get('subs_per_1k_views', '–')} |")
        lines.append("")
    (ROOT / "data" / "growth.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
