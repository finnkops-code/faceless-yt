# Content guide (read before writing any script)

## Channel
Working name: **Hidden Ledger**. Long-form (8–12 min) English explainers on **how familiar companies,
industries and everyday things really make money**. Audience: curious US/UK/CA/AU adults, 20–50.
Promise: "The business behind the thing you use every day, explained with real numbers."

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
1. Read `data/stats.json` (if present): which videos got the best views per day since publish & likes.
   Lean towards the patterns that work (company type, title framing), avoid what flops.
2. Check `content/published/` + `content/queue/` so you never repeat a company.
3. Prefer topics with search demand + a fresh news hook (recent earnings, price hike, launch).
   Mix: 60% famous consumer brands (Costco, Netflix, Spotify, IKEA, Ryanair, Starbucks, Nintendo…),
   25% "hidden industries" (why printer ink is expensive, how airlines make money from credit cards),
   15% big-picture explainers (how a stadium gets paid for, why gift cards are pure profit).

## Script format — `content/queue/NNN-slug.json`
```json
{
  "slug": "002-how-ryanair-makes-money",
  "title": "≤ 70 chars, curiosity + specific number, no clickbait lies",
  "description": "2–3 sentence summary with the main keywords",
  "tags": ["8–15 tags"],
  "category_id": "27",
  "thumbnail": {"text": "3–6 WORDS", "highlight": "WORDS TO COLOR YELLOW"},
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
  numbered label; first section is the cold-open hook, then the Hidden Ledger ident plays automatically.
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

## Cadence
2 videos per week (Mon + Thu publish). Quality over volume.

## Voice
Kokoro `bm_fable` (British male), chosen by Finn. Do not set `voice` per script unless asked.
