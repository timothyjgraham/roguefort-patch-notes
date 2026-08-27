#!/usr/bin/env python3
"""Build the Roguefort patch notes site.

Reads every notes/<version>.md and writes docs/<version>.html, plus
docs/index.html for the newest version. Run it after editing the notes:

    python3 build.py

Each notes file may start with optional front matter comments:

    <!-- date: 27 August 2026 -->
    <!-- lede: Hamsters! -->
    <!-- tag: Playtest -->

The design is driven by the Steam capsule art: a strict PICO-8 palette,
dot-lattice dithering instead of gradients, hard 1px outlines with a warm
rim-light, and zero border radius anywhere.
"""

import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
NOTES = ROOT / "notes"
DOCS = ROOT / "docs"
ASSETS = ROOT / "assets"

# Sections that describe what is still broken rather than what changed.
CAVEAT_SECTIONS = ("known issues",)


def version_key(name: str):
    return [int(p) if p.isdigit() else p for p in re.split(r"[.\-]", name)]


def parse(path: Path):
    text = path.read_text(encoding="utf-8")
    meta = dict(re.findall(r"<!--\s*(\w+):\s*(.*?)\s*-->", text))
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)

    title, sections = "", []
    for line in text.splitlines():
        line = line.rstrip()
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            sections.append({"name": line[3:].strip(), "bullets": []})
        elif line.startswith("- ") and sections:
            sections[-1]["bullets"].append(line[2:].strip())
    return {
        "version": path.stem,
        "title": title,
        "sections": sections,
        "date": meta.get("date", ""),
        "lede": meta.get("lede", ""),
        "tag": meta.get("tag", ""),
    }


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def split_credit(bullet: str):
    """Peel a trailing (handle, handle) credit off a bullet."""
    m = re.search(r"\s*\(([^()]{1,90})\)\s*$", bullet)
    if not m:
        return bullet, []
    inner = m.group(1)
    if inner.endswith((".", "!", "?")) or inner[0].islower() and " " in inner and "," not in inner:
        # Looks like prose in brackets rather than a credit line.
        return bullet, []
    body = bullet[: m.start()].rstrip()
    if not body.endswith((".", "!", "?", '"')):
        return bullet, []
    parts = [p.strip() for p in inner.split(",")]
    return body, parts


def render_bullet(bullet: str) -> str:
    body, credits = split_credit(bullet)
    out = html.escape(body)
    # In-game bracket labels such as [Sheltered] get the game's own chip look.
    out = re.sub(r"\[([A-Za-z][\w \-]{0,18})\]", r'<span class="tag">[\1]</span>', out)
    credit_html = ""
    if credits:
        bits = []
        for c in credits:
            cls = "who" if " " not in c else "who-note"
            bits.append(f'<span class="{cls}">{html.escape(c)}</span>')
        credit_html = f'<span class="credits">{"".join(bits)}</span>'
    return f'<li class="change">{out}{credit_html}</li>'


def fill(tpl: str, mapping: dict) -> str:
    """Single-pass {{key}} substitution.

    Deliberately not str.format: the template is mostly CSS and JS, and
    doubling every brace in it is a standing invitation to typos.
    """
    return re.sub(r"\{\{(\w+)\}\}", lambda m: str(mapping[m.group(1)]), tpl)


MAX_CHIPS = 4


def build_switcher(current, all_versions):
    """Newest few versions as chips, plus a link to the full register.

    A chip per release overflows the bar once there are a dozen or so;
    the register page is the thing that scales.
    """
    shown = all_versions[:MAX_CHIPS]
    if current not in shown:
        shown = all_versions[: MAX_CHIPS - 1] + [current]
    chips = "".join(
        '<a class="ver{on}" href="{v}.html"{cur}>{v}</a>'.format(
            v=html.escape(v),
            on=" on" if v == current else "",
            cur=' aria-current="page"' if v == current else "",
        )
        for v in shown
    )
    more = f" ({len(all_versions)})" if len(all_versions) > len(shown) else ""
    return chips + f'<a class="ver ver-all" href="index.html">All{more}</a>'


def build_pager(older, newer):
    def cell(note, kind, label):
        if not note:
            return ""
        name = note["lede"] or note["version"]
        return (
            f'<a class="pg pg-{kind}" href="{html.escape(note["version"])}.html">'
            f'<span class="pg-k">{label}</span>'
            f'<span class="pg-v">{html.escape(name)}</span>'
            f'<span class="pg-n">{html.escape(note["version"])}</span></a>'
        )
    return (
        cell(older, "prev", "Previous release")
        + '<a class="pg pg-all" href="index.html">All releases</a>'
        + cell(newer, "next", "Next release")
    )


