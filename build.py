#!/usr/bin/env python3
"""Build the Roguefort patch notes site.

Reads every notes/<version>.md and writes docs/<version>.html, plus
docs/index.html for the newest version. Run it after editing the notes:

    python3 build.py

Each notes file may start with optional front matter comments:

    <!-- date: 27 August 2026 -->
    <!-- lede: Speed buys distance again. -->
    <!-- tag: Playtest -->
"""

import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
NOTES = ROOT / "notes"
DOCS = ROOT / "docs"

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


def render(note, all_versions):
    sections = note["sections"]
    total = sum(len(s["bullets"]) for s in sections)

    index_rows = []
    body_rows = []
    for s in sections:
        sid = slug(s["name"])
        n = len(s["bullets"])
        caveat = any(k in s["name"].lower() for k in CAVEAT_SECTIONS)
        index_rows.append(
            f'<li><a class="idx" href="#{sid}" data-idx="{sid}">'
            f'<span class="idx-name">{html.escape(s["name"])}</span>'
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

    switcher = "".join(
        f'<a class="ver{" on" if v == note["version"] else ""}" href="{v}.html">{v}</a>'
        for v in all_versions
    )

    return TEMPLATE.format(
        version=html.escape(note["version"]),
        title=html.escape(note["title"] or f"Roguefort {note['version']}"),
        lede=html.escape(note["lede"]),
        date=html.escape(note["date"]),
        tag=html.escape(note["tag"] or "Build"),
        total=total,
        n_sections=len(sections),
        index_rows="\n".join(index_rows),
        body_rows="\n".join(body_rows),
        switcher=switcher,
    )


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="Roguefort {version} patch notes. {total} changes across {n_sections} sections.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Young+Serif&family=Newsreader:ital,opsz,wght@0,6..72,300..600;1,6..72,300..500&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{
  --cave: #15160f;
  --stone: #1d1f16;
  --edge: #313426;
  --paste: #efe7d1;
  --dim: #a5a48f;
  --rind: #c39a4f;
  --vein: #7fb0a5;
  --wrap: 1180px;
}}
* {{ box-sizing: border-box; }}
html {{ scroll-behavior: smooth; scroll-padding-top: 90px; }}
body {{
  margin: 0;
  background: var(--cave);
  color: var(--paste);
  font-family: Newsreader, Georgia, serif;
  font-size: 17px;
  line-height: 1.62;
  -webkit-font-smoothing: antialiased;
}}
a {{ color: var(--vein); }}
.mono {{ font-family: "JetBrains Mono", ui-monospace, monospace; }}

