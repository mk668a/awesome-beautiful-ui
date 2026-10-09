# Working on Awesome Beautiful UI

This repository curates distinctive UI projects and provides a research harness. Run commands from a writable checkout with Python 3.9+; the scripts use only the standard library.

## Files and responsibilities

- `list.json` is the curated source. Generate the README list with `python3 scripts/build.py`; do not edit between its list markers.
- `skills/find-candidates/queries.json` controls discovery. Existing entries and repositories in `research/findings/` are excluded; searches default to ascending stars.
- `research/findings/*.json` stores script-owned `facts` and researcher-owned `research`. Follow `skills/research-candidates/references/researcher-brief.md` when researching.
- `skills/judge-candidates/rules.json` controls inclusion. `judge.py` validates observations before applying these rules. Correct the inputs or rules and rerun; do not hand-edit verdicts.
- `research/verdicts.json` is an ignored output. Regenerate it before use; `--as-of YYYY-MM-DD` fixes the evaluation date for reproducible verdicts.

## Workflow

Read the relevant `skills/<name>/SKILL.md` before running a workflow. Discover candidates, collect facts, research each candidate, then judge. When delegating research, assign one finding file per worker and preserve others' changes. Use `--reset-research` for an explicit re-research request; ordinary fact refreshes retain research.

Apply entries only when the requested task includes adding them to the list. `judge.py --apply` appends eligible entries; existing entries must be edited separately. Rebuild the README after list changes. Use `audit-list` to investigate moved, missing, duplicated, archived, or license-unresolved entries. A build skips 404s with warnings and keeps them in `list.json` for follow-up.

Check `git status` before editing and preserve existing work. Never print or commit credentials. Network commands read `GITHUB_TOKEN`, `GH_TOKEN`, or a logged-in `gh` CLI; imports and `--help` require no authentication.

## Plugin packaging

The root `plugin.json` is the canonical [Agent Plugins 1.0](https://agent-plugins.org/specification) manifest, used by Codex. Claude Code uses the generated `.claude-plugin/plugin.json` compatibility manifest. Both share `skills/`; do not duplicate implementations. The two marketplace catalogs are client-specific distribution files.

After changing metadata, run `python3 scripts/sync_plugin.py`. Keep the installation instructions in `MAINTAINING.md` and the skill descriptions aligned with the implementation. The README is for readers of the list; maintainer documentation goes in `MAINTAINING.md`.

## Verification

Run `python3 -m unittest`.
