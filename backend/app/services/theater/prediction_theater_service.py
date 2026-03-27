from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

from sqlalchemy import String, and_, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.exceptions import NotFoundError, SparkleException
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.models.plan import PlanType
from app.models.task import TaskType
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.insight_copy import present_pattern_name
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService
from app.services.llm_fallback_utils import analysis_llm
from app.services.plan_service import PlanService
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.cognitive_service import CognitiveService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.task_service import TaskService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalized_topic_terms(topic: str) -> list[str]:
    normalized = " ".join(topic.strip().lower().split())
    if not normalized:
        return []

    cleaned = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff+#]+", " ", normalized)
    compact = cleaned
    filler_phrases = (
        "帮我",
        "请帮我",
        "我想",
        "想要",
        "想学",
        "学习一下",
        "学习",
        "学会",
        "学",
        "推演一下",
        "推演",
        "模拟一下",
        "模拟",
        "一下",
        "路径",
        "路线",
        "计划",
        "怎么",
        "如何",
        "的",
    )
    for phrase in filler_phrases:
        compact = compact.replace(phrase, " ")

    segmented = re.sub(r"(以及|还有|还有|并且|并|与|和|及|跟|或)", " ", compact)
    tokens = re.findall(r"[a-z0-9+#]+|[\u4e00-\u9fff]{2,}", segmented)
    terms: list[str] = []
    for candidate in [normalized, cleaned, compact, segmented, *tokens]:
        term = " ".join(str(candidate).strip().split())
        if len(term) < 2:
            continue
        if term not in terms:
            terms.append(term)

    alias_expansions = {
        "线性代数": ("特征值", "特征向量", "向量", "矩阵", "线性变换", "特征分解"),
        "微积分": ("导数", "积分", "极限"),
        "概率论与数理统计": ("概率", "统计", "随机变量"),
    }
    for alias, markers in alias_expansions.items():
        if any(marker in compact for marker in markers) and alias not in terms:
            terms.append(alias)
    return terms


class TheaterTimeoutError(SparkleException):
    def __init__(self):
        super().__init__(
            message="这次推演花的时间有点长，我们先停在这里。你可以换个更具体的目标重试，或稍后再试。",
            status_code=504,
            detail={"error_code": "THEATER_TIMEOUT"},
        )


class TheaterNodeAccessError(NotFoundError):
    def __init__(self):
        super().__init__(
            message="未找到可访问的知识节点",
            detail={"error_code": "THEATER_TARGET_NODE_NOT_ACCESSIBLE"},
        )


@dataclass(frozen=True)
class TheaterPathStep:
    index: int
    node_id: str
    node_name: str
    rationale: str
    current_mastery: float
    predicted_mastery: float
    risk_level: str
    estimated_minutes: int
    day_label: str
    checkpoint_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "rationale": self.rationale,
            "current_mastery": round(self.current_mastery, 2),
            "predicted_mastery": round(self.predicted_mastery, 2),
            "risk_level": self.risk_level,
            "estimated_minutes": self.estimated_minutes,
            "day_label": self.day_label,
            "checkpoint_label": self.checkpoint_label,
        }


@dataclass(frozen=True)
class TheaterPathOption:
    id: str
    title: str
    summary: str
    strategy_type: str
    expert_ids: list[str]
    estimated_completion_rate: float
    estimated_mastery: float
    daily_minutes: int
    risks: list[str]
    steps: list[TheaterPathStep]
    route_score: float = 0.0
    checkpoint_days: list[int] | None = None
    week_one_tasks: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "strategy_type": self.strategy_type,
            "expert_ids": self.expert_ids,
            "estimated_completion_rate": round(self.estimated_completion_rate, 4),
            "estimated_mastery": round(self.estimated_mastery, 2),
            "daily_minutes": self.daily_minutes,
            "risks": self.risks,
            "route_score": round(self.route_score, 2),
            "checkpoint_days": list(self.checkpoint_days or []),
            "week_one_tasks": list(self.week_one_tasks or []),
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class TheaterTargetContext:
    name: str
    description: str
    target_node_id: str | None
    resolution_mode: str
    backbone: list[dict[str, Any]]


class PredictionAccuracyTracker:
    PREDICTION_KEY_PREFIX = "theater:prediction:"
    SUMMARY_KEY_PREFIX = "theater:prediction:summary:"
    TTL_SECONDS = 60 * 60 * 24 * 7

    async def record_prediction(self, payload: dict[str, Any]) -> None:
        prediction_id = str(payload.get("prediction_id") or "").strip()
        if not prediction_id:
            return
        await cache_service.set(f"{self.PREDICTION_KEY_PREFIX}{prediction_id}", payload, ttl=self.TTL_SECONDS)

    async def record_actual(
        self,
        prediction_id: str,
        *,
        actual_completion_rate: float,
        actual_mastery: float,
    ) -> dict[str, Any] | None:
        cached = await cache_service.get(f"{self.PREDICTION_KEY_PREFIX}{prediction_id}")
        if not isinstance(cached, dict):
            return None

        predicted = cached.get("selected_prediction") if isinstance(cached.get("selected_prediction"), dict) else {}
        predicted_completion = float(predicted.get("estimated_completion_rate") or 0.0)
        predicted_mastery = float(predicted.get("estimated_mastery") or 0.0)
        completion_error = abs(predicted_completion - actual_completion_rate)
        mastery_error = abs(predicted_mastery - actual_mastery)
        accuracy_score = _clamp(1.0 - ((completion_error * 0.55) + (mastery_error / 100.0 * 0.45)), 0.0, 1.0)

        summary = {
            "prediction_id": prediction_id,
            "predicted_completion_rate": round(predicted_completion, 4),
            "predicted_mastery": round(predicted_mastery, 2),
            "actual_completion_rate": round(actual_completion_rate, 4),
            "actual_mastery": round(actual_mastery, 2),
            "completion_error": round(completion_error, 4),
            "mastery_error": round(mastery_error, 2),
            "accuracy_score": round(accuracy_score, 4),
            "evaluated_at": _utcnow().isoformat(),
        }
        cached["accuracy_summary"] = summary
        await cache_service.set(f"{self.PREDICTION_KEY_PREFIX}{prediction_id}", cached, ttl=self.TTL_SECONDS)
        await cache_service.set(f"{self.SUMMARY_KEY_PREFIX}{prediction_id}", summary, ttl=self.TTL_SECONDS)
        return summary

    async def get_summary(self, prediction_id: str) -> dict[str, Any] | None:
        cached = await cache_service.get(f"{self.SUMMARY_KEY_PREFIX}{prediction_id}")
        return cached if isinstance(cached, dict) else None


