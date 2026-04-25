"""Structured cold-start intake for exam sprint mode."""

from __future__ import annotations

import json
import math
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.models.plan import PlanPriority, PlanStage, PlanType
from app.models.task import Task
from app.orchestration.bottleneck_analyzer import bottleneck_analyzer
from app.orchestration.planning_workflow import (
    PLANNING_PROFILE_KEYS,
    PlanningSession,
    PlanningWorkflowManager,
    _task_type_for_day_spec,
)
from app.scenario_packs.exam_prep_14d import load_exam_prep_14d_manifest
from app.schemas.exam_sprint import (
    ExamSprintAssessment,
    ExamSprintGoalModel,
    ExamSprintIntakeRequest,
    ExamSprintIntakeResponse,
    ExamSprintLaunchPayload,
    ExamSprintPackSelection,
    ExamSprintStrategyPreview,
    ExamSprintUserModel,
)
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.plan_service import PlanService
from app.services.profile_write_service import ProfileWriteService
from app.services.task_service import TaskService


@dataclass
class GeneratedPlanBundle:
    plan_id: str
    plan_name: str
    first_day_task_ids: list[str]
    recommended_task_id: str | None
    first_day_focus: str
    first_day_output: str


class ExamSprintIntakeService:
    """Turn a 6-field intake form into an initial sprint model and launch payload."""

    def __init__(
        self,
        db: AsyncSession,
        redis_client=None,
        planning_manager: PlanningWorkflowManager | None = None,
    ) -> None:
        self.db = db
        self.redis = redis_client or cache_service.redis
        self.planning_manager = planning_manager or PlanningWorkflowManager(redis_client=self.redis)

    async def intake(
        self,
        *,
        user_id: UUID,
        request: ExamSprintIntakeRequest,
        profile_context: dict[str, Any] | None = None,
    ) -> ExamSprintIntakeResponse:
        today = self._today()
        if request.exam_date < today:
            raise ValueError("考试日期不能早于今天")

        conversation_id = self._strip(request.conversation_id) or f"exam-sprint-{uuid.uuid4()}"
        planning_session_id = str(uuid.uuid4())
        days_left = max(1, (request.exam_date - today).days)

        selected_pack = self._select_pack(days_left=days_left)
        goal_model = self._build_goal_model(request=request, days_left=days_left)
        assessment = self._build_initial_assessment(request=request, goal_model=goal_model, days_left=days_left)
        user_model = self._build_user_model(
            request=request,
            planning_session_id=planning_session_id,
            conversation_id=conversation_id,
        )

        collected = self._build_collected(
            request=request,
            user_model=user_model,
            goal_model=goal_model,
            selected_pack=selected_pack,
            assessment=assessment,
        )

        cold_start_context = {
            **self.planning_manager._build_cold_start_context(collected),
            "target_mode": goal_model.target_mode,
            "recommended_mode": goal_model.recommended_mode,
            "estimated_score_now": goal_model.estimated_score_now,
            "exam_date": request.exam_date.isoformat(),
            "study_time_minutes": request.daily_study_minutes,
            "weak_chapters": list(request.baseline.weak_chapters),
            "scope_text": self._strip(request.scope_context.text),
            "scope_file_ids": list(request.scope_context.file_ids),
            "scope_file_names": list(request.scope_context.file_names),
        }
        collected["cold_start_context"] = cold_start_context

        session = PlanningSession(
            planning_session_id=planning_session_id,
            chat_session_id=conversation_id,
            user_id=str(user_id),
            state="AWAITING_CONFIRM",
            goal_raw=self._goal_raw(subject=request.subject, days_left=days_left, target_mode=request.target_mode),
            collected=collected,
        )
        await self.planning_manager.save_session(session)

        runtime_state = await self.planning_manager.runtime_adapter.get_or_create_state(
            user_id=str(user_id),
            conversation_id=conversation_id,
            db=self.db,
            planning_session_id=planning_session_id,
            goal_raw=session.goal_raw,
            profile_context=profile_context,
            collected=collected,
        )

        session.bottlenecks = self._build_rule_bottlenecks(session)
        strategy = self.planning_manager._build_strategy(session, aurora_state=runtime_state)
        session.confirmed_strategy = strategy
        await self._persist_profile_payloads(
            user_id=user_id,
            cold_start_context=cold_start_context,
            conversation_id=conversation_id,
        )

        generated = await self._generate_plan_and_tasks(
            user_id=user_id,
            request=request,
            session=session,
            runtime_state=runtime_state,
            strategy=strategy,
            goal_model=goal_model,
            assessment=assessment,
            selected_pack=selected_pack,
        )

        session.state = "DONE"
        await self.planning_manager.save_session(session)
        runtime_state.current_intent = {"intent_type": "wait", "target_tension_id": None, "payload": {}}
        await self.planning_manager.runtime_adapter.save_state(runtime_state, db=self.db)

        return ExamSprintIntakeResponse(
            planning_session_id=planning_session_id,
            conversation_id=conversation_id,
            user_model=user_model,
            goal_model=goal_model,
            selected_pack=selected_pack,
            initial_assessment=assessment,
            strategy_preview=ExamSprintStrategyPreview(
                sprint_mode=str(strategy.get("sprint_policy", {}).get("sprint_mode") or "standard_exam_sprint"),
                daily_commitment_range=self._strip(strategy.get("daily_commitment_range")) or "1-2小时",
                first_day_focus=generated.first_day_focus,
                first_day_output=generated.first_day_output,
            ),
            launch=ExamSprintLaunchPayload(
                plan_id=generated.plan_id,
                plan_name=generated.plan_name,
                first_day_task_ids=generated.first_day_task_ids,
                recommended_task_id=generated.recommended_task_id,
                plan_route=f"/plans/{generated.plan_id}",
                recommended_task_route=(
                    f"/tasks/{generated.recommended_task_id}" if generated.recommended_task_id else None
                ),
            ),
        )

    async def _persist_profile_payloads(
        self,
        *,
        user_id: UUID,
        cold_start_context: dict[str, Any],
        conversation_id: str,
    ) -> None:
        writer = ProfileWriteService(self.db, self.redis)
        await writer.set_explicit_preferences(
            user_id=user_id,
            updates={
                PLANNING_PROFILE_KEYS["cold_start_context"]: cold_start_context,
                PLANNING_PROFILE_KEYS["onboarding_modeling_state"]: {
                    "completed": True,
                    "skipped": False,
                    "conversation_id": conversation_id,
                    "source": "exam_sprint_setup",
                },
            },
            evidence_refs_by_key={
                PLANNING_PROFILE_KEYS["cold_start_context"]: [{"type": "system", "id": "exam_sprint_intake.v1"}],
                PLANNING_PROFILE_KEYS["onboarding_modeling_state"]: [
                    {"type": "system", "id": "exam_sprint_setup_complete.v1"}
                ],
            },
            source_type="system",
            source="exam_sprint_intake",
        )

    async def _generate_plan_and_tasks(
        self,
        *,
        user_id: UUID,
        request: ExamSprintIntakeRequest,
        session: PlanningSession,
        runtime_state,
        strategy: dict[str, Any],
        goal_model: ExamSprintGoalModel,
        assessment: ExamSprintAssessment,
        selected_pack: ExamSprintPackSelection,
    ) -> GeneratedPlanBundle:
        daily_hours = self._safe_int(session.collected.get("daily_available_hours")) or 1
        subject = self._strip(
            session.collected.get("subject") or session.collected.get("exam_scope") or request.subject
        )
        sprint_policy = self._as_dict(strategy.get("sprint_policy"))
        last_24h_mode = bool(sprint_policy.get("last_24h_mode"))
        last_24h_error_clusters = (
            await self.planning_manager._load_last_24h_error_clusters(
                db=self.db,
                user_id=user_id,
                subject=subject,
            )
            if last_24h_mode
            else []
        )
        plan = await PlanService.create(
            db=self.db,
            obj_in=PlanCreate(
                name=f"{goal_model.days_left}天{subject}冲刺",
                type=PlanType.SPRINT,
                description=json.dumps(
                    {
                        "strategy": strategy,
                        "bottlenecks": session.bottlenecks or [],
                        "initial_assessment": assessment.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                ),
                subject=subject[:100],
                target_date=request.exam_date,
                daily_available_minutes=request.daily_study_minutes,
                total_estimated_hours=float(goal_model.days_left * max(daily_hours, 1)),
                priority=PlanPriority.HIGH,
                plan_stage=PlanStage.SPRINT,
            ),
            user_id=user_id,
            redis_client=self.redis,
        )

        created_tasks: list[Task] = []
        phases = list(strategy.get("phases") or [])
        first_day_focus = ""
        first_day_output = ""

        for index, phase in enumerate(phases, start=1):
            for day_spec in self.planning_manager._daily_task_specs(
                phase,
                phase_index=index,
                session=session,
                error_clusters=last_24h_error_clusters,
            ):
                guide_json = self.planning_manager._build_task_guide_json(
                    session=session,
                    phase=phase,
                    phase_index=index,
                    default_daily_hours=daily_hours,
                    day_number=day_spec["day"],
                    day_focus=day_spec["focus"],
                    day_spec=day_spec,
                    aurora_state=runtime_state,
                )
                task = await TaskService.create(
                    db=self.db,
                    obj_in=TaskCreate(
                        title=(
                            f"Day {day_spec['day']} · {self._strip(phase.get('label'))}"
                            f" - {self._strip(day_spec.get('title_focus') or day_spec.get('task_kind') or '检索推进')}"
                        ),
                        type=coerce_task_type(_task_type_for_day_spec(day_spec)),
                        plan_id=plan.id,
                        estimated_minutes=max(
                            self._safe_int(day_spec.get("estimated_minutes"))
                            or (self._safe_int(phase.get("daily_hours")) or daily_hours) * 60,
                            30,
                        ),
                        difficulty=self.planning_manager._mastery_to_difficulty(
                            session.collected.get("avg_mastery_score"),
                            index,
                        ),
                        energy_cost=self.planning_manager._mastery_to_difficulty(
                            session.collected.get("avg_mastery_score"),
                            index,
                        ),
                        guide_content=self._strip(guide_json.get("objective") or day_spec["focus"]),
                        guide_json=guide_json,
                        ai_prompt=self.planning_manager._build_task_ai_prompt(
                            session=session,
                            phase={**phase, "focus": day_spec["focus"]},
                            guide_json=guide_json,
                            aurora_state=runtime_state,
                        ),
                        source_planning_session_id=session.planning_session_id,
                        phase_index=index,
                        success_criteria=self._strip(guide_json.get("success_criteria") or phase.get("output")),
                        tags=[
                            "规划生成",
                            subject,
                            f"phase:{index}",
                            f"day:{day_spec['day']}",
                            self._strip(sprint_policy.get("sprint_mode") or "exam_sprint"),
                            self._strip(day_spec.get("task_kind") or "retrieval"),
                        ],
                    ),
                    user_id=user_id,
                )
                task.order_index = int(day_spec["day"]) * 1000 + (
                    self._safe_int(day_spec.get("order_index_offset")) or 0
                )
                created_tasks.append(task)
                if int(day_spec["day"]) == 1 and not first_day_focus:
                    first_day_focus = self._strip(day_spec.get("focus") or task.guide_content)
                    first_day_output = self._strip(guide_json.get("output_action"))

        first_day_tasks = [task for task in created_tasks if int(task.order_index or 0) // 1000 == 1]
        first_day_task_ids = [str(task.id) for task in first_day_tasks]
        recommended_task_id = first_day_task_ids[0] if first_day_task_ids else None
        if last_24h_mode:
            recommendation = "今天不再学新内容：先过高频知识点，再按错因回看错题，最后完成 30 分钟短模拟。"
        else:
            recommendation = self.planning_manager._first_day_recommendation_fallback(
                subject=subject,
                task_count=len(first_day_tasks) or 1,
            )
        plan.source_metadata = {
            **self._as_dict(plan.source_metadata),
            "day_highlights": {
                "day": 1,
                "recommendation": recommendation,
            },
            "exam_sprint_intake": {
                "selected_pack": selected_pack.model_dump(mode="json"),
                "goal_model": goal_model.model_dump(mode="json"),
                "study_time_minutes": request.daily_study_minutes,
                "weak_chapters": list(request.baseline.weak_chapters),
            },
            "post_exam_review": {
                "eligible_after": request.exam_date.isoformat(),
                "invited_at": None,
                "notification_id": None,
                "completed_at": None,
                "review_id": None,
            },
        }
        if last_24h_mode:
            plan.source_metadata.update(
                {
                    "last_24h_mode": True,
                    "last_24h_strategy": self._as_dict(sprint_policy.get("last_24h_strategy")),
                    "last_24h_error_clusters": last_24h_error_clusters,
                }
            )
        await self.db.commit()

        return GeneratedPlanBundle(
            plan_id=str(plan.id),
            plan_name=plan.name,
            first_day_task_ids=first_day_task_ids,
            recommended_task_id=recommended_task_id,
            first_day_focus=first_day_focus or "先把考试范围和高频保底线稳住。",
            first_day_output=first_day_output or "完成一次闭卷输出和最小检查。",
        )

    def _build_user_model(
        self,
        *,
        request: ExamSprintIntakeRequest,
        planning_session_id: str,
        conversation_id: str,
    ) -> ExamSprintUserModel:
        return ExamSprintUserModel(
            subject=self._strip(request.subject),
            exam_scope=self._scope_summary(request),
            knowledge_baseline=self._baseline_label(request.baseline.current_level),
            current_level=request.baseline.current_level,
            weak_chapters=self._clean_str_list(request.baseline.weak_chapters),
            daily_study_minutes=request.daily_study_minutes,
            available_materials=self._available_materials(request),
            scope_file_ids=list(request.scope_context.file_ids),
            scope_file_names=list(request.scope_context.file_names),
            planning_session_id=planning_session_id,
            conversation_id=conversation_id,
        )

    def _build_goal_model(self, *, request: ExamSprintIntakeRequest, days_left: int) -> ExamSprintGoalModel:
        score_now = max(0, min(100, int(request.baseline.current_level)))
        recommended_mode = self._recommended_mode(
            current_level=score_now,
            daily_study_minutes=request.daily_study_minutes,
            days_left=days_left,
        )
        return ExamSprintGoalModel(
            exam_date=request.exam_date,
            days_left=days_left,
            target_mode=request.target_mode,
            estimated_score_now=score_now,
            target_score_hint=self._target_score_hint(request.target_mode),
            recommended_mode=recommended_mode,
        )

    def _build_initial_assessment(
        self,
        *,
        request: ExamSprintIntakeRequest,
        goal_model: ExamSprintGoalModel,
        days_left: int,
    ) -> ExamSprintAssessment:
        probability = self._pass_probability(
            current_level=goal_model.estimated_score_now,
            days_left=days_left,
            daily_study_minutes=request.daily_study_minutes,
            has_scope=bool(self._strip(request.scope_context.text) or request.scope_context.file_ids),
            weak_chapter_count=len(self._clean_str_list(request.baseline.weak_chapters)),
            target_mode=request.target_mode,
        )
        recommended_label = self._mode_label(goal_model.recommended_mode)
        summary = (
            f"基于你的基础、时间和范围清晰度，{days_left} 天内通过概率约 {round(probability * 100)}%。"
            f"建议先用「{recommended_label}」模式，今天先把第一天任务跑起来。"
        )
        return ExamSprintAssessment(
            pass_probability=probability,
            recommended_mode=goal_model.recommended_mode,
            recommended_mode_label=recommended_label,
            summary=summary,
        )

    def _build_collected(
        self,
        *,
        request: ExamSprintIntakeRequest,
        user_model: ExamSprintUserModel,
        goal_model: ExamSprintGoalModel,
        selected_pack: ExamSprintPackSelection,
        assessment: ExamSprintAssessment,
    ) -> dict[str, Any]:
        materials = user_model.available_materials
        goal_raw = self._goal_raw(
            subject=user_model.subject,
            days_left=goal_model.days_left,
            target_mode=goal_model.target_mode,
        )
        return {
            "goal_raw": goal_raw,
            "primary_goal_description": goal_raw,
            "goal_type": "exam",
            "subject": user_model.subject,
            "exam_scope": user_model.exam_scope,
            "knowledge_baseline": user_model.knowledge_baseline,
            "time_available": f"每天约 {request.daily_study_minutes} 分钟",
            "daily_available_hours": self._daily_hours(request.daily_study_minutes),
            "study_time_minutes": request.daily_study_minutes,
            "time_constraint_days": goal_model.days_left,
            "exam_date": request.exam_date.isoformat(),
            "available_materials": materials,
            "scope_file_ids": list(request.scope_context.file_ids),
            "scope_file_names": list(request.scope_context.file_names),
            "weak_chapters": list(user_model.weak_chapters),
            "avg_mastery_score": goal_model.estimated_score_now,
            "target_mode": goal_model.target_mode,
            "recommended_mode": goal_model.recommended_mode,
            "estimated_score_now": goal_model.estimated_score_now,
            "selected_pack": selected_pack.model_dump(mode="json"),
            "initial_assessment": assessment.model_dump(mode="json"),
        }

    def _build_rule_bottlenecks(self, session: PlanningSession) -> list[dict[str, Any]]:
        weak_nodes = [
            {
                "name": chapter,
                "mastery_score": max(5, int(session.collected.get("avg_mastery_score") or 0) - 15 - index * 8),
            }
            for index, chapter in enumerate(self._clean_str_list(session.collected.get("weak_chapters")))
        ]
        analysis = bottleneck_analyzer._rule_fallback(
            subject=self._strip(session.collected.get("subject")) or "这门课",
            knowledge_baseline=self._strip(session.collected.get("knowledge_baseline")) or "基础不稳",
            time_constraint_days=self._safe_int(session.collected.get("time_constraint_days")) or 7,
            daily_available_hours=float(self._safe_int(session.collected.get("daily_available_hours")) or 1),
            galaxy_weak_nodes=weak_nodes,
            available_materials=self._clean_str_list(session.collected.get("available_materials")),
            blocked_days=self._clean_str_list(session.collected.get("blocked_days")),
            open_tensions=[],
        )
        return [
            {
                "id": item.id,
                "description": item.description,
                "severity": item.severity,
                "specific_risk": item.specific_risk,
                "affected_concepts": item.affected_concepts,
                "recommendation": item.recommendation,
            }
            for item in analysis.bottlenecks
        ]

    def _select_pack(self, *, days_left: int) -> ExamSprintPackSelection:
        if 8 <= days_left <= 14:
            try:
                manifest = load_exam_prep_14d_manifest()
                return ExamSprintPackSelection(
                    pack_id=manifest.id,
                    pack_name=manifest.name,
                    selection_type="scenario_pack",
                    reason=f"距离考试还有 {days_left} 天，命中内置 14 天考试冲刺骨架。",
                )
            except Exception as exc:  # pragma: no cover - fallback path
                logger.warning("Failed to load exam sprint pack, falling back to generic policy: {}", exc)
        if days_left <= 7:
            return ExamSprintPackSelection(
                pack_id="generic_exam_survival",
                pack_name="7-Day Survival Sprint",
                selection_type="generic_policy",
                reason=f"距离考试只有 {days_left} 天，优先启用保底生存策略。",
            )
        return ExamSprintPackSelection(
            pack_id="generic_exam_sprint",
            pack_name="Standard Exam Sprint",
            selection_type="generic_policy",
            reason=f"距离考试还有 {days_left} 天，使用通用考试冲刺策略。",
        )

    def _available_materials(self, request: ExamSprintIntakeRequest) -> list[str]:
        materials: list[str] = []
        text = self._strip(request.scope_context.text)
        if text:
            materials.append("老师重点")
            for token in ("真题", "课件", "教材", "笔记", "题库", "往年题"):
                if token in text and token not in materials:
                    materials.append(token)
        if request.scope_context.file_ids:
            materials.append("上传资料")
        return materials

    def _scope_summary(self, request: ExamSprintIntakeRequest) -> str:
        text = self._strip(request.scope_context.text)
        if text:
            return text
        if request.scope_context.file_ids:
            return f"已上传 {len(request.scope_context.file_ids)} 份范围资料，待系统提炼老师重点。"
        return f"{self._strip(request.subject)} 的具体范围待进一步校准。"

    @staticmethod
    def _baseline_label(current_level: int) -> str:
        if current_level <= 25:
            return "完全没学过"
        if current_level <= 50:
            return "上过课但没复习"
        if current_level <= 75:
            return "已经学过一部分"
        return "基础较稳，主要是提分冲刺"

    def _recommended_mode(self, *, current_level: int, daily_study_minutes: int, days_left: int) -> str:
        if current_level < 55 or (days_left <= 7 and daily_study_minutes < 120):
            return "pass"
        if current_level >= 75 and daily_study_minutes >= 120 and days_left >= 10:
            return "high_score"
        return "hold"

    @staticmethod
    def _target_score_hint(target_mode: str) -> int:
        return {
            "pass": 60,
            "hold": 75,
            "high_score": 85,
        }.get(target_mode, 60)

    def _pass_probability(
        self,
        *,
        current_level: int,
        days_left: int,
        daily_study_minutes: int,
        has_scope: bool,
        weak_chapter_count: int,
        target_mode: str,
    ) -> float:
        readiness = (
            current_level * 0.6
            + min(days_left * 3, 24)
            + min(daily_study_minutes / 12, 18)
            + (8 if has_scope else 0)
            - min(weak_chapter_count * 4, 16)
            - {"pass": 0, "hold": 6, "high_score": 12}.get(target_mode, 0)
        )
        probability = readiness / 100
        return max(0.08, min(round(probability, 2), 0.95))

    @staticmethod
    def _mode_label(mode: str) -> str:
        return {
            "pass": "先过",
            "hold": "保分",
            "high_score": "冲高分",
        }.get(mode, "先过")

    def _goal_raw(self, *, subject: str, days_left: int, target_mode: str) -> str:
        return f"{days_left}天后冲刺 {self._strip(subject)}，目标是{self._mode_label(target_mode)}。"

    @staticmethod
    def _daily_hours(daily_study_minutes: int) -> int:
        return max(1, math.ceil(daily_study_minutes / 60))

    @staticmethod
    def _today() -> date:
        return datetime.now(UTC).date()

    @staticmethod
    def _strip(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    def _clean_str_list(self, value: Any) -> list[str]:
        if isinstance(value, list | tuple | set):
            return [self._strip(item) for item in value if self._strip(item)]
        text = self._strip(value)
        return [text] if text else []

    @staticmethod
    def _as_dict(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}
