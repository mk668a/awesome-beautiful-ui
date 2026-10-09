---
name: judge-candidates
description: Use after research-candidates, or when asked which researched repositories get into the Awesome Beautiful UI list, why one was rejected, or to change the inclusion rules. Runs a script that applies rules.json to the finding files and writes research/verdicts.json. The verdict comes from the script, never from the agent. Third step of find, research, judge.
license: MIT
compatibility: Run from a checkout of awesome-beautiful-ui. Needs Python 3.9+. No network access.
---

# judge-candidates

Step 3 of 3.

```sh
python3 skills/judge-candidates/scripts/judge.py
```

It reads every file in `research/findings/`, applies [`rules.json`](./rules.json), prints one line per repository (verdict, repository, ids of the rules that failed) and writes `research/verdicts.json`. This output is ignored by Git and must be regenerated before use. Use `--as-of YYYY-MM-DD` to fix the evaluation date; it is recorded as `asOf` in the output.

Do not decide, adjust or overrule a verdict yourself. If a verdict looks wrong, either the finding is wrong (fix it through `research-candidates`) or a rule is wrong (propose a change to `rules.json`). Then run the script again.

## Verdicts

| Verdict | Meaning | Next |
|---|---|---|
| `include` | Passed every rule | Goes in the main list |
| `quiet` | Passed, but archived or no recent push | Goes in the list. The build places it under Quiet classics |
| `needs-research` | A finding is unfinished or missing a field | Back to `research-candidates` for that repository |
| `reject` | Failed a rule that research cannot fix | Stays out. The finding file records why |

When several rules fail, the most severe verdict wins, in the order of the `verdicts` array in `rules.json`.

## The rules are defined in rules.json

Each rule is one line: a `field` of the finding, an `op`, a `value`, the verdict `onFail`, and a `reason`. Rules with `"stage": "research"` are skipped until the finding's research is marked done, so an unresearched repository gets `needs-research` and not a false `reject`.

Before evaluating a rule, missing or malformed values produce `needs-research` for that rule rather than its rejection verdict. Confirmed disqualifiers still take precedence. Evidence must contain nonempty strings and valid HTTP(S) URLs. Unresolved licenses and nonempty `unverified` arrays prevent inclusion.

Available ops: `eq`, `in`, `notIn` (case-insensitive), `gte`, `minLength`, `nonEmpty`, `matches` (full regular-expression match), `knownLicense`, `httpUrls`, `date`, and `withinMonths` (a date no older than N months).

The `on-topic` rule lists repositories the maintainer keeps out although they pass every other rule. Add a repository there to exclude it; `--apply` does not remove an entry already in `list.json`.

The `active` rule is also read by `scripts/build.py`, so the three-month window is defined in one place.

## Adding the result to the list

Only when asked:

```sh
python3 skills/judge-candidates/scripts/judge.py --apply
python3 scripts/build.py
```

`--apply` appends the `include` and `quiet` entries that are not yet in `list.json`.
