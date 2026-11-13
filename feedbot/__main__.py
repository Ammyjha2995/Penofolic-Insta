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

from . import news, writer, cards

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


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"items": []}


def save_state(st):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=21)).isoformat()
    st["items"] = [x for x in st["items"] if x.get("at", "") >= cutoff]
    STATE.write_text(json.dumps(st, indent=1, ensure_ascii=False))


def output(**kv):
    path = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"{k}={v}")
        if path:
            with open(path, "a") as f:
                f.write(f"{k}={v}\n")


def nice_date(d):
    return f"{d.day} {d:%B %Y}"


def make_post(stories, c, folder, date_str):
    title = writer.write(stories, c)
    cap = writer.caption(stories, title, c, date_str)
    paths = cards.render_all(stories, title, date_str, c, folder)
    meta = {"date": date_str, "cover": title, "caption": cap, "slides": [p.name for p in paths],
            "stories": [{k: s.get(k) for k in ("title", "hook", "points", "why", "category", "sources", "links", "score", "link", "summary")} for s in stories]}
    (Path(folder) / "post.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    return meta


# ---------------------------------------------------------------- commands
def cmd_draft(a):
    c = cfg()
    now = datetime.now(tz(c))
    st = load_state()
    sigs = {s for x in st["items"] for s in x.get("sigs", [])}
    picked = news.score_and_pick(news.fetch(c, tz(c)), c, sigs, now.astimezone(timezone.utc))
    if not picked:
        log.warning("no qualifying stories today")
        return output(folder="")
    for s in picked:
        log.info("pick %.1f [%s] %s (%s)", s["score"], s["category"], s["title"], ", ".join(s["sources"]))
    folder = ROOT / "queue" / now.strftime("%Y-%m-%d")
    if folder.exists():
        folder = ROOT / "queue" / now.strftime("%Y-%m-%d-%H%M")
    make_post(picked, c, folder, nice_date(now))
    st["items"].append({"at": datetime.now(timezone.utc).isoformat(), "folder": str(folder.relative_to(ROOT)),
                        "status": "drafted", "sigs": [g for s in picked for g in s["all_sigs"]]})
    save_state(st)
    output(folder=str(folder.relative_to(ROOT)))


def _sha_for(folder):
    out = subprocess.run(["git", "log", "-1", "--format=%H", "--", folder], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if not out:
        raise SystemExit(f"{folder} is not committed yet")
    return out


def _urls(folder, meta, cdn=True):
    repo, sha = os.environ["GITHUB_REPOSITORY"], _sha_for(folder)
    base = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
    if base:
        return [f"{base}/{folder}/{n}" for n in meta["slides"]]
    if cdn:
        return [f"https://cdn.jsdelivr.net/gh/{repo}@{sha}/{folder}/{n}" for n in meta["slides"]]
    return [f"https://raw.githubusercontent.com/{repo}/{sha}/{folder}/{n}" for n in meta["slides"]]


def cmd_open_issue(a):
    from . import gh
    folder = a.folder
    meta = json.loads((ROOT / folder / "post.json").read_text())
    gh.ensure_labels()
    imgs = _urls(folder, meta, cdn=False)
    srcs = "\n".join(f"- **{s['hook']}** ({', '.join(s['sources'])}) — [source]({s['link']})" for s in meta["stories"])
    body = f"""<!-- feedbot:folder={folder} -->
**To publish:** add the label `approved`. **To skip:** close this issue.
You can edit the caption below first (keep it inside the fence).

### Caption
```text
{meta['caption']}
```

### Stories
{srcs}

### Slides
{' '.join(f'<img src="{u}" width="220">' for u in imgs)}
"""
    n = gh.create_issue(f"Instagram draft: Economy Today, {meta['date']}", body)
    output(issue=n)


def _reachable(url):
    for _ in range(6):
        try:
            r = requests.get(url, timeout=30, stream=True)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
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

    urls = _urls(folder, meta, cdn=True)
    if not _reachable(urls[0]):
        log.warning("CDN not reachable yet, falling back to raw.githubusercontent.com")
        urls = _urls(folder, meta, cdn=False)
    if a.dry_run:
        print(json.dumps({"folder": folder, "urls": urls, "caption": cap}, indent=1, ensure_ascii=False))
        return
    token = os.environ["IG_ACCESS_TOKEN"].strip()
    media_id, link = instagram.publish(urls, cap, token, os.environ.get("IG_USER_ID") or None)
    log.info("published %s %s", media_id, link)

    st = load_state()
    for x in st["items"]:
        if x.get("folder") == folder:
            x.update(status="published", media_id=media_id, permalink=link)
    save_state(st)
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
    title = a.title or "What moved India's economy"
    if a.ai:
        title = writer.write(stories, c)
    else:
        for s in stories:
            s.setdefault("hook", s["title"]); s.setdefault("points", []); s.setdefault("why", "")
    paths = cards.render_all(stories, title, date_str, c, out)
    (out / "caption.txt").write_text(writer.caption(stories, title, c, date_str))
    print("\n".join(map(str, paths)))


def main():
    p = argparse.ArgumentParser(prog="feedbot")
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("draft").set_defaults(fn=cmd_draft)
    o = sp.add_parser("open-issue"); o.add_argument("--folder", required=True); o.set_defaults(fn=cmd_open_issue)
    pb = sp.add_parser("publish"); pb.add_argument("--issue", type=int); pb.add_argument("--folder")
    pb.add_argument("--dry-run", action="store_true"); pb.set_defaults(fn=cmd_publish)
    sp.add_parser("refresh-token").set_defaults(fn=cmd_refresh)
    pv = sp.add_parser("preview"); pv.add_argument("file"); pv.add_argument("--title"); pv.add_argument("--ai", action="store_true")
    pv.set_defaults(fn=cmd_preview)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
