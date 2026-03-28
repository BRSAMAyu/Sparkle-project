from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.core.cache import cache_service
from app.models.cognitive import BehaviorPattern
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, NodeRelation, StudyRecord, UserNodeStatus
from app.models.plan import Plan, PlanType
from app.models.recommendation import UserLearningProfile
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.services.insight_copy import present_pattern_description, present_pattern_name, present_pattern_solution
from app.services.llm_fallback_utils import analysis_llm


@dataclass(frozen=True)
class SimulationSeed:
    topic: str
    context: str
    tension_point: str
    source_type: str
    source_ids: list[str]
    relevance_score: float
    suggested_scenario: str
    suggested_experts: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "context": self.context,
            "tension_point": self.tension_point,
            "source_type": self.source_type,
            "source_ids": self.source_ids,
            "relevance_score": round(self.relevance_score, 4),
            "suggested_scenario": self.suggested_scenario,
            "suggested_experts": self.suggested_experts,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SimulationSeed":
        return cls(
            topic=str(payload.get("topic") or ""),
            context=str(payload.get("context") or ""),
            tension_point=str(payload.get("tension_point") or ""),
            source_type=str(payload.get("source_type") or "galaxy"),
            source_ids=[str(item) for item in list(payload.get("source_ids") or [])],
            relevance_score=float(payload.get("relevance_score") or 0.0),
            suggested_scenario=str(payload.get("suggested_scenario") or "study_group"),
            suggested_experts=[str(item) for item in list(payload.get("suggested_experts") or [])],
        )