def render(note, all_versions, older=None, newer=None):
    sections = note["sections"]
    total = sum(len(s["bullets"]) for s in sections)

    index_rows = []
    body_rows = []
    for s in sections:
        sid = slug(s["name"])
        n = len(s["bullets"])
        caveat = any(k in s["name"].lower() for k in CAVEAT_SECTIONS)
        index_rows.append(
            f'<li><a class="idx{" idx-caveat" if caveat else ""}" href="#{sid}" data-idx="{sid}">'
            f'<span class="idx-name">{html.escape(s["name"])}</span>'
            f'<span class="idx-dots" aria-hidden="true"></span>'
            f'<span class="idx-n" data-count="{sid}">{n}</span></a></li>'
        )
        bullets = "\n".join(render_bullet(b) for b in s["bullets"])
        body_rows.append(
            f'<section class="sec{" caveat" if caveat else ""}" id="{sid}" data-sec="{sid}">'
            f'<h2>{html.escape(s["name"])}'
            f'<span class="sec-n">{n}</span></h2>'
            f'<ul class="changes">{bullets}</ul>'
            f'</section>'
        )

    switcher = build_switcher(note["version"], all_versions)
    pager = build_pager(older, newer)

    return fill(TEMPLATE, {
        "version": html.escape(note["version"]),
        "title": html.escape(note["title"] or f"Roguefort {note['version']}"),
        "lede": html.escape(note["lede"]),
        "date": html.escape(note["date"]),
        "tag": html.escape(note["tag"] or "Build"),
        "total": total,
        "n_sections": len(sections),
        "index_rows": "\n".join(index_rows),
        "body_rows": "\n".join(body_rows),
        "switcher": switcher,
        "pager": pager,
        "css": CSS,
    })


