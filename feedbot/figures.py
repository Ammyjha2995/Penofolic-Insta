"""Pick an infographic for a story using ONLY numbers found in the source text.

kinds:
  bars    two comparable values (before -> after), or a level + % growth (previous value implied)
  ring    a single percentage
  impact  world story: AI-rated impact on India (Low/Medium/High per channel)
  keyword no usable numbers: typographic slide
"""
import re

MAG = {"lakh crore": ("lakh cr", 1e12), "trillion": ("tn", 1e12), "tn": ("tn", 1e12), "billion": ("bn", 1e9),
       "bn": ("bn", 1e9), "million": ("mn", 1e6), "mn": ("mn", 1e6), "crore": ("cr", 1e7), "cr": ("cr", 1e7),
       "lakh": ("lakh", 1e5)}
CUR = r"(₹|Rs\.?\s?|INR\s?|US\$|\$|€|£)"
AMT = re.compile(CUR + r"\s?([\d,]+(?:\.\d+)?)\s?(lakh crore|trillion|billion|million|crore|lakh|tn|bn|mn|cr)?\b", re.I)
PCT = re.compile(r"(-?\d+(?:\.\d+)?)\s?(?:%|per ?cent)", re.I)
FROM_TO = re.compile(r"from\s+(\d+(?:\.\d+)?)\s?(?:%|per ?cent)?\s+(?:in\s+\w+\s+)?to\s+(\d+(?:\.\d+)?)\s?(%|per ?cent)", re.I)
TO_FROM = re.compile(r"to\s+(\d+(?:\.\d+)?)\s?(%|per ?cent)\s+(?:in\s+\w+\s+)?from\s+(\d+(?:\.\d+)?)", re.I)
UPW = re.compile(r"\b(rise|rises|rose|climb|climbs|jump|jumps|surge|surges|grow|grows|grew|up|higher|increase|increases|widen|widens|gain|gains|hike)\b", re.I)
DOWNW = re.compile(r"\b(fall|falls|fell|decline|declines|drop|drops|ease|eases|eased|slip|slips|down|lower|cut|cuts|narrow|narrows|shrink|slows|dip|dips)\b", re.I)


def _cur(sym):
    sym = sym.strip().upper().replace(".", "")
    return "₹" if sym in ("₹", "RS", "INR") else ("$" if "$" in sym else sym)


def amounts(text):
    out = []
    for m in AMT.finditer(text):
        num = float(m.group(2).replace(",", ""))
        mag = (m.group(3) or "").lower()
        short, mult = MAG.get(mag, ("", 1))
        out.append({"cur": _cur(m.group(1)), "num": num, "short": short, "abs": num * mult,
                    "text": f"{_cur(m.group(1))}{m.group(2)}{(' ' + short) if short else ''}"})
    return out


def direction(text):
    u, dn = UPW.search(text), DOWNW.search(text)
    if u and (not dn or u.start() < dn.start()):
        return True
    if dn:
        return False
    return None


def fmt(x):
    return f"{x:,.2f}".rstrip("0").rstrip(".")


def pick(story):
    title, summary = story["title"], story.get("summary", "")
    text = title + " . " + summary
    up = direction(title) if direction(title) is not None else direction(text)
    res = {"up": up}

    m = FROM_TO.search(text)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return dict(res, kind="bars", bars=[{"label": "Before", "value": a, "text": f"{fmt(a)}%"},
                                           {"label": "Latest", "value": b, "text": f"{fmt(b)}%"}],
                    figure=f"{fmt(b)}%", change=None, delta=f"{'+' if b >= a else '−'}{fmt(abs(b - a))} pts")
    m = TO_FROM.search(text)
    if m:
        b, a = float(m.group(1)), float(m.group(3))
        return dict(res, kind="bars", bars=[{"label": "Before", "value": a, "text": f"{fmt(a)}%"},
                                           {"label": "Latest", "value": b, "text": f"{fmt(b)}%"}],
                    figure=f"{fmt(b)}%", change=None, delta=f"{'+' if b >= a else '−'}{fmt(abs(b - a))} pts")

    amts, pcts = amounts(title) or amounts(text), [float(p) for p in PCT.findall(title)] or [float(p) for p in PCT.findall(text)]
    if amts and pcts and up is not None and 0 < abs(pcts[0]) < 200:
        lvl, g = amts[0], abs(pcts[0])
        prev = lvl["num"] / (1 + g / 100) if up else lvl["num"] / (1 - g / 100)
        prev_text = f"{lvl['cur']}{fmt(round(prev, 2))}{(' ' + lvl['short']) if lvl['short'] else ''}"
        return dict(res, kind="bars", implied=True,
                    bars=[{"label": "Previous period (implied)", "value": prev, "text": prev_text},
                          {"label": "Latest", "value": lvl["num"], "text": lvl["text"]}],
                    figure=lvl["text"], change=f"{fmt(g)}% {'up' if up else 'down'}",
                    delta=f"{'+' if up else '−'}{fmt(g)}%")
    if pcts:
        p = pcts[0]
        return dict(res, kind="ring", pct=min(abs(p), 100), pct_text=f"{'+' if up else ('−' if up is False else '')}{fmt(abs(p))}%",
                    figure=f"{fmt(abs(p))}%", change=None)
    if amts:
        return dict(res, kind="keyword", figure=amts[0]["text"], change=None)
    return dict(res, kind="keyword", figure=None, change=None)
