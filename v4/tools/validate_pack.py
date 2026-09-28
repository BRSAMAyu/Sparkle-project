#!/usr/bin/env python3
"""Validate the design package only. Does not validate the Sparkle application."""
import json,sys
from pathlib import Path
from packlib import check_dag,ready
root=Path(__file__).resolve().parents[1]; errors=[]
data=json.loads((root/'04_tasks/tasks.json').read_text());tasks=data['tasks'];ids={t['id'] for t in tasks}
errors+=check_dag(tasks)
for t in tasks:
    if not (root/f"04_tasks/cards/{t['id']}.md").is_file():errors.append('missing card '+t['id'])
    for s in t['specs']:
        if not (root/s).is_file():errors.append('missing spec '+s)
    if len(t['acceptance'])<3:errors.append('insufficient checks '+t['id'])
    if t['risk']=='high' and t['independent_reviewers']<2:errors.append('high risk lacks independent reviewers')
mods=json.loads((root/'01_product/MODULE_MATRIX.json').read_text())['features']
if len(mods)!=len({m['name'] for m in mods}):errors.append('duplicate modules')
for m in mods:
    if not m['task_ids'] or not set(m['task_ids']) <= ids:errors.append('uncovered module '+m['name'])
scenarios=[json.loads(l) for l in (root/'06_evaluation/scenarios.jsonl').read_text().splitlines() if l.strip()]
if len(scenarios)!=len({s['case_id'] for s in scenarios}):errors.append('duplicate scenario')
for s in scenarios:
    if not set(s['tasks'])<=ids:errors.append('unknown scenario task')
for s in json.loads((root/'00_context/SOURCE_INDEX.json').read_text()):
    if not (root/s['copy']).is_file():errors.append('missing source copy '+s['id'])
for p in root.rglob('*'):
    if p.is_file() and p.suffix.lower() in {'.ttf','.otf','.woff','.woff2'}:errors.append('font bundled '+str(p))
initial=ready(tasks)
if len(initial)!=6:errors.append('initial six slots not ready')
# Measure token proposal contrast, not the full application.
def lum(h):
    c=[int(h[i:i+2],16)/255 for i in (1,3,5)]
    z=[v/12.92 if v<=0.04045 else ((v+0.055)/1.055)**2.4 for v in c]
    return sum(x*y for x,y in zip(z,[.2126,.7152,.0722]))
def contrast(a,b):
    x,y=sorted([lum(a),lum(b)]);return (y+.05)/(x+.05)
contrast_results={}
tokens=json.loads((root/'02_design/TOKENS.proposal.json').read_text())
for name,p in tokens['themes'].items():
    pairs={'body':('ink','surface'),'secondary':('muted','surface'),'button':('on_accent','accent'),'error':('error','surface'),'warning':('warning','surface')}
    contrast_results[name]={k:round(contrast(p[a],p[b]),2) for k,(a,b) in pairs.items()}
    for k,v in contrast_results[name].items():
        if v<4.5:errors.append(f'contrast {name}/{k} {v}')
report={'scope':'PACKAGE_ONLY_NOT_PRODUCT','tasks':len(tasks),'modules':len(mods),'scenario_specs':len(scenarios),'initial_ready':initial,'contrast_proposal_only':contrast_results,'errors':errors,'pass':not errors}
print(json.dumps(report,ensure_ascii=False,indent=2));sys.exit(1 if errors else 0)
