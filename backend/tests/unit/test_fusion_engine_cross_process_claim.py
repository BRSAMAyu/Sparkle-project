"""V3-FIX-418 red/green: the fusion belief write must hold ACROSS processes.

``FusionEngine.update_user_state`` is a GET->fuse->SETEX read-modify-write
guarded by a module-level per-user ``asyncio.Lock`` (``_user_state_locks``).
That lock is process-local, but the call face is cross-process by deployment:
chat requests land on any uvicorn worker (``chat_signal_collector``), while
``TaskEventConsumer`` starts one consumer per worker lifespan (``main.py``) and
the ``sparkle_events`` group dispatches each event to ONE pod of the HPA
(k8s ``minReplicas=1/maxReplicas=5``). Two writers for the same user landing
on different processes cannot see each other's lock, and the last writer
silently drops the first writer's fused evidence (the WT294-P0 comment in
``fusion_engine.py`` documents the in-process variant of exactly this loss).

Fix direction (ledger V3-FIX-418, precedent V3-FIX-193/wt705 +
``batch_worklane._try_claim``): a per-user Redis SET NX EX claim taken inside
the process-local lock. The loser waits (bounded) for the peer to commit and
release, then claims and re-reads — fusing on TOP of the peer's state instead
of overwriting it. Budget exhausted or Redis claim store failing → fail-open
proceed (last-writer-wins stays the priced bounded harm; liveness does not
depend on Redis).

Test strategy mirrors test_state_estimator_cross_process_debounce.py: one
event loop plays both "processes".
- Each process gets its OWN ``_user_state_locks`` table (swapped between the
  two runs) — that is what makes them mutually invisible in-process.
- Both share ONE fake redis (production passes the same ``cache_service.redis``
  to every caller) — that store is both the belief-state store and the claim
  store.
- Process A is parked inside its state ``setex`` behind a gate — already past
  its load (empty state) but before its save: exactly the read-modify-write
  window where a second process must not overwrite.
"""

from __future__ import annotations

import asyncio

import app.services.evidence.fusion_engine as fusion_module
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)

_FUSION_CLAIM_PREFIX = "aurora:belief_state_claim:v1:"


def _ev(eid: str, strength: float) -> UnifiedEvidence:
    return UnifiedEvidence(
        evidence_id=eid,
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT,
        target_latent_variable=EvidenceTarget.GOAL_CLARITY,
        direction=EvidenceDirection.OBSERVE,
        strength=strength,
        confidence=0.9,
    )


