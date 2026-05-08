from __future__ import annotations

import inspect
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from difflib import SequenceMatcher
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
from app.aurora.runtime_v1.models import AuroraStateSnapshot
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


@dataclass(frozen=True)
class CheckpointQuestion:
    question_id: str
    focus: str
    question: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "question_id": self.question_id,
            "focus": self.focus,
            "question": self.question,
            "reason": self.reason,
        }


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
        runtime_plan, personalization = await self._build_runtime_nudge(
            user_id=user_id,
            plan=plan,
            session_id=session_id,
            conversation_id=nudge_id,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
        )
        fallback_content = personalization.get("opening") or (
            f"今天是你「{plan.name}」计划的第 {checkpoint_day} 天，也是你设置的一个检查点。"
            f"我们来快速复盘一下——{checkpoint_description}"
        )
        content = self._runtime_message_or_fallback(runtime_plan, fallback=fallback_content)
        checkpoint_questions = list(personalization.get("questions") or [])
        widget = {
            "type": "aurora_nudge_entry",
            "data": {
                "nudge_id": nudge_id,
                "cta_label": "开始复盘",
                "checkpoint_description": checkpoint_description,
                "opening_summary": personalization.get("opening") or content,
                "previous_runtime_state_summary": personalization.get("previous_runtime_state_summary") or "",
                "open_threads": list(personalization.get("open_threads") or []),
                "unclosed_questions": list(personalization.get("unclosed_questions") or []),
                "checkpoint_questions": checkpoint_questions,
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
                    "opening_summary": personalization.get("opening") or content,
                    "question_plan": checkpoint_questions,
                    "previous_runtime_state_summary": personalization.get("previous_runtime_state_summary") or "",
                    "open_threads": list(personalization.get("open_threads") or []),
                    "progress_facts": list(personalization.get("progress_facts") or []),
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

        try:
            from app.core.event_bus import event_bus
            await event_bus.publish("nudge.triggered", {
                "user_id": str(user_id),
                "nudge_id": nudge_id,
                "type": "checkpoint",
                "plan_id": str(plan_id),
                "checkpoint_day": checkpoint_day,
                "message_id": str(message.id),
            })
        except Exception:
            pass

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
    ) -> tuple[AuroraRuntimeTurnPlan | None, dict[str, Any]]:
        progress_context = await self._build_checkpoint_progress_context(
            plan=plan,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
        )
        recent_messages = await self._load_recent_messages(user_id=user_id, session_id=session_id)
        personalization = await self._build_checkpoint_personalization(
            user_id=user_id,
            plan=plan,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
            checkpoint_state=progress_context["checkpoint_state"],
            recent_messages=recent_messages,
        )
        progress_context["checkpoint_state"].update(
            {
                "previous_runtime_state_summary": personalization["previous_runtime_state_summary"],
                "open_threads": personalization["open_threads"],
                "unclosed_questions": personalization["unclosed_questions"],
                "personalized_opening": personalization["opening"],
                "personalized_questions": personalization["questions"],
                "narrative_variant": personalization["narrative_variant"],
            }
        )
        user_message = self._checkpoint_trigger_message(
            plan=plan,
            checkpoint_day=checkpoint_day,
            progress_context=progress_context,
        )
        try:
            runtime_plan = await self.runtime_service.plan_turn(
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
            return runtime_plan, personalization
        except Exception as exc:
            logger.warning(
                f"Aurora checkpoint runtime nudge failed plan={plan.id} checkpoint_day={checkpoint_day}: {exc}"
            )
            return None, personalization

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

    async def _build_checkpoint_personalization(
        self,
        *,
        user_id: UUID,
        plan: Plan,
        checkpoint_day: int,
        checkpoint_description: str,
        checkpoint_state: dict[str, Any],
        recent_messages: list[dict[str, Any]],
    ) -> dict[str, Any]:
        previous_snapshots = await self._load_previous_checkpoint_snapshots(user_id=user_id)
        previous_summary = self._previous_runtime_state_summary(previous_snapshots)
        open_threads = self._open_runtime_threads(previous_snapshots)
        unclosed_questions = self._unclosed_questions(recent_messages)
        progress_facts = self._progress_facts(checkpoint_state)
        questions = self._checkpoint_question_plan(
            checkpoint_state=checkpoint_state,
            open_threads=open_threads,
            unclosed_questions=unclosed_questions,
        )
        previous_openings = [
            str(message.get("content") or "")
            for message in recent_messages
            if str(message.get("role") or "").lower() == "assistant"
        ]
        previous_openings.extend(
            self._snapshot_narrative_history(previous_snapshots),
        )
        opening, narrative_variant = self._checkpoint_opening(
            plan=plan,
            checkpoint_day=checkpoint_day,
            checkpoint_description=checkpoint_description,
            previous_summary=previous_summary,
            open_threads=open_threads,
            unclosed_questions=unclosed_questions,
            progress_facts=progress_facts,
            previous_openings=previous_openings,
        )
        return {
            "opening": opening,
            "questions": [question.to_dict() for question in questions],
            "previous_runtime_state_summary": previous_summary,
            "open_threads": open_threads,
            "unclosed_questions": unclosed_questions,
            "progress_facts": progress_facts,
            "narrative_variant": narrative_variant,
        }

    async def _load_previous_checkpoint_snapshots(self, *, user_id: UUID, limit: int = 12) -> list[AuroraStateSnapshot]:
        result = await self.db.execute(
            select(AuroraStateSnapshot)
            .where(
                AuroraStateSnapshot.user_id == user_id,
                AuroraStateSnapshot.surface == AURORA_CHECKPOINT_SURFACE,
            )
            .order_by(AuroraStateSnapshot.snapshot_at.desc(), AuroraStateSnapshot.created_at.desc())
            .limit(max(1, limit))
        )
        return list(result.scalars().all())

    def _previous_runtime_state_summary(self, snapshots: list[AuroraStateSnapshot]) -> str:
        if not snapshots:
            return ""
        latest = snapshots[0]
        user_snapshot = dict(latest.user_model_snapshot or {})
        pieces = []
        checkpoint_description = str(user_snapshot.get("checkpoint_description") or "").strip()
        blocker = str(user_snapshot.get("blocker_summary") or "").strip()
        next_task = str(user_snapshot.get("next_task_title") or "").strip()
        if checkpoint_description:
            pieces.append(f"上次 checkpoint 是「{checkpoint_description}」")
        if blocker:
            pieces.append(f"当时还没闭合的是「{blocker}」")
        if next_task:
            pieces.append(f"后面接着的是「{next_task}」")
        if not pieces:
            for item in latest.informational_tensions or []:
                if isinstance(item, dict) and str(item.get("description") or "").strip():
                    pieces.append(str(item["description"]).strip())
                    break
        return "，".join(pieces)[:180]

    def _open_runtime_threads(self, snapshots: list[AuroraStateSnapshot]) -> list[str]:
        threads: list[str] = []
        seen: set[str] = set()
        for snapshot in snapshots[:4]:
            for item in snapshot.informational_tensions or []:
                if not isinstance(item, dict):
                    continue
                if str(item.get("status") or "open") in {"resolved", "dropped"}:
                    continue
                text = str(item.get("description") or "").strip()
                if text and text not in seen:
                    seen.add(text)
                    threads.append(text[:80])
            for item in snapshot.latent_threads or []:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("context_snapshot") or item.get("summary") or "").strip()
                if text and text not in seen:
                    seen.add(text)
                    threads.append(text[:80])
            if len(threads) >= 3:
                break
        return threads[:3]

    def _snapshot_narrative_history(self, snapshots: list[AuroraStateSnapshot]) -> list[str]:
        history: list[str] = []
        for snapshot in snapshots:
            metadata = dict(snapshot.runtime_metadata or {})
            narrative = str(metadata.get("opening") or metadata.get("narrative") or "").strip()
            if narrative:
                history.append(narrative)
        return history

    def _unclosed_questions(self, recent_messages: list[dict[str, Any]]) -> list[str]:
        questions: list[str] = []
        for message in reversed(recent_messages):
            if str(message.get("role") or "").lower() != "assistant":
                continue
            for fragment in self._question_fragments(str(message.get("content") or "")):
                if fragment not in questions:
                    questions.append(fragment)
                if len(questions) >= 3:
                    return questions
        return questions

    @staticmethod
    def _question_fragments(text: str) -> list[str]:
        normalized = " ".join(str(text or "").split())
        if not normalized:
            return []
        fragments: list[str] = []
        for marker in ("？", "?"):
            parts = normalized.split(marker)
            running = ""
            for part in parts[:-1]:
                running = f"{running}{part}".strip()
                if not running:
                    continue
                fragments.append(f"{running[-80:]}{marker}")
                running = ""
        return fragments

    def _progress_facts(self, checkpoint_state: dict[str, Any]) -> list[str]:
        completion = checkpoint_state.get("completion_percent")
        expected = checkpoint_state.get("expected_completion_percent")
        completed_tasks = checkpoint_state.get("completed_tasks")
        total_tasks = checkpoint_state.get("total_tasks")
        facts = []
        if completed_tasks is not None and total_tasks:
            facts.append(f"完成了 {completed_tasks}/{total_tasks} 个任务")
        if completion is not None and expected is not None:
            facts.append(f"当前完成率 {completion}%，原本预期 {expected}%")
        lagging = checkpoint_state.get("specific_lagging_domain")
        if lagging:
            facts.append(f"最需要留意的是「{lagging}」")
        if checkpoint_state.get("status") == "on_track":
            facts.append("整体节奏还在可控范围内")
        return facts[:4]

    def _checkpoint_question_plan(
        self,
        *,
        checkpoint_state: dict[str, Any],
        open_threads: list[str],
        unclosed_questions: list[str],
    ) -> list[CheckpointQuestion]:
        questions: list[CheckpointQuestion] = []
        status = str(checkpoint_state.get("status") or "")
        lagging_domain = str(checkpoint_state.get("specific_lagging_domain") or "").strip()
        completion = float(checkpoint_state.get("completion_rate") or 0.0)
        expected = float(checkpoint_state.get("expected_completion_rate") or 0.0)

        if unclosed_questions:
            questions.append(
                CheckpointQuestion(
                    question_id="previous-question",
                    focus="continuity",
                    question=f"上次我问到「{unclosed_questions[0]}」，后来你实际试了一下吗？",
                    reason="这个答案能判断上个 checkpoint 是已经闭合，还是只是进度没有同步。",
                )
            )
        elif open_threads:
            questions.append(
                CheckpointQuestion(
                    question_id="open-thread",
                    focus="continuity",
                    question=f"上次留下的「{open_threads[0]}」，现在更像解决了、还卡着，还是暂时不重要了？",
                    reason="先处理未闭合线索，后面的调整才不会像重新开一段模板复盘。",
                )
            )

        if status == "behind" or lagging_domain:
            domain_text = f"「{lagging_domain}」" if lagging_domain else "这块落后的内容"
            questions.append(
                CheckpointQuestion(
                    question_id="lagging-cause",
                    focus="bottleneck",
                    question=f"现在最该先修的是 {domain_text} 的理解、做题手感，还是时间安排？",
                    reason="不同原因对应不同下一步：补概念、换练法、或收紧任务密度。",
                )
            )

        if expected - completion >= 0.18:
            questions.append(
                CheckpointQuestion(
                    question_id="minimum-viable-next-step",
                    focus="next_step",
                    question="如果今天只保留一个最小补救动作，你愿意把它放在什么时候、做多大？",
                    reason="差距已经足够影响计划，先确定一个能落地的最小动作比完整重排更稳。",
                )
            )
        elif not questions:
            questions.append(
                CheckpointQuestion(
                    question_id="keep-or-adjust",
                    focus="next_step",
                    question="接下来一天你想保持原节奏，还是把某一块稍微调轻一点？",
                    reason="进度可控时只需要确认微调，不需要把复盘扩成新的负担。",
                )
            )

        deduped: list[CheckpointQuestion] = []
        seen_focus: set[str] = set()
        for question in questions:
            key = question.question
            if key in seen_focus:
                continue
            seen_focus.add(key)
            deduped.append(question)
            if len(deduped) >= 3:
                break
        return deduped or [
            CheckpointQuestion(
                question_id="checkpoint-pulse",
                focus="next_step",
                question="这个 checkpoint 之后，下一步你最想让我帮你收紧哪一点？",
                reason="至少确认一个具体方向，Aurora 才能把后续陪跑接到真实进展上。",
            )
        ]

    def _checkpoint_opening(
        self,
        *,
        plan: Plan,
        checkpoint_day: int,
        checkpoint_description: str,
        previous_summary: str,
        open_threads: list[str],
        unclosed_questions: list[str],
        progress_facts: list[str],
        previous_openings: list[str],
    ) -> tuple[str, str]:
        fact_text = "；".join(progress_facts) or "我先看这次 checkpoint 的真实进展"
        if previous_summary:
            drafts = [
                (
                    "continuity",
                    f"接着上次的线索来：{previous_summary}。这次到「{plan.name}」第 {checkpoint_day} 天，{fact_text}。",
                ),
                (
                    "progress_delta",
                    f"这次不从模板开场，先看变化：{fact_text}。上次留下的背景是：{previous_summary}。",
                ),
            ]
        elif unclosed_questions:
            drafts = [
                (
                    "unclosed_question",
                    f"我先接住上次没收口的问题：{unclosed_questions[0]} 现在来到第 {checkpoint_day} 天，{fact_text}。",
                ),
                (
                    "progress_delta",
                    f"先不重新盘一遍，我们直接看这次 checkpoint 的新信号：{fact_text}。",
                ),
            ]
        elif open_threads:
            drafts = [
                (
                    "open_thread",
                    f"上次还挂着「{open_threads[0]}」，这次先拿它对照真实进度：{fact_text}。",
                ),
                (
                    "progress_delta",
                    f"这轮我换个角度看 checkpoint：不是问一套固定问题，而是先看 {fact_text}。",
                ),
            ]
        else:
            description = f"「{checkpoint_description}」" if checkpoint_description else "这个检查点"
            drafts = [
                (
                    "progress_delta",
                    f"到了「{plan.name}」第 {checkpoint_day} 天的 {description}，我先看真实进展：{fact_text}。",
                ),
                (
                    "minimal_debrief",
                    f"这个 checkpoint 我们不做长复盘，先抓会改变下一步的事实：{fact_text}。",
                ),
            ]

        for variant, draft in drafts:
            if not self._too_similar_to_history(draft, previous_openings):
                return draft, variant
        variant, draft = drafts[-1]
        return f"{draft} 这次我会换一个聚焦点，只问最必要的部分。", f"{variant}_deduped"

    @staticmethod
    def _too_similar_to_history(draft: str, history: list[str], *, threshold: float = 0.7) -> bool:
        normalized_draft = " ".join(str(draft or "").split())
        if not normalized_draft:
            return False
        for item in history[-12:]:
            normalized_item = " ".join(str(item or "").split())
            if not normalized_item:
                continue
            if SequenceMatcher(None, normalized_draft, normalized_item).ratio() > threshold:
                return True
        return False

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
    """Small Redis-backed checkpoint debrief flow."""

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
            planned_question = self._planned_question_at(state, 0)
            if planned_question:
                state["question_index"] = 0
                state["current_question_id"] = planned_question.get("question_id")
                await self._save_session(state)
                return {
                    "message": self._format_planned_question(planned_question),
                    "is_debrief": True,
                    "finished": False,
                    "state": state,
                    "question_reason": planned_question.get("reason"),
                }
            return {
                "message": "这个检查点的情况怎么样？",
                "is_debrief": True,
                "finished": False,
                "state": state,
            }

        active = await self._get_active_session(session_uuid)
        if not active:
            return None

        if active.get("question_plan"):
            return await self._process_planned_turn(
                active=active,
                user_id=user_id,
                session_uuid=session_uuid,
                user_message=user_message,
            )

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

    async def _process_planned_turn(
        self,
        *,
        active: dict[str, Any],
        user_id: UUID,
        session_uuid: UUID,
        user_message: str,
    ) -> dict[str, Any]:
        answers = list(active.get("answers") or [])
        answers.append(
            {
                "question_id": str(active.get("current_question_id") or ""),
                "answer": user_message,
            }
        )
        active["answers"] = answers
        active["progress_good"] = bool(active.get("progress_good", True)) and self._goal_met_from_text(user_message)

        next_index = int(active.get("question_index") or 0) + 1
        next_question = self._planned_question_at(active, next_index)
        if next_question:
            active["question_index"] = next_index
            active["assistant_round"] = next_index + 1
            active["current_question_id"] = next_question.get("question_id")
            await self._save_session(active)
            return {
                "message": self._format_planned_question(next_question),
                "is_debrief": True,
                "finished": False,
                "state": active,
                "question_reason": next_question.get("reason"),
            }

        return await self._finish_planned_session(
            active=active,
            user_id=user_id,
            session_uuid=session_uuid,
        )

    async def _finish_planned_session(
        self,
        *,
        active: dict[str, Any],
        user_id: UUID,
        session_uuid: UUID,
    ) -> dict[str, Any]:
        answers = [
            str(item.get("answer") or "").strip()
            for item in list(active.get("answers") or [])
            if isinstance(item, dict) and str(item.get("answer") or "").strip()
        ]
        first_answer = answers[0] if answers else ""
        second_answer = "。".join(answers[1:]) if len(answers) > 1 else first_answer
        goal_met = bool(active.get("progress_good", True))
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
                    "first_answer": first_answer,
                    "second_answer": second_answer,
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
                first_answer=first_answer,
                second_answer=second_answer,
                goal_met=goal_met,
            )
        except Exception as exc:
            logger.warning(f"Aurora checkpoint runtime finalize failed session={session_uuid}: {exc}")
        await self._clear_session(active)
        if goal_met:
            message = "这个 checkpoint 先算闭合。后面我会按你刚确认的节奏继续接住。"
        elif adjustment:
            message = "我按这次真实偏差收紧一下后续节奏，已经在下一阶段前插入一个「复盘补强」任务。"
        else:
            message = "我先记录这次偏差，后续任务暂时不打乱；下一步只盯最影响进度的那一小块。"
        return {
            "message": message,
            "is_debrief": True,
            "finished": True,
            "goal_met": goal_met,
            "adjustment": adjustment,
            "aurora_runtime": aurora_runtime,
            "answers": answers,
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
            "opening_summary": str(debrief_context.get("opening_summary") or ""),
            "question_plan": self._normalize_question_plan(debrief_context.get("question_plan")),
            "previous_runtime_state_summary": str(debrief_context.get("previous_runtime_state_summary") or ""),
            "open_threads": [
                str(item).strip() for item in list(debrief_context.get("open_threads") or []) if str(item).strip()
            ][:3],
            "progress_facts": [
                str(item).strip() for item in list(debrief_context.get("progress_facts") or []) if str(item).strip()
            ][:4],
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

    def _normalize_question_plan(self, raw: Any) -> list[dict[str, str]]:
        if not isinstance(raw, list):
            return []
        questions: list[dict[str, str]] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            question = str(item.get("question") or "").strip()
            reason = str(item.get("reason") or "").strip()
            if not question or not reason:
                continue
            questions.append(
                {
                    "question_id": str(item.get("question_id") or f"question-{index + 1}").strip(),
                    "focus": str(item.get("focus") or "checkpoint").strip(),
                    "question": question,
                    "reason": reason,
                }
            )
            if len(questions) >= 3:
                break
        return questions

    @staticmethod
    def _planned_question_at(state: dict[str, Any], index: int) -> dict[str, str] | None:
        plan = state.get("question_plan")
        if not isinstance(plan, list) or index < 0 or index >= len(plan):
            return None
        item = plan[index]
        return item if isinstance(item, dict) else None

    @staticmethod
    def _format_planned_question(question: dict[str, str]) -> str:
        prompt = str(question.get("question") or "").strip()
        reason = str(question.get("reason") or "").strip()
        if not reason:
            return prompt
        return f"{prompt}\n\n我问这个是因为：{reason}"

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
