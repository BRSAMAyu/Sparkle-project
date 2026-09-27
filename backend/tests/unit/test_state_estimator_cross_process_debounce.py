"""V3-FIX-193 red/green: the estimator debounce must hold ACROSS processes.

V3-FIX-14 made the debounce check-then-act atomic per user, but only with a
process-local ``asyncio.Lock`` (``_DEBOUNCE_LOCKS``). The deployment shape is
FastAPI multi-worker × Celery (``cognitive_stream_worker`` also calls
``update_state``): two processes each pass their own in-process lock and each
pass the freshness check, so both mint a snapshot — the debounce silently
degrades to the bounded-harm double write that V3-FIX-11 only tolerated as a
theoretical residual.

Fix direction (ledger T-estimator-debounce-cross-process): a per-user Redis
SET NX claim, replicating the in-repo precedent
``app/services/batch_worklane.py`` ``_try_claim``/``_release_claim``
(injectable store, TypeError get-then-set fallback, fail-open when Redis is
absent).

Test strategy: one event loop plays both "processes".
- Each process gets its OWN ``_DEBOUNCE_LOCKS`` table (swapped between the two
  runs) — that is what makes them mutually invisible in-process.
- Both share ONE session stand-in (there is one PostgreSQL): committed rows
  are visible to the other process, pending (uncommitted) ones are NOT (READ
  COMMITTED semantics).
- The shared cross-process store is a FakeRedis mounted at
  ``cache_service.redis`` (production lookup path); pre-fix nothing reads it,
  so the red run exercises the real double-write behavior through the current
  interface.
- Process A is parked inside ``commit()`` behind a gate — exactly the window
  where a second process must not mint.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from uuid import uuid4

import app.core.cache as cache_module
import app.services.state_estimator_service as estimator_module
from app.models.user_state import UserStateSnapshot
from app.services.state_estimator_service import StateEstimatorService

_ESTIMATOR_CLAIM_PREFIX = "state_estimator:claim:"


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class _ScalarOneOrNone:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ScalarsAll:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows


class _TwoProcessSharedSession:
    """Session stand-in shared by BOTH simulated processes (one PostgreSQL).

    The FIRST commit is parked behind ``commit_gate`` so the test can hold
    process A mid-critical-section while process B runs — the interleaving
    window where the cross-process debounce loses atomicity.
    """

    def __init__(self) -> None:
        self.committed: list[UserStateSnapshot] = []
        self.pending: list[UserStateSnapshot] = []
        self.commits = 0
        self.entered_commit = asyncio.Event()
        self.commit_gate: asyncio.Event | None = None

    async def execute(self, stmt):
        await asyncio.sleep(0)  # cooperative yield between the two "processes"
        if "TrackingEvent" in str(stmt):
            return _ScalarsAll([])
        desc = {d["name"] for d in stmt.column_descriptions}
        if any(name in desc for name in ("UserStateSnapshot", "user_id", "id")):
            ordered = sorted(self.committed, key=lambda s: s.snapshot_at, reverse=True)
            return _ScalarOneOrNone(ordered[0] if ordered else None)
        return _ScalarsAll([])

    def add(self, obj):
        self.pending.append(obj)

    async def commit(self):
        if self.commit_gate is not None:
            gate, self.commit_gate = self.commit_gate, None
            self.entered_commit.set()
            await gate.wait()
        self.commits += 1
        self.committed.extend(self.pending)
        self.pending.clear()

    async def refresh(self, obj):
        return None


class _FakeClaimRedis:
    """Redis stand-in for the cross-process claim (SET NX semantics)."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        if nx and key in self.kv:
            return None  # 已被占：与 redis-py set(nx=True) 返回 None 一致
        self.kv[key] = value
        return True

    async def get(self, key: str):
        return self.kv.get(key)

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self.kv.pop(key, None) is not None:
                deleted += 1
        return deleted


class _NoNxRedis(_FakeClaimRedis):
    """Fake whose ``set`` lacks nx/ex — drives the TypeError fallback path."""

    async def set(self, key: str, value: str):
        self.kv[key] = value
        return True


async def _run_update(db, user_id):
    service = StateEstimatorService(db)
    return await service.update_state(user_id, timezone_name=None)


