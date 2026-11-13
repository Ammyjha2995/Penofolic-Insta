"""Text for the 8 AM carousel and the 8 PM Reel.

Claude (optional, ANTHROPIC_API_KEY) writes hooks, summaries, questions, voiceover lines and hashtag
ideas from the feed text only. Any generated sentence containing a number that is not in the source is
discarded and replaced by a safe fallback. Every post gets exactly 5 hashtags.
"""
import json, os, re, logging
import requests
from . import figures

log = logging.getLogger("feedbot")
API = "https://api.anthropic.com/v1/messages"
NUM = re.compile(r"\d[\d,.]*")

RULES = """Audience: Indian students, exam aspirants, professionals and policymakers.
Tone: precise, neutral, plain English, no hype, no emojis, no investment advice.
STRICT: use ONLY facts in the given TITLE and TEXT. Never add numbers, dates, names or causes not stated there.
Copy numbers exactly as written. Paraphrase; do not copy sentences. "why" lines describe likely effects, not certainties."""

CAROUSEL = RULES + """

You write Penofolic's 8 AM Instagram carousel (3 stories). Return ONLY JSON:
{"question": "cover hook question, max 10 words, about story 1",
 "caption_hook": "first caption line, max 110 characters, a number or bold claim + a question",
 "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
 "stories": [{"id": 1, "hook": "headline in own words, max 12 words", "points": ["max 18 words", "max 18 words"],
              "why": "max 24 words; for WORLD stories: the likely channel to India", "label": "2-3 word tile label",
              "impact": [["Rupee", "Low|Medium|High"], ["Exports", "..."], ["Interest rates", "..."]]}]}
"impact" only for WORLD stories (3 channels most relevant to the story). Hashtags: 4 specific, widely used tags
(2 topic + 2 audience such as #UPSC), no spaces, not #Penofolic.

STORIES:
"""

REEL = RULES + """

You write Penofolic's 8 PM Instagram Reel about ONE story (about 25 seconds, English voiceover). Return ONLY JSON:
{"question": "hook question, max 10 words", "headline": "max 12 words", "points": ["max 16 words", "max 16 words"],
 "why": "max 26 words, why it matters to an ordinary Indian", "chart_title": "max 6 words",
 "caption_hook": "first caption line, max 110 characters", "hashtags": ["#Tag1", "#Tag2", "#Tag3", "#Tag4"],
 "vo": {"hook": "spoken, max 16 words", "what": "spoken, max 30 words", "chart": "spoken, max 20 words",
        "why": "spoken, max 28 words"}}
Write voiceover for the ear: short sentences, say "rupees 14.42 trillion" not "₹14.42 tn".

STORY:
"""


def _nums(text):
    return {n.rstrip(".,").replace(",", "") for n in NUM.findall(text or "")}


def _safe(text, src):
    return bool(text) and all(n in src for n in _nums(text))


