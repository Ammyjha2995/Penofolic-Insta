"""Penofolic carousel v2: 5 slides, hook -> 3 stories with infographics -> engagement close."""
import math
from PIL import Image, ImageDraw
from .cards import (font, wrap, fit, spaced, lines_block, logo, rings, FEAT,
                    W, H, M, NAVY, NAVY2, GOLD, GOLD2, CREAM, INK, MUTED, LINE, WHITE)

NAVY3 = (28, 53, 80)
SOFT = (200, 208, 216)
UP, DOWN = (46, 160, 105), (214, 84, 72)


# ------------------------------------------------------------ shared pieces
def progress(d, i, n, dark):
    gap, top = 10, 34
    seg = (W - 2 * M - gap * (n - 1)) / n
    for k in range(n):
        x = M + k * (seg + gap)
        on = k < i
        d.rounded_rectangle((x, top, x + seg, top + 6), radius=3,
                            fill=GOLD if on else ((52, 72, 92) if dark else LINE))


def chip(d, text, x_right, y, dark):
    f = font("sans", 21, "Bold")
    tw = sum(d.textlength(c, font=f, features=FEAT) + f.size * 0.16 for c in text)
    d.rounded_rectangle((x_right - tw - 44, y, x_right, y + 48), radius=24, fill=GOLD if dark else NAVY)
    spaced(d, (x_right - tw - 22, y + 12), text, f, NAVY if dark else GOLD2, 0.16)


def triangle(d, x, y, size, up, fill):
    if up:
        d.polygon([(x, y + size), (x + size, y + size), (x + size / 2, y)], fill=fill)
    else:
        d.polygon([(x, y), (x + size, y), (x + size / 2, y + size)], fill=fill)


def footer(img, d, source, date_str, dark):
    d.line((M, H - 128, W - M, H - 128), fill=(52, 72, 92) if dark else LINE, width=2)
    d.text((M, H - 100), "Source: " + source, font=font("sans", 23, "SemiBold"), fill=WHITE if dark else INK, features=FEAT)
    d.text((M, H - 66), date_str, font=font("sans", 22, "Medium"), fill=SOFT if dark else MUTED, features=FEAT)
    lg = logo("light" if dark else "dark", 66)
    img.alpha_composite(lg, (W - M - lg.width, H - 106))


def why_box(d, text, top, dark, anchor_bottom=True):
    if not text:
        return top
    wf = font("italic", 42, "Medium")
    wl = wrap(d, text, wf, W - 2 * M - 80)[:3]
    h = 100 + len(wl) * 50
    if anchor_bottom:
        top = max(top, H - 160 - h)
    d.rectangle((M, top, W - M, top + h), fill=NAVY3 if dark else NAVY)
    d.rectangle((M, top, M + 6, top + h), fill=GOLD)
    spaced(d, (M + 40, top + 32), "WHY IT MATTERS", font("sans", 20, "Bold"), GOLD2)
    lines_block(d, M + 40, top + 74, wl, wf, WHITE, 50)
    return top + h


def headline(d, text, y, dark, sizes=(84, 78, 72, 66, 60)):
    f, ls = fit(d, text, "serif", "SemiBold", W - 2 * M, 3, list(sizes))
    return lines_block(d, M, y, ls, f, WHITE if dark else NAVY, int(f.size * 1.08))


def base(dark):
    img = Image.new("RGBA", (W, H), (NAVY if dark else CREAM) + (255,))
    return img, ImageDraw.Draw(img)


