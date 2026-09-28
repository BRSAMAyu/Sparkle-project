#!/usr/bin/env python3
"""Print advisory next tasks. Never writes fleet state or launches agents."""
import argparse,json
from pathlib import Path
from packlib import ready
p=argparse.ArgumentParser();p.add_argument('--state',type=Path);p.add_argument('--slots',type=int,default=6);p.add_argument('--heavy-active',action='store_true')
a=p.parse_args();root=Path(__file__).resolve().parents[1]
tasks=json.loads((root/'04_tasks/tasks.json').read_text())['tasks']
state=json.loads(a.state.read_text()).get('tasks',{}) if a.state else {}
print(json.dumps({'advisory_only':True,'leader_is_separate':True,'task_ids':ready(tasks,state,a.slots,heavy_active=a.heavy_active),'warning':'Still bind actual paths and acquire existing repository fleet leases before work.'},ensure_ascii=False,indent=2))
