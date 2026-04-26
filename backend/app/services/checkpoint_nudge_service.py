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
    AuroraRuntimeTurnPlan,
    AuroraRuntimeV1Service,
    build_aurora_surface_metadata,
)
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.plan import Plan
from app.models.task import Task, TaskStatus
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

    def __init__(
        self,
        db: AsyncSession,
        redis=None,
        *,
        runtime_service: AuroraRuntimeV1Service | None = None,
    ) -> None:
        self.db = db
        self.redis = redis
        self.runtime_service = runtime_service or AuroraRuntimeV1Service(redis_client=redis)

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
            getattr(checkpoint, "day", 0) or (checkpoint.get("day") if isinstance(checkpoint, dict) else 0)
        )
        checkpoint_description = str(
            getattr(checkpoint, "description", "")
            or (checkpoint.get("description") if isinstance(checkpoint, dict) else "")
        ).strip()
        session_id = await self._resolve_target_session_id(user_id)
        nudge_id = f"cp:{plan_id}:{checkpoint_day}"
        fallback_content = (
            f"今天是你「{plan.name}」计划的第 {checkpoint_day} 天，也是你设置的一个检查点。"
            f"我们来快速复盘一下——{checkpoint_description}"
        )
        runtime_plan = await self._build_runtime_nudge(
            user_id=user_id,
            plan=plan,
            session_id=session_id,
            conversation_id=nudge_id,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
        )
        content = self._runtime_message_or_fallback(runtime_plan, fallback=fallback_content)
        widget = {
            "type": "aurora_nudge_entry",
            "data": {
                "nudge_id": nudge_id,
                "cta_label": "开始复盘",
                "checkpoint_description": checkpoint_description,
                "metadata": build_aurora_surface_metadata(
                    surface=AURORA_CHECKPOINT_SURFACE,
                    surface_complete=bool(runtime_plan.surface_complete) if runtime_plan else False,
                    modeling_complete=bool(runtime_plan.modeling_complete) if runtime_plan else False,
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

    async def _build_runtime_nudge(
        self,
        *,
        user_id: UUID,
        plan: Plan,
        session_id: UUID,
        conversation_id: str,
        checkpoint_day: int,
        checkpoint_description: str,
    ) -> AuroraRuntimeTurnPlan | None:
        progress_context = await self._build_checkpoint_progress_context(
            plan=plan,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
        )
        recent_messages = await self._load_recent_messages(user_id=user_id, session_id=session_id)
        user_message = self._checkpoint_trigger_message(
            plan=plan,
            checkpoint_day=checkpoint_day,
            progress_context=progress_context,
        )
        try:
            return await self.runtime_service.plan_turn(
                active_db=self.db,
                user_id=str(user_id),
                surface=AURORA_CHECKPOINT_SURFACE,
                conversation_id=conversation_id,
                request_id=f"checkpoint:{plan.id}:{checkpoint_day}:{uuid.uuid4().hex[:8]}",
                user_message=user_message,
                request_extra_context={
                    "checkpoint_state": progress_context["checkpoint_state"],
                    "task_state": progress_context["task_state"],
                    "cold_start_context": progress_context["cold_start_context"],
                    "informational_tensions": progress_context["informational_tensions"],
                    "surface_complete": False,
                    "decision_loop_required": True,
                },
                conversation_context={"messages": recent_messages},
                user_context_payload={
                    "profile_context": {
                        "cold_start_context": progress_context["cold_start_context"],
                    },
                    "task_state": progress_context["task_state"],
                    "checkpoint_state": progress_context["checkpoint_state"],
                },
            )
        except Exception as exc:
            logger.warning(
                f"Aurora checkpoint runtime nudge failed plan={plan.id} checkpoint_day={checkpoint_day}: {exc}"
            )
            return None

    async def _build_checkpoint_progress_context(
        self,
        *,
        plan: Plan,
        checkpoint_day: int,
        checkpoint_description: str,
    ) -> dict[str, Any]:
        tasks = await self._load_plan_tasks(plan.id)
        total_tasks = len(tasks)
        completed_tasks = [task for task in tasks if task.status == TaskStatus.COMPLETED]
        pending_tasks = [task for task in tasks if task.status != TaskStatus.COMPLETED]
        completion_rate = (len(completed_tasks) / total_tasks) if total_tasks else float(plan.progress or 0.0)
        expected_rate = self._expected_completion_rate(plan=plan, checkpoint_day=checkpoint_day, tasks=tasks)
        lagging_tasks = self._lagging_tasks(tasks=tasks, checkpoint_day=checkpoint_day)
        if not lagging_tasks and completion_rate < expected_rate:
            lagging_tasks = pending_tasks[:5]
        lagging_domains = self._task_domains(lagging_tasks)
        if not lagging_domains:
            lagging_domains = self._task_domains(pending_tasks[:5])
        progress_delta = round(completion_rate - expected_rate, 4)
        checkpoint_state = {
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "checkpoint_day": checkpoint_day,
            "checkpoint_description": checkpoint_description,
            "completion_rate": round(completion_rate, 4),
            "completion_percent": round(completion_rate * 100),
            "expected_completion_rate": round(expected_rate, 4),
            "expected_completion_percent": round(expected_rate * 100),
            "progress_delta": progress_delta,
            "completed_tasks": len(completed_tasks),
            "total_tasks": total_tasks,
            "pending_tasks": [
                {"title": task.title, "tags": task.tags or [], "status": str(task.status.value)}
                for task in pending_tasks[:8]
            ],
            "lagging_domains": lagging_domains,
            "specific_lagging_domain": lagging_domains[0] if lagging_domains else None,
            "lagging_task_titles": [task.title for task in lagging_tasks[:5]],
            "status": "behind" if progress_delta < -0.05 else "on_track",
        }
        task_state = {
            "plan_id": str(plan.id),
            "completion_rate": checkpoint_state["completion_rate"],
            "completion_percent": checkpoint_state["completion_percent"],
            "expected_completion_rate": checkpoint_state["expected_completion_rate"],
            "lagging_domains": lagging_domains,
            "current_task": pending_tasks[0].title if pending_tasks else None,
            "stage": "checkpoint",
        }
        cold_start_context = {
            "plan_name": plan.name,
            "subject": plan.subject,
            "goal_type": (
                "exam" if plan.type and str(plan.type.value) == "sprint" else str(plan.type.value if plan.type else "")
            ),
            "daily_available_minutes": plan.daily_available_minutes,
            "target_date": plan.target_date.isoformat() if plan.target_date else None,
            "checkpoint_completion_rate": checkpoint_state["completion_rate"],
            "checkpoint_lagging_domains": lagging_domains,
        }
        tensions = []
        if lagging_domains:
            tensions.append(
                {
                    "tension_id": f"{plan.id}:checkpoint:{checkpoint_day}:lagging-domain",
                    "domain": lagging_domains[0],
                    "description": f"checkpoint 完成率 {checkpoint_state['completion_percent']}%，落后域：{lagging_domains[0]}",
                    "priority": min(1.0, max(0.55, abs(progress_delta) + 0.55)),
                    "status": "open",
                    "evidence": checkpoint_state["lagging_task_titles"],
                    "importance_reasoning": "中段 checkpoint 需要基于真实进度定位后续计划是否要收紧或补强。",
                }
            )
        return {
            "checkpoint_state": checkpoint_state,
            "task_state": task_state,
            "cold_start_context": cold_start_context,
            "informational_tensions": tensions,
        }

    async def _load_plan_tasks(self, plan_id: UUID) -> list[Task]:
        result = await self.db.execute(
            select(Task).where(Task.plan_id == plan_id).order_by(Task.order_index.asc(), Task.created_at.asc())
        )
        return list(result.scalars().all())

    async def _load_recent_messages(self, *, user_id: UUID, session_id: UUID) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == user_id, ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(8)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            {
                "role": str(message.role.value if hasattr(message.role, "value") else message.role),
                "content": message.content,
                "created_at": message.created_at.isoformat() if message.created_at else None,
            }
            for message in rows
        ]

    def _checkpoint_trigger_message(
        self,
        *,
        plan: Plan,
        checkpoint_day: int,
        progress_context: dict[str, Any],
    ) -> str:
        checkpoint_state = progress_context["checkpoint_state"]
        domains = "、".join(checkpoint_state.get("lagging_domains") or [])
        return (
            f"触发「{plan.name}」第 {checkpoint_day} 天 checkpoint。"
            f"当前完成率 {checkpoint_state['completion_percent']}%，"
            f"预期 {checkpoint_state['expected_completion_percent']}%。"
            f"落后域：{domains or '暂无明确落后域'}。请生成一次针对性中段 nudge。"
        )

    def _runtime_message_or_fallback(self, runtime_plan: AuroraRuntimeTurnPlan | None, *, fallback: str) -> str:
        if runtime_plan and runtime_plan.messages:
            text = "\n".join(str(message).strip() for message in runtime_plan.messages if str(message).strip()).strip()
            if text:
                return text
        return fallback

    def _expected_completion_rate(self, *, plan: Plan, checkpoint_day: int, tasks: list[Task]) -> float:
        total_days = self._plan_total_days(plan=plan, tasks=tasks)
        if total_days <= 0:
            return min(1.0, max(0.0, float(plan.progress or 0.0)))
        return min(1.0, max(0.0, checkpoint_day / total_days))

    def _plan_total_days(self, *, plan: Plan, tasks: list[Task]) -> int:
        if plan.created_at and plan.target_date:
            local_start = (plan.created_at.replace(tzinfo=UTC) + timedelta(hours=8)).date()
            return max(1, (plan.target_date - local_start).days + 1)
        phase_indices = [int(task.phase_index) for task in tasks if task.phase_index is not None]
        return max(phase_indices, default=1)

    def _lagging_tasks(self, *, tasks: list[Task], checkpoint_day: int) -> list[Task]:
        lagging: list[Task] = []
        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                continue
            if task.phase_index is not None and int(task.phase_index) <= checkpoint_day:
                lagging.append(task)
                continue
            if task.due_date is not None and task.due_date <= (datetime.now(UTC) + timedelta(hours=8)).date():
                lagging.append(task)
        return lagging

    def _task_domains(self, tasks: list[Task]) -> list[str]:
        domains: list[str] = []
        seen: set[str] = set()
        for task in tasks:
            candidates = []
            if isinstance(task.tags, list):
                candidates.extend(str(tag) for tag in task.tags if str(tag).strip())
            candidates.append(str(task.title or ""))
            for candidate in candidates:
                domain = self._extract_domain_label(candidate)
                if domain and domain not in seen:
                    seen.add(domain)
                    domains.append(domain)
                    break
        return domains

    @staticmethod
    def _extract_domain_label(text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned:
            return ""
        for separator in ("·", "：", ":", "-", "—", "|"):
            if separator in cleaned:
                parts = [part.strip() for part in cleaned.split(separator) if part.strip()]
                if parts:
                    cleaned = parts[-1]
        return cleaned[:24]

    async def _resolve_target_session_id(self, user_id: UUID) -> UUID:
        result = await self.db.execute(
            select(ChatSession.id)
            .where(ChatSession.user_id == user_id, ChatSession.is_active.is_(True))
            .order_by(desc(ChatSession.last_message_at), desc(ChatSession.created_at))
            .limit(1)
        )
        session_id = result.scalar_one_or_none()
        return session_id or uuid.uuid4()

    async def _ensure_session(self, *, user_id: UUID, session_id: UUID, now: datetime) -> None:
        session = await self.db.get(ChatSession, session_id)
        if session is None:
            self.db.add(ChatSession(id=session_id, user_id=user_id, is_active=True, last_message_at=now))
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
        debrief_context = context.get("debrief_context") if isinstance(context.get("debrief_context"), dict) else None
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

        goal_met = self._goal_met_from_text(user_message) and bool(active.get("progress_good", True))
        active["assistant_round"] = 3
        active["second_answer"] = user_message
        active["goal_met"] = goal_met
        adjustment = None
        aurora_runtime = None
        if not goal_met:
            adjustment = await AdaptiveReplanner(self.db, self.redis).adjust_for_checkpoint(
                user_id=user_id,
                plan_id=UUID(str(active["plan_id"])),
                debrief_result={
                    "goal_met": False,
                    "checkpoint_day": int(active.get("checkpoint_day") or 0),
                    "checkpoint_description": active.get("checkpoint_description") or "",
                    "first_answer": active.get("first_answer") or "",
                    "second_answer": user_message,
                },
            )
        try:
            aurora_runtime = await AuroraCheckpointRuntimeService(self.db, self.redis).finalize_checkpoint_debrief(
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
            logger.warning(f"Aurora checkpoint runtime finalize failed session={session_uuid}: {exc}")
        await self._clear_session(active)
        if goal_met:
            message = "很好，按计划推进就行。"
        elif adjustment:
            message = "我来看看后续计划要不要调整。已经在下一阶段前插入了一个「复盘补强」任务。"
        else:
            message = "我来看看后续计划要不要调整。当前先记录这次偏差，后续任务先不额外打乱。"
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
        nudge_id = str(debrief_context.get("nudge_id") or f"cp:{plan_id}:{checkpoint_day}")
        plan = await self.db.get(Plan, UUID(plan_id)) if plan_id else None
        state = {
            "user_id": str(user_id),
            "session_id": str(session_id),
            "nudge_id": nudge_id,
            "plan_id": plan_id,
            "plan_name": plan.name if plan else "当前计划",
            "checkpoint_day": checkpoint_day,
            "checkpoint_description": str(debrief_context.get("checkpoint_description") or ""),
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
        normalized.append({"day": day_int, "description": str(item.get("description") or "")})
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
    result = await db.execute(select(Plan).where(Plan.is_active.is_(True), Plan.created_at >= cutoff))
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
                await service.send_nudge(user_id=plan.user_id, plan_id=plan.id, checkpoint=checkpoint)
                await _redis_setex(redis, key, CHECKPOINT_TRIGGER_TTL_SECONDS, "1")
                triggered += 1
            except Exception as exc:
                logger.warning(f"Checkpoint nudge failed plan={plan.id} day={checkpoint['day']}: {exc}")
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