/* ---- top rail ---- */
.rail {{
  position: sticky; top: 0; z-index: 30;
  background: rgba(21,22,15,.93);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--edge);
}}
.rail-in {{
  max-width: var(--wrap); margin: 0 auto; padding: 10px 24px;
  display: flex; align-items: center; gap: 18px;
}}
.mark {{
  font-family: "Young Serif", Georgia, serif;
  font-size: 19px; letter-spacing: .01em; color: var(--paste);
  text-decoration: none; white-space: nowrap;
}}
.mark span {{ color: var(--rind); }}
.wheel {{ flex: none; }}
.vers {{ display: flex; gap: 6px; margin-left: auto; }}
.ver {{
  font-family: "JetBrains Mono", monospace; font-size: 12px;
  padding: 5px 9px; border: 1px solid var(--edge); border-radius: 2px;
  color: var(--dim); text-decoration: none;
}}
.ver.on {{ color: var(--cave); background: var(--rind); border-color: var(--rind); }}
.ver:hover {{ color: var(--paste); border-color: var(--vein); }}
.ver.on:hover {{ color: var(--cave); }}
.find {{ position: relative; }}
.find input {{
  font-family: "JetBrains Mono", monospace; font-size: 12.5px;
  width: 208px; padding: 7px 10px 7px 26px;
  color: var(--paste); background: var(--stone);
  border: 1px solid var(--edge); border-radius: 2px;
}}
.find input::placeholder {{ color: #6e7060; }}
.find input:focus {{ outline: none; border-color: var(--vein); }}
.find::before {{
  content: "/"; position: absolute; left: 10px; top: 50%; transform: translateY(-50%);
  font-family: "JetBrains Mono", monospace; font-size: 12px; color: #6e7060;
}}

/* ---- hero ---- */
.hero {{ max-width: var(--wrap); margin: 0 auto; padding: 76px 24px 40px; }}
.eyebrow {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
  letter-spacing: .22em; text-transform: uppercase; color: var(--rind);
  margin: 0 0 18px;
}}
.num {{
  font-family: "Young Serif", Georgia, serif;
  font-size: clamp(62px, 13vw, 132px); line-height: .84;
  margin: 0; letter-spacing: -.02em;
}}
.lede {{
  font-family: "Young Serif", Georgia, serif;
  font-size: clamp(21px, 3.1vw, 31px); line-height: 1.28;
  max-width: 15ch; color: var(--paste);
  margin: 30px 0 0; padding-left: 18px;
  border-left: 3px solid var(--vein);
}}
.facts {{
  font-family: "JetBrains Mono", monospace; font-size: 12px;
  color: var(--dim); margin-top: 34px;
  display: flex; flex-wrap: wrap; gap: 8px 16px;
}}
.facts b {{ color: var(--paste); font-weight: 600; }}

/* ---- layout ---- */
.wrap {{
  max-width: var(--wrap); margin: 0 auto; padding: 0 24px 120px;
  display: grid; grid-template-columns: 232px 1fr; gap: 56px;
  align-items: start;
}}
.side {{ position: sticky; top: 78px; }}
.side h3 {{
  font-family: "JetBrains Mono", monospace; font-size: 10.5px;
  letter-spacing: .2em; text-transform: uppercase; color: #6e7060;
  margin: 0 0 12px; font-weight: 400;
}}
.side ul {{ list-style: none; margin: 0; padding: 0; max-height: 74vh; overflow: auto; }}
.idx {{
  display: flex; justify-content: space-between; gap: 10px; align-items: baseline;
  padding: 3px 0; text-decoration: none; color: var(--dim);
  font-size: 14.5px; line-height: 1.3;
}}
.idx:hover {{ color: var(--paste); }}
.idx.on {{ color: var(--rind); }}
.idx-n {{
  font-family: "JetBrains Mono", monospace; font-size: 10.5px;
  color: #6e7060; flex: none;
}}
.idx.on .idx-n {{ color: var(--rind); }}

/* ---- sections ---- */
.sec {{ margin: 0 0 58px; scroll-margin-top: 88px; }}
.sec h2 {{
  font-family: "Young Serif", Georgia, serif; font-weight: 400;
  font-size: 27px; line-height: 1.2; margin: 0 0 20px;
  padding-bottom: 12px; border-bottom: 1px solid var(--edge);
  display: flex; align-items: baseline; justify-content: space-between; gap: 16px;
}}
.sec-n {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
  color: #6e7060; flex: none;
}}
.changes {{ list-style: none; margin: 0; padding: 0; }}
.change {{
  position: relative; padding: 0 0 15px 22px; margin: 0 0 15px;
  border-bottom: 1px solid rgba(49,52,38,.55);
}}
.change:last-child {{ border-bottom: 0; }}
.change::before {{
  content: ""; position: absolute; left: 0; top: .62em;
  width: 7px; height: 7px; border-radius: 50%;
  border: 1.5px solid var(--vein);
}}
.caveat .sec-n, .caveat h2 {{ color: var(--rind); }}
.caveat .change::before {{ border-color: var(--rind); border-radius: 0; transform: rotate(45deg); }}
.caveat .change {{ color: var(--dim); }}
.tag {{
  font-family: "JetBrains Mono", monospace; font-size: .82em;
  color: var(--vein);
}}
.credits {{ display: inline; }}
.who-note {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
  color: #6e7060; margin-left: 6px; white-space: nowrap;
}}
.who {{
  font-family: "JetBrains Mono", monospace; font-size: 11px;
  color: var(--dim); background: var(--stone);
  border: 1px solid var(--edge); border-radius: 2px;
  padding: 1px 6px; margin-left: 6px; white-space: nowrap;
  display: inline-block; vertical-align: 1px;
}}

