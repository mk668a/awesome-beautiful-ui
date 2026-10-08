#!/usr/bin/env python3
"""Regenerates the list in README.md from list.json and live GitHub data.

Usage: python3 scripts/build.py
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

ROOT = Path(__file__).resolve().parent.parent
START = "<!-- LIST:START -->"
END = "<!-- LIST:END -->"

SECTIONS = [
    ("gems", "Hidden gems", "Lesser known, each with one effect or idea that is clearly its own."),
    ("motion", "Motion and text animation", None),
    ("components", "Components and design systems", None),
    ("webgl", "WebGL and creative coding", None),
    ("terminal", "Terminal and TUI", None),
    ("widgets", "Widgets and building blocks", None),
]

PERMISSIVE = {
    "MIT", "ISC", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "0BSD", "Unlicense", "CC0-1.0",
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


def months_ago(months):
    """Today minus N calendar months, as a date."""
    today = date.today()
    index = today.year * 12 + today.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(today.day, last_day))


def stars(n):
    if n < 1000:
        return str(n)
    return "%.1fk" % (n / 1000) if n < 10000 else "%.0fk" % (n / 1000)


def license_tag(entry, data):
    spdx = entry.get("license") or (data.get("license") or {}).get("spdx_id")
    if not spdx or spdx == "NOASSERTION":
        return "license: see repo ⚠"
    return spdx if spdx in PERMISSIVE else spdx + " ⚠"


def line(e):
    return "- [%s](https://github.com/%s) - %s `★ %s` `%s` `%s`" % (
        e["name"], e["full_name"], e["note"], stars(e["stars"]), e["license_tag"], e["pushed"][:7],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    entries = json.loads((ROOT / "list.json").read_text(encoding="utf-8"))
    known = {section for section, _, _ in SECTIONS}
    for e in entries:
        if e["section"] not in known:
            sys.exit('%s: unknown section "%s"' % (e["repo"], e["section"]))

    # The activity window is defined once, with the other inclusion rules.
    rules = json.loads((ROOT / "skills/judge-candidates/rules.json").read_text(encoding="utf-8"))["rules"]
    quiet_after = next(r["value"] for r in rules if r["id"] == "active")
    cutoff = months_ago(quiet_after).isoformat()

    token = _token()

    def resolve(entry):
        data = gh("/repos/" + entry["repo"], token)
        if data is None:
            print("warning: %s: not found; skipped (kept in list.json)" % entry["repo"], file=sys.stderr)
            return None
        if data["full_name"].lower() != entry["repo"].lower():
            print("moved: %s -> %s (update list.json)" % (entry["repo"], data["full_name"]), file=sys.stderr)
        return dict(
            entry,
            full_name=data["full_name"],
            stars=data["stargazers_count"],
            pushed=data["pushed_at"],
            license_tag=license_tag(entry, data),
            quiet=data["archived"] or data["pushed_at"][:10] < cutoff,
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        resolved = list(pool.map(resolve, entries))

    skipped = sum(e is None for e in resolved)
    resolved = [e for e in resolved if e is not None]
    active = [e for e in resolved if not e["quiet"]]
    quiet = [e for e in resolved if e["quiet"]]
    by_stars = lambda e: -e["stars"]

    out = ["_Last refreshed %s. %d active, %d quiet._" % (date.today().isoformat(), len(active), len(quiet)), ""]
    if skipped:
        out += ["_%d unavailable repositories omitted from this refresh._" % skipped, ""]
    for section, title, intro in SECTIONS:
        rows = sorted((e for e in active if e["section"] == section), key=by_stars)
        if not rows:
            continue
        out += ["## " + title, ""]
        if intro:
            out += [intro, ""]
        out += [line(e) for e in rows] + [""]
    out += [
        "## Quiet classics",
        "",
        "No push in the last %d months, or archived. Many of these are simply finished. "
        "They move back up on their own when development resumes." % quiet_after,
        "",
    ]
    out += [line(e) for e in sorted(quiet, key=by_stars)] + [""]

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    a, b = readme.find(START), readme.find(END)
    if a < 0 or b < a:
        sys.exit("README.md is missing the LIST markers")
    readme_path.write_text(readme[: a + len(START)] + "\n" + "\n".join(out) + readme[b:], encoding="utf-8")
    print("README.md updated: %d active, %d quiet" % (len(active), len(quiet)))


if __name__ == "__main__":
    main()
