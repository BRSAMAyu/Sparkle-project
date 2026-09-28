"""Read-only package checks and advisory scheduling; no product execution."""
from __future__ import annotations
import hashlib,json,re
from pathlib import Path


def check_dag(tasks: list[dict]) -> list[str]:
    errors=[]; ids=[t['id'] for t in tasks]; by={t['id']:t for t in tasks}
    if len(set(ids))!=len(ids):errors.append('duplicate task id')
    for t in tasks:
        for d in t.get('depends_on',[]):
            if d not in by:errors.append(f"{t['id']}: missing {d}")
    visiting=set();done=set()
    def visit(k):
        if k in visiting:raise ValueError('cycle: '+k)
        if k in done or k not in by:return
        visiting.add(k)
        for d in by[k].get('depends_on',[]):visit(d)
        visiting.remove(k);done.add(k)
    try:
        for k in by:visit(k)
    except ValueError as e:errors.append(str(e))
    return errors


def ready(tasks: list[dict], state: dict | None = None, slots: int = 6,
          active_locks: set[str] | None = None, heavy_active: bool = False) -> list[str]:
    if slots<0 or slots>6:raise ValueError('background slots must be in 0..6')
    if check_dag(tasks):raise ValueError('invalid task graph')
    state=state or {}; result=[]; locks=set(active_locks or set()); heavy=heavy_active
    def completed(k):
        r=state.get(k,{})
        return r.get('implementation_state')=='INTEGRATED' and r.get('evidence_verdict')=='PASS'
    for t in tasks:
        s=state.get(t['id'],{})
        if completed(t['id']) or s.get('implementation_state') in {'WORKING','REVIEW_READY'}:continue
        if s.get('evidence_verdict')=='BLOCKED':continue
        if not all(completed(d) for d in t.get('depends_on',[])):continue
        req=set(t.get('required_locks',[]))
        if req & locks or (heavy and t.get('heavy_token_required')):continue
        result.append(t['id']); locks |= req
        heavy=heavy or bool(t.get('heavy_token_required'))
        if len(result)>=slots:break
    return result if slots else []


def check_receipt(data: dict, root: Path, required_reviewers: int = 1) -> list[str]:
    """Mechanical consistency, NOT proof that a claimed run or independent review truly happened."""
    errors=[]; root=root.resolve()
    if data.get('verdict')!='PASS':errors.append('verdict not PASS')
    sha=data.get('source_sha','')
    if not re.fullmatch(r'[a-f0-9]{7,40}',sha):errors.append('invalid source_sha')
    if not data.get('build_id'):errors.append('missing build_id')
    if not data.get('implementation_session'):errors.append('missing implementation_session')
    reviewers=data.get('reviews',[]); sessions={r.get('session') for r in reviewers if r.get('session')}
    if len(sessions)<required_reviewers:errors.append('insufficient distinct review sessions')
    if data.get('implementation_session') in sessions:errors.append('author cannot self-review')
    for r in reviewers:
        if r.get('verdict')!='APPROVE' or r.get('source_sha')!=sha:errors.append('review not approved for this sha')
    runs=data.get('runs',[])
    if not runs:errors.append('missing actual runs')
    for run in runs:
        if not run.get('command') or run.get('exit_code')!=0 or run.get('failed',0)>0 or run.get('skipped',0)>0:
            errors.append('failed, skipped or incomplete run')
    artifacts=data.get('artifacts',[])
    if not artifacts:errors.append('missing artifacts')
    for item in artifacts:
        p=(root/item.get('path','')).resolve()
        if not p.is_relative_to(root):errors.append('artifact outside evidence root');continue
        if not p.is_file():errors.append('missing artifact');continue
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item.get('sha256'):errors.append('artifact hash mismatch')
    return errors