async def test_cross_process_concurrent_updates_mint_only_one_snapshot(monkeypatch):
    """V3-FIX-193: two PROCESSES racing on one user must mint ONE snapshot.

    RED against the pre-fix code: process A is parked mid-commit, process B
    passes its own (process-local) lock, passes the freshness check (A is not
    committed yet), and mints a second snapshot — the FastAPI multi-worker ×
    Celery double write. The in-process V3-FIX-14 lock cannot see B.
    """
    user_id = uuid4()
    shared_db = _TwoProcessSharedSession()
    gate_a = asyncio.Event()  # A 的提交闸门（本地持有；会话消费后置 None）
    shared_db.commit_gate = gate_a
    monkeypatch.setattr(cache_module.cache_service, "redis", _FakeClaimRedis())

    original_locks = estimator_module._DEBOUNCE_LOCKS
    try:
        # "进程 A"：自己的进程内锁表
        estimator_module._DEBOUNCE_LOCKS = defaultdict(asyncio.Lock)
        task_a = asyncio.create_task(_run_update(shared_db, user_id))
        await asyncio.wait_for(shared_db.entered_commit.wait(), timeout=5)

        # "进程 B"：跨进程 = 互不可见的进程内锁表（换表即换"进程"）
        estimator_module._DEBOUNCE_LOCKS = defaultdict(asyncio.Lock)
        task_b = asyncio.create_task(_run_update(shared_db, user_id))
        await asyncio.sleep(0.05)  # 给 B 走完 claim 尝试 / （修前）直接双写

        gate_a.set()  # 放行 A 的提交
        result_a = await asyncio.wait_for(task_a, timeout=5)
        result_b = await asyncio.wait_for(task_b, timeout=5)
    finally:
        estimator_module._DEBOUNCE_LOCKS = original_locks

    assert len(shared_db.committed) == 1, (
        f"cross-process concurrent update_state minted {len(shared_db.committed)} "
        "snapshots (FastAPI worker + Celery worker double write); the debounce "
        "must hold across processes via a shared claim, not only the "
        "process-local asyncio.Lock"
    )
    assert shared_db.commits == 1
    assert result_b is result_a, "the cross-process loser must be debounced onto the winner's snapshot"


async def test_cross_process_claim_released_after_completion(monkeypatch):
    """The per-user claim must not outlive the write: the claim key is gone
    after success, so the next cross-process call can claim again (no stale
    claim pinning the user)."""
    user_id = uuid4()
    shared_db = _TwoProcessSharedSession()
    shared_redis = _FakeClaimRedis()
    monkeypatch.setattr(cache_module.cache_service, "redis", shared_redis)

    original_locks = estimator_module._DEBOUNCE_LOCKS
    try:
        estimator_module._DEBOUNCE_LOCKS = defaultdict(asyncio.Lock)
        await asyncio.wait_for(_run_update(shared_db, user_id), timeout=5)
    finally:
        estimator_module._DEBOUNCE_LOCKS = original_locks

    assert shared_redis.kv == {}, "claim key must be released after the write completes"


async def test_redis_absent_degrades_to_inprocess_debounce(monkeypatch):
    """Fail-open per the batch_worklane precedent: Redis absent → behave
    exactly like pre-V3-FIX-193 (process-local lock only). Liveness of the
    estimator must not depend on Redis."""
    monkeypatch.setattr(cache_module.cache_service, "redis", None)
    shared_db = _TwoProcessSharedSession()

    returned = await asyncio.wait_for(_run_update(shared_db, uuid4()), timeout=5)

    assert returned is not None
    assert len(shared_db.committed) == 1


async def test_claim_store_injection_overrides_cache_service(monkeypatch):
    """Constructor-injected store (batch_worklane ``store=`` precedent) takes
    priority over ``cache_service.redis`` — and a peer claim held past the
    wait budget must fail OPEN (mint) WITHOUT touching the peer's claim key."""
    user_id = uuid4()
    shared_db = _TwoProcessSharedSession()
    injected = _FakeClaimRedis()
    injected.kv[f"{_ESTIMATOR_CLAIM_PREFIX}{user_id}"] = "1"  # 对端已抢 claim

    # cache_service.redis 故意指向另一个空 store：注入必须优先于它
    monkeypatch.setattr(cache_module.cache_service, "redis", _FakeClaimRedis())
    monkeypatch.setattr(estimator_module, "_ESTIMATOR_CLAIM_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(estimator_module, "_ESTIMATOR_CLAIM_RETRY_INTERVAL_SECONDS", 0.01)

    service = StateEstimatorService(shared_db, claim_store=injected)
    returned = await asyncio.wait_for(service.update_state(user_id, timezone_name=None), timeout=5)

    # 预算耗尽对端仍未放 → fail-open 放行重算，但绝不释放/覆盖对端的 claim 键
    assert returned is not None
    assert len(shared_db.committed) == 1
    assert injected.kv[f"{_ESTIMATOR_CLAIM_PREFIX}{user_id}"] == "1"


async def test_typeerror_fallback_get_then_set_still_failopen(monkeypatch):
    """Fake clients without nx/ex support (TypeError path, batch_worklane
    precedent) degrade to get-then-set: a peer-held claim still runs out the
    wait budget and then fails open — liveness preserved, no crash."""
    user_id = uuid4()
    shared_db = _TwoProcessSharedSession()
    shared_redis = _NoNxRedis()
    shared_redis.kv[f"{_ESTIMATOR_CLAIM_PREFIX}{user_id}"] = "1"  # 对端在途
    monkeypatch.setattr(cache_module.cache_service, "redis", shared_redis)
    monkeypatch.setattr(estimator_module, "_ESTIMATOR_CLAIM_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(estimator_module, "_ESTIMATOR_CLAIM_RETRY_INTERVAL_SECONDS", 0.01)

    returned = await asyncio.wait_for(_run_update(shared_db, user_id), timeout=5)

    assert returned is not None, "TypeError fallback must not break the estimator"
    assert shared_db.commits >= 1  # fail-open：放行重算
