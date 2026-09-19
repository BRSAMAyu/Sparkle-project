#!/usr/bin/env python3
from pathlib import Path
import json, sys, re
ROOT=Path(__file__).resolve().parents[1]
errors=[]; warnings=[]
def err(x): errors.append(x)
def check(rel):
    if not (ROOT/rel).exists(): err(f"missing file: {rel}")
for r in ['README_START_HERE.md','NORTH_STAR.md','V3_DEFINITION_OF_DONE.md','07_tasks/tasks.json','07_tasks/TASK_INDEX.md','07_tasks/dependency_graph.mmd','05_metrics_eval/scenarios_v3.jsonl','05_metrics_eval/persona_library.json','06_agent_fleet/LEADER_PROMPT.md','06_agent_fleet/WORKER_PROMPT.md','06_agent_fleet/REVIEWER_PROMPT.md']:
    check(r)
data=json.loads((ROOT/'07_tasks/tasks.json').read_text(encoding='utf-8')); tasks=data['tasks']; ids=[t['id'] for t in tasks]; idset=set(ids)
if len(ids)!=len(idset): err('duplicate task ids')
if len(tasks)!=107: err(f'task count expected 107 got {len(tasks)}')
for t in tasks:
    for d in t['depends_on']:
        if d not in idset: err(f"{t['id']} missing dependency {d}")
    if not (ROOT/'07_tasks/cards'/f"{t['id']}.md").exists(): err(f"missing card {t['id']}")
    for r in t.get('must_read',[]):
        if not (ROOT/r).exists(): err(f"{t['id']} must_read missing: {r}")
    if t['risk'] in ('high','critical') and t['reviewers_required']<2: err(f"{t['id']} high risk requires 2 reviewers")
from collections import defaultdict,deque
ind={i:0 for i in idset}; g=defaultdict(list)
for t in tasks:
    for d in t['depends_on']: g[d].append(t['id']); ind[t['id']]+=1
q=deque([i for i,v in ind.items() if v==0]); visited=[]
while q:
    x=q.popleft(); visited.append(x)
    for y in g[x]:
        ind[y]-=1
        if ind[y]==0:q.append(y)
if len(visited)!=len(tasks): err('dependency graph has cycle')
initial=sorted([t['id'] for t in tasks if not t['depends_on']])
if initial!=['B-01','B-02','B-03','B-04','B-05','B-06']: err(f'initial frontier wrong: {initial}')
lines=[x for x in (ROOT/'05_metrics_eval/scenarios_v3.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
if len(lines)!=260: err(f'scenario count expected 260 got {len(lines)}')
caseids=[]
for ln in lines:
    try: caseids.append(json.loads(ln)['case_id'])
    except Exception as e: err(f'bad scenario {e}')
if len(caseids)!=len(set(caseids)): err('duplicate scenario case_id')
for p in ROOT.rglob('*.md'):
    txt=p.read_text(encoding='utf-8',errors='ignore')
    if re.search(r'\bSpark\b(?!le)',txt): warnings.append(f'possible old product name: {p.relative_to(ROOT)}')
print(json.dumps({'ok':not errors,'task_count':len(tasks),'scenario_count':len(lines),'errors':errors,'warnings':warnings[:25]},ensure_ascii=False,indent=2))
sys.exit(1 if errors else 0)
