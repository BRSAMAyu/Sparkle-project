from __future__ import annotations

import math
import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.agents.reflection_agent import TriggeredReflectionResult, get_reflection_agent
from app.config import settings
from app.core.event_bus import event_bus
from app.core.metrics import get_or_create_metric
from app.event_publishers.srl_events import publish_srl_event
from app.models.galaxy import KnowledgeNode
from app.models.task import Task
from app.models.task_feedback import TaskFeedback, TaskFeedbackCategory
from app.models.task_resources import TaskKnowledgeLink
from app.models.user_preferences import UserPreferencesCenter
from app.services.aurora_stage25_reflection_kill_switch_service import AuroraStage25ReflectionKillSwitchService
from app.services.cognitive_service import CognitiveService
from app.services.memory_inferred_write_lane import InferredEpisodicCandidate, MemoryInferredWriteLaneService
from app.services.memory_service import MemoryService
from app.services.route_history_service import RouteHistoryService
from app.services.rule_y_adapter import RuleYAdapter
from app.services.srl_phase_traits import derive_reflection_prompt_style
from app.services.system_update_service import SystemUpdateService, build_system_update


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


REFLECTION_TRIGGER_FIRED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_reflection_trigger_fired_total",
    "Total reflection triggers by category and mode",
    ["category", "mode", "status"],
)
REFLECTION_CONTEXT_INJECTED_TOKENS = get_or_create_metric(
    Histogram,
    "sparkle_reflection_context_injected_tokens",
    "Injected reflection context token count",
    ["category"],
    buckets=[32, 64, 128, 256, 400, 600, 800],
)
REFLECTION_CONTEXT_TRUNCATED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_reflection_context_truncated_total",
    "Reflection context truncation events",
    ["category"],
)
REFLECTION_RULE_Y_PASS_RATE = get_or_create_metric(
    Gauge,
    "sparkle_reflection_rule_y_pass_rate",
    "Latest Rule Y pass rate for reflection writes",
    ["category"],
)
REFLECTION_LLM_LATENCY = get_or_create_metric(
    Histogram,
    "sparkle_reflection_llm_latency_seconds",
    "Reflection LLM latency in seconds",
    ["category"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0],
)
REFLECTION_LLM_COST = get_or_create_metric(
    Counter,
    "sparkle_reflection_llm_cost_usd_total",
    "Estimated reflection LLM cost in USD",
    ["category"],
)
REFLECTION_SKIPPED_TOTAL = get_or_create_metric(
    Counter,
    "sparkle_reflection_skipped_total",
    "Reflection executions skipped by reason",
    ["category", "reason"],
)


