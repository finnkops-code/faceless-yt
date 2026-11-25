# Content guide (read before writing any script)

## Channel
Channel: **Price Tag Physics** (@PriceTagPhysics, renamed from Hidden Ledger on 25-11-2026; tagline "The hidden forces behind every price tag"). Long-form (8–12 min) English explainers on **how familiar companies,
industries and everyday things really make money**. Audience: curious US/UK/CA/AU adults, 20–50.
Promise: "The business behind the thing you use every day, explained with real numbers."

## North star: viewers, watch time, subscribers (Finn's end goal — steer on this every run)
Every decision (topic, title, thumbnail, structure, Shorts) is judged by one question:
**will this get more people to click, keep watching, and subscribe?** Revenue follows from these three.
Read `data/growth.md` (scoreboard) and `data/stats.json` before every script and act on it.

**1. Viewers = impressions × click-through.** The topic and the title/thumbnail decide 80% of views.
- Pick topics people already search for or are talking about this week (earnings, price hikes, layoffs,
  launches, viral moments). A famous brand + a surprising mechanism beats an obscure company.
- Title: ≤ 60 chars, one concrete number or paradox, curiosity gap that the video honestly pays off
  ("Costco Barely Profits From Its Products. So How Does It Make $9 Billion?").
  Write 3 title options in the script (`title_options`) and pick the strongest as `title`.
- Thumbnail text 3–5 words, never a repeat of the title; one big number or contrast.
- Every video gets 3 thumbnails for YouTube's "Test & compare" (YouTube picks the one with the most
  watch time): A = split photo + headline (`text`), B = one giant number (`variants` style "number"),
  C = full photo + statement band (`variants` style "band"). Make A, B and C test genuinely different
  angles (e.g. the paradox vs the money vs the product) — not three wordings of the same idea.
  Numbers on thumbnails must be exactly true (no rounding up, no merging two different figures).

**2. Watch time = retention.** Mid-roll ads and recommendations both depend on it.
- First 30 seconds: state the paradox immediately, promise the payoff, no channel intro, no "in this video".
- Open a loop every 60–90 s ("but that's not where the real money is…") and close it later.
- Never let a section run long without a new number, chart, or turn. Cut anything that doesn't move
  the story; 9–11 min of tight story beats 12 min with filler.
- Put the single most surprising fact in the middle third, not the start, to carry viewers through.

**3. Subscribers = a reason to come back.**
- Make it a recognisable series ("How X really makes money") with a consistent promise and look.
- One short, natural subscribe line right after the biggest reveal (not at the start):
  e.g. "If you like seeing the business behind everyday things, that's what this channel does every week."
- End with a question that invites comments + a tease of the next company (builds return visits).
- Shorts are the subscriber funnel: each Short is the best standalone fact of the long video, and its
  description + end card point to the full breakdown.

**Feedback loop (every run, written into the script as `growth_notes`):**
- Compare videos on views/day, average view %, and subs per 1k views (`data/growth.md`).
- Note what the best performer did differently (topic type, title pattern, hook, length) and copy it;
  note the worst and avoid it. With < 5 videos, follow the playbook above and vary ONE thing per video
  (e.g. title framing or topic type) so results teach us something.
- Shorts that outperform point to topics worth a full long-form video.

## Why this niche
- Long-form Education & Science has the strongest verified median RPM in recent creator data and the
  highest share of views that show an ad. Business/finance advertisers bid on this audience.
- It's evergreen, works with stock footage + data charts, and isn't personal financial advice
  (no "buy this stock", no "AI expert" persona). That keeps it clear of YouTube's YMYL / AI-persona issues.

## Monetization rules (YouTube "inauthentic content" policy, July 2026)
Never publish anything that looks mass-produced. Every video MUST have:
1. One central question or paradox in the first 15 seconds (the hook).
2. Real, current, sourced numbers (company filings, earnings releases, government data). Minimum 3 charts.
3. An actual argument: a model/flywheel/mechanism the viewer didn't know, plus a "can it last?" counterpoint.
4. A unique structure: do NOT reuse the same section order or sentence templates across videos.
5. Sources listed in `sources`. If a number can't be verified, leave it out.
No sensational or misleading titles, no distressing content, no fake people or testimonials.