# ------------------------------------------------------------ slide 1: hook
def hook(c, date_str, n):
    img, d = base(True)
    rings(img, W - 60, 300, [200, 320, 440], GOLD, 55)
    d = ImageDraw.Draw(img)
    progress(d, 1, n, True)
    # brand header: logo | tagline, then series + date
    lg = logo("light", 104)
    img.alpha_composite(lg, (M - 8, 66))
    d = ImageDraw.Draw(img)
    x = M + lg.width + 26
    d.line((x, 80, x, 160), fill=GOLD, width=2)
    tag = c.get("tagline", "The economy, decoded.")
    d.text((x + 28, 78), tag, font=font("italic", 44, "SemiBold"), fill=WHITE, features=FEAT)
    d.text((x + 28, 132), c.get("subline", "Ideas. Research. Impact."), font=font("sans", 22, "Medium"), fill=GOLD2, features=FEAT)
    spaced(d, (M, 214), "THE DAILY BRIEF  ·  " + date_str.upper(), font("sans", 20, "Bold"), SOFT, 0.14)

    if c.get("figure"):
        spaced(d, (M, 292), "TODAY'S BIG NUMBER", font("sans", 22, "Bold"), GOLD2)
        f, _ = fit(d, c["figure"], "serif", "SemiBold", W - 2 * M, 1, [220, 200, 180, 160, 140])
        d.text((M - 6, 316), c["figure"], font=f, fill=GOLD2, features=FEAT)
        y = 316 + int(f.size * 1.0)
    else:
        spaced(d, (M, 292), "TODAY'S TOP STORY", font("sans", 22, "Bold"), GOLD2)
        f, ls = fit(d, c["headline"], "serif", "SemiBold", W - 2 * M, 3, [96, 88, 80, 72])
        y = lines_block(d, M, 330, ls, f, GOLD2, int(f.size * 1.05)) + 20

    if c.get("change"):  # trend badge
        bf = font("sans", 30, "Bold")
        tw = d.textlength(c["change"], font=bf, features=FEAT)
        col = UP if c.get("up", True) else DOWN
        d.rounded_rectangle((M, y, M + tw + 92, y + 60), radius=30, fill=col)
        triangle(d, M + 26, y + 18, 24, c.get("up", True), WHITE)
        d.text((M + 64, y + 12), c["change"], font=bf, fill=WHITE, features=FEAT)
        y += 100

    qf, ql = fit(d, c["question"], "italic", "Medium", W - 2 * M, 2, [64, 58, 52])
    y = lines_block(d, M, y + 6, ql, qf, WHITE, int(qf.size * 1.12)) + 44

    spaced(d, (M, y), "INSIDE TODAY", font("sans", 20, "Bold"), GOLD2)
    y += 44
    tf = font("sans", 29, "Medium")
    for k, t in enumerate(c["teasers"], 1):
        d.ellipse((M, y + 4, M + 40, y + 44), outline=GOLD, width=2)
        nf = font("sans", 22, "Bold")
        d.text((M + 20 - d.textlength(str(k), font=nf) / 2, y + 10), str(k), font=nf, fill=GOLD2)
        tl = wrap(d, t, tf, W - 2 * M - 70)
        line = tl[0] if len(tl) == 1 else tl[0].rstrip(".,;:") + "…"
        while d.textlength(line, font=tf, features=FEAT) > W - 2 * M - 70:
            line = line[:-2].rsplit(" ", 1)[0] + "…"
        d.text((M + 62, y + 6), line, font=tf, fill=(226, 232, 238), features=FEAT)
        y += 62

    sf = font("sans", 26, "Bold")
    label = "SWIPE"
    bw = d.textlength(label, font=sf) + 120
    x0, y0 = W - M - bw, H - M - 64
    d.rounded_rectangle((x0, y0, W - M, y0 + 64), radius=32, fill=GOLD)
    d.text((x0 + 30, y0 + 16), label, font=sf, fill=NAVY)
    ax = W - M - 58
    d.line((ax, y0 + 32, ax + 30, y0 + 32), fill=NAVY, width=4)
    d.polygon([(ax + 30, y0 + 22), (ax + 42, y0 + 32), (ax + 30, y0 + 42)], fill=NAVY)
    return img.convert("RGB")


