"""Upload a rendered video to YouTube via the Data API v3.

Needs env: YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
NOTE: until the Google Cloud project passes YouTube's API audit, every API upload is
locked to private. Set repo variable UPLOAD_MODE=api only after the audit is approved.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]
# captions.insert additionally needs youtube.force-ssl. Re-run get_token.py once to grant it;
# until then captions are skipped (the SRT is still in the release for manual upload).
CAPTION_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"


def creds():
    return Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"],
                       token_uri="https://oauth2.googleapis.com/token",
                       client_id=os.environ["YT_CLIENT_ID"],
                       client_secret=os.environ["YT_CLIENT_SECRET"])


def client():
    # no explicit scopes: the refreshed token gets every scope that was granted
    # (upload, readonly, force-ssl for captions/comments/localizations, yt-analytics)
    return build("youtube", "v3", credentials=creds(), cache_discovery=False)

def next_slot(hour_utc=15):
    """Default publish time: next day at 15:00 UTC (US morning)."""
    now = datetime.now(timezone.utc)
    slot = (now + timedelta(days=1)).replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    return slot.isoformat().replace("+00:00", "Z")


def add_captions(yt, vid, srt: Path):
    if not srt.exists():
        return
    try:
        yt.captions().insert(part="snippet", body={"snippet": {
            "videoId": vid, "language": "en", "name": "English", "isDraft": False}},
            media_body=MediaFileUpload(str(srt), mimetype="application/octet-stream")).execute()
        print("  captions uploaded")
    except Exception as e:
        print(f"  captions skipped (token lacks youtube.force-ssl?): {e}")


def upload(out_dir: Path, meta=None, publish_at=None, shorts=True):
    meta = meta or json.loads((out_dir / "metadata.json").read_text())
    yt = client()
    publish_at = publish_at or meta.get("publish_at") or next_slot()
    body = {
        "snippet": {"title": meta["title"], "description": meta["description"],
                    "tags": meta["tags"], "categoryId": meta["category_id"],
                    "defaultLanguage": "en", "defaultAudioLanguage": "en"},
        "status": {"privacyStatus": "private", "publishAt": publish_at,
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": False,
                   "embeddable": True},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(out_dir / "video.mp4"),
                                                        chunksize=8 << 20, resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"  upload {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"  uploaded https://youtu.be/{vid} (publishes {publish_at})")
    thumb = out_dir / "thumbnail.jpg"
    if thumb.exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:  # requires a phone-verified channel
            print(f"  thumbnail not set: {e}")
    add_captions(yt, vid, out_dir / "captions.srt")
    if meta.get("pinned_comment"):
        try:  # posted as the channel; pinning itself is a Studio-only action (done in the browser)
            yt.commentThreads().insert(part="snippet", body={"snippet": {"videoId": vid, "topLevelComment": {
                "snippet": {"textOriginal": meta["pinned_comment"]}}}}).execute()
            print("  comment posted (pin it in Studio)")
        except Exception as e:
            print(f"  comment not posted: {e}")
    rec = {"id": vid, "publish_at": publish_at, "shorts": []}
    if shorts:
        # Shorts go out one per day after the long video, each linking back to it.
        base = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        for k, sdir in enumerate(sorted(out_dir.glob("short_*"))):
            if not (sdir / "video.mp4").exists():
                continue
            sm = json.loads((sdir / "metadata.json").read_text())
            sm["description"] = sm["description"].replace("{LONG_URL}", f"https://youtu.be/{vid}")
            when = (base + timedelta(days=k + 1, hours=-2)).isoformat().replace("+00:00", "Z")
            rec["shorts"].append(upload(sdir, meta=sm, publish_at=when, shorts=False))
    (out_dir / "youtube.json").write_text(json.dumps(rec))
    return vid


if __name__ == "__main__":
    upload(Path(sys.argv[1]))
