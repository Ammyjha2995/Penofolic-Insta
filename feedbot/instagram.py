"""Instagram Graph API (Instagram API with Instagram Login) publishing."""
import time, logging
import requests

log = logging.getLogger("feedbot")
VER = "v25.0"


def base(token):
    """IGAA... tokens (Instagram Login) use graph.instagram.com; EAA... tokens (business /
    system-user tokens from Meta's unified login) use graph.facebook.com."""
    return "https://graph.instagram.com" if token.startswith("IG") else "https://graph.facebook.com"


def never_expires(token):
    return not token.startswith("IG")


class IGError(RuntimeError):
    pass


def _call(method, path, token, **params):
    url = f"{base(token)}/{VER}/{path}"
    params["access_token"] = token
    r = requests.request(method, url, params=params if method == "GET" else None,
                         data=params if method == "POST" else None, timeout=60)
    try:
        js = r.json()
    except ValueError:
        js = {"raw": r.text[:300]}
    if r.status_code >= 400 or "error" in js:
        err = js.get("error", js)
        raise IGError(f"{method} {path} -> {r.status_code}: {err.get('message', err)}")
    return js


def account(token):
    if never_expires(token):
        raise IGError("With a system-user (EAA...) token, add the IG_USER_ID secret (the number under your account name in the Meta dashboard)")
    js = _call("GET", "me", token, fields="user_id,username")
    return js.get("user_id") or js.get("id"), js.get("username")


def _wait(container_id, token, tries=30):
    for _ in range(tries):
        st = _call("GET", container_id, token, fields="status_code").get("status_code")
        if st == "FINISHED":
            return
        if st in ("ERROR", "EXPIRED"):
            raise IGError(f"container {container_id} status {st}")
        time.sleep(4)
    raise IGError(f"container {container_id} not ready")


def publish(image_urls, caption, token, user_id=None):
    user_id = user_id or account(token)[0]
    if len(image_urls) == 1:
        c = _call("POST", f"{user_id}/media", token, image_url=image_urls[0], caption=caption)["id"]
    else:
        children = []
        for u in image_urls[:10]:
            cid = _call("POST", f"{user_id}/media", token, image_url=u, is_carousel_item="true")["id"]
            children.append(cid)
            log.info("item container %s", cid)
        for cid in children:
            _wait(cid, token)
        c = _call("POST", f"{user_id}/media", token, media_type="CAROUSEL",
                  children=",".join(children), caption=caption)["id"]
    _wait(c, token)
    media_id = _call("POST", f"{user_id}/media_publish", token, creation_id=c)["id"]
    try:
        link = _call("GET", media_id, token, fields="permalink").get("permalink", "")
    except IGError:
        link = ""
    return media_id, link


def refresh(token):
    """Swap a long-lived token (older than 24h) for a fresh 60-day one."""
    r = requests.get("https://graph.instagram.com/refresh_access_token",
                     params={"grant_type": "ig_refresh_token", "access_token": token}, timeout=30)
    js = r.json()
    if r.status_code >= 400 or "access_token" not in js:
        raise IGError(f"refresh failed: {js}")
    return js["access_token"], js.get("expires_in")