class SeedExtractor:
    CACHE_PREFIX = "simulation:recommended_seeds:"
    CACHE_TTL_SECONDS = 60 * 5
    DEFAULT_PREWARM_SCENARIOS = (
        None,
        "study_group",
        "knowledge_debate",
        "historical_roleplay",
        "socratic_dialogue",
    )

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _is_missing_learning_profile_table(exc: Exception) -> bool:
        lowered = str(exc).lower()
        return "user_learning_profiles" in lowered and (
            "does not exist" in lowered or "undefinedtable" in lowered or "no such table" in lowered
        )

    async def _load_learning_profile_row(self, user_id: UUID):
        try:
            result = await self.db.execute(
                select(
                    UserLearningProfile.id,
                    UserLearningProfile.subject_distribution,
                    UserLearningProfile.preferred_duration_minutes,
                    UserLearningProfile.preferred_difficulty,
                ).where(UserLearningProfile.user_id == user_id)
            )
            return result.first()
        except Exception as exc:
            if not self._is_missing_learning_profile_table(exc):
                raise

            logger.warning(
                f"user_learning_profiles table missing during seed extraction for {user_id}; using degraded onboarding context"
            )
            with suppress(Exception):
                await self.db.rollback()
            return None

    async def get_cached_or_generate(
        self,
        user_id: UUID,
        *,
        scenario_key: str | None = None,
        limit: int = 3,
        force_refresh: bool = False,
    ) -> list[SimulationSeed]:
        cache_key = self._cache_key(user_id, scenario_key=scenario_key, limit=limit)
        if not force_refresh:
            cached = await cache_service.get(cache_key)
            if isinstance(cached, list):
                return [SimulationSeed.from_dict(item) for item in cached if isinstance(item, dict)]

        seeds = await self.extract_seeds(user_id, scenario_key=scenario_key, limit=limit)
        await cache_service.set(
            cache_key,
            [seed.to_dict() for seed in seeds],
            ttl=self.CACHE_TTL_SECONDS,
        )
        return seeds

    async def prewarm_for_scenarios(
        self,
        user_id: UUID,
        *,
        scenario_keys: tuple[str | None, ...] | None = None,
        limit: int = 3,
    ) -> None:
        for scenario_key in scenario_keys or self.DEFAULT_PREWARM_SCENARIOS:
            await self.get_cached_or_generate(
                user_id,
                scenario_key=scenario_key,
                limit=limit,
                force_refresh=True,
            )

    async def extract_seeds(
        self,
        user_id: UUID,
        *,
        scenario_key: str | None = None,
        limit: int = 3,
    ) -> list[SimulationSeed]:
        seeds: list[SimulationSeed] = []
        seeds.extend(await self._galaxy_seeds(user_id))
        seeds.extend(await self._error_seeds(user_id))
        seeds.extend(await self._sprint_seeds(user_id))
        seeds.extend(await self._cognitive_seeds(user_id))
        seeds.extend(await self._timeline_seeds(user_id))

        ranked = self._rank_by_scenario(seeds, scenario_key=scenario_key)
        if len(ranked) > limit:
            ranked = await self._refine_with_llm(ranked, scenario_key=scenario_key, limit=limit)
        ranked = ranked[: max(limit, 1)]
        if ranked:
            return ranked
        cold_start_seeds = await self._cold_start_seeds(
            user_id,
            scenario_key=scenario_key,
            limit=limit,
        )
        if cold_start_seeds:
            return cold_start_seeds
        return self._fallback_seeds(scenario_key=scenario_key, limit=limit)

    def _cache_key(self, user_id: UUID, *, scenario_key: str | None, limit: int) -> str:
        scenario_part = scenario_key or "default"
        return f"{self.CACHE_PREFIX}{user_id}:{scenario_part}:{max(limit, 1)}"

    async def _galaxy_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        source_node = aliased(KnowledgeNode)
        target_node = aliased(KnowledgeNode)
        source_status = aliased(UserNodeStatus)
        target_status = aliased(UserNodeStatus)

        stmt = (
            select(
                source_node.id,
                source_node.name,
                source_node.description,
                target_node.id,
                target_node.name,
                target_node.description,
                NodeRelation.relation_type,
                func.coalesce(source_status.mastery_score, 0.0),
                func.coalesce(target_status.mastery_score, 0.0),
                func.coalesce(NodeRelation.strength, 0.4),
            )
            .join(source_node, source_node.id == NodeRelation.source_node_id)
            .join(target_node, target_node.id == NodeRelation.target_node_id)
            .outerjoin(
                source_status,
                and_(source_status.node_id == source_node.id, source_status.user_id == user_id),
            )
            .outerjoin(
                target_status,
                and_(target_status.node_id == target_node.id, target_status.user_id == user_id),
            )
            .where(or_(source_status.user_id == user_id, target_status.user_id == user_id))
            .order_by(
                desc(
                    func.abs(
                        func.coalesce(source_status.mastery_score, 0.0)
                        - func.coalesce(target_status.mastery_score, 0.0)
                    )
                ),
                desc(NodeRelation.strength),
            )
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for (
            source_id,
            source_name,
            source_description,
            target_id,
            target_name,
            target_description,
            relation_type,
            source_mastery,
            target_mastery,
            strength,
        ) in rows:
            mastery_gap = abs(float(source_mastery or 0.0) - float(target_mastery or 0.0))
            weaker_name = source_name if float(source_mastery or 0.0) <= float(target_mastery or 0.0) else target_name
            relation_label = str(relation_type or "related").replace("_", " ").lower()
            seeds.append(
                SimulationSeed(
                    topic=f"{source_name} 与 {target_name} 的关键区别",
                    context=(
                        f"图谱显示 {source_name} 与 {target_name} 之间存在 {relation_label} 关系。"
                        f" 当前掌握差为 {mastery_gap:.0f} 分。"
                        f" {source_description or target_description or '适合用一场可视化讨论梳理依赖与边界。'}"
                    ),
                    tension_point=f"{weaker_name} 是当前更可能拖慢理解链路的薄弱点，值得优先拆解。",
                    source_type="galaxy",
                    source_ids=[str(source_id), str(target_id)],
                    relevance_score=min(0.98, 0.58 + mastery_gap / 140 + float(strength or 0.0) * 0.18),
                    suggested_scenario="knowledge_debate",
                    suggested_experts=["星图导航", "深度分析"],
                )
            )
        return seeds

    async def _error_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        stmt = (
            select(
                ErrorRecord.id,
                ErrorRecord.subject_code,
                ErrorRecord.chapter,
                ErrorRecord.question_text,
                ErrorRecord.latest_analysis,
                ErrorRecord.mastery_level,
            )
            .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
            .order_by(ErrorRecord.updated_at.desc())
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for error_id, subject_code, chapter, question_text, latest_analysis, mastery_level in rows:
            analysis = self._coerce_error_analysis(latest_analysis)
            root_cause = str(analysis.get("root_cause") or analysis.get("error_type") or "").strip()
            subject_label = str(chapter or subject_code or "近期错题").strip()
            prompt = root_cause or str(question_text or "").strip()[:90] or "同类题目中出现了重复失误。"
            weakness_factor = 1.0 - float(mastery_level or 0.0)
            seeds.append(
                SimulationSeed(
                    topic=f"{subject_label} 错因深挖",
                    context=f"错题本最近记录显示：{prompt}",
                    tension_point="需要辨认这是概念误解、步骤跳跃，还是符号与细节失守。",
                    source_type="error_book",
                    source_ids=[str(error_id)],
                    relevance_score=min(0.97, 0.62 + weakness_factor * 0.25),
                    suggested_scenario="study_group",
                    suggested_experts=["错题教练", "深度分析"],
                )
            )
        return seeds

    def _coerce_error_analysis(self, latest_analysis: Any) -> dict[str, Any]:
        if isinstance(latest_analysis, dict):
            return latest_analysis
        if isinstance(latest_analysis, list):
            # Historical rows sometimes store analysis steps as a list of items.
            # Prefer the first mapping that carries a meaningful error summary.
            for item in latest_analysis:
                if isinstance(item, dict):
                    root_cause = item.get("root_cause") or item.get("error_type")
                    if root_cause:
                        return item
            return {}
        return {}

    async def _sprint_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        stmt = (
            select(Plan.id, Plan.name, Plan.description, Plan.progress, Plan.target_date, Plan.subject)
            .where(Plan.user_id == user_id, Plan.type == PlanType.SPRINT)
            .order_by(Plan.is_active.desc(), Plan.updated_at.desc())
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for plan_id, name, description, progress, target_date, subject in rows:
            progress_value = float(progress or 0.0)
            if progress_value >= 0.85:
                continue
            seeds.append(
                SimulationSeed(
                    topic=f"复盘 {name} 的推进瓶颈",
                    context=(
                        f"当前 Sprint 进度约为 {progress_value * 100:.0f}%。"
                        f" {description or (subject and f'主题聚焦在 {subject}。') or '值得复盘节奏、难度与时间预算。'}"
                        f" {'目标日期为 ' + str(target_date) + '。' if target_date else ''}"
                    ).strip(),
                    tension_point="问题不一定在努力不够，也可能是路径设计、时间预算或前置条件错配。",
                    source_type="sprint",
                    source_ids=[str(plan_id)],
                    relevance_score=min(0.96, 0.57 + (1.0 - progress_value) * 0.3),
                    suggested_scenario="study_group",
                    suggested_experts=["时间规划", "深度分析"],
                )
            )
        return seeds

    async def _cognitive_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        stmt = (
            select(
                BehaviorPattern.id,
                BehaviorPattern.pattern_name,
                BehaviorPattern.description,
                BehaviorPattern.solution_text,
                BehaviorPattern.confidence_score,
            )
            .where(
                BehaviorPattern.user_id == user_id,
                BehaviorPattern.is_archived.is_(False),
                BehaviorPattern.confidence_score >= 0.65,
            )
            .order_by(desc(BehaviorPattern.confidence_score), desc(BehaviorPattern.updated_at))
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for pattern_id, pattern_name, description, solution_text, confidence in rows:
            display_name = present_pattern_name(pattern_name)
            seeds.append(
                SimulationSeed(
                    topic=f"拆解你的 {display_name} 学习定式",
                    context=(
                        present_pattern_description(pattern_name, description)
                        or present_pattern_solution(pattern_name, solution_text)
                        or "最近的行为画像显示这里存在稳定模式。"
                    ),
                    tension_point="这类定式往往不是不会，而是在某个决策瞬间重复做出同样选择。",
                    source_type="cognitive",
                    source_ids=[str(pattern_id)],
                    relevance_score=min(0.95, 0.55 + float(confidence or 0.0) * 0.35),
                    suggested_scenario="socratic_dialogue",
                    suggested_experts=["学伴", "认知教练"],
                )
            )
        return seeds

    async def _timeline_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(days=7)
        previous_cutoff = now - timedelta(days=14)
        recent_delta = func.coalesce(
            func.sum(
                case(
                    (StudyRecord.created_at >= recent_cutoff, StudyRecord.mastery_delta),
                    else_=0.0,
                )
            ),
            0.0,
        )
        previous_delta = func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            StudyRecord.created_at >= previous_cutoff,
                            StudyRecord.created_at < recent_cutoff,
                        ),
                        StudyRecord.mastery_delta,
                    ),
                    else_=0.0,
                )
            ),
            0.0,
        )
        recent_minutes = func.coalesce(
            func.sum(
                case(
                    (StudyRecord.created_at >= recent_cutoff, StudyRecord.study_minutes),
                    else_=0,
                )
            ),
            0,
        )
        stmt = (
            select(
                KnowledgeNode.id,
                KnowledgeNode.name,
                recent_delta.label("recent_delta"),
                previous_delta.label("previous_delta"),
                recent_minutes.label("recent_minutes"),
            )
            .join(KnowledgeNode, KnowledgeNode.id == StudyRecord.node_id)
            .where(StudyRecord.user_id == user_id, StudyRecord.created_at >= previous_cutoff)
            .group_by(KnowledgeNode.id, KnowledgeNode.name)
            .order_by((recent_delta - previous_delta).asc(), recent_minutes.asc())
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for node_id, node_name, recent_value, previous_value, minutes in rows:
            recent_float = float(recent_value or 0.0)
            previous_float = float(previous_value or 0.0)
            if recent_float >= previous_float:
                continue
            drop = previous_float - recent_float
            seeds.append(
                SimulationSeed(
                    topic=f"{node_name} 最近进入波动期",
                    context=(
                        f"近 7 天累计提升 {recent_float:.1f}，前 7 天为 {previous_float:.1f}，"
                        f"最近投入约 {int(minutes or 0)} 分钟。"
                    ),
                    tension_point="这可能意味着投入下降、复习断档，或题型升级带来的短期回撤。",
                    source_type="timeline",
                    source_ids=[str(node_id)],
                    relevance_score=min(0.94, 0.54 + drop / 8),
                    suggested_scenario="knowledge_debate",
                    suggested_experts=["星图导航", "学伴"],
                )
            )
        return seeds

    def _rank_by_scenario(
        self,
        seeds: list[SimulationSeed],
        *,
        scenario_key: str | None,
    ) -> list[SimulationSeed]:
        deduped: dict[tuple[str, str], SimulationSeed] = {}
        for seed in seeds:
            key = (seed.topic, seed.source_type)
            best = deduped.get(key)
            if best is None or seed.relevance_score > best.relevance_score:
                deduped[key] = seed

        ranked = sorted(
            deduped.values(),
            key=lambda seed: (
                1 if scenario_key and seed.suggested_scenario == scenario_key else 0,
                seed.relevance_score,
            ),
            reverse=True,
        )
        return ranked

    async def _refine_with_llm(
        self,
        seeds: list[SimulationSeed],
        *,
        scenario_key: str | None,
        limit: int,
    ) -> list[SimulationSeed]:
        if len(seeds) <= limit:
            return seeds

        fallback_topics = [seed.topic for seed in seeds[:limit]]
        payload = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with a selected_topics array. "
                        "Pick the most action-worthy learning exploration seeds."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Preferred scenario: {scenario_key or 'auto'}\n"
                        f"Limit: {limit}\n"
                        f"Candidates: {[seed.to_dict() for seed in seeds[:8]]}\n"
                        "Favor seeds that are concrete, timely, and easy to start without extra setup."
                    ),
                },
            ],
            fallback={"selected_topics": fallback_topics},
            temperature=0.2,
        )
        selected_topics = self._extract_selected_topics(payload)
        if not selected_topics:
            return seeds

        refined = [seed for seed in seeds if seed.topic in selected_topics]
        if len(refined) < limit:
            missing = [seed for seed in seeds if seed.topic not in selected_topics]
            refined.extend(missing[: limit - len(refined)])
        return refined

    @staticmethod
    def _extract_selected_topics(payload: Any) -> set[str]:
        raw_items: list[Any]
        if isinstance(payload, dict):
            raw = payload.get("selected_topics")
            if isinstance(raw, list):
                raw_items = raw
            elif raw is None:
                raw_items = []
            else:
                raw_items = [raw]
        elif isinstance(payload, list):
            raw_items = payload
        elif payload is None:
            raw_items = []
        else:
            raw_items = [payload]

        selected_topics: set[str] = set()
        for item in raw_items:
            if isinstance(item, dict):
                topic = str(item.get("topic") or item.get("selected_topic") or "").strip()
            else:
                topic = str(item).strip()
            if topic:
                selected_topics.add(topic)
        return selected_topics

    def _fallback_seeds(self, *, scenario_key: str | None, limit: int) -> list[SimulationSeed]:
        defaults = [
            SimulationSeed(
                topic="从一个卡住的知识点开始圆桌讨论",
                context="如果你最近有一个总觉得会但讲不清的问题，这就是最适合启动模拟的入口。",
                tension_point="目标不是立刻答对，而是找出为什么它总在关键时刻变模糊。",
                source_type="fallback",
                source_ids=[],
                relevance_score=0.5,
                suggested_scenario="study_group",
                suggested_experts=["学伴", "深度分析"],
            ),
            SimulationSeed(
                topic="用一场知识辩论检验前置概念",
                context="把一个核心概念放到正反论证里，最容易看出你是真的理解还是只记住表面结论。",
                tension_point="一旦论证链条断掉，真正的前置薄弱点就会暴露出来。",
                source_type="fallback",
                source_ids=[],
                relevance_score=0.48,
                suggested_scenario="knowledge_debate",
                suggested_experts=["星图导航", "深度分析"],
            ),
            SimulationSeed(
                topic="用苏格拉底式追问拆出卡点",
                context="适合在你说不清、但又隐约知道哪里不对的时候使用。",
                tension_point="关键不是给答案，而是用连续追问把思路里的空白处显出来。",
                source_type="fallback",
                source_ids=[],
                relevance_score=0.46,
                suggested_scenario="socratic_dialogue",
                suggested_experts=["学伴"],
            ),
        ]
        ranked = self._rank_by_scenario(defaults, scenario_key=scenario_key)
        return ranked[: max(limit, 1)]

    async def _cold_start_seeds(
        self,
        user_id: UUID,
        *,
        scenario_key: str | None,
        limit: int,
    ) -> list[SimulationSeed]:
        seeds: list[SimulationSeed] = []
        seeds.extend(await self._onboarding_seeds(user_id))
        seeds.extend(await self._task_bootstrap_seeds(user_id))
        seeds.extend(await self._active_plan_bootstrap_seeds(user_id))
        if not seeds:
            seeds.extend(await self._graph_bootstrap_seeds(limit=max(limit * 2, 4)))
        ranked = self._rank_by_scenario(seeds, scenario_key=scenario_key)
        return ranked[: max(limit, 1)]

    async def _onboarding_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        profile_row = await self._load_learning_profile_row(user_id)
        user_row = (
            await self.db.execute(
                select(User.nickname, User.full_name, User.curiosity_preference, User.depth_preference).where(
                    User.id == user_id
                )
            )
        ).first()
        plan_rows = (
            await self.db.execute(
                select(Plan.subject, Plan.name)
                .where(Plan.user_id == user_id, Plan.is_active.is_(True))
                .order_by(desc(Plan.updated_at))
                .limit(3)
            )
        ).all()

        profile_id = str(profile_row[0]) if profile_row else ""
        subject_distribution = profile_row[1] if profile_row else {}
        preferred_duration = int(profile_row[2] or 25) if profile_row else 25
        preferred_difficulty = float(profile_row[3] or 0.0) if profile_row else 0.0
        curiosity = float(user_row[2] or 0.0) if user_row else 0.0
        depth = float(user_row[3] or 0.0) if user_row else 0.0
        learner_name = str((user_row[0] if user_row and user_row[0] else user_row[1] if user_row else "") or "").strip()

        subject_hints = self._extract_profile_subject_hints(subject_distribution)
        for subject, name in plan_rows:
            label = str(subject or name or "").strip()
            if label and label not in subject_hints:
                subject_hints.append(label)

        scenario_key = self._preferred_onboarding_scenario(curiosity=curiosity, depth=depth)
        experts = self._preferred_onboarding_experts(curiosity=curiosity, depth=depth)
        difficulty_hint = "先用低门槛例子建立直觉" if preferred_difficulty and preferred_difficulty < 2.5 else "先搭清概念骨架再进入练习"
        pace_hint = f"按你偏好的 {max(preferred_duration, 20)} 分钟节奏切分" if preferred_duration else "先切成 20-30 分钟能完成的小步"

        seeds: list[SimulationSeed] = []
        for subject in subject_hints[:3]:
            seeds.append(
                SimulationSeed(
                    topic=f"先为 {subject} 生成一条入门理解路线",
                    context=(
                        f"{learner_name + '的' if learner_name else '你的'}学习画像显示，{subject} 是当前最值得优先启动的方向。"
                        f" 建议 {pace_hint}，并通过一场仿真先找出第一步和第一处易错点。"
                    ),
                    tension_point=f"{difficulty_hint}，不要一上来就把 {subject} 变成纯刷题任务。",
                    source_type="onboarding_profile",
                    source_ids=[profile_id] if profile_id else [],
                    relevance_score=0.78,
                    suggested_scenario=scenario_key,
                    suggested_experts=experts,
                )
            )

        if not seeds and profile_id:
            seeds.append(
                SimulationSeed(
                    topic="先确定最适合你的学习启动方式",
                    context=(
                        f"画像里已经记录了你的学习节奏偏好，适合先做一轮冷启动仿真，"
                        f"确认应该从提问式、辩论式还是小组式开始。"
                    ),
                    tension_point="先把启动方式选对，比一开始就追求高强度更重要。",
                    source_type="onboarding_profile",
                    source_ids=[profile_id],
                    relevance_score=0.7,
                    suggested_scenario=scenario_key,
                    suggested_experts=experts,
                )
            )
        return seeds

    @staticmethod
    def _extract_profile_subject_hints(subject_distribution: Any) -> list[str]:
        if not isinstance(subject_distribution, dict):
            return []
        ranked_items = sorted(
            ((str(key).strip(), float(value or 0.0)) for key, value in subject_distribution.items()),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            key
            for key, _ in ranked_items
            if key and not SeedExtractor._looks_like_identifier(key)
        ]

    @staticmethod
    def _looks_like_identifier(value: str) -> bool:
        compact = value.replace("-", "").strip().lower()
        if len(compact) >= 16 and all(char in "0123456789abcdef" for char in compact):
            return True
        return False

    @staticmethod
    def _preferred_onboarding_scenario(*, curiosity: float, depth: float) -> str:
        if curiosity >= 0.65:
            return "historical_roleplay"
        if depth >= 0.6:
            return "knowledge_debate"
        return "study_group"

    @staticmethod
    def _preferred_onboarding_experts(*, curiosity: float, depth: float) -> list[str]:
        if curiosity >= 0.65:
            return ["学伴", "故事化引导"]
        if depth >= 0.6:
            return ["深度分析", "星图导航"]
        return ["学伴", "时间规划"]

    async def _task_bootstrap_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        stmt = (
            select(Task.id, Task.title, Task.status, Task.estimated_minutes, KnowledgeNode.name)
            .outerjoin(KnowledgeNode, KnowledgeNode.id == Task.knowledge_node_id)
            .where(
                Task.user_id == user_id,
                Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            )
            .order_by(desc(Task.priority), desc(Task.updated_at))
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for task_id, title, status, estimated_minutes, node_name in rows:
            label = str(node_name or title or "").strip()
            if not label:
                continue
            status_label = "正在推进" if status == TaskStatus.IN_PROGRESS else "尚未开始"
            seeds.append(
                SimulationSeed(
                    topic=f"把 {label} 拆成第一轮可执行练习",
                    context=(
                        f"你当前有一个{status_label}的任务：{title}。"
                        f" 预计时长约 {int(estimated_minutes or 25)} 分钟，适合先用一场仿真把第一步说清楚。"
                    ),
                    tension_point="重点不是直接做完，而是先拆出起步动作、常见误区和第一轮反馈点。",
                    source_type="task_bootstrap",
                    source_ids=[str(task_id)],
                    relevance_score=0.72 if status == TaskStatus.IN_PROGRESS else 0.66,
                    suggested_scenario="study_group",
                    suggested_experts=["学伴", "时间规划"],
                )
            )
        return seeds

    async def _active_plan_bootstrap_seeds(self, user_id: UUID) -> list[SimulationSeed]:
        stmt = (
            select(Plan.id, Plan.subject, Plan.name, Plan.progress)
            .where(Plan.user_id == user_id, Plan.is_active.is_(True))
            .order_by(desc(Plan.updated_at))
            .limit(4)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for plan_id, subject, name, progress in rows:
            label = str(subject or name or "").strip()
            if not label:
                continue
            progress_pct = float(progress or 0.0) * 100.0
            seeds.append(
                SimulationSeed(
                    topic=f"把 {label} 变成一条更稳的学习起步路线",
                    context=(
                        f"当前你已经围绕 {label} 建立了计划，进度约 {progress_pct:.0f}%。"
                        " 如果还没真正形成稳定节奏，最适合先通过一场模拟把路径和卡点说透。"
                    ),
                    tension_point="这里最容易出的问题通常不是目标不对，而是第一步过大、节奏过猛或前置条件没补齐。",
                    source_type="plan_bootstrap",
                    source_ids=[str(plan_id)],
                    relevance_score=min(0.78, 0.62 + max(0.0, 1.0 - float(progress or 0.0)) * 0.12),
                    suggested_scenario="socratic_dialogue",
                    suggested_experts=["学伴", "深度分析"],
                )
            )
        return seeds

    async def _graph_bootstrap_seeds(self, *, limit: int) -> list[SimulationSeed]:
        stmt = (
            select(KnowledgeNode.id, KnowledgeNode.name, KnowledgeNode.description, KnowledgeNode.importance_level)
            .where(KnowledgeNode.is_seed.is_(True))
            .order_by(desc(KnowledgeNode.importance_level), desc(KnowledgeNode.updated_at))
            .limit(limit)
        )
        rows = (await self.db.execute(stmt)).all()
        seeds: list[SimulationSeed] = []
        for node_id, name, description, importance in rows:
            label = str(name or "").strip()
            if not label:
                continue
            seeds.append(
                SimulationSeed(
                    topic=f"从 {label} 开始搭一条入门理解链",
                    context=(
                        description
                        or f"{label} 是当前知识星图里较核心的主题之一，适合作为冷启动时的第一条探索线。"
                    ),
                    tension_point="先找出它最关键的前置概念和最容易误解的边界，比盲目刷题更适合作为起步。",
                    source_type="starter_graph",
                    source_ids=[str(node_id)],
                    relevance_score=min(0.7, 0.52 + float(importance or 1) * 0.03),
                    suggested_scenario="knowledge_debate",
                    suggested_experts=["星图导航", "学伴"],
                )
            )
        return seeds