def _trim(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def _first_sentence(summary, title):
    sent = re.split(r"(?<=[.!?])\s+", (summary or "").strip())[0]
    if not sent or len(set(sent.lower().split()) - set(title.lower().split())) < 4:
        return []
    return [_trim(sent, 150)]


def _ask(prompt, cfg):
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not (cfg["ai"].get("enabled") and key):
        log.info("AI off: using headline-based text")
        return None
    try:
        r = requests.post(API, timeout=120, headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                                     "content-type": "application/json"},
                          json={"model": cfg["ai"]["model"], "max_tokens": cfg["ai"]["max_tokens"],
                                "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        text = "".join(b.get("text", "") for b in r.json()["content"])
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as ex:
        log.warning("AI failed (%s): using headline-based text", ex)
        return None


def _block(i, s):
    return (f"[{i}] REGION: {s.get('region', 'india').upper()}\nSOURCE: {s.get('source') or s['sources'][0]}\n"
            f"TITLE: {s['title']}\nTEXT: {s.get('summary') or '(none)'}")


def hashtags(cfg, stories, suggested):
    p = cfg["post"]
    out, seen = [p.get("hashtag_brand", "#Penofolic")], set()
    seen.add(out[0].lower())

    def add(tag):
        tag = "#" + re.sub(r"[^A-Za-z0-9_]", "", tag.lstrip("#"))
        if len(tag) > 2 and tag[1].isalpha() and tag.lower() not in seen and len(out) < 5:
            seen.add(tag.lower())
            out.append(tag)

    for t in suggested or []:
        add(t)
    lead = stories[0]
    for t in cfg.get("category_tags", {}).get(lead.get("category"), []):
        add(t)
    aud = p.get("hashtags_audience_world" if lead.get("region") == "world" else "hashtags_audience_india", [])
    for t in aud:
        add(t)
    for s in stories[1:]:
        for t in cfg.get("category_tags", {}).get(s.get("category"), []):
            add(t)
    return out[:5]


# ------------------------------------------------------------ carousel
def carousel(stories, cfg):
    data = _ask(CAROUSEL + "\n\n".join(_block(i, s) for i, s in enumerate(stories, 1)), cfg) or {}
    by_id = {int(x.get("id", 0)): x for x in data.get("stories", []) if isinstance(x, dict)}
    for i, s in enumerate(stories, 1):
        src = _nums(s["title"] + " " + s.get("summary", ""))
        g = by_id.get(i, {})
        s["fig"] = figures.pick(s)
        s["hook"] = _trim(g.get("hook"), 110) if _safe(g.get("hook"), src) else _trim(s["title"], 110)
        s["points"] = [_trim(p, 150) for p in g.get("points", [])[:2] if _safe(p, src)] or _first_sentence(s.get("summary"), s["title"])
        s["why"] = _trim(g.get("why"), 190) if _safe(g.get("why"), src) else ""
        lab = g.get("label") or " ".join(s["hook"].split()[:3])
        s["label"] = _trim(lab, 28) if not _nums(lab) or _safe(lab, src) else " ".join(s["hook"].split()[:3])
        imp = [(str(a)[:24], b) for a, b in (g.get("impact") or []) if b in ("Low", "Medium", "High")][:3]
        if s.get("region") == "world" and imp:
            s["fig"] = dict(s["fig"], kind="impact", impact=imp)
    lead = stories[0]
    lsrc = _nums(lead["title"] + " " + lead.get("summary", ""))
    q = data.get("question")
    question = _trim(q, 80) if _safe(q, lsrc) else "What does it mean for you?"
    ch = data.get("caption_hook")
    allsrc = set().union(*(_nums(s["title"] + " " + s.get("summary", "")) for s in stories))
    cap_hook = _trim(ch, 120) if _safe(ch, allsrc) else (
        f"{lead['fig']['figure']}: {lead['hook']}" if lead["fig"].get("figure") else lead["hook"])
    return {"question": question, "caption_hook": cap_hook, "hashtags": hashtags(cfg, stories, data.get("hashtags"))}


def caption_carousel(stories, meta, date_str):
    lines = [meta["caption_hook"], "", f"The Daily Brief · {date_str}", ""]
    for i, s in enumerate(stories, 1):
        lines.append(f"{i}. {s['hook']} ({', '.join(s['sources'][:2])})")
    lines += ["", "Swipe for the numbers and why each one matters.",
              "Which story affects you most? Comment 1, 2 or 3 👇", "",
              "Summaries by Penofolic from public reports. Not investment advice.", "",
              " ".join(meta["hashtags"])]
    return "\n".join(lines)[:2150]


# ------------------------------------------------------------ reel
def reel(story, cfg):
    s = story
    src = _nums(s["title"] + " " + s.get("summary", ""))
    fig = figures.pick(s)
    g = _ask(REEL + _block(1, s), cfg) or {}

    def ok(key, n, fallback):
        v = g.get(key)
        return _trim(v, n) if _safe(v, src) else fallback

    headline = ok("headline", 110, _trim(s["title"], 110))
    points = [_trim(p, 140) for p in (g.get("points") or [])[:2] if _safe(p, src)] or _first_sentence(s.get("summary"), s["title"])
    why = ok("why", 200, "")
    vo = g.get("vo") or {}
    vos = {k: (_trim(vo.get(k), 220) if _safe(vo.get(k), src) else "") for k in ("hook", "what", "chart", "why")}
    if not vos["what"]:
        vos["what"] = headline
    if not vos["hook"]:
        vos["hook"] = "Here is tonight's big economic story."
    if fig["kind"] == "impact":
        fig = dict(fig, kind="keyword")
    return {
        "fig": fig, "tag": ("WORLD · " if s.get("region") == "world" else "INDIA · ") + s["category"].upper(),
        "question": ok("question", 80, "What does it mean for you?"), "headline": headline, "points": points,
        "why": why, "chart_title": ok("chart_title", 40, _trim(" ".join(headline.split()[:6]), 40)),
        "source": ", ".join(s["sources"][:2]), "vo": vos,
        "caption_hook": ok("caption_hook", 120, (f"{fig['figure']}: " if fig.get("figure") else "") + headline),
        "hashtags": hashtags(cfg, [s], g.get("hashtags")),
    }


def caption_reel(r, date_str):
    lines = [r["caption_hook"], ""] + ([r["headline"], ""] if r["headline"] not in r["caption_hook"] else [])
    lines += [f"• {p}" for p in r["points"]] or [""]
    if r["why"]:
        lines += ["", "Why it matters: " + r["why"]]
    lines += ["", f"Source: {r['source']} · {date_str}", "Follow for daily economics, explained. Not investment advice.", "",
              " ".join(r["hashtags"])]
    return "\n".join(lines)[:2150]
