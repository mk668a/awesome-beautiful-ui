# Site researcher brief

Give this to the subagent that researches one product site, a library or collection whose source is not on GitHub. Replace `{url}` and `{file}`.

---

Research the product site `{url}` for the Awesome Beautiful UI list and record what you find in `{file}`. You are recording observations. You are not deciding whether it gets in: a script does that from the file.

Start with:

```sh
python3 skills/research-candidates/scripts/collect_facts.py {url}
```

It refreshes the `facts` block in the file and prints the page description. Then look at the product itself: open its gallery or demos, its pricing page and its changelog or newest entries.

Edit only the `research` block of `{file}`. Leave `facts` alone.

| Field | What to write |
|---|---|
| `status` | `"done"` when every field below is filled |
| `researchedAt` | Today's date, `YYYY-MM-DD` |
| `kind` | `library`, `component-collection`, `tool`, `app` (an end-user product that merely has a nice UI, including site builders), `list` (a directory of other people's work), `template`, `course` or `other` |
| `name` | Display name as the product writes it |
| `note` | One sentence, 10 to 160 characters, ending with a period, saying what it is or what is distinctive. Plain words, no superlatives from the tagline, no em dash |
| `openSource` | `true` if the source of the effects that set it apart is in a public repository. Then research that repository instead and say which one in `unverified` until you have. A public wrapper such as an MCP plugin, or a repository holding only the ordinary free part, does not count |
| `pricing` | `free` (everything usable at no cost, an account or free API key allowed), `freemium` (a useful free part and paid extras) or `paid` |
| `lastUpdated` | The newest date, `YYYY-MM-DD`, on which you saw the product change: a changelog entry, a dated new component, a release post |
| `lastUpdatedEvidence` | The URLs where that date is shown |
| `genericCollection` | `true` if it is a collection of ordinary components with nothing you would recognize as its own |
| `demoViewed` | `true` only if you saw it running, or saw screenshots or recordings of it, in this session |
| `signature.effects` | The specific effects or ideas that are its own, each named concretely. Empty if there are none |
| `signature.evidenceUrls` | The URLs where you saw those effects |
| `unverified` | Anything above that you inferred instead of observing, in plain sentences |

The judge blocks inclusion while `unverified` contains observations. Resolve them with evidence; do not delete them just to pass a rule. A page that only says "new" without a date is not a date: write the nearest dated evidence you found, or leave `lastUpdated` empty and explain in `unverified`.

Look at pages headlessly, for example with Chrome's `--headless=new --screenshot`, and read the image. Never open a visible browser window: it takes over the user's screen.

Only record what a tool result in this session supports. If you could not open the demo, set `demoViewed` to `false` and say so in `unverified`. Do not edit any other file.

Reply with one line: the site, the `kind`, the `pricing` and the first signature effect or "no signature".
