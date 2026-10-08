# Contributing

## What gets in

- **It is open source and on GitHub.** The list is refreshed from the GitHub API.
- **It has something of its own.** Say in one line what that is: a specific effect, an idea, or a level of polish that sets it apart. "A collection of components" is not enough.
- **It runs on the user's own machine.** No required hosted service to render the UI.

You do not need to check activity yourself. The build script sorts entries into the main list or Quiet classics by last push date.

## How to add an entry

1. Add an object to [`list.json`](./list.json):

   ```json
   { "section": "gems", "repo": "owner/name", "name": "Display Name", "note": "One line that ends with a period." }
   ```

   `section` is one of `gems`, `motion`, `components`, `webgl`, `terminal`, `widgets`. Use `gems` for lesser-known projects with one clearly distinctive effect or idea.

2. If GitHub cannot identify the license (the entry shows `license: see repo`), read the license file and add a `"license"` field with what it says.

3. Regenerate the README and commit both files:

   ```sh
   python3 scripts/build.py
   ```

Do not edit the generated part of `README.md` by hand. It is overwritten on the next run.