CSS = """
/* ------------------------------------------------------------------
   Palette sampled from the Steam capsules. Strict PICO-8 index:
   the whole capsule is 26-47 unique colours, so nothing here is
   invented or nudged. Sky is the dominant colour of the art (22-32%
   of every capsule); yellow is under 2% and belongs to the wordmark.
   Warm colours fail contrast on cream, so they are structure only --
   markers, rules, keylines, offsets -- never letterforms on paper.
   ------------------------------------------------------------------ */
:root {
  --sky:    #29ADFF;   /* Cantal Sky   - dominant field */
  --deep:   #065AB5;   /* deep sea / upper sky band     */
  --mid:    #1D2B53;   /* bridges night to deep in the ramp */
  --night:  #111D35;   /* Deep Night   - text, substrate*/
  --cream:  #FFF1E8;   /* Curd Cream   - the paper      */
  --crust:  #49333B;   /* the cliff. unlisted in the kit*/
  --ember:  #FF6C24;   /* Ember Rock   - accent         */
  --rind:   #FFA300;   /* Rind Orange  - 1px rim-light  */
  --cellar: #742F29;   /* Cellar Brown - muted text     */
  --ink:    #271F1B;   /* Ink Black    - hard outline   */
  --yellow: #FFEC27;   /* Roguefort Yellow - wordmark   */

  --disp: "Grenze Gotisch", "Palatino Linotype", Georgia, serif;
  --body: Bitter, Georgia, "Times New Roman", serif;
  --mono: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;

  --wrap: 1040px;
  --pad: 56px;
  --barh: 54px;
}

/* Dot-lattice dither. The art ramps every colour transition with a
   1px dot on a 2px lattice, not with a blend. conic-gradient at a
   quarter turn gives exactly that, with hard axis-aligned edges. */
.dot { background-image: conic-gradient(currentColor 25%, #0000 0); background-size: 2px 2px; }

* { box-sizing: border-box; }
html { scroll-behavior: smooth; scroll-padding-top: calc(var(--barh) + 16px); }
body {
  margin: 0;
  background: var(--sky);
  color: var(--night);
  font-family: var(--body);
  font-size: 16.5px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}
/* The art has no curves anywhere. Neither does this page. */
* { border-radius: 0 !important; }

.skip {
  position: absolute; left: 8px; top: -60px; z-index: 90;
  background: var(--night); color: var(--cream); padding: 10px 14px;
  font-family: var(--mono); font-size: 13px; text-decoration: none;
  border: 2px solid var(--rind);
}
.skip:focus { top: 8px; }

/* ================= masthead ================= */
.mast {
  position: relative; overflow: hidden;
  background: var(--night);
  padding: 46px 0 0;
}
.mast-in {
  position: relative; z-index: 3;
  max-width: var(--wrap); margin: 0 auto; padding: 0 var(--pad) 52px;
}
.wordmark {
  display: block; width: 100%; max-width: 370px; height: auto;
  image-rendering: pixelated;              /* press kit: nearest-neighbour only */
}
/* Build plaque: says what the document is and which build it covers.
   Left-aligned and cellular rather than a lone big numeral -- the
   version reads loud because its cell is filled, not because it is huge. */
.plaque {
  display: inline-flex; flex-wrap: wrap; margin: 24px 0 0;
  font-family: var(--mono); font-size: 15px; line-height: 1;
  border: 2px solid var(--rind); box-shadow: 4px 4px 0 var(--deep);
}
.plaque span { padding: 11px 15px; display: block; }
.plaque-k { color: var(--cream); }
.plaque-v { background: var(--rind); color: var(--night); font-weight: 500; }
.plaque-t { color: var(--cream); border-left: 2px solid var(--rind); }

/* Visually hidden, still announced. The h1's visible text is the update
   name; screen readers get the full "Roguefort 0.19.0 patch notes" first. */
.vh {
  position: absolute; width: 1px; height: 1px; margin: -1px; padding: 0;
  overflow: hidden; clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap; border: 0;
}

/* --- the signature: the update name as an extruded pixel title card.
   Borrows the wordmark's construction -- yellow face, ink outline,
   brown extrusion falling down-right, zero blur -- at the light 500
   cut, which is condensed and sharp like the real logo rather than
   fat. A short two-step extrusion; a long one reads as cartoon 3D.
   Offsets are in em so the construction scales with the type. Used
   ONLY here; spending it on 25 section headings would waste it. --- */
.card {
  font-family: var(--disp); font-weight: 500;
  font-size: clamp(40px, 9.5vw, 104px); line-height: 1.06;
  margin: 26px 0 0; padding: 0 0 .12em;
  color: var(--yellow);
  letter-spacing: .005em;
  text-shadow:
    .02em 0 0 var(--ink), -.02em 0 0 var(--ink),
    0 .02em 0 var(--ink), 0 -.02em 0 var(--ink),
    .02em .02em 0 var(--ink), -.02em .02em 0 var(--ink),
    .02em -.02em 0 var(--ink), -.02em -.02em 0 var(--ink),
    .032em .032em 0 var(--cellar), .044em .044em 0 var(--cellar),
    .056em .056em 0 var(--ink);
}
.mast-meta {
  position: relative; margin: 30px 0 0;
  font-family: var(--mono); font-size: 13.5px; color: var(--cream);
  display: flex; flex-wrap: wrap; gap: 6px 20px; align-items: baseline;
}
.mast-meta b { color: var(--rind); font-weight: 500; }
.mast-meta kbd {
  font-family: var(--mono); font-size: 12px; color: var(--night);
  background: var(--cream); padding: 1px 6px; border: 1px solid var(--cream);
  box-shadow: 2px 2px 0 var(--deep);
}

/* Dither ramp, night -> deep -> sky. Density comes from the lattice
   itself -- a quarter dot (25%) and a checker (50%) -- rather than from
   masked rows, which read as scanlines instead of as a screen. */
.ramp { position: relative; z-index: 3; }
.ramp b {
  display: block; height: 11px;
  background-image: conic-gradient(currentColor 25%, #0000 0);
  background-size: 2px 2px;
}
.ramp b.k {
  background-image: conic-gradient(currentColor 25%, #0000 0),
                    conic-gradient(currentColor 25%, #0000 0);
  background-size: 2px 2px, 2px 2px;
  background-position: 0 0, 1px 1px;
}
.r1 { background-color: var(--night); color: var(--mid); }
.r2 { background-color: var(--night); color: var(--mid); }
.r3 { background-color: var(--mid);   color: var(--deep); }
.r4 { background-color: var(--mid);   color: var(--deep); }
.r5 { background-color: var(--deep);  color: var(--sky); }
.r6 { background-color: var(--deep);  color: var(--sky); }
.r7 { background-color: var(--sky);   color: var(--deep); }
.r8 { background-color: var(--sky);   color: var(--deep); }

/* blueprint construction marks -- only here, where the art puts them */
.marks { position: absolute; inset: 0 0 auto; height: 320px; z-index: 2; width: 100%; height: 100%; pointer-events: none; }

.ridge { display: block; width: 100%; height: 54px; background: var(--sky); }

/* ================= sticky bar ================= */
.bar {
  position: sticky; top: 0; z-index: 40;
  background: var(--night);
  border-bottom: 2px solid var(--ink);
}
.rail { height: 3px; background: var(--rind); width: 0; }
.bar-in {
  max-width: var(--wrap); margin: 0 auto;
  padding: 9px var(--pad); min-height: var(--barh);
  display: flex; align-items: center; gap: 14px;
}
.bar-mark {
  font-family: var(--disp); font-weight: 700; font-size: 21px;
  color: var(--yellow); text-decoration: none; flex: none; line-height: 1;
}
.bar-here {
  font-family: var(--mono); font-size: 12.5px; color: var(--cream);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  min-width: 0; flex: 1 1 auto;
}
.bar-here::before { content: "\\25B8"; color: var(--rind); margin-right: 8px; }
.bar-here:empty::before { content: none; }
.vers { display: flex; flex-wrap: wrap; gap: 5px; flex: 0 1 auto; min-width: 0; }
.ver {
  font-family: var(--mono); font-size: 12px; line-height: 1;
  padding: 6px 8px; text-decoration: none;
  color: var(--cream); border: 1px solid var(--deep);
}
.ver:hover { border-color: var(--rind); }
.ver.on { color: var(--night); background: var(--rind); border-color: var(--rind); }
.find { flex: none; }
.find input {
  font-family: var(--mono); font-size: 13px;
  width: 210px; padding: 7px 10px;
  color: var(--night); background: var(--cream);
  border: 1px solid var(--cream); box-shadow: 3px 3px 0 var(--deep);
}
.find input::placeholder { color: var(--cellar); opacity: 1; }
.find input:focus { box-shadow: 3px 3px 0 var(--rind); }

/* ================= the cream plate ================= */
main { max-width: var(--wrap); margin: 0 auto; padding: 0 0 64px; }
.plate {
  background: var(--cream);
  border-left: 2px solid var(--ink); border-right: 2px solid var(--ink);
  border-bottom: 2px solid var(--ink);
  box-shadow: 6px 6px 0 var(--deep);
  padding: 0 var(--pad) 60px;
}

/* ---- contents: one ruled plate, not a grid of cards ---- */
.toc { padding: 44px 0 40px; }
.toc-h {
  display: flex; align-items: baseline; justify-content: space-between;
  gap: 16px; margin: 0 0 4px;
  border-bottom: 2px solid var(--night); padding-bottom: 10px;
}
.toc-h h2 { font-family: var(--disp); font-weight: 700; font-size: 26px; margin: 0; line-height: 1; }
.toc-h span { font-family: var(--mono); font-size: 12.5px; color: var(--cellar); }
.toc ul {
  list-style: none; margin: 14px 0 0; padding: 0;
  columns: 3; column-gap: 40px;
}
.toc li { break-inside: avoid; margin: 0 0 1px; }
.idx {
  display: flex; align-items: baseline; gap: 6px;
  text-decoration: none; color: var(--night);
  font-size: 14px; line-height: 1.45; padding: 2px 4px 2px 0;
}
.idx-name { flex: 0 1 auto; }
.idx-dots {
  flex: 1 1 auto; min-width: 8px; height: 1px; align-self: center;
  color: var(--cellar); opacity: .55;
  background-image: conic-gradient(currentColor 25%, #0000 0);
  background-size: 2px 2px;
}
.idx-n { font-family: var(--mono); font-size: 12px; color: var(--cellar); flex: none; }
.idx:hover { color: var(--cellar); }
.idx:hover .idx-name { text-decoration: underline; }
.idx.on { background: var(--night); color: var(--cream); padding-left: 4px; }
.idx.on .idx-n { color: var(--rind); }
.idx.on .idx-dots { color: var(--sky); opacity: .8; }
.idx-caveat .idx-n { color: var(--cellar); }
.toc-end { border-top: 2px solid var(--night); margin-top: 16px; }

/* ---- sections ---- */
.sec { margin: 0 0 52px; scroll-margin-top: calc(var(--barh) + 16px); }
.sec h2 {
  position: relative;
  font-family: var(--disp); font-weight: 700;
  font-size: clamp(25px, 3.6vw, 34px); line-height: 1.12;
  margin: 0 0 30px; padding-bottom: 12px; max-width: 68ch;
  border-bottom: 2px solid var(--night);
  display: flex; align-items: baseline; justify-content: space-between; gap: 18px;
}
/* dither rule, in place of a plain hairline */
.sec h2::after {
  content: ""; position: absolute; left: 0; right: 0; bottom: -9px; height: 5px;
  color: var(--ember);
  background-image: conic-gradient(currentColor 25%, #0000 0);
  background-size: 2px 2px;
}
.sec-n {
  font-family: var(--mono); font-size: 13px; font-weight: 400;
  color: var(--cellar); flex: none;
}
.sec-n::before { content: "\\27E6"; }
.sec-n::after  { content: "\\27E7"; }

.changes { list-style: none; margin: 0; padding: 0; max-width: 68ch; }
.change {
  position: relative; padding: 0 0 14px 26px; margin: 0 0 14px;
  border-bottom: 1px solid rgba(73,51,59,.22);
}
.change:last-child { border-bottom: 0; }
.change::before {
  content: ""; position: absolute; left: 0; top: .52em;
  width: 7px; height: 7px; background: var(--ember);
}
.tag { font-family: var(--mono); font-size: .84em; color: var(--cellar); }

/* credit chips: cream face, hard outline, hard rim-light offset. 200+
   of these, so they stay quiet but sit at 10.4:1 on the plate. */
.credits { display: inline; }
.who {
  font-family: var(--mono); font-size: 11.5px; line-height: 1.5;
  color: var(--crust); background: var(--cream);
  border: 1px solid var(--crust); box-shadow: 2px 2px 0 var(--rind);
  padding: 0 6px; margin: 0 2px 0 8px;
  display: inline-block; vertical-align: 1px; white-space: nowrap;
}
.who-note {
  font-family: var(--mono); font-size: 11.5px; color: var(--cellar);
  margin-left: 8px;
}

/* ---- known issues: a different material, not a different colour ---- */
.sec.caveat {
  background-color: var(--night);
  background-image: conic-gradient(rgba(6,90,181,.45) 25%, #0000 0);
  background-size: 2px 2px;
  color: var(--cream);
  margin: 64px calc(var(--pad) * -1) -60px;
  padding: 38px var(--pad) 60px;
  border-top: 2px solid var(--ink);
}
.caveat h2 { color: var(--cream); border-bottom-color: var(--rind); }
.caveat h2::after { color: var(--rind); }
.caveat .sec-n { color: var(--rind); }
.caveat .change { border-bottom-color: rgba(255,241,232,.18); }
.caveat .change::before { background: none; border: 2px solid var(--rind); }
.caveat .tag { color: var(--sky); }
.caveat .who {
  color: var(--cream); background: var(--night);
  border-color: var(--rind); box-shadow: 2px 2px 0 var(--deep);
}
.caveat .who-note { color: var(--sky); }

/* ---- filter states ---- */
.hidden { display: none !important; }
.empty {
  border: 2px solid var(--night); box-shadow: 5px 5px 0 var(--ember);
  padding: 30px; margin: 30px 0 10px; font-size: 15.5px; max-width: 68ch;
}
.empty b { font-family: var(--mono); font-weight: 500; }

/* ---- index: featured release + the register ---- */
.cta { margin: 26px 0 0; }
.cta a {
  display: inline-block; font-family: var(--mono); font-size: 15px; line-height: 1;
  background: var(--cream); color: var(--night); text-decoration: none;
  padding: 14px 18px; border: 2px solid var(--cream); box-shadow: 5px 5px 0 var(--rind);
}
.cta a:hover { box-shadow: 5px 5px 0 var(--ember); }

.reg { list-style: none; margin: 14px 0 0; padding: 0; }
.reg li { border-bottom: 1px solid rgba(73,51,59,.22); }
.reg li:last-child { border-bottom: 0; }
.reg a {
  display: flex; align-items: baseline; gap: 14px;
  padding: 15px 6px; text-decoration: none; color: var(--night);
}
.reg a:hover { background: var(--night); color: var(--cream); }
.reg-name { font-family: var(--disp); font-weight: 500; font-size: 23px; line-height: 1.15; flex: 0 1 auto; }
.reg-dots {
  flex: 1 1 auto; min-width: 12px; height: 1px; align-self: center;
  color: var(--cellar); opacity: .5;
  background-image: conic-gradient(currentColor 25%, #0000 0); background-size: 2px 2px;
}
.reg-meta { font-family: var(--mono); font-size: 12.5px; color: var(--cellar); flex: none; }
.reg-meta b { color: var(--night); font-weight: 500; }
.reg-new {
  font-family: var(--mono); font-size: 11px; color: var(--night);
  background: var(--rind); padding: 2px 7px; margin-left: 10px;
}
.reg a:hover .reg-meta { color: var(--sky); }
.reg a:hover .reg-meta b { color: var(--cream); }
.reg a:hover .reg-dots { color: var(--sky); opacity: .8; }

/* ---- release page: prev / next ---- */
.pager {
  max-width: var(--wrap); margin: 0 auto; padding: 34px var(--pad) 0;
  display: flex; gap: 12px; flex-wrap: wrap; align-items: stretch;
}
.pg {
  flex: 1 1 220px; text-decoration: none; padding: 14px 16px;
  background: var(--cream); color: var(--night);
  border: 2px solid var(--ink); box-shadow: 4px 4px 0 var(--deep);
}
.pg:hover { box-shadow: 4px 4px 0 var(--rind); }
.pg-k { display: block; font-family: var(--mono); font-size: 11.5px; color: var(--cellar); margin-bottom: 5px; }
.pg-v { display: block; font-family: var(--disp); font-weight: 500; font-size: 21px; line-height: 1.1; }
.pg-n { display: block; font-family: var(--mono); font-size: 12px; color: var(--cellar); margin-top: 3px; }
.pg-next { text-align: right; }
.pg-all { flex: 0 1 auto; display: flex; align-items: center; font-family: var(--mono); font-size: 13px; }

.foot {
  max-width: var(--wrap); margin: 0 auto; padding: 26px var(--pad) 70px;
  font-family: var(--mono); font-size: 12.5px; color: var(--night);
  display: flex; flex-wrap: wrap; gap: 10px 26px; justify-content: space-between;
}
.foot a { color: var(--night); text-underline-offset: 3px; }

/* ================= responsive ================= */
@media (max-width: 900px) { .toc ul { columns: 2; } }
@media (max-width: 760px) {
  :root { --pad: 26px; }
  .toc ul { columns: 2; }
  .mast { padding-top: 30px; }
  .bar-in { flex-wrap: wrap; gap: 9px 12px; }
  .bar-here { order: 5; flex: 1 1 100%; }
  .find { flex: 1 1 100%; }
  .find input { width: 100%; }
  .plaque { font-size: 14px; }
  .plaque span { padding: 10px 12px; }
  .plate { border-left: 0; border-right: 0; box-shadow: none; }
  .sec.caveat { margin-left: calc(var(--pad) * -1); margin-right: calc(var(--pad) * -1); }
}
@media (max-width: 460px) {
  :root { --pad: 16px; }
  .reg a { flex-wrap: wrap; gap: 4px 10px; }
  .reg-dots { display: none; }
  .reg-name { flex: 1 1 100%; font-size: 21px; }
  .pg-next { text-align: left; }
  body { font-size: 16px; }
  .toc ul { columns: 1; }
  .wordmark { max-width: 250px; }
  .plaque { font-size: 12.5px; }
  .plaque span { padding: 9px 10px; }
  .ramp b { height: 8px; }
  .mast { padding-top: 24px; }
  .ridge { height: 34px; }
  .change { padding-left: 20px; }
  .foot { flex-direction: column; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition: none !important; animation: none !important; }
}
:focus-visible {
  outline: 3px solid var(--ember);
  outline-offset: 2px;
}
.bar :focus-visible, .mast :focus-visible { outline-color: var(--rind); }
"""


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{title}}</title>
<meta name="description" content="Roguefort {{version}} patch notes. {{total}} changes across {{n_sections}} sections.">
<meta name="theme-color" content="#111D35">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;500;700&family=DM+Mono:wght@400;500&family=Grenze+Gotisch:wght@500;700&display=swap" rel="stylesheet">
<style>
{{css}}</style>
</head>
<body>