class PredictionTheaterService:
    SNAPSHOT_PREFIX = "theater:snapshot:"
    SNAPSHOT_TTL_SECONDS = 60 * 60 * 24 * 7
    MAX_GRAPH_NODES = 12
    PREDICTION_TIMEOUT_SECONDS = 30.0

    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph_reasoning = GraphReasoningService(db)
        self.structure = GraphStructureEvolutionService(db)
        self.accuracy = PredictionAccuracyTracker()

    async def generate_prediction(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None = None,
        horizon_days: int = 14,
        preview_mode: bool = False,
    ) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(
                self._generate_prediction_payload(
                    user_id=user_id,
                    topic=topic,
                    target_node_id=target_node_id,
                    horizon_days=horizon_days,
                    preview_mode=preview_mode,
                ),
                timeout=self.PREDICTION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError as exc:
            raise TheaterTimeoutError() from exc

    async def _generate_prediction_payload(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None = None,
        horizon_days: int = 14,
        preview_mode: bool = False,
    ) -> dict[str, Any]:
        target_context = await self._resolve_target_context(
            user_id=user_id,
            topic=topic,
            target_node_id=target_node_id,
        )
        backbone = list(target_context.backbone)
        if not backbone:
            raise ValueError("Unable to generate a learning backbone for the selected topic")

        mastery_map = await self._get_mastery_map(user_id)
        study_preferences = await self._build_user_learning_profile(user_id)
        pattern_names = await self._top_pattern_names(user_id)
        options = self._build_path_options(
            target_name=target_context.name,
            backbone=backbone,
            mastery_map=mastery_map,
            horizon_days=max(7, min(horizon_days, 30)),
            study_preferences=study_preferences,
            pattern_names=pattern_names,
        )
        selected_prediction = options[0].to_dict() if options else {}
        graph_bundle = {"nodes": [], "edges": []}
        discussion: list[dict[str, Any]] = []
        if not preview_mode:
            graph_bundle = await self._build_graph_bundle(backbone, mastery_map)
            discussion = await self._build_discussion(
                topic=topic,
                target_name=target_context.name,
                options=options,
                graph_bundle=graph_bundle,
                pattern_names=pattern_names,
            )
        generated_at = _utcnow()
        timeline = self._build_timeline(
            options,
            discussion,
            horizon_days=max(7, min(horizon_days, 30)),
        )

        prediction_id = str(uuid4())
        payload = {
            "prediction_id": prediction_id,
            "topic": topic,
            "target_node_id": target_context.target_node_id,
            "target_name": target_context.name,
            "horizon_days": horizon_days,
            "generated_at": generated_at.isoformat(),
            "paths": [option.to_dict() for option in options],
            "discussion_turns": discussion,
            "graph": graph_bundle,
            "timeline": timeline,
            "selected_prediction": selected_prediction,
            "recommended_route_id": options[0].id if options else "",
            "target_resolution_mode": target_context.resolution_mode,
            "accuracy_tracking": self._build_accuracy_tracking(
                prediction_id=prediction_id,
                generated_at=generated_at,
            ),
            "routing_notes": {
                "patterns": pattern_names,
                "recommended_entry": options[0].title if options else "稳扎稳打",
                "target_resolution_mode": target_context.resolution_mode,
            },
            "preview_mode": preview_mode,
        }
        await self.accuracy.record_prediction(payload)
        if not preview_mode:
            query = {"topic": topic}
            if target_context.target_node_id:
                query["target_node_id"] = target_context.target_node_id
            deep_link = f"/theater?{urlencode(query)}"
            await SystemUpdateService().enqueue(
                user_id,
                build_system_update(
                    update_type="theater_prediction_ready",
                    category="learning_insight",
                    title=f"已生成知识推演「{target_context.name}」",
                    description=(
                        f"为“{topic}”生成了 {len(options)} 条可采纳路径，"
                        f"推荐入口是 {options[0].title if options else '稳扎稳打'}。"
                    ),
                    priority="medium",
                    metadata={
                        "prediction_id": prediction_id,
                        "target_node_id": target_context.target_node_id,
                        "target_name": target_context.name,
                        "topic": topic,
                        "title": options[0].title if options else target_context.name,
                        "path_count": len(options),
                        "deep_link": deep_link,
                        "target_resolution_mode": target_context.resolution_mode,
                        "prediction_preview": {
                            "prediction_id": prediction_id,
                            "topic": topic,
                            "target_node_id": target_context.target_node_id,
                            "target_name": target_context.name,
                            "paths": [option.to_dict() for option in options[:3]],
                        },
                    },
                ),
            )
        return payload

    async def _resolve_target_context(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None,
    ) -> TheaterTargetContext:
        if target_node_id is not None:
            target_node = await self._resolve_target_node_for_user(
                user_id=user_id,
                topic=topic,
                target_node_id=target_node_id,
            )
            return await self._build_target_context_from_node(user_id=user_id, target_node=target_node)

        try:
            target_node = await self._resolve_target_node_for_user(
                user_id=user_id,
                topic=topic,
                target_node_id=None,
            )
        except ValueError:
            return await self._build_free_mode_target_context(topic)
        return await self._build_target_context_from_node(user_id=user_id, target_node=target_node)

    async def _build_target_context_from_node(
        self,
        *,
        user_id: UUID,
        target_node: KnowledgeNode,
    ) -> TheaterTargetContext:
        learning_path = await self.graph_reasoning.generate_learning_path(
            user_id,
            target_node.id,
            include_related_suggestions=True,
        )
        backbone = [item for item in learning_path if not item.get("is_optional")]
        if not backbone:
            raise ValueError("Unable to generate a learning backbone for the selected topic")
        return TheaterTargetContext(
            name=str(target_node.name or "当前主题"),
            description=str(target_node.description or ""),
            target_node_id=str(target_node.id),
            resolution_mode="knowledge_graph",
            backbone=backbone,
        )

    async def _build_free_mode_target_context(self, topic: str) -> TheaterTargetContext:
        fallback = self._fallback_free_mode_target(topic)
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with keys target_name, description, prerequisites, milestones. "
                        "This is for a free-mode learning theater when no knowledge graph node is found."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"User topic: {topic}\n"
                        "Extract the most likely learning target, 2-4 prerequisite concepts, and 1-2 milestone outcomes. "
                        "Keep it concrete and beginner-friendly."
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.2,
        )
        parsed = payload if isinstance(payload, dict) else fallback
        target_name = str(parsed.get("target_name") or fallback["target_name"]).strip() or fallback["target_name"]
        description = str(parsed.get("description") or fallback["description"]).strip() or fallback["description"]
        prerequisites = self._coerce_string_list(parsed.get("prerequisites")) or list(fallback["prerequisites"])
        milestones = self._coerce_string_list(parsed.get("milestones")) or list(fallback["milestones"])
        backbone_names = self._dedupe_preserve_order([*prerequisites, target_name, *milestones])
        backbone = [
            {
                "id": f"free-step-{index + 1}",
                "name": name,
                "description": description if index == 0 else f"{target_name} 自由模式推演中的关键阶段",
                "is_target": index == max(len(backbone_names) - 2, 0),
            }
            for index, name in enumerate(backbone_names[:5])
        ]
        return TheaterTargetContext(
            name=target_name,
            description=description,
            target_node_id=None,
            resolution_mode="free_mode",
            backbone=backbone,
        )

    def _fallback_free_mode_target(self, topic: str) -> dict[str, Any]:
        terms = _normalized_topic_terms(topic)
        candidates = [term for term in terms if len(term) >= 2]
        target_name = candidates[0] if candidates else topic.strip() or "当前学习主题"
        prerequisites = candidates[1:4]
        if not prerequisites:
            prerequisites = [f"{target_name} 的核心概念", f"{target_name} 的关键步骤"]
        milestones = [f"{target_name} 的典型练习", f"{target_name} 的迁移应用"]
        return {
            "target_name": target_name,
            "description": f"围绕 {target_name} 生成一条不依赖既有图谱节点的自由模式学习路径。",
            "prerequisites": prerequisites[:3],
            "milestones": milestones[:2],
        }

    @staticmethod
    def _coerce_string_list(raw: Any) -> list[str]:
        if isinstance(raw, list):
            items = raw
        elif raw is None:
            items = []
        else:
            items = [raw]
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        deduped: list[str] = []
        for item in items:
            normalized = str(item).strip()
            if normalized and normalized not in deduped:
                deduped.append(normalized)
        return deduped

    async def simulate_what_if(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        skip_node_id: str | None = None,
        skip_node_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_or_raise(prediction_id)
        selected_route = self._find_route(cached, route_id)
        skipped_steps = self._find_steps(
            selected_route,
            skip_node_ids=list(skip_node_ids or ([skip_node_id] if skip_node_id else [])),
        )
        skipped_step = skipped_steps[0]
        target_name = str(cached.get("target_name") or "")

        downstream = [
            step for step in list(selected_route.get("steps") or [])
            if int(step.get("index") or 0) > min(int(item.get("index") or 0) for item in skipped_steps)
        ]
        mastery_penalty = 6 + (len(downstream) * 2.5) + sum(
            5 if str(step.get("risk_level") or "") == "high" else (3 if str(step.get("risk_level") or "") == "medium" else 1.5)
            for step in skipped_steps
        )
        predicted_mastery = _clamp(float(selected_route.get("estimated_mastery") or 0.0) - mastery_penalty, 5.0, 100.0)
        completion_penalty = 0.05 + (len(downstream) * 0.025) + (len(skipped_steps) * 0.03)
        predicted_completion = _clamp(
            float(selected_route.get("estimated_completion_rate") or 0.0) - completion_penalty,
            0.15,
            0.99,
        )

        consequence_lines = [
            f"跳过 {'、'.join(str(step.get('node_name') or '') for step in skipped_steps)} 后，{target_name} 的推导链会变短，但中间校验点也会减少。",
        ]
        if downstream:
            consequence_lines.append(
                f"最容易受影响的是 {downstream[0].get('node_name')}，因为它默认依赖前一步的符号感和方法熟练度。"
            )
        if any(float(step.get("current_mastery") or 0.0) < 60 for step in skipped_steps):
            consequence_lines.append("被跳过的节点里仍有偏弱环节，直接跳过会放大后面“看得懂但做不稳”的风险。")

        suggestion = (
            f"建议不要完全跳过 {skipped_step.get('node_name')}，可以把它压缩成 {max(20, int(skipped_step.get('estimated_minutes') or 30) // 2)} 分钟速览。"
        )
        remaining_path = [
            step
            for step in list(selected_route.get("steps") or [])
            if str(step.get("node_id") or "") not in {str(item.get("node_id") or "") for item in skipped_steps}
        ]
        result = {
            "prediction_id": prediction_id,
            "route_id": route_id,
            "skip_node_id": str(skipped_step.get("node_id") or ""),
            "skip_node_name": skipped_step.get("node_name"),
            "skip_node_ids": [str(step.get("node_id") or "") for step in skipped_steps],
            "skip_node_names": [str(step.get("node_name") or "") for step in skipped_steps],
            "original_mastery": round(float(selected_route.get("estimated_mastery") or 0.0), 2),
            "original_completion_rate": round(float(selected_route.get("estimated_completion_rate") or 0.0), 4),
            "predicted_mastery": round(predicted_mastery, 2),
            "predicted_completion_rate": round(predicted_completion, 4),
            "delta_mastery": round(predicted_mastery - float(selected_route.get("estimated_mastery") or 0.0), 2),
            "delta_completion_rate": round(
                predicted_completion - float(selected_route.get("estimated_completion_rate") or 0.0),
                4,
            ),
            "consequences": consequence_lines,
            "suggestion": suggestion,
            "remaining_path": remaining_path,
            "branch_label": f"跳过 {'、'.join(str(step.get('node_name') or '') for step in skipped_steps)}",
            "branch_focus_node_ids": [str(step.get("node_id") or "") for step in skipped_steps[:2]],
            "branch_timeline": self._build_branch_timeline(
                route=selected_route,
                skipped_steps=skipped_steps,
                predicted_mastery=predicted_mastery,
                predicted_completion=predicted_completion,
            ),
            "user_id": str(user_id),
        }
        return result

    async def save_snapshot(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        note: str | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_or_raise(prediction_id)
        selected_route = self._find_route(cached, route_id)
        snapshot_id = str(uuid4())
        snapshot = {
            "snapshot_id": snapshot_id,
            "prediction_id": prediction_id,
            "route_id": route_id,
            "saved_at": _utcnow().isoformat(),
            "title": selected_route.get("title"),
            "topic": cached.get("topic"),
            "target_name": cached.get("target_name"),
            "graph": cached.get("graph"),
            "discussion_turns": cached.get("discussion_turns"),
            "selected_route": selected_route,
            "note": note,
            "share_hint": {
                "resource_type": "cognitive_fragment",
                "title": f"知识推演剧场：{selected_route.get('title')}",
            },
            "owner_id": str(user_id),
        }
        await cache_service.set(f"{self.SNAPSHOT_PREFIX}{snapshot_id}", snapshot, ttl=self.SNAPSHOT_TTL_SECONDS)
        return snapshot

    async def adopt_prediction(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        source_chat_session_id: str | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_or_raise(prediction_id)
        selected_route = self._find_route(cached, route_id)
        target_name = str(cached.get("target_name") or "学习目标")
        horizon_days = int(cached.get("horizon_days") or 14)
        steps = list(selected_route.get("steps") or [])

        plan = await PlanService.create(
            db=self.db,
            obj_in=PlanCreate(
                name=f"{target_name} · {selected_route.get('title')}",
                type=PlanType.SPRINT,
                description=str(selected_route.get("summary") or ""),
                subject=target_name,
                target_date=date.today() + timedelta(days=horizon_days),
                daily_available_minutes=int(selected_route.get("daily_minutes") or 40),
                total_estimated_hours=max(1.0, sum((int(step.get("estimated_minutes") or 25) for step in steps)) / 60.0),
            ),
            user_id=user_id,
            redis_client=cache_service.redis,
        )
        plan.source = "prediction_theater"
        plan.source_metadata = {
            "prediction_id": prediction_id,
            "route_id": route_id,
            "target_node_id": cached.get("target_node_id"),
            "target_name": target_name,
            "steps": steps,
        }
        self.db.add(plan)

        created_tasks = await self._create_week_one_tasks(
            user_id=user_id,
            plan_id=plan.id,
            route=selected_route,
            target_name=target_name,
        )
        checkpoint_dates = self._build_checkpoint_schedule(
            route=selected_route,
            created_tasks=created_tasks,
        )
        review_due_on = (date.today() + timedelta(days=7)).isoformat()
        plan.source_metadata = {
            **(plan.source_metadata or {}),
            "created_tasks": created_tasks,
            "checkpoint_dates": checkpoint_dates,
            "review_due_on": review_due_on,
        }
        self.db.add(plan)

        risk_steps = [step for step in steps if str(step.get("risk_level") or "") in {"medium", "high"}]
        for step in risk_steps[:3]:
            node_id = step.get("node_id")
            if not node_id:
                continue
            try:
                await self.structure.tag_node_signal(UUID(str(node_id)), "signal:predicted_risk", active=True)
            except Exception:
                continue

        cached["selected_prediction"] = selected_route
        cached["adopted_plan_id"] = str(plan.id)
        cached["adopted_at"] = _utcnow().isoformat()
        await cache_service.set(
            f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
            cached,
            ttl=self.accuracy.TTL_SECONDS,
        )

        try:
            await CognitiveService(self.db).create_fragment(
                user_id=user_id,
                source_type="prediction_theater",
                resource_type="prediction_route",
                content=(
                    f"采纳了知识推演路径「{selected_route.get('title')}」，"
                    f"目标是 {target_name}。"
                    f" 核心策略：{selected_route.get('summary') or '按推荐路径推进学习。'}"
                    f" 关键风险：{'；'.join(list(selected_route.get('risks') or [])[:2]) or '暂无显著风险。'}"
                ),
                context_tags={
                    "prediction_id": prediction_id,
                    "route_id": route_id,
                    "target_node_id": cached.get("target_node_id"),
                    "target_name": target_name,
                    "plan_id": str(plan.id),
                    "origin": "knowledge_theater",
                },
                severity=2,
            )
        except Exception:
            pass

        query = {"topic": str(cached.get("topic") or "")}
        if cached.get("target_node_id"):
            query["target_node_id"] = str(cached.get("target_node_id"))
        deep_link = f"/theater?{urlencode(query)}"
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="theater_route_adopted",
                category="learning_insight",
                title=f"已采纳推演路径「{selected_route.get('title')}」",
                description=f"已根据推演创建计划「{plan.name}」，并拆出首周任务与检查点。",
                priority="medium",
                metadata={
                    "prediction_id": prediction_id,
                    "route_id": route_id,
                    "plan_id": str(plan.id),
                    "title": str(selected_route.get("title") or plan.name),
                    "deep_link": deep_link,
                    "created_tasks": created_tasks,
                    "checkpoint_dates": checkpoint_dates,
                    "review_due_on": review_due_on,
                },
            ),
        )
        if source_chat_session_id:
            await self._write_back_to_chat(
                user_id=user_id,
                session_id=source_chat_session_id,
                content=f"已根据推演创建计划「{plan.name}」",
                metadata={
                    "plan_id": str(plan.id),
                    "prediction_id": prediction_id,
                    "route_id": route_id,
                },
            )

        await self.db.commit()
        return {
            "prediction_id": prediction_id,
            "route_id": route_id,
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "source_metadata": plan.source_metadata,
            "created_tasks": created_tasks,
            "checkpoint_dates": checkpoint_dates,
            "review_due_on": review_due_on,
        }

    async def _write_back_to_chat(
        self,
        *,
        user_id: UUID,
        session_id: str,
        content: str,
        metadata: dict[str, Any],
    ) -> None:
        try:
            session_uuid = UUID(str(session_id))
        except (TypeError, ValueError):
            return
        session = await self.db.get(ChatSession, session_uuid)
        if session is None or session.user_id != user_id:
            return
        message = ChatMessage(
            user_id=user_id,
            session_id=session_uuid,
            role=MessageRole.SYSTEM,
            content=content,
            actions={"metadata": metadata},
        )
        self.db.add(message)
        session.last_message_at = _utcnow()
        self.db.add(session)

    async def record_actual_outcome(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        actual_completion_rate: float | None = None,
        actual_mastery: float | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_or_raise(prediction_id)
        target_node_id = cached.get("target_node_id")
        adopted_plan_id = cached.get("adopted_plan_id")

        resolved_completion = float(actual_completion_rate or 0.0)
        if adopted_plan_id and actual_completion_rate is None:
            from app.models.plan import Plan

            plan = await self.db.get(Plan, UUID(str(adopted_plan_id)))
            if plan:
                resolved_completion = float(plan.progress or 0.0)

        resolved_mastery = float(actual_mastery or 0.0)
        if target_node_id and actual_mastery is None:
            status = await self.db.get(UserNodeStatus, (user_id, UUID(str(target_node_id))))
            if status:
                resolved_mastery = float(status.mastery_score or 0.0)

        summary = await self.accuracy.record_actual(
            prediction_id,
            actual_completion_rate=resolved_completion,
            actual_mastery=resolved_mastery,
        )
        if not summary:
            raise ValueError("Prediction record not found")
        cached["accuracy_tracking"] = {
            **dict(cached.get("accuracy_tracking") or {}),
            "status": "recorded",
            "recorded_at": _utcnow().isoformat(),
        }
        await cache_service.set(
            f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
            cached,
            ttl=self.accuracy.TTL_SECONDS,
        )
        return summary

    async def get_accuracy_summary(self, prediction_id: str) -> dict[str, Any] | None:
        return await self.accuracy.get_summary(prediction_id)

    async def _resolve_target_node(
        self,
        *,
        topic: str,
        target_node_id: UUID | None,
    ) -> KnowledgeNode:
        if target_node_id is not None:
            target_node = await self.db.get(KnowledgeNode, target_node_id)
            if target_node:
                return target_node

        normalized = topic.strip().lower()
        if not normalized:
            raise ValueError("Topic cannot be empty")

        search_terms = _normalized_topic_terms(topic)
        if not search_terms:
            raise ValueError("Topic cannot be empty")

        conditions = []
        for term in search_terms:
            conditions.extend(
                [
                    func.lower(KnowledgeNode.name).contains(term),
                    func.lower(func.coalesce(KnowledgeNode.description, "")).contains(term),
                    func.lower(cast(KnowledgeNode.keywords, String)).contains(term),
                ]
            )

        stmt = (
            select(KnowledgeNode)
            .where(or_(*conditions))
            .limit(30)
        )
        result = await self.db.execute(stmt)
        candidates = list(result.scalars().all())
        node = self._pick_best_target_node(candidates=candidates, normalized_topic=normalized, search_terms=search_terms)
        if node:
            return node

        # Fallback to a broader slice of high-signal nodes so free-form topics
        # from cards and recommendations can still land on a usable target.
        fallback_stmt = (
            select(KnowledgeNode)
            .where(or_(KnowledgeNode.is_seed.is_(True), KnowledgeNode.importance_level >= 3))
            .order_by(desc(KnowledgeNode.importance_level), desc(KnowledgeNode.updated_at))
            .limit(200)
        )
        fallback_result = await self.db.execute(fallback_stmt)
        fallback_candidates = list(fallback_result.scalars().all())
        node = self._pick_best_target_node(
            candidates=fallback_candidates,
            normalized_topic=normalized,
            search_terms=search_terms,
        )
        if not node:
            raise ValueError(f'No knowledge node found for topic "{topic}"')
        return node

    @staticmethod
    def _pick_best_target_node(
        *,
        candidates: list[KnowledgeNode],
        normalized_topic: str,
        search_terms: list[str],
    ) -> KnowledgeNode | None:
        if not candidates:
            return None

        def score(node: KnowledgeNode) -> tuple[float, int, float, datetime]:
            name = str(node.name or "").strip().lower()
            description = str(node.description or "").strip().lower()
            keyword_blob = " ".join(
                str(item).strip().lower()
                for item in (node.keywords or [])
                if str(item).strip()
            )
            best = 0.0
            matched_terms = 0
            lexical_total = 0.0

            for term in search_terms:
                if not term:
                    continue
                term_score = 0.0
                if name == term:
                    term_score = max(term_score, 120.0)
                if term == normalized_topic and term in name:
                    term_score = max(term_score, 105.0)
                if term in name:
                    term_score = max(term_score, 95.0 + min(len(term), 20))
                if name and name in normalized_topic:
                    term_score = max(term_score, 88.0 + min(len(name), 20))
                if term in description:
                    term_score = max(term_score, 54.0 + min(len(term), 18))
                if term in keyword_blob:
                    term_score = max(term_score, 66.0 + min(len(term), 18))
                if description and description in normalized_topic:
                    term_score = max(term_score, 42.0)
                if keyword_blob and keyword_blob in normalized_topic:
                    term_score = max(term_score, 40.0)
                if term_score > 0:
                    matched_terms += 1
                    lexical_total += term_score
                best = max(best, term_score)

            lexical_score = best + lexical_total + matched_terms * 18.0
            return (
                lexical_score,
                matched_terms,
                float(getattr(node, "importance_level", 0) or 0),
                getattr(node, "updated_at", None) or datetime.min,
            )

        best_node = max(candidates, key=score)
        best_score = score(best_node)
        if best_score[0] <= 0:
            fallback_node = PredictionTheaterService._pick_character_overlap_node(
                candidates=candidates,
                search_terms=search_terms,
            )
            if fallback_node is None:
                return None
            return fallback_node
        return best_node

    @staticmethod
    def _pick_character_overlap_node(
        *,
        candidates: list[KnowledgeNode],
        search_terms: list[str],
    ) -> KnowledgeNode | None:
        filtered_terms = [
            term
            for term in search_terms
            if term and len(term.strip()) >= 2
        ]
        topic_chars = [
            char
            for term in filtered_terms
            for char in term
            if re.match(r"[0-9a-zA-Z\u4e00-\u9fff+#]", char)
            and char not in {"帮", "我", "推", "演", "学", "习", "路", "径", "与", "和", "的"}
        ]
        if not topic_chars:
            return None

        def overlap_score(node: KnowledgeNode) -> tuple[float, int, float, datetime]:
            corpus = " ".join(
                [
                    str(node.name or "").strip().lower(),
                    str(node.description or "").strip().lower(),
                    " ".join(
                        str(item).strip().lower()
                        for item in (node.keywords or [])
                        if str(item).strip()
                    ),
                ]
            )
            overlap = sum(1 for char in set(topic_chars) if char in corpus)
            coverage = overlap / max(len(set(topic_chars)), 1)
            return (
                coverage,
                overlap,
                float(getattr(node, "importance_level", 0) or 0),
                getattr(node, "updated_at", None) or datetime.min,
            )

        best_node = max(candidates, key=overlap_score)
        best_score = overlap_score(best_node)
        if best_score[1] >= 2 and best_score[0] >= 0.18:
            return best_node
        return None

    async def _resolve_target_node_for_user(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None,
    ) -> KnowledgeNode:
        if target_node_id is None:
            return await self._resolve_target_node(topic=topic, target_node_id=None)

        target_node = await self.db.get(KnowledgeNode, target_node_id)
        if target_node is None:
            raise TheaterNodeAccessError()

        if bool(target_node.is_seed) or int(target_node.importance_level or 0) >= 3:
            return target_node

        user_status = await self.db.get(UserNodeStatus, (user_id, target_node_id))
        if user_status is not None:
            return target_node

        raise TheaterNodeAccessError()

    async def _get_mastery_map(self, user_id: UUID) -> dict[str, float]:
        result = await self.db.execute(
            select(UserNodeStatus.node_id, UserNodeStatus.mastery_score).where(UserNodeStatus.user_id == user_id)
        )
        return {str(node_id): float(score or 0.0) for node_id, score in result.all()}

    async def _build_user_learning_profile(self, user_id: UUID) -> dict[str, Any]:
        recent_records = (
            await self.db.execute(
                select(StudyRecord.study_minutes)
                .where(StudyRecord.user_id == user_id)
                .order_by(desc(StudyRecord.created_at))
                .limit(20)
            )
        ).all()
        average_minutes = 40
        if recent_records:
            average_minutes = int(
                sum(int(item[0] or 0) for item in recent_records) / max(len(recent_records), 1)
            ) or 40
        return {
            "average_session_minutes": int(_clamp(float(average_minutes), 25, 90)),
        }

    async def _top_pattern_names(self, user_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(BehaviorPattern.pattern_name)
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.is_archived.is_(False),
            )
            .order_by(desc(BehaviorPattern.confidence_score), desc(BehaviorPattern.updated_at))
            .limit(3)
        )
        return [present_pattern_name(str(item[0])) for item in result.all() if str(item[0]).strip()]

    async def _build_graph_bundle(
        self,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
    ) -> dict[str, Any]:
        node_ids: list[UUID] = []
        for item in backbone[: self.MAX_GRAPH_NODES]:
            try:
                node_ids.append(UUID(str(item["id"])))
            except (KeyError, TypeError, ValueError):
                return self._build_synthetic_graph_bundle(backbone, mastery_map)
        result = await self.db.execute(
            select(KnowledgeNode.id, KnowledgeNode.name, KnowledgeNode.description)
            .where(KnowledgeNode.id.in_(node_ids))
        )
        rows = result.all()
        nodes_by_id = {
            str(node_id): {
                "id": str(node_id),
                "name": name,
                "description": description or "",
                "current_mastery": round(mastery_map.get(str(node_id), 0.0), 2),
                "predicted_mastery": round(_clamp(mastery_map.get(str(node_id), 0.0) + 18, 8, 100), 2),
                "risk_level": "high" if mastery_map.get(str(node_id), 0.0) < 45 else ("medium" if mastery_map.get(str(node_id), 0.0) < 70 else "low"),
            }
            for node_id, name, description in rows
        }
        edge_rows = (
            await self.db.execute(
                select(NodeRelation.source_node_id, NodeRelation.target_node_id, NodeRelation.relation_type, NodeRelation.strength)
                .where(
                    NodeRelation.source_node_id.in_(node_ids),
                    NodeRelation.target_node_id.in_(node_ids),
                )
            )
        ).all()
        edges = [
            {
                "id": f"{source_id}_{target_id}_{relation_type}",
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": str(relation_type or "related").lower(),
                "strength": float(strength or 0.5),
            }
            for source_id, target_id, relation_type, strength in edge_rows
        ]
        if not edges:
            ordered_ids = list(nodes_by_id.keys())
            edges = [
                {
                    "id": f"{ordered_ids[index]}_{ordered_ids[index + 1]}_prerequisite",
                    "source_id": ordered_ids[index],
                    "target_id": ordered_ids[index + 1],
                    "relation_type": "prerequisite",
                    "strength": 0.58,
                }
                for index in range(len(ordered_ids) - 1)
            ]
        return {"nodes": list(nodes_by_id.values()), "edges": edges}

    def _build_synthetic_graph_bundle(
        self,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
    ) -> dict[str, Any]:
        nodes = []
        ordered_ids: list[str] = []
        total = max(len(backbone), 1)
        for index, item in enumerate(backbone[: self.MAX_GRAPH_NODES]):
            node_id = str(item.get("id") or f"free-step-{index + 1}")
            ordered_ids.append(node_id)
            current_mastery = mastery_map.get(node_id, _clamp(34 + index * 7, 18, 74))
            nodes.append(
                {
                    "id": node_id,
                    "name": str(item.get("name") or f"阶段 {index + 1}"),
                    "description": str(item.get("description") or "自由模式推演阶段"),
                    "current_mastery": round(current_mastery, 2),
                    "predicted_mastery": round(_clamp(current_mastery + 16 - index, 12, 92), 2),
                    "risk_level": "high" if index < max(total - 2, 1) else "medium",
                }
            )
        edges = [
            {
                "id": f"{ordered_ids[index]}_{ordered_ids[index + 1]}_free_mode",
                "source_id": ordered_ids[index],
                "target_id": ordered_ids[index + 1],
                "relation_type": "prerequisite",
                "strength": round(_clamp(0.66 - index * 0.06, 0.36, 0.76), 2),
            }
            for index in range(len(ordered_ids) - 1)
        ]
        return {"nodes": nodes, "edges": edges}

    def _build_path_options(
        self,
        *,
        target_name: str,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
        horizon_days: int,
        study_preferences: dict[str, Any],
        pattern_names: list[str],
    ) -> list[TheaterPathOption]:
        node_names = [str(item.get("name") or "") for item in backbone]
        average_mastery = sum(mastery_map.get(str(item["id"]), 0.0) for item in backbone) / max(len(backbone), 1)
        session_minutes = int(study_preferences.get("average_session_minutes") or 40)
        strategies = [
            {
                "id": "path_foundation",
                "title": "稳扎稳打",
                "strategy_type": "foundation",
                "expert_ids": ["galaxy_guide", "time_tutor"],
                "summary": f"先顺着 {target_name} 的前置链路补齐基础，再进入目标节点和应用练习。",
                "order": list(backbone),
                "completion_bias": 0.10,
                "mastery_bias": -2.0,
                "risk_bias": "节奏稳，但后半段会更密集。",
            },
            {
                "id": "path_breakthrough",
                "title": "重点突破",
                "strategy_type": "breakthrough",
                "expert_ids": ["exam_oracle", "deep_analyst"],
                "summary": f"先切入 {target_name} 的核心概念，再按暴露出的缺口回补关键前置。",
                "order": [backbone[-1], *backbone[:-1]] if backbone else [],
                "completion_bias": -0.08,
                "mastery_bias": 5.0,
                "risk_bias": "上手快，但如果前置薄弱，后面会频繁回补。",
            },
            {
                "id": "path_personalized",
                "title": "你的历史最优模式",
                "strategy_type": "personalized",
                "expert_ids": ["study_buddy", "galaxy_guide"],
                "summary": f"根据你最近的学习时长和认知模式，把 {target_name} 切成更容易连续坚持的小步。",
                "order": list(backbone),
                "completion_bias": 0.03,
                "mastery_bias": 1.5,
                "risk_bias": f"需要保持每天约 {session_minutes} 分钟的连续性。",
            },
        ]

        options: list[TheaterPathOption] = []
        for idx, strategy in enumerate(strategies):
            ordered_backbone = [item for item in strategy["order"] if isinstance(item, dict)]
            steps: list[TheaterPathStep] = []
            total_steps = max(len(ordered_backbone), 1)
            checkpoint_days = self._checkpoint_days_for_horizon(horizon_days)
            for step_index, item in enumerate(ordered_backbone, start=1):
                node_id = str(item.get("id") or "")
                current_mastery = mastery_map.get(node_id, 0.0)
                predicted_mastery = _clamp(current_mastery + (18 - step_index * 1.5) + float(strategy["mastery_bias"]), 8, 100)
                risk_level = "high" if current_mastery < 45 else ("medium" if current_mastery < 70 else "low")
                if strategy["strategy_type"] == "breakthrough" and step_index == 1:
                    risk_level = "medium" if risk_level == "high" else risk_level
                estimated_minutes = int(_clamp(session_minutes + (6 if step_index == total_steps else 0), 25, 95))
                day_slot = max(1, round((step_index / total_steps) * horizon_days))
                rationale = self._step_rationale(
                    strategy_type=str(strategy["strategy_type"]),
                    node_name=str(item.get("name") or "当前节点"),
                    is_target=bool(item.get("is_target")),
                )
                checkpoint_label = (
                    f"Checkpoint · Day {day_slot}"
                    if day_slot in checkpoint_days or step_index == total_steps
                    else None
                )
                steps.append(
                    TheaterPathStep(
                        index=step_index,
                        node_id=node_id,
                        node_name=str(item.get("name") or "当前节点"),
                        rationale=rationale,
                        current_mastery=current_mastery,
                        predicted_mastery=predicted_mastery,
                        risk_level=risk_level,
                        estimated_minutes=estimated_minutes,
                        day_label=f"Day {day_slot}",
                        checkpoint_label=checkpoint_label,
                    )
                )

            completion_rate = _clamp(
                0.52 + (average_mastery / 220.0) + float(strategy["completion_bias"]) - (len(steps) / 70.0),
                0.35,
                0.96,
            )
            estimated_mastery = _clamp(
                average_mastery + 18 + float(strategy["mastery_bias"]) - (len(pattern_names) * 1.2),
                20,
                96,
            )
            risks = [str(strategy["risk_bias"])]
            if pattern_names:
                risks.append(f"近期行为模式提示：{pattern_names[0]} 可能影响这条路径的稳定执行。")
            if node_names:
                risks.append(f"{node_names[min(len(node_names) - 1, 0)]} 的掌握情况会决定后续理解是否顺滑。")
            route_score = self._route_score(
                completion_rate=completion_rate,
                estimated_mastery=estimated_mastery,
                risks=risks,
                strategy_type=str(strategy["strategy_type"]),
            )
            options.append(
                TheaterPathOption(
                    id=str(strategy["id"]),
                    title=str(strategy["title"]),
                    summary=str(strategy["summary"]),
                    strategy_type=str(strategy["strategy_type"]),
                    expert_ids=list(strategy["expert_ids"]),
                    estimated_completion_rate=completion_rate,
                    estimated_mastery=estimated_mastery,
                    daily_minutes=session_minutes,
                    risks=risks[:3],
                    route_score=route_score,
                    checkpoint_days=checkpoint_days,
                    week_one_tasks=self._week_one_task_blueprints(steps=steps, target_name=target_name),
                    steps=steps,
                )
            )
        return options

    async def _build_discussion(
        self,
        *,
        topic: str,
        target_name: str,
        options: list[TheaterPathOption],
        graph_bundle: dict[str, Any],
        pattern_names: list[str],
    ) -> list[dict[str, Any]]:
        fallback = self._fallback_discussion(topic=topic, target_name=target_name, options=options, pattern_names=pattern_names)
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with a turns array. Each turn needs agent_id, display_name, "
                        "turn_type, content, related_node_ids."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Topic: {topic}\n"
                        f"Target: {target_name}\n"
                        f"Path options: {[item.to_dict() for item in options]}\n"
                        f"Graph: {graph_bundle}\n"
                        f"Behavior patterns: {pattern_names}\n"
                        "Create 3-4 concise roundtable turns that compare the paths and point to the main risks."
                    ),
                },
            ],
            fallback={"turns": fallback},
            temperature=0.25,
        )
        if isinstance(payload, list):
            turns = list(payload)
        elif isinstance(payload, dict):
            turns = list(payload.get("turns") or [])
        else:
            turns = []
        normalized: list[dict[str, Any]] = []
        for index, turn in enumerate(turns):
            if not isinstance(turn, dict):
                continue
            normalized.append(
                {
                    "turn_index": index,
                    "agent_id": str(turn.get("agent_id") or fallback[min(index, len(fallback) - 1)]["agent_id"]),
                    "display_name": str(turn.get("display_name") or fallback[min(index, len(fallback) - 1)]["display_name"]),
                    "turn_type": str(turn.get("turn_type") or "analysis"),
                    "content": str(turn.get("content") or fallback[min(index, len(fallback) - 1)]["content"]),
                    "related_node_ids": [str(item) for item in list(turn.get("related_node_ids") or []) if str(item).strip()],
                }
            )
        return normalized or fallback

    def _build_timeline(
        self,
        options: list[TheaterPathOption],
        discussion: list[dict[str, Any]],
        *,
        horizon_days: int,
    ) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        baseline = options[0] if options else None
        for option in options:
            start_mastery = (
                sum(step.current_mastery for step in option.steps) / max(len(option.steps), 1)
            )
            for day in range(1, max(horizon_days, 1) + 1):
                progress_ratio = day / max(horizon_days, 1)
                step_index = min(
                    len(option.steps) - 1,
                    max(0, int(progress_ratio * max(len(option.steps), 1)) - 1),
                )
                active_step = option.steps[step_index] if option.steps else None
                projected_mastery = _clamp(
                    start_mastery + ((option.estimated_mastery - start_mastery) * (progress_ratio ** 0.86)),
                    0,
                    100,
                )
                projected_completion = _clamp(
                    option.estimated_completion_rate * (progress_ratio ** 0.94),
                    0.02,
                    option.estimated_completion_rate,
                )
                focus_node_ids = [
                    step.node_id
                    for step in option.steps[max(0, step_index - 1): step_index + 2]
                ]
                comparison_delta = (
                    option.estimated_mastery - baseline.estimated_mastery
                    if baseline is not None
                    else 0.0
                )
                frames.append(
                    {
                        "index": len(frames),
                        "label": f"Day {day}",
                        "day_index": day,
                        "route_id": option.id,
                        "focus_node_ids": focus_node_ids,
                        "discussion_turn_index": min(day - 1, max(len(discussion) - 1, 0)),
                        "projected_mastery": round(projected_mastery, 2),
                        "projected_completion_rate": round(projected_completion, 4),
                        "active_step_node_id": active_step.node_id if active_step else "",
                        "active_step_title": active_step.node_name if active_step else option.title,
                        "compare_label": (
                            "推荐基线"
                            if baseline is not None and option.id == baseline.id
                            else f"相对推荐 {comparison_delta:+.0f}%"
                        ),
                        "branch_type": "baseline",
                    }
                )
        return frames

    @staticmethod
    def _checkpoint_days_for_horizon(horizon_days: int) -> list[int]:
        return sorted({1, min(3, horizon_days), min(7, horizon_days), horizon_days})

    @staticmethod
    def _route_score(
        *,
        completion_rate: float,
        estimated_mastery: float,
        risks: list[str],
        strategy_type: str,
    ) -> float:
        penalty = len(risks) * 2.5
        if strategy_type == "breakthrough":
            penalty += 2
        return _clamp((completion_rate * 100 * 0.46) + (estimated_mastery * 0.54) - penalty, 0, 100)

    def _week_one_task_blueprints(
        self,
        *,
        steps: list[TheaterPathStep],
        target_name: str,
    ) -> list[dict[str, Any]]:
        blueprints: list[dict[str, Any]] = []
        for step in steps[:3]:
            blueprints.append(
                {
                    "title": f"{step.day_label} · 推进 {step.node_name}",
                    "node_id": step.node_id,
                    "estimated_minutes": step.estimated_minutes,
                    "day_label": step.day_label,
                    "checkpoint_label": step.checkpoint_label,
                    "summary": f"围绕 {target_name} 补齐 {step.node_name}，并把 {step.rationale}",
                }
            )
        return blueprints

    def _build_branch_timeline(
        self,
        *,
        route: dict[str, Any],
        skipped_steps: list[dict[str, Any]],
        predicted_mastery: float,
        predicted_completion: float,
    ) -> list[dict[str, Any]]:
        remaining_steps = [
            step
            for step in list(route.get("steps") or [])
            if str(step.get("node_id") or "") not in {str(item.get("node_id") or "") for item in skipped_steps}
        ]
        day_count = max(len(remaining_steps), 4)
        original_mastery = float(route.get("estimated_mastery") or predicted_mastery)
        original_completion = float(route.get("estimated_completion_rate") or predicted_completion)
        frames: list[dict[str, Any]] = []
        for day in range(1, day_count + 1):
            progress_ratio = day / day_count
            active_step = remaining_steps[min(len(remaining_steps) - 1, max(day - 1, 0))] if remaining_steps else {}
            mastery_value = original_mastery + ((predicted_mastery - original_mastery) * progress_ratio)
            completion_value = original_completion + ((predicted_completion - original_completion) * progress_ratio)
            frames.append(
                {
                    "index": day - 1,
                    "label": f"Day {day}",
                    "day_index": day,
                    "route_id": str(route.get("id") or ""),
                    "focus_node_ids": [str(active_step.get("node_id") or "")] if active_step else [],
                    "discussion_turn_index": 0,
                    "projected_mastery": round(mastery_value, 2),
                    "projected_completion_rate": round(completion_value, 4),
                    "active_step_node_id": str(active_step.get("node_id") or ""),
                    "active_step_title": str(active_step.get("node_name") or "分支推演"),
                    "compare_label": "What-If 分支",
                    "branch_type": "what_if",
                }
            )
        return frames

    async def _create_week_one_tasks(
        self,
        *,
        user_id: UUID,
        plan_id: UUID,
        route: dict[str, Any],
        target_name: str,
    ) -> list[dict[str, Any]]:
        created: list[dict[str, Any]] = []
        for index, step in enumerate(list(route.get("steps") or [])[:3]):
            node_id = self._maybe_uuid(step.get("node_id"))
            due_date = date.today() + timedelta(days=min(index * 2, 6))
            task = await TaskService.create(
                self.db,
                TaskCreate(
                    title=f"{step.get('day_label') or f'Day {index + 1}'} · 推进 {step.get('node_name') or target_name}",
                    type=TaskType.LEARNING,
                    plan_id=plan_id,
                    tags=["theater_path", str(route.get("strategy_type") or "route")],
                    estimated_minutes=int(step.get("estimated_minutes") or 30),
                    difficulty=2 if str(step.get("risk_level") or "") == "low" else 3,
                    energy_cost=2,
                    guide_content=str(step.get("rationale") or ""),
                    due_date=due_date,
                    knowledge_node_id=node_id,
                ),
                user_id,
            )
            created.append(
                {
                    "task_id": str(task.id),
                    "title": task.title,
                    "due_date": due_date.isoformat(),
                    "task_type": task.type.value,
                    "node_id": str(node_id) if node_id else "",
                }
            )
        for checkpoint_day in self._checkpoint_days_for_horizon(7)[1:3]:
            due_date = date.today() + timedelta(days=checkpoint_day - 1)
            task = await TaskService.create(
                self.db,
                TaskCreate(
                    title=f"Checkpoint · 回看 {target_name} 的推演进度",
                    type=TaskType.REFLECTION,
                    plan_id=plan_id,
                    tags=["theater_checkpoint"],
                    estimated_minutes=15,
                    difficulty=1,
                    energy_cost=1,
                    guide_content="回看本周路径执行情况，对比推演预期与真实推进差异。",
                    due_date=due_date,
                ),
                user_id,
            )
            created.append(
                {
                    "task_id": str(task.id),
                    "title": task.title,
                    "due_date": due_date.isoformat(),
                    "task_type": task.type.value,
                    "node_id": "",
                }
            )
        return created

    def _build_checkpoint_schedule(
        self,
        *,
        route: dict[str, Any],
        created_tasks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        del route
        checkpoints: list[dict[str, Any]] = []
        for item in created_tasks:
            if item.get("task_type") != TaskType.REFLECTION.value:
                continue
            checkpoints.append(
                {
                    "label": item.get("title"),
                    "date": item.get("due_date"),
                    "task_id": item.get("task_id"),
                }
            )
        return checkpoints

    @staticmethod
    def _build_accuracy_tracking(
        *,
        prediction_id: str,
        generated_at: datetime,
    ) -> dict[str, Any]:
        due_on = (generated_at.date() + timedelta(days=7)).isoformat()
        return {
            "prediction_id": prediction_id,
            "status": "pending_feedback",
            "due_on": due_on,
            "summary_hint": "建议在 7 天后回填真实完成率和掌握度，检查这次推演是否命中。",
        }

    def _fallback_discussion(
        self,
        *,
        topic: str,
        target_name: str,
        options: list[TheaterPathOption],
        pattern_names: list[str],
    ) -> list[dict[str, Any]]:
        anchor_option = options[0] if options else None
        anchor_nodes = [step.node_id for step in anchor_option.steps[:2]] if anchor_option else []
        pattern_hint = pattern_names[0] if pattern_names else "连续性"
        return [
            {
                "turn_index": 0,
                "agent_id": "galaxy_guide",
                "display_name": "星图导航",
                "turn_type": "analysis",
                "content": f"{target_name} 的关键不是会不会做题，而是前置链是否闭合。最稳的路径通常要先补齐依赖。",
                "related_node_ids": anchor_nodes,
            },
            {
                "turn_index": 1,
                "agent_id": "deep_analyst",
                "display_name": "深度分析",
                "turn_type": "rebuttal",
                "content": f"如果目标是尽快推进 {topic}，重点突破路径会更有手感，但需要接受中途回补基础的成本。",
                "related_node_ids": anchor_nodes,
            },
            {
                "turn_index": 2,
                "agent_id": "study_buddy",
                "display_name": "学伴",
                "turn_type": "synthesis",
                "content": f"结合你最近的 {pattern_hint} 模式，更建议选一条能每天稳定推进的小步路径，而不是一次压太多。",
                "related_node_ids": anchor_nodes,
            },
        ]

    async def _get_prediction_or_raise(self, prediction_id: str) -> dict[str, Any]:
        cached = await cache_service.get(f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}")
        if not isinstance(cached, dict):
            raise ValueError("Prediction not found or expired")
        return cached

    @staticmethod
    def _find_route(payload: dict[str, Any], route_id: str) -> dict[str, Any]:
        for route in list(payload.get("paths") or []):
            if isinstance(route, dict) and str(route.get("id") or "") == route_id:
                return route
        raise ValueError("Requested route not found")

    @staticmethod
    def _find_step(route: dict[str, Any], node_id: str) -> dict[str, Any]:
        for step in list(route.get("steps") or []):
            if isinstance(step, dict) and str(step.get("node_id") or "") == node_id:
                return step
        raise ValueError("Requested node not found in the route")

    @staticmethod
    def _find_steps(route: dict[str, Any], skip_node_ids: list[str]) -> list[dict[str, Any]]:
        normalized_ids = [str(node_id).strip() for node_id in skip_node_ids if str(node_id).strip()]
        matched = [
            step
            for step in list(route.get("steps") or [])
            if isinstance(step, dict) and str(step.get("node_id") or "") in normalized_ids
        ]
        if matched:
            return matched
        fallback = list(route.get("steps") or [])
        if fallback and isinstance(fallback[0], dict):
            return [fallback[0]]
        raise ValueError("Requested node not found in the route")

    @staticmethod
    def _maybe_uuid(value: Any) -> UUID | None:
        try:
            return UUID(str(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _step_rationale(*, strategy_type: str, node_name: str, is_target: bool) -> str:
        if is_target:
            return f"这是目标节点 {node_name}，需要把概念、计算和表达三件事一起打通。"
        if strategy_type == "breakthrough":
            return f"{node_name} 作为回补节点出现，作用是在暴露出卡点后快速止损。"
        if strategy_type == "personalized":
            return f"{node_name} 被切进小步节奏里，目的是降低启动阻力并提高连续完成率。"
        return f"{node_name} 是前置链的一环，先补齐它能减少后续推导中的理解断层。"
