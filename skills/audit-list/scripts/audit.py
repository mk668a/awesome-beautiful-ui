#!/usr/bin/env python3
"""Checks every entry in list.json and prints one line per problem.

Usage: python3 audit.py [--list list.json]
Exit code is the number of problems.

Entries with a "url" are sites outside GitHub: they are checked for an HTTP
error and for a confirmed update older than the site-active rule allows.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

RULES = Path(__file__).resolve().parents[2] / "judge-candidates" / "rules.json"


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


def site_status(url):
    """HTTP status of a site, or the network error as text."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; awesome-beautiful-ui)"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status
    except urllib.error.HTTPError as err:
        return err.code
    except (urllib.error.URLError, TimeoutError) as err:
        return str(getattr(err, "reason", err))


def months_ago(months):
    """Today minus N calendar months, as a date."""
    today = date.today()
    index = today.year * 12 + today.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(today.day, last_day))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", default="list.json")
    args = parser.parse_args()


    all_entries = json.loads(Path(args.list).read_text(encoding="utf-8"))
    entries = [e for e in all_entries if e.get("repo")]
    sites = [e for e in all_entries if e.get("url")]
    token = _token() if entries else None
    with ThreadPoolExecutor(max_workers=8) as pool:
        fetched = list(pool.map(lambda e: gh("/repos/" + e["repo"], token), entries))
        statuses = list(pool.map(lambda e: site_status(e["url"]), sites))

    problems = []
    rules = json.loads(RULES.read_text(encoding="utf-8"))["rules"]
    cutoff = months_ago(next(r["value"] for r in rules if r["id"] == "site-active")).isoformat()
    seen_sites = {}
    for entry, status in zip(sites, statuses):
        url = entry["url"]
        if url.lower() in seen_sites:
            problems.append(("duplicate", url, "same site as " + seen_sites[url.lower()]))
        seen_sites[url.lower()] = url
        if status != 200:
            problems.append(("unreachable", url, "HTTP %s" % status if isinstance(status, int) else status))
        if entry.get("updated", "") < cutoff:
            problems.append(("stale", url, "update last confirmed %s" % entry.get("updated")))

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
    print("%d entries checked, %d problem(s)" % (len(all_entries), len(problems)), file=sys.stderr)
    sys.exit(len(problems))


if __name__ == "__main__":
    main()
