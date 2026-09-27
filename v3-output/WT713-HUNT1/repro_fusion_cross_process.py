"""WT713 hunt1 TEMP evidence test — DELETE AFTER RUN.

FusionEngine.update_user_state guards its load->fuse->save read-modify-write
with a module-level per-user asyncio.Lock (``_user_state_locks``). Same class
as V3-FIX-193: the lock is process-local, so two processes writing the same
user's belief state (FastAPI chat signal path vs TaskEventConsumer consumer
group dispatch) interleave and the last writer silently drops the first
writer's evidence (the in-file WT294-P0 comment documents the in-process
variant of exactly this loss).

Test strategy mirrors test_state_estimator_cross_process_debounce.py:
one event loop plays both processes; each gets its OWN ``_user_state_locks``
table (swapped between the runs), both share ONE fake redis (one Redis).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import app.services.evidence.fusion_engine as fe_module
from app.services.evidence.fusion_engine import FusionEngine
from app.services.evidence.unified_evidence import (
    EvidenceDirection,
    EvidenceSourceType,
    EvidenceTarget,
    UnifiedEvidence,
)


class YieldingFakeRedis:
    """Fake redis: every op awaits a sleep(0) tick so coroutines interleave.

    ``gate_save_after_get``: when armed, the FIRST setex parks on an event —
    that holds "process A" inside its critical section after its load but
    before its save, exactly the read-modify-write window.
    """

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.gate_save_after_get = False
        self._save_gate: asyncio.Event | None = None

    async def get(self, key: str):
        await asyncio.sleep(0)
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, payload: str) -> None:
        await asyncio.sleep(0)
        if self.gate_save_after_get:
            self.gate_save_after_get = False
            self._save_gate = asyncio.Event()
            await self._save_gate.wait()
        self.store[key] = payload

    async def set(self, key: str, payload: str) -> None:
        await asyncio.sleep(0)
        self.store[key] = payload

    async def expire(self, key: str, ttl: int) -> None:
        return None

    async def delete(self, *keys: str) -> None:
        for k in keys:
            self.store.pop(k, None)


def _evidence(eid: str, strength: float) -> UnifiedEvidence:
    return UnifiedEvidence(
        evidence_id=eid,
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT,
        target_latent_variable=EvidenceTarget.GOAL_CLARITY,
        direction=EvidenceDirection.OBSERVE,
        strength=strength,
        confidence=0.9,
    )


async def main() -> int:
    redis = YieldingFakeRedis()
    redis.gate_save_after_get = True  # park A after its load, before its save

    # Process A: own lock table.
    fe_module._user_state_locks.__init__()  # fresh table = "process A"
    engine_a = FusionEngine("u1")
    task_a = asyncio.create_task(
        engine_a.update_user_state(redis, user_id="u1", evidence_items=[_evidence("ev-a", 0.8)])
    )
    # Let A enter the lock, load (empty), and park inside gated setex.
    while redis._save_gate is None:
        await asyncio.sleep(0)
    await asyncio.sleep(0)

    # Process B: SWAP the lock table — that is what makes B another process.
    old_table = fe_module._user_state_locks
    fe_module._user_state_locks = type(old_table)()  # fresh table = "process B"
    engine_b = FusionEngine("u1")
    task_b = asyncio.create_task(
        engine_b.update_user_state(redis, user_id="u1", evidence_items=[_evidence("ev-b", 0.6)])
    )
    await task_b
    # B done writing its full fused state (based on the SAME empty prior A read);
    # now release A — its save overwrites B's.
    redis._save_gate.set()
    await task_a
    fe_module._user_state_locks = old_table

    # Single-process semantics: both evidences must survive in the fused state.
    final = await FusionEngine("u1").load_state(redis, "u1")
    var = final.get_variable(EvidenceTarget.GOAL_CLARITY)
    observations = list(var.last_evidence_ids)
    print("last_evidence_ids:", observations)
    has_a = "ev-a" in observations
    has_b = "ev-b" in observations
    if not (has_a and has_b):
        print(f"RED: cross-process lost update — ev-a present={has_a}, ev-b present={has_b}")
        return 1
    print("GREEN: both evidences survived")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