<a class="skip" href="#doc">Skip to the changes</a>

<header class="mast">
  <svg class="marks" viewBox="0 0 1200 420" preserveAspectRatio="xMidYMin slice" aria-hidden="true" focusable="false">
    <defs>
      <path id="spk" d="M0,-11 L2.5,-2.5 L11,0 L2.5,2.5 L0,11 L-2.5,2.5 L-11,0 L-2.5,-2.5 Z"/>
    </defs>
    <g stroke="#FFF1E8" stroke-opacity=".13" stroke-width="1" fill="none" shape-rendering="crispEdges">
      <path d="M150 0 V70 M150 104 V190"/>
      <path d="M470 0 V44 M470 82 V150 M470 186 V240"/>
      <path d="M860 0 V96 M860 130 V210"/>
      <path d="M1060 0 V58 M1060 92 V164"/>
      <path d="M40 118 H96 M132 118 H286 M508 118 H642 M900 118 H1030"/>
      <path d="M60 300 H210 M250 300 H430 M745 300 H902"/>
      <path d="M140 58 H160 M150 48 V68"/>
      <path d="M850 176 H870 M860 166 V186"/>
      <path d="M60 40 H92 M60 40 V72"/>
      <path d="M1140 216 H1108 M1140 216 V184"/>
    </g>
    <g fill="#FFF1E8" fill-opacity=".34" shape-rendering="crispEdges">
      <use href="#spk" transform="translate(330,86)"/>
      <use href="#spk" transform="translate(712,52) scale(.7)"/>
      <use href="#spk" transform="translate(988,150)"/>
      <use href="#spk" transform="translate(232,214) scale(.6)"/>
    </g>
  </svg>
  <div class="mast-in">
    <img class="wordmark" src="assets/roguefort-wordmark.png"
         srcset="assets/roguefort-wordmark.png 1x, assets/roguefort-wordmark@2x.png 2x"
         width="526" height="166" alt="Roguefort">
    <p class="plaque">
      <span class="plaque-k">Patch notes</span><span class="plaque-v">{{version}}</span><span class="plaque-t">{{tag}}</span>
    </p>
    <h1 class="card"><span class="vh">Roguefort {{version}} patch notes: </span>{{lede}}</h1>
    <p class="mast-meta">
      <span>{{date}}</span>
      <span><b>{{total}}</b> changes</span>
      <span><b>{{n_sections}}</b> sections</span>
      <span>press <kbd>/</kbd> to filter</span>
    </p>
  </div>
  <div class="ramp" aria-hidden="true">
    <b class="r1"></b><b class="r2 k"></b><b class="r3"></b><b class="r4 k"></b><b class="r5"></b><b class="r6 k"></b><b class="r7 k"></b><b class="r8"></b>
  </div>
  <svg class="ridge" viewBox="0 0 1200 54" preserveAspectRatio="none" aria-hidden="true" focusable="false">
    <path fill="#49333B" d="M0,54 V22 H74 V10 H158 V30 H242 V16 H340 V34 H424 V20 H524 V38 H604 V24 H704 V12 H792 V32 H880 V18 H978 V36 H1068 V22 H1142 V32 H1200 V54 Z"/>
    <path fill="none" stroke="#FFA300" stroke-width="3" vector-effect="non-scaling-stroke"
          d="M0,25 H74 V13 H158 V33 H242 V19 H340 V37 H424 V23 H524 V41 H604 V27 H704 V15 H792 V35 H880 V21 H978 V39 H1068 V25 H1142 V35 H1200"/>
    <path fill="none" stroke="#271F1B" stroke-width="3" vector-effect="non-scaling-stroke"
          d="M0,22 H74 V10 H158 V30 H242 V16 H340 V34 H424 V20 H524 V38 H604 V24 H704 V12 H792 V32 H880 V18 H978 V36 H1068 V22 H1142 V32 H1200"/>
  </svg>
