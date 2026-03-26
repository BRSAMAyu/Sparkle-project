from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.cognitive import BehaviorPattern
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.models.plan import PlanType
from app.schemas.plan import PlanCreate
from app.services.galaxy.graph_structure_service import GraphStructureEvolutionService
from app.services.llm_fallback_utils import analysis_llm
from app.services.plan_service import PlanService
from app.services.graph_reasoning_service import GraphReasoningService
from app.services.cognitive_service import CognitiveService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


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
            "steps": [step.to_dict() for step in self.steps],
        }


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
    ) -> dict[str, Any]:
        target_node = await self._resolve_target_node(topic=topic, target_node_id=target_node_id)
        learning_path = await self.graph_reasoning.generate_learning_path(
            user_id,
            target_node.id,
            include_related_suggestions=True,
        )
        backbone = [item for item in learning_path if not item.get("is_optional")]
        if not backbone:
            raise ValueError("Unable to generate a learning backbone for the selected topic")

        mastery_map = await self._get_mastery_map(user_id)
        study_preferences = await self._build_user_learning_profile(user_id)
        pattern_names = await self._top_pattern_names(user_id)
        graph_bundle = await self._build_graph_bundle(backbone, mastery_map)
        options = self._build_path_options(
            target_name=target_node.name,
            backbone=backbone,
            mastery_map=mastery_map,
            horizon_days=max(7, min(horizon_days, 30)),
            study_preferences=study_preferences,
            pattern_names=pattern_names,
        )
        selected_prediction = options[0].to_dict() if options else {}
        discussion = await self._build_discussion(
            topic=topic,
            target_name=target_node.name,
            options=options,
            graph_bundle=graph_bundle,
            pattern_names=pattern_names,
        )
        timeline = self._build_timeline(options, discussion)

        prediction_id = str(uuid4())
        payload = {
            "prediction_id": prediction_id,
            "topic": topic,
            "target_node_id": str(target_node.id),
            "target_name": target_node.name,
            "horizon_days": horizon_days,
            "generated_at": _utcnow().isoformat(),
            "paths": [option.to_dict() for option in options],
            "discussion_turns": discussion,
            "graph": graph_bundle,
            "timeline": timeline,
            "selected_prediction": selected_prediction,
            "routing_notes": {
                "patterns": pattern_names,
                "recommended_entry": options[0].title if options else "稳扎稳打",
            },
        }
        await self.accuracy.record_prediction(payload)
        return payload

    async def simulate_what_if(
        self,
        *,
        user_id: UUID,
        prediction_id: str,
        route_id: str,
        skip_node_id: str,
    ) -> dict[str, Any]:
        cached = await self._get_prediction_or_raise(prediction_id)
        selected_route = self._find_route(cached, route_id)
        skipped_step = self._find_step(selected_route, skip_node_id)
        target_name = str(cached.get("target_name") or "")

        downstream = [
            step for step in list(selected_route.get("steps") or [])
            if int(step.get("index") or 0) > int(skipped_step.get("index") or 0)
        ]
        mastery_penalty = 8 + (len(downstream) * 3)
        predicted_mastery = _clamp(float(selected_route.get("estimated_mastery") or 0.0) - mastery_penalty, 5.0, 100.0)
        completion_penalty = 0.08 + (len(downstream) * 0.03)
        predicted_completion = _clamp(
            float(selected_route.get("estimated_completion_rate") or 0.0) - completion_penalty,
            0.15,
            0.99,
        )

        consequence_lines = [
            f"跳过 {skipped_step.get('node_name')} 后，{target_name} 的推导链会变短，但中间校验点也会减少。",
        ]
        if downstream:
            consequence_lines.append(
                f"最容易受影响的是 {downstream[0].get('node_name')}，因为它默认依赖前一步的符号感和方法熟练度。"
            )
        if float(skipped_step.get("current_mastery") or 0.0) < 60:
            consequence_lines.append("当前这个节点本身仍偏弱，直接跳过会放大后面“看得懂但做不稳”的风险。")

        suggestion = (
            f"建议不要完全跳过 {skipped_step.get('node_name')}，可以把它压缩成 {max(20, int(skipped_step.get('estimated_minutes') or 30) // 2)} 分钟速览。"
        )
        result = {
            "prediction_id": prediction_id,
            "route_id": route_id,
            "skip_node_id": skip_node_id,
            "skip_node_name": skipped_step.get("node_name"),
            "predicted_mastery": round(predicted_mastery, 2),
            "predicted_completion_rate": round(predicted_completion, 4),
            "delta_mastery": round(predicted_mastery - float(selected_route.get("estimated_mastery") or 0.0), 2),
            "delta_completion_rate": round(
                predicted_completion - float(selected_route.get("estimated_completion_rate") or 0.0),
                4,
            ),
            "consequences": consequence_lines,
            "suggestion": suggestion,
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

        await self.db.commit()
        return {
            "prediction_id": prediction_id,
            "route_id": route_id,
            "plan_id": str(plan.id),
            "plan_name": plan.name,
            "source_metadata": plan.source_metadata,
        }

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

        stmt = (
            select(KnowledgeNode)
            .where(
                or_(
                    func.lower(KnowledgeNode.name).contains(normalized),
                    func.lower(func.coalesce(KnowledgeNode.description, "")).contains(normalized),
                )
            )
            .order_by(desc(KnowledgeNode.importance_level), desc(KnowledgeNode.updated_at))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        node = result.scalar_one_or_none()
        if not node:
            raise ValueError(f'No knowledge node found for topic "{topic}"')
        return node

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
        return [str(item[0]) for item in result.all() if str(item[0]).strip()]

    async def _build_graph_bundle(
        self,
        backbone: list[dict[str, Any]],
        mastery_map: dict[str, float],
    ) -> dict[str, Any]:
        node_ids = [UUID(str(item["id"])) for item in backbone[: self.MAX_GRAPH_NODES]]
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
        turns = list((payload or {}).get("turns") or [])
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

    def _build_timeline(self, options: list[TheaterPathOption], discussion: list[dict[str, Any]]) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        for index, option in enumerate(options):
            frames.append(
                {
                    "index": index,
                    "label": option.title,
                    "route_id": option.id,
                    "focus_node_ids": [step.node_id for step in option.steps[:3]],
                    "discussion_turn_index": min(index, max(len(discussion) - 1, 0)),
                }
            )
        return frames

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
    def _step_rationale(*, strategy_type: str, node_name: str, is_target: bool) -> str:
        if is_target:
            return f"这是目标节点 {node_name}，需要把概念、计算和表达三件事一起打通。"
        if strategy_type == "breakthrough":
            return f"{node_name} 作为回补节点出现，作用是在暴露出卡点后快速止损。"
        if strategy_type == "personalized":
            return f"{node_name} 被切进小步节奏里，目的是降低启动阻力并提高连续完成率。"
        return f"{node_name} 是前置链的一环，先补齐它能减少后续推导中的理解断层。"
