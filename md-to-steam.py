#!/usr/bin/env python3
"""Convert a notes/<ver>.md patch note into its Steam BBCode twin.

    python3 md-to-steam.py notes/0.19.6.md notes/0.19.6.steam.txt

Matches the conventions in notes/0.19.4.steam.txt: [b] for the H1 and every
"##" section, [list]/[*] for bullets, **bold** to [b]bold[/b], header comments
dropped, and no blank line between a section header and its list.
"""
import re, sys

def inline(t):
    return re.sub(r'\*\*(.+?)\*\*', r'[b]\1[/b]', t)

def convert(md):
    out, in_list = [], False
    for ln in md.split('\n'):
        if ln.startswith('<!--'):
            continue
        if ln.startswith('# '):
            out.append('[b]' + inline(ln[2:].strip()) + '[/b]'); continue
        if ln.startswith('## '):
            if in_list: out.append('[/list]'); in_list = False
            out.append(''); out.append('[b]' + inline(ln[3:].strip()) + '[/b]'); continue
        if ln.startswith('- '):
            if not in_list: out.append('[list]'); in_list = True
            out.append('[*]' + inline(ln[2:].strip())); continue
        if ln.strip() == '':
            if in_list: out.append('[/list]'); in_list = False
            out.append(''); continue
        out.append(inline(ln.rstrip()))
    if in_list: out.append('[/list]')
    txt = re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip() + '\n'
    return re.sub(r'(\[/b\])\n\n(\[list\])', r'\1\n\2', txt)

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    open(dst, 'w', encoding='utf-8').write(convert(open(src, encoding='utf-8').read()))
    body = open(dst, encoding='utf-8').read()
    for tag in ('list', 'b'):
        o, c = body.count(f'[{tag}]'), body.count(f'[/{tag}]')
        assert o == c, f'UNBALANCED [{tag}]: {o} open, {c} close'
    assert not re.search(r'^\#|\*\*|^- ', body, re.M), 'markdown left in output'
    print(f'wrote {dst} ({len(body.splitlines())} lines, tags balanced)')
