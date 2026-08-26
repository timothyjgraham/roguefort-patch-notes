# Roguefort patch notes site

A static site built from Markdown. No framework, no build dependencies, no
package.json — one Python script turns `notes/*.md` into HTML in `docs/`, and
GitHub Pages serves `docs/` directly.

```
notes/0.19.0.md      the patch notes, in Markdown
build.py             the generator
docs/index.html      newest version (what visitors land on)
docs/0.19.0.html     the permanent link for this version
```

## Publish it

1. Create a repo (for example `roguefort-patch-notes`) and push this folder.
2. In the repo, open **Settings → Pages**.
3. Under **Build and deployment**, set Source to **Deploy from a branch**,
   branch **main**, folder **/docs**. Save.
4. Wait about a minute. The site appears at
   `https://<your-account>.github.io/roguefort-patch-notes/`.

A custom domain (`patchnotes.roguefort.com`) is set in the same Pages settings:
add the domain there, then add a CNAME record at your DNS provider pointing to
`<your-account>.github.io`.

## Add the next version

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

Older versions keep working — `docs/0.19.0.html` stays put, and every page shows
a switcher for all versions found in `notes/`.

## What the page does

- **Filter** — press `/` or click the field to narrow the whole document as you
  type. Section counts update live, empty sections drop out, `Esc` clears.
- **Section index** — the sidebar shows how many changes landed in each area and
  tracks where you are as you scroll.
- **Credits** — a trailing `(handle)` on any bullet renders as a credit chip, so
  the community reporters stay attached to their fixes.
- **Known issues** — sections whose name contains "known issues" are styled as
  caveats rather than changes, so nobody mistakes them for fixes.

## Notes on the content

This copy of `0.19.0.md` is the public-safe version: exploit reproduction steps,
networking internals and the list of renamed third-party names have been taken
out. Keep the internal draft somewhere else, and treat `notes/` as published
material.
