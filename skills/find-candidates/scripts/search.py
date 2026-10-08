#!/usr/bin/env python3
"""Runs the searches defined in queries.json and writes the candidates that are
not yet in list.json or the findings directory.

Usage: python3 search.py [--queries queries.json] [--list list.json]
                         [--out research/candidates.json]
                         [--only QUERY_ID]... [--min-stars N] [--new-within-days N]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
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
    parser.add_argument("--queries", default=str(Path(__file__).resolve().parent.parent / "queries.json"))
    parser.add_argument("--list", default="list.json")
    parser.add_argument("--findings", default="research/findings")
    parser.add_argument("--order", choices=["asc", "desc"], help="GitHub star ordering")
    parser.add_argument("--out", default="research/candidates.json")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--min-stars", type=int)
    parser.add_argument("--new-within-days", type=int)
    args = parser.parse_args()


    config = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    order = args.order or config.get("order", "asc")
    if order not in ("asc", "desc"):
        parser.error("queries.order must be asc or desc")
    filters = dict(config["filters"])
    if args.min_stars is not None:
        filters["minStars"] = args.min_stars

    queries = [q for q in config["queries"] if not args.only or q["id"] in args.only]
    if not queries:
        sys.exit("No query matches --only %s" % ", ".join(args.only))

    flag = lambda value: "true" if value else "false"
    qualifiers = [
        "pushed:>%s" % months_ago(filters["pushedWithinMonths"]).isoformat(),
        "stars:>=%d" % filters["minStars"],
        "archived:" + flag(filters["archived"]),
        "fork:" + flag(filters["fork"]),
    ]
    if args.new_within_days:
        qualifiers.append("created:>%s" % (date.today() - timedelta(days=args.new_within_days)).isoformat())

    listed = {e["repo"].lower() for e in json.loads(Path(args.list).read_text(encoding="utf-8"))}
    for path in Path(args.findings).glob("*.json"):
        finding = json.loads(path.read_text(encoding="utf-8"))
        facts = finding.get("facts") or {}
        for repo in (finding.get("repo"), facts.get("repo"), facts.get("movedFrom")):
            if isinstance(repo, str):
                listed.add(repo.lower())
    exclude = config.get("exclude", {})
    exclude_name = re.compile(exclude["namePattern"], re.I) if exclude.get("namePattern") else None
    exclude_topics = set(exclude.get("topics", []))

    token = _token()
    found = {}
    excluded = 0
    for query in queries:
        q = urllib.parse.quote("%s %s" % (query["q"], " ".join(qualifiers)))
        data = gh("/search/repositories?q=%s&sort=stars&order=%s&per_page=%d" % (q, order, config["perQuery"]), token)
        for r in (data or {}).get("items", []):
            key = r["full_name"].lower()
            if key in listed:
                continue
            if key in found:
                found[key]["queryIds"].append(query["id"])
                continue
            topics = r.get("topics") or []
            if (exclude_name and exclude_name.search(r["name"])) or exclude_topics.intersection(topics):
                excluded += 1
                continue
            found[key] = {
                "repo": r["full_name"],
                "stars": r["stargazers_count"],
                "created": r["created_at"][:10],
                "pushed": r["pushed_at"][:10],
                "license": (r.get("license") or {}).get("spdx_id"),
                "topics": topics,
                "description": r.get("description"),
                "queryIds": [query["id"]],
                "suggestedSection": query["section"],
            }

    candidates = sorted(found.values(), key=lambda c: (
        c["stars"] if order == "asc" else -c["stars"], c["repo"].lower()
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "qualifiers": qualifiers,
                "queryIds": [q["id"] for q in queries],
                "order": order,
                "candidates": candidates,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    for c in candidates:
        description = " ".join((c["description"] or "").split())[:110]
        print("\t".join([c["repo"], str(c["stars"]), c["pushed"], ",".join(c["queryIds"]), description]))
    print("%d candidates written to %s (%d dropped by exclude rules)" % (len(candidates), out, excluded), file=sys.stderr)


if __name__ == "__main__":
    main()