class _TwoProcessSharedRedis:
    """跨进程共享存储替身：两个「进程」传入同一个 redis 实例（生产同此）。

    每个 op 都 ``await asyncio.sleep(0)`` 让协程交错。``arm_save_gate`` 后
    第一次 ``setex``（global belief state 落盘）停在事件上——把调用方停在
    已读未写的读改写窗口正中。
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.claim_attempts: list[tuple[str, bool]] = []
        self._save_gate: asyncio.Event | None = None  # armed，尚未被 setex 消费
        self._parked_gate: asyncio.Event | None = None  # 已被 setex 消费，调用方正停在上面
        self.save_gate_entered = asyncio.Event()

    def arm_save_gate(self) -> None:
        self._save_gate = asyncio.Event()

    def release_save_gate(self) -> None:
        gate = self._parked_gate or self._save_gate
        self._parked_gate = None
        self._save_gate = None
        if gate is not None:
            gate.set()

    async def get(self, key: str):
        await asyncio.sleep(0)
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, payload: str) -> None:
        await asyncio.sleep(0)
        if self._save_gate is not None:
            gate, self._save_gate = self._save_gate, None
            self._parked_gate = gate
            self.save_gate_entered.set()
            await gate.wait()
        self.store[key] = payload

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        await asyncio.sleep(0)
        acquired = not (nx and key in self.store)
        self.claim_attempts.append((key, acquired))
        if not acquired:
            return None  # redis-py set(nx=True) 被占返回 None
        self.store[key] = value
        return True

    async def expire(self, key: str, ttl: int) -> None:
        return None

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self.store.pop(key, None) is not None:
                deleted += 1
        return deleted


class _BrokenClaimRedis(_TwoProcessSharedRedis):
    """``set`` 整体故障的存储：claim 路径不可用，状态读写（get/setex）正常。"""

    async def set(self, key: str, value: str, ex: int | None = None, nx: bool = False):
        await asyncio.sleep(0)
        raise RuntimeError("redis claim path down")


class _NoNxRedis(_TwoProcessSharedRedis):
    """``set`` 不支持 nx/ex 的替身——驱动 TypeError get-then-set 降级路径。"""

    async def set(self, key: str, value: str):
        await asyncio.sleep(0)
        self.store[key] = value
        return True


async def _update(redis, user_id: str, evidence_items: list[UnifiedEvidence]):
    return await FusionEngine(user_id).update_user_state(redis, user_id=user_id, evidence_items=evidence_items)


async def _fused_evidence_ids(redis, user_id: str) -> list[str]:
    state = await FusionEngine(user_id).load_state(redis, user_id)
    return list(state.get_variable(EvidenceTarget.GOAL_CLARITY).last_evidence_ids)


async def test_cross_process_concurrent_updates_do_not_lose_evidence():
    """V3-FIX-418: two PROCESSES racing on one user must not drop evidence.

    RED against the pre-fix code: process A is parked mid-read-modify-write
    (loaded the empty state, not yet saved), process B passes its own
    (process-local) lock, reads the SAME empty state, and saves first — then
    A's save lands and B's evidence is silently gone. The in-process
    WT294-P0 lock cannot see across the process boundary.
    """
    shared_redis = _TwoProcessSharedRedis()
    shared_redis.arm_save_gate()  # A 的 global state 落盘闸门

    original_locks = fusion_module._user_state_locks
    try:
        # "进程 A"：自己的进程内锁表
        fusion_module._user_state_locks = type(original_locks)()
        task_a = asyncio.create_task(_update(shared_redis, "u1", [_ev("ev-a", 0.8)]))
        await asyncio.wait_for(shared_redis.save_gate_entered.wait(), timeout=5)

        # "进程 B"：跨进程 = 互不可见的进程内锁表（换表即换"进程"）
        fusion_module._user_state_locks = type(original_locks)()
        task_b = asyncio.create_task(_update(shared_redis, "u1", [_ev("ev-b", 0.6)]))
        await asyncio.sleep(0.05)  # B 走完 claim 尝试（修后进入有界等待）/（修前）直接双写

        shared_redis.release_save_gate()  # 放行 A 的落盘
        await asyncio.wait_for(task_a, timeout=5)
        await asyncio.wait_for(task_b, timeout=5)
    finally:
        fusion_module._user_state_locks = original_locks

    observations = await _fused_evidence_ids(shared_redis, "u1")
    assert "ev-a" in observations and "ev-b" in observations, (
        f"cross-process concurrent update_user_state lost evidence "
        f"(last_evidence_ids={observations}): the second writer overwrote the "
        "first writer's fused state — the per-user guard must hold across "
        "processes (uvicorn workers × TaskEventConsumer replicas), not only "
        "within one event loop"
    )


async def test_cross_process_claim_released_after_completion():
    """The per-user claim must not outlive the write: the claim key is gone
    after success, so the next cross-process writer can claim immediately
    (no stale claim pinning the user)."""
    shared_redis = _TwoProcessSharedRedis()
    await asyncio.wait_for(_update(shared_redis, "u2", [_ev("ev-a", 0.5)]), timeout=5)

    assert f"{_FUSION_CLAIM_PREFIX}u2" not in shared_redis.store, "claim key must be released after the write completes"
    assert "ev-a" in await _fused_evidence_ids(shared_redis, "u2")


async def test_claim_store_failure_fails_open_update_survives():
    """Fail-open per the batch_worklane / V3-FIX-193 precedent: a failing
    claim store must not break the fusion write path (liveness does not
    depend on Redis claim availability) — the update completes and the
    evidence is fused."""
    shared_redis = _BrokenClaimRedis()
    state = await asyncio.wait_for(_update(shared_redis, "u3", [_ev("ev-c", 0.7)]), timeout=5)

    assert state is not None
    assert "ev-c" in list(state.get_variable(EvidenceTarget.GOAL_CLARITY).last_evidence_ids), (
        "fusion write must survive a failing claim store (fail-open)"
    )


async def test_typeerror_fallback_get_then_set_still_failopen(monkeypatch):
    """Fake clients without nx/ex support (TypeError path, batch_worklane
    precedent) degrade to get-then-set: a peer-held claim still runs out the
    wait budget and then fails open — liveness preserved, no crash, and the
    loser NEVER deletes the peer's claim key."""
    shared_redis = _NoNxRedis()
    shared_redis.store[f"{_FUSION_CLAIM_PREFIX}u4"] = "1"  # 对端在途
    monkeypatch.setattr(fusion_module, "_FUSION_CLAIM_WAIT_SECONDS", 0.05)
    monkeypatch.setattr(fusion_module, "_FUSION_CLAIM_RETRY_INTERVAL_SECONDS", 0.01)

    state = await asyncio.wait_for(_update(shared_redis, "u4", [_ev("ev-d", 0.4)]), timeout=5)

    assert state is not None, "TypeError fallback must not break the fusion write"
    assert "ev-d" in list(state.get_variable(EvidenceTarget.GOAL_CLARITY).last_evidence_ids)
    assert shared_redis.store[f"{_FUSION_CLAIM_PREFIX}u4"] == "1", (
        "budget-exhausted loser must fail open WITHOUT deleting the peer's claim"
    )
