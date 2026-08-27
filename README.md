# Roguefort patch notes

Source for the Roguefort patch notes site, published at
**<https://timothyjgraham.github.io/roguefort-patch-notes/>**

Each release is a Markdown file in `notes/`; a small Python script turns them
into the published pages in `docs/`, which GitHub Pages serves.

```
notes/0.19.0.md      the patch notes, in Markdown
build.py             the generator — template, CSS and JS all live in here
assets/              the wordmark, copied into docs/ on every build
docs/index.html      newest version (what visitors land on)
docs/0.19.0.html     the permanent link for this version
```

## Adding a release

1. Write `notes/0.20.0.md`, following the same shape as `0.19.0.md`:
   `# Title`, then `## Section` headings, then `- ` bullets.
2. Optionally set the date, the update name and the build label at the top:

   ```
   <!-- date: 14 September 2026 -->
   <!-- lede: Hamsters! -->
   <!-- tag: Playtest -->
   ```

   `lede` is the update's name, and it is set as the title card — the largest
   element on the page. Give it a name, not a sentence.

3. Run `python3 build.py`.
4. Commit and push. Pages redeploys on its own.

Older releases keep working — `docs/0.19.0.html` stays put, and every page shows
a switcher for all versions found in `notes/`.

Don't hand-edit anything in `docs/`. It is generated, and the next build
overwrites it.

## What the page does

- **Filter** — press `/` or click the field to narrow the whole document as you
  type. Section counts update live, empty sections drop out, `Esc` clears.
- **Contents** — the plate under the masthead shows how many changes landed in
  each area, and highlights where you are as you scroll.
- **Credits** — a trailing `(handle)` on any bullet renders as a credit chip, so
  reporters stay attached to the changes they found.
- **Known issues** — sections whose name contains "known issues" render on a
  dark substrate instead of the paper, so they can't be mistaken for fixes.

## Editing the design

The palette and motifs are taken from the game's Steam capsule art: a strict
PICO-8 index, dot-lattice dithering in place of gradients, hard outlines with a
warm rim-light, and no border radius anywhere.

It is all one template string in `build.py`. Placeholders are `{{name}}`, not
`{name}`, so braces in the CSS and JS don't need doubling.

## Pages settings

Served from the `main` branch, `/docs` folder (Settings → Pages). The generated
files are committed, so there's no build workflow to maintain.
