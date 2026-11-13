"""Penofolic 8 PM Reel: one big story, ~27 s, 1080x1920, animated, with background music.

Frames are drawn with Pillow and piped straight into ffmpeg (no temp images).
"""
import math, subprocess, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from .cards import font, wrap, spaced, lines_block, logo, rings, FEAT, NAVY, GOLD, GOLD2, CREAM, INK, MUTED, WHITE, ASSETS

W, H, M, FPS = 1080, 1920, 90, 30
NAVY3, SOFT, UP, DOWN = (28, 53, 80), (200, 208, 216), (46, 160, 105), (214, 84, 72)
SCENES = [("hook", 4.5), ("what", 6.0), ("chart", 6.5), ("why", 5.0), ("outro", 5.0)]
FADE = 0.35


def ease(x):  # ease-out cubic, clamped
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def appear(t, start, dur=0.45):
    return ease((t - start) / dur)


def blend_text(img, xy, text, fnt, fill, alpha, dy=24):
    """Draw text sliding up and fading in (alpha 0..1)."""
    if alpha <= 0:
        return
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text((xy[0], xy[1] + (1 - alpha) * dy), text, font=fnt, fill=fill + (int(255 * alpha),), features=FEAT)
    img.alpha_composite(layer)


def base():
    img = Image.new("RGBA", (W, H), NAVY + (255,))
    rings(img, W - 40, 420, [240, 380, 520], GOLD, 40)
    return img


def brand_header(img):
    lg = logo("light", 92)
    img.alpha_composite(lg, (M - 8, 170))
    d = ImageDraw.Draw(img)
    x = M + lg.width + 24
    d.line((x, 182, x, 252), fill=GOLD, width=2)
    d.text((x + 24, 180), "The economy, decoded.", font=font("italic", 40, "SemiBold"), fill=WHITE, features=FEAT)
    d.text((x + 24, 228), "Ideas. Research. Impact.", font=font("sans", 21, "Medium"), fill=GOLD2, features=FEAT)


def triangle(d, x, y, s, fill):
    d.polygon([(x, y + s), (x + s, y + s), (x + s / 2, y)], fill=fill)


# ------------------------------------------------------------ scenes
def s_hook(t, c):
    img = base(); brand_header(img); d = ImageDraw.Draw(img)
    spaced(d, (M, 380), "TONIGHT'S BIG STORY", font("sans", 26, "Bold"), GOLD2)
    if c.get("value") is not None:
        v = c["value"] * ease((t - 0.3) / 1.8)
        num = c["fmt"].format(v)
        f = font("serif", 230, "SemiBold")
        while d.textlength(c["fmt"].format(c["value"]), font=f, features=FEAT) > W - 2 * M and f.size > 120:
            f = font("serif", f.size - 10, "SemiBold")
        d.text((M - 6, 450), num, font=f, fill=GOLD2, features=FEAT)
    else:
        hf = font("serif", 100, "SemiBold")
        for k, ln in enumerate(wrap(d, c["headline"], hf, W - 2 * M)[:3]):
            blend_text(img, (M, 450 + k * 108), ln, hf, GOLD2, appear(t, 0.2 + k * 0.25))
    a = appear(t, 2.1, 0.35) if c.get("change") else 0
    if a > 0:
        bf = font("sans", 36, "Bold")
        tw = d.textlength(c["change"], font=bf, features=FEAT)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        sc = 0.8 + 0.2 * a
        x0, y0 = M, 730
        col = UP if c.get("up", True) else DOWN
        ld.rounded_rectangle((x0, y0, x0 + (tw + 110) * sc, y0 + 76 * sc), radius=int(38 * sc), fill=col + (int(255 * a),))
        if c.get("up", True):
            triangle(ld, x0 + 30 * sc, y0 + 24 * sc, 28 * sc, WHITE + (int(255 * a),))
        else:
            ld.polygon([(x0 + 30 * sc, y0 + 24 * sc), (x0 + 58 * sc, y0 + 24 * sc), (x0 + 44 * sc, y0 + 52 * sc)], fill=WHITE + (int(255 * a),))
        ld.text((x0 + 76 * sc, y0 + 16 * sc), c["change"], font=font("sans", int(36 * sc), "Bold"), fill=WHITE + (int(255 * a),), features=FEAT)
        img.alpha_composite(layer)
    qf = font("italic", 72, "Medium")
    for k, ln in enumerate(wrap(d, c["question"], qf, W - 2 * M)[:3]):
        blend_text(img, (M, 900 + k * 84), ln, qf, WHITE, appear(t, 2.6 + k * 0.25))
    return img


