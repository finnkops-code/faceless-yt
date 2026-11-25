"""Run ONCE on your own computer to get the YouTube refresh token.

1. Download the OAuth client JSON (type: Desktop app) from Google Cloud → save as client_secret.json here
2. pip install google-auth-oauthlib
3. python get_token.py  → a browser opens, log in with the CHANNEL's Google account
4. Copy the three printed values into GitHub → Settings → Secrets → Actions
"""
import json

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
cfg = json.load(open("client_secret.json"))
cfg = cfg.get("installed") or cfg.get("web")
print("\nYT_CLIENT_ID     =", cfg["client_id"])
print("YT_CLIENT_SECRET =", cfg["client_secret"])
print("YT_REFRESH_TOKEN =", creds.refresh_token)
