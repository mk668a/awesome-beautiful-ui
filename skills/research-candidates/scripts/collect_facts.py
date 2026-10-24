#!/usr/bin/env python3
"""Fetches the machine-checkable facts for repositories and product sites and
stores each as a finding file. An existing research block is kept, so facts can
be refreshed.

Usage: python3 collect_facts.py owner/name|https://site [...] [--out research/findings]
       python3 collect_facts.py --candidates research/candidates.json [--limit N]

A site is a product outside GitHub, recorded by its URL. With a single
repository or site it also prints the README start or the page description.
"""

import argparse
import base64
import copy
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

EMPTY_RESEARCH = {
    "status": "pending",
    "researchedAt": None,
    "kind": None,
    "section": None,
    "name": None,
    "note": None,
    "license": None,
    "requiresHostedService": None,
    "genericCollection": None,
    "demoViewed": None,
    "signature": {"effects": [], "evidenceUrls": []},
    "unverified": [],
}

EMPTY_SITE_RESEARCH = {
    "status": "pending",
    "researchedAt": None,
    "kind": None,
    "name": None,
    "note": None,
    "openSource": None,
    "pricing": None,
    "lastUpdated": None,
    "lastUpdatedEvidence": [],
    "genericCollection": None,
    "demoViewed": None,
    "signature": {"effects": [], "evidenceUrls": []},
    "unverified": [],
}

USER_AGENT = "Mozilla/5.0 (compatible; awesome-beautiful-ui)"


def is_url(value):
    return value.startswith(("http://", "https://"))


def site_url(url):
    """Canonical form of a site URL: https, no www, query or trailing slash."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    return "https://" + host + parts.path.rstrip("/")


def site_slug(url):
    parts = urlsplit(site_url(url))
    return "site__" + re.sub(r"[^a-z0-9.]+", "_", (parts.hostname + parts.path).lower()).strip("_")


class PageMeta(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title, self.meta, self._in_title = "", {}, False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta" and attrs.get("content"):
            key = attrs.get("name") or attrs.get("property")
            if key:
                self.meta.setdefault(key.lower(), attrs["content"].strip())

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def collect_site(url):
    url = site_url(url)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    facts = {"found": False, "url": url, "finalUrl": None, "status": None,
             "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            facts.update(status=res.status, finalUrl=res.geturl())
            body = res.read(2_000_000).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as err:
        # Only a gone page is a confirmed absence. Bot walls and rate limits leave it unknown.
        facts.update(status=err.code, found=False if err.code in (404, 410) else None)
        return facts, None
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        # Unreachable is recorded, not fatal, so one dead site does not stop a batch.
        facts.update(found=None, error=str(getattr(err, "reason", err)))
        return facts, None
    page = PageMeta()
    page.feed(body)
    description = page.meta.get("description") or page.meta.get("og:description")
    facts.update(
        found=True,
        title=" ".join(page.title.split()) or page.meta.get("og:title"),
        description=description,
        keywords=page.meta.get("keywords"),
    )
    return facts, description


def _token():
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        return env
    try:
        return subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("No GitHub token. Set GITHUB_TOKEN or log in with the gh CLI.")


def gh(path, token):
    """GET a GitHub API path. Returns None on 404."""
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "User-Agent": "awesome-beautiful-ui",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise SystemExit("%s: HTTP %s" % (path, err.code))


def decode(file):
    if not file or not file.get("content"):
        return None
    return base64.b64decode(file["content"]).decode("utf-8", errors="replace")


def head(text, lines, chars):
    if text is None:
        return None
    return "\n".join([l for l in text.splitlines() if l.strip()][:lines])[:chars]


def collect(repo, token):
    data = gh("/repos/" + repo, token)
    if data is None:
        return {"found": False, "repo": repo}, None
    name = data["full_name"]
    license_file = gh("/repos/%s/license" % name, token)
    readme = gh("/repos/%s/readme" % name, token)
    root = gh("/repos/%s/contents" % name, token)
    facts = {
        "found": True,
        "repo": name,
        "movedFrom": None if name.lower() == repo.lower() else repo,
        "fetchedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stars": data["stargazers_count"],
        "archived": data["archived"],
        "fork": data["fork"],
        "created": data["created_at"][:10],
        "pushed": data["pushed_at"][:10],
        "description": data.get("description"),
        "homepage": data.get("homepage") or None,
        "topics": data.get("topics") or [],
        "license": {
            "spdx": (data.get("license") or {}).get("spdx_id"),
            "file": (license_file or {}).get("path"),
            "head": head(decode(license_file), 12, 1200),
        },
        "rootFiles": [f["name"] for f in root] if isinstance(root, list) else [],
    }
    return facts, head(decode(readme), 80, 5000)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("repos", nargs="*")
    parser.add_argument("--candidates")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--order", choices=["stars-asc", "stars-desc", "input"], default="stars-asc")
    parser.add_argument("--reset-research", action="store_true", help="reset selected findings to pending")
    parser.add_argument("--out", default="research/findings")
    args = parser.parse_args()


    repos = list(args.repos)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    if args.candidates:
        candidates = json.loads(Path(args.candidates).read_text(encoding="utf-8"))["candidates"]
        if args.order != "input":
            # Site candidates have no stars and keep their order ahead of repositories.
            candidates = sorted(candidates, key=lambda c: (
                c.get("stars", 0) if args.order == "stars-asc" else -c.get("stars", 0),
                (c.get("repo") or "").lower()
            ))
        repos += [c.get("repo") or c["url"] for c in candidates]
    repos = list(dict.fromkeys(site_url(r) if is_url(r) else r.lower() for r in repos))
    if args.limit is not None:
        repos = repos[:args.limit]
    if not repos or any("/" not in r for r in repos):
        parser.error("give owner/name repositories, site URLs or --candidates <file>")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    token = None if all(is_url(r) for r in repos) else _token()
    for repo in repos:
        if is_url(repo):
            facts, intro = collect_site(repo)
            path = out_dir / (site_slug(facts["url"]) + ".json")
            research = copy.deepcopy(EMPTY_SITE_RESEARCH)
            identity = {"url": facts["url"]}
        else:
            facts, intro = collect(repo, token)
            path = out_dir / (facts["repo"].lower().replace("/", "__") + ".json")
            research = copy.deepcopy(EMPTY_RESEARCH)
            identity = {"repo": facts["repo"]}
        if path.exists() and not args.reset_research:
            research = json.loads(path.read_text(encoding="utf-8")).get("research") or research
        finding = dict({"schema": 1}, **identity, facts=facts, research=research)
        path.write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if len(repos) == 1:
            label = "description" if is_url(repo) else "readmeHead"
            print(json.dumps({"file": str(path), "facts": facts, label: intro}, indent=2, ensure_ascii=False))
        else:
            print("%s\t%s" % (path, research["status"]))


if __name__ == "__main__":
    main()
