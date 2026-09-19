from pathlib import Path
import json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
def test_task_count_and_dag():
 d=json.loads((ROOT/'07_tasks/tasks.json').read_text())['tasks'];assert len(d)==107
 ids={t['id'] for t in d};assert len(ids)==107
 from collections import defaultdict,deque
 ind={i:0 for i in ids};g=defaultdict(list)
 for t in d:
  for x in t['depends_on']: assert x in ids;g[x].append(t['id']);ind[t['id']]+=1
 q=deque([i for i,v in ind.items() if v==0]);n=0
 while q:
  x=q.popleft();n+=1
  for y in g[x]:
   ind[y]-=1
   if ind[y]==0:q.append(y)
 assert n==107;assert sorted([t['id'] for t in d if not t['depends_on']])==['B-01','B-02','B-03','B-04','B-05','B-06']
def test_cards_and_must_read():
 d=json.loads((ROOT/'07_tasks/tasks.json').read_text())['tasks']
 for t in d:
  assert (ROOT/'07_tasks/cards'/f"{t['id']}.md").exists()
  for r in t['must_read']: assert (ROOT/r).exists(),(t['id'],r)
def test_scenarios():
 rows=[json.loads(x) for x in (ROOT/'05_metrics_eval/scenarios_v3.jsonl').read_text().splitlines() if x];assert len(rows)==260;assert len({x['case_id'] for x in rows})==260
def test_validator():
 r=subprocess.run([sys.executable,str(ROOT/'10_tools/validate_pack.py')],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
