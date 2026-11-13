"""Fetch economics RSS feeds, rank stories by relevance, coverage and recency."""
import html, re, time, hashlib, logging
from datetime import datetime, timedelta, timezone
import feedparser, requests

log = logging.getLogger("feedbot")
UA = {"User-Agent": "Mozilla/5.0 (compatible; PenofolicFeedBot/1.0; +https://penofolic.pages.dev)"}
STOP = set("a an the of to in on for and or with by at from as is are was be has have its it this that after over into amid says said new india india's indian govt government crore lakh rs per cent".split())


def clean(text):
    text = text or ""
    for _ in range(2):
        text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _kw_regex(kw):
    if kw != kw.lower():  # acronyms and names (RBI, Fed, Bank of England): case-sensitive
        return re.compile(r"(?<![A-Za-z])" + re.escape(kw) + r"(?![A-Za-z])")
    return re.compile(r"(?<![A-Za-z])" + re.escape(kw) + r"s?(?![A-Za-z])", re.I)


def tokens(title):
    words = re.findall(r"[a-z0-9₹%]+", title.lower())
    return {w for w in words if w not in STOP and len(w) > 2}


def signature(title):
    return hashlib.sha1(" ".join(sorted(tokens(title))).encode()).hexdigest()[:12]


def _published(entry, tz):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            dt = datetime(*t[:6], tzinfo=timezone.utc)
            raw = entry.get(key.replace("_parsed", ""), "")
            # feeds without a timezone (e.g. RBI) are in IST, not UTC
            if raw and not re.search(r"([+-]\d{4}|GMT|UTC|Z)\s*$", raw.strip()):
                dt = dt.replace(tzinfo=tz)
            return dt
    return None


def fetch(cfg, tz):
    stories = []
    for f in cfg["feeds"]:
        try:
            r = requests.get(f["url"], headers=UA, timeout=25)
            r.raise_for_status()
            parsed = feedparser.parse(r.content)
            n = 0
            for e in parsed.entries:
                title = clean(e.get("title"))
                if not title:
                    continue
                src = f["name"]
                if f.get("aggregator"):  # Google News: "Headline - Publisher"
                    pub = (e.get("source") or {}).get("title") or ""
                    if " - " in title:
                        title, tail = title.rsplit(" - ", 1)
                        pub = pub or tail
                    src = pub.strip() or src
                stories.append({
                    "title": title,
                    "summary": clean(e.get("summary") or e.get("description"))[:900],
                    "link": e.get("link", ""),
                    "source": src,
                    "source_weight": float(f.get("weight", 0)),
                    "region": f.get("region", "india"),
                    "published": _published(e, tz),
                })
                n += 1
            log.info("feed ok  %-18s %3d items", f["name"], n)
        except Exception as ex:  # one bad feed must not stop the run
            log.warning("feed FAIL %-18s %s", f["name"], ex)
    return stories


def fetch_trends(cfg):
    """Google Trends daily searches (India): search terms + their news headlines, as token sets."""
    url = cfg.get("trends", {}).get("url")
    if not url:
        return []
    try:
        r = requests.get(url, headers=UA, timeout=25)
        r.raise_for_status()
        terms = []
        for e in feedparser.parse(r.content).entries:
            words = tokens(clean(e.get("title")))
            for k, v in e.items():
                if k.startswith("ht_news_item_title"):
                    words |= tokens(clean(v))
            if words:
                terms.append(words)
        log.info("trends ok %d topics", len(terms))
        return terms
    except Exception as ex:
        log.warning("trends FAIL %s", ex)
        return []


def trend_boost(story_tokens, trends, cap):
    hits = sum(1 for t in trends if len(story_tokens & t) >= 2)
    return min(cap, 3.0 * hits)


def score_and_pick(stories, cfg, posted_sigs, now, trends=(), quota=None):
    p = cfg["post"]
    window = timedelta(hours=p["lookback_hours"])
    excl = [x.lower() for x in cfg.get("exclude", [])]
    cats = {c: [(_kw_regex(k), w) for k, w in kws.items()] for c, kws in cfg["categories"].items()}

    fresh = []
    seen_links = set()
    for s in stories:
        if s["link"] in seen_links:
            continue
        seen_links.add(s["link"])
        if s["published"] and now - s["published"] > window:
            continue
        low = (s["title"] + " " + s["summary"]).lower()
        if any(x in low for x in excl) or len(s["title"]) < 25:
            continue
        cat_scores = {}
        for c, pats in cats.items():
            sc = sum(w * (2 if rx.search(s["title"]) else 1) for rx, w in pats if rx.search(s["title"]) or rx.search(s["summary"]))
            if sc:
                cat_scores[c] = sc
        if not cat_scores:
            continue
        s["category"] = max(cat_scores, key=cat_scores.get)
        s["topic_score"] = sum(cat_scores.values())
        s["tokens"] = tokens(s["title"])
        s["sig"] = signature(s["title"])
        fresh.append(s)

    # cluster near-duplicate headlines across sources (coverage = trending signal)
    clusters = []
    for s in sorted(fresh, key=lambda x: -x["topic_score"]):
        for c in clusters:
            a, b = s["tokens"], c[0]["tokens"]
            if a and b and len(a & b) / len(a | b) >= 0.34:
                c.append(s)
                break
        else:
            clusters.append([s])

    ranked = []
    for c in clusters:
        lead = max(c, key=lambda x: (x["source_weight"], len(x["summary"])))
        age_h = min(((now - x["published"]).total_seconds() / 3600 for x in c if x["published"]), default=p["lookback_hours"] / 2)
        recency = max(0.0, 1 - age_h / p["lookback_hours"]) * 2
        sources = sorted({x["source"] for x in c})
        tb = trend_boost(set().union(*(x["tokens"] for x in c)), trends, cfg.get("trends", {}).get("max_boost", 6))
        score = lead["topic_score"] + 1.5 * (len(sources) - 1) + recency + lead["source_weight"] + tb
        if any(x["sig"] in posted_sigs for x in c) or score < p["min_score"]:
            continue
        region = "world" if any(x["region"] == "world" for x in c) else "india"
        lead = dict(lead, score=round(score, 2), sources=sources, region=region, trending=tb > 0,
                    links=[x["link"] for x in c], all_sigs=[x["sig"] for x in c])
        ranked.append(lead)
    ranked.sort(key=lambda x: -x["score"])

    quota = quota or {"india": int(p.get("india_stories", 2)), "world": int(p.get("world_stories", 1))}
    total = min(sum(quota.values()), 8)  # Instagram carousel: 10 slides incl. cover + closing

    def take(pool, n, picked, per_cat):
        for s in pool:
            if len([x for x in picked if x in pool]) >= n or len(picked) >= total:
                break
            if s in picked or per_cat.get(s["category"], 0) >= p["max_per_category"]:
                continue
            per_cat[s["category"]] = per_cat.get(s["category"], 0) + 1
            picked.append(s)

    picked, per_cat = [], {}
    for reg in ("india", "world"):
        take([s for s in ranked if s["region"] == reg], quota[reg], picked, per_cat)
    take(ranked, total, picked, per_cat)  # if one region is thin, fill from the other
    picked.sort(key=lambda s: (s["region"] != "india", -s["score"]))
    for s in picked:
        s.pop("tokens", None)
    return picked
