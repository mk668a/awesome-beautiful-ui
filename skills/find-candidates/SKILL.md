---
name: find-candidates
description: Use when asked to find new projects for the Awesome Beautiful UI list, to look for what is missing in a section, or to scan GitHub for recently active beautiful UI, motion, WebGL or terminal projects. Runs the searches defined in queries.json and writes the repositories not yet listed to research/candidates.json. First step of find, research, judge.
license: MIT
compatibility: Run from a checkout of awesome-beautiful-ui. Needs Python 3.9+ and a GitHub token (GITHUB_TOKEN, or a logged-in gh CLI).
---

# find-candidates

Step 1 of 3. It only gathers. Research is done by `research-candidates` and the decision is made by `judge-candidates`.

```sh
python3 skills/find-candidates/scripts/search.py
```

This writes `research/candidates.json` and prints one line per candidate. Repositories already in `list.json` or any finding file are excluded, including pending and rejected findings and recorded rename aliases. Revisit those through `research-candidates` directly.

## The search is defined in queries.json

[`queries.json`](./queries.json) holds everything the script does. Change the search by editing that file, not the script.

| Key | Meaning |
|---|---|
| `filters` | Applied to every query: last push within N months, minimum stars, archived, fork |
| `order` | GitHub star ordering: `asc` (default) or `desc` |
| `perQuery` | Results taken from each query, lowest stars first by default |
| `exclude` | Repositories dropped before they are written: a name pattern and a list of topics |
| `queries` | One GitHub search each, with an `id` and the list section it feeds |

Flags for one-off runs, without editing the file:

| Flag | Effect |
|---|---|
| `--findings <path>` | Directory of already-seen findings to exclude |
| `--order asc` / `--order desc` | Override star ordering for retrieval and output |
| `--only <id>` | Run just that query. Repeatable |
| `--min-stars N` | Override `filters.minStars`, for example 50 when hunting for hidden gems |
| `--new-within-days N` | Only repositories created in the last N days |
| `--out <path>` | Write somewhere other than `research/candidates.json` |

## Next

Hand the result to `research-candidates`. Do not pick winners here: star count alone does not establish eligibility.
