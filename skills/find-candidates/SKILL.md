---
name: find-candidates
description: Use when asked to find new projects for the Awesome Beautiful UI list, to look for what is missing in a section, or to scan GitHub and the web for recently active beautiful UI, motion, WebGL or terminal projects, including products that are not open source. Runs the searches defined in queries.json and writes the repositories not yet listed to research/candidates.json and the product sites to research/site-candidates.json. First step of find, research, judge.
license: MIT
compatibility: Run from a checkout of awesome-beautiful-ui. Needs Python 3.9+ and a GitHub token (GITHUB_TOKEN, or a logged-in gh CLI).
---

# find-candidates

Step 1 of 3. It only gathers. Research is done by `research-candidates` and the decision is made by `judge-candidates`.

```sh
python3 skills/find-candidates/scripts/search.py
```

This writes `research/candidates.json` and prints one line per candidate. Repositories already in `list.json` or any finding file are excluded, including pending and rejected findings and recorded rename aliases. Revisit those through `research-candidates` directly.

## Sites outside GitHub

Free and freemium products whose source is not public are found with the same axes. Each query in `queries.json` may carry `web` phrases, and some queries have only those. A script cannot search the web, so you search and `sites.py` keeps the records:

```sh
python3 skills/find-candidates/scripts/sites.py start          # prints QUERY_ID<TAB>PHRASE
python3 skills/find-candidates/scripts/sites.py add --query framer-components https://example.com
python3 skills/find-candidates/scripts/sites.py check          # canary coverage
```

Run every phrase through web search, all in parallel. Record the product's own site, not the page that mentioned it: when a result is a directory entry, a comparison or an alternatives article, open it and add the products it names. Sites with a public source repository can be added too; research rejects them in favor of the repository. Add known sites as well, so coverage stays measurable.

`check` exits nonzero when a site in `webCanaries` was not surfaced. That means the phrases miss how such products describe themselves, so change the phrases and run again, before researching anything. Products outside GitHub tend to describe themselves by where they are used (Framer, Webflow, MCP, copy code) and by the libraries they compete with, not by GitHub topics.

## The search is defined in queries.json

[`queries.json`](./queries.json) holds everything the script does. Change the search by editing that file, not the script.

| Key | Meaning |
|---|---|
| `filters` | Applied to every query: last push within N months, minimum stars, archived, fork |
| `order` | GitHub star ordering: `asc` (default) or `desc` |
| `perQuery` | Results taken from each query, lowest stars first by default |
| `exclude` | Repositories dropped before they are written: a name pattern and a list of topics |
| `queries` | One axis each, with an `id`, the list section it feeds, a GitHub search `q` and web search phrases `web`. Either may be missing |
| `webCanaries` | Sites outside GitHub that a web run must surface. A miss means the `web` phrases need work |

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

Hand both results to `research-candidates`. Do not pick winners here: star count alone does not establish eligibility.