class TaskReflectionService:
    """Generate lightweight reflection prompts and persist reflection answers."""

    PLAN_COOLDOWN = timedelta(hours=24)
    TRIGGER_COOLDOWN = timedelta(hours=24)
    ELIGIBLE_CATEGORIES = {
        TaskFeedbackCategory.TOO_DIFFICULT.value,
        TaskFeedbackCategory.UNCLEAR.value,
        "abandoned",
        "intervention_ineffective",
        "plan_stall",
        "overload",
        "plan_completed",
        "milestone_reached",
    }
    PROMPT_TEMPLATES = {
        TaskFeedbackCategory.TOO_DIFFICULT.value: {
            "question": "你觉得难在哪里？是概念没理解、题量太大、还是注意力不够集中？",
            "options": ["概念没理解", "题量太大", "注意力不够集中"],
        },
        TaskFeedbackCategory.UNCLEAR.value: {
            "question": "是任务描述不清楚，还是你不确定从哪里开始？",
            "options": ["任务描述不清楚", "不知道从哪里开始", "缺少示例"],
        },
        "abandoned": {
            "question": "是这个任务不重要了，还是遇到了阻力让你暂时放下？",
            "options": ["任务已经不重要", "遇到了阻力", "时间安排冲突"],
        },
        "intervention_ineffective": {
            "question": "建议已经给到，但结果还是没转好。你感觉真正卡住你的是什么？",
            "options": ["建议太重了", "建议不贴合当前情况", "知道该做但还是起不来"],
        },
        "plan_stall": {
            "question": "这段时间计划停住了，更像是哪一种情况？",
            "options": ["步骤太大不好开始", "节奏太密跟不上", "优先级一直被打断"],
        },
        "overload": {
            "question": "同一天连续失败或取消，最像是哪种过载？",
            "options": ["任务堆得太满", "精力撑不住", "时间被切得太碎"],
        },
        "plan_completed": {
            "question": "计划完成了，回顾一下，这次最有价值的收获是什么？",
            "options": ["找到了有效的学习方法", "执行力比预期好", "目标拆解得很合理"],
        },
        "milestone_reached": {
            "question": "你刚达成一个里程碑，是什么让你这次能稳定推进？",
            "options": ["节奏把控得好", "方法找对了", "坚持了计划"],
        },
    }
    TRIGGER_PROMPT_VERSIONS = {
        TaskFeedbackCategory.TOO_DIFFICULT.value: "v1",
        TaskFeedbackCategory.UNCLEAR.value: "v1",
        "abandoned": "v1",
        "intervention_ineffective": "v1",
        "plan_stall": "v1",
        "overload": "v1",
        "plan_completed": "v1",
        "milestone_reached": "v1",
    }

    def __init__(self, db: AsyncSession, redis=None):
        self.db = db
        self.redis = redis
        self.system_updates = SystemUpdateService(redis)
        self.kill_switch = AuroraStage25ReflectionKillSwitchService()

    async def maybe_enqueue_reflection_prompt(
        self,
        *,
        user_id: UUID,
        task: Task,
        feedback: TaskFeedback | None,
        category: str | None,
        time_spent_minutes: int | None,
    ) -> dict[str, object] | None:
        normalized = str(category or "").strip().lower()
        if normalized not in self.ELIGIBLE_CATEGORIES:
            return None
        if not await self._is_trigger_enabled(normalized):
            return None
        if (time_spent_minutes or 0) <= 10:
            return None
        if not task.plan_id:
            return None
        if await self._on_cooldown(user_id=user_id, plan_id=task.plan_id):
            return None

        prompt = await self._build_prompt(
            category=normalized,
            task_id=task.id,
            plan_id=task.plan_id,
            feedback_id=getattr(feedback, "id", None),
            user_id=user_id,
            task_title=task.title,
        )
        try:
            await self.system_updates.enqueue(
                user_id,
                build_system_update(
                    update_type="reflection_prompt",
                    category="reflection",
                    title="想更精准地帮你调整一下",
                    description=prompt["question"],
                    priority="medium",
                    metadata={
                        "widget_type": "reflection_card",
                        "reflection_prompt": prompt,
                    },
                ),
            )
            await self._mark_prompted(user_id=user_id, plan_id=task.plan_id)
        except Exception as exc:
            logger.warning(f"Failed to enqueue reflection prompt: {exc}")
        return prompt

    async def create_abandon_feedback_and_prompt(
        self,
        *,
        user_id: UUID,
        task: Task,
        reason: str | None,
        time_spent_minutes: int | None,
    ) -> tuple[TaskFeedback, dict[str, object] | None]:
        result = await self.db.execute(
            select(TaskFeedback).where(
                TaskFeedback.user_id == user_id,
                TaskFeedback.task_id == task.id,
            )
        )
        feedback = result.scalar_one_or_none()
        if feedback is None:
            feedback = TaskFeedback(
                user_id=user_id,
                task_id=task.id,
                feedback_text=reason,
                category="abandoned",
                task_difficulty_snapshot=task.difficulty,
                task_type_snapshot=task.type.value if task.type else None,
                actual_minutes_snapshot=time_spent_minutes,
            )
            self.db.add(feedback)
            await self.db.flush()
        prompt = await self.maybe_enqueue_reflection_prompt(
            user_id=user_id,
            task=task,
            feedback=feedback,
            category="abandoned",
            time_spent_minutes=time_spent_minutes,
        )
        return feedback, prompt

    async def handle_triggered_reflection(
        self,
        *,
        user_id: UUID,
        category: str,
        trigger_payload: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = str(category or "").strip().lower()
        if normalized not in self.ELIGIBLE_CATEGORIES:
            raise ValueError(f"Unsupported reflection trigger category: {category}")
        if not await self._is_trigger_enabled(normalized):
            REFLECTION_SKIPPED_TOTAL.labels(category=normalized, reason="category_disabled").inc()
            return {"status": "skipped", "reason": "category_disabled", "category": normalized}
        if await self._trigger_on_cooldown(user_id=user_id, category=normalized):
            REFLECTION_SKIPPED_TOTAL.labels(category=normalized, reason="cooldown").inc()
            return {"status": "skipped", "reason": "cooldown", "category": normalized}

        mode = await self.kill_switch.get_mode()
        if mode == "off":
            REFLECTION_SKIPPED_TOTAL.labels(category=normalized, reason="off").inc()
            return {"status": "skipped", "reason": "off", "category": normalized}

        reflection_context = await self._build_reflection_context(
            user_id=user_id,
            trigger=normalized,
            trigger_payload=trigger_payload,
        )
        reflector = get_reflection_agent()
        reflection = await reflector.reflect(
            user_id=str(user_id),
            trigger_category=normalized,
            trigger_payload=trigger_payload,
            context=reflection_context,
        )
        assert isinstance(reflection, TriggeredReflectionResult)

        REFLECTION_TRIGGER_FIRED_TOTAL.labels(category=normalized, mode=mode, status="generated").inc()
        REFLECTION_CONTEXT_INJECTED_TOKENS.labels(category=normalized).observe(reflection.context_tokens)
        if reflection.context_truncated:
            REFLECTION_CONTEXT_TRUNCATED_TOTAL.labels(category=normalized).inc()
        REFLECTION_LLM_LATENCY.labels(category=normalized).observe(reflection.llm_latency_ms / 1000.0)
        REFLECTION_LLM_COST.labels(category=normalized).inc(reflection.estimated_cost_usd)

        result: dict[str, Any] = {
            "status": "shadowed" if mode == "shadow" else "generated",
            "category": normalized,
            "mode": mode,
            "reflection_id": reflection.reflection_id,
            "summary": reflection.summary,
            "confidence": reflection.confidence,
            "reasoning": reflection.reasoning,
            "evidence": reflection.evidence,
            "context_tokens": reflection.context_tokens,
            "context_truncated": reflection.context_truncated,
            "llm_latency_ms": reflection.llm_latency_ms,
            "estimated_cost_usd": reflection.estimated_cost_usd,
        }

        candidate = self._build_rule_y_candidate(
            user_id=user_id,
            category=normalized,
            reflection=reflection,
            trigger_payload=trigger_payload,
        )
        validated = RuleYAdapter.validate(candidate)
        pass_rate = 1.0 if validated is not None else 0.0
        REFLECTION_RULE_Y_PASS_RATE.labels(category=normalized).set(pass_rate)
        effective_mode = await self.kill_switch.record_rule_y_pass_rate(pass_rate)
        result["rule_y_pass_rate"] = pass_rate
        result["effective_mode"] = effective_mode

        if validated is None:
            REFLECTION_TRIGGER_FIRED_TOTAL.labels(category=normalized, mode=mode, status="rule_y_failed").inc()
            result["status"] = "blocked"
            result["reason"] = "rule_y_failed"
            return result

        if mode == "shadow" or effective_mode != "live":
            await self._mark_triggered(user_id=user_id, category=normalized)
            if effective_mode != "live":
                result["status"] = "shadowed"
                result["reason"] = "auto_degraded"
            return result

        lane = MemoryInferredWriteLaneService(self.db)
        record = await lane.write_candidate_to_l1(
            user_id=user_id,
            session_id=uuid.uuid4(),
            candidate=validated,
            force_write=True,
            source_type="reflection",
            extra_tags=[
                "stage25:reflection",
                f"reflection_category:{normalized}",
                "user_correction_eligible:true",
            ],
        )
        await self._mark_triggered(user_id=user_id, category=normalized)
        if record is None:
            REFLECTION_TRIGGER_FIRED_TOTAL.labels(category=normalized, mode=mode, status="write_blocked").inc()
            result["status"] = "blocked"
            result["reason"] = "write_blocked"
            return result

        REFLECTION_TRIGGER_FIRED_TOTAL.labels(category=normalized, mode=mode, status="written").inc()
        result["status"] = "written"
        result["memory_id"] = str(record.id)
        await event_bus.publish(
            "reflection.generated",
            {
                "event_type": "reflection.generated",
                "user_id": str(user_id),
                "category": normalized,
                "reflection_id": reflection.reflection_id,
                "memory_id": str(record.id),
                "mode": mode,
                "timestamp": _utcnow().isoformat(),
            },
        )
        return result

    async def submit_reflection_answer(
        self,
        *,
        user_id: UUID,
        feedback_id: UUID,
        selected_option: str | None,
        free_text: str | None,
        stuck_point: str | None = None,
        effective_method: str | None = None,
        adjustment_intention: str | None = None,
    ) -> dict[str, object]:
        result = await self.db.execute(
            select(TaskFeedback, Task)
            .join(Task, Task.id == TaskFeedback.task_id)
            .where(
                TaskFeedback.id == feedback_id,
                TaskFeedback.user_id == user_id,
            )
        )
        row = result.one_or_none()
        if row is None:
            raise ValueError("Feedback not found")
        feedback, task = row

        prompt = await self._build_prompt(
            category=str(feedback.category or "").strip().lower() or "abandoned",
            task_id=task.id,
            plan_id=task.plan_id,
            feedback_id=feedback.id,
            user_id=user_id,
            task_title=task.title,
        )
        structured = self._normalize_structured_reflection(
            selected_option=selected_option,
            free_text=free_text,
            stuck_point=stuck_point,
            effective_method=effective_method,
            adjustment_intention=adjustment_intention,
        )
        recent_reflections = await self._load_recent_reflection_memories(user_id=user_id, feedback_id=feedback.id)
        linked_nodes = await self._resolve_reflection_knowledge_nodes(
            user_id=user_id,
            task=task,
            stuck_point=structured["stuck_point"],
        )
        await self._persist_reflection_node_links(
            task=task,
            linked_nodes=linked_nodes,
            stuck_point=structured["stuck_point"],
        )
        ai_response = self._build_connection_response(
            task=task,
            structured=structured,
            linked_nodes=linked_nodes,
            recent_reflections=recent_reflections,
        )
        payload = {
            "prompt": prompt,
            "selected_option": (selected_option or "").strip() or None,
            "free_text": (free_text or "").strip() or None,
            "stuck_point": structured["stuck_point"],
            "effective_method": structured["effective_method"],
            "adjustment_intention": structured["adjustment_intention"],
            "linked_knowledge_nodes": linked_nodes,
            "ai_response": ai_response,
            "submitted_at": _utcnow().isoformat(),
            "status": "completed",
        }
        feedback.reflection_payload = payload
        await self.db.flush()

        fragment_parts = [
            f"任务《{task.title}》的反思反馈：",
            prompt["question"],
        ]
        if payload["selected_option"]:
            fragment_parts.append(f"用户选择：{payload['selected_option']}")
        if payload["free_text"]:
            fragment_parts.append(f"补充说明：{payload['free_text']}")
        if structured["stuck_point"]:
            fragment_parts.append(f"卡点：{structured['stuck_point']}")
        if structured["effective_method"]:
            fragment_parts.append(f"有效方法：{structured['effective_method']}")
        if structured["adjustment_intention"]:
            fragment_parts.append(f"下次调整：{structured['adjustment_intention']}")

        cognitive_service = CognitiveService(self.db)
        fragment = await cognitive_service.create_fragment(
            user_id=user_id,
            content=" ".join(fragment_parts),
            source_type="reflection_auto",
            context_tags={
                "task_id": str(task.id),
                "plan_id": str(task.plan_id) if task.plan_id else "",
                "feedback_id": str(feedback.id),
                "selected_option": payload["selected_option"],
                "stuck_point": structured["stuck_point"],
                "effective_method": structured["effective_method"],
                "adjustment_intention": structured["adjustment_intention"],
                "linked_knowledge_node_ids": [item["id"] for item in linked_nodes],
                "reflection_category": str(feedback.category or ""),
            },
            error_tags=[f"reflection.{str(feedback.category or 'unknown')}"],
            severity=2,
            task_id=task.id,
            source_event_id=f"reflection_auto:{feedback.id}",
        )
        await cognitive_service.analyze_behavior(user_id, fragment.id)
        memory = await self._write_structured_reflection_memory(
            user_id=user_id,
            task=task,
            feedback=feedback,
            structured=structured,
            linked_nodes=linked_nodes,
            ai_response=ai_response,
        )
        if memory is not None:
            payload["memory_id"] = str(memory.id)
            feedback.reflection_payload = dict(payload)
            flag_modified(feedback, "reflection_payload")
            await self.db.flush()

        if task.plan_id:
            try:
                from app.services.card_protocol.main_chain_artifact_service import MainChainArtifactService

                artifact_service = MainChainArtifactService(self.db)
                await artifact_service.refresh_for_legacy_plan(
                    legacy_plan_id=task.plan_id,
                    generated_reason="task_reflection_submitted",
                    include_reflection=True,
                    linked_feedback_id=str(feedback.id),
                )
            except Exception as exc:
                logger.warning(f"Failed to refresh Phase4 reflection report: {exc}")
        from app.core.event_bus import ReflectionCompletedEvent

        reflection_event = ReflectionCompletedEvent(
            user_id=str(user_id),
            feedback_id=str(feedback.id),
            task_id=str(task.id),
            plan_id=str(task.plan_id) if task.plan_id else None,
        )
        await event_bus.publish("reflection.completed", reflection_event.to_dict())
        await publish_srl_event(
            user_id=user_id,
            trigger_event_type="reflection.completed",
            evidence_id=str(feedback.id),
            metadata={"plan_id": str(task.plan_id) if task.plan_id else None},
        )
        return payload

    async def _build_prompt(
        self,
        *,
        category: str,
        task_id: UUID,
        plan_id: UUID | None,
        feedback_id: UUID | None,
        user_id: UUID | None = None,
        task_title: str,
    ) -> dict[str, object]:
        template = self.PROMPT_TEMPLATES.get(category) or self.PROMPT_TEMPLATES["abandoned"]
        reflection_prompt_style = await self._get_reflection_prompt_style(user_id) if user_id else "default"
        question = str(template["question"])
        options = list(template["options"])
        if reflection_prompt_style == "alternative_exploration":
            question = f"{question} 也可以顺手看看有没有另一条更顺的做法。"
            options = [*options, "换个做法试试"]
        elif reflection_prompt_style == "single_path_deepening":
            question = f"{question} 我们先沿着一条最稳的路径往下拆。"
        return {
            "task_id": str(task_id),
            "plan_id": str(plan_id) if plan_id else "",
            "feedback_id": str(feedback_id) if feedback_id else "",
            "task_title": task_title,
            "category": category,
            "question": "把这次任务变成下次更会做的线索：先抓住 3 个具体点。",
            "options": options,
            "legacy_question": question,
            "fields": [
                {
                    "key": "stuck_point",
                    "label": "这个任务中你卡在哪里了？",
                    "hint": "例如：热力学公式看得懂，但不知道什么时候套用",
                    "required": True,
                },
                {
                    "key": "effective_method",
                    "label": "哪个方法让你觉得有进展？",
                    "hint": "例如：先画能量流向图，再列方程",
                    "required": False,
                },
                {
                    "key": "adjustment_intention",
                    "label": "下次会换什么做法？",
                    "hint": "例如：先做 1 道代表题，再进入整组练习",
                    "required": False,
                },
            ],
            "reflection_prompt_style": reflection_prompt_style,
        }

    def _normalize_structured_reflection(
        self,
        *,
        selected_option: str | None,
        free_text: str | None,
        stuck_point: str | None,
        effective_method: str | None,
        adjustment_intention: str | None,
    ) -> dict[str, str | None]:
        selected = (selected_option or "").strip()
        free = (free_text or "").strip()
        stuck = (stuck_point or "").strip()
        method = (effective_method or "").strip()
        adjustment = (adjustment_intention or "").strip()
        if not stuck:
            if selected and free:
                stuck = f"{selected}：{free}"
            else:
                stuck = selected or free
        return {
            "stuck_point": stuck or None,
            "effective_method": method or None,
            "adjustment_intention": adjustment or None,
        }

    async def _load_recent_reflection_memories(
        self,
        *,
        user_id: UUID,
        feedback_id: UUID,
    ) -> list[dict[str, Any]]:
        try:
            rows = await MemoryService(self.db).list_recent_episodic(user_id, limit=8)
        except Exception as exc:
            logger.warning(f"Failed to load recent reflection memories: {exc}")
            return []
        current_source_id = str(feedback_id)
        memories: list[dict[str, Any]] = []
        for row in rows:
            if str(getattr(row, "source_type", "") or "") != "reflection":
                continue
            if str(getattr(row, "source_id", "") or "") == current_source_id:
                continue
            summary = str(getattr(row, "summary", "") or "").strip()
            if summary:
                memories.append(
                    {
                        "id": str(row.id),
                        "summary": summary,
                        "occurred_at": row.occurred_at.isoformat() if row.occurred_at else None,
                    }
                )
            if len(memories) >= 3:
                break
        return memories

    async def _resolve_reflection_knowledge_nodes(
        self,
        *,
        user_id: UUID,
        task: Task,
        stuck_point: str | None,
    ) -> list[dict[str, Any]]:
        haystack = f"{task.title or ''} {stuck_point or ''} {' '.join(str(tag) for tag in (task.tags or []))}".strip()
        nodes_by_id: dict[str, dict[str, Any]] = {}

        if task.knowledge_node_id:
            node = await self.db.get(KnowledgeNode, task.knowledge_node_id)
            if node is not None:
                nodes_by_id[str(node.id)] = self._serialize_reflection_node(
                    node,
                    source="task_primary",
                    confidence=0.95,
                )

        link_result = await self.db.execute(
            select(TaskKnowledgeLink, KnowledgeNode)
            .join(KnowledgeNode, TaskKnowledgeLink.knowledge_node_id == KnowledgeNode.id)
            .where(TaskKnowledgeLink.task_id == task.id)
            .order_by(TaskKnowledgeLink.is_primary.desc(), TaskKnowledgeLink.order_index.asc())
        )
        for link, node in link_result.all():
            node_id = str(node.id)
            nodes_by_id.setdefault(
                node_id,
                self._serialize_reflection_node(
                    node,
                    source="task_link",
                    confidence=float(link.strength or (0.86 if link.is_primary else 0.72)),
                ),
            )

        if haystack:
            try:
                result = await self.db.execute(
                    select(KnowledgeNode)
                    .where(KnowledgeNode.deleted_at.is_(None))
                    .order_by(KnowledgeNode.is_seed.desc(), KnowledgeNode.updated_at.desc())
                    .limit(500)
                )
                for node in result.scalars().all():
                    score = self._score_reflection_node_match(node, haystack)
                    if score < 0.35:
                        continue
                    node_id = str(node.id)
                    existing = nodes_by_id.get(node_id)
                    if existing is None or score > float(existing.get("confidence") or 0.0):
                        nodes_by_id[node_id] = self._serialize_reflection_node(
                            node,
                            source="stuck_point_parse",
                            confidence=score,
                        )
            except Exception as exc:
                logger.warning(f"Failed to parse reflection stuck point into Galaxy nodes: {exc}")

        return sorted(
            nodes_by_id.values(),
            key=lambda item: float(item.get("confidence") or 0.0),
            reverse=True,
        )[:3]

    async def _persist_reflection_node_links(
        self,
        *,
        task: Task,
        linked_nodes: list[dict[str, Any]],
        stuck_point: str | None,
    ) -> None:
        if not linked_nodes:
            return
        for index, item in enumerate(linked_nodes):
            try:
                node_id = UUID(str(item["id"]))
            except (ValueError, KeyError):
                continue
            existing = await self.db.execute(
                select(TaskKnowledgeLink).where(
                    TaskKnowledgeLink.task_id == task.id,
                    TaskKnowledgeLink.knowledge_node_id == node_id,
                )
            )
            link = existing.scalar_one_or_none()
            if link is not None:
                if not link.notes and stuck_point:
                    link.notes = f"reflection_stuck_point: {stuck_point[:180]}"
                continue
            self.db.add(
                TaskKnowledgeLink(
                    task_id=task.id,
                    knowledge_node_id=node_id,
                    relation_type="reflection_stuck_point",
                    strength=float(item.get("confidence") or 0.7),
                    notes=f"reflection_stuck_point: {(stuck_point or '')[:180]}",
                    order_index=100 + index,
                    is_primary=False,
                )
            )
        await self.db.flush()

    async def _write_structured_reflection_memory(
        self,
        *,
        user_id: UUID,
        task: Task,
        feedback: TaskFeedback,
        structured: dict[str, str | None],
        linked_nodes: list[dict[str, Any]],
        ai_response: str,
    ):
        summary = self._build_reflection_memory_summary(
            task=task,
            structured=structured,
            linked_nodes=linked_nodes,
        )
        if not summary:
            return None
        tags = [
            "task_reflection",
            "reflection:structured",
            f"reflection_category:{str(feedback.category or 'unknown')}",
            f"task:{task.id}",
        ]
        tags.extend(f"knowledge_node:{item['id']}" for item in linked_nodes if item.get("id"))
        semantic_seed = f"{user_id}:{task.id}:{structured.get('stuck_point') or ''}:{structured.get('adjustment_intention') or ''}"
        try:
            return await MemoryService(self.db).create_episodic_memory(
                user_id=user_id,
                summary=summary,
                source_type="reflection",
                source_id=str(feedback.id),
                occurred_at=_utcnow(),
                importance_score=0.78,
                tags=tags,
                evidence_refs=[
                    {"type": "task", "id": str(task.id), "schema_version": "task.v1"},
                    {
                        "type": "summary",
                        "id": str(feedback.id),
                        "schema_version": "task_reflection.v1",
                        "stuck_point": structured.get("stuck_point"),
                        "effective_method": structured.get("effective_method"),
                        "adjustment_intention": structured.get("adjustment_intention"),
                        "linked_knowledge_nodes": linked_nodes,
                        "ai_response": ai_response,
                    },
                ],
                confidence=0.88,
                evidence_token=f"task_reflection:{feedback.id}",
                decay_policy="60d",
                source_lane="direct_capture",
                semantic_key=str(uuid.uuid5(uuid.NAMESPACE_URL, semantic_seed)),
                subject_type="reflection",
                mentioned_entity_hash=(
                    uuid.uuid5(uuid.NAMESPACE_URL, str(linked_nodes[0]["id"])).hex
                    if linked_nodes
                    else None
                ),
                mentioned_entity_owner_user_id=user_id if linked_nodes else None,
            )
        except Exception as exc:
            logger.warning(f"Failed to write task reflection memory: {exc}")
            return None

    def _build_connection_response(
        self,
        *,
        task: Task,
        structured: dict[str, str | None],
        linked_nodes: list[dict[str, Any]],
        recent_reflections: list[dict[str, Any]],
    ) -> str:
        stuck = self._compact_text(structured.get("stuck_point") or "这个卡点", limit=42)
        method = self._compact_text(structured.get("effective_method") or "", limit=36)
        adjustment = self._compact_text(structured.get("adjustment_intention") or "", limit=42)
        node_name = self._compact_text(str(linked_nodes[0].get("name") or ""), limit=28) if linked_nodes else ""
        previous = self._compact_text(
            str(recent_reflections[0].get("summary") or "") if recent_reflections else "",
            limit=46,
        )

        if previous and node_name:
            return (
                f"你这次卡在「{stuck}」，我先把它挂到「{node_name}」上；"
                f"它和之前「{previous}」那条反思有相似的阻力，我会在下次对话里带着这条线索接上。"
            )
        if previous:
            return (
                f"你这次提到的「{stuck}」和之前「{previous}」里的阻力有点像；"
                f"我记下来了，下次会先从这个重复卡点切入。"
            )
        if node_name:
            tail = f"下次我会优先按「{adjustment}」帮你接上。" if adjustment else "下次对话我会优先从这个节点接上。"
            return f"你这次卡在「{stuck}」，我把它先挂到「{node_name}」下面；{tail}"
        if method or adjustment:
            method_part = f"，有效推进方式是「{method}」" if method else ""
            next_part = f"；下次先试「{adjustment}」" if adjustment else ""
            return f"你这次的卡点是「{stuck}」{method_part}{next_part}，我会把它作为下次任务前的提醒。"
        return f"你这次的卡点是「{stuck}」，我会把它作为后续对话里需要回到的线索。"

    def _build_reflection_memory_summary(
        self,
        *,
        task: Task,
        structured: dict[str, str | None],
        linked_nodes: list[dict[str, Any]],
    ) -> str:
        parts = [f"任务《{task.title}》反思"]
        if structured.get("stuck_point"):
            parts.append(f"卡点：{structured['stuck_point']}")
        if structured.get("effective_method"):
            parts.append(f"有效方法：{structured['effective_method']}")
        if structured.get("adjustment_intention"):
            parts.append(f"下次调整：{structured['adjustment_intention']}")
        if linked_nodes:
            node_names = "、".join(str(item.get("name") or item.get("id")) for item in linked_nodes[:2])
            parts.append(f"关联节点：{node_names}")
        return "；".join(part for part in parts if part).strip()

    @staticmethod
    def _serialize_reflection_node(
        node: KnowledgeNode,
        *,
        source: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "id": str(node.id),
            "name": str(node.name or "").strip(),
            "source": source,
            "confidence": round(max(0.0, min(float(confidence), 1.0)), 2),
        }

    def _score_reflection_node_match(self, node: KnowledgeNode, haystack: str) -> float:
        lowered = haystack.lower()
        score = 0.0
        name = str(node.name or "").strip()
        if name and name in haystack:
            score = max(score, 0.92)
        if name and haystack in name and len(haystack) >= 3:
            score = max(score, 0.5)
        name_en = str(node.name_en or "").strip().lower()
        if name_en and name_en in lowered:
            score = max(score, 0.84)
        keyword_hits = 0
        for keyword in list(node.keywords or []):
            keyword_text = str(keyword or "").strip()
            if keyword_text and keyword_text.lower() in lowered:
                keyword_hits += 1
        if keyword_hits:
            score = max(score, min(0.85, 0.42 + keyword_hits * 0.14))
        terms = self._reflection_terms(haystack)
        if terms:
            node_text = " ".join(
                [
                    name,
                    str(node.name_en or ""),
                    str(node.description or "")[:300],
                    " ".join(str(keyword or "") for keyword in list(node.keywords or [])),
                ]
            ).lower()
            overlap = sum(1 for term in terms if term.lower() in node_text)
            if overlap:
                score = max(score, min(0.72, 0.25 + overlap * 0.12))
        return score

    @staticmethod
    def _reflection_terms(text: str) -> list[str]:
        raw_terms = re.findall(r"[A-Za-z][A-Za-z0-9_+.-]{2,}|[\u4e00-\u9fff]{2,}", text or "")
        stopwords = {"这个", "任务", "哪里", "下次", "方法", "觉得", "有点", "还是", "不会", "不懂", "卡住"}
        terms: list[str] = []
        for term in raw_terms:
            if term in stopwords or len(term.strip()) < 2:
                continue
            if term not in terms:
                terms.append(term)
        return terms[:12]

    @staticmethod
    def _compact_text(value: str, *, limit: int) -> str:
        text = re.sub(r"\s+", " ", value or "").strip()
        if len(text) <= limit:
            return text
        return f"{text[: limit - 1]}…"

    async def _get_reflection_prompt_style(self, user_id: UUID | None) -> str:
        if user_id is None:
            return "default"
        result = await self.db.execute(
            select(UserPreferencesCenter.traits_prior).where(UserPreferencesCenter.user_id == user_id)
        )
        traits_prior = result.scalar_one_or_none()
        return derive_reflection_prompt_style(dict(traits_prior or {}))

    async def _on_cooldown(self, *, user_id: UUID, plan_id: UUID) -> bool:
        if not self.redis:
            return False
        key = f"reflection_prompt:{user_id}:{plan_id}"
        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

    async def _mark_prompted(self, *, user_id: UUID, plan_id: UUID) -> None:
        if not self.redis:
            return
        key = f"reflection_prompt:{user_id}:{plan_id}"
        try:
            await self.redis.setex(key, int(self.PLAN_COOLDOWN.total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to set reflection cooldown: {exc}")

    async def _build_reflection_context(
        self,
        *,
        user_id: UUID,
        trigger: str,
        trigger_payload: dict[str, Any],
    ) -> dict[str, Any]:
        recent_limit = max(1, min(int(settings.AURORA_REFLECTION_CONTEXT_LIMIT or 20), 20))
        max_tokens = max(1, int(settings.AURORA_REFLECTION_CONTEXT_MAX_TOKENS or 800))
        window_days = max(1, int(trigger_payload.get("window_days") or 14))
        route_history = RouteHistoryService(self.db)
        recent = await route_history.read_recent_decisions(
            user_id=user_id,
            limit=recent_limit,
            since=_utcnow() - timedelta(days=window_days),
        )
        entries = list(recent)
        decision_id = str(trigger_payload.get("decision_id") or "").strip()
        if decision_id:
            try:
                chain = await route_history.read_decision_chain(
                    user_id=user_id,
                    decision_id=UUID(decision_id),
                    depth=int(trigger_payload.get("decision_chain_depth") or 3),
                )
            except ValueError:
                chain = []
            existing_ids = {item.decision_id for item in entries}
            for item in chain:
                if item.decision_id not in existing_ids:
                    entries.append(item)
                    existing_ids.add(item.decision_id)

        entries.sort(key=lambda item: item.decided_at, reverse=True)
        used_tokens = 0
        truncated = False
        lines: list[str] = []
        for item in entries:
            freshness_days = max(0, (_utcnow() - (item.outcome_timestamp or item.decided_at)).days)
            source_confidence = 0.84 if item.outcome else 0.72
            route_mode = str(item.decision_payload.get("route_execution_mode") or item.decision_payload.get("mode") or "n/a")
            outcome = item.outcome or "pending"
            line = (
                f"- [source=route_history; confidence={source_confidence:.2f}; "
                f"freshness={freshness_days}d; user_correction_eligible=true] "
                f"{item.decided_at.isoformat()} | decision={item.decision_type} | "
                f"route={route_mode} | outcome={outcome} | state={item.source_state_v2_key or 'n/a'}"
            )
            line_tokens = self._estimate_tokens(line)
            if not lines and line_tokens > max_tokens:
                line = self._truncate_to_token_budget(line, max_tokens)
                line_tokens = self._estimate_tokens(line)
                truncated = True
            if lines and used_tokens + line_tokens > max_tokens:
                truncated = True
                break
            lines.append(line)
            used_tokens += line_tokens

        if not lines:
            fallback_line = "- [source=route_history; confidence=0.0; freshness=0d; user_correction_eligible=true] no recent decisions found"
            if self._estimate_tokens(fallback_line) > max_tokens:
                fallback_line = self._truncate_to_token_budget(fallback_line, max_tokens)
            lines = [fallback_line]
            used_tokens = self._estimate_tokens(lines[0])

        return {
            "trigger": trigger,
            "route_history_context": "\n".join(lines),
            "route_history_context_tokens": used_tokens,
            "route_history_context_truncated": truncated,
            "route_history_context_entry_count": len(lines),
        }

    def _build_rule_y_candidate(
        self,
        *,
        user_id: UUID,
        category: str,
        reflection: TriggeredReflectionResult,
        trigger_payload: dict[str, Any],
    ) -> InferredEpisodicCandidate:
        evidence_token = f"reflection_trigger:{category}:{reflection.reflection_id}"
        occurred_at = _utcnow()
        confidence = max(float(settings.MEMORY_INFERRED_MIN_CONFIDENCE), float(reflection.confidence or 0.0))
        semantic_seed = f"{user_id}:{category}:{reflection.summary.strip().lower()}"
        return InferredEpisodicCandidate(
            candidate_text=reflection.summary.strip(),
            subject_type="self",
            confidence=round(min(confidence, 0.99), 2),
            evidence_token=evidence_token,
            decay_policy="30d",
            source_lane=MemoryInferredWriteLaneService.SOURCE_LANE,
            semantic_key=str(uuid.uuid5(uuid.NAMESPACE_URL, semantic_seed)),
            evidence_refs=[
                {
                    "type": "summary",
                    "id": reflection.reflection_id,
                    "schema_version": "stage25.rule_y.v1",
                    "source": "route_history",
                    "model_confidence": reflection.confidence,
                    "freshness": "recent_window",
                    "user_correction_eligible": True,
                    "trigger_payload": {key: str(value) for key, value in trigger_payload.items()},
                }
            ],
            occurred_at=occurred_at,
            due_at=None,
            mentioned_entity_hash=None,
            mentioned_entity_owner_user_id=user_id,
        )

    async def _is_trigger_enabled(self, category: str) -> bool:
        return await self.kill_switch.is_trigger_enabled(category)

    async def _trigger_on_cooldown(self, *, user_id: UUID, category: str) -> bool:
        if not self.redis:
            return False
        key = f"reflection_trigger:{user_id}:{category}"
        try:
            return bool(await self.redis.exists(key))
        except Exception:
            return False

    async def _mark_triggered(self, *, user_id: UUID, category: str) -> None:
        if not self.redis:
            return
        key = f"reflection_trigger:{user_id}:{category}"
        try:
            await self.redis.setex(key, int(self.TRIGGER_COOLDOWN.total_seconds()), "1")
        except Exception as exc:
            logger.warning(f"Failed to set reflection trigger cooldown: {exc}")

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, math.ceil(len(text or "") / 4))

    def _truncate_to_token_budget(self, text: str, max_tokens: int) -> str:
        max_chars = max(8, max_tokens * 4)
        if len(text) <= max_chars:
            return text
        return f"{text[: max_chars - 1]}…"
