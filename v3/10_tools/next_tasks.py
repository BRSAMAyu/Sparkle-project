#!/usr/bin/env python3
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--state',default='.sparkle_v3_fleet_state.json'); p.add_argument('--limit',type=int,default=6); a=p.parse_args()
tasks=json.loads((ROOT/'07_tasks/tasks.json').read_text(encoding='utf-8'))['tasks']; sp=Path(a.state)
state=json.loads(sp.read_text(encoding='utf-8')) if sp.exists() else {'tasks':{}}
def st(i): return state.get('tasks',{}).get(i,{}).get('status','TODO')
done={t['id'] for t in tasks if st(t['id'])=='DONE'}; running=[t for t in tasks if st(t['id']) in ('CLAIMED','READY_FOR_REVIEW','CHANGES')]
used={l for t in running for l in t['required_locks']}
cands=[]
for t in tasks:
    if st(t['id'])!='TODO' or not all(d in done for d in t['depends_on']) or used.intersection(t['required_locks']): continue
    cands.append(t)
risk={'critical':0,'high':1,'medium':2,'low':3}; res={'MEDIUM':0,'LIGHT':1,'HEAVY':2}
cands.sort(key=lambda t:(t['gate'],risk.get(t['risk'],9),res.get(t['resource_class'],9),t['id']))
chosen=[]; locks=set(used); heavy=sum(t['resource_class']=='HEAVY' for t in running)
for t in cands:
    if locks.intersection(t['required_locks']): continue
    if t['resource_class']=='HEAVY' and heavy>=4: continue
    chosen.append(t);locks.update(t['required_locks']);heavy+=t['resource_class']=='HEAVY'
    if len(chosen)>=a.limit: break
print(json.dumps([{'id':t['id'],'title':t['title'],'resource':t['resource_class'],'locks':t['required_locks'],'deps':t['depends_on']} for t in chosen],ensure_ascii=False,indent=2))