</header>

<div class="bar">
  <div class="rail" id="rail"></div>
  <div class="bar-in">
    <a class="bar-mark" href="#top">Roguefort</a>
    <span class="bar-here" id="here" aria-live="off"></span>
    <nav class="vers" aria-label="Versions">{{switcher}}</nav>
    <div class="find">
      <input id="q" type="search" placeholder="/ filter changes" aria-label="Filter changes" autocomplete="off">
    </div>
  </div>
</div>

<main id="top">
  <div class="plate">
    <nav class="toc" aria-label="Sections">
      <div class="toc-h">
        <h2>Contents</h2>
        <span><b id="live-total">{{total}}</b> changes in <b id="live-secs">{{n_sections}}</b> sections</span>
      </div>
      <ul>{{index_rows}}</ul>
      <div class="toc-end"></div>
    </nav>
    <div id="doc">
      {{body_rows}}
      <div class="empty hidden" id="empty"></div>
    </div>
  </div>
</main>

<nav class="pager" aria-label="Other releases">{{pager}}</nav>

<footer class="foot">
  <span>Roguefort {{version}} &middot; {{date}}</span>
  <span>Community reporters are credited against each change.</span>
</footer>

<script>
(function () {
  var q = document.getElementById('q');
  var empty = document.getElementById('empty');
  var rail = document.getElementById('rail');
  var here = document.getElementById('here');
  var liveTotal = document.getElementById('live-total');
  var liveSecs = document.getElementById('live-secs');
  var secs = [].slice.call(document.querySelectorAll('.sec'));
  var idx = [].slice.call(document.querySelectorAll('.idx'));

  var items = [];
  secs.forEach(function (s) {
    [].slice.call(s.querySelectorAll('.change')).forEach(function (li) {
      items.push({ el: li, sec: s, text: li.textContent.toLowerCase() });
    });
  });

  function countEl(id) { return document.querySelector('[data-count="' + id + '"]'); }

  function filter() {
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    secs.forEach(function (s) { s._n = 0; });
    items.forEach(function (it) {
      var hit = !term || it.text.indexOf(term) !== -1;
      it.el.classList.toggle('hidden', !hit);
      if (hit) { it.sec._n++; shown++; }
    });
    secs.forEach(function (s) {
      s.classList.toggle('hidden', s._n === 0);
      var id = s.dataset.sec;
      countEl(id).textContent = s._n;
      document.querySelector('[data-idx="' + id + '"]').parentElement
        .classList.toggle('hidden', s._n === 0);
      s.querySelector('.sec-n').textContent = s._n;
    });
    liveTotal.textContent = shown;
    liveSecs.textContent = secs.filter(function (s) { return s._n > 0; }).length;
    if (shown === 0) {
      empty.textContent = '';
      empty.appendChild(document.createTextNode('Nothing matches '));
      var b = document.createElement('b');
      b.textContent = q.value;
      empty.appendChild(b);
      empty.appendChild(document.createTextNode('. Try a shorter word, like mount, save or road.'));
      empty.classList.remove('hidden');
    } else {
      empty.classList.add('hidden');
    }
    onScroll();
  }

  q.addEventListener('input', filter);
  q.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { q.value = ''; filter(); q.blur(); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== q) { e.preventDefault(); q.focus(); }
  });

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      rail.style.width = (h > 0 ? Math.min(1, window.scrollY / h) * 100 : 0) + '%';
      var top = window.scrollY + 120, cur = null, curName = '';
      secs.forEach(function (s) {
        if (!s.classList.contains('hidden') && s.offsetTop <= top) {
          cur = s.dataset.sec;
          curName = s.querySelector('h2').firstChild.textContent;
        }
      });
      idx.forEach(function (a) { a.classList.toggle('on', a.dataset.idx === cur); });
      here.textContent = curName;
      ticking = false;
    });
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  onScroll();
})();
</script>
</body>
</html>
"""


INDEX_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Roguefort patch notes</title>
<meta name="description" content="Every Roguefort patch note. Latest: {{version}}, {{lede}} - {{total}} changes across {{n_sections}} sections.">
<meta name="theme-color" content="#111D35">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bitter:wght@400;500;700&family=DM+Mono:wght@400;500&family=Grenze+Gotisch:wght@500;700&display=swap" rel="stylesheet">
<style>{{css}}</style>
</head>
<body>

<a class="skip" href="#releases">Skip to all releases</a>

<header class="mast">
  <svg class="marks" viewBox="0 0 1200 420" preserveAspectRatio="xMidYMin slice" aria-hidden="true" focusable="false">
    <defs>
      <path id="spk" d="M0,-11 L2.5,-2.5 L11,0 L2.5,2.5 L0,11 L-2.5,2.5 L-11,0 L-2.5,-2.5 Z"/>
    </defs>
    <g stroke="#FFF1E8" stroke-opacity=".13" stroke-width="1" fill="none" shape-rendering="crispEdges">
      <path d="M150 0 V70 M150 104 V190"/>
      <path d="M470 0 V44 M470 82 V150 M470 186 V240"/>
      <path d="M860 0 V96 M860 130 V210"/>
      <path d="M1060 0 V58 M1060 92 V164"/>
      <path d="M40 118 H96 M132 118 H286 M508 118 H642 M900 118 H1030"/>
      <path d="M60 300 H210 M250 300 H430 M745 300 H902"/>
      <path d="M140 58 H160 M150 48 V68"/>
      <path d="M850 176 H870 M860 166 V186"/>
      <path d="M60 40 H92 M60 40 V72"/>
      <path d="M1140 216 H1108 M1140 216 V184"/>
    </g>
    <g fill="#FFF1E8" fill-opacity=".34" shape-rendering="crispEdges">
      <use href="#spk" transform="translate(330,86)"/>
      <use href="#spk" transform="translate(712,52) scale(.7)"/>
      <use href="#spk" transform="translate(988,150)"/>
      <use href="#spk" transform="translate(232,214) scale(.6)"/>
    </g>
  </svg>
  <div class="mast-in">
    <img class="wordmark" src="assets/roguefort-wordmark.png"
         srcset="assets/roguefort-wordmark.png 1x, assets/roguefort-wordmark@2x.png 2x"
         width="526" height="166" alt="Roguefort">
    <p class="plaque">
      <span class="plaque-k">Patch notes</span><span class="plaque-v">{{version}}</span><span class="plaque-t">{{tag}}</span>
    </p>
    <h1 class="card"><span class="vh">Roguefort patch notes. Latest release: </span>{{lede}}</h1>
    <p class="mast-meta">
      <span>{{date}}</span>
      <span><b>{{total}}</b> changes</span>
      <span><b>{{n_sections}}</b> sections</span>
    </p>
    <p class="cta"><a href="{{version}}.html">Read the {{version}} notes &rarr;</a></p>
  </div>
  <div class="ramp" aria-hidden="true">
    <b class="r1"></b><b class="r2 k"></b><b class="r3"></b><b class="r4 k"></b><b class="r5"></b><b class="r6 k"></b><b class="r7 k"></b><b class="r8"></b>
  </div>
  <svg class="ridge" viewBox="0 0 1200 54" preserveAspectRatio="none" aria-hidden="true" focusable="false">
    <path fill="#49333B" d="M0,54 V22 H74 V10 H158 V30 H242 V16 H340 V34 H424 V20 H524 V38 H604 V24 H704 V12 H792 V32 H880 V18 H978 V36 H1068 V22 H1142 V32 H1200 V54 Z"/>
    <path fill="none" stroke="#FFA300" stroke-width="3" vector-effect="non-scaling-stroke"
          d="M0,25 H74 V13 H158 V33 H242 V19 H340 V37 H424 V23 H524 V41 H604 V27 H704 V15 H792 V35 H880 V21 H978 V39 H1068 V25 H1142 V35 H1200"/>
    <path fill="none" stroke="#271F1B" stroke-width="3" vector-effect="non-scaling-stroke"
          d="M0,22 H74 V10 H158 V30 H242 V16 H340 V34 H424 V20 H524 V38 H604 V24 H704 V12 H792 V32 H880 V18 H978 V36 H1068 V22 H1142 V32 H1200"/>
  </svg>
</header>

<main>
  <div class="plate">
    <section class="toc" id="releases">
      <div class="toc-h">
        <h2>All releases</h2>
        <span><b>{{n_versions}}</b> {{release_word}}</span>
      </div>
      <ol class="reg">{{rows}}</ol>
      <div class="toc-end"></div>
    </section>
  </div>
</main>

<footer class="foot">
  <span>Roguefort patch notes</span>
  <span>Community reporters are credited against each change.</span>
</footer>
</body>
</html>
"""


