"""Turn spelled-out numbers from the narration back into digits for subtitles.
'two hundred ninety seven billion dollars' -> '$297 billion', 'ninety two percent' -> '92%',
'twenty twenty six' -> '2026', 'one dollar fifty' -> '$1.50'."""
import re

UNITS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                     "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split())}
SCALES = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
NUMW = set(UNITS) | set(TENS) | {"hundred", "point"}


def _int(words):
    total, cur = 0, 0
    for w in words:
        if w in UNITS:
            cur += UNITS[w]
        elif w in TENS:
            cur += TENS[w]
        elif w == "hundred":
            cur = (cur or 1) * 100
    return total + cur


def _year(words):
    """'nineteen eighties' / 'twenty twenty six' -> year form, else None."""
    if len(words) >= 2 and words[0] in ("nineteen", "twenty") and (words[1] in TENS or words[1] in UNITS) \
            and "hundred" not in words:
        hi = 19 if words[0] == "nineteen" else 20
        lo = _int(words[1:])
        if 10 <= lo <= 99:
            return f"{hi}{lo:02d}"
    return None


def digits(text):
    toks = re.findall(r"[A-Za-z']+|[^A-Za-z']+", text)
    out, i = [], 0
    while i < len(toks):
        w = toks[i].lower()
        if w in NUMW - {"point", "hundred"}:
            j, run = i, []
            while j < len(toks) and (toks[j].lower() in NUMW or toks[j] == " "):
                if toks[j] != " ":
                    run.append(toks[j].lower())
                j += 1
            while toks[j - 1] == " ":
                j -= 1
            if run[-1] == "point":
                run.pop(); j -= 2
            yr = _year(run)
            if "point" in run:
                k = run.index("point")
                val = f"{_int(run[:k])}." + "".join(str(UNITS.get(x, TENS.get(x, 0))) for x in run[k + 1:])
            elif yr and len(run) <= 3 and not any(s in run for s in ("hundred",)):
                val = yr
            else:
                val = str(_int(run))
            rest = toks[j:]
            nxt = rest[1].lower() if len(rest) > 1 else ""
            nn = rest[3].lower() if len(rest) > 3 else ""
            if nxt in SCALES and nn in ("dollars", "dollar"):
                out.append(f"${val} {nxt}"); i = j + 4; continue
            if nxt in ("dollars", "dollar"):
                if nn in UNITS or nn in TENS:      # 'one dollar fifty'
                    out.append(f"${val}.{_int([nn]):02d}"); i = j + 4; continue
                out.append(f"${val}"); i = j + 2; continue
            if nxt == "percent":
                out.append(f"{val}%"); i = j + 2; continue
            if nxt == "eighties" and val in ("19",):
                out.append("1980s"); i = j + 2; continue
            out.append(val if (len(run) > 1 or int(float(val)) >= 10 or nxt in SCALES) else toks[i])
            i = j
            continue
        out.append(toks[i]); i += 1
    return "".join(out)