def s_what(t, c):
    img = base(); d = ImageDraw.Draw(img)
    a = appear(t, 0.0, 0.3)
    tf = font("sans", 24, "Bold")
    tag = c["tag"]
    tw = sum(d.textlength(ch, font=tf) + tf.size * 0.16 for ch in tag)
    if a > 0:
        d.rounded_rectangle((M, 300, M + tw + 48, 354), radius=27, fill=GOLD)
        spaced(d, (M + 24, 314), tag, tf, NAVY, 0.16)
    spaced(d, (M, 420), "WHAT HAPPENED", font("sans", 26, "Bold"), GOLD2)
    hf = font("serif", 96, "SemiBold")
    y = 480
    for k, ln in enumerate(wrap(d, c["headline"], hf, W - 2 * M)[:4]):
        blend_text(img, (M, y), ln, hf, WHITE, appear(t, 0.3 + k * 0.25))
        y += 104
    y += 60
    pf = font("sans", 44, "Medium")
    for k, p in enumerate(c["points"][:2]):
        st = 1.8 + k * 1.2
        al = appear(t, st)
        if al > 0:
            d.ellipse((M, y + 20, M + 18, y + 38), fill=GOLD)
        for ln in wrap(d, p, pf, W - 2 * M - 50)[:3]:
            blend_text(img, (M + 50, y), ln, pf, (226, 232, 238), al)
            y += 60
        y += 40
    return img


def s_chart(t, c):
    img = base(); d = ImageDraw.Draw(img)
    spaced(d, (M, 380), "BY THE NUMBERS", font("sans", 26, "Bold"), GOLD2)
    d.text((M, 430), c["chart_title"], font=font("serif", 76, "SemiBold"), fill=WHITE, features=FEAT)
    top = 640
    d.rounded_rectangle((M, top, W - M, top + 700), radius=24, fill=CREAM)
    full = W - 2 * M - 120
    maxv = max(b["value"] for b in c["bars"])
    yy = top + 70
    lf, vf = font("sans", 34, "SemiBold"), font("serif", 84, "SemiBold")
    for k, b in enumerate(c["bars"]):
        g = ease((t - 0.4 - k * 0.6) / 1.4)
        col = (176, 186, 196) if k == 0 else GOLD
        d.text((M + 60, yy), b["label"], font=lf, fill=MUTED, features=FEAT)
        yy += 56
        w = max(4, int(full * b["value"] / maxv * g))
        d.rounded_rectangle((M + 60, yy, M + 60 + w, yy + 130), radius=14, fill=col)
        if g > 0.6:
            al = (g - 0.6) / 0.4
            txt = b["text"]
            lw = d.textlength(txt, font=vf, features=FEAT)
            layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((M + 60 + w - lw - 30, yy + 18), txt, font=vf,
                                       fill=(WHITE if k else NAVY) + (int(255 * al),), features=FEAT)
            img.alpha_composite(layer)
        yy += 210
    a = appear(t, 3.4, 0.35) if c.get("delta") else 0
    if a > 0:
        bf = font("sans", 44, "Bold")
        txt = c["delta"]
        tw = d.textlength(txt, font=bf, features=FEAT)
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        x0, y0 = W - M - tw - 150, top + 560
        neg = txt.startswith(("−", "-"))
        ld.rounded_rectangle((x0, y0, W - M - 40, y0 + 92), radius=46, fill=(DOWN if neg else UP) + (int(255 * a),))
        if neg:
            ld.polygon([(x0 + 34, y0 + 30), (x0 + 68, y0 + 30), (x0 + 51, y0 + 62)], fill=WHITE + (int(255 * a),))
        else:
            triangle(ld, x0 + 34, y0 + 28, 34, WHITE + (int(255 * a),))
        ld.text((x0 + 88, y0 + 18), txt, font=bf, fill=WHITE + (int(255 * a),), features=FEAT)
        img.alpha_composite(layer)
    nf = font("sans", 26, "Medium")
    d.text((M, top + 740), c["chart_note"], font=nf, fill=SOFT, features=FEAT)
    return img


def s_why(t, c):
    img = base(); d = ImageDraw.Draw(img)
    spaced(d, (M, 420), "WHY IT MATTERS TO YOU", font("sans", 28, "Bold"), GOLD2)
    d.rectangle((M, 480, M + int(140 * appear(t, 0.1, 0.6)), 486), fill=GOLD)
    wf = font("italic", 82, "Medium")
    y = 560
    for k, ln in enumerate(wrap(d, c["why"], wf, W - 2 * M)[:6]):
        blend_text(img, (M, y), ln, wf, WHITE, appear(t, 0.4 + k * 0.35))
        y += 98
    sf = font("sans", 28, "SemiBold")
    blend_text(img, (M, 1450), "Source: " + c["source"], sf, SOFT, appear(t, 2.6))
    return img


