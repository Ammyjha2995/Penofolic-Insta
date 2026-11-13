"""Minimal GitHub REST helpers (issues used as the approval inbox)."""
import os, requests

API = "https://api.github.com"


def _h():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"}


def repo():
    return os.environ["GITHUB_REPOSITORY"]


def ensure_labels():
    for name, color, desc in [("insta-draft", "0f2234", "Instagram draft awaiting approval"),
                              ("approved", "bb9c63", "Publish this draft to Instagram"),
                              ("published", "2e7d32", "Posted to Instagram")]:
        requests.post(f"{API}/repos/{repo()}/labels", headers=_h(), timeout=30,
                      json={"name": name, "color": color, "description": desc})  # 422 if it exists: fine


def create_issue(title, body):
    r = requests.post(f"{API}/repos/{repo()}/issues", headers=_h(), timeout=30,
                      json={"title": title, "body": body, "labels": ["insta-draft"]})
    r.raise_for_status()
    return r.json()["number"]


def get_issue(n):
    r = requests.get(f"{API}/repos/{repo()}/issues/{n}", headers=_h(), timeout=30)
    r.raise_for_status()
    return r.json()


def comment(n, text):
    requests.post(f"{API}/repos/{repo()}/issues/{n}/comments", headers=_h(), timeout=30, json={"body": text})


def close(n, labels=None):
    payload = {"state": "closed"}
    if labels is not None:
        payload["labels"] = labels
    requests.patch(f"{API}/repos/{repo()}/issues/{n}", headers=_h(), timeout=30, json=payload)
