# Roguefort patch notes

Source for the Roguefort patch notes site. Each release is a Markdown file in
`notes/`; a small Python script turns them into the published pages in `docs/`,
which GitHub Pages serves.

```
notes/0.19.0.md      the patch notes, in Markdown
build.py             the generator
docs/index.html      newest version (what visitors land on)
docs/0.19.0.html     the permanent link for this version
```

## Adding a release

1. Write `notes/0.20.0.md`, following the same shape as `0.19.0.md`:
   `# Title`, then `## Section` headings, then `- ` bullets.
2. Optionally set the header line, the pull quote and the build label at the top:

   ```
   <!-- date: 14 September 2026 -->
   <!-- lede: The one where roads stopped lying to you. -->
   <!-- tag: Playtest -->
   ```

3. Run `python3 build.py`.
4. Commit and push. Pages redeploys on its own.

Older releases keep working — `docs/0.19.0.html` stays put, and every page shows
a switcher for all versions found in `notes/`.

## What the page does

- **Filter** — press `/` or click the field to narrow the whole document as you
  type. Section counts update live, empty sections drop out, `Esc` clears.
- **Section index** — the sidebar shows how many changes landed in each area and
  tracks where you are as you scroll.
- **Credits** — a trailing `(handle)` on any bullet renders as a credit chip, so
  reporters stay attached to the changes they found.
- **Known issues** — sections whose name contains "known issues" are styled as
  caveats rather than changes, so they aren't mistaken for fixes.

## Pages settings

Served from the `main` branch, `/docs` folder (Settings → Pages). The optional
workflow in `.github/workflows/pages.yml` rebuilds from Markdown on push instead,
if you'd rather not commit generated files.