def s_outro(t, c):
    img = base(); d = ImageDraw.Draw(img)
    a = appear(t, 0.0, 0.6)
    size = int(380 * (0.85 + 0.15 * a))
    ph = Image.open(ASSETS / "founder.png").convert("RGBA").resize((size, size), Image.LANCZOS)
    ring = Image.new("RGBA", (size + 20, size + 20), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, size + 19, size + 19), fill=GOLD + (255,))
    ring.alpha_composite(ph, (10, 10))
    ring.putalpha(ring.getchannel("A").point(lambda v: int(v * a)))
    img.alpha_composite(ring, ((W - ring.width) // 2, 330 + (400 - ring.height) // 2))
    nf = font("serif", 84, "SemiBold")
    name = c["founder"]
    blend_text(img, ((W - d.textlength(name, font=nf)) / 2, 790), name, nf, WHITE, appear(t, 0.5))
    tf = font("sans", 28, "Bold")
    title = c["founder_title"]
    tw = sum(d.textlength(ch, font=tf) + tf.size * 0.18 for ch in title)
    if appear(t, 0.8) > 0.5:
        spaced(d, ((W - tw) / 2, 900), title, tf, GOLD2, 0.18)
    cf = font("sans", 36, "Medium")
    cr = c["founder_line"]
    blend_text(img, ((W - d.textlength(cr, font=cf)) / 2, 950), cr, cf, (214, 222, 230), appear(t, 1.0))
    # follow button
    al = appear(t, 1.6, 0.4)
    if al > 0:
        bf = font("sans", 42, "Bold")
        lbl = f"Follow {c['handle']}"
        bw = d.textlength(lbl, font=bf) + 110
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
        x0, y0 = (W - bw) / 2, 1110
        ld.rounded_rectangle((x0, y0, x0 + bw, y0 + 104), radius=52, fill=GOLD + (int(255 * al),))
        ld.text((x0 + 55, y0 + 26), lbl, font=bf, fill=NAVY + (int(255 * al),))
        img.alpha_composite(layer)
    sf = font("italic", 46, "Medium")
    sub = "Daily economics, explained."
    blend_text(img, ((W - d.textlength(sub, font=sf)) / 2, 1260), sub, sf, GOLD2, appear(t, 2.0))
    lg = logo("light", 120)
    if appear(t, 2.3) > 0:
        lg.putalpha(lg.getchannel("A").point(lambda v: int(v * appear(t, 2.3))))
        img.alpha_composite(lg, ((W - lg.width) // 2, 1380))
    return img


def s_ring(t, c):
    img = base(); d = ImageDraw.Draw(img)
    spaced(d, (M, 380), "BY THE NUMBERS", font("sans", 26, "Bold"), GOLD2)
    d.text((M, 430), c["chart_title"], font=font("serif", 76, "SemiBold"), fill=WHITE, features=FEAT)
    cx, cy, r = W // 2, 1000, 300
    g = ease((t - 0.3) / 1.8)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
    ld.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(52, 72, 92, 255), width=56)
    if g > 0:
        ld.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * c["pct"] / 100 * g, fill=GOLD + (255,), width=56)
    img.alpha_composite(layer); d = ImageDraw.Draw(img)
    pf = font("serif", 170, "SemiBold")
    txt = c["pct_text"]
    d.text((cx - d.textlength(txt, font=pf, features=FEAT) / 2, cy - 120), txt, font=pf, fill=WHITE, features=FEAT)
    lf = font("sans", 30, "Bold")
    for k, ln in enumerate(wrap(d, c.get("pct_label", ""), lf, 2 * r - 160)[:2]):
        blend_text(img, (cx - d.textlength(ln, font=lf) / 2, cy + 80 + k * 40), ln, lf, GOLD2, appear(t, 1.6))
    return img


FN = {"hook": s_hook, "what": s_what, "chart": s_chart, "ring": s_ring, "why": s_why, "outro": s_outro}
MIN = {"hook": 4.5, "what": 6.0, "chart": 6.5, "ring": 5.5, "why": 5.0, "outro": 5.0}


def frame(t_total, c, cache, scenes=None):
    scenes = scenes or SCENES
    acc = 0.0
    for k, (name, dur) in enumerate(scenes):
        if t_total < acc + dur or k == len(scenes) - 1:
            tl = t_total - acc
            img = FN[name](tl, c)
            if k and tl < FADE:  # crossfade from previous scene's last frame
                prev = cache.get(k - 1)
                if prev is None:
                    pn, pd = scenes[k - 1]
                    prev = cache[k - 1] = FN[pn](pd, c)
                img = Image.blend(prev, img, tl / FADE)
            break
        acc += dur
    d = ImageDraw.Draw(img)  # running progress line
    total = sum(x[1] for x in scenes)
    d.rectangle((0, 0, int(W * t_total / total), 10), fill=GOLD)
    return img.convert("RGB")


# ------------------------------------------------------------ audio (sample placeholder)
def ambient_track(path, seconds, sr=44100):
    """Soft synth pad (Am-F-C-G) used only when no music file is supplied."""
    t = np.arange(int(seconds * sr)) / sr
    chords = [(220.0, 261.63, 329.63), (174.61, 220.0, 261.63), (130.81, 196.0, 261.63), (196.0, 246.94, 293.66)]
    out = np.zeros_like(t)
    bar = 3.0
    for i in range(int(seconds / bar) + 1):
        s, e = int(i * bar * sr), int(min(seconds, (i + 1) * bar + 0.6) * sr)
        if s >= len(t):
            break
        tt = t[s:e] - t[s]
        env = np.minimum(1, tt / 0.8) * np.exp(-tt / 4.5)
        for f in chords[i % 4]:
            out[s:e] += env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) / 3
        for k in range(6):  # gentle plucks
            ps = s + int(k * 0.5 * sr)
            if ps >= e:
                break
            n = int(0.45 * sr)
            pt = np.arange(min(n, len(t) - ps)) / sr
            out[ps:ps + len(pt)] += 0.18 * np.exp(-pt / 0.12) * np.sin(2 * np.pi * chords[i % 4][k % 3] * 2 * pt)
    out = np.convolve(out, np.ones(8) / 8, mode="same")
    fade = np.minimum(1, np.minimum(t / 1.0, (seconds - t) / 2.0))
    out = out * fade
    out = (out / np.max(np.abs(out)) * 0.35 * 32767).astype(np.int16)
    with wave.open(str(path), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(out.tobytes())


def _load_music(path, seconds):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-stream_loop", "-1", "-i", str(path), "-t", str(seconds),
                          "-f", "s16le", "-ac", "1", "-ar", "44100", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768


def render(c, out_mp4, music=None, voice=None, workdir=None):
    """c: scene content. voice: dict scene->spoken text (English); music: path to MP3/WAV or None (generated)."""
    from . import voice as tts
    out_mp4 = Path(out_mp4); out_mp4.parent.mkdir(parents=True, exist_ok=True)
    work = Path(workdir or out_mp4.parent)
    chart = {"bars": "chart", "ring": "ring"}.get(c.get("kind"))
    names = ["hook", "what"] + ([chart] if chart else []) + (["why"] if c.get("why") else []) + ["outro"]
    clips, scenes = {}, []
    for nm in names:
        key = "chart" if nm in ("chart", "ring") else nm
        text = (voice or {}).get(key)
        clip = tts.synth(text, c.get("voice_name", "en-IN-NeerjaNeural"), work / f"vo-{key}.mp3") if text else None
        if clip is not None:
            clips[nm] = clip
        dur = MIN[nm] if clip is None else max(MIN[nm], len(clip) / 44100 + 1.0)
        scenes.append((nm, round(dur, 2)))
    total = sum(x[1] for x in scenes)

    # audio: music bed ducked under voice
    n = int(total * 44100)
    if music:
        bed = _load_music(music, total)
    else:
        tmp = work / "bed.wav"
        ambient_track(tmp, total)
        with wave.open(str(tmp)) as w:
            bed = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        tmp.unlink(missing_ok=True)
    bed = np.pad(bed, (0, max(0, n - len(bed))))[:n]
    vo = np.zeros(n, dtype=np.float32)
    acc = 0.0
    for nm, dur in scenes:
        if nm in clips:
            st = int((acc + 0.35) * 44100)
            seg = clips[nm][: max(0, n - st)]
            vo[st:st + len(seg)] += seg
        acc += dur
    if clips:
        env = np.convolve((np.abs(vo) > 0.01).astype(np.float32), np.ones(13230) / 13230, mode="same")
        gain = 0.55 - 0.40 * np.clip(env * 3, 0, 1)
        mix = bed * gain + vo * 1.1
    else:
        mix = bed * 0.9
    mix = mix / max(1e-6, np.max(np.abs(mix))) * 0.89
    wav = work / "mix.wav"
    with wave.open(str(wav), "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes((mix * 32767).astype(np.int16).tobytes())

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-ar", "44100", "-shortest", "-movflags", "+faststart", str(out_mp4)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    cache = {}
    for i in range(int(total * FPS)):
        p.stdin.write(frame(i / FPS, c, cache, scenes).tobytes())
    p.stdin.close(); p.wait()
    wav.unlink(missing_ok=True)
    for f in work.glob("vo-*.mp3"):
        f.unlink()
    cover = out_mp4.with_name("cover.jpg")
    frame(min(4.0, scenes[0][1] - 0.1), c, {}, scenes).save(cover, "JPEG", quality=92)
    return out_mp4, cover, scenes
