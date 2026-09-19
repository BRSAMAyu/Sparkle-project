#!/usr/bin/env python3
from pathlib import Path
import argparse,json,datetime
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='cmd',required=True)
for name in ['init','show']:
 p=sub.add_parser(name);p.add_argument('--state',default='.sparkle_v3_fleet_state.json')
for name in ['claim','ready','changes','done','blocked']:
 p=sub.add_parser(name);p.add_argument('--state',default='.sparkle_v3_fleet_state.json');p.add_argument('--task',required=True);p.add_argument('--agent');p.add_argument('--evidence')
a=parser.parse_args();sp=Path(a.state);defs={t['id']:t for t in json.loads((ROOT/'07_tasks/tasks.json').read_text())['tasks']}
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
if a.cmd=='init':
 if sp.exists(): raise SystemExit(f'{sp} exists')
 st={'version':1,'created_at':now(),'tasks':{i:{'status':'TODO'} for i in defs}};sp.write_text(json.dumps(st,ensure_ascii=False,indent=2)+'\n');print(sp);raise SystemExit
if not sp.exists(): raise SystemExit('state missing; run init')
st=json.loads(sp.read_text())
if a.cmd=='show': print(json.dumps(st,ensure_ascii=False,indent=2));raise SystemExit
if a.task not in defs: raise SystemExit('unknown task')
rec=st['tasks'][a.task];mp={'claim':'CLAIMED','ready':'READY_FOR_REVIEW','changes':'CHANGES','done':'DONE','blocked':'BLOCKED'}
if a.cmd=='claim':
 missing=[d for d in defs[a.task]['depends_on'] if st['tasks'][d]['status']!='DONE']
 if missing: raise SystemExit(f'deps not done: {missing}')
 locks=set(defs[a.task]['required_locks'])
 for tid,r in st['tasks'].items():
  if tid!=a.task and r['status'] in ('CLAIMED','READY_FOR_REVIEW','CHANGES') and locks.intersection(defs[tid]['required_locks']): raise SystemExit(f'lock conflict with {tid}')
rec['status']=mp[a.cmd];rec['updated_at']=now()
if getattr(a,'agent',None): rec['agent']=a.agent
if getattr(a,'evidence',None): rec.setdefault('evidence',[]).append(a.evidence)
sp.write_text(json.dumps(st,ensure_ascii=False,indent=2)+'\n');print(json.dumps({a.task:rec},ensure_ascii=False,indent=2))
