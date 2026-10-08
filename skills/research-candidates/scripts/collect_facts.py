#!/usr/bin/env python3
"""Fetches the machine-checkable facts for repositories and stores each as a
finding file. An existing research block is kept, so facts can be refreshed.

Usage: python3 collect_facts.py owner/name [owner/name ...] [--out research/findings]
       python3 collect_facts.py --candidates research/candidates.json [--limit N]

With a single repository it also prints the README start for the researcher.
"""

import argparse
import base64
import copy
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

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
            candidates = sorted(candidates, key=lambda c: (
                c["stars"] if args.order == "stars-asc" else -c["stars"], c["repo"].lower()
            ))
        repos += [c["repo"] for c in candidates]
    repos = list(dict.fromkeys(repo.lower() for repo in repos))
    if args.limit is not None:
        repos = repos[:args.limit]
    if not repos or any("/" not in r for r in repos):
        parser.error("give owner/name repositories or --candidates <file>")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    token = _token()
    for repo in repos:
        facts, readme_head = collect(repo, token)
        path = out_dir / (facts["repo"].lower().replace("/", "__") + ".json")
        research = copy.deepcopy(EMPTY_RESEARCH)
        if path.exists() and not args.reset_research:
            research = json.loads(path.read_text(encoding="utf-8")).get("research") or research
        finding = {"schema": 1, "repo": facts["repo"], "facts": facts, "research": research}
        path.write_text(json.dumps(finding, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if len(repos) == 1:
            print(json.dumps({"file": str(path), "facts": facts, "readmeHead": readme_head}, indent=2, ensure_ascii=False))
        else:
            print("%s\t%s" % (path, research["status"]))


if __name__ == "__main__":
    main()
