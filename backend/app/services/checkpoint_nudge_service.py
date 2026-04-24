from __future__ import annotations

import inspect
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1 import (
    AURORA_CHECKPOINT_SURFACE,
    AuroraCheckpointRuntimeService,
    build_aurora_surface_metadata,
)
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan
from app.orchestration.adaptive_replanner import AdaptiveReplanner

CHECKPOINT_TRIGGER_TTL_SECONDS = 7 * 24 * 60 * 60
DEBRIEF_SESSION_TTL_SECONDS = 60 * 60


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _coerce_session_uuid(session_id: str | UUID | None) -> UUID:
    if isinstance(session_id, UUID):
        return session_id
    raw = str(session_id or "").strip()
    try:
        return UUID(raw)
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"sparkle-session:{raw or uuid.uuid4()}")


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _redis_get(redis: Any, key: str) -> Any:
    if redis is None:
        return None
    getter = getattr(redis, "get", None)
    if getter is None:
        return None
    return await _maybe_await(getter(key))


async def _redis_setex(redis: Any, key: str, ttl: int, value: Any) -> None:
    if redis is None:
        return
    if hasattr(redis, "setex"):
        await _maybe_await(redis.setex(key, ttl, value))
        return
    if hasattr(redis, "set"):
        try:
            await _maybe_await(redis.set(key, value, ex=ttl))
        except TypeError:
            await _maybe_await(redis.set(key, value, ttl=ttl))


async def _redis_delete(redis: Any, key: str) -> None:
    if redis is None:
        return
    deleter = getattr(redis, "delete", None)
    if deleter is not None:
        await _maybe_await(deleter(key))


@dataclass(frozen=True)
class CheckpointPayload:
    day: int
    description: str


