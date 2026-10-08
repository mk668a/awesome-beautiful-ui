---
name: audit-list
description: Use when asked to check the health of the Awesome Beautiful UI list, before a release or refresh, or when the build script prints a "moved" warning. Finds entries whose repository moved, was archived or deleted, and entries whose license is still unresolved, then proposes the list.json fixes.
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
| `duplicate` | Two entries point at the same repository. Keep one |

Report the findings and the exact edits you propose. Apply them only if asked, then regenerate with `python3 scripts/build.py`.
