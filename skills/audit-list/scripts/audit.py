#!/usr/bin/env python3
"""Checks every entry in list.json and prints one line per problem.

Usage: python3 audit.py [--list list.json]
Exit code is the number of problems.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", default="list.json")
    args = parser.parse_args()


    entries = json.loads(Path(args.list).read_text(encoding="utf-8"))
    token = _token()
    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched = list(pool.map(lambda e: gh("/repos/" + e["repo"], token), entries))

    problems = []
    seen = {}
    for entry, data in zip(entries, fetched):
        repo = entry["repo"]
        if data is None:
            problems.append(("missing", repo, "not found or private"))
            continue
        key = data["full_name"].lower()
        if key in seen:
            problems.append(("duplicate", repo, "same repository as " + seen[key]))
        seen[key] = repo
        if key != repo.lower():
            problems.append(("moved", repo, "now " + data["full_name"]))
        if data["archived"]:
            problems.append(("archived", repo, "last push " + data["pushed_at"][:10]))
        spdx = (data.get("license") or {}).get("spdx_id")
        if not entry.get("license") and (not spdx or spdx == "NOASSERTION"):
            problems.append(("license-unresolved", repo, "GitHub reports %s" % (spdx or "no license")))

    for problem in sorted(problems):
        print("\t".join(problem))
    print("%d entries checked, %d problem(s)" % (len(entries), len(problems)), file=sys.stderr)
    sys.exit(len(problems))


if __name__ == "__main__":
    main()