/* ---- filter states ---- */
.hidden {{ display: none !important; }}
mark {{ background: rgba(127,176,165,.22); color: var(--paste); border-radius: 2px; }}
.empty {{
  border: 1px dashed var(--edge); padding: 28px; text-align: center;
  color: var(--dim); font-size: 15px;
}}
.empty b {{ color: var(--paste); font-weight: 600; }}

.foot {{
  max-width: var(--wrap); margin: 0 auto; padding: 28px 24px 60px;
  border-top: 1px solid var(--edge);
  font-family: "JetBrains Mono", monospace; font-size: 11.5px; color: #6e7060;
  display: flex; flex-wrap: wrap; gap: 14px; justify-content: space-between;
}}

@media (max-width: 900px) {{
  .wrap {{ grid-template-columns: 1fr; gap: 30px; }}
  .side {{ position: static; }}
  .side ul {{
    display: flex; gap: 8px; overflow-x: auto; max-height: none;
    padding-bottom: 8px;
  }}
  .idx {{ border: 1px solid var(--edge); border-radius: 2px; padding: 5px 9px; white-space: nowrap; }}
  .find input {{ width: 100%; }}
  .rail-in {{ flex-wrap: wrap; gap: 10px 14px; padding: 10px 18px; }}
  .vers {{ order: 3; }}
  .find {{ order: 4; flex: 1 1 100%; }}
  .hero {{ padding-top: 48px; }}
}}
@media (prefers-reduced-motion: reduce) {{
  html {{ scroll-behavior: auto; }}
  * {{ transition: none !important; }}
}}
:focus-visible {{ outline: 2px solid var(--vein); outline-offset: 3px; }}
</style>
</head>
<body>

<header class="rail">
  <div class="rail-in">
    <a class="mark" href="#top">Rogue<span>fort</span></a>
    <svg class="wheel" width="30" height="30" viewBox="0 0 40 40" aria-hidden="true">
      <circle cx="20" cy="20" r="18" fill="#1d1f16" stroke="#c39a4f" stroke-width="2.5"/>
      <circle cx="20" cy="20" r="14.5" fill="#efe7d1"/>
      <g stroke="#7fb0a5" stroke-width="1.5" stroke-linecap="round" opacity=".85">
        <path d="M13 14 L17 19 L14 24"/><path d="M24 13 L21 18 L26 22"/><path d="M18 27 L23 28"/>
      </g>
      <path id="bite" d="" fill="#15160f"/>
    </svg>
    <div class="vers">{switcher}</div>
    <div class="find">
      <input id="q" type="search" placeholder="filter changes" aria-label="Filter changes" autocomplete="off">
    </div>
  </div>
</header>

<main id="top">
  <div class="hero">
    <p class="eyebrow">{tag} build &middot; {date}</p>
    <h1 class="num">{version}</h1>
    <p class="lede">{lede}</p>
    <p class="facts">
      <span><b>{total}</b> changes</span>
      <span><b>{n_sections}</b> sections</span>
      <span>press <b>/</b> to filter</span>
    </p>
  </div>

  <div class="wrap">
    <nav class="side" aria-label="Sections">
      <h3>Sections</h3>
      <ul>{index_rows}</ul>
    </nav>
    <div id="doc">
      {body_rows}
      <div class="empty hidden" id="empty"></div>
    </div>
  </div>
</main>

<footer class="foot">
  <span>Roguefort {version} &middot; {date}</span>
  <span>Community credits shown against each change.</span>
</footer>

