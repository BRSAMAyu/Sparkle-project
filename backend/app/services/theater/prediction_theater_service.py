from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import logging
import re
import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlencode
from uuid import UUID, uuid4

from sqlalchemy import String, cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.event_bus import event_bus_reliable
from app.core.exceptions import AuthorizationError, NotFoundError, SparkleException
from app.models.chat import ChatMessage, ChatSession, MessageRole
from app.models.cognitive import BehaviorPattern
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.models.plan import PlanType
from app.models.task import TaskType
from app.models.theater_candidate_bundle import TheaterCandidateBundle
from app.models.theater_prediction import TheaterPrediction
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate
from app.services.cognitive_service import CognitiveService
from app.services.expansion_service import ExpansionService
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService
from app.services.galaxy_service import GalaxyService
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.insight_copy import present_pattern_name
from app.services.llm_fallback_utils import analysis_llm
from app.services.plan_service import PlanService
from app.services.system_update_service import SystemUpdateService, build_system_update
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


async def _result_all(result: Any) -> list[Any]:
    rows = result.all()
    if inspect.isawaitable(rows):
        rows = await rows
    return list(rows)


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


def _topic_key(topic: str) -> str:
    return " ".join(str(topic or "").strip().casefold().split())


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
    current_mastery: float | None
    predicted_mastery: float | None
    risk_level: str
    estimated_minutes: int
    day_label: str
    checkpoint_label: str | None = None
    mapped_galaxy_node_id: str | None = None
    source_type: str = "graph_verified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "rationale": self.rationale,
            "current_mastery": round(self.current_mastery, 2) if self.current_mastery is not None else None,
            "predicted_mastery": round(self.predicted_mastery, 2) if self.predicted_mastery is not None else None,
            "risk_level": self.risk_level,
            "estimated_minutes": self.estimated_minutes,
            "day_label": self.day_label,
            "checkpoint_label": self.checkpoint_label,
            "mapped_galaxy_node_id": self.mapped_galaxy_node_id,
            "source_type": self.source_type,
        }


@dataclass(frozen=True)
class TheaterPathOption:
    id: str
    title: str
    summary: str
    strategy_type: str
    expert_ids: list[str]
    estimated_completion_rate: float | None
    estimated_mastery: float | None
    daily_minutes: int
    risks: list[str]
    steps: list[TheaterPathStep]
    route_score: float = 0.0
    checkpoint_days: list[int] | None = None
    week_one_tasks: list[dict[str, Any]] | None = None
    data_sufficiency_score: float = 0.0
    data_quality: str = "low"
    completion_range_low: float = 0.0
    completion_range_high: float = 0.0
    mastery_range_low: float = 0.0
    mastery_range_high: float = 0.0
    calibration_basis: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "strategy_type": self.strategy_type,
            "expert_ids": self.expert_ids,
            "estimated_completion_rate": (
                round(self.estimated_completion_rate, 4) if self.estimated_completion_rate is not None else None
            ),
            "estimated_mastery": round(self.estimated_mastery, 2) if self.estimated_mastery is not None else None,
            "daily_minutes": self.daily_minutes,
            "risks": self.risks,
            "route_score": round(self.route_score, 2),
            "checkpoint_days": list(self.checkpoint_days or []),
            "week_one_tasks": list(self.week_one_tasks or []),
            "data_sufficiency_score": round(self.data_sufficiency_score, 4),
            "confidence_score": round(self.data_sufficiency_score, 4),
            "data_quality": self.data_quality,
            "completion_range_low": round(self.completion_range_low, 4) if self.completion_range_low else 0.0,
            "completion_range_high": round(self.completion_range_high, 4) if self.completion_range_high else 0.0,
            "mastery_range_low": round(self.mastery_range_low, 2) if self.mastery_range_low else 0.0,
            "mastery_range_high": round(self.mastery_range_high, 2) if self.mastery_range_high else 0.0,
            "calibration_basis": self.calibration_basis,
            "steps": [step.to_dict() for step in self.steps],
        }


@dataclass(frozen=True)
class TheaterTargetContext:
    name: str
    description: str
    target_node_id: str | None
    resolution_mode: str
    backbone: list[dict[str, Any]]
    semantic_matches: list[dict[str, Any]]
    disclaimer: str | None = None


