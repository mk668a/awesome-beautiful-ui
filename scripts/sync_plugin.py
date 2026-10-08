#!/usr/bin/env python3
"""Generate client packaging from the canonical Agent Plugins manifest.

Usage: python3 scripts/sync_plugin.py [--check]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report stale files without writing")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    metadata = {key: manifest[key] for key in (
        "name", "version", "description", "author", "homepage", "repository", "license", "keywords"
    ) if key in manifest}
    name = manifest["name"]
    marketplace_name = name + "-local"
    files = {
        ".claude-plugin/plugin.json": metadata,
        ".claude-plugin/marketplace.json": {
            "name": marketplace_name,
            "description": manifest["description"],
            "owner": {"name": manifest["author"]["name"]},
            "plugins": [{"name": name, "source": "./", "description": manifest["description"]}],
        },
        ".agents/plugins/marketplace.json": {
            "name": marketplace_name,
            "interface": {"displayName": "Awesome Beautiful UI"},
            "plugins": [{
                "name": name,
                "source": {"source": "local", "path": "./"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": "Productivity",
            }],
        },
    }
    stale = []
    for relative, data in files.items():
        path = ROOT / relative
        expected = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        if path.is_file() and path.read_text(encoding="utf-8") == expected:
            continue
        stale.append(relative)
        if not args.check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected, encoding="utf-8")
        print(("stale: " if args.check else "wrote: ") + relative)
    if args.check and stale:
        sys.exit("Run python3 scripts/sync_plugin.py to refresh client packaging.")
    if not stale:
        print("Client packaging is up to date.")


if __name__ == "__main__":
    main()
