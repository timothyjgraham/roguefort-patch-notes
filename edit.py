#!/usr/bin/env python3
"""Edit the patch notes in the browser, with the real page beside you.

    python3 edit.py            # opens the newest notes/<version>.md
    python3 edit.py 0.32.1     # opens that version

Left: the Markdown. Right: docs/<version>.html exactly as the site will show
it. Save (Cmd+S) writes notes/<version>.md, runs build.py and md-to-steam.py,
and reloads the preview. Done saves too, then tells you to hand back to Claude,
who reads `git diff` for your changes and commits. Nothing here commits or
pushes, and the server only listens on this machine.

If the file changed on disk since you opened it (Claude edited it, say), Save
refuses and offers to load the new copy instead of writing over it.
"""

import json
import re
import subprocess
import sys
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).parent
NOTES = ROOT / "notes"
DOCS = ROOT / "docs"
PORT = 8765


def version_key(name):
    return [int(p) if p.isdigit() else p for p in re.split(r"[.\-]", name)]


def versions():
    return sorted((p.stem for p in NOTES.glob("*.md")), key=version_key, reverse=True)


def note_path(v):
    if not re.fullmatch(r"[0-9A-Za-z.\-]+", v or ""):
        raise ValueError("bad version")
    return NOTES / f"{v}.md"


def rebuild(v):
    out = []
    for cmd in (["python3", "build.py"],
                ["python3", "md-to-steam.py", f"notes/{v}.md", f"notes/{v}.steam.txt"]):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        out.append((r.stdout + r.stderr).strip())
        if r.returncode != 0:
            return False, "\n".join(out)
    return True, "\n".join(out)


