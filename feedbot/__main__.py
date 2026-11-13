"""Penofolic Instagram feed bot.

  python -m feedbot draft                 fetch news, write, render slides into queue/<date>/
  python -m feedbot open-issue --folder F  open a GitHub issue for approval
  python -m feedbot publish --issue N      publish an approved draft (or --folder F)
  python -m feedbot refresh-token          write a fresh 60-day Instagram token to new_token.txt
  python -m feedbot preview FILE.json      render slides from a saved stories file (no network)
"""
import argparse, json, logging, os, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests, yaml

from . import news, writer, cards2

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state" / "posted.json"
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("feedbot")


def cfg():
    return yaml.safe_load((ROOT / "config.yml").read_text(encoding="utf-8"))


def tz(c):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(c["brand"]["timezone"])
    except Exception:
        return timezone(timedelta(hours=5, minutes=30))


ITEMS = ROOT / "state" / "items"


def load_state():
    """All draft records: legacy state/posted.json + one file per draft in state/items/ (no merge conflicts)."""
    items = json.loads(STATE.read_text()).get("items", []) if STATE.exists() else []
    if ITEMS.exists():
        for f in sorted(ITEMS.glob("*.json")):
            try:
                items.append(json.loads(f.read_text()))
            except ValueError:
                pass
    return {"items": items}


def _item_path(folder):
    return ITEMS / (Path(folder).name + ".json")


def save_item(item):
    ITEMS.mkdir(parents=True, exist_ok=True)
    _item_path(item["folder"]).write_text(json.dumps(item, indent=1, ensure_ascii=False))


def prune_items(days=21):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    for f in ITEMS.glob("*.json") if ITEMS.exists() else []:
        try:
            if json.loads(f.read_text()).get("at", "") < cutoff:
                f.unlink()
        except ValueError:
            f.unlink()


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}={v}")
        if path:
            with open(path, "a") as f:
                f.write(f"{k}={v}\n")


def nice_date(d):
    return f"{d.day} {d:%B %Y}"


FIGNUM = re.compile(r"^(\D*?)(-?[\d,]+(?:\.(\d+))?)(.*)$")


def reel_content(r, c):
    """Map writer.reel output to the Reel scene fields."""
    f = r["fig"]
    m = FIGNUM.match(f.get("figure") or "")
    value = fmt = None
    if m:
        value = float(m.group(2).replace(",", ""))
        dec = len(m.group(3) or "")
        fmt = m.group(1).replace("{", "{{") + "{:,." + str(dec) + "f}" + m.group(4).replace("{", "{{")
    a = c.get("about", {})
    out = {"kind": f["kind"], "value": value, "fmt": fmt, "change": f.get("change"), "up": f.get("up") is not False,
           "question": r["question"], "tag": r["tag"], "headline": r["headline"], "points": r["points"],
           "chart_title": r["chart_title"], "why": r["why"], "source": r["source"],
           "founder": a.get("name", "Amit Kumar"), "founder_title": a.get("title", "FOUNDER, PENOFOLIC"),
           "founder_line": " · ".join(a.get("credentials", [])), "handle": c["brand"]["handle"],
           "voice_name": c.get("reel", {}).get("voice", "en-IN-NeerjaNeural")}
    if f["kind"] == "bars":
        out.update(bars=f["bars"], delta=f.get("delta"),
                   chart_note="Earlier figure implied from the reported growth rate." if f.get("implied") else "")
    elif f["kind"] == "ring":
        out.update(pct=f["pct"], pct_text=f["pct_text"], pct_label=r["tag"].split("·")[-1].strip())
    return out


def _pick(c, now, quota):
    st = load_state()
    sigs = {s for x in st["items"] for s in x.get("sigs", [])}
    stories = news.fetch(c, tz(c))
    trends = news.fetch_trends(c)
    return news.score_and_pick(stories, c, sigs, now.astimezone(timezone.utc), trends, quota)


def _record(folder, kind, picked):
    prune_items()
    save_item({"at": datetime.now(timezone.utc).isoformat(), "folder": str(folder.relative_to(ROOT)), "type": kind,
               "status": "drafted", "sigs": [g for s in picked for g in s["all_sigs"]]})


def _prune(days=10):
    """Delete queue folders older than `days` (Instagram has already fetched them)."""
    import shutil
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    for f in (ROOT / "queue").glob("20*"):
        if f.is_dir() and f.name[:10] < cutoff:
            shutil.rmtree(f, ignore_errors=True)