# ------------------------------------------------------------ story slides
def story_bars(s, i, n, date_str):
    """Before -> after horizontal bars."""
    img, d = base(False)
    progress(d, i, n, False)
    chip(d, s["tag"], W - M, 76, False)
    d.text((M, 70), f"{i - 1:02d}", font=font("serif", 60, "SemiBold"), fill=GOLD, features=FEAT)
    y = headline(d, s["hook"], 170, False) + 40

    a, b = s["bars"]
    top = y if s.get("why") else max(y, (y + H - 150 - 400) // 2)
    d.rectangle((M, top, W - M, top + 400), fill=WHITE)
    lf, vf = font("sans", 27, "SemiBold"), font("serif", 62, "SemiBold")
    maxv = max(a["value"], b["value"])
    full = W - 2 * M - 80
    yy = top + 36
    for bar, col, txt in ((a, (176, 186, 196), INK), (b, GOLD, NAVY)):
        d.text((M + 40, yy), bar["label"], font=lf, fill=MUTED, features=FEAT)
        yy += 44
        w = int(full * bar["value"] / maxv)
        d.rounded_rectangle((M + 40, yy, M + 40 + w, yy + 84), radius=10, fill=col)
        lab = bar["text"]
        lw = d.textlength(lab, font=vf, features=FEAT)
        inside = lw + 40 < w
        d.text((M + 40 + (w - lw - 24 if inside else w + 16), yy + 4), lab, font=vf,
               fill=(WHITE if col == GOLD else NAVY) if inside else txt, features=FEAT)
        yy += 120
    if s.get("delta"):
        bf = font("sans", 26, "Bold")
        tw = d.textlength(s["delta"], font=bf, features=FEAT)
        neg = s["delta"].startswith(("−", "-"))
        d.rounded_rectangle((W - M - tw - 100, top - 26, W - M - 30, top + 26), radius=26, fill=DOWN if neg else UP)
        triangle(d, W - M - tw - 76, top - 10, 20, not neg, WHITE)
        d.text((W - M - tw - 46, top - 16), s["delta"], font=bf, fill=WHITE, features=FEAT)
    why_box(d, s["why"], top + 440, False)
    footer(img, d, s["source"], date_str, False)
    return img.convert("RGB")


def story_ring(s, i, n, date_str):
    """Percentage ring gauge on a dark slide."""
    img, d = base(True)
    progress(d, i, n, True)
    chip(d, s["tag"], W - M, 76, True)
    d.text((M, 70), f"{i - 1:02d}", font=font("serif", 60, "SemiBold"), fill=GOLD, features=FEAT)
    y = headline(d, s["hook"], 170, True) + 40

    r, cx = 200, M + 205
    cy = y + 225
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(52, 72, 92, 255), width=34)
    ld.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * min(s["pct"], 100) / 100, fill=GOLD + (255,), width=34)
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    pf = font("serif", 104, "SemiBold")
    t = f"{s['pct_text']}"
    d.text((cx - d.textlength(t, font=pf, features=FEAT) / 2, cy - 64), t, font=pf, fill=WHITE, features=FEAT)
    sf = font("sans", 19, "Bold")
    for k, ln in enumerate(wrap(d, s["pct_label"], sf, 2 * r - 110)[:2]):
        d.text((cx - d.textlength(ln, font=sf) / 2, cy + 44 + k * 26), ln, font=sf, fill=GOLD2)

    x = cx + r + 60
    ff = font("sans", 31, "Medium")
    yy = cy - 140
    for p in s["points"][:2]:
        pl = wrap(d, p, ff, W - M - x)[:4]
        d.rectangle((x, yy + 8, x + 4, yy + 8 + len(pl) * 44 - 10), fill=GOLD)
        yy = lines_block(d, x + 24, yy, pl, ff, (226, 232, 238), 44) + 26
    why_box(d, s["why"], cy + r + 60, True)
    footer(img, d, s["source"], date_str, True)
    return img.convert("RGB")