## Topic selection (every run)
1. Read `data/growth.md` + `data/stats.json`: rank by views/day, average view %, subs per 1k views.
   Read `data/comments.md`: companies viewers ask for get priority (we promise this in the pinned comment).
   Lean towards the patterns that win on those three, avoid what flops (see North star above).
2. Check `content/published/` + `content/queue/` so you never repeat a company.
3. Prefer topics with search demand + a fresh news hook (recent earnings, price hike, launch).
   Mix: 60% famous consumer brands (Costco, Netflix, Spotify, IKEA, Ryanair, Starbucks, Nintendo…),
   25% "hidden industries" (why printer ink is expensive, how airlines make money from credit cards),
   15% big-picture explainers (how a stadium gets paid for, why gift cards are pure profit).

## Script format — `content/queue/NNN-slug.json`
```json
{
  "slug": "002-how-ryanair-makes-money",
  "title": "≤ 60 chars, curiosity + specific number, no clickbait lies",
  "title_options": ["3 alternatives considered"],
  "growth_notes": "what the stats told you and which ONE thing this video tests",
  "pinned_comment": "question that invites comments, tied to this video (e.g. 'Would you still pay $65 if...?')",
  "description": "2–3 sentence summary with the main keywords",
  "tags": ["8–15 tags"],
  "category_id": "27",
  "thumbnail": {"text": "3–6 WORDS", "highlight": "WORDS TO COLOR YELLOW", "photo_query": "e.g. Costco warehouse store",
    "variants": [{"style": "number", "number": "$5.9 BILLION", "label": "3–6 words of context"},
                 {"style": "band", "text": "a different angle, 4–7 words", "highlight": "WORD"}]},
  "sections": [
    {"chapter": "optional chapter name", "narration": "...",
     "visuals": ["stock video query", "..."], "images": ["commons:Costco store exterior", "photo query"]},
    {"narration": "...", "visuals": ["..."],
     "callouts": [{"at": "exact words from narration where the number is spoken",
                   "text": "$9.2 billion", "label": "Net income, fiscal 2026"}]},
    {"narration": "...", "visuals": ["..."], "chart": {"type": "bar|hbar|line", "title": "...",
      "subtitle": "optional context", "labels": ["..."], "values": [5.9, 9.2],
      "prefix": "$", "suffix": " billion", "decimals": 1,
      "highlight": "label to color gold (optional)", "source": "short source"}},
    {"title_card": "short big statement", "kicker": "small label", "narration": "..."}
  ],
  "fallback_images": ["commons:<Company> store interior", "commons:<Company> headquarters", "... 6–10 queries"],
  "sources": ["full source names"],
  "shorts": [
    {"title": "≤ 60 chars, one surprising fact (#Shorts is added automatically)",
     "headline": "≤ 8 words shown at the top of the frame",
     "narration": "70–120 words, standalone, first sentence is the hook",
     "visuals": ["subject-first stock query", "..."], "images": ["commons:<Company> ..."],
     "callouts": [{"at": "exact words", "text": "$4.8 billion", "label": "membership fees per year"}],
     "chart": {"optional, same schema as above, plus \"at\": \"exact words\""}}
  ]
}
```
- Total narration **1,350–1,700 words** (≈ 8.5–11 min). Videos under 8:00 get no mid-roll ads.
- 14–20 sections, 60–130 words each. First section has `chapter` (chapters need start at 0:00).
- Write numbers as words in narration where TTS might misread ("twenty twenty-six", "nine point two billion").
- **Every section needs footage — the screen must never be static.** Charts and title cards are
  overlaid on blurred footage, so chart/title sections need `visuals` too.
- `images`: 1–2 photo queries per section where a real thing helps. Prefix `commons:` to search
  Wikimedia Commons for the actual company/place/product (store exteriors, HQ, products, food court);
  without prefix it searches Pexels photos. Only free licenses are used and credits go in the
  description automatically. No logos, no identifiable private people.
- `visuals`: 2–3 concrete, filmable stock-footage queries per section (objects/places/actions, no brand
  logos, no specific people). Pexels has no brand footage — "airplane cabin", not "Ryanair plane".
- End with a CTA asking which company to break down next (comments = topic ideas + engagement).