class PredictionAccuracyTracker:
    PREDICTION_KEY_PREFIX = "theater:prediction:"
    SUMMARY_KEY_PREFIX = "theater:prediction:summary:"
    USER_INDEX_KEY = "theater:prediction:users"
    USER_PREDICTION_INDEX_PREFIX = "theater:prediction:user:"
    TTL_SECONDS = 60 * 60 * 24 * 7

    async def record_prediction(self, payload: dict[str, Any]) -> None:
        prediction_id = str(payload.get("prediction_id") or "").strip()
        if not prediction_id:
            return
        await cache_service.set(f"{self.PREDICTION_KEY_PREFIX}{prediction_id}", payload, ttl=self.TTL_SECONDS)
        redis_client = cache_service.redis
        user_id = str(payload.get("user_id") or "").strip()
        if redis_client is not None and user_id:
            await redis_client.sadd(self.USER_INDEX_KEY, user_id)
            await redis_client.sadd(f"{self.USER_PREDICTION_INDEX_PREFIX}{user_id}", prediction_id)
            await redis_client.expire(f"{self.USER_PREDICTION_INDEX_PREFIX}{user_id}", self.TTL_SECONDS)

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
        completion_range_low = predicted.get("completion_range_low")
        completion_range_high = predicted.get("completion_range_high")
        mastery_range_low = predicted.get("mastery_range_low")
        mastery_range_high = predicted.get("mastery_range_high")
        completion_error = abs(predicted_completion - actual_completion_rate)
        mastery_error = abs(predicted_mastery - actual_mastery)
        accuracy_score = _clamp(1.0 - ((completion_error * 0.55) + (mastery_error / 100.0 * 0.45)), 0.0, 1.0)
        within_completion_range = (
            completion_range_low is not None
            and completion_range_high is not None
            and float(completion_range_low) <= actual_completion_rate <= float(completion_range_high)
        )
        within_mastery_range = (
            mastery_range_low is not None
            and mastery_range_high is not None
            and float(mastery_range_low) <= actual_mastery <= float(mastery_range_high)
        )

        summary = {
            "prediction_id": prediction_id,
            "topic": str(cached.get("topic") or ""),
            "date": str(cached.get("generated_at") or _utcnow().date().isoformat())[:10],
            "predicted_completion_rate": round(predicted_completion, 4),
            "predicted_mastery": round(predicted_mastery, 2),
            "actual_completion_rate": round(actual_completion_rate, 4),
            "actual_mastery": round(actual_mastery, 2),
            "completion_error": round(completion_error, 4),
            "mastery_error": round(mastery_error, 2),
            "accuracy_score": round(accuracy_score, 4),
            "within_completion_range": within_completion_range,
            "within_mastery_range": within_mastery_range,
            "within_predicted_range": bool(within_completion_range and within_mastery_range),
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
    MAX_GRAPH_NODES = 14
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
        simulation_session_id: str | None = None,
        context: str | None = None,
        available_time_per_day: int | None = None,
        current_level: str | None = None,
        materials: str | None = None,
        goal_type: str | None = None,
    ) -> dict[str, Any]:
        try:
            return await asyncio.wait_for(
                self._generate_prediction_payload(
                    user_id=user_id,
                    topic=topic,
                    target_node_id=target_node_id,
                    horizon_days=horizon_days,
                    preview_mode=preview_mode,
                    simulation_session_id=simulation_session_id,
                    context=context,
                    available_time_per_day=available_time_per_day,
                    current_level=current_level,
                    materials=materials,
                    goal_type=goal_type,
                ),
                timeout=self.PREDICTION_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise TheaterTimeoutError() from exc

    async def _generate_prediction_payload(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None = None,
        horizon_days: int = 14,
        preview_mode: bool = False,
        simulation_session_id: str | None = None,
        context: str | None = None,
        available_time_per_day: int | None = None,
        current_level: str | None = None,
        materials: str | None = None,
        goal_type: str | None = None,
    ) -> dict[str, Any]:
        request_context = {
            "context": str(context or "").strip() or None,
            "available_time_per_day": available_time_per_day,
            "current_level": str(current_level or "").strip() or None,
            "materials": str(materials or "").strip() or None,
            "goal_type": str(goal_type or "").strip() or None,
        }
        if (
            target_node_id is None
            and not preview_mode
            and await self._requires_clarification(
                user_id=user_id,
                topic=topic,
                request_context=request_context,
            )
        ):
            return self._build_clarification_response(topic=topic)
        target_context = await self._resolve_target_context(
            user_id=user_id,
            topic=topic,
            target_node_id=target_node_id,
            context=request_context["context"],
        )
        backbone = list(target_context.backbone)
        if not backbone:
            raise ValueError("Unable to generate a learning backbone for the selected topic")

        mastery_map = await self._get_mastery_map(user_id)
        study_preferences = await self._build_user_learning_profile(
            user_id,
            available_time_per_day=available_time_per_day,
        )
        pattern_names = await self._top_pattern_names(user_id)
        error_evidence = await self._related_error_evidence(
            user_id=user_id,
            topic=topic,
            backbone=backbone,
        )
        mastery_evidence = self._related_mastery_evidence(
            backbone=backbone,
            mastery_map=mastery_map,
        )
        calibration_profile = await self._build_prediction_calibration(user_id)
        topic_calibration = await self._topic_calibration_signal(user_id=user_id, topic=topic)
        options = await self._build_path_options(
            topic=topic,
            target_name=target_context.name,
            backbone=backbone,
            mastery_map=mastery_map,
            horizon_days=max(7, min(horizon_days, 30)),
            study_preferences=study_preferences,
            pattern_names=pattern_names,
            calibration_profile=calibration_profile,
            has_graph_context=target_context.resolution_mode != "freeform_only",
            request_context=request_context,
            mastery_evidence=mastery_evidence,
            error_evidence=error_evidence,
            topic_calibration=topic_calibration,
            risk_overrides=(
                await self._assess_step_risks(backbone, mastery_map)
                if target_context.resolution_mode != "graph_explicit"
                else None
            ),
        )
        selected_prediction = options[0].to_dict() if options else {}
        prediction_id = str(uuid4())
        graph_bundle = {"nodes": [], "edges": []}
        discussion: list[dict[str, Any]] = []
        candidate_bundle_id = ""
        if not preview_mode:
            graph_bundle = await self._build_graph_bundle(
                backbone,
                mastery_map,
                target_context=target_context,
            )
            discussion = await self._build_discussion(
                topic=topic,
                target_name=target_context.name,
                options=options,
                graph_bundle=graph_bundle,
                pattern_names=pattern_names,
            )
            if target_context.resolution_mode != "graph_explicit":
                candidate_bundle_id = await self._persist_candidate_bundle(
                    user_id=user_id,
                    prediction_id=prediction_id,
                    topic=topic,
                    target_context=target_context,
                    graph_bundle=graph_bundle,
                )
        generated_at = _utcnow()
        timeline = self._build_timeline(
            options,
            discussion,
            available_time_per_day=int(study_preferences.get("average_session_minutes") or 40),
        )
        payload = {
            "status": "ready",
            "prediction_id": prediction_id,
            "user_id": str(user_id),
            "topic": topic,
            "simulation_session_id": simulation_session_id,
            "target_node_id": target_context.target_node_id,
            "target_name": target_context.name,
            "candidate_bundle_id": candidate_bundle_id,
            "horizon_days": horizon_days,
            "generated_at": generated_at.isoformat(),
            "paths": [option.to_dict() for option in options],
            "discussion_turns": discussion,
            "graph": graph_bundle,
            "timeline": timeline,
            "selected_prediction": selected_prediction,
            "recommended_route_id": options[0].id if options else "",
            "target_resolution_mode": target_context.resolution_mode,
            "disclaimer": (
                target_context.disclaimer
                if target_context.resolution_mode in {"freeform_only", "hybrid_semantic"}
                and int(calibration_profile.get("sample_count") or 0) < 3
                else None
            ),
            "calibration_prompt": (
                self._build_calibration_prompt(
                    topic=topic,
                    age_days=topic_calibration.get("latest_pending_age_days"),
                )
                if int(topic_calibration.get("sample_count") or 0) < 3
                and bool(options)
                and str(options[0].data_quality) == "low"
                else None
            ),
            "accuracy_tracking": self._build_accuracy_tracking(
                prediction_id=prediction_id,
                generated_at=generated_at,
                calibration_profile=calibration_profile,
            ),
            "evidence_summary": self._build_prediction_evidence_summary(
                target_context=target_context,
                options=options,
                mastery_evidence=mastery_evidence,
                error_evidence=error_evidence,
                calibration_profile=calibration_profile,
                topic_calibration=topic_calibration,
            ),
            "recommended_next_action": self._build_prediction_next_action(
                prediction_id=prediction_id,
                topic=topic,
                recommended_route=options[0].to_dict() if options else {},
            ),
            "routing_notes": {
                "patterns": pattern_names,
                "recommended_entry": options[0].title if options else "稳扎稳打",
                "target_resolution_mode": target_context.resolution_mode,
                "semantic_matches": target_context.semantic_matches,
                "calibration_profile": calibration_profile,
                "request_context": request_context,
                "mastery_evidence": mastery_evidence,
                "error_evidence": error_evidence,
                "topic_calibration": topic_calibration,
            },
            "preview_mode": preview_mode,
        }
        await self.accuracy.record_prediction(payload)
        await self._persist_prediction(payload)
        if not preview_mode:
            query = {"topic": topic}
            if target_context.target_node_id:
                query["target_node_id"] = target_context.target_node_id
            if simulation_session_id:
                query["simulation_session_id"] = simulation_session_id
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
                        "simulation_session_id": simulation_session_id,
                        "title": options[0].title if options else target_context.name,
                        "path_count": len(options),
                        "deep_link": deep_link,
                        "candidate_bundle_id": candidate_bundle_id,
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
        if not preview_mode and target_context.resolution_mode != "graph_explicit" and self.db is not None:
            await self.db.commit()
        return payload

    async def _resolve_target_context(
        self,
        *,
        user_id: UUID,
        topic: str,
        target_node_id: UUID | None,
        context: str | None = None,
    ) -> TheaterTargetContext:
        if target_node_id is not None:
            target_node = await self._resolve_target_node_for_user(
                user_id=user_id,
                topic=topic,
                target_node_id=target_node_id,
            )
            return await self._build_target_context_from_node(user_id=user_id, target_node=target_node)
        return await self._build_free_mode_target_context(topic, context=context)

    async def _requires_clarification(
        self,
        *,
        user_id: UUID,
        topic: str,
        request_context: dict[str, Any],
    ) -> bool:
        if len(str(topic or "").strip()) > 20:
            return False
        if str(request_context.get("context") or "").strip():
            return False
        semantic_matches = await self._topic_graph_candidates(user_id=user_id, topic=topic)
        return not bool(semantic_matches)

    def _build_clarification_response(self, *, topic: str) -> dict[str, Any]:
        return {
            "status": "clarification_needed",
            "topic": topic,
            "questions": [
                "你学这个是为了什么？（考试/项目/兴趣）",
                "你目前对这个主题了解多少？（完全没接触/学过基础/有一定经验）",
                "你有多少时间可以投入？（每天/每周的大概时长）",
                "你有在用什么学习材料？（教材名/课程名/无）",
            ],
            "prediction": None,
        }

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
        backbone = []
        for item in learning_path:
            if item.get("is_optional"):
                continue
            node_id = str(item.get("id") or "")
            if not node_id:
                continue
            backbone.append(
                {
                    "id": node_id,
                    "name": str(item.get("name") or "当前主题"),
                    "description": str(item.get("description") or target_node.description or ""),
                    "node_type": "target" if bool(item.get("is_target")) else "concept",
                    "is_target": bool(item.get("is_target")),
                    "source_type": "graph_explicit",
                    "mapped_galaxy_node_id": node_id,
                    "candidate_status": None,
                    "aliases": [],
                    "sector_weights": dict(item.get("sector_weights") or {}),
                }
            )
        if not backbone:
            raise ValueError("Unable to generate a learning backbone for the selected topic")
        return TheaterTargetContext(
            name=str(target_node.name or "当前主题"),
            description=str(target_node.description or ""),
            target_node_id=str(target_node.id),
            resolution_mode="graph_explicit",
            backbone=backbone,
            semantic_matches=[],
            disclaimer=None,
        )

    async def _build_free_mode_target_context(self, topic: str, *, context: str | None = None) -> TheaterTargetContext:
        fallback = self._fallback_free_mode_target(topic)
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是学习路径推演助手。请只返回严格 JSON 对象，不要输出 Markdown。"
                        "必须包含字段：target_name、description、prerequisites、core_concepts、"
                        "milestones、misconceptions、applications、aliases。"
                        "所有字段值都必须使用中文表达；术语缩写如 LLM、RAG 可以保留。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"学习主题：{topic}\n"
                        f"补充说明：{str(context or '').strip() or '无'}\n"
                        "请把它理解为一个需要自由推演的学习目标，输出：\n"
                        "1. 一个清晰的目标名称。\n"
                        "2. 一段中文描述。\n"
                        "3. 2-4 个前置知识。\n"
                        "4. 3-5 个核心概念。\n"
                        "5. 2-3 个里程碑。\n"
                        "6. 1-3 个常见误区。\n"
                        "7. 1-2 个典型应用场景。\n"
                        "8. 1-3 个别名或相关叫法。\n"
                        "请偏向结构化学习视角，而不是只给课程目录。"
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.2,
        )
        parsed = payload if isinstance(payload, dict) else fallback
        for field in (
            "target_name",
            "description",
            "prerequisites",
            "core_concepts",
            "milestones",
            "misconceptions",
            "applications",
            "aliases",
        ):
            if field not in parsed or parsed.get(field) in (None, "", []):
                parsed[field] = self._default_free_mode_field(field, topic, fallback=fallback)
        target_name = str(parsed.get("target_name") or fallback["target_name"]).strip() or fallback["target_name"]
        description = str(parsed.get("description") or fallback["description"]).strip() or fallback["description"]
        prerequisites = self._coerce_string_list(parsed.get("prerequisites")) or list(fallback["prerequisites"])
        core_concepts = self._coerce_string_list(parsed.get("core_concepts")) or list(fallback["core_concepts"])
        milestones = self._coerce_string_list(parsed.get("milestones")) or list(fallback["milestones"])
        misconceptions = self._coerce_string_list(parsed.get("misconceptions")) or list(fallback["misconceptions"])
        applications = self._coerce_string_list(parsed.get("applications")) or list(fallback["applications"])
        aliases = self._coerce_string_list(parsed.get("aliases")) or list(fallback["aliases"])
        backbone = self._build_freeform_backbone(
            target_name=target_name,
            description=description,
            prerequisites=prerequisites,
            core_concepts=core_concepts,
            milestones=milestones,
            misconceptions=misconceptions,
            applications=applications,
            aliases=aliases,
        )
        enriched_backbone, semantic_matches = await self._semantic_enrich_freeform_nodes(
            topic=topic,
            target_name=target_name,
            backbone=backbone,
        )
        return TheaterTargetContext(
            name=target_name,
            description=description,
            target_node_id=None,
            resolution_mode="hybrid_semantic" if semantic_matches else "freeform_only",
            backbone=enriched_backbone,
            semantic_matches=semantic_matches,
            disclaimer="此推演基于AI对主题的通用理解，未经你的实际学习数据验证。预测数字仅供参考，不代表真实准确度。",
        )

    def _default_free_mode_field(
        self,
        field: str,
        topic: str,
        *,
        fallback: dict[str, Any] | None = None,
    ) -> Any:
        base = fallback or self._fallback_free_mode_target(topic)
        if field == "target_name":
            return base["target_name"]
        if field == "description":
            return base["description"]
        if field == "prerequisites":
            return list(base["prerequisites"])
        if field == "core_concepts":
            return list(base["core_concepts"])
        if field == "milestones":
            return list(base["milestones"])
        if field == "misconceptions":
            return list(base["misconceptions"])
        if field == "applications":
            return list(base["applications"])
        if field == "aliases":
            return list(base["aliases"])
        return ""

    def _fallback_free_mode_target(self, topic: str) -> dict[str, Any]:
        terms = _normalized_topic_terms(topic)
        candidates = [term for term in terms if len(term) >= 2]
        target_name = candidates[0] if candidates else topic.strip() or "当前学习主题"
        normalized_target = target_name if target_name.endswith("学习路径") else f"{target_name} 学习路径"
        prerequisites = candidates[1:4]
        if not prerequisites:
            prerequisites = [f"{target_name} 的基础概念", f"{target_name} 的问题框架"]
        core_concepts = [
            f"{target_name} 的基本原理",
            f"{target_name} 的关键组成",
            f"{target_name} 的实践流程",
        ]
        milestones = [f"完成一个 {target_name} 入门案例", f"能够解释 {target_name} 的核心思路"]
        return {
            "target_name": normalized_target,
            "description": f"围绕 {target_name} 生成一张独立于现有知识星图的中文自由推演概念图。",
            "prerequisites": prerequisites[:3],
            "core_concepts": core_concepts[:4],
            "milestones": milestones[:2],
            "misconceptions": [f"把 {target_name} 当成零散技巧记忆，而不是系统能力"],
            "applications": [f"用 {target_name} 解决一个真实问题"],
            "aliases": [target_name],
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

    def _build_freeform_backbone(
        self,
        *,
        target_name: str,
        description: str,
        prerequisites: list[str],
        core_concepts: list[str],
        milestones: list[str],
        misconceptions: list[str],
        applications: list[str],
        aliases: list[str],
    ) -> list[dict[str, Any]]:
        nodes: list[dict[str, Any]] = []

        def append_nodes(items: list[str], *, node_type: str, is_target: bool = False) -> None:
            for item in items:
                name = str(item).strip()
                if not name:
                    continue
                nodes.append(
                    {
                        "id": f"free-node-{len(nodes) + 1}",
                        "name": name,
                        "description": self._freeform_node_description(
                            target_name=target_name,
                            description=description,
                            node_name=name,
                            node_type=node_type,
                        ),
                        "node_type": node_type,
                        "is_target": is_target,
                        "source_type": "freeform",
                        "mapped_galaxy_node_id": None,
                        "candidate_status": "pending_review",
                        "aliases": aliases if is_target else [],
                        "sector_weights": {},
                    }
                )

        append_nodes(prerequisites[:3], node_type="prerequisite")
        append_nodes(core_concepts[:4], node_type="concept")
        append_nodes([target_name], node_type="target", is_target=True)
        append_nodes(milestones[:2], node_type="milestone")
        append_nodes(applications[:2], node_type="application")
        append_nodes(misconceptions[:2], node_type="misconception")

        deduped: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        for node in nodes:
            normalized_name = str(node.get("name") or "").strip().lower()
            if not normalized_name or normalized_name in seen_names:
                continue
            seen_names.add(normalized_name)
            deduped.append(node)

        if len(deduped) < 8:
            append_nodes(
                [
                    f"{target_name} 的评估标准",
                    f"{target_name} 的常见任务",
                    f"{target_name} 的迁移练习",
                ],
                node_type="concept",
            )
            deduped = []
            seen_names = set()
            for node in nodes:
                normalized_name = str(node.get("name") or "").strip().lower()
                if not normalized_name or normalized_name in seen_names:
                    continue
                seen_names.add(normalized_name)
                deduped.append(node)
        return deduped[: self.MAX_GRAPH_NODES]

    @staticmethod
    def _freeform_node_description(
        *,
        target_name: str,
        description: str,
        node_name: str,
        node_type: str,
    ) -> str:
        mapping = {
            "prerequisite": f"{node_name} 是进入 {target_name} 前需要先补齐的前置基础。",
            "concept": f"{node_name} 是理解 {target_name} 时必须真正吃透的核心概念。",
            "target": description or f"{target_name} 是本轮推演的核心目标。",
            "milestone": f"{node_name} 是衡量 {target_name} 是否开始成形的阶段里程碑。",
            "application": f"{node_name} 展示了 {target_name} 可以落地到什么样的真实场景。",
            "misconception": f"{node_name} 是学习 {target_name} 时最容易踩到的误区。",
        }
        return mapping.get(node_type, description or f"{node_name} 是 {target_name} 推演图中的关键节点。")

    async def _semantic_enrich_freeform_nodes(
        self,
        *,
        topic: str,
        target_name: str,
        backbone: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if self.db is None or not backbone:
            return backbone, []
        galaxy = GalaxyService(self.db)
        enriched: list[dict[str, Any]] = []
        semantic_matches: list[dict[str, Any]] = []
        for node in backbone:
            updated = dict(node)
            queries = self._dedupe_preserve_order(
                [
                    str(node.get("name") or ""),
                    *self._coerce_string_list(node.get("aliases")),
                    topic,
                    target_name,
                ]
            )
            best_match: dict[str, Any] | None = None
            for query in queries[:3]:
                try:
                    results = await galaxy.semantic_search_nodes(query, limit=2, threshold=0.22)
                except Exception as exc:
                    logger.warning(
                        "Prediction theater semantic node enrichment failed for query %s: %s",
                        query,
                        exc,
                        exc_info=True,
                    )
                    results = []
                for candidate in results:
                    confidence = self._semantic_match_confidence(
                        query=query,
                        node_name=str(node.get("name") or ""),
                        candidate_name=str(candidate.name or ""),
                        candidate_description=str(candidate.description or ""),
                    )
                    if confidence < 0.56:
                        continue
                    payload = self._build_semantic_match_payload(
                        freeform_node=node,
                        query=query,
                        candidate=candidate,
                        confidence=confidence,
                    )
                    if best_match is None or float(payload["confidence"]) > float(best_match["confidence"]):
                        best_match = payload
            if best_match is not None:
                updated["mapped_galaxy_node_id"] = str(best_match["galaxy_node_id"])
                updated["sector_weights"] = dict(best_match.get("sector_weights") or {})
                semantic_matches.append(best_match)
            enriched.append(updated)
        return enriched, semantic_matches

    async def _topic_graph_candidates(
        self,
        *,
        user_id: UUID,
        topic: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        del user_id
        if self.db is None or not str(topic or "").strip():
            return []
        galaxy = GalaxyService(self.db)
        try:
            results = await galaxy.semantic_search_nodes(topic, limit=limit, threshold=0.22)
        except Exception as exc:
            logger.warning("Prediction theater topic candidate lookup failed for topic %s: %s", topic, exc, exc_info=True)
            return []
        return [
            {
                "node_id": str(item.id),
                "node_name": str(item.name or ""),
                "description": str(item.description or ""),
            }
            for item in results
            if str(item.name or "").strip()
        ]

    @staticmethod
    def _semantic_match_confidence(
        *,
        query: str,
        node_name: str,
        candidate_name: str,
        candidate_description: str,
    ) -> float:
        query_terms = {term for term in re.split(r"[\s/,_-]+", query.lower()) if len(term) >= 2}
        source_terms = {term for term in re.split(r"[\s/,_-]+", node_name.lower()) if len(term) >= 2}
        candidate_terms = {
            term
            for term in re.split(r"[\s/,_-]+", f"{candidate_name} {candidate_description}".lower())
            if len(term) >= 2
        }
        overlap = len((query_terms | source_terms) & candidate_terms)
        contains = (
            1.0 if node_name and node_name.lower() in f"{candidate_name} {candidate_description}".lower() else 0.0
        )
        return _clamp((overlap * 0.14) + (contains * 0.32) + 0.28, 0.0, 0.96)

    def _build_semantic_match_payload(
        self,
        *,
        freeform_node: dict[str, Any],
        query: str,
        candidate: KnowledgeNode,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "freeform_node_id": str(freeform_node.get("id") or ""),
            "freeform_node_name": str(freeform_node.get("name") or ""),
            "galaxy_node_id": str(candidate.id),
            "galaxy_node_name": str(candidate.name or ""),
            "confidence": round(confidence, 2),
            "evidence": f"“{freeform_node.get('name') or query}” 与知识星图节点“{candidate.name or ''}”语义接近，可作为参考映射。",
            "query": query,
            "sector_weights": dict(getattr(candidate, "sector_weights", None) or {}),
        }

    async def _assess_step_risks(
        self,
        steps: list[dict[str, Any]],
        user_mastery: dict[str, float],
    ) -> list[str]:
        if not steps:
            return []
        cache_key = self._risk_assessment_cache_key(
            steps=steps,
            user_mastery=user_mastery,
        )
        cached = await cache_service.get(cache_key)
        if isinstance(cached, list) and cached:
            return [str(item).strip().lower() for item in cached]
        serialized_steps = [
            {
                "id": str(step.get("id") or ""),
                "name": str(step.get("name") or step.get("node_name") or ""),
                "current_mastery": round(user_mastery.get(str(step.get("id") or ""), 0.0), 2),
            }
            for step in steps
        ]
        fallback = [
            self._risk_level_for_step(
                current_mastery=float(item.get("current_mastery") or 0.0),
                index=index,
                total=len(serialized_steps),
            )
            for index, item in enumerate(serialized_steps)
        ]
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "请返回严格 JSON 数组。数组中的每一项都必须是 low、medium、high 之一，表示学习步骤的风险等级。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "请根据每个学习步骤的标题和当前掌握度，判断它对当前用户的推进风险。\n"
                        f"步骤数据：{json.dumps(serialized_steps, ensure_ascii=False)}"
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.15,
        )
        if not isinstance(payload, list):
            return fallback
        normalized: list[str] = []
        for index, item in enumerate(payload[: len(serialized_steps)]):
            level = str(item).strip().lower()
            normalized.append(level if level in {"low", "medium", "high"} else fallback[index])
        while len(normalized) < len(serialized_steps):
            normalized.append(fallback[len(normalized)])
        await cache_service.set(cache_key, normalized, ttl=60 * 60 * 12)
        return normalized

    @staticmethod
    def _risk_assessment_cache_key(
        *,
        steps: list[dict[str, Any]],
        user_mastery: dict[str, float],
    ) -> str:
        fingerprint = json.dumps(
            {
                "steps": [
                    {
                        "id": str(step.get("id") or ""),
                        "name": str(step.get("name") or step.get("node_name") or ""),
                    }
                    for step in steps
                ],
                "mastery": {str(key): round(float(value), 2) for key, value in sorted(user_mastery.items())},
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        return f"theater:risk-assessment:{hashlib.sha256(fingerprint.encode('utf-8')).hexdigest()}"

    async def simulate_what_if(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        skip_node_id: str | None = None,
        skip_node_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
        selected_route = self._find_route(cached, route_id)
        skipped_steps = self._find_steps(
            selected_route,
            skip_node_ids=list(skip_node_ids or ([skip_node_id] if skip_node_id else [])),
        )
        skipped_step = skipped_steps[0]
        target_name = str(cached.get("target_name") or "")

        downstream = [
            step
            for step in list(selected_route.get("steps") or [])
            if int(step.get("index") or 0) > min(int(item.get("index") or 0) for item in skipped_steps)
        ]
        mastery_penalty = (
            6
            + (len(downstream) * 2.5)
            + sum(
                5
                if str(step.get("risk_level") or "") == "high"
                else (3 if str(step.get("risk_level") or "") == "medium" else 1.5)
                for step in skipped_steps
            )
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

        suggestion = f"建议不要完全跳过 {skipped_step.get('node_name')}，可以把它压缩成 {max(20, int(skipped_step.get('estimated_minutes') or 30) // 2)} 分钟速览。"
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
        cached = await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
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

    async def promote_node_to_galaxy(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        theater_node_id: str,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
        graph = dict(cached.get("graph") or {})
        nodes = [node for node in list(graph.get("nodes") or []) if isinstance(node, dict)]
        node = next(
            (item for item in nodes if str(item.get("id") or "") == theater_node_id),
            None,
        )
        if node is None:
            raise ValueError("Theater node not found in this prediction")

        source_type = str(node.get("source_type") or "freeform")
        mapped_node_id = self._maybe_uuid(node.get("mapped_galaxy_node_id"))
        if mapped_node_id is not None and source_type in {"graph_explicit", "hybrid_reference"}:
            existing = await self.db.get(KnowledgeNode, mapped_node_id)
            if existing is not None:
                await self._patch_prediction_cache_with_promoted_node(
                    cached=cached,
                    prediction_id=prediction_id,
                    theater_node_id=theater_node_id,
                    galaxy_node_id=str(existing.id),
                    candidate_status=None,
                )
                return {
                    "prediction_id": prediction_id,
                    "theater_node_id": theater_node_id,
                    "node_name": existing.name,
                    "galaxy_node_id": str(existing.id),
                    "created": False,
                    "source_type": source_type,
                }

        payload = await self._build_galaxy_candidate_from_prediction(
            user_id=user_id,
            cached=cached,
            theater_node=node,
        )
        expansion_service = ExpansionService(self.db)
        try:
            promoted_node, created = await expansion_service.upsert_node_from_candidate(
                user_id=user_id,
                candidate=payload["candidate"],
                trigger_node_id=payload["trigger_node_id"],
                parent_node_id=payload["parent_node_id"],
                subject_id=payload["subject_id"],
                source_type="theater_candidate",
                generate_embedding=True,
                unlock_for_user=True,
                commit=False,
                invalidate_caches=False,
            )
            await self._record_candidate_bundle_promotion(
                user_id=user_id,
                prediction_id=prediction_id,
                theater_node_id=theater_node_id,
                galaxy_node=promoted_node,
                commit=False,
            )
            await self.db.commit()
        except Exception as exc:
            await self.db.rollback()
            logger.error("Prediction theater candidate promotion failed: %s", exc, exc_info=True)
            raise

        await expansion_service._invalidate_after_graph_mutation(user_id)
        await self._patch_prediction_cache_with_promoted_node(
            cached=cached,
            prediction_id=prediction_id,
            theater_node_id=theater_node_id,
            galaxy_node_id=str(promoted_node.id),
            candidate_status=None,
        )
        return {
            "prediction_id": prediction_id,
            "theater_node_id": theater_node_id,
            "node_name": promoted_node.name,
            "galaxy_node_id": str(promoted_node.id),
            "created": created,
            "source_type": source_type,
        }

    async def adopt_prediction(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        source_chat_session_id: str | None = None,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
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
                total_estimated_hours=max(
                    1.0, sum(int(step.get("estimated_minutes") or 25) for step in steps) / 60.0
                ),
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
            "candidate_bundle_id": cached.get("candidate_bundle_id"),
            "target_resolution_mode": cached.get("target_resolution_mode"),
            "semantic_matches": (dict(cached.get("routing_notes") or {}).get("semantic_matches") or []),
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
            node_id = step.get("mapped_galaxy_node_id") or step.get("node_id")
            if not node_id:
                continue
            try:
                await self.structure.tag_node_signal(UUID(str(node_id)), "signal:predicted_risk", active=True)
            except Exception as exc:
                logger.warning("Failed to tag predicted risk node %s: %s", node_id, exc, exc_info=True)
                continue

        cached["selected_prediction"] = selected_route
        cached["adopted_plan_id"] = str(plan.id)
        cached["adopted_at"] = _utcnow().isoformat()
        await cache_service.set(
            f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
            cached,
            ttl=self.accuracy.TTL_SECONDS,
        )
        await self._update_prediction_db(
            user_id=user_id,
            prediction_id=prediction_id,
            updates={
                "adopted_plan_id": plan.id,
                "adopted_at": _utcnow(),
                "selected_prediction": selected_route,
            },
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
        except Exception as exc:
            logger.warning("Failed to create prediction theater cognitive fragment: %s", exc, exc_info=True)

        query = {
            "topic": str(cached.get("topic") or ""),
            "prediction_id": prediction_id,
            "route_id": route_id,
        }
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

    async def get_prediction(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
    ) -> dict[str, Any]:
        return await self._get_prediction_for_user_or_raise(
            prediction_id,
            user_id=user_id,
        )

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
        cached = await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
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
        await self._update_prediction_db(
            user_id=user_id,
            prediction_id=prediction_id,
            updates={
                "accuracy_status": "recorded",
                "accuracy_summary": summary,
                "accuracy_tracking": cached["accuracy_tracking"],
            },
        )
        return summary

    async def get_accuracy_summary(self, *, user_id: UUID, prediction_id: str) -> dict[str, Any] | None:
        await self._get_prediction_for_user_or_raise(prediction_id, user_id=user_id)
        cached = await self.accuracy.get_summary(prediction_id)
        if cached is not None:
            return {
                **cached,
                "comparison_pairs": await self._recent_comparison_pairs(user_id=user_id, limit=10),
            }
        # DB fallback
        if self.db is None:
            return None
        try:
            result = await self.db.execute(
                select(TheaterPrediction.accuracy_summary).where(
                    TheaterPrediction.prediction_id == prediction_id,
                    TheaterPrediction.user_id == user_id,
                    TheaterPrediction.deleted_at.is_(None),
                )
            )
            row = result.scalar_one_or_none()
            if not isinstance(row, dict):
                return None
            return {
                **row,
                "comparison_pairs": await self._recent_comparison_pairs(user_id=user_id, limit=10),
            }
        except Exception as exc:
            logger.warning("Prediction accuracy summary lookup failed for user %s: %s", user_id, exc, exc_info=True)
            return None

    async def get_accuracy_overview(self, *, user_id: UUID) -> dict[str, Any]:
        calibration = await self._build_prediction_calibration(user_id)
        sample_count = int(calibration.get("sample_count") or 0)
        avg_accuracy_score = float(calibration.get("avg_accuracy_score") or 0.0)
        coverage_rate = calibration.get("coverage_rate")
        if sample_count == 0:
            trend = "insufficient_data"
        elif avg_accuracy_score >= 0.8:
            trend = "stable"
        elif avg_accuracy_score >= 0.65:
            trend = "improving"
        else:
            trend = "needs_adjustment"
        return {
            "sample_count": sample_count,
            "avg_accuracy_score": round(avg_accuracy_score, 4),
            "completion_bias_mean": round(float(calibration.get("completion_bias_mean") or 0.0), 4),
            "mastery_bias_mean": round(float(calibration.get("mastery_bias_mean") or 0.0), 2),
            "completion_mae": round(float(calibration.get("completion_mae") or 0.0), 4),
            "mastery_mae": round(float(calibration.get("mastery_mae") or 0.0), 2),
            "coverage_rate": round(float(coverage_rate), 4) if coverage_rate is not None else None,
            "data_sufficiency_score": round(
                float(calibration.get("data_sufficiency_score") or calibration.get("confidence_score") or 0.0),
                4,
            ),
            "confidence_score": round(
                float(calibration.get("data_sufficiency_score") or calibration.get("confidence_score") or 0.0),
                4,
            ),
            "data_status": str(calibration.get("data_status") or "cold_start"),
            "trend": trend,
        }

    async def auto_check_predictions(self, user_id: UUID) -> list[dict[str, Any]]:
        pending_predictions = await self._get_pending_predictions(user_id)
        today = _utcnow().date()
        results: list[dict[str, Any]] = []
        for prediction in pending_predictions:
            accuracy_tracking = dict(prediction.get("accuracy_tracking") or {})
            due_on = str(accuracy_tracking.get("due_on") or "").strip()
            if not due_on:
                continue
            try:
                due_date = date.fromisoformat(due_on)
            except ValueError:
                continue
            if due_date > today:
                continue
            actual = await self._compute_actual_from_prediction(user_id, prediction)
            if not actual:
                continue
            summary = await self.record_actual_outcome(
                user_id=user_id,
                prediction_id=str(prediction.get("prediction_id") or ""),
                actual_completion_rate=actual.get("completion"),
                actual_mastery=actual.get("mastery"),
            )
            results.append(summary)
        return results

    async def _get_pending_predictions(self, user_id: UUID) -> list[dict[str, Any]]:
        redis_client = cache_service.redis
        redis_ids: set[str] = set()
        results: list[dict[str, Any]] = []
        if redis_client is not None:
            indexed_prediction_ids = await redis_client.smembers(
                f"{self.accuracy.USER_PREDICTION_INDEX_PREFIX}{user_id}"
            )
            prediction_keys = [
                f"{self.accuracy.PREDICTION_KEY_PREFIX}{raw_id.decode() if isinstance(raw_id, bytes) else str(raw_id)}"
                for raw_id in indexed_prediction_ids
            ]
            if not prediction_keys:
                async for raw_key in redis_client.scan_iter(f"{self.accuracy.PREDICTION_KEY_PREFIX}*"):
                    key = raw_key.decode() if isinstance(raw_key, bytes) else str(raw_key)
                    prediction_keys.append(key)
            for key in prediction_keys:
                cached = await cache_service.get(key)
                if not isinstance(cached, dict):
                    continue
                if str(cached.get("user_id") or "").strip() != str(user_id):
                    continue
                accuracy_tracking = dict(cached.get("accuracy_tracking") or {})
                if str(accuracy_tracking.get("status") or "").strip() != "pending_feedback":
                    continue
                results.append(cached)
                redis_ids.add(str(cached.get("prediction_id") or ""))

        # DB fallback: fill in predictions that Redis missed (expired or
        # never cached) and that are due for accuracy evaluation.
        if self.db is not None:
            try:
                db_result = await self.db.execute(
                    select(TheaterPrediction)
                    .where(
                        TheaterPrediction.user_id == user_id,
                        TheaterPrediction.accuracy_status == "pending_feedback",
                        TheaterPrediction.accuracy_due_on <= _utcnow(),
                        TheaterPrediction.deleted_at.is_(None),
                    )
                    .order_by(desc(TheaterPrediction.generated_at))
                )
                rows = db_result.scalars().all()
                for row in rows:
                    if row.prediction_id in redis_ids:
                        continue  # Already have it from Redis
                    results.append(self._prediction_row_to_payload(row))
            except Exception as exc:
                logger.warning("DB fallback for pending predictions failed: %s", exc)
        return results

    async def _recent_comparison_pairs(self, *, user_id: UUID, limit: int = 10) -> list[dict[str, Any]]:
        if self.db is None:
            return []
        try:
            result = await self.db.execute(
                select(
                    TheaterPrediction.topic,
                    TheaterPrediction.generated_at,
                    TheaterPrediction.accuracy_summary,
                )
                .where(
                    TheaterPrediction.user_id == user_id,
                    TheaterPrediction.accuracy_summary.is_not(None),
                    TheaterPrediction.deleted_at.is_(None),
                )
                .order_by(desc(TheaterPrediction.generated_at))
                .limit(max(limit, 1))
            )
            rows = await _result_all(result)
        except Exception as exc:
            logger.warning("Failed to fetch comparison pairs for %s: %s", user_id, exc)
            return []

        pairs: list[dict[str, Any]] = []
        for topic, generated_at, accuracy_summary in rows:
            if not isinstance(accuracy_summary, dict):
                continue
            pairs.append(
                {
                    "predicted_completion": round(float(accuracy_summary.get("predicted_completion_rate") or 0.0), 4),
                    "actual_completion": round(float(accuracy_summary.get("actual_completion_rate") or 0.0), 4),
                    "predicted_mastery": round(float(accuracy_summary.get("predicted_mastery") or 0.0), 2),
                    "actual_mastery": round(float(accuracy_summary.get("actual_mastery") or 0.0), 2),
                    "topic": str(topic or ""),
                    "date": (
                        generated_at.date().isoformat()
                        if isinstance(generated_at, datetime)
                        else str(accuracy_summary.get("date") or "")[:10]
                    ),
                }
            )
        return pairs

    async def _topic_calibration_signal(self, *, user_id: UUID, topic: str) -> dict[str, Any]:
        default_signal = {
            "sample_count": 0,
            "force_low_quality": False,
            "latest_pending_age_days": None,
        }
        if self.db is None:
            return default_signal

        normalized_topic = _topic_key(topic)
        if not normalized_topic:
            return default_signal

        try:
            result = await self.db.execute(
                select(
                    TheaterPrediction.topic,
                    TheaterPrediction.generated_at,
                    TheaterPrediction.accuracy_summary,
                    TheaterPrediction.accuracy_status,
                )
                .where(
                    TheaterPrediction.user_id == user_id,
                    TheaterPrediction.deleted_at.is_(None),
                )
                .order_by(desc(TheaterPrediction.generated_at))
                .limit(30)
            )
            rows = await _result_all(result)
        except Exception as exc:
            logger.warning("Failed to build topical calibration signal for %s / %s: %s", user_id, topic, exc)
            return default_signal

        matching_rows = [row for row in rows if _topic_key(str(row[0] or "")) == normalized_topic]
        calibrated_rows = [row for row in matching_rows if isinstance(row[2], dict)]
        directional_biases: list[int] = []
        for _, _, accuracy_summary, _ in calibrated_rows[:3]:
            completion_delta = float(accuracy_summary.get("actual_completion_rate") or 0.0) - float(
                accuracy_summary.get("predicted_completion_rate") or 0.0
            )
            mastery_delta = float(accuracy_summary.get("actual_mastery") or 0.0) - float(
                accuracy_summary.get("predicted_mastery") or 0.0
            )
            direction = 0
            if abs(completion_delta) > 0.15:
                direction = 1 if completion_delta > 0 else -1
            elif abs(mastery_delta) > 15.0:
                direction = 1 if mastery_delta > 0 else -1
            if direction:
                directional_biases.append(direction)

        latest_pending_age_days: int | None = None
        for _, generated_at, accuracy_summary, accuracy_status in matching_rows:
            if isinstance(accuracy_summary, dict) or str(accuracy_status or "") == "recorded":
                continue
            if isinstance(generated_at, datetime):
                latest_pending_age_days = max((_utcnow().date() - generated_at.date()).days, 0)
                break

        return {
            "sample_count": len(calibrated_rows),
            "force_low_quality": len(directional_biases) >= 3 and len(set(directional_biases[:3])) == 1,
            "latest_pending_age_days": latest_pending_age_days,
        }

    @staticmethod
    def _apply_calibration_bias(
        value: float | None,
        *,
        bias_mean: float | None,
        weight: float = 0.75,
        lower: float,
        upper: float,
    ) -> float | None:
        if value is None or bias_mean is None:
            return value
        return _clamp(float(value) + (float(bias_mean) * weight), lower, upper)

    @staticmethod
    def _build_calibration_prompt(*, topic: str, age_days: int | None) -> str | None:
        if age_days is None:
            return None
        return f"你之前的推演“{topic}”已过去 {age_days} 天，是否已完成？回填真实数据可以让未来的推演更准确。"

    async def _compute_actual_from_prediction(
        self,
        user_id: UUID,
        prediction: dict[str, Any],
    ) -> dict[str, float] | None:
        resolved_mastery: float | None = None
        target_node_id = self._maybe_uuid(prediction.get("target_node_id"))
        if target_node_id is not None:
            status = await self.db.get(UserNodeStatus, (user_id, target_node_id))
            if status is not None:
                resolved_mastery = float(status.mastery_score or 0.0)
        if resolved_mastery is None:
            selected_prediction = dict(prediction.get("selected_prediction") or {})
            route_steps = [step for step in list(selected_prediction.get("steps") or []) if isinstance(step, dict)]
            candidate_node_ids = [
                self._maybe_uuid(step.get("mapped_galaxy_node_id") or step.get("node_id")) for step in route_steps
            ]
            valid_node_ids = [node_id for node_id in candidate_node_ids if node_id is not None]
            if valid_node_ids:
                result = await self.db.execute(
                    select(UserNodeStatus.mastery_score).where(
                        UserNodeStatus.user_id == user_id,
                        UserNodeStatus.node_id.in_(valid_node_ids),
                    )
                )
                mastery_scores = [float(score or 0.0) for score in result.scalars().all()]
                if mastery_scores:
                    resolved_mastery = sum(mastery_scores) / len(mastery_scores)

        resolved_completion: float | None = None
        adopted_plan_id = self._maybe_uuid(prediction.get("adopted_plan_id"))
        if adopted_plan_id is not None:
            from app.models.plan import Plan

            plan = await self.db.get(Plan, adopted_plan_id)
            if plan is not None:
                resolved_completion = float(plan.progress or 0.0)

        if resolved_mastery is None and resolved_completion is None:
            return None
        return {
            "mastery": float(resolved_mastery or 0.0),
            "completion": float(resolved_completion or 0.0),
        }

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

        stmt = select(KnowledgeNode).where(or_(*conditions)).limit(30)
        result = await self.db.execute(stmt)
        candidates = list(result.scalars().all())
        node = self._pick_best_target_node(
            candidates=candidates, normalized_topic=normalized, search_terms=search_terms
        )
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
            keyword_blob = " ".join(str(item).strip().lower() for item in (node.keywords or []) if str(item).strip())
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
        filtered_terms = [term for term in search_terms if term and len(term.strip()) >= 2]
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
                    " ".join(str(item).strip().lower() for item in (node.keywords or []) if str(item).strip()),
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
        return {str(node_id): float(score or 0.0) for node_id, score in await _result_all(result)}

    async def _build_user_learning_profile(
        self,
        user_id: UUID,
        *,
        available_time_per_day: int | None = None,
    ) -> dict[str, Any]:
        recent_result = await self.db.execute(
            select(StudyRecord.study_minutes)
            .where(StudyRecord.user_id == user_id)
            .order_by(desc(StudyRecord.created_at))
            .limit(20)
        )
        recent_records = await _result_all(recent_result)
        average_minutes = 40
        if recent_records:
            average_minutes = int(sum(int(item[0] or 0) for item in recent_records) / max(len(recent_records), 1)) or 40
        if available_time_per_day is not None:
            average_minutes = int(available_time_per_day)
        return {
            "average_session_minutes": int(_clamp(float(average_minutes), 25, 90)),
        }

    def _related_mastery_evidence(
        self,
        *,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for item in backbone:
            mapped_id = str(item.get("mapped_galaxy_node_id") or item.get("id") or "")
            mastery_score = mastery_map.get(mapped_id)
            evidence.append(
                {
                    "node_name": str(item.get("name") or ""),
                    "node_id": mapped_id or None,
                    "mastery_score": mastery_score if mastery_score is not None else None,
                    "source_type": "graph_verified" if mapped_id and mastery_score is not None else "ai_suggested",
                }
            )
        return evidence

    async def _related_error_evidence(
        self,
        *,
        user_id: UUID,
        topic: str,
        backbone: list[dict[str, Any]],
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        topic_terms = {
            term.casefold()
            for term in [topic, *[str(item.get("name") or "") for item in backbone]]
            if str(term).strip()
        }
        if not topic_terms:
            return []
        result = await self.db.execute(
            select(
                ErrorRecord.id,
                ErrorRecord.chapter,
                ErrorRecord.question_text,
                ErrorRecord.user_answer,
                ErrorRecord.correct_answer,
                ErrorRecord.latest_analysis,
                ErrorRecord.linked_knowledge_node_ids,
            )
            .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
            .order_by(desc(ErrorRecord.updated_at), desc(ErrorRecord.created_at))
            .limit(50)
        )
        rows = await _result_all(result)
        evidence: list[dict[str, Any]] = []
        for error_id, chapter, question_text, user_answer, correct_answer, latest_analysis, linked_node_ids in rows:
            haystack = " ".join(
                [
                    str(chapter or ""),
                    str(question_text or ""),
                    json.dumps(latest_analysis, ensure_ascii=False)
                    if isinstance(latest_analysis, dict)
                    else str(latest_analysis or ""),
                    " ".join(str(node_id) for node_id in list(linked_node_ids or [])),
                ]
            ).casefold()
            if not any(term in haystack for term in topic_terms):
                continue
            evidence.append(
                {
                    "error_id": str(error_id),
                    "chapter": str(chapter or "").strip(),
                    "question_text": str(question_text or "").strip(),
                    "user_answer": str(user_answer or "").strip(),
                    "correct_answer": str(correct_answer or "").strip(),
                    "root_cause": (
                        str((latest_analysis or {}).get("root_cause") or "").strip()
                        if isinstance(latest_analysis, dict)
                        else str(latest_analysis or "").strip()
                    ),
                }
            )
            if len(evidence) >= limit:
                break
        return evidence

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
        return [present_pattern_name(str(item[0])) for item in await _result_all(result) if str(item[0]).strip()]

    async def _build_graph_bundle(
        self,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
        *,
        target_context: TheaterTargetContext,
    ) -> dict[str, Any]:
        if target_context.resolution_mode != "graph_explicit":
            return self._build_synthetic_graph_bundle(
                backbone,
                mastery_map,
                semantic_matches=target_context.semantic_matches,
            )
        node_ids: list[UUID] = []
        for item in backbone[: self.MAX_GRAPH_NODES]:
            try:
                node_ids.append(UUID(str(item["id"])))
            except (KeyError, TypeError, ValueError):
                return self._build_synthetic_graph_bundle(
                    backbone,
                    mastery_map,
                    semantic_matches=target_context.semantic_matches,
                )
        result = await self.db.execute(
            select(KnowledgeNode.id, KnowledgeNode.name, KnowledgeNode.description, KnowledgeNode.sector_weights).where(
                KnowledgeNode.id.in_(node_ids)
            )
        )
        rows = await _result_all(result)
        nodes_by_id = {
            str(node_id): {
                "id": str(node_id),
                "name": name,
                "description": description or "",
                "current_mastery": round(mastery_map.get(str(node_id), 0.0), 2),
                "predicted_mastery": round(mastery_map.get(str(node_id), 0.0), 2),
                "risk_level": "high"
                if mastery_map.get(str(node_id), 0.0) < 45
                else ("medium" if mastery_map.get(str(node_id), 0.0) < 70 else "low"),
                "source_type": "graph_explicit",
                "mapped_galaxy_node_id": str(node_id),
                "candidate_status": None,
                "aliases": [],
                "sector_weights": dict(sector_weights or {}),
                "is_target": any(
                    str(item.get("id") or "") == str(node_id) and bool(item.get("is_target")) for item in backbone
                ),
            }
            for node_id, name, description, sector_weights in rows
        }
        edge_result = await self.db.execute(
            select(
                NodeRelation.source_node_id,
                NodeRelation.target_node_id,
                NodeRelation.relation_type,
                NodeRelation.strength,
            ).where(
                NodeRelation.source_node_id.in_(node_ids),
                NodeRelation.target_node_id.in_(node_ids),
            )
        )
        edge_rows = await _result_all(edge_result)
        edges = [
            {
                "id": f"{source_id}_{target_id}_{relation_type}",
                "source_id": str(source_id),
                "target_id": str(target_id),
                "relation_type": str(relation_type or "related").lower(),
                "strength": float(strength or 0.5),
                "confidence": round(_clamp(float(strength or 0.5) + 0.22, 0.45, 0.96), 2),
                "evidence": f"知识星图里已存在 {relation_type or 'related'} 关系。",
                "source_type": "graph_explicit",
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
                    "confidence": 0.61,
                    "evidence": "根据显式目标路径补出的前置顺序。",
                    "source_type": "graph_explicit",
                }
                for index in range(len(ordered_ids) - 1)
            ]
        return {"nodes": list(nodes_by_id.values()), "edges": edges}

    def _build_synthetic_graph_bundle(
        self,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
        risk_overrides: list[str] | None = None,
        semantic_matches: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        nodes = []
        ordered_ids: list[str] = []
        total = max(len(backbone), 1)
        for index, item in enumerate(backbone[: self.MAX_GRAPH_NODES]):
            node_id = str(item.get("id") or f"free-step-{index + 1}")
            ordered_ids.append(node_id)
            mastery_key = str(item.get("mapped_galaxy_node_id") or node_id)
            current_mastery = mastery_map.get(mastery_key, _clamp(34 + index * 7, 18, 74))
            nodes.append(
                {
                    "id": node_id,
                    "name": str(item.get("name") or f"阶段 {index + 1}"),
                    "description": str(item.get("description") or "自由模式推演阶段"),
                    "current_mastery": round(current_mastery, 2),
                    "predicted_mastery": round(_clamp(current_mastery + 16 - index, 12, 92), 2),
                    "risk_level": (
                        str(risk_overrides[index]).strip().lower()
                        if risk_overrides and index < len(risk_overrides)
                        else self._risk_level_for_step(
                            current_mastery=current_mastery,
                            index=index,
                            total=total,
                        )
                    ),
                    "source_type": str(item.get("source_type") or "freeform"),
                    "mapped_galaxy_node_id": (str(item.get("mapped_galaxy_node_id") or "") or None),
                    "candidate_status": item.get("candidate_status"),
                    "aliases": list(item.get("aliases") or []),
                    "sector_weights": dict(item.get("sector_weights") or {}),
                    "is_target": bool(item.get("is_target")),
                    "node_type": str(item.get("node_type") or "concept"),
                }
            )
        edges = self._build_freeform_edges(backbone[: self.MAX_GRAPH_NODES])

        reference_nodes: list[dict[str, Any]] = []
        reference_edges: list[dict[str, Any]] = []
        for match in semantic_matches or []:
            freeform_node_id = str(match.get("freeform_node_id") or "")
            galaxy_node_id = str(match.get("galaxy_node_id") or "")
            galaxy_node_name = str(match.get("galaxy_node_name") or "")
            if not freeform_node_id or not galaxy_node_id or not galaxy_node_name:
                continue
            ref_id = f"ref-{galaxy_node_id}"
            if not any(node["id"] == ref_id for node in reference_nodes):
                reference_nodes.append(
                    {
                        "id": ref_id,
                        "name": galaxy_node_name,
                        "description": str(match.get("evidence") or "来自知识星图的语义参考节点。"),
                        "current_mastery": 0.0,
                        "predicted_mastery": 0.0,
                        "risk_level": "low",
                        "source_type": "hybrid_reference",
                        "mapped_galaxy_node_id": galaxy_node_id,
                        "candidate_status": None,
                        "aliases": [],
                        "sector_weights": dict(match.get("sector_weights") or {}),
                        "is_target": False,
                        "node_type": "reference",
                    }
                )
            reference_edges.append(
                {
                    "id": f"{freeform_node_id}_{ref_id}_semantic_reference",
                    "source_id": freeform_node_id,
                    "target_id": ref_id,
                    "relation_type": "compare",
                    "strength": 0.42,
                    "confidence": float(match.get("confidence") or 0.58),
                    "evidence": str(match.get("evidence") or "与知识星图中的相关节点存在语义映射。"),
                    "source_type": "hybrid_reference",
                }
            )
        return {"nodes": [*nodes, *reference_nodes], "edges": [*edges, *reference_edges]}

    def _build_freeform_edges(self, backbone: list[dict[str, Any]]) -> list[dict[str, Any]]:
        prerequisites = [item for item in backbone if str(item.get("node_type") or "") == "prerequisite"]
        concepts = [item for item in backbone if str(item.get("node_type") or "") == "concept"]
        targets = [item for item in backbone if bool(item.get("is_target"))]
        milestones = [item for item in backbone if str(item.get("node_type") or "") == "milestone"]
        applications = [item for item in backbone if str(item.get("node_type") or "") == "application"]
        misconceptions = [item for item in backbone if str(item.get("node_type") or "") == "misconception"]

        edges: list[dict[str, Any]] = []

        def add_edge(
            source_id: str,
            target_id: str,
            relation_type: str,
            strength: float,
            evidence: str,
            *,
            source_type: str = "freeform",
        ) -> None:
            if not source_id or not target_id or source_id == target_id:
                return
            edge_id = f"{source_id}_{target_id}_{relation_type}"
            if any(item["id"] == edge_id for item in edges):
                return
            edges.append(
                {
                    "id": edge_id,
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation_type": relation_type,
                    "strength": round(strength, 2),
                    "confidence": round(_clamp(strength + 0.18, 0.42, 0.94), 2),
                    "evidence": evidence,
                    "source_type": source_type,
                }
            )

        target = targets[0] if targets else None
        for item in prerequisites:
            for concept in concepts[:2]:
                add_edge(
                    str(item.get("id") or ""),
                    str(concept.get("id") or ""),
                    "prerequisite",
                    0.66,
                    f"{item.get('name') or ''} 是理解 {concept.get('name') or ''} 前要先补的基础。",
                )
        if target is not None:
            for concept in concepts:
                add_edge(
                    str(concept.get("id") or ""),
                    str(target.get("id") or ""),
                    "part_of",
                    0.72,
                    f"{concept.get('name') or ''} 构成了目标 {target.get('name') or ''} 的核心部分。",
                )
            for item in prerequisites:
                add_edge(
                    str(item.get("id") or ""),
                    str(target.get("id") or ""),
                    "depends_on",
                    0.58,
                    f"{target.get('name') or ''} 需要建立在 {item.get('name') or ''} 之上。",
                )
            for milestone in milestones:
                add_edge(
                    str(target.get("id") or ""),
                    str(milestone.get("id") or ""),
                    "application",
                    0.63,
                    f"{milestone.get('name') or ''} 可以作为 {target.get('name') or ''} 的阶段性产出。",
                )
            for application in applications:
                add_edge(
                    str(target.get("id") or ""),
                    str(application.get("id") or ""),
                    "application",
                    0.68,
                    f"{application.get('name') or ''} 体现了 {target.get('name') or ''} 的落地方向。",
                )
            for misconception in misconceptions:
                add_edge(
                    str(misconception.get("id") or ""),
                    str(target.get("id") or ""),
                    "confusion_with",
                    0.48,
                    f"{misconception.get('name') or ''} 是学习 {target.get('name') or ''} 时容易出现的误区。",
                )
        for index in range(max(len(concepts) - 1, 0)):
            add_edge(
                str(concepts[index].get("id") or ""),
                str(concepts[index + 1].get("id") or ""),
                "compare",
                0.44,
                f"{concepts[index].get('name') or ''} 与 {concepts[index + 1].get('name') or ''} 需要放在一起理解与对比。",
            )
        ordered_ids = [str(item.get("id") or "") for item in backbone if str(item.get("id") or "")]
        for index in range(len(ordered_ids) - 1):
            add_edge(
                ordered_ids[index],
                ordered_ids[index + 1],
                "depends_on",
                0.39,
                "这两个节点在推演节奏上存在连续推进关系。",
            )
        return edges

    async def _persist_candidate_bundle(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        topic: str,
        target_context: TheaterTargetContext,
        graph_bundle: dict[str, Any],
    ) -> str:
        if self.db is None:
            return ""
        bundle = TheaterCandidateBundle(
            user_id=user_id,
            prediction_id=prediction_id,
            topic=topic,
            target_name=target_context.name,
            target_resolution_mode=target_context.resolution_mode,
            status="pending_review",
            nodes_payload=list(graph_bundle.get("nodes") or []),
            edges_payload=list(graph_bundle.get("edges") or []),
            semantic_matches=list(target_context.semantic_matches or []),
            source_metadata={
                "target_description": target_context.description,
                "target_node_id": target_context.target_node_id,
                "backbone_node_ids": [str(item.get("id") or "") for item in target_context.backbone],
            },
        )
        self.db.add(bundle)
        await self.db.flush()
        return str(bundle.id)

    async def _build_galaxy_candidate_from_prediction(
        self,
        *,
        user_id: UUID,
        cached: dict[str, Any],
        theater_node: dict[str, Any],
    ) -> dict[str, Any]:
        del user_id
        parent_node_id: UUID | None = None
        trigger_node_id: UUID | None = None
        relation_type = "related"
        relation_strength = 0.68
        graph = dict(cached.get("graph") or {})
        nodes_by_id = {
            str(item.get("id") or ""): item for item in list(graph.get("nodes") or []) if isinstance(item, dict)
        }
        for edge in list(graph.get("edges") or []):
            if not isinstance(edge, dict):
                continue
            source_id = str(edge.get("source_id") or "")
            target_id = str(edge.get("target_id") or "")
            if theater_node.get("id") not in {source_id, target_id}:
                continue
            neighbor_id = target_id if source_id == theater_node.get("id") else source_id
            neighbor = dict(nodes_by_id.get(neighbor_id) or {})
            mapped_neighbor_id = self._maybe_uuid(neighbor.get("mapped_galaxy_node_id") or neighbor.get("id"))
            if mapped_neighbor_id is None:
                continue
            parent_node_id = mapped_neighbor_id
            trigger_node_id = mapped_neighbor_id
            relation_type = str(edge.get("relation_type") or "related")
            relation_strength = float(edge.get("strength") or 0.68)
            break

        if parent_node_id is None:
            target_node_id = self._maybe_uuid(cached.get("target_node_id"))
            parent_node_id = target_node_id
            trigger_node_id = target_node_id

        subject_id: int | None = None
        if parent_node_id is not None:
            parent_node = await self.db.get(KnowledgeNode, parent_node_id)
            if parent_node is not None:
                subject_id = getattr(parent_node, "subject_id", None)

        candidate = {
            "name": str(theater_node.get("name") or "未命名节点"),
            "name_en": None,
            "description": str(theater_node.get("description") or ""),
            "importance_level": 4 if bool(theater_node.get("is_target")) else 3,
            "relation_to_trigger": relation_type,
            "relation_strength": relation_strength,
            "keywords": self._dedupe_preserve_order(
                [
                    *self._coerce_string_list(theater_node.get("aliases")),
                    str(cached.get("topic") or ""),
                    str(cached.get("target_name") or ""),
                ]
            ),
            "sector_weights": dict(theater_node.get("sector_weights") or {}),
        }
        return {
            "candidate": candidate,
            "parent_node_id": parent_node_id,
            "trigger_node_id": trigger_node_id,
            "subject_id": subject_id,
        }

    async def _record_candidate_bundle_promotion(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        theater_node_id: str,
        galaxy_node: KnowledgeNode,
        commit: bool = True,
    ) -> None:
        if self.db is None:
            return
        result = await self.db.execute(
            select(TheaterCandidateBundle).where(
                TheaterCandidateBundle.prediction_id == prediction_id,
                TheaterCandidateBundle.user_id == user_id,
                TheaterCandidateBundle.deleted_at.is_(None),
            )
        )
        bundle = result.scalar_one_or_none()
        if bundle is None:
            return
        metadata = dict(bundle.source_metadata or {})
        promoted_nodes = dict(metadata.get("promoted_nodes") or {})
        promoted_nodes[theater_node_id] = {
            "galaxy_node_id": str(galaxy_node.id),
            "name": galaxy_node.name,
            "promoted_at": _utcnow().isoformat(),
        }
        metadata["promoted_nodes"] = promoted_nodes
        bundle.source_metadata = metadata
        bundle.status = "partially_applied"
        self.db.add(bundle)
        if commit:
            await self.db.commit()

    async def _patch_prediction_cache_with_promoted_node(
        self,
        *,
        cached: dict[str, Any],
        prediction_id: str,
        theater_node_id: str,
        galaxy_node_id: str,
        candidate_status: str | None,
    ) -> None:
        graph = dict(cached.get("graph") or {})
        graph_nodes = []
        for item in list(graph.get("nodes") or []):
            if not isinstance(item, dict):
                continue
            updated = dict(item)
            if str(updated.get("id") or "") == theater_node_id:
                updated["mapped_galaxy_node_id"] = galaxy_node_id
                updated["candidate_status"] = candidate_status
            graph_nodes.append(updated)
        graph["nodes"] = graph_nodes
        cached["graph"] = graph
        cached["candidate_bundle_id"] = str(cached.get("candidate_bundle_id") or "")

        updated_paths = []
        for path in list(cached.get("paths") or []):
            if not isinstance(path, dict):
                continue
            updated_path = dict(path)
            updated_steps = []
            for step in list(path.get("steps") or []):
                if not isinstance(step, dict):
                    continue
                updated_step = dict(step)
                if str(updated_step.get("node_id") or "") == theater_node_id:
                    updated_step["mapped_galaxy_node_id"] = galaxy_node_id
                updated_steps.append(updated_step)
            updated_path["steps"] = updated_steps
            updated_paths.append(updated_path)
        cached["paths"] = updated_paths
        await cache_service.set(
            f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
            cached,
            ttl=self.accuracy.TTL_SECONDS,
        )

    async def _build_prediction_calibration(self, user_id: UUID) -> dict[str, Any]:
        default_profile = {
            "sample_count": 0,
            "completion_bias_mean": 0.0,
            "mastery_bias_mean": 0.0,
            "completion_mae": 0.12,
            "mastery_mae": 12.0,
            "completion_mean_actual": None,
            "mastery_mean_actual": None,
            "avg_accuracy_score": 0.0,
            "coverage_rate": None,
            "data_sufficiency_score": 0.42,
            "data_status": "cold_start",
            "strategy_profiles": {},
        }
        if self.db is None:
            return default_profile
        try:
            result = await self.db.execute(
                select(
                    TheaterPrediction.selected_prediction,
                    TheaterPrediction.accuracy_summary,
                )
                .where(
                    TheaterPrediction.user_id == user_id,
                    TheaterPrediction.accuracy_summary.is_not(None),
                    TheaterPrediction.deleted_at.is_(None),
                )
                .order_by(
                    desc(TheaterPrediction.generated_at),
                )
                .limit(40)
            )
            rows = await _result_all(result)
        except Exception as exc:
            logger.warning("Failed to build theater calibration profile for %s: %s", user_id, exc)
            return default_profile

        if not rows:
            return default_profile

        completion_biases: list[float] = []
        mastery_biases: list[float] = []
        completion_errors: list[float] = []
        mastery_errors: list[float] = []
        accuracy_scores: list[float] = []
        actual_completion_rates: list[float] = []
        actual_mastery_scores: list[float] = []
        coverage_hits = 0
        coverage_total = 0
        strategy_samples: dict[str, dict[str, list[float] | int]] = {}

        for selected_prediction, accuracy_summary in rows:
            if not isinstance(selected_prediction, dict) or not isinstance(accuracy_summary, dict):
                continue
            predicted_completion = float(
                accuracy_summary.get("predicted_completion_rate")
                or selected_prediction.get("estimated_completion_rate")
                or 0.0,
            )
            predicted_mastery = float(
                accuracy_summary.get("predicted_mastery") or selected_prediction.get("estimated_mastery") or 0.0,
            )
            actual_completion = float(accuracy_summary.get("actual_completion_rate") or 0.0)
            actual_mastery = float(accuracy_summary.get("actual_mastery") or 0.0)
            completion_bias = actual_completion - predicted_completion
            mastery_bias = actual_mastery - predicted_mastery
            completion_error = abs(completion_bias)
            mastery_error = abs(mastery_bias)
            strategy_type = str(selected_prediction.get("strategy_type") or "unknown")

            completion_biases.append(completion_bias)
            mastery_biases.append(mastery_bias)
            completion_errors.append(completion_error)
            mastery_errors.append(mastery_error)
            accuracy_scores.append(float(accuracy_summary.get("accuracy_score") or 0.0))
            actual_completion_rates.append(actual_completion)
            actual_mastery_scores.append(actual_mastery)

            strategy_bucket = strategy_samples.setdefault(
                strategy_type,
                {
                    "completion_biases": [],
                    "mastery_biases": [],
                    "completion_errors": [],
                    "mastery_errors": [],
                    "sample_count": 0,
                },
            )
            strategy_bucket["completion_biases"].append(completion_bias)
            strategy_bucket["mastery_biases"].append(mastery_bias)
            strategy_bucket["completion_errors"].append(completion_error)
            strategy_bucket["mastery_errors"].append(mastery_error)
            strategy_bucket["sample_count"] = int(strategy_bucket["sample_count"]) + 1

            completion_low = selected_prediction.get("completion_range_low")
            completion_high = selected_prediction.get("completion_range_high")
            mastery_low = selected_prediction.get("mastery_range_low")
            mastery_high = selected_prediction.get("mastery_range_high")
            if all(value is not None for value in [completion_low, completion_high, mastery_low, mastery_high]):
                coverage_total += 1
                if float(completion_low) <= actual_completion <= float(completion_high) and float(
                    mastery_low
                ) <= actual_mastery <= float(mastery_high):
                    coverage_hits += 1

        sample_count = len(accuracy_scores)
        if sample_count == 0:
            return default_profile

        strategy_profiles: dict[str, Any] = {}
        for strategy_type, bucket in strategy_samples.items():
            strategy_profiles[strategy_type] = {
                "sample_count": int(bucket["sample_count"]),
                "completion_bias_mean": round(statistics.mean(bucket["completion_biases"]), 4),
                "mastery_bias_mean": round(statistics.mean(bucket["mastery_biases"]), 2),
                "completion_mae": round(statistics.mean(bucket["completion_errors"]), 4),
                "mastery_mae": round(statistics.mean(bucket["mastery_errors"]), 2),
            }

        return {
            "sample_count": sample_count,
            "completion_bias_mean": round(statistics.mean(completion_biases), 4),
            "mastery_bias_mean": round(statistics.mean(mastery_biases), 2),
            "completion_mae": round(statistics.mean(completion_errors), 4),
            "mastery_mae": round(statistics.mean(mastery_errors), 2),
            "completion_mean_actual": round(statistics.mean(actual_completion_rates), 4),
            "mastery_mean_actual": round(statistics.mean(actual_mastery_scores), 2),
            "avg_accuracy_score": round(statistics.mean(accuracy_scores), 4),
            "coverage_rate": round((coverage_hits / coverage_total), 4) if coverage_total else None,
            "data_sufficiency_score": round(_clamp(0.45 + min(sample_count, 20) * 0.02, 0.45, 0.9), 4),
            "data_status": "calibrated" if sample_count >= 5 else "blended_history",
            "strategy_profiles": strategy_profiles,
        }

    async def _build_path_options(
        self,
        *,
        topic: str,
        target_name: str,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
        horizon_days: int,
        study_preferences: dict[str, Any],
        pattern_names: list[str],
        calibration_profile: dict[str, Any],
        has_graph_context: bool,
        request_context: dict[str, Any],
        mastery_evidence: list[dict[str, Any]],
        error_evidence: list[dict[str, Any]],
        topic_calibration: dict[str, Any],
        risk_overrides: list[str] | None = None,
    ) -> list[TheaterPathOption]:
        session_minutes = int(study_preferences.get("average_session_minutes") or 40)
        node_names = [str(item.get("name") or "") for item in backbone]
        average_mastery = sum(
            mastery_score
            for mastery_score in (
                mastery_map.get(str(item.get("mapped_galaxy_node_id") or item.get("id") or "")) for item in backbone
            )
            if mastery_score is not None
        ) / max(
            1,
            len(
                [
                    item
                    for item in backbone
                    if mastery_map.get(str(item.get("mapped_galaxy_node_id") or item.get("id") or "")) is not None
                ]
            ),
        )
        fallback_plans = self._dynamic_path_plan_fallback(
            target_name=target_name,
            backbone=backbone,
            available_time_per_day=session_minutes,
            goal_type=str(request_context.get("goal_type") or "").strip() or None,
        )
        dynamic_plans = await self._generate_dynamic_path_plans(
            topic=topic,
            target_name=target_name,
            request_context=request_context,
            mastery_evidence=mastery_evidence,
            error_evidence=error_evidence,
            backbone=backbone,
            fallback=fallback_plans,
        )
        options: list[TheaterPathOption] = []
        checkpoint_days = self._checkpoint_days_for_horizon(horizon_days)
        sample_count = int(calibration_profile.get("sample_count") or 0)
        data_sufficiency_score = _clamp(
            float(
                calibration_profile.get("data_sufficiency_score") or calibration_profile.get("confidence_score") or 0.42
            ),
            0.36,
            0.92,
        )
        data_quality = (
            "low"
            if bool(topic_calibration.get("force_low_quality"))
            else ("high" if has_graph_context and sample_count >= 5 else ("medium" if has_graph_context else "low"))
        )
        for idx, strategy in enumerate(dynamic_plans):
            steps = self._materialize_dynamic_steps(
                plan=strategy,
                backbone=backbone,
                mastery_map=mastery_map,
                checkpoint_days=checkpoint_days,
                available_time_per_day=session_minutes,
                risk_overrides=risk_overrides,
            )
            strategy_type = str(strategy.get("strategy_type") or f"path_{idx + 1}")
            sample_count = int(calibration_profile.get("sample_count") or 0)
            strategy_profile = (
                calibration_profile.get("strategy_profiles", {}).get(strategy_type)
                if isinstance(calibration_profile.get("strategy_profiles"), dict)
                else None
            )
            completion_rate = self._completion_rate_from_history(
                calibration_profile=calibration_profile,
                steps=steps,
            )
            completion_rate = self._apply_calibration_bias(
                completion_rate,
                bias_mean=(
                    strategy_profile.get("completion_bias_mean")
                    if isinstance(strategy_profile, dict)
                    else calibration_profile.get("completion_bias_mean")
                ),
                weight=0.75,
                lower=0.05,
                upper=0.95,
            )
            completion_margin = (
                _clamp(float(calibration_profile.get("completion_mae") or 0.12) + (len(steps) * 0.008), 0.06, 0.24)
                if completion_rate is not None and sample_count >= 5
                else None
            )
            predicted_values = [step.predicted_mastery for step in steps if step.predicted_mastery is not None]
            current_values = [step.current_mastery for step in steps if step.current_mastery is not None]
            estimated_mastery = (
                round(sum(predicted_values) / len(predicted_values), 2)
                if predicted_values
                else (round(sum(current_values) / len(current_values), 2) if current_values else None)
            )
            estimated_mastery = self._apply_calibration_bias(
                estimated_mastery,
                bias_mean=(
                    strategy_profile.get("mastery_bias_mean")
                    if isinstance(strategy_profile, dict)
                    else calibration_profile.get("mastery_bias_mean")
                ),
                weight=0.75,
                lower=0.0,
                upper=100.0,
            )
            if estimated_mastery is not None:
                estimated_mastery = round(float(estimated_mastery), 2)
            mastery_margin = (
                _clamp(float(calibration_profile.get("mastery_mae") or 12.0) + (len(steps) * 0.75), 6.0, 24.0)
                if estimated_mastery is not None and sample_count >= 5
                else None
            )
            completion_range_low = (
                _clamp(completion_rate - float(completion_margin or 0.0), 0.0, 1.0)
                if completion_rate is not None and completion_margin is not None
                else 0.0
            )
            completion_range_high = (
                _clamp(completion_rate + float(completion_margin or 0.0), 0.0, 1.0)
                if completion_rate is not None and completion_margin is not None
                else 0.0
            )
            mastery_range_low = (
                _clamp(float(estimated_mastery) - float(mastery_margin or 0.0), 0.0, 100.0)
                if estimated_mastery is not None and mastery_margin is not None
                else 0.0
            )
            mastery_range_high = (
                _clamp(float(estimated_mastery) + float(mastery_margin or 0.0), 0.0, 100.0)
                if estimated_mastery is not None and mastery_margin is not None
                else 0.0
            )
            risks = [str(strategy.get("not_for") or "").strip() or "这条路径更依赖你按步骤执行。"]
            if pattern_names:
                risks.append(f"近期行为模式提示：{pattern_names[0]} 可能影响这条路径的稳定执行。")
            if node_names:
                risks.append(f"{node_names[min(len(node_names) - 1, 0)]} 的掌握情况会决定后续理解是否顺滑。")
            if sample_count < 5:
                risks.append("当前历史校准样本不足，完成率数字不会作为主结论提供。")
            route_score = self._route_score(
                completion_rate=completion_rate or 0.0,
                estimated_mastery=float(estimated_mastery or average_mastery or 0.0),
                risks=risks,
                strategy_type=strategy_type,
            )
            options.append(
                TheaterPathOption(
                    id=str(strategy.get("id") or f"path_dynamic_{idx + 1}"),
                    title=str(strategy.get("title") or f"路径 {idx + 1}"),
                    summary=(
                        str(strategy.get("summary") or "").strip()
                        or f"适合：{str(strategy.get('fit_for') or '需要更明确的目标约束')}；不适合：{str(strategy.get('not_for') or '缺少执行空间的情况')}。"
                    ),
                    strategy_type=strategy_type,
                    expert_ids=[
                        str(item).strip() for item in list(strategy.get("expert_ids") or []) if str(item).strip()
                    ],
                    estimated_completion_rate=completion_rate,
                    estimated_mastery=estimated_mastery,
                    daily_minutes=session_minutes,
                    risks=risks[:3],
                    route_score=route_score,
                    checkpoint_days=checkpoint_days,
                    week_one_tasks=self._week_one_task_blueprints(steps=steps, target_name=target_name),
                    data_sufficiency_score=data_sufficiency_score,
                    data_quality=data_quality,
                    completion_range_low=completion_range_low,
                    completion_range_high=completion_range_high,
                    mastery_range_low=mastery_range_low,
                    mastery_range_high=mastery_range_high,
                    calibration_basis=(
                        "personal_history"
                        if sample_count >= 5
                        else ("cold_start" if sample_count == 0 else "blended_history")
                    ),
                    steps=steps,
                )
            )
        return options

    def _dynamic_path_plan_fallback(
        self,
        *,
        target_name: str,
        backbone: list[dict[str, Any]],
        available_time_per_day: int,
        goal_type: str | None,
    ) -> list[dict[str, Any]]:
        ordered = [dict(item) for item in backbone if isinstance(item, dict)]
        reversed_order = list(reversed(ordered))
        quick_steps = ordered[: max(2, min(len(ordered), 3))]
        return [
            {
                "id": "path_constraint_first",
                "title": "约束优先路径",
                "strategy_type": "constraint_first",
                "summary": f"先围绕 {target_name} 最核心的前置与目标节点压缩成小步，适合时间有限时执行。",
                "fit_for": "适合每天时间有限、需要先建立最小闭环的情况",
                "not_for": "不适合希望一次性铺开全部相关内容的情况",
                "expert_ids": ["galaxy_guide", "time_tutor"],
                "steps": quick_steps,
            },
            {
                "id": "path_full_chain",
                "title": "完整链路路径",
                "strategy_type": "full_chain",
                "summary": f"沿着 {target_name} 的前置关系完整推进，适合系统建立理解。",
                "fit_for": "适合想系统掌握概念依赖和完整链路的情况",
                "not_for": "不适合只想快速过一遍重点的情况",
                "expert_ids": ["deep_analyst", "galaxy_guide"],
                "steps": ordered,
            },
            {
                "id": "path_target_backtrack",
                "title": "目标回溯路径",
                "strategy_type": "target_backtrack",
                "summary": f"先接触 {target_name} 的目标问题，再回补暴露出的前置缺口。",
                "fit_for": "适合有明确项目或考试牵引，需要先看目标长什么样的情况",
                "not_for": "不适合完全零基础且容易被高难度内容打断的情况",
                "expert_ids": ["exam_oracle", "study_buddy"]
                if goal_type == "exam"
                else ["study_buddy", "deep_analyst"],
                "steps": reversed_order[: len(ordered)],
            },
        ][: 2 if available_time_per_day <= 30 else 3]

    async def _generate_dynamic_path_plans(
        self,
        *,
        topic: str,
        target_name: str,
        request_context: dict[str, Any],
        mastery_evidence: list[dict[str, Any]],
        error_evidence: list[dict[str, Any]],
        backbone: list[dict[str, Any]],
        fallback: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是学习路径规划专家。请只返回严格 JSON，对象包含 paths 数组。"
                        "每条路径必须包含 id, title, strategy_type, summary, fit_for, not_for, expert_ids, steps。"
                        "steps 数组中的每一项必须包含 node_name, rationale, estimated_minutes, risk_level, "
                        "source_type, mapped_galaxy_node_id, predicted_mastery。"
                        "不要编造已有掌握度；没有数据的 predicted_mastery 可以为 null。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "你是学习路径规划专家。根据以下信息，设计 2-3 条差异化的学习路径：\n\n"
                        f"学习主题：{topic}\n"
                        f"学习目标：{request_context.get('goal_type') or '[未提供]'}\n"
                        f"当前水平：{request_context.get('current_level') or '[未提供]'}\n"
                        f"每日可用时间：{request_context.get('available_time_per_day') or '[未提供]'} 分钟\n"
                        f"学习材料：{request_context.get('materials') or '[未提供]'}\n"
                        f"补充说明：{request_context.get('context') or '[未提供]'}\n\n"
                        f"已掌握的相关知识节点：{json.dumps(mastery_evidence, ensure_ascii=False)}\n\n"
                        f"错题本中相关的错误：{json.dumps(error_evidence, ensure_ascii=False)}\n\n"
                        f"候选知识骨架：{json.dumps(backbone, ensure_ascii=False)}\n\n"
                        "要求：\n"
                        "1. 每条路径必须有明确的适用场景。\n"
                        "2. 每条路径的步骤必须基于上述已掌握和未掌握的知识节点。\n"
                        "3. 如果某个步骤涉及用户知识图谱中的节点，标注 mapped_galaxy_node_id。\n"
                        "4. 对于用户知识图谱中不存在的步骤，明确标注 source_type: ai_suggested。\n"
                        "5. 不要编造掌握度数字；已有数据的用真实 mastery_score，没有数据的 predicted_mastery 允许为 null。\n"
                        "6. 时间估算基于用户的 available_time_per_day，不要硬编码。\n"
                        f"7. 目标名称统一围绕 {target_name}。\n"
                    ),
                },
            ],
            fallback={"paths": fallback},
            temperature=0.25,
        )
        if not isinstance(payload, dict):
            return fallback
        plans = [item for item in list(payload.get("paths") or []) if isinstance(item, dict)]
        return plans[:3] or fallback

    def _materialize_dynamic_steps(
        self,
        *,
        plan: dict[str, Any],
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
        checkpoint_days: list[int],
        available_time_per_day: int,
        risk_overrides: list[str] | None,
    ) -> list[TheaterPathStep]:
        backbone_by_name = {str(item.get("name") or "").strip(): item for item in backbone}
        raw_steps = [item for item in list(plan.get("steps") or []) if isinstance(item, dict)]
        steps: list[TheaterPathStep] = []
        cumulative_minutes = 0
        for step_index, raw in enumerate(raw_steps or backbone, start=1):
            raw_name = str(raw.get("node_name") or raw.get("name") or "当前节点").strip() or "当前节点"
            matched = backbone_by_name.get(raw_name)
            node_id = str((matched or raw).get("id") or f"ai-step-{step_index}")
            mapped_galaxy_node_id = str((matched or raw).get("mapped_galaxy_node_id") or "").strip() or None
            mastery_key = mapped_galaxy_node_id or node_id
            current_mastery = mastery_map.get(mastery_key)
            predicted_mastery = raw.get("predicted_mastery")
            if predicted_mastery is not None:
                try:
                    predicted_mastery = _clamp(float(predicted_mastery), 0.0, 100.0)
                except (TypeError, ValueError):
                    predicted_mastery = None
            estimated_minutes = int(_clamp(float(raw.get("estimated_minutes") or available_time_per_day), 10.0, 180.0))
            cumulative_minutes += estimated_minutes
            day_slot = max(1, int((cumulative_minutes - 1) / max(available_time_per_day, 1)) + 1)
            risk_level = (
                str(risk_overrides[step_index - 1]).strip().lower()
                if risk_overrides and step_index - 1 < len(risk_overrides)
                else str(
                    raw.get("risk_level")
                    or self._risk_level_for_step(
                        current_mastery=float(current_mastery or 0.0),
                        index=step_index - 1,
                        total=max(len(raw_steps), 1),
                    )
                )
                .strip()
                .lower()
            )
            steps.append(
                TheaterPathStep(
                    index=step_index,
                    node_id=node_id,
                    node_name=raw_name,
                    rationale=str(
                        raw.get("rationale")
                        or self._step_rationale(
                            strategy_type=str(plan.get("strategy_type") or "custom"),
                            node_name=raw_name,
                            is_target=bool((matched or raw).get("is_target")),
                        )
                    ),
                    current_mastery=float(current_mastery) if current_mastery is not None else None,
                    predicted_mastery=float(predicted_mastery) if predicted_mastery is not None else None,
                    risk_level=risk_level or "medium",
                    estimated_minutes=estimated_minutes,
                    day_label=f"第 {day_slot} 天",
                    checkpoint_label=(
                        f"检查点 · 第 {day_slot} 天"
                        if day_slot in checkpoint_days or step_index == len(raw_steps or backbone)
                        else None
                    ),
                    mapped_galaxy_node_id=mapped_galaxy_node_id,
                    source_type=(
                        str(raw.get("source_type") or "")
                        or ("graph_verified" if mapped_galaxy_node_id else "ai_suggested")
                    ),
                )
            )
        return steps

    def _completion_rate_from_history(
        self,
        *,
        calibration_profile: dict[str, Any],
        steps: list[TheaterPathStep],
    ) -> float | None:
        sample_count = int(calibration_profile.get("sample_count") or 0)
        baseline = calibration_profile.get("completion_mean_actual")
        if sample_count < 5 or baseline is None:
            return None
        ai_suggested_count = len([step for step in steps if step.source_type == "ai_suggested"])
        hard_risk_count = len([step for step in steps if step.risk_level == "high"])
        adjustment = ((len(steps) - 3) * 0.03) + (hard_risk_count * 0.04) + (ai_suggested_count * 0.03)
        return _clamp(float(baseline) - adjustment, 0.05, 0.95)

    @staticmethod
    def _risk_level_for_step(
        *,
        current_mastery: float,
        index: int,
        total: int,
    ) -> str:
        if current_mastery < 45:
            return "high"
        if current_mastery < 70:
            return "medium"
        return "medium" if index < max(total - 2, 1) else "low"

    async def _build_discussion(
        self,
        *,
        topic: str,
        target_name: str,
        options: list[TheaterPathOption],
        graph_bundle: dict[str, Any],
        pattern_names: list[str],
    ) -> list[dict[str, Any]]:
        fallback = self._fallback_discussion(
            topic=topic, target_name=target_name, options=options, pattern_names=pattern_names
        )
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是知识推演剧场里的圆桌主持。请只返回严格 JSON 对象，包含 turns 数组。"
                        "每个 turn 必须包含 agent_id、display_name、turn_type、content、related_node_ids。"
                        "所有 content 必须是自然流畅的中文。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"主题：{topic}\n"
                        f"目标：{target_name}\n"
                        f"路径候选：{[item.to_dict() for item in options]}\n"
                        f"关系图：{graph_bundle}\n"
                        f"行为模式：{pattern_names}\n"
                        "请生成 3-4 段简洁的中文圆桌讨论，比较这些路径、指出主要风险，并给出取舍建议。"
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
                    "display_name": str(
                        turn.get("display_name") or fallback[min(index, len(fallback) - 1)]["display_name"]
                    ),
                    "turn_type": str(turn.get("turn_type") or "analysis"),
                    "content": str(turn.get("content") or fallback[min(index, len(fallback) - 1)]["content"]),
                    "related_node_ids": [
                        str(item) for item in list(turn.get("related_node_ids") or []) if str(item).strip()
                    ],
                }
            )
        return normalized or fallback

    def _build_timeline(
        self,
        options: list[TheaterPathOption],
        discussion: list[dict[str, Any]],
        *,
        available_time_per_day: int,
    ) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for option in options:
            cumulative_minutes = 0
            for step_index, active_step in enumerate(option.steps, start=1):
                cumulative_minutes += int(active_step.estimated_minutes or 0)
                day_index = max(1, int((cumulative_minutes - 1) / max(available_time_per_day, 1)) + 1)
                projected_mastery = float(active_step.predicted_mastery or active_step.current_mastery or 0.0)
                projected_completion = (
                    round(float(option.estimated_completion_rate), 4)
                    if option.estimated_completion_rate is not None
                    else None
                )
                frames.append(
                    {
                        "index": len(frames),
                        "label": f"第 {day_index} 天 · 步骤 {step_index}",
                        "day_index": day_index,
                        "route_id": option.id,
                        "focus_node_ids": [active_step.node_id],
                        "discussion_turn_index": min(step_index - 1, max(len(discussion) - 1, 0)),
                        "projected_mastery": round(projected_mastery, 2),
                        "projected_completion_rate": projected_completion,
                        "active_step_node_id": active_step.node_id,
                        "active_step_title": active_step.node_name,
                        "compare_label": "推荐基线" if option.id == options[0].id else None,
                        "branch_type": "baseline" if option.id == options[0].id else "alternative",
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
        if strategy_type == "target_backtrack":
            penalty += 2
        elif strategy_type == "full_chain":
            penalty += 1
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
                    "label": f"第 {day} 天",
                    "day_index": day,
                    "route_id": str(route.get("id") or ""),
                    "focus_node_ids": [str(active_step.get("node_id") or "")] if active_step else [],
                    "discussion_turn_index": 0,
                    "projected_mastery": round(mastery_value, 2),
                    "projected_completion_rate": round(completion_value, 4),
                    "active_step_node_id": str(active_step.get("node_id") or ""),
                    "active_step_title": str(active_step.get("node_name") or "分支推演"),
                    "compare_label": "假设分支",
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
            node_id = self._maybe_uuid(step.get("mapped_galaxy_node_id") or step.get("node_id"))
            due_date = date.today() + timedelta(days=min(index * 2, 6))
            task = await TaskService.create(
                self.db,
                TaskCreate(
                    title=f"{step.get('day_label') or f'第 {index + 1} 天'} · 推进 {step.get('node_name') or target_name}",
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
                    title=f"检查点 · 回看 {target_name} 的推演进度",
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
    def _build_prediction_evidence_summary(
        *,
        target_context: TheaterTargetContext,
        options: list[TheaterPathOption],
        mastery_evidence: list[dict[str, Any]],
        error_evidence: list[dict[str, Any]],
        calibration_profile: dict[str, Any],
        topic_calibration: dict[str, Any],
    ) -> dict[str, Any]:
        best_route = options[0] if options else None
        graph_source_count = sum(
            1 for item in target_context.backbone if str(item.get("source_type") or "").startswith("graph")
        )
        sample_count = int(calibration_profile.get("sample_count") or 0)
        data_quality = best_route.data_quality if best_route else "low"
        confidence = best_route.data_sufficiency_score if best_route else 0.0
        evidence_points: list[str] = []
        if graph_source_count:
            evidence_points.append(f"{graph_source_count} 个路径节点来自你的知识星图")
        if mastery_evidence:
            evidence_points.append(f"{len(mastery_evidence)} 条掌握度证据参与估计")
        if error_evidence:
            evidence_points.append(f"{len(error_evidence)} 条错题/卡点证据参与风险判断")
        if sample_count:
            evidence_points.append(f"参考了 {sample_count} 次历史推演回填")
        if not evidence_points:
            evidence_points.append("当前主要基于主题结构推演，数字只适合当作区间参考")
        return {
            "data_quality": data_quality,
            "confidence_score": round(float(confidence or 0.0), 4),
            "is_cold_start": sample_count == 0,
            "target_resolution_mode": target_context.resolution_mode,
            "semantic_match_count": len(target_context.semantic_matches),
            "mastery_evidence_count": len(mastery_evidence),
            "error_evidence_count": len(error_evidence),
            "calibration_sample_count": sample_count,
            "topic_pending_feedback_count": int(topic_calibration.get("pending_count") or 0),
            "evidence_points": evidence_points[:4],
            "user_copy": "；".join(evidence_points[:3]),
        }

    @staticmethod
    def _build_prediction_next_action(
        *,
        prediction_id: str,
        topic: str,
        recommended_route: dict[str, Any],
    ) -> dict[str, Any]:
        route_id = str(recommended_route.get("id") or "").strip()
        title = str(recommended_route.get("title") or topic or "推荐路径").strip()
        week_one_tasks = [
            item for item in list(recommended_route.get("week_one_tasks") or []) if isinstance(item, dict)
        ]
        first_task = week_one_tasks[0] if week_one_tasks else {}
        return {
            "id": "adopt-recommended-route",
            "title": f"采纳「{title}」",
            "summary": (
                str(first_task.get("summary") or first_task.get("title") or "").strip()
                or "把推荐路径转成计划和第一周任务，再用真实结果校准预测。"
            ),
            "deep_link": f"/theater?prediction_id={quote(prediction_id)}&route_id={quote(route_id)}",
            "kind": "adopt_theater_route",
            "route_id": route_id,
            "prediction_id": prediction_id,
        }

    @staticmethod
    def _build_accuracy_tracking(
        *,
        prediction_id: str,
        generated_at: datetime,
        calibration_profile: dict[str, Any],
    ) -> dict[str, Any]:
        due_on = (generated_at.date() + timedelta(days=7)).isoformat()
        sample_count = int(calibration_profile.get("sample_count") or 0)
        avg_accuracy_score = float(calibration_profile.get("avg_accuracy_score") or 0.0)
        model_confidence = float(
            calibration_profile.get("data_sufficiency_score") or calibration_profile.get("confidence_score") or 0.0
        )
        coverage_rate = calibration_profile.get("coverage_rate")
        data_status = str(calibration_profile.get("data_status") or "cold_start")
        if sample_count >= 5:
            summary_hint = (
                f"基于你最近 {sample_count} 次已回填推演做过校准，当前模型稳定度约 {round(model_confidence * 100)}%。"
            )
        elif sample_count > 0:
            summary_hint = f"目前只积累了 {sample_count} 次回填记录，系统会继续边用边校准，建议把区间预测当作主参考。"
        else:
            summary_hint = "这还是冷启动预测，建议在 7 天后回填真实完成率和掌握度，帮系统建立你的校准基线。"
        return {
            "prediction_id": prediction_id,
            "status": "pending_feedback",
            "due_on": due_on,
            "summary_hint": summary_hint,
            "sample_count": sample_count,
            "avg_accuracy_score": round(avg_accuracy_score, 4),
            "model_confidence": round(model_confidence, 4),
            "coverage_rate": round(float(coverage_rate), 4) if coverage_rate is not None else None,
            "data_status": data_status,
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
        # 1. Hot path: Redis cache
        cached = await cache_service.get(f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}")
        if isinstance(cached, dict):
            return cached

        # 2. DB fallback
        if self.db is None:
            raise ValueError("Prediction not found or expired")
        result = await self.db.execute(
            select(TheaterPrediction).where(
                TheaterPrediction.prediction_id == prediction_id,
                TheaterPrediction.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError("Prediction not found or expired")

        # 3. Reconstruct full payload dict
        payload = self._prediction_row_to_payload(row)

        # 4. Hydrate graph from linked TheaterCandidateBundle
        await self._hydrate_graph_from_bundle(payload)

        # 4. Backfill Redis cache for subsequent reads
        try:
            await cache_service.set(
                f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
                payload,
                ttl=self.accuracy.TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("Prediction cache backfill failed for %s: %s", prediction_id, exc, exc_info=True)
        return payload

    async def _get_prediction_for_user_or_raise(self, prediction_id: str, *, user_id: UUID) -> dict[str, Any]:
        cached = await cache_service.get(f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}")
        if isinstance(cached, dict):
            owner_id = str(cached.get("user_id") or "").strip()
            if owner_id == str(user_id):
                return cached
            if owner_id:
                await self._raise_prediction_access_denied(user_id=user_id, prediction_id=prediction_id)

        if self.db is None:
            await self._raise_prediction_access_denied(user_id=user_id, prediction_id=prediction_id)

        result = await self.db.execute(
            select(TheaterPrediction).where(
                TheaterPrediction.prediction_id == prediction_id,
                TheaterPrediction.user_id == user_id,
                TheaterPrediction.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            await self._raise_prediction_access_denied(user_id=user_id, prediction_id=prediction_id)

        payload = self._prediction_row_to_payload(row)
        await self._hydrate_graph_from_bundle(payload)
        try:
            await cache_service.set(
                f"{self.accuracy.PREDICTION_KEY_PREFIX}{prediction_id}",
                payload,
                ttl=self.accuracy.TTL_SECONDS,
            )
        except Exception as exc:
            logger.debug("Prediction cache refresh failed for %s: %s", prediction_id, exc, exc_info=True)
        return payload

    async def _raise_prediction_access_denied(self, *, user_id: UUID, prediction_id: str) -> None:
        payload = {
            "event_type": "theater.access_denied",
            "requester_id": str(user_id),
            "target_resource_id": prediction_id,
            "timestamp": _utcnow().isoformat(),
        }
        try:
            payload["user_id"] = str(user_id)
            await event_bus_reliable.publish("theater.access_denied", payload)
        except Exception as exc:
            logger.warning("Failed to publish theater.access_denied for %s: %s", prediction_id, exc)
        raise AuthorizationError(
            message="resource access denied",
            detail={"error_code": "THEATER_ACCESS_DENIED"},
        )

    def _prediction_row_to_payload(self, row: TheaterPrediction) -> dict[str, Any]:
        """Reconstruct the full payload dict from a DB row.

        Graph data is loaded eagerly from the linked TheaterCandidateBundle.
        Callers must invoke ``await _hydrate_graph_from_bundle(payload)`` after
        getting the result if they need the graph populated.
        """
        payload: dict[str, Any] = {
            "prediction_id": row.prediction_id,
            "user_id": str(row.user_id) if row.user_id else "",
            "topic": row.topic,
            "simulation_session_id": row.simulation_session_id,
            "target_node_id": str(row.target_node_id) if row.target_node_id else None,
            "target_name": row.target_name,
            "candidate_bundle_id": str(row.candidate_bundle_id) if row.candidate_bundle_id else None,
            "horizon_days": row.horizon_days,
            "generated_at": row.generated_at.isoformat() if row.generated_at else None,
            "paths": row.paths or [],
            "discussion_turns": row.discussion_turns or [],
            "timeline": row.timeline or [],
            "selected_prediction": row.selected_prediction or {},
            "recommended_route_id": row.recommended_route_id or "",
            "target_resolution_mode": row.target_resolution_mode,
            "accuracy_tracking": row.accuracy_tracking or {},
            "routing_notes": row.routing_notes or {},
            "preview_mode": row.preview_mode,
        }
        if row.adopted_plan_id:
            payload["adopted_plan_id"] = str(row.adopted_plan_id)
        if row.adopted_at:
            payload["adopted_at"] = row.adopted_at.isoformat()
        if row.accuracy_summary:
            payload["accuracy_summary"] = row.accuracy_summary
        # Placeholder — will be populated by _hydrate_graph_from_bundle
        payload["graph"] = {"nodes": [], "edges": []}
        return payload

    async def _hydrate_graph_from_bundle(self, payload: dict[str, Any]) -> None:
        """Populate the ``graph`` key from the linked TheaterCandidateBundle."""
        bundle_id = self._maybe_uuid(payload.get("candidate_bundle_id"))
        if bundle_id is None or self.db is None:
            return
        try:
            bundle = await self.db.get(TheaterCandidateBundle, bundle_id)
            if bundle is not None:
                payload["graph"] = {
                    "nodes": list(bundle.nodes_payload or []),
                    "edges": list(bundle.edges_payload or []),
                }
        except Exception as exc:
            logger.debug("Prediction graph hydration skipped for bundle %s: %s", bundle_id, exc, exc_info=True)

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
        if strategy_type == "target_backtrack":
            return f"{node_name} 作为回补节点出现，作用是在暴露出卡点后快速止损。"
        if strategy_type == "constraint_first":
            return f"{node_name} 被切进小步节奏里，目的是降低启动阻力并提高连续完成率。"
        if strategy_type == "full_chain":
            return f"{node_name} 被放回完整依赖链中，作用是让后续理解建立在稳定前置之上。"
        return f"{node_name} 是前置链的一环，先补齐它能减少后续推导中的理解断层。"

    # ------------------------------------------------------------------
    # DB persistence helpers
    # ------------------------------------------------------------------

    async def _persist_prediction(self, payload: dict[str, Any]) -> None:
        """Write prediction to DB after Redis cache. Failure is non-blocking."""
        if self.db is None:
            return
        prediction_id = str(payload.get("prediction_id") or "").strip()
        if not prediction_id:
            return
        try:
            accuracy_tracking = dict(payload.get("accuracy_tracking") or {})
            due_on_raw = str(accuracy_tracking.get("due_on") or "").strip()
            due_on: datetime | None = None
            if due_on_raw:
                try:
                    due_on = datetime.fromisoformat(due_on_raw)
                except (TypeError, ValueError):
                    pass
            generated_at_raw = payload.get("generated_at")
            generated_at: datetime | None = None
            if isinstance(generated_at_raw, str):
                try:
                    generated_at = datetime.fromisoformat(generated_at_raw)
                except (TypeError, ValueError):
                    pass
            if generated_at is None:
                generated_at = _utcnow()

            candidate_bundle_id = self._maybe_uuid(payload.get("candidate_bundle_id"))
            target_node_id = self._maybe_uuid(payload.get("target_node_id"))

            # Use a savepoint so best-effort persistence failures do not poison
            # or roll back the caller's outer transaction.
            async with self.db.begin_nested():
                row = TheaterPrediction(
                    prediction_id=prediction_id,
                    user_id=self._maybe_uuid(payload.get("user_id")),
                    topic=str(payload.get("topic") or ""),
                    target_name=str(payload.get("target_name") or ""),
                    target_node_id=target_node_id,
                    target_resolution_mode=str(payload.get("target_resolution_mode") or "freeform_only"),
                    horizon_days=int(payload.get("horizon_days") or 14),
                    preview_mode=bool(payload.get("preview_mode")),
                    generated_at=generated_at,
                    candidate_bundle_id=candidate_bundle_id,
                    simulation_session_id=payload.get("simulation_session_id"),
                    recommended_route_id=payload.get("recommended_route_id"),
                    accuracy_status=str(accuracy_tracking.get("status") or "pending_feedback"),
                    accuracy_due_on=due_on,
                    paths=list(payload.get("paths") or []),
                    discussion_turns=list(payload.get("discussion_turns") or []),
                    timeline=list(payload.get("timeline") or []),
                    selected_prediction=payload.get("selected_prediction"),
                    routing_notes=dict(payload.get("routing_notes") or {}),
                    accuracy_tracking=accuracy_tracking,
                )
                self.db.add(row)
                await self.db.flush()
                try:
                    await event_bus_reliable.publish(
                        "theater.resource_created",
                        {
                            "event_type": "theater.resource_created",
                            "user_id": str(row.user_id) if row.user_id else "",
                            "prediction_id": prediction_id,
                            "candidate_bundle_id": str(candidate_bundle_id) if candidate_bundle_id else None,
                            "simulation_session_id": row.simulation_session_id,
                            "topic": row.topic,
                            "timestamp": _utcnow().isoformat(),
                        },
                    )
                except Exception as publish_exc:
                    logger.warning("Failed to publish theater.resource_created for %s: %s", prediction_id, publish_exc)
        except Exception as exc:
            logger.warning("Failed to persist prediction %s to DB: %s", prediction_id, exc)

    async def _update_prediction_db(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        updates: dict[str, Any],
    ) -> None:
        """Update a persisted prediction row. Failure is non-blocking."""
        if self.db is None:
            return
        try:
            # Keep best-effort updates isolated from the caller's transaction.
            async with self.db.begin_nested():
                result = await self.db.execute(
                    select(TheaterPrediction).where(
                        TheaterPrediction.prediction_id == prediction_id,
                        TheaterPrediction.user_id == user_id,
                        TheaterPrediction.deleted_at.is_(None),
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    return
                for key, value in updates.items():
                    setattr(row, key, value)
                await self.db.flush()
        except Exception as exc:
            logger.warning("Failed to update prediction %s in DB: %s", prediction_id, exc)