<script>
(function () {{
  var q = document.getElementById('q');
  var empty = document.getElementById('empty');
  var secs = Array.prototype.slice.call(document.querySelectorAll('.sec'));
  var idx = Array.prototype.slice.call(document.querySelectorAll('.idx'));
  var bite = document.getElementById('bite');

  // Keep the original text so filtering can restore it.
  var items = [];
  secs.forEach(function (s) {{
    s.querySelectorAll('.change').forEach(function (li) {{
      items.push({{ el: li, sec: s, text: li.textContent.toLowerCase() }});
    }});
  }});

  function countEl(id) {{ return document.querySelector('[data-count="' + id + '"]'); }}

  function filter() {{
    var term = q.value.trim().toLowerCase();
    var shown = 0;
    secs.forEach(function (s) {{ s._n = 0; }});
    items.forEach(function (it) {{
      var hit = !term || it.text.indexOf(term) !== -1;
      it.el.classList.toggle('hidden', !hit);
      if (hit) {{ it.sec._n++; shown++; }}
    }});
    secs.forEach(function (s) {{
      s.classList.toggle('hidden', s._n === 0);
      var id = s.dataset.sec;
      countEl(id).textContent = s._n;
      var link = document.querySelector('[data-idx="' + id + '"]');
      link.parentElement.classList.toggle('hidden', s._n === 0);
      s.querySelector('.sec-n').textContent = s._n;
    }});
    if (shown === 0) {{
      empty.innerHTML = 'Nothing matches <b>' + q.value.replace(/[<>&]/g, '') +
        '</b>. Try a shorter word, like <b>mount</b> or <b>save</b>.';
      empty.classList.remove('hidden');
    }} else {{
      empty.classList.add('hidden');
    }}
  }}

  q.addEventListener('input', filter);
  q.addEventListener('keydown', function (e) {{
    if (e.key === 'Escape') {{ q.value = ''; filter(); q.blur(); }}
  }});
  document.addEventListener('keydown', function (e) {{
    if (e.key === '/' && document.activeElement !== q) {{ e.preventDefault(); q.focus(); }}
  }});

  // The wheel in the rail is eaten as you read, like the moon chip in game.
  function wedge(p) {{
    if (p <= 0) return '';
    if (p >= 0.999) return 'M20 20 m-15 0 a15 15 0 1 0 30 0 a15 15 0 1 0 -30 0';
    var a = -Math.PI / 2, b = a + p * Math.PI * 2, r = 15;
    return 'M20 20 L' + (20 + r * Math.cos(a)) + ' ' + (20 + r * Math.sin(a)) +
      ' A' + r + ' ' + r + ' 0 ' + (p > 0.5 ? 1 : 0) + ' 1 ' +
      (20 + r * Math.cos(b)) + ' ' + (20 + r * Math.sin(b)) + ' Z';
  }}

  var ticking = false;
  function onScroll() {{
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {{
      var h = document.documentElement.scrollHeight - window.innerHeight;
      bite.setAttribute('d', wedge(h > 0 ? Math.min(1, window.scrollY / h) : 0));
      var top = window.scrollY + 130, cur = null;
      secs.forEach(function (s) {{ if (!s.classList.contains('hidden') && s.offsetTop <= top) cur = s.dataset.sec; }});
      idx.forEach(function (a) {{ a.classList.toggle('on', a.dataset.idx === cur); }});
      ticking = false;
    }});
  }}
  window.addEventListener('scroll', onScroll, {{ passive: true }});
  onScroll();
}})();
</script>
</body>
</html>
"""


def main():
    DOCS.mkdir(exist_ok=True)
    files = sorted(NOTES.glob("*.md"), key=lambda p: version_key(p.stem), reverse=True)
    if not files:
        raise SystemExit("No notes found. Add notes/<version>.md and run again.")

    versions = [f.stem for f in files]
    for f in files:
        note = parse(f)
        (DOCS / f"{f.stem}.html").write_text(render(note, versions), encoding="utf-8")
        print(f"built docs/{f.stem}.html  ({sum(len(s['bullets']) for s in note['sections'])} changes)")

    shutil.copy(DOCS / f"{versions[0]}.html", DOCS / "index.html")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"index.html -> {versions[0]}")


if __name__ == "__main__":
    main()