def _folder(now, kind):
    f = ROOT / "queue" / f"{now:%Y-%m-%d}-{kind}"
    return f if not f.exists() else ROOT / "queue" / f"{now:%Y-%m-%d-%H%M}-{kind}"


# ---------------------------------------------------------------- commands
def cmd_draft(a):
    c = cfg()
    now = datetime.now(tz(c))
    date_str = nice_date(now)
    _prune()
    if a.kind == "reel":
        cands = _pick(c, now, {"india": 2, "world": 1})
        if not cands:
            log.warning("no qualifying stories"); return output(folder="")
        from . import figures
        lead = max(cands, key=lambda s: s["score"] + (2 if figures.pick(s)["kind"] in ("bars", "ring") else 0))
        log.info("reel story %.1f [%s] %s", lead["score"], lead["category"], lead["title"])
        folder = _folder(now, "reel"); folder.mkdir(parents=True)
        r = writer.reel(lead, c)
        from . import reel
        rc = reel_content(r, c)
        voice = r["vo"] if c.get("reel", {}).get("voice", "none") != "none" else None
        music = c.get("reel", {}).get("music") or None
        mp4, cover, scenes = reel.render(rc, folder / "reel.mp4", music=(ROOT / music) if music else None, voice=voice, workdir=folder)
        meta = {"type": "reel", "date": date_str, "caption": writer.caption_reel(r, date_str), "video": mp4.name,
                "cover": cover.name, "slides": [cover.name], "scenes": scenes,
                "stories": [{"hook": r["headline"], "sources": lead["sources"], "link": lead["link"], "title": lead["title"]}]}
        (folder / "post.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
        _record(folder, "reel", [lead])
        return output(folder=str(folder.relative_to(ROOT)))

    picked = _pick(c, now, None)
    if not picked:
        log.warning("no qualifying stories today"); return output(folder="")
    for s in picked:
        log.info("pick %.1f [%s]%s %s (%s)", s["score"], s["category"], " TRENDING" if s.get("trending") else "", s["title"], ", ".join(s["sources"]))
    folder = _folder(now, "carousel")
    meta = writer.carousel(picked, c)
    paths = cards2.render_carousel(picked, meta, date_str, c, folder)
    post = {"type": "carousel", "date": date_str, "caption": writer.caption_carousel(picked, meta, date_str),
            "slides": [p.name for p in paths],
            "stories": [{k: s.get(k) for k in ("title", "hook", "points", "why", "category", "region", "sources", "link", "score", "trending")} for s in picked]}
    (folder / "post.json").write_text(json.dumps(post, indent=1, ensure_ascii=False))
    _record(folder, "carousel", picked)
    output(folder=str(folder.relative_to(ROOT)))


def _sha_for(folder):
    out = subprocess.run(["git", "log", "-1", "--format=%H", "--", folder], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not out:
        raise SystemExit(f"{folder} is not committed yet")
    return out


def _urls(folder, names, cdn=True):
    repo, sha = os.environ["GITHUB_REPOSITORY"], _sha_for(folder)
    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if base:
        return [f"{base}/{folder}/{n}" for n in names]
    if cdn:
        return [f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{folder}/{n}" for n in names]
    return [f"https://raw.githubusercontent.com/{repo}/{sha}/{folder}/{n}" for n in names]


def cmd_open_issue(a):
    from . import gh
    folder = a.folder
    meta = json.loads((ROOT / folder / "post.json").read_text())
    gh.ensure_labels()
    imgs = _urls(folder, meta["slides"], cdn=False)
    srcs = "\n".join(f"- **{s['hook']}** ({', '.join(s['sources'])}){' 🔥 trending' if s.get('trending') else ''} — [source]({s['link']})" for s in meta["stories"])
    is_reel = meta.get("type") == "reel"
    media = (f"**▶ [Watch the Reel]({_urls(folder, [meta['video']], cdn=False)[0]})**\n\n<img src=\"{imgs[0]}\" width=\"260\">"
             if is_reel else " ".join(f'<img src="{u}" width="220">' for u in imgs))
    body = f"""<!-- feedbot:folder={folder} -->
**To publish:** add the label `approved`. **To skip:** close this issue.
You can edit the caption below first (keep it inside the fence).

### Caption
```text
{meta['caption']}
```

### Stories
{srcs}

### {'Reel' if is_reel else 'Slides'}
{media}
"""
    n = gh.create_issue(f"Instagram draft: {'8 PM Reel' if is_reel else '8 AM Carousel'}, {meta['date']}", body)
    output(issue=n)


def _reachable(url):
    for _ in range(6):
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith(("image/", "video/", "application/octet-stream")):
                return True
        except requests.RequestException:
            pass
        time.sleep(5)
    return False


def cmd_publish(a):
    from . import instagram
    issue = None
    if a.issue:
        from . import gh
        issue = gh.get_issue(a.issue)
        body = issue["body"] or ""
        m = re.search(r"feedbot:folder=([^\s>]+)", body)
        if not m:
            raise SystemExit("issue is not a feedbot draft")
        folder = m.group(1)
        cm = re.search(r"### Caption\s*```(?:text)?\n(.*?)\n```", body, re.S)
    else:
        folder, cm = a.folder, None
    meta = json.loads((ROOT / folder / "post.json").read_text())
    cap = cm.group(1).strip() if cm else meta["caption"]

    is_reel = meta.get("type") == "reel"
    names = [meta["video"], meta["cover"]] if is_reel else meta["slides"]
    urls = _urls(folder, names, cdn=True)
    if not _reachable(urls[0]):
        log.warning("CDN not reachable yet, falling back to raw.githubusercontent.com")
        urls = _urls(folder, names, cdn=False)
    if a.dry_run:
        print(json.dumps({"folder": folder, "type": meta.get("type"), "urls": urls, "caption": cap}, indent=1, ensure_ascii=False))
        return
    token = os.environ["IG_ACCESS_TOKEN"].strip()
    uid = os.environ.get("IG_USER_ID") or None
    if is_reel:
        media_id, link = instagram.publish_reel(urls[0], urls[1], cap, token, uid)
    else:
        media_id, link = instagram.publish(urls, cap, token, uid)
    log.info("published %s %s", media_id, link)

    ip = _item_path(folder)
    item = json.loads(ip.read_text()) if ip.exists() else {"at": datetime.now(timezone.utc).isoformat(), "folder": folder, "sigs": []}
    item.update(status="published", media_id=media_id, permalink=link)
    save_item(item)
    if issue:
        from . import gh
        gh.comment(a.issue, f"Published to Instagram: {link or media_id}")
        gh.close(a.issue, labels=["insta-draft", "published"])
    output(permalink=link)


def cmd_refresh(a):
    from . import instagram
    cur = os.environ["IG_ACCESS_TOKEN"].strip()
    if instagram.never_expires(cur):
        log.info("system-user token: never expires, nothing to refresh")
        return
    tok, exp = instagram.refresh(cur)
    print(f"::add-mask::{tok}")
    (ROOT / "new_token.txt").write_text(tok)
    log.info("token refreshed, valid for %s days", int(exp or 0) // 86400)


def cmd_preview(a):
    c = cfg()
    stories = json.loads(Path(a.file).read_text())
    out = ROOT / "preview"
    date_str = nice_date(datetime.now(tz(c)))
    meta = writer.carousel(stories, c)
    paths = cards2.render_carousel(stories, meta, date_str, c, out)
    (out / "caption.txt").write_text(writer.caption_carousel(stories, meta, date_str))
    print("\n".join(map(str, paths)))


def main():
    p = argparse.ArgumentParser(prog="feedbot")
    sp = p.add_subparsers(dest="cmd", required=True)
    dr = sp.add_parser("draft"); dr.add_argument("--kind", choices=["carousel", "reel"], default="carousel"); dr.set_defaults(fn=cmd_draft)
    o = sp.add_parser("open-issue"); o.add_argument("--folder", required=True); o.set_defaults(fn=cmd_open_issue)
    pb = sp.add_parser("publish"); pb.add_argument("--issue", type=int); pb.add_argument("--folder")
    pb.add_argument("--dry-run", action="store_true"); pb.set_defaults(fn=cmd_publish)
    sp.add_parser("refresh-token").set_defaults(fn=cmd_refresh)
    pv = sp.add_parser("preview"); pv.add_argument("file"); pv.add_argument("--title")
    pv.set_defaults(fn=cmd_preview)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
