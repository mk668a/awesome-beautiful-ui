---
name: audit-list
description: Use when asked to check the health of the Awesome Beautiful UI list, before a release or refresh, or when the build script prints a "moved" warning. Finds entries whose repository moved, was archived or deleted, entries whose license is still unresolved, and sites that are unreachable or whose last confirmed update is stale, then proposes the list.json fixes.
license: MIT
compatibility: Run from a checkout of awesome-beautiful-ui. Needs Python 3.9+ and a GitHub token (GITHUB_TOKEN, or a logged-in gh CLI).
---

# audit-list

```sh
python3 skills/audit-list/scripts/audit.py --list list.json
```

The script checks every entry and prints one line per problem. It exits with the number of problems, so zero means clean.

| Finding | What to do |
|---|---|
| `moved` | Change `repo` in `list.json` to the new name |
| `archived` | Nothing required. The build places it under Quiet classics. Mention it |
| `missing` | The repository is gone or private. Propose removing the entry |
| `license-unresolved` | Run the `research-candidates` skill on it to read the license, then add a `license` field |
| `duplicate` | Two entries point at the same repository or site. Keep one |
| `unreachable` | A site returned an HTTP error or did not answer. Open it by hand: bot protection can return 403 to a live site. Propose removal only if it is gone |
| `stale` | A site's confirmed update is older than the `site-active` rule allows. Re-research it with `research-candidates`, then update `updated` in `list.json` |

Report the findings and the exact edits you propose. Apply them only if asked, then regenerate with `python3 scripts/build.py`.