def changed_vs_git(v):
    r = subprocess.run(["git", "diff", "--stat", "HEAD", "--", f"notes/{v}.md"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.stdout.strip()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT), **kw)

    def log_message(self, *a):
        pass

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/":
            body = EDITOR_HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/versions":
            return self.send_json(200, {"versions": versions(), "start": START})
        if u.path == "/api/note":
            try:
                p = note_path(q.get("v", [""])[0])
            except ValueError:
                return self.send_json(400, {"error": "bad version"})
            if not p.exists():
                return self.send_json(404, {"error": "no such note"})
            return self.send_json(200, {"text": p.read_text(encoding="utf-8"),
                                        "mtime": p.stat().st_mtime_ns})
        if u.path == "/api/steam":
            v = q.get("v", [""])[0]
            p = NOTES / f"{v}.steam.txt"
            if not re.fullmatch(r"[0-9A-Za-z.\-]+", v) or not p.exists():
                return self.send_json(404, {"error": "no steam text yet"})
            return self.send_json(200, {"text": p.read_text(encoding="utf-8")})
        if u.path.startswith("/docs/") or u.path.startswith("/assets/"):
            return super().do_GET()
        self.send_error(404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path not in ("/api/save", "/api/done"):
            return self.send_error(404)
        n = int(self.headers.get("Content-Length", "0"))
        data = json.loads(self.rfile.read(n) or b"{}")
        try:
            p = note_path(data.get("v", ""))
        except ValueError:
            return self.send_json(400, {"error": "bad version"})
        if p.exists() and data.get("force") is not True and p.stat().st_mtime_ns != data.get("mtime"):
            return self.send_json(409, {"error": "changed on disk"})
        p.write_text(data["text"], encoding="utf-8")
        ok, log = rebuild(data["v"])
        return self.send_json(200 if ok else 500, {
            "ok": ok, "log": log, "mtime": p.stat().st_mtime_ns,
            "diff": changed_vs_git(data["v"]),
        })


EDITOR_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Patch Notes Editor</title>
<style>
:root{--bg:#1d2b53;--panel:#0f1830;--ink:#fff1e8;--dim:#c2c3c7;--line:#5f574f;--ok:#00e436;--warn:#ffa300;--bad:#ff004d;--sel:#ffa300}
*{box-sizing:border-box}
html,body{margin:0;height:100%;background:var(--bg);color:var(--ink);font:14px/1.4 ui-monospace,Menlo,monospace}
header{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px;border-bottom:2px solid var(--line);background:var(--panel)}
header b{color:var(--sel)}
select,button{font:inherit;color:var(--ink);background:var(--bg);border:2px solid var(--line);padding:4px 10px;cursor:pointer;border-radius:0}
button:hover,select:hover{border-color:var(--sel)}
button.primary{border-color:var(--sel)}
#status{margin-left:auto;color:var(--dim)}
#status.dirty{color:var(--warn)}#status.bad{color:var(--bad)}#status.ok{color:var(--ok)}
main{display:grid;grid-template-columns:1fr 1fr;height:calc(100% - 82px)}
textarea{width:100%;height:100%;resize:none;border:0;border-right:2px solid var(--line);padding:14px;background:var(--panel);color:var(--ink);font:14px/1.55 ui-monospace,Menlo,monospace;outline:none;tab-size:2}
iframe{width:100%;height:100%;border:0;background:#fff}
footer{height:32px;display:flex;gap:16px;align-items:center;padding:0 12px;border-top:2px solid var(--line);background:var(--panel);color:var(--dim);font-size:12px;overflow:hidden;white-space:nowrap}
footer .w{color:var(--warn)}
#done{position:fixed;inset:0;display:none;place-items:center;background:rgba(0,0,0,.6)}
#done div{background:var(--panel);border:2px solid var(--sel);padding:20px 24px;max-width:520px}
#done pre{white-space:pre-wrap;color:var(--dim)}
@media (max-width:800px){main{grid-template-columns:1fr;grid-template-rows:1fr 1fr}textarea{border-right:0;border-bottom:2px solid var(--line)}}
</style></head><body>
<header>
  <b>Patch notes</b>
  <select id="ver"></select>
  <button id="save" class="primary" title="Cmd+S">Save and preview</button>
  <button id="steam">Copy Steam text</button>
  <button id="doneBtn">Done</button>
  <span id="status">loading</span>
</header>
<main>
  <textarea id="md" spellcheck="true"></textarea>
  <iframe id="pv" title="preview"></iframe>
</main>
<footer id="checks"></footer>
<div id="done"><div>
  <p><b>Saved.</b> Go back to Claude and say <b>done with the notes</b>. Claude reads your changes from git, commits them, and publishes only when you say publish.</p>
  <pre id="diff"></pre>
  <button onclick="document.getElementById('done').style.display='none'">Keep editing</button>
</div></div>
<script>
const $=id=>document.getElementById(id);
let v=null, mtime=null, saved='', busy=false;
function status(t,c){const s=$('status');s.textContent=t;s.className=c||''}
function dirty(){return $('md').value!==saved}
function checks(){
  const t=$('md').value, lines=t.split('\n');
  const bullets=lines.filter(l=>l.startsWith('- '));
  const body=lines.filter(l=>!l.startsWith('# ')&&!l.startsWith('<!--')).join('\n');
  const semi=(body.match(/;/g)||[]).length, dash=(body.match(/—/g)||[]).length;
  const ta=bullets.filter(l=>/^- (The|A) /.test(l)).length;
  const fix=bullets.filter(l=>/no longer|rather than|\bstops\b/i.test(l)).length;
  const bold=bullets.filter(l=>l.startsWith('- **')).length;
  const pct=bullets.length?Math.round(100*ta/bullets.length):0;
  const w=(c,s)=>c?`<span class="w">${s}</span>`:s;
  $('checks').innerHTML=[`${bullets.length} bullets`,w(semi,`${semi} semicolons`),w(dash,`${dash} em-dashes`),
    w(pct>25,`${pct}% open The/A`),w(bullets.length&&fix/bullets.length>.1,`${fix} no longer/stops/rather than`),w(bold,`${bold} bold leads`)].join(' &middot; ');
}
async function load(ver){
  const r=await fetch('/api/note?v='+encodeURIComponent(ver));const j=await r.json();
  v=ver; mtime=j.mtime; saved=j.text; $('md').value=j.text; checks();
  $('pv').src='/docs/'+ver+'.html?'+Date.now(); status('saved','ok');
  history.replaceState(null,'','/?v='+ver);
}
async function save(force){
  if(busy) return null; busy=true; status('building');
  const scroll=(()=>{try{return $('pv').contentWindow.scrollY}catch(e){return 0}})();
  const r=await fetch('/api/save',{method:'POST',body:JSON.stringify({v,text:$('md').value,mtime,force:!!force})});
  busy=false; const j=await r.json();
  if(r.status===409){
    if(confirm('This file changed on disk since you opened it (maybe Claude edited it).\n\nOK: load the copy on disk (your unsaved edits are lost).\nCancel: keep yours and save over it.')){await load(v);return null}
    return save(true);
  }
  if(!j.ok){status('build failed, see console','bad');console.error(j.log);return null}
  mtime=j.mtime; saved=$('md').value; status('saved','ok');
  $('pv').onload=()=>{try{$('pv').contentWindow.scrollTo(0,scroll)}catch(e){}};
  $('pv').src='/docs/'+v+'.html?'+Date.now();
  return j;
}
$('md').addEventListener('input',()=>{status(dirty()?'unsaved':'saved',dirty()?'dirty':'ok');checks()});
$('save').onclick=()=>save();
$('doneBtn').onclick=async()=>{const j=dirty()?await save():await save();if(j){$('diff').textContent=j.diff||'No changes since the last commit.';$('done').style.display='grid'}};
$('steam').onclick=async()=>{if(dirty())await save();const r=await fetch('/api/steam?v='+v);const j=await r.json();
  if(j.text){await navigator.clipboard.writeText(j.text);status('Steam text copied','ok')}else status('no Steam text yet','bad')};
$('ver').onchange=async e=>{if(dirty()&&!confirm('Discard unsaved edits?')){e.target.value=v;return}load(e.target.value)};
document.addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key==='s'){e.preventDefault();save()}});
window.addEventListener('beforeunload',e=>{if(dirty()){e.preventDefault();e.returnValue=''}});
(async()=>{const j=await (await fetch('/api/versions')).json();
  const want=new URLSearchParams(location.search).get('v')||j.start;
  $('ver').innerHTML=j.versions.map(x=>`<option${x===want?' selected':''}>${x}</option>`).join('');
  load(want)})();
</script></body></html>"""

START = None

if __name__ == "__main__":
    all_v = versions()
    START = sys.argv[1] if len(sys.argv) > 1 else all_v[0]
    if START not in all_v:
        sys.exit(f"no notes/{START}.md")
    srv = HTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}/?v={START}"
    print(f"Patch notes editor: {url}  (Ctrl+C to stop)")
    threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
