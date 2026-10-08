# Researcher brief

Give this to the subagent that researches one repository. Replace `{repo}` and `{file}`.

---

Research the GitHub repository `{repo}` for the Awesome Beautiful UI list and record what you find in `{file}`. You are recording observations. You are not deciding whether it gets in: a script does that from the file.

Start with:

```sh
python3 skills/research-candidates/scripts/collect_facts.py {repo}
```

It refreshes the `facts` block in the file and prints the start of the README. Then look at the project itself: open its homepage, demo or docs, and for terminal tools the screenshots or recordings in the README.

Edit only the `research` block of `{file}`. Leave `facts` alone.

| Field | What to write |
|---|---|
| `status` | `"done"` when every field below is filled |
| `researchedAt` | Today's date, `YYYY-MM-DD` |
| `kind` | `library`, `component-collection`, `tool` (something you run, including terminal apps), `app` (an end-user product that merely has a nice UI), `list`, `template`, `course` or `other` |
| `section` | `gems`, `motion`, `components`, `webgl`, `terminal` or `widgets`. `gems` is for lesser-known projects whose appeal is one clearly distinctive thing |
| `name` | Display name as the project writes it |
| `note` | One sentence, 10 to 160 characters, ending with a period, saying what it is or what is distinctive. Plain words, no superlatives from the project's tagline, no em dash |
| `license` | What the license actually is. If `facts.license.spdx` is a real identifier, repeat it. If it is `NOASSERTION` or `null`, read `facts.license.head` or find the license in the repository and describe it, for example `MIT + Commons Clause`. Write `unknown` if you cannot tell |
| `requiresHostedService` | `true` if it cannot render or run without the project's own hosted service or a paid API |
| `genericCollection` | `true` if it is a collection of ordinary components with nothing you would recognize as its own |
| `demoViewed` | `true` only if you saw it running, or saw screenshots or recordings of it, in this session |
| `signature.effects` | The specific effects or ideas that are its own, each named concretely (`"liquid metal shader"`, `"structural diff by syntax tree"`). Empty if there are none |
| `signature.evidenceUrls` | The URLs where you saw those effects |
| `unverified` | Anything above that you inferred instead of observing, in plain sentences |

The judge blocks inclusion while `unverified` contains observations. Resolve them with evidence; do not delete them just to pass a rule.

Only record what a tool result in this session supports. If you could not open the demo, set `demoViewed` to `false` and say so in `unverified`. Do not edit any other file.

Reply with one line: the repository, the `kind`, and the first signature effect or "no signature".