class CheckpointNudgeService:
    """Writes checkpoint review nudges into the user's existing chat stream."""

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def send_nudge(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        checkpoint: dict[str, Any] | CheckpointPayload,
    ) -> ChatMessage:
        plan = await self.db.get(Plan, plan_id)
        if plan is None or plan.user_id != user_id:
            raise ValueError(f"Plan {plan_id} not found for user {user_id}")

        checkpoint_day = int(
            getattr(checkpoint, "day", 0)
            or (checkpoint.get("day") if isinstance(checkpoint, dict) else 0)
        )
        checkpoint_description = str(
            getattr(checkpoint, "description", "")
            or (checkpoint.get("description") if isinstance(checkpoint, dict) else "")
        ).strip()
        session_id = await self._resolve_target_session_id(user_id)
        nudge_id = f"cp:{plan_id}:{checkpoint_day}"
        content = (
            f"今天是你「{plan.name}」计划的第 {checkpoint_day} 天，也是你设置的一个检查点。"
            f"我们来快速复盘一下——{checkpoint_description}"
        )
        widget = {
            "type": "aurora_nudge_entry",
            "data": {
                "nudge_id": nudge_id,
                "cta_label": "开始复盘",
                "checkpoint_description": checkpoint_description,
                "metadata": build_aurora_surface_metadata(
                    surface=AURORA_CHECKPOINT_SURFACE,
                    surface_complete=False,
                    modeling_complete=False,
                ),
                "debrief_context": {
                    "nudge_id": nudge_id,
                    "plan_id": str(plan_id),
                    "checkpoint_day": checkpoint_day,
                    "checkpoint_description": checkpoint_description,
                },
            },
        }
        now = _utcnow()
        await self._ensure_session(user_id=user_id, session_id=session_id, now=now)
        message = ChatMessage(
            user_id=user_id,
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=content,
            actions=[widget],
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message

    async def _resolve_target_session_id(self, user_id: UUID) -> UUID:
        result = await self.db.execute(
            select(ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatSession.is_active.is_(True))
            .order_by(desc(ChatSession.last_message_at), desc(ChatSession.created_at))
            .limit(1)
        )
        session_id = result.scalar_one_or_none()
        return session_id or uuid.uuid4()

    async def _ensure_session(
        self, *, user_id: UUID, session_id: UUID, now: datetime
    ) -> None:
        session = await self.db.get(ChatSession, session_id)
        if session is None:
            self.db.add(
                ChatSession(
                    id=session_id, user_id=user_id, is_active=True, last_message_at=now
                )
            )
        else:
            session.is_active = True
            session.last_message_at = now


class CheckpointDebriefService:
    """Small Redis-backed three-turn checkpoint debrief state machine."""

    NEGATIVE_MARKERS = (
        "落后",
        "没完成",
        "没做完",
        "跑偏",
        "没时间",
        "来不及",
        "没跟上",
        "没有完成",
    )

    def __init__(self, db: AsyncSession, redis=None) -> None:
        self.db = db
        self.redis = redis

    async def process_turn(
        self,
        *,
        user_id: UUID,
        chat_session_id: str | UUID,
        user_message: str,
        context: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        context = context or {}
        debrief_context = (
            context.get("debrief_context")
            if isinstance(context.get("debrief_context"), dict)
            else None
        )
        session_uuid = _coerce_session_uuid(chat_session_id)

        if debrief_context:
            state = await self._start_session(
                user_id=user_id,
                session_id=session_uuid,
                debrief_context=dict(debrief_context),
            )
            return {
                "message": "这个检查点的情况怎么样？",
                "is_debrief": True,
                "finished": False,
                "state": state,
            }

        active = await self._get_active_session(session_uuid)
        if not active:
            return None

        assistant_round = int(active.get("assistant_round") or 1)
        if assistant_round <= 1:
            progress_good = self._goal_met_from_text(user_message)
            active["assistant_round"] = 2
            active["first_answer"] = user_message
            active["progress_good"] = progress_good
            await self._save_session(active)
            if progress_good:
                message = "哪个部分你感觉最踏实？"
            else:
                message = "卡在哪里了，是理解问题还是时间问题？"
            return {
                "message": message,
                "is_debrief": True,
                "finished": False,
                "state": active,
            }

        goal_met = self._goal_met_from_text(user_message) and bool(
            active.get("progress_good", True)
        )
        active["assistant_round"] = 3
        active["second_answer"] = user_message
        active["goal_met"] = goal_met
        adjustment = None
        aurora_runtime = None
        if not goal_met:
            adjustment = await AdaptiveReplanner(
                self.db, self.redis
            ).adjust_for_checkpoint(
                user_id=user_id,
                plan_id=UUID(str(active["plan_id"])),
                debrief_result={
                    "goal_met": False,
                    "checkpoint_day": int(active.get("checkpoint_day") or 0),
                    "checkpoint_description": active.get("checkpoint_description")
                    or "",
                    "first_answer": active.get("first_answer") or "",
                    "second_answer": user_message,
                },
            )
        try:
            aurora_runtime = await AuroraCheckpointRuntimeService(
                self.db, self.redis
            ).finalize_checkpoint_debrief(
                user_id=user_id,
                session_id=session_uuid,
                conversation_id=str(active.get("nudge_id") or ""),
                plan_id=UUID(str(active["plan_id"])) if active.get("plan_id") else None,
                checkpoint_day=int(active.get("checkpoint_day") or 0),
                checkpoint_description=str(active.get("checkpoint_description") or ""),
                first_answer=str(active.get("first_answer") or ""),
                second_answer=user_message,
                goal_met=goal_met,
            )
        except Exception as exc:
            logger.warning(
                f"Aurora checkpoint runtime finalize failed session={session_uuid}: {exc}"
            )
        await self._clear_session(active)
        if goal_met:
            message = "很好，按计划推进就行。"
        elif adjustment:
            message = "我来看看后续计划要不要调整。已经在下一阶段前插入了一个「复盘补强」任务。"
        else:
            message = (
                "我来看看后续计划要不要调整。当前先记录这次偏差，后续任务先不额外打乱。"
            )
        return {
            "message": message,
            "is_debrief": True,
            "finished": True,
            "goal_met": goal_met,
            "adjustment": adjustment,
            "aurora_runtime": aurora_runtime,
        }

    async def _start_session(
        self,
        *,
        user_id: UUID,
        session_id: UUID,
        debrief_context: dict[str, Any],
    ) -> dict[str, Any]:
        plan_id = str(debrief_context.get("plan_id") or "")
        checkpoint_day = int(debrief_context.get("checkpoint_day") or 0)
        nudge_id = str(
            debrief_context.get("nudge_id") or f"cp:{plan_id}:{checkpoint_day}"
        )
        plan = await self.db.get(Plan, UUID(plan_id)) if plan_id else None
        state = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "nudge_id": nudge_id,
            "plan_id": plan_id,
            "plan_name": plan.name if plan else "当前计划",
            "checkpoint_day": checkpoint_day,
            "checkpoint_description": str(
                debrief_context.get("checkpoint_description") or ""
            ),
            "assistant_round": 1,
            "created_at": _utcnow().isoformat(),
        }
        await self._save_session(state)
        await _redis_setex(
            self.redis,
            self._active_key(session_id),
            DEBRIEF_SESSION_TTL_SECONDS,
            nudge_id,
        )
        return state

    async def _get_active_session(self, session_id: UUID) -> dict[str, Any] | None:
        nudge_id = await _redis_get(self.redis, self._active_key(session_id))
        if isinstance(nudge_id, bytes):
            nudge_id = nudge_id.decode("utf-8")
        if not nudge_id:
            return None
        raw = await _redis_get(self.redis, self._session_key(session_id, str(nudge_id)))
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if isinstance(raw, str):
            try:
                return json.loads(raw)
            except ValueError:
                return None
        return raw if isinstance(raw, dict) else None

    async def _save_session(self, state: dict[str, Any]) -> None:
        session_id = _coerce_session_uuid(state.get("session_id"))
        nudge_id = str(state.get("nudge_id") or "")
        await _redis_setex(
            self.redis,
            self._session_key(session_id, nudge_id),
            DEBRIEF_SESSION_TTL_SECONDS,
            json.dumps(state, ensure_ascii=False),
        )
        await _redis_setex(
            self.redis,
            self._active_key(session_id),
            DEBRIEF_SESSION_TTL_SECONDS,
            nudge_id,
        )

    async def _clear_session(self, state: dict[str, Any]) -> None:
        session_id = _coerce_session_uuid(state.get("session_id"))
        nudge_id = str(state.get("nudge_id") or "")
        await _redis_delete(self.redis, self._session_key(session_id, nudge_id))
        await _redis_delete(self.redis, self._active_key(session_id))

    @classmethod
    def _goal_met_from_text(cls, text: str) -> bool:
        haystack = str(text or "").lower()
        return not any(marker in haystack for marker in cls.NEGATIVE_MARKERS)

    @staticmethod
    def _active_key(session_id: UUID) -> str:
        return f"debrief:active:{session_id}"

    @staticmethod
    def _session_key(session_id: UUID, nudge_id: str) -> str:
        return f"debrief:session:{session_id}:{nudge_id}"


def extract_strategy_checkpoints(plan: Plan) -> list[dict[str, Any]]:
    if not plan.description:
        return []
    try:
        payload = json.loads(plan.description)
    except (TypeError, ValueError):
        return []
    strategy = payload.get("strategy") if isinstance(payload, dict) else None
    checkpoints = strategy.get("checkpoints") if isinstance(strategy, dict) else None
    if not isinstance(checkpoints, list):
        return []
    normalized = []
    for item in checkpoints:
        if not isinstance(item, dict):
            continue
        day = item.get("day")
        try:
            day_int = int(day)
        except (TypeError, ValueError):
            continue
        if day_int <= 0:
            continue
        normalized.append(
            {"day": day_int, "description": str(item.get("description") or "")}
        )
    return normalized


def plan_day_number(plan: Plan, *, today: date | None = None) -> int:
    local_today = today or (datetime.now(UTC) + timedelta(hours=8)).date()
    created_at = plan.created_at or _utcnow()
    local_start = (created_at.replace(tzinfo=UTC) + timedelta(hours=8)).date()
    return (local_today - local_start).days + 1


async def scan_and_send_checkpoint_nudges(
    *,
    db: AsyncSession,
    redis,
    today: date | None = None,
) -> dict[str, int]:
    cutoff = _utcnow() - timedelta(days=30)
    result = await db.execute(
        select(Plan).where(Plan.is_active.is_(True), Plan.created_at >= cutoff)
    )
    plans = list(result.scalars().all())
    scanned = 0
    triggered = 0
    skipped_duplicate = 0
    service = CheckpointNudgeService(db, redis)
    for plan in plans:
        scanned += 1
        today_day = plan_day_number(plan, today=today)
        for checkpoint in extract_strategy_checkpoints(plan):
            if int(checkpoint["day"]) != today_day:
                continue
            key = f"checkpoint:triggered:{plan.id}:{checkpoint['day']}"
            if await _redis_get(redis, key):
                skipped_duplicate += 1
                continue
            try:
                await service.send_nudge(
                    user_id=plan.user_id, plan_id=plan.id, checkpoint=checkpoint
                )
                await _redis_setex(redis, key, CHECKPOINT_TRIGGER_TTL_SECONDS, "1")
                triggered += 1
            except Exception as exc:
                logger.warning(
                    f"Checkpoint nudge failed plan={plan.id} day={checkpoint['day']}: {exc}"
                )
    return {
        "scanned": scanned,
        "triggered": triggered,
        "skipped_duplicate": skipped_duplicate,
    }


async def scan_and_dispatch_checkpoint_wakes(
    *,
    db: AsyncSession,
    redis,
    now: datetime | None = None,
) -> dict[str, int]:
    return await AuroraCheckpointRuntimeService(db, redis).process_due_wakes(now=now)
