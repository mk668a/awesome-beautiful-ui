---
name: research-candidates
description: Use after find-candidates, or when asked to research one or more GitHub repositories for the Awesome Beautiful UI list, to re-research an entry, or to resolve a license shown as "see repo". Creates one finding file per repository under research/findings and has a subagent fill in what a script cannot check. Second step of find, research, judge.
license: MIT
compatibility: Run from a checkout of awesome-beautiful-ui. Needs Python 3.9+ and a GitHub token (GITHUB_TOKEN, or a logged-in gh CLI). Uses subagents when the client has them.
---

# research-candidates

Step 2 of 3. Every repository gets one JSON file in `research/findings/`. The file has two blocks:

- `facts`: stars, last push, archived, license as GitHub sees it. Written by the script.
- `research`: what kind of thing it is, what is distinctive about it, where that was seen. Written by a researcher.

Nothing is decided here. `judge-candidates` reads these files and applies the rules.

## 1. Create the finding files

```sh
# everything from the last search (or the first N)
python3 skills/research-candidates/scripts/collect_facts.py --candidates research/candidates.json --limit 20

# or specific repositories
python3 skills/research-candidates/scripts/collect_facts.py owner/name other/name
```

Candidates are sorted by ascending stars before `--limit` is applied, so older star-descending search files also prioritize hidden gems. Use `--order stars-desc` or `--order input` to override. Explicit repository arguments come first; duplicates are removed before the limit.

Re-running refreshes `facts` and keeps an existing `research` block. For an explicit re-research request, pass `--reset-research` to reset the selected findings to pending. A single-repository run prints the facts and README excerpt; a batch prints file paths and status.

## 2. Research each pending file with a subagent

For every file whose status is `pending`, start one subagent and give it [references/researcher-brief.md](references/researcher-brief.md) with `{repo}` and `{file}` filled in. Start them together so they run in parallel. One repository per subagent: each needs its own context to read a README and open a demo, and a failure then costs one file, not the batch.

If the client has no subagents, follow the brief yourself, one repository at a time.

## 3. Hand over

When the subagents have replied, run `judge-candidates`. Unfinished or invalid observations produce `needs-research`; confirmed disqualifiers can still produce `reject`. For a `needs-research` result, revisit the failed fields even when the finding is marked `done`. Resolve the observations honestly, then rerun the judge.