## Production quality rules (Finn's standard: must feel like a professional, human-made production)
- **Every number that is spoken must be on screen.** Either the section has a `chart`, or each number
  gets a `callouts` entry. `at` = 2–4 consecutive words copied exactly from the narration where the
  number is said (the card appears at that moment). `text` = the number formatted for the eye
  ("$5.9 billion", "92.3%", "84.1 million", "$60 → $65"), `label` = 2–6 words of context.
  Max 3 callouts per section; don't put a callout on a section that already shows the same number in a chart.
- **Charts show full values:** always set `prefix`/`suffix` so labels read "$5.9 billion", never "$5.9".
  Keep labels short (≤ 28 characters). 2–6 data points per chart.
- **Put the subject first in every visual query** ("gas station pumps", "hot dog stand", "checkout cashier"):
  the first two words must appear in the clip's tags or the clip is rejected.
- **Footage must match what is being said in that sentence.** Write literal, filmable queries tied to the
  topic (e.g. "airplane cabin passengers", "supermarket checkout cashier"). Never generic finance filler
  ("money counting", "stock market screen", "trading chart") — those return crypto/bitcoin footage.
  Crypto, bitcoin and trading imagery are blocked unless the video is about them.
- `fallback_images` (required): 6–10 `commons:` queries for real photos of the company/industry. Stock
  clips are only used when their tags match at least two words of the query; whatever is still missing
  is filled from these real photos, so the screen never shows unrelated filler.
- Prefer real photos of the company via `images` with `commons:` (stores, HQ, products, food) — they
  make the video feel specific instead of stock.
- Use `title_card` max 2× per video (hook statement + one key insight). Chapters get an automatic
  numbered label; first section is the cold-open hook, then the Price Tag Physics ident plays automatically.
- No word-by-word burned captions in long-form (subtitles go up as a separate SRT track).

## Shorts (every video: 3, max 3)
- Each Short is a standalone 30–50 s story built on ONE striking number or twist from the long video.
  Never a trailer ("watch the full video to find out") — it must pay off on its own; the closing card
  pointing to the full breakdown is added automatically.
- Hook in the first sentence, no intro, no greeting. End on the payoff line.
- Same rules as long-form: every spoken number gets a callout or the chart, subject-first visual
  queries, `commons:` photos of the real company. 3–5 visual/image queries per Short.
- Avoid ambiguous stock queries ("hot dog" returns dogs): for food/products of the company, use `commons:` images.
- Rendered vertically (1080×1920) with big burned-in captions (Shorts are mostly watched muted).
- They publish one per day after the long video and link to it.

## Subtitles
Every long video and Short gets a clean English SRT (2 lines, ≤ 42 chars) uploaded as a caption
track — long-form has no burned-in captions, Shorts do.

## Translations (every video + its Shorts)
After the video is published (its YouTube ID is in data/<slug>.youtube.json or given by Finn), write
content/localize/<videoId>.json with translated title + 2–3 sentence summary in es, pt, de and hi
(natural, not literal; keep numbers exactly; end the summary with "(Video in English, with subtitles.)"
in that language). The workflow applies them automatically; viewers in those languages see their own.

## Automatic visual QA
Every downloaded stock clip/photo is checked with an open-source CLIP model: if it looks more like an
off-topic concept (dog, lake, cartoon, crypto chart, empty shelves, landscape...) than like its query,
it is rejected and the next candidate is used. Thumbnail photos are ranked by how well they show the
subject (`thumbnail.photo_query`, e.g. "Costco warehouse store", defaults to the title). Each release
contains `qa_sheet.jpg` (a frame every 20 s) and `qa_log.txt` (what was rejected) for review.
Still write precise, subject-first queries: QA catches mistakes, it doesn't fix vague queries.

## End screen + pinned comment (every long video)
- End screen (last 20 s): template "1 video, 1 subscribe", video = "Best for viewer". The narration's
  last ~20 s should be the closing question + tease, with no new facts, so nothing important is covered.
- Pinned comment: one specific question tied to the video that invites an answer (not "like and
  subscribe"). Rotate: topic request / opinion question / "what surprised you most?".

## Cadence
2 videos per week (Mon + Thu publish). Quality over volume.

## Voice
Kokoro `bm_fable` (British male), chosen by Finn. Do not set `voice` per script unless asked.
