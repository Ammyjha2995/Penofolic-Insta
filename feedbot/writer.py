"""Turn picked stories into card text and an Instagram caption.

With an ANTHROPIC_API_KEY, Claude writes short, plain-English summaries using ONLY facts in the
feed text; any sentence containing a number not present in the source is discarded.
Without a key, cards use the headline only.
"""
import json, os, re, logging
import requests

log = logging.getLogger("feedbot")
API = "https://api.anthropic.com/v1/messages"

PROMPT = """You write the daily "Economy Today" Instagram carousel for Penofolic, an Indian economics and policy advisory firm.
Audience: students, professionals and policymakers. Tone: precise, neutral, plain English, no hype, no emojis, no investment advice.

For EACH story below write:
- "hook": the story in at most 12 words (a headline in your own words, not copied)
- "points": 2 short factual bullets, each at most 18 words
- "why": one sentence, at most 24 words, on why it matters. For INDIA stories: for India's economy, households or businesses.
  For WORLD stories: the likely channel to India (e.g. rupee, capital flows, exports, oil import bill, interest rates), stated as a possibility, not a fact

STRICT RULES:
- Use ONLY facts stated in that story's TITLE and TEXT. Never add numbers, dates, names or causes that are not there.
- Copy every number exactly as written in the source (e.g. "₹14.42 trillion", "11.8%").
- Do not reuse the source's sentences; paraphrase.
- If the text is too thin for 2 points, give 1.

Also write "cover": a 4-7 word title for the carousel cover that captures today's main theme.

Return ONLY JSON: {"cover": "...", "stories": [{"id": 1, "hook": "...", "points": ["..",".."], "why": "..."}, ...]}

STORIES:
"""

NUM = re.compile(r"\d[\d,.]*")


def _nums(text):
    return {n.rstrip(".,").replace(",", "") for n in NUM.findall(text)}


def _safe(text, source_nums):
    """Reject a generated sentence that contains a number not in the source."""
    return all(n in source_nums for n in _nums(text))


def _trim(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def _first_sentence(summary, title):
    sent = re.split(r"(?<=[.!?])\s+", summary.strip())[0] if summary else ""
    t = set(title.lower().split())
    if not sent or len(set(sent.lower().split()) - t) < 4:  # adds nothing beyond the headline
        return []
    return [_trim(sent, 160)]


def fallback(stories):
    for s in stories:
        s["hook"] = _trim(s["title"], 110)
        s["points"], s["why"] = _first_sentence(s.get("summary", ""), s["title"]), ""
    return "What moved the economy today"


def write(stories, cfg):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not (cfg["ai"].get("enabled") and key):
        log.info("AI off (no ANTHROPIC_API_KEY): using headlines")
        return fallback(stories)
    block = "\n\n".join(f"[{i}] REGION: {s.get('region', 'india').upper()}\nSOURCE: {s['source']}\nTITLE: {s['title']}\nTEXT: {s['summary'] or '(none)'}"
                        for i, s in enumerate(stories, 1))
    try:
        r = requests.post(API, timeout=90, headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": cfg["ai"]["model"], "max_tokens": cfg["ai"]["max_tokens"],
                  "messages": [{"role": "user", "content": PROMPT + block}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as ex:
        log.warning("AI failed (%s): using headlines", ex)
        return fallback(stories)

    by_id = {int(x.get("id", 0)): x for x in data.get("stories", [])}
    for i, s in enumerate(stories, 1):
        src = _nums(s["title"] + " " + s["summary"])
        g = by_id.get(i, {})
        hook = g.get("hook", "")
        s["hook"] = _trim(hook, 110) if hook and _safe(hook, src) else _trim(s["title"], 110)
        s["points"] = [_trim(p, 150) for p in g.get("points", [])[:2] if p and _safe(p, src)] or _first_sentence(s["summary"], s["title"])
        why = g.get("why", "")
        s["why"] = _trim(why, 190) if why and _safe(why, src) else ""
    cover = _trim(data.get("cover", ""), 60)
    return cover if cover and not _nums(cover) else "What moved the economy today"


def caption(stories, cover, cfg, date_str):
    b = cfg["brand"]
    lines = [f"Economy Today · {date_str}", cover, ""]
    for reg, label in (("india", "INDIA"), ("world", "WORLD")):
        sec = [(i, s) for i, s in enumerate(stories, 1) if s.get("region", "india") == reg]
        if sec:
            lines.append(label)
            lines += [f"{i}. {s['hook']}" for i, s in sec]
            lines.append("")
    lines.pop()
    lines += ["", "Swipe through for the key facts and why each one matters.", "",
              "Sources: " + ", ".join(sorted({x for s in stories for x in s['sources']})) +
              ". Summaries by Penofolic; read the original reports for full details. Not investment advice.", "",
              f"Follow {b['handle']} for a daily economics briefing.", b["website"], ""]
    tags = list(cfg["post"]["hashtags_base"])
    extra = {"Monetary policy": ["#RBI", "#MonetaryPolicy"], "Inflation": ["#Inflation", "#CPI"],
             "Growth": ["#GDP", "#EconomicGrowth"], "Fiscal": ["#PublicFinance", "#Budget"],
             "Trade": ["#Trade", "#Exports"], "Markets": ["#Rupee", "#Markets"],
             "Banking": ["#Banking", "#Finance"], "Jobs": ["#Jobs", "#Employment"],
             "Infrastructure": ["#Infrastructure"], "Investment": ["#Investment"]}
    if any(s.get("region") == "world" for s in stories):
        tags += ["#GlobalEconomy", "#WorldEconomy"]
    for s in stories:
        for t in extra.get(s["category"], []):
            if t not in tags:
                tags.append(t)
    lines.append(" ".join(tags[:15]))
    return "\n".join(lines)[:2150]
