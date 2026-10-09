#!/usr/bin/env python3
"""Applies rules.json to every finding file and writes the verdicts.

No network: the same findings, rules and as-of date give the same verdicts.

Usage: python3 judge.py [--findings research/findings] [--rules rules.json]
                        [--out research/verdicts.json] [--list list.json] [--apply]
"""

import argparse
import json
import math
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit


def months_ago(months, as_of=None):
    """Today minus N calendar months, as a date."""
    today = as_of or date.today()
    index = today.year * 12 + today.month - 1 - months
    year, month = divmod(index, 12)
    month += 1
    last_day = (date(year + month // 12, month % 12 + 1, 1) - timedelta(days=1)).day
    return date(year, month, min(today.day, last_day))


def get(obj, path):
    for key in path.split("."):
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def parse_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("expected YYYY-MM-DD")
    return date.fromisoformat(value)


def string_list(value):
    return isinstance(value, list) and all(isinstance(s, str) and s.strip() for s in value)


def http_url(value):
    try:
        url = urlsplit(value)
        return (not any(c.isspace() for c in value) and url.scheme in ("http", "https")
                and bool(url.hostname) and not url.username and not url.password)
    except ValueError:
        return False


def valid_input(value, rule, as_of):
    """Unknown or malformed observations are not evidence of rejection."""
    op, expected = rule["op"], rule.get("value")
    if op in ("withinMonths", "date"):
        try:
            return parse_date(value) <= as_of
        except ValueError:
            return False
    if op in ("minLength", "httpUrls") or (op == "eq" and isinstance(expected, list)):
        return string_list(value)
    if op == "gte":
        return type(value) in (int, float) and math.isfinite(value)
    if op == "eq":
        return type(value) is type(expected)
    return isinstance(value, str) and bool(value.strip())


OPS = {
    "eq": lambda v, x: type(v) is type(x) and v == x,
    "in": lambda v, x: v in x,
    "notIn": lambda v, x: v.casefold() not in {s.casefold() for s in x},
    "gte": lambda v, x: isinstance(v, (int, float)) and not isinstance(v, bool) and v >= x,
    "minLength": lambda v, x: string_list(v) and len(v) >= x,
    "nonEmpty": lambda v, x: isinstance(v, str) and bool(v.strip()),
    "matches": lambda v, x: isinstance(v, str) and re.fullmatch(x, v) is not None,
    "knownLicense": lambda v, x: v.strip().casefold() not in {s.casefold() for s in x},
    "httpUrls": lambda v, x: len(v) >= x and all(http_url(s) for s in v),
    "date": lambda v, x: True,  # checked by valid_input
    "withinMonths": lambda v, x: parse_date(v) >= months_ago(x),
}


def judge(finding, rules, verdicts, as_of=None):
    as_of = as_of or date.today()
    researched = get(finding, "research.status") == "done"
    failed = []
    repo = get(finding, "facts.repo")
    if not isinstance(repo, str) or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo, flags=re.ASCII):
        failed.append({"id": "repo", "onFail": "needs-research", "reason": "Missing or invalid facts.repo."})
    for r in rules:
        if r["stage"] == "research" and not researched:
            continue
        value = get(finding, r["field"])
        if not valid_input(value, r, as_of):
            failed.append({"id": r["id"], "onFail": "needs-research",
                           "reason": "Missing or invalid %s." % r["field"]})
            continue
        passed = (parse_date(value) >= months_ago(r["value"], as_of)
                  if r["op"] == "withinMonths" else OPS[r["op"]](value, r.get("value")))
        if not passed:
            failed.append({"id": r["id"], "onFail": r["onFail"], "reason": r["reason"]})
    # The most severe failure wins. verdicts is ordered from most to least severe.
    for verdict in verdicts:
        if any(f["onFail"] == verdict for f in failed):
            return verdict, failed
    return verdicts[-1], failed


def entry_for(finding):
    facts, research = finding["facts"], finding["research"]
    entry = {"section": research["section"], "repo": facts["repo"], "name": research["name"], "note": research["note"]}
    spdx = get(finding, "facts.license.spdx")
    unresolved = not spdx or spdx == "NOASSERTION"
    if unresolved and research.get("license") and research["license"] != "unknown":
        entry["license"] = research["license"]
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--findings", default="research/findings")
    parser.add_argument("--rules", default=str(Path(__file__).resolve().parent.parent / "rules.json"))
    parser.add_argument("--out", default="research/verdicts.json")
    parser.add_argument("--list", default="list.json")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--as-of", type=parse_date, default=date.today(), metavar="YYYY-MM-DD")
    args = parser.parse_args()

    config = json.loads(Path(args.rules).read_text(encoding="utf-8"))
    rules, verdicts = config["rules"], config["verdicts"]
    for r in rules:
        if r["op"] not in OPS:
            sys.exit('rule %s: unknown op "%s"' % (r["id"], r["op"]))
        if r["onFail"] not in verdicts:
            sys.exit('rule %s: unknown verdict "%s"' % (r["id"], r["onFail"]))

    results = []
    for path in sorted(Path(args.findings).glob("*.json")):
        finding = json.loads(path.read_text(encoding="utf-8"))
        verdict, failed = judge(finding, rules, verdicts, args.as_of)
        results.append({
            "repo": get(finding, "facts.repo") or get(finding, "repo") or path.stem,
            "verdict": verdict,
            "failed": failed,
            "entry": entry_for(finding) if verdict in ("include", "quiet") else None,
        })

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(
            {"judgedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "asOf": args.as_of.isoformat(), "results": results},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    for r in results:
        print("\t".join([r["verdict"], str(r["repo"]), ",".join(f["id"] for f in r["failed"]) or "-"]))
    counts = ", ".join("%d %s" % (sum(r["verdict"] == v for r in results), v) for v in verdicts)
    print("%d judged: %s. Written to %s" % (len(results), counts, args.out), file=sys.stderr)

    if args.apply:
        list_path = Path(args.list)
        entries = json.loads(list_path.read_text(encoding="utf-8"))
        listed = {e["repo"].lower() for e in entries}
        added = []
        for result in results:
            entry = result["entry"]
            if entry and entry["repo"].lower() not in listed:
                added.append(entry)
                listed.add(entry["repo"].lower())
        rows = ["  { %s }" % json.dumps(e, ensure_ascii=False)[1:-1] for e in entries + added]
        list_path.write_text("[\n" + ",\n".join(rows) + "\n]\n", encoding="utf-8")
        print("%d entries added to %s. Run python3 scripts/build.py to regenerate the README." % (len(added), list_path), file=sys.stderr)


if __name__ == "__main__":
    main()
