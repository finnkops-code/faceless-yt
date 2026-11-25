# faceless-yt — Hidden Ledger Uploader

**[Privacy Policy](PRIVACY.md) · [Terms of Service](TERMS.md)** — This tool uses **YouTube API Services** ([YouTube Terms of Service](https://www.youtube.com/t/terms), [Google Privacy Policy](https://policies.google.com/privacy)). Private single-channel tool for the YouTube channel *Hidden Ledger*; no other users.

Automated long-form explainer channel: script → voice → b-roll + charts → captions → thumbnail → YouTube.

```
Claude (scheduled task)  ──writes──►  content/queue/NNN-slug.json  ──push──►  GitHub Actions
                                                                                 │ render (edge-tts, Pexels, ffmpeg)
                                                                                 ├─ UPLOAD_MODE=release → GitHub Release (browser upload)
                                                                                 └─ UPLOAD_MODE=api     → YouTube Data API (after audit)
data/stats.json  ◄── daily stats snapshot ── feeds topic choice next run
```

- `CONTENT_GUIDE.md` — niche, rules and script schema
- `pipeline/` — render, tts, visuals, thumbnail, upload, stats
- `get_token.py` — one-time OAuth to obtain the refresh token

Local test: `pip install -r requirements.txt && python -m pipeline.render content/queue/<file>.json`

Secrets: `PIXABAY_API_KEY` and/or `PEXELS_API_KEY` (at least one), `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.
Variables: `UPLOAD_MODE` (`release` default, `api` after audit), `MAX_PER_RUN` (default 1).
Optional: drop royalty-free `.mp3` tracks in `assets/music/` (e.g. YouTube Audio Library) for background music.
