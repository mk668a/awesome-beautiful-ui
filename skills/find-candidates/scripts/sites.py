#!/usr/bin/env python3
"""Records the product sites an agent finds with the "web" phrases in
queries.json. A script cannot run a web search, so the agent searches and this
script keeps the bookkeeping: normalized URLs, exclusions and canary coverage.

Usage: python3 sites.py start [--only QUERY_ID]...
       python3 sites.py add --query QUERY_ID URL [URL ...]
       python3 sites.py check

start   writes an empty research/site-candidates.json and prints one search
        phrase per line, as QUERY_ID<TAB>PHRASE.
add     records the product sites one phrase surfaced. Sites already listed
        or researched are noted as surfaced but not written as candidates.
check   reports whether every webCanaries site was surfaced. Exit code is
        the number of canaries missed; a miss means the phrases need work.
"""

import argparse
import fcntl
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

NOT_A_PRODUCT = re.compile(r"(^|\.)(github\.com|githubusercontent\.com|npmjs\.com|youtube\.com|x\.com|twitter\.com|reddit\.com|medium\.com)$")


def site_url(url):
    """Canonical form of a site URL: https, no www, query or trailing slash."""
    parts = urlsplit(url.strip())
    host = (parts.hostname or "").lower()
    host = host[4:] if host.startswith("www.") else host
    return "https://" + host + parts.path.rstrip("/")


def known_sites(list_path, findings):
    known = {site_url(e["url"]) for e in json.loads(Path(list_path).read_text(encoding="utf-8")) if e.get("url")}
    for path in Path(findings).glob("*.json"):
        finding = json.loads(path.read_text(encoding="utf-8"))
        for url in (finding.get("url"), (finding.get("facts") or {}).get("url")):
            if isinstance(url, str):
                known.add(site_url(url))
    return known


def read(out):
    if not out.exists():
        sys.exit("%s not found. Run: sites.py start" % out)
    return json.loads(out.read_text(encoding="utf-8"))


def write(out, data):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["start", "add", "check"])
    parser.add_argument("urls", nargs="*")
    parser.add_argument("--queries", default=str(Path(__file__).resolve().parent.parent / "queries.json"))
    parser.add_argument("--list", default="list.json")
    parser.add_argument("--findings", default="research/findings")
    parser.add_argument("--out", default="research/site-candidates.json")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--query", help="the query id whose phrase surfaced the URLs (add)")
    args = parser.parse_args()

    config = json.loads(Path(args.queries).read_text(encoding="utf-8"))
    queries = {q["id"]: q for q in config["queries"] if q.get("web")}
    out = Path(args.out)

    if args.command == "start":
        selected = [q for q in queries.values() if not args.only or q["id"] in args.only]
        if not selected:
            sys.exit("No web query matches --only %s" % ", ".join(args.only))
        write(out, {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "queryIds": [q["id"] for q in selected], "surfaced": {}, "candidates": []})
        for q in selected:
            for phrase in q["web"]:
                print("%s\t%s" % (q["id"], phrase))
        return

    if args.command == "add":
        if args.query not in queries:
            parser.error("--query must be one of: %s" % ", ".join(queries))
        if not args.urls or not all(u.startswith(("http://", "https://")) for u in args.urls):
            parser.error("give the product site URLs")
        known = known_sites(args.list, args.findings)
        read(out)
        # Agents searching in parallel add at the same time.
        lock = open(out, "a")
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = read(out)
        candidates = {c["url"]: c for c in data["candidates"]}
        for raw in args.urls:
            url = site_url(raw)
            if NOT_A_PRODUCT.search(urlsplit(url).hostname or ""):
                print("skip\t%s\tnot a product site; research a repository with collect_facts.py" % url)
                continue
            seen = data["surfaced"].setdefault(url, [])
            if args.query not in seen:
                seen.append(args.query)
            if url in known:
                print("known\t%s" % url)
            elif url in candidates:
                print("again\t%s" % url)
            else:
                candidates[url] = {"url": url, "queryIds": seen}
                print("new\t%s" % url)
        data["candidates"] = list(candidates.values())
        write(out, data)
        lock.close()
        return

    data = read(out)
    missed = [c for c in config.get("webCanaries", []) if site_url(c) not in data["surfaced"]]
    for canary in config.get("webCanaries", []):
        found_by = data["surfaced"].get(site_url(canary))
        print("%s\t%s\t%s" % ("ok" if found_by else "MISSED", site_url(canary), ",".join(found_by or [])))
    print("%d candidates, %d surfaced; %d canary missed" % (len(data["candidates"]), len(data["surfaced"]), len(missed)),
          file=sys.stderr)
    sys.exit(len(missed))


if __name__ == "__main__":
    main()