def render_index(notes, all_versions):
    newest = notes[0]
    rows = []
    for n in notes:
        name = n["lede"] or n["version"]
        total = sum(len(sec["bullets"]) for sec in n["sections"])
        newest_tag = '<span class="reg-new">latest</span>' if n is newest else ""
        date = f' &middot; {html.escape(n["date"])}' if n["date"] else ""
        rows.append(
            f'<li><a href="{html.escape(n["version"])}.html">'
            f'<span class="reg-name">{html.escape(name)}</span>'
            f'<span class="reg-dots" aria-hidden="true"></span>'
            f'<span class="reg-meta"><b>{html.escape(n["version"])}</b>{date}'
            f' &middot; {total} changes{newest_tag}</span></a></li>'
        )
    return fill(INDEX_TEMPLATE, {
        "css": CSS,
        "version": html.escape(newest["version"]),
        "lede": html.escape(newest["lede"] or newest["version"]),
        "date": html.escape(newest["date"]),
        "tag": html.escape(newest["tag"] or "Build"),
        "total": sum(len(s["bullets"]) for s in newest["sections"]),
        "n_sections": len(newest["sections"]),
        "n_versions": len(all_versions),
        "release_word": "release" if len(all_versions) == 1 else "releases",
        "rows": "\n".join(rows),
    })