def story_impact(s, i, n, date_str):
    """World story with an impact-on-India meter."""
    img, d = base(False)
    progress(d, i, n, False)
    chip(d, s["tag"], W - M, 76, False)
    d.text((M, 70), f"{i - 1:02d}", font=font("serif", 60, "SemiBold"), fill=GOLD, features=FEAT)
    y = headline(d, s["hook"], 170, False) + 40

    rows = s["impact"]
    box_h = 110 + len(rows) * 112
    top = y if s.get("why") else max(y, (y + H - 150 - box_h) // 2)
    d.rectangle((M, top, W - M, top + box_h), fill=WHITE)
    spaced(d, (M + 40, top + 32), "IMPACT ON INDIA", font("sans", 21, "Bold"), GOLD)
    lvl = {"Low": 1, "Medium": 2, "High": 3}
    lf, vf = font("sans", 31, "SemiBold"), font("sans", 22, "Bold")
    yy = top + 100
    seg_w, gap = 92, 10
    for name, level in rows:
        nl = wrap(d, name, lf, 330)[:2]
        lines_block(d, M + 40, yy + (10 if len(nl) == 1 else -8), nl, lf, NAVY, 38)
        x0 = W - M - 40 - 3 * seg_w - 2 * gap - 130
        for k in range(3):
            on = k < lvl[level]
            d.rounded_rectangle((x0 + k * (seg_w + gap), yy + 12, x0 + k * (seg_w + gap) + seg_w, yy + 44),
                                radius=6, fill=(GOLD if on else LINE))
        d.text((W - M - 40 - d.textlength(level.upper(), font=vf), yy + 14), level.upper(), font=vf, fill=MUTED)
        yy += 112
    why_box(d, s["why"], top + box_h + 40, False)
    footer(img, d, s["source"], date_str, False)
    return img.convert("RGB")


# ------------------------------------------------------------ slide 5: engage + about
def _founder(size):
    from .cards import ASSETS
    ph = Image.open(ASSETS / "founder.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    ring = Image.new("RGBA", (size + 16, size + 16), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, size + 15, size + 15), fill=GOLD + (255,))
    ring.alpha_composite(ph, (8, 8))
    return ring


def engage(titles, cfg, n):
    img, d = base(True)
    rings(img, W - 40, 120, [220, 340], GOLD, 40)
    d = ImageDraw.Draw(img)
    progress(d, n, n, True)
    spaced(d, (M, 96), "YOUR TURN", font("sans", 22, "Bold"), GOLD2)
    qf, ql = fit(d, "Which story affects you most?", "serif", "SemiBold", W - 2 * M, 2, [80, 74])
    y = lines_block(d, M, 132, ql, qf, WHITE, int(qf.size * 1.04)) + 34

    # vote tiles
    tw = (W - 2 * M - 40) / 3
    for k, t in enumerate(titles[:3]):
        x = M + k * (tw + 20)
        d.rounded_rectangle((x, y, x + tw, y + 196), radius=18, fill=NAVY3, outline=GOLD, width=2)
        nf = font("serif", 92, "SemiBold")
        d.text((x + tw / 2 - d.textlength(str(k + 1), font=nf, features=FEAT) / 2, y + 6), str(k + 1), font=nf, fill=GOLD2, features=FEAT)
        tf = font("sans", 24, "SemiBold")
        ty = y + 122
        for ln in wrap(d, t, tf, tw - 30)[:2]:
            d.text((x + tw / 2 - d.textlength(ln, font=tf, features=FEAT) / 2, ty), ln, font=tf, fill=(226, 232, 238), features=FEAT)
            ty += 32
    y += 226
    cf = font("italic", 46, "Medium")
    t = "Comment 1, 2 or 3 below"
    d.text(((W - d.textlength(t, font=cf)) / 2, y), t, font=cf, fill=GOLD2)
    y += 84

    # action buttons: Follow (filled), Like, Share
    bf = font("sans", 30, "Bold")
    labels = [f"Follow {cfg['brand']['handle']}", "Like", "Share"]
    widths = [d.textlength(lb, font=bf) + 70 for lb in labels]
    x = (W - sum(widths) - 2 * 20) / 2
    for k, (lb, bw) in enumerate(zip(labels, widths)):
        if k == 0:
            d.rounded_rectangle((x, y, x + bw, y + 78), radius=39, fill=GOLD)
            d.text((x + 35, y + 20), lb, font=bf, fill=NAVY)
        else:
            d.rounded_rectangle((x, y, x + bw, y + 78), radius=39, outline=GOLD2, width=3)
            d.text((x + 35, y + 20), lb, font=bf, fill=WHITE)
        x += bw + 20
    y += 128

    # founder strip: circular photo on the navy background, no card
    a = cfg.get("about", {})
    d.line((M, y, W - M, y), fill=(52, 72, 92), width=2)
    ph = _founder(250)
    py = y + 46
    img.alpha_composite(ph, (M, py))
    d = ImageDraw.Draw(img)
    tx = M + ph.width + 44
    tw2 = W - M - tx
    ty = py + 22
    d.text((tx, ty), a.get("name", "Amit Kumar"), font=font("serif", 60, "SemiBold"), fill=WHITE, features=FEAT)
    ty += 72
    spaced(d, (tx, ty), a.get("title", "FOUNDER"), font("sans", 22, "Bold"), GOLD2, 0.18)
    ty += 46
    cf2 = font("sans", 27, "Medium")
    for line in a.get("credentials", []):
        for ln in wrap(d, line, cf2, tw2)[:2]:
            d.text((tx, ty), ln, font=cf2, fill=(214, 222, 230), features=FEAT)
            ty += 36
    lg = logo("light", 96)
    img.alpha_composite(lg, ((W - lg.width) // 2, H - 62 - lg.height))
    return img.convert("RGB")


def story_keyword(s, i, n, date_str):
    """No usable numbers: big headline, key facts, why-box (light slide)."""
    img, d = base(False)
    progress(d, i, n, False)
    chip(d, s["tag"], W - M, 76, False)
    d.text((M, 70), f"{i - 1:02d}", font=font("serif", 60, "SemiBold"), fill=GOLD, features=FEAT)
    sparse = not s.get("why") and len(s.get("points", [])) < 2
    f0, ls0 = fit(d, s["hook"], "serif", "SemiBold", W - 2 * M, 4, [92, 84, 76, 68, 60])
    est = len(ls0) * int(f0.size * 1.08) + 80 + (130 if s.get("figure") else 0) + 60 * len(s.get("points", []))
    y = headline(d, s["hook"], max(170, (H - 150 - est) // 2) if sparse else 170, False, sizes=(92, 84, 76, 68, 60)) + 30
    d.rectangle((M, y, M + 90, y + 5), fill=GOLD)
    y += 50
    if s.get("figure"):
        f, _ = fit(d, s["figure"], "serif", "SemiBold", W - 2 * M, 1, [150, 130, 110])
        d.text((M - 4, y - 20), s["figure"], font=f, fill=GOLD, features=FEAT)
        y += int(f.size * 1.0)
    pf = font("sans", 34, "Medium")
    for p in s.get("points", [])[:2]:
        pl = wrap(d, p, pf, W - 2 * M - 46)[:3]
        d.ellipse((M + 2, y + 16, M + 16, y + 30), fill=GOLD)
        y = lines_block(d, M + 46, y, pl, pf, INK, 48) + 24
    why_box(d, s.get("why", ""), y + 20, False)
    footer(img, d, s["source"], date_str, False)
    return img.convert("RGB")


def render_carousel(stories, meta, date_str, cfg, out_dir):
    """stories: enriched by writer.carousel (hook, points, why, label, fig). Returns slide paths."""
    from pathlib import Path
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    n = len(stories) + 2
    lead = stories[0]
    lf = lead["fig"]
    cover = {"figure": lf.get("figure"), "change": lf.get("change"), "up": lf.get("up") is not False,
             "headline": lead["hook"], "question": meta["question"], "teasers": [s["hook"] for s in stories]}
    slides = [hook(cover, date_str, n)]
    for i, s in enumerate(stories, 2):
        f = s["fig"]
        d = {"tag": ("WORLD · " if s.get("region") == "world" else "INDIA · ") + s["category"].upper(),
             "hook": s["hook"], "points": s.get("points", []), "why": s.get("why", ""),
             "source": " · ".join(s["sources"][:3]), "figure": f.get("figure")}
        if f["kind"] == "bars":
            slides.append(story_bars(dict(d, bars=f["bars"], delta=f.get("delta")), i, n, date_str))
        elif f["kind"] == "ring":
            slides.append(story_ring(dict(d, pct=f["pct"], pct_text=f["pct_text"], pct_label=s["label"].upper()), i, n, date_str))
        elif f["kind"] == "impact":
            slides.append(story_impact(dict(d, impact=f["impact"]), i, n, date_str))
        else:
            slides.append(story_keyword(d, i, n, date_str))
    slides.append(engage([s["label"] for s in stories], cfg, n))
    paths = []
    for k, im in enumerate(slides, 1):
        p = out / f"slide-{k:02d}.jpg"
        im.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths
