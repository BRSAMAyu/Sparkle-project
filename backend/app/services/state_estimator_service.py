from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.business_metrics import STATE_ESTIMATOR_LATENCY, STATE_ESTIMATOR_RUNS
from app.core.telemetry_boundary import (
    STATE_ESTIMATOR_MIN_INTERVAL_SECONDS,
    TELEMETRY_DERIVED_LOAD_CAP,
    TELEMETRY_DERIVED_STRAIN_CAP,
)
from app.models.event import TrackingEvent
from app.models.user_state import UserStateSnapshot


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


#: V3-FIX-14: one lock per user so the debounce check-then-act below is a
#: single critical section (check freshness -> compute -> commit). Without
#: it, two concurrent telemetry-triggered calls both pass the freshness
#: check and both mint a snapshot. V3-FIX-193: this lock is process-local by
#: design (fast path; the service is constructed per request), so the
#: cross-process face (FastAPI multi-worker × Celery) is covered by the
#: Redis claim below — a residual same-process-vs-itself duplicate is
#: bounded harm (both writers apply the same cap/debounce bounds; reads
#: take the latest row), matching the V3-FIX-11 receipt's hazard assessment.
_DEBOUNCE_LOCKS: defaultdict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

#: V3-FIX-193: 跨进程防抖 claim 键前缀（SET NX，先例 batch_worklane._try_claim）。
_ESTIMATOR_CLAIM_PREFIX = "state_estimator:claim:"
#: claim TTL：只须盖住"取数→计算→提交"时长（正常远小于 1s）。持锁进程崩溃后
#: 残留键到期自清，行为退化回进程内锁 + 有界危害，不会永久卡死某用户。
_ESTIMATOR_CLAIM_TTL_SECONDS = 10
#: 对端进程持 claim 时的有界等待预算：等它提交并释放后抢到 claim，落入下方
#: 既有 freshness 检查即走 debounce（对端快照已可见）。预算耗尽仍抢不到 →
#: 放行（fail-open，与 batch_worklane 先例一致）："对端已提交"由 freshness
#: 检查吸收；"对端未提交仍双写"是 V3-FIX-11 认定过的有界危害。
_ESTIMATOR_CLAIM_WAIT_SECONDS = 1.0
_ESTIMATOR_CLAIM_RETRY_INTERVAL_SECONDS = 0.05


@dataclass
class StateWindow:
    start: datetime
    end: datetime