def main():
    DOCS.mkdir(exist_ok=True)
    files = sorted(NOTES.glob("*.md"), key=lambda p: version_key(p.stem), reverse=True)
    if not files:
        raise SystemExit("No notes found. Add notes/<version>.md and run again.")

    if ASSETS.is_dir():
        shutil.copytree(ASSETS, DOCS / "assets", dirs_exist_ok=True)

    notes = [parse(f) for f in files]
    versions = [n["version"] for n in notes]

    for i, note in enumerate(notes):
        older = notes[i + 1] if i + 1 < len(notes) else None
        newer = notes[i - 1] if i > 0 else None
        html_out = render(note, versions, older, newer)
        (DOCS / f"{note['version']}.html").write_text(html_out, encoding="utf-8")
        print(f"built docs/{note['version']}.html  ({sum(len(s['bullets']) for s in note['sections'])} changes)")

    (DOCS / "index.html").write_text(render_index(notes, versions), encoding="utf-8")
    word = "release" if len(versions) == 1 else "releases"
    print(f"built docs/index.html  ({len(versions)} {word}, newest {versions[0]})")

    # Drop pages whose notes file has gone, so docs/ cannot drift out of sync.
    keep = {f"{v}.html" for v in versions} | {"index.html"}
    for stale in sorted(DOCS.glob("*.html")):
        if stale.name not in keep:
            stale.unlink()
            print(f"removed stale docs/{stale.name}")

    (DOCS / ".nojekyll").write_text("", encoding="utf-8")


if __name__ == "__main__":
    main()
