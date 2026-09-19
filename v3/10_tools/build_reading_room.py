#!/usr/bin/env python3
from pathlib import Path
import html
ROOT=Path(__file__).resolve().parents[1]
files=sorted(p for p in ROOT.rglob('*.md') if 'cards' not in p.parts)
sections=[]
for p in files:
 txt=p.read_text(encoding='utf-8',errors='ignore');sections.append('<section><h2>'+html.escape(str(p.relative_to(ROOT)))+'</h2><pre>'+html.escape(txt)+'</pre></section>')
head='<!doctype html><meta charset="utf-8"><title>Sparkle V3 Reading Room</title><style>body{max-width:1120px;margin:30px auto;font:15px/1.55 system-ui;background:#f5f1ea;color:#2b2724;padding:0 24px}input{position:sticky;top:10px;width:100%;padding:12px;font-size:16px}section{background:white;margin:18px 0;padding:20px;border-radius:14px}pre{white-space:pre-wrap;font:14px/1.55 ui-monospace,monospace}h2{font-size:18px}</style><input id=q placeholder="搜索 V3 文档"><main>'
tail='</main><script>q.oninput=()=>{let v=q.value.toLowerCase();document.querySelectorAll("section").forEach(s=>s.style.display=s.innerText.toLowerCase().includes(v)?"block":"none")}</script>'
(ROOT/'READING_ROOM.html').write_text(head+''.join(sections)+tail,encoding='utf-8');print(len(files))