class StateEstimatorService:
    def __init__(self, db: AsyncSession, claim_store: Any | None = None):
        self.db = db
        # V3-FIX-193: 跨进程 claim 存储可注入（测试用 FakeRedis）；None 时惰性
        # 取 cache_service.redis（先例 batch_worklane._get_store）。
        self._claim_store_override = claim_store

    def _get_claim_store(self) -> Any:
        """跨进程 claim 存储（redis）。导入放内层，测试可用注入替身。"""
        if self._claim_store_override is not None:
            return self._claim_store_override
        try:
            from app.core.cache import cache_service

            return cache_service.redis
        except Exception:  # noqa: BLE001 — cache 模块异常不阻塞估算主链路
            return None

    def _claim_key(self, user_id: UUID) -> str:
        return f"{_ESTIMATOR_CLAIM_PREFIX}{user_id}"

    async def _try_claim(self, user_id: UUID) -> bool:
        """SET NX per-user claim（先例 batch_worklane._try_claim）。

        True = 抢到（本进程负责本次重算）；False = 另一进程（FastAPI 多
        worker 或 Celery worker）正在为该用户重算。Redis 缺席/故障时返回
        True：退化为既有进程内锁，估算存活不依赖 Redis（fail-open）。
        """
        store = self._get_claim_store()
        if store is None:
            return True
        try:
            acquired = await store.set(self._claim_key(user_id), "1", nx=True, ex=_ESTIMATOR_CLAIM_TTL_SECONDS)
            # set(nx=True) 返回 True = 抢到；None/False = 已被占
            return bool(acquired)
        except TypeError:
            # 某些 fake/客户端不支持 nx/ex —— 降级为 get-then-set（测试环境）
            try:
                if await store.get(self._claim_key(user_id)):
                    return False
                await store.set(self._claim_key(user_id), "1")
                return True
            except Exception:  # noqa: BLE001
                return True
        except Exception as exc:  # noqa: BLE001 — 存储故障不阻塞估算
            logger.warning("[StateEstimator] cross-process claim failed (proceeding): {}", exc)
            return True

    async def _await_claim(self, user_id: UUID) -> bool:
        """对端持 claim 时有界等待其提交释放；抢到返回 True，预算耗尽返回 False。"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _ESTIMATOR_CLAIM_WAIT_SECONDS
        while loop.time() < deadline:
            await asyncio.sleep(_ESTIMATOR_CLAIM_RETRY_INTERVAL_SECONDS)
            if await self._try_claim(user_id):
                return True
        return False

    async def _release_claim(self, user_id: UUID) -> None:
        store = self._get_claim_store()
        if store is None:
            return
        try:
            await store.delete(self._claim_key(user_id))
        except Exception:  # noqa: BLE001 — 残留 claim 由 TTL 兜底
            pass

    async def update_state(
        self,
        user_id: UUID,
        timezone_name: str | None,
        *,
        force: bool = False,
    ) -> UserStateSnapshot:
        """Recompute the user's state snapshot from recent telemetry.

        V3-FIX-11 T1 (D-01 R2 F4 "request-arms-the-estimator"): every
        telemetry ingest endpoint call and every cognitive stream worker event
        used to synchronously mint a fresh snapshot here, and the raw
        event-volume term saturated cognitive_load at ~50 events/24h. Two
        bounds now apply:

        - debounce: telemetry-triggered recomputes for the same user are
          rate-limited to one per STATE_ESTIMATOR_MIN_INTERVAL_SECONDS; inside
          the window the latest existing snapshot is returned unchanged, so no
          single telemetry request can synchronously move user state.
        - cap: the telemetry-derived portion of cognitive_load is capped by
          TELEMETRY_DERIVED_LOAD_CAP (see _compute_state).

        ``force=True`` bypasses the debounce for server-side schedulers
        (nightly review etc.) that own their cadence.

        V3-FIX-14: the freshness check and the snapshot write run inside a
        per-user lock (``_DEBOUNCE_LOCKS``), so concurrent telemetry-triggered
        calls serialize: the second caller re-checks freshness after the
        first one committed and gets the existing snapshot instead of minting
        a duplicate. ``force`` still skips the freshness *check*, but its
        write is serialized against the same lock.

        V3-FIX-193: that lock is process-local and the deployment runs FastAPI
        multi-worker × Celery, so the same serialization is repeated across
        processes with a per-user Redis SET NX claim (precedent:
        ``batch_worklane._try_claim``). A caller that loses the claim waits
        (bounded) for the peer to commit and release, then falls into the
        freshness check above and is debounced onto the peer's snapshot. If
        the wait budget runs out the call proceeds anyway (fail-open, matching
        the batch_worklane precedent): "peer already committed" is absorbed by
        the freshness check; the residual double write is the bounded harm the
        V3-FIX-11 receipt already priced in. Redis absent → claim always
        succeeds → behaviour identical to V3-FIX-14.
        """
        async with _DEBOUNCE_LOCKS[user_id]:
            claimed = await self._try_claim(user_id)
            if not claimed:
                # V3-FIX-193: 另一进程正在为该用户重算。有界等待其提交释放
                # claim；抢到后落入下方 freshness 检查即走 debounce。预算耗尽
                # 仍未抢到则放行（fail-open）：双写是有界危害，估算不被 Redis
                # 故障卡死。未抢到时不释放 claim——那是对端的锁。
                claimed = await self._await_claim(user_id)
            try:
                if not force:
                    latest = await self.get_latest_snapshot(user_id)
                    if latest is not None and (_utcnow() - latest.snapshot_at) < timedelta(
                        seconds=STATE_ESTIMATOR_MIN_INTERVAL_SECONDS
                    ):
                        STATE_ESTIMATOR_RUNS.labels(result="debounced").inc()
                        return latest

                start_time = _utcnow()
                window = self._default_window()
                events = await self._fetch_recent_events(user_id, window)
                snapshot = self._compute_state(user_id, events, window, timezone_name)
                self.db.add(snapshot)
                await self.db.commit()
                await self.db.refresh(snapshot)
                STATE_ESTIMATOR_RUNS.labels(result="success").inc()
                STATE_ESTIMATOR_LATENCY.observe((_utcnow() - start_time).total_seconds())
                return snapshot
            finally:
                if claimed:
                    await self._release_claim(user_id)

    async def get_latest_snapshot(self, user_id: UUID) -> UserStateSnapshot | None:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .order_by(desc(UserStateSnapshot.snapshot_at))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_id(self, user_id: UUID, snapshot_id: str) -> UserStateSnapshot | None:
        result = await self.db.execute(
            select(UserStateSnapshot)
            .where(UserStateSnapshot.user_id == user_id)
            .where(UserStateSnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    def _default_window(self) -> StateWindow:
        end = _utcnow()
        start = end - timedelta(hours=24)
        return StateWindow(start=start, end=end)

    async def _fetch_recent_events(self, user_id: UUID, window: StateWindow) -> list[TrackingEvent]:
        result = await self.db.execute(
            select(TrackingEvent)
            .where(TrackingEvent.user_id == user_id)
            .where(TrackingEvent.received_at >= window.start)
            .order_by(TrackingEvent.received_at.desc())
            .limit(200)
        )
        return list(result.scalars().all())

    def _compute_state(
        self,
        user_id: UUID,
        events: list[TrackingEvent],
        window: StateWindow,
        timezone_name: str | None,
    ) -> UserStateSnapshot:
        total_events = len(events)
        wrong_events = 0
        focus_start_at: datetime | None = None
        focus_end_at: datetime | None = None
        sprint_mode = False

        for event in events:
            if event.event_type in {"quiz_wrong", "error_recorded"}:
                wrong_events += 1
            if event.event_type == "question_submit":
                payload = event.payload or {}
                if payload.get("correct") is False:
                    wrong_events += 1
            if event.event_type == "focus_start":
                focus_start_at = event.received_at
            if event.event_type == "focus_end":
                focus_end_at = event.received_at
            payload = event.payload or {}
            if payload.get("sprint_mode") is True:
                sprint_mode = True

        focus_mode = False
        if focus_start_at and (not focus_end_at or focus_end_at < focus_start_at):
            if _utcnow() - focus_start_at < timedelta(hours=2):
                focus_mode = True

        wrong_ratio = wrong_events / max(1, total_events)
        # V3-FIX-11 T1: BOTH terms below are computed from client telemetry
        # (wrong-event counts and raw volume are client-asserted rows in
        # tracking_events), so the combined telemetry-derived load is capped
        # by TELEMETRY_DERIVED_LOAD_CAP: semantically empty noise (heartbeat /
        # screen_view floods, ~50 events/24h) can no longer saturate
        # cognitive_load to 1.0 and drive interruptibility to 0. Direction is
        # preserved (more struggle -> higher load), only the ceiling is
        # bounded. Server-authoritative signals (event_registry domain, D-01)
        # may later add on top of this cap.
        telemetry_load = (wrong_events * 0.15) + (total_events * 0.02)
        cognitive_load = min(min(1.0, telemetry_load), TELEMETRY_DERIVED_LOAD_CAP)
        # V3-FIX-14: strain_index is likewise 100% client-telemetry-derived
        # (wrong-event counts are client-asserted rows) and is consumed on a
        # decision-adjacent surface (plan_context prompt injection), so the
        # forged quiz_wrong flood must not saturate it either. The estimator
        # is the only writer of the column, so this producer-side cap bounds
        # every reader (events API readback, chat prior_outputs, evidence
        # health). Direction preserved, only the ceiling is bounded.
        strain_index = min(
            min(1.0, wrong_ratio + (0.2 if wrong_events >= 3 else 0.0)),
            TELEMETRY_DERIVED_STRAIN_CAP,
        )
        interruptibility = max(0.0, 1.0 - cognitive_load - (0.2 if focus_mode else 0.0))

        tz = None
        if timezone_name:
            try:
                tz = ZoneInfo(timezone_name)
            except Exception:
                tz = None
        now_local = _utcnow().astimezone(tz) if tz else _utcnow()
        time_context = {
            "hour": now_local.hour,
            "weekday": now_local.weekday(),
        }

        derived_event_ids = [event.event_id for event in events[:20]]

        return UserStateSnapshot(
            user_id=user_id,
            snapshot_at=_utcnow(),
            window_start=window.start,
            window_end=window.end,
            cognitive_load=cognitive_load,
            interruptibility=interruptibility,
            strain_index=strain_index,
            focus_mode=focus_mode,
            sprint_mode=sprint_mode,
            knowledge_state=None,
            time_context=time_context,
            derived_event_ids=derived_event_ids,
        )
