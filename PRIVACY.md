# Hidden Ledger Uploader — Privacy Policy

_Last updated: 25 November 2026_

Hidden Ledger Uploader is a private, single-user tool operated by Finn Kops for his own YouTube channel
"Price Tag Physics" (formerly "Hidden Ledger"). It is not offered to the public and has no other users.

## What the tool accesses
Through the YouTube Data API, with the channel owner's explicit OAuth consent, the tool:
- uploads videos, titles, descriptions and thumbnails to the owner's own channel (`youtube.upload`);
- reads public statistics of the owner's own videos and channel (`youtube.readonly`) to decide which topics to make next.

## What is stored
- An OAuth refresh token, stored as an encrypted GitHub Actions secret. It is used only to act on the owner's channel.
- Aggregated public statistics (views, likes, comment counts per video) stored in `data/stats.json` in this repository.

No personal data of viewers or any other user is collected, stored, sold or shared.

## Revoking access
The owner can revoke access at any time at https://myaccount.google.com/permissions.

## Contact
finnkops@gmail.com

The tool's use of information received from Google APIs adheres to the
[Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
including the Limited Use requirements, and to the [YouTube API Services Terms of Service](https://developers.google.com/youtube/terms/api-services-terms-of-service).
YouTube's Terms of Service apply: https://www.youtube.com/t/terms — Google Privacy Policy: https://policies.google.com/privacy
