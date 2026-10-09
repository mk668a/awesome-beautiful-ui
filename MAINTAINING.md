# Maintaining Awesome Beautiful UI

For people who maintain the list or run its research harness. To suggest an entry, [CONTRIBUTING.md](./CONTRIBUTING.md) is enough.

## Building the list

Everything between the list markers in [`README.md`](./README.md) is generated. The curated part lives in [`list.json`](./list.json): the repository, a display name, a section and a one-line note.

```sh
python3 scripts/build.py
```

The script needs Python 3.9 or newer, no packages to install, and a GitHub token: it reads `GITHUB_TOKEN`, or asks the `gh` CLI if you are logged in. For each entry it fetches the current stars, license and last push, sorts each section by stars, and moves anything archived or without a push in three months to Quiet classics. If development resumes, the next run moves it back. Repositories returning 404 are skipped with a warning and remain in `list.json` for audit; other API errors stop the build.

Screenshots are captured separately with `python3 scripts/screenshots.py`; the build adds the ones that exist under `assets/screenshots/`. The site is built from the README by `python3 scripts/pages.py` and deployed by the Pages workflow.

## Agent skills

This repository is also an [Agent Plugins 1.0](https://agent-plugins.org) plugin: a `plugin.json` at the root and four skills under [`skills/`](./skills). An AI coding agent that supports the format can use them to do the research behind the list.

| Step | Skill | What it does | Defined in | Result |
|---|---|---|---|---|
| 1 | `find-candidates` | Searches GitHub for active projects not yet listed | [`queries.json`](./skills/find-candidates/queries.json) | `research/candidates.json` |
| 2 | `research-candidates` | One subagent per repository records what it is and what is distinctive | [`researcher-brief.md`](./skills/research-candidates/references/researcher-brief.md) | `research/findings/*.json` |
| 3 | `judge-candidates` | A script applies the inclusion rules to the findings | [`rules.json`](./skills/judge-candidates/rules.json) | `research/verdicts.json` |
|  | `audit-list` | Finds entries that moved, were archived or deleted, or have an unresolved license |  | printed |

The agent researches, but it does not decide. Whether a repository gets in is computed from its finding file by `judge.py`, which has no network access and no judgement of its own, so the same findings, rules and evaluation date give the same verdict:

```sh
python3 skills/judge-candidates/scripts/judge.py
```

`research/verdicts.json` is generated and ignored by Git. Use `--as-of YYYY-MM-DD` to reproduce verdicts for a fixed date. Missing or malformed observations, unresolved licenses, and recorded unverified claims require more research before inclusion. Discovery excludes all existing findings and defaults to low-star candidates first.

## Install the agent plugin

### Use with Codex or Claude Code

Both clients use the same four skills. Codex reads the root Agent Plugins 1.0 manifest; Claude Code uses the compatibility manifest in `.claude-plugin/plugin.json`. See the [Agent Plugins client list](https://agent-plugins.org/compatible-clients), [Codex packaging guide](https://developers.openai.com/plugins/build/plugins), and [Claude Code manifest reference](https://code.claude.com/docs/en/plugins-reference).

Run these workflows from a writable checkout of this repository, with Python 3.9+ and GitHub authentication available. The skills operate on the checkout's `list.json` and `research/`; an installed plugin cache is not the working checkout.

For Codex, run from this repository:

```sh
codex plugin marketplace add .
codex plugin add awesome-beautiful-ui@awesome-beautiful-ui-local
```

Start a new Codex session in this checkout and ask it to use `find-candidates`, `research-candidates`, `judge-candidates`, or `audit-list` from Awesome Beautiful UI.

For Claude Code, load the checkout for one session:

```sh
claude --plugin-dir .
```

Then invoke, for example, `/awesome-beautiful-ui:find-candidates`. To install persistently instead:

```sh
claude plugin marketplace add .
claude plugin install awesome-beautiful-ui@awesome-beautiful-ui-local
```

Restart the client after installation. Installing the plugin does not itself run a search or change the list.

### Verify the harness

```sh
python3 -m unittest
```

The standard-library suite uses `tests/fixtures/findings/`, temporary output files, and mocked GitHub responses. No token or network access is required.

### Maintain plugin packaging

`plugin.json` is the source of truth for plugin metadata. The compatibility manifest and the two client marketplace catalogs are generated:

```sh
python3 scripts/sync_plugin.py
python3 scripts/sync_plugin.py --check
claude plugin validate .claude-plugin/plugin.json --strict
claude plugin validate .claude-plugin/marketplace.json --strict
```

The marketplace catalogs are client-specific distribution files, outside the portable Agent Plugins core. Do not copy the skill implementations into client-specific directories.
