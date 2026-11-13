"""Render 1080x1350 (4:5) carousel slides in the Penofolic navy-and-gold brand."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, features

ROOT = Path(__file__).resolve().parent.parent
FONTS, ASSETS = ROOT / "fonts", ROOT / "assets"
W, H, M = 1080, 1350, 84  # size and outer margin
FEAT = ["lnum", "kern"] if features.check("raqm") else None  # lining figures: 11.8% not old-style

NAVY, NAVY2, GOLD, GOLD2 = (15, 34, 52), (20, 39, 56), (187, 156, 99), (212, 185, 127)
CREAM, INK, MUTED, LINE, WHITE = (246, 244, 239), (20, 32, 45), (93, 106, 119), (222, 216, 204), (255, 255, 255)


def font(kind, size, weight="Regular"):
    f = ImageFont.truetype(str(FONTS / {"serif": "Cormorant.ttf", "italic": "Cormorant-Italic.ttf", "sans": "Manrope.ttf"}[kind]), size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        pass
    return f


def wrap(draw, text, fnt, width):
    lines, line = [], ""
    for word in text.split():
        test = (line + " " + word).strip()
        if draw.textlength(test, font=fnt, features=FEAT) <= width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def fit(draw, text, kind, weight, width, max_lines, sizes):
    """Largest font size from `sizes` at which text fits in max_lines."""
    for s in sizes:
        f = font(kind, s, weight)
        lines = wrap(draw, text, f, width)
        if len(lines) <= max_lines:
            return f, lines
    f = font(kind, sizes[-1], weight)
    lines = wrap(draw, text, f, width)[:max_lines]
    lines[-1] = lines[-1].rstrip(".,;:") + "…"
    return f, lines


def spaced(draw, xy, text, fnt, fill, tracking=0.18):
    """Letter-spaced uppercase label; returns end x."""
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, features=FEAT)
        x += draw.textlength(ch, font=fnt, features=FEAT) + fnt.size * tracking
    return x


def lines_block(draw, x, y, lines, fnt, fill, lh):
    for ln in lines:
        draw.text((x, y), ln, font=fnt, fill=fill, features=FEAT)
        y += lh
    return y


def logo(kind, height):
    im = Image.open(ASSETS / f"logo-{kind}.png").convert("RGBA")
    return im.resize((int(im.width * height / im.height), height), Image.LANCZOS)


def rings(img, cx, cy, radii, color, alpha):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for r in radii:
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color + (alpha,), width=2)
    img.alpha_composite(layer)


# ---------------------------------------------------------------- slides
def cover(stories, title, date_str, cfg):
    img = Image.new("RGBA", (W, H), NAVY + (255,))
    rings(img, W - 40, 120, [180, 300, 420], GOLD, 60)
    d = ImageDraw.Draw(img)
    d.line((M, M + 12, M + 56, M + 12), fill=GOLD, width=2)
    spaced(d, (M + 76, M), "ECONOMY TODAY", font("sans", 24, "Bold"), GOLD2)
    d.text((M, M + 50), date_str, font=font("sans", 26, "Medium"), fill=(200, 208, 216))

    f, ls = fit(d, title, "serif", "SemiBold", W - 2 * M, 3, [104, 96, 88, 80, 72])
    y = lines_block(d, M, 250, ls, f, WHITE, int(f.size * 1.02))
    ni = sum(1 for s in stories if s.get("region", "india") == "india")
    nw = len(stories) - ni
    sub = f"{ni} from India · {nw} from the world" if nw and ni else f"{len(stories)} stories shaping the economy"
    d.text((M, y + 10), sub, font=font("italic", 40, "Medium"), fill=GOLD2, features=FEAT)

    y = max(y + 90, 600)
    bottom = H - 190
    groups = [(lab, [(i, x) for i, x in enumerate(stories, 1) if x.get("region", "india") == reg])
              for reg, lab in (("india", "INDIA"), ("world", "WORLD"))]
    groups = [g for g in groups if g[1]]
    show_labels = len(groups) > 1
    head_h = 46 if show_labels else 0
    row = min(96, (bottom - y - head_h * len(groups)) // len(stories))
    two_lines = row >= 92
    num_f, txt_f = font("serif", 40, "SemiBold"), font("sans", 28 if two_lines else 27, "Medium")
    lab_f = font("sans", 18, "Bold")
    for lab, items in groups:
        if show_labels:
            spaced(d, (M, y + 8), lab, lab_f, GOLD2)
            y += head_h
        for i, x in items:
            d.line((M, y, W - M, y), fill=(52, 72, 92), width=1)
            d.text((M, y + 14), f"{i:02d}", font=num_f, fill=GOLD, features=FEAT)
            tl = wrap(d, x["hook"], txt_f, W - 2 * M - 100)
            keep = 2 if two_lines else 1
            if len(tl) > keep:
                tl = tl[:keep]
                while d.textlength(tl[-1] + "…", font=txt_f, features=FEAT) > W - 2 * M - 100:
                    tl[-1] = tl[-1].rsplit(" ", 1)[0]
                tl[-1] = tl[-1].rstrip(".,;:") + "…"
            ty = y + (row - len(tl) * int(txt_f.size * 1.3)) // 2 + 2
            lines_block(d, M + 100, ty, tl, txt_f, (226, 232, 238), int(txt_f.size * 1.3))
            y += row
    lg = logo("light", 92)
    img.alpha_composite(lg, (M - 6, H - M - lg.height + 10))
    sf = font("sans", 24, "Bold")
    tw = d.textlength("SWIPE  →", font=sf, features=FEAT)
    d.text((W - M - tw, H - M - 30), "SWIPE  →", font=sf, fill=GOLD2, features=FEAT)
    return img.convert("RGB")


def story(s, i, n, date_str, cfg):
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 14), fill=NAVY)
    d.rectangle((0, 14, 260, 18), fill=GOLD)

    d.text((M, M + 8), f"{i:02d}", font=font("serif", 64, "SemiBold"), fill=GOLD, features=FEAT)
    d.text((M + 92, M + 36), f"/ {n:02d}", font=font("sans", 24, "Medium"), fill=MUTED, features=FEAT)
    tag = ("WORLD · " if s.get("region") == "world" else "") + s["category"].upper()
    tf = font("sans", 21, "Bold")
    tw = sum(d.textlength(c, font=tf, features=FEAT) + tf.size * 0.16 for c in tag)
    d.rounded_rectangle((W - M - tw - 44, M + 22, W - M, M + 70), radius=24, fill=NAVY)
    spaced(d, (W - M - tw - 22, M + 34), tag, tf, GOLD2, 0.16)

    # headline (bigger and vertically centred when there is no summary to show)
    bare = not s.get("points") and not s.get("why")
    limit = H - 150  # content must end above the footer rule
    for k in (1.0, 0.93, 0.86, 0.8, 0.74):
        sizes = [int(v * k) for v in ([108, 100, 92, 84, 76, 68] if bare else [88, 80, 72, 64, 58])]
        f, ls = fit(d, s["hook"], "serif", "SemiBold", W - 2 * M, 5 if bare else 4, sizes)
        lh = int(f.size * 1.08)
        pf = font("sans", int(35 * k), "Medium")
        pts = [wrap(d, p, pf, W - 2 * M - 46)[:3] for p in s.get("points", [])]
        wf = font("italic", int(44 * k), "Medium")
        wl = wrap(d, s["why"], wf, W - 2 * M - 80)[:4] if s.get("why") else []
        plh, wlh = int(pf.size * 1.43), int(wf.size * 1.2)
        box_h = (int(98 * k) + len(wl) * wlh) if wl else 0
        need = 230 + len(ls) * lh + 72 + sum(len(x) * plh + 26 for x in pts) + (box_h + 30 if wl else 0)
        if need <= limit:
            break
    top = max(230, (H - len(ls) * lh) // 2 - 90) if bare else 230
    y = lines_block(d, M, top, ls, f, NAVY, lh) + 26
    d.rectangle((M, y, M + 90, y + 4), fill=GOLD)
    y += 46

    for pl in pts:  # key facts
        dot = int(pf.size * 0.5)
        d.ellipse((M + 2, y + dot, M + 15, y + dot + 13), fill=GOLD)
        y = lines_block(d, M + 46, y, pl, pf, INK, plh) + 26

    if wl:  # why it matters, anchored low but never into the footer
        btop = min(max(y + 20, limit - box_h - 20), limit - box_h)
        d.rectangle((M, btop, W - M, btop + box_h), fill=NAVY)
        d.rectangle((M, btop, M + 6, btop + box_h), fill=GOLD)
        spaced(d, (M + 40, btop + int(34 * k)), "WHY IT MATTERS", font("sans", 20, "Bold"), GOLD2)
        lines_block(d, M + 40, btop + int(76 * k), wl, wf, WHITE, wlh)
    elif bare:
        d.text((M, y), "Full report: see source below.", font=font("italic", 40, "Medium"), fill=MUTED, features=FEAT)

    # footer
    d.line((M, H - 128, W - M, H - 128), fill=LINE, width=2)
    src = "Source: " + " · ".join(s["sources"][:3])
    d.text((M, H - 100), src, font=font("sans", 23, "SemiBold"), fill=INK, features=FEAT)
    d.text((M, H - 66), date_str, font=font("sans", 22, "Medium"), fill=MUTED, features=FEAT)
    lg = logo("dark", 66)
    img.alpha_composite(lg, (W - M - lg.width, H - 106))
    return img.convert("RGB")


def closing(cfg):
    img = Image.new("RGBA", (W, H), NAVY + (255,))
    rings(img, W // 2, H // 2 - 120, [230, 340, 450], GOLD, 45)
    d = ImageDraw.Draw(img)
    lg = logo("light", 230)
    img.alpha_composite(lg, ((W - lg.width) // 2, 330))
    f = font("serif", 66, "SemiBold")
    t = "Daily economics, explained."
    d.text(((W - d.textlength(t, font=f, features=FEAT)) / 2, 690), t, font=f, fill=WHITE, features=FEAT)
    f2 = font("italic", 40, "Medium")
    t2 = "Ideas. Research. Impact."
    d.text(((W - d.textlength(t2, font=f2, features=FEAT)) / 2, 780), t2, font=f2, fill=GOLD2, features=FEAT)
    bf = font("sans", 30, "Bold")
    t3 = f"Follow {cfg['brand']['handle']}"
    bw = d.textlength(t3, font=bf, features=FEAT) + 80
    d.rectangle(((W - bw) / 2, 900, (W + bw) / 2, 976), fill=GOLD)
    d.text(((W - bw) / 2 + 40, 919), t3, font=bf, fill=NAVY, features=FEAT)
    sf = font("sans", 26, "Medium")
    t4 = cfg["brand"]["website"]
    d.text(((W - d.textlength(t4, font=sf, features=FEAT)) / 2, 1020), t4, font=sf, fill=(200, 208, 216))
    nf = font("sans", 20, "Medium")
    t5 = "Summaries of public news reports. Not investment advice."
    d.text(((W - d.textlength(t5, font=nf, features=FEAT)) / 2, H - 110), t5, font=nf, fill=(130, 148, 165))
    return img.convert("RGB")


def render_all(stories, title, date_str, cfg, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides = [cover(stories, title, date_str, cfg)]
    slides += [story(s, i, len(stories), date_str, cfg) for i, s in enumerate(stories, 1)]
    slides.append(closing(cfg))
    paths = []
    for k, im in enumerate(slides, 1):
        p = out_dir / f"slide-{k:02d}.jpg"
        im.save(p, "JPEG", quality=92, optimize=True, progressive=False)
        paths.append(p)
    return paths
