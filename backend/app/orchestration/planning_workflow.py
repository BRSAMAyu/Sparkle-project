from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1 import AuroraRuntimePlanningAdapter, AuroraRuntimePlanningState
from app.core.cache import cache_service
from app.models.plan import PlanPriority, PlanStage, PlanType
from app.models.task import Task
from app.orchestration.exam_sprint_policy import ExamSprintPolicyEngine, ExamSprintPolicyInput
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.plan_service import PlanService
from app.services.profile_write_service import ProfileWriteService
from app.services.task_service import TaskService

PLANNING_SESSION_TTL = 2 * 60 * 60
PLANNING_SESSION_PREFIX = "planning:session:"
PLANNING_PROFILE_KEYS = {
    "cold_start_context": "cold_start_context",
    "knowledge_gaps": "knowledge_gaps",
    "onboarding_modeling_state": "onboarding_modeling_state",
}

PLANNING_CONFIRM_PATTERNS = (
    "确认这个方案",
    "确认方案",
    "按这个来",
    "就这样",
    "开始生成",
    "开始规划",
    "可以",
    "好",
)
PLANNING_CANCEL_PATTERNS = (
    "取消规划",
    "先不规划了",
    "不规划了",
    "停一下规划",
)
PLANNING_ENOUGH_PATTERNS = (
    "够了",
    "行了",
    "不用问了",
    "你来规划吧",
    "开始规划",
)
PLANNING_ADJUST_PATTERNS = (
    "调整",
    "修改",
    "改成",
    "轻一点",
    "重一点",
    "真题",
    "节奏",
    "每天",
    "时间",
    "阶段",
)
PLANNING_VERB_PATTERNS = (
    "规划",
    "计划",
    "安排",
    "冲刺",
)
PLANNING_GOAL_PATTERNS = (
    "备考",
    "复习",
    "考试",
    "期末",
    "不挂科",
    "冲刺",
    "学习",
    "学",
)
PLANNING_SUBJECT_PATTERNS = (
    "计算机网络",
    "计网",
    "高数",
    "线代",
    "概率论",
    "操作系统",
    "数据库",
    "英语",
    "四级",
    "六级",
)
PLANNING_TASK_BYPASS_PATTERNS = (
    "创建任务",
    "create task",
    "任务完成",
    "任务完成没有",
    "今天做什么",
    "明天做什么",
    "更新这个计划",
    "更新计划",
    "查一下任务",
    "查一下这个任务",
    "这个任务完成没有",
)
PLANNING_TIMEBOX_RE = re.compile(
    r"(?:(?:[一二两三四五六七八九十\d]+)\s*(?:天|日|周)|(?:day|days|week|weeks))",
    re.IGNORECASE,
)


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


@dataclass
class PlanningSession:
    planning_session_id: str
    chat_session_id: str
    user_id: str
    state: str
    goal_raw: str
    collected: dict[str, Any] = field(default_factory=dict)
    turns_in_state: int = 0
    bottlenecks: list[dict[str, Any]] | None = None
    confirmed_strategy: dict[str, Any] | None = None
    created_at: str = field(default_factory=lambda: _utcnow().isoformat())
    expires_at: str = field(default_factory=lambda: (_utcnow() + timedelta(seconds=PLANNING_SESSION_TTL)).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> PlanningSession:
        return cls(
            planning_session_id=_strip(payload.get("planning_session_id")),
            chat_session_id=_strip(payload.get("chat_session_id")),
            user_id=_strip(payload.get("user_id")),
            state=_strip(payload.get("state")) or "DETECTED",
            goal_raw=_strip(payload.get("goal_raw")),
            collected=_as_dict(payload.get("collected")),
            turns_in_state=int(payload.get("turns_in_state") or 0),
            bottlenecks=list(payload.get("bottlenecks") or []) or None,
            confirmed_strategy=_as_dict(payload.get("confirmed_strategy")) or None,
            created_at=_strip(payload.get("created_at")) or _utcnow().isoformat(),
            expires_at=_strip(payload.get("expires_at"))
            or (_utcnow() + timedelta(seconds=PLANNING_SESSION_TTL)).isoformat(),
        )


class PlanningWorkflowManager:
    REQUIRED_FIELDS = ("exam_scope", "knowledge_baseline", "time_available")

    def __init__(self, redis_client=None, runtime_adapter: AuroraRuntimePlanningAdapter | None = None) -> None:
        self.redis = redis_client or cache_service.redis
        self.runtime_adapter = runtime_adapter or AuroraRuntimePlanningAdapter(redis_client=self.redis)

    def detect_planning_intent(self, message: str, context: dict[str, Any] | None = None) -> bool:
        text = _strip(message).lower()
        if not text:
            return False
        ctx = _as_dict(context)
        if ctx.get("plan_id"):
            return False
        if ctx.get("from_modeling_complete"):
            return True
        route_intent = _strip(ctx.get("route_intent") or ctx.get("intent")).lower()
        if route_intent in {"create_task", "update_task", "get_task_detail", "plan_update"}:
            return False
        if any(token in text for token in PLANNING_TASK_BYPASS_PATTERNS):
            return False

        has_timebox = bool(PLANNING_TIMEBOX_RE.search(text))
        has_planning_verb = any(token in text for token in PLANNING_VERB_PATTERNS)
        has_goal = any(token in text for token in PLANNING_GOAL_PATTERNS)
        has_subject = any(token in text for token in PLANNING_SUBJECT_PATTERNS)
        has_goal_commitment = any(token in text for token in ("想在", "希望在", "准备", "冲到", "冲刺"))
        asks_for_help = "帮我" in text or "给我" in text
        mentions_existing_plan = any(
            token in text for token in ("更新这个计划", "调整这个计划", "已有计划", "这个计划")
        )

        if mentions_existing_plan:
            return False

        return has_timebox and (
            has_planning_verb or has_goal_commitment or (asks_for_help and (has_goal or has_subject))
        )

    async def get_active_session(self, chat_session_id: str) -> PlanningSession | None:
        if not self.redis or not chat_session_id:
            return None
        raw = await self.redis.get(f"{PLANNING_SESSION_PREFIX}{chat_session_id}")
        if not raw:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            payload = json.loads(raw)
        except Exception:
            logger.warning("Invalid planning session payload for {}", chat_session_id)
            return None
        session = PlanningSession.from_dict(_as_dict(payload))
        if session.state.upper() in {"DONE", "ABANDONED"}:
            return None
        return session

    async def save_session(self, session: PlanningSession) -> None:
        if not self.redis:
            return
        await self.redis.setex(
            f"{PLANNING_SESSION_PREFIX}{session.chat_session_id}",
            PLANNING_SESSION_TTL,
            json.dumps(session.to_dict(), ensure_ascii=False),
        )

    async def create_session(self, *, chat_session_id: str, user_id: str, goal_raw: str) -> PlanningSession:
        session = PlanningSession(
            planning_session_id=str(uuid.uuid4()),
            chat_session_id=chat_session_id,
            user_id=user_id,
            state="CLARIFYING",
            goal_raw=goal_raw,
        )
        await self.save_session(session)
        return session

    async def abandon_session(self, session: PlanningSession) -> None:
        session.state = "ABANDONED"
        await self.save_session(session)

    @staticmethod
    def build_plan_from_modeling_output(modeling_output: dict[str, Any]) -> dict[str, Any]:
        """Convert Aurora modeling activity_profile / cold_start_context into planning input.

        Allows the orchestrator to auto-bridge from modeling_complete=True to the
        planning workflow without requiring the user to re-state their goal.
        """
        profile = _as_dict(modeling_output.get("activity_profile"))
        user_model = _as_dict(modeling_output.get("user_model_snapshot"))
        cold_start = _as_dict(
            modeling_output.get("cold_start_context")
            or modeling_output.get("cold_start")
            or (user_model.get("preferences") or {}).get("cold_start_context")
        )

        goal_raw = (
            _strip(cold_start.get("goal_raw") or cold_start.get("goal_summary") or cold_start.get("goal"))
            or _strip(user_model.get("goal_raw") or user_model.get("goal_summary"))
            or "完成学习目标"
        )
        return {
            "from_modeling_complete": True,
            "goal_raw": goal_raw,
            "collected": {
                "exam_scope": _strip(
                    cold_start.get("exam_scope")
                    or cold_start.get("scope")
                    or user_model.get("exam_scope")
                    or user_model.get("subject")
                ),
                "knowledge_baseline": _strip(
                    cold_start.get("knowledge_baseline")
                    or cold_start.get("baseline")
                    or user_model.get("knowledge_baseline")
                ),
                "time_available": _strip(
                    cold_start.get("time_available")
                    or cold_start.get("time")
                    or user_model.get("time_available")
                ),
                "daily_available_hours": cold_start.get("daily_available_hours")
                or user_model.get("daily_available_hours"),
                "time_constraint_days": cold_start.get("time_constraint_days")
                or user_model.get("time_constraint_days")
                or user_model.get("days_remaining"),
                "subject": _strip(
                    cold_start.get("subject") or user_model.get("subject") or cold_start.get("exam_scope")
                ),
                "motivation": _strip(
                    cold_start.get("motivation") or user_model.get("motivation") or user_model.get("goal_motivation")
                ),
            },
            "activity_profile": profile,
            "galaxy_baseline": modeling_output.get("galaxy_baseline"),
        }

    async def process_planning_turn(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        chat_session_id: str,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        profile_context = _as_dict(context.get("profile_context"))
        session = await self.get_active_session(chat_session_id)
        if session is None:
            if not self.detect_planning_intent(message, context):
                return None
            modeling_output = _as_dict(context.get("modeling_output"))
            if context.get("from_modeling_complete") and modeling_output:
                bridge = self.build_plan_from_modeling_output(modeling_output)
                goal_raw = _strip(bridge.get("goal_raw")) or message
            else:
                bridge = {}
                goal_raw = message
            session = await self.create_session(
                chat_session_id=chat_session_id,
                user_id=str(user_id),
                goal_raw=goal_raw,
            )
            prefill_context = dict(context)
            if bridge.get("galaxy_baseline"):
                prefill_context["galaxy_baseline"] = bridge["galaxy_baseline"]
            session.collected.update(await self._prefill_from_profile_context(prefill_context))
            if bridge.get("collected"):
                for key, value in _as_dict(bridge["collected"]).items():
                    if value and not session.collected.get(key):
                        session.collected[key] = value

        runtime_state = await self.runtime_adapter.get_or_create_state(
            user_id=str(user_id),
            conversation_id=chat_session_id,
            db=db,
            planning_session_id=session.planning_session_id,
            goal_raw=session.goal_raw or message,
            profile_context=profile_context,
            collected=session.collected,
        )

        context_session_id = _strip(context.get("planning_session_id"))
        if context_session_id and context_session_id != session.planning_session_id:
            return {"bypass_planning": True}

        lowered = _strip(message).lower()
        if any(token in lowered for token in PLANNING_CANCEL_PATTERNS):
            await self.abandon_session(session)
            return {
                "message": "好的，先退出这轮规划。我会保留已经了解的信息，之后你想继续时我们可以直接接上。",
                "widgets": [],
                "metadata": self.runtime_adapter.build_response_metadata(runtime_state, surface_complete=False),
            }

        extracted_fields = self._extract_clarifying_fields(message)
        if not self.is_message_relevant_to_planning(session, message, extracted_fields=extracted_fields):
            await self.runtime_adapter.absorb_user_turn(
                state=runtime_state,
                db=db,
                message=message,
                extracted_fields=extracted_fields,
                is_detour=True,
            )
            return {"bypass_planning": True}

        runtime_state = await self.runtime_adapter.absorb_user_turn(
            state=runtime_state,
            db=db,
            message=message,
            extracted_fields=extracted_fields,
            is_detour=False,
        )

        if session.state == "CLARIFYING":
            return await self._handle_clarifying(
                db=db,
                user_id=user_id,
                session=session,
                user_message=message,
                runtime_state=runtime_state,
                extracted_fields=extracted_fields,
                profile_context=profile_context,
            )
        if session.state == "AWAITING_CONFIRM":
            if any(token in lowered for token in PLANNING_CONFIRM_PATTERNS):
                return await self._handle_generating(
                    db=db,
                    user_id=user_id,
                    session=session,
                    runtime_state=runtime_state,
                    profile_context=profile_context,
                )
            return await self._handle_strategy_revision(
                db=db,
                session=session,
                user_message=message,
                runtime_state=runtime_state,
            )
        if session.state == "STRATEGY_REVISION":
            return await self._handle_strategy_revision(
                db=db,
                session=session,
                user_message=message,
                runtime_state=runtime_state,
            )
        return None

    async def process_onboarding_turn(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: str,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        state = await self._load_onboarding_state(conversation_id)
        profile_seed = await self._prefill_from_profile_context(context)
        collected = _as_dict(state.get("collected"))
        collected.update({key: value for key, value in profile_seed.items() if value and key not in collected})
        turn = int(state.get("turn") or 0)

        if turn == 0:
            reply = "你好！简单问一下，你最近最想搞定的一件事是什么？比如考试、学技能，或者完成某个项目？"
            turn = 1
        else:
            self._update_onboarding_collected(collected, message, turn)
            turn += 1
            if turn == 2:
                reply = self._build_onboarding_question_two(collected)
            elif turn == 3:
                reply = "平时每天大概能花多少时间在这上面？有没有特别忙或者完全没空的几天？"
            else:
                await self._persist_profile_payload(
                    db=db,
                    user_id=user_id,
                    key=PLANNING_PROFILE_KEYS["cold_start_context"],
                    value=self._build_cold_start_context(collected),
                )
                await self._persist_profile_payload(
                    db=db,
                    user_id=user_id,
                    key=PLANNING_PROFILE_KEYS["onboarding_modeling_state"],
                    value={"completed": True, "skipped": False, "conversation_id": conversation_id},
                )
                await self._save_onboarding_state(conversation_id, {})
                return {
                    "message": self._build_onboarding_summary(collected),
                    "widgets": [],
                    "is_complete": True,
                }

        await self._save_onboarding_state(
            conversation_id,
            {"turn": turn, "collected": collected},
        )
        return {"message": reply, "widgets": [], "is_complete": False}

    async def skip_onboarding(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        conversation_id: str,
    ) -> None:
        state = await self._load_onboarding_state(conversation_id)
        collected = _as_dict(state.get("collected"))
        if collected:
            await self._persist_profile_payload(
                db=db,
                user_id=user_id,
                key=PLANNING_PROFILE_KEYS["cold_start_context"],
                value=self._build_cold_start_context(collected),
            )
        await self._persist_profile_payload(
            db=db,
            user_id=user_id,
            key=PLANNING_PROFILE_KEYS["onboarding_modeling_state"],
            value={"completed": False, "skipped": True, "conversation_id": conversation_id},
        )
        await self._save_onboarding_state(conversation_id, {})

    async def _handle_clarifying(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        session: PlanningSession,
        user_message: str,
        runtime_state: AuroraRuntimePlanningState,
        extracted_fields: dict[str, Any],
        profile_context: dict[str, Any],
    ) -> dict[str, Any]:
        session.collected.update(extracted_fields)
        session.collected.setdefault("goal_raw", session.goal_raw)
        session.turns_in_state += 1
        runtime_state = await self.runtime_adapter.sync_session(
            state=runtime_state,
            db=db,
            planning_session_id=session.planning_session_id,
            goal_raw=session.goal_raw,
            collected=session.collected,
            profile_context=profile_context,
        )
        if self._is_ready_for_bottlenecks(session, user_message):
            session.state = "BOTTLENECK"
            session.bottlenecks = self._build_bottlenecks(session, aurora_state=runtime_state)
            strategy = self._build_strategy(session, aurora_state=runtime_state)
            session.confirmed_strategy = strategy
            session.state = "AWAITING_CONFIRM"
            await self._persist_profile_payload(
                db=db,
                user_id=user_id,
                key=PLANNING_PROFILE_KEYS["cold_start_context"],
                value=self._build_cold_start_context(session.collected),
            )
            await self.save_session(session)
            return {
                "message": self._build_strategy_intro(session, runtime_state),
                "widgets": [
                    {"type": "planning_progress_strip", "data": self._progress_data("AWAITING_CONFIRM")},
                    {
                        "type": "planning_bottleneck_card",
                        "data": {"type": "bottleneck_analysis", "bottlenecks": session.bottlenecks or []},
                    },
                    {
                        "type": "planning_strategy_card",
                        "data": {
                            "type": "strategy_proposal",
                            "strategy": strategy,
                            "planning_session_id": session.planning_session_id,
                            "actions": self._strategy_actions(session.planning_session_id),
                        },
                    },
                ],
                "metadata": self.runtime_adapter.build_response_metadata(runtime_state, surface_complete=False),
            }

        prompt = self._next_clarifying_prompt(session, aurora_state=runtime_state)
        _, prompt_domain = self.runtime_adapter.build_next_prompt(runtime_state)
        await self.runtime_adapter.note_question_asked(state=runtime_state, db=db, domain=prompt_domain)
        await self.save_session(session)
        return {
            "message": prompt,
            "widgets": [{"type": "planning_progress_strip", "data": self._progress_data("CLARIFYING")}],
            "metadata": self.runtime_adapter.build_response_metadata(runtime_state, surface_complete=False),
        }

    async def _handle_strategy_revision(
        self,
        *,
        db: AsyncSession,
        session: PlanningSession,
        user_message: str,
        runtime_state: AuroraRuntimePlanningState,
    ) -> dict[str, Any]:
        strategy = _as_dict(session.confirmed_strategy)
        if strategy:
            first_phase = strategy.get("phases", [{}])[0]
            if "真题" in user_message:
                first_phase["method"] = f"{_strip(first_phase.get('method'))} 优先把真题和课件一起使用。".strip()
                materials = list(session.collected.get("available_materials") or [])
                if "真题" not in materials:
                    materials.append("真题")
                session.collected["available_materials"] = materials
            if "轻一点" in user_message or "时间少" in user_message:
                strategy["daily_commitment_range"] = "1–3小时"
                await self.runtime_adapter.update_activity_profile(
                    state=runtime_state,
                    db=db,
                    updates={"task_density_hint": 0.35, "conversation_style": "structured"},
                )
            if "重一点" in user_message or "更猛" in user_message:
                strategy["daily_commitment_range"] = "3–5小时"
                await self.runtime_adapter.update_activity_profile(
                    state=runtime_state,
                    db=db,
                    updates={"task_density_hint": 0.9, "conversation_style": "structured"},
                )
            strategy["adjustment_note"] = user_message.strip()
            strategy["aurora_brief"] = self.runtime_adapter.build_strategy_brief(runtime_state)
        runtime_state = await self.runtime_adapter.sync_session(
            state=runtime_state,
            db=db,
            planning_session_id=session.planning_session_id,
            goal_raw=session.goal_raw,
            collected=session.collected,
            profile_context=None,
        )
        session.confirmed_strategy = strategy
        session.state = "AWAITING_CONFIRM"
        await self.save_session(session)
        return {
            "message": "我按你的反馈把策略收紧了一版，你确认后我就开始生成任务卡。",
            "widgets": [
                {"type": "planning_progress_strip", "data": self._progress_data("AWAITING_CONFIRM")},
                {
                    "type": "planning_strategy_card",
                    "data": {
                        "type": "strategy_proposal",
                        "strategy": strategy,
                        "planning_session_id": session.planning_session_id,
                        "actions": self._strategy_actions(
                            session.planning_session_id,
                            adjust_label="继续调整",
                            adjust_prompt="我还想再调整：",
                        ),
                    },
                },
            ],
            "metadata": self.runtime_adapter.build_response_metadata(runtime_state, surface_complete=False),
        }

    async def _handle_generating(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        session: PlanningSession,
        runtime_state: AuroraRuntimePlanningState,
        profile_context: dict[str, Any],
    ) -> dict[str, Any]:
        runtime_state = await self.runtime_adapter.sync_session(
            state=runtime_state,
            db=db,
            planning_session_id=session.planning_session_id,
            goal_raw=session.goal_raw,
            collected=session.collected,
            profile_context=profile_context,
        )
        strategy = _as_dict(session.confirmed_strategy)
        if not strategy:
            strategy = self._build_strategy(session, aurora_state=runtime_state)
            session.confirmed_strategy = strategy

        days = _safe_int(strategy.get("total_days")) or _safe_int(session.collected.get("time_constraint_days")) or 7
        daily_hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "考试科目")
        plan = await PlanService.create(
            db=db,
            obj_in=PlanCreate(
                name=f"{days}天{subject}冲刺",
                type=PlanType.SPRINT,
                description=json.dumps(
                    {"strategy": strategy, "bottlenecks": session.bottlenecks or []}, ensure_ascii=False
                ),
                subject=subject[:100],
                target_date=(_utcnow() + timedelta(days=days)).date(),
                daily_available_minutes=max(daily_hours * 60, 30),
                total_estimated_hours=float(days * daily_hours),
                priority=PlanPriority.HIGH,
                plan_stage=PlanStage.SPRINT,
            ),
            user_id=user_id,
            redis_client=cache_service.redis,
        )

        created_tasks: list[Task] = []
        phases = list(strategy.get("phases") or [])
        for index, phase in enumerate(phases, start=1):
            for day_spec in self._daily_task_specs(phase, phase_index=index):
                guide_json = self._build_task_guide_json(
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
                    db=db,
                    obj_in=TaskCreate(
                        title=(
                            f"Day {day_spec['day']} · {_strip(phase.get('label'))}"
                            f" - {_strip(day_spec.get('title_focus') or day_spec.get('task_kind') or '检索推进')}"
                        ),
                        type=coerce_task_type("learning"),
                        plan_id=plan.id,
                        estimated_minutes=max(
                            _safe_int(day_spec.get("estimated_minutes"))
                            or (_safe_int(phase.get("daily_hours")) or daily_hours) * 60,
                            30,
                        ),
                        difficulty=self._mastery_to_difficulty(
                            session.collected.get("avg_mastery_score"), index
                        ),
                        energy_cost=self._mastery_to_difficulty(
                            session.collected.get("avg_mastery_score"), index
                        ),
                        guide_content=_strip(guide_json.get("objective") or day_spec["focus"]),
                        guide_json=guide_json,
                        ai_prompt=self._build_task_ai_prompt(
                            session=session,
                            phase={**phase, "focus": day_spec["focus"]},
                            guide_json=guide_json,
                            aurora_state=runtime_state,
                        ),
                        source_planning_session_id=session.planning_session_id,
                        phase_index=index,
                        success_criteria=_strip(guide_json.get("success_criteria") or phase.get("output")),
                        tags=[
                            "规划生成",
                            subject,
                            f"phase:{index}",
                            f"day:{day_spec['day']}",
                            _strip(strategy.get("sprint_policy", {}).get("sprint_mode") or "exam_sprint"),
                            _strip(day_spec.get("task_kind") or "retrieval"),
                        ],
                    ),
                    user_id=user_id,
                )
                task.order_index = int(day_spec["day"]) * 1000
                created_tasks.append(task)
        if created_tasks:
            await db.commit()

        session.state = "DONE"
        await self.save_session(session)
        runtime_state.current_intent = {"intent_type": "wait", "target_tension_id": None, "payload": {}}
        await self.runtime_adapter.save_state(runtime_state, db=db)
        return {
            "message": "方案已经确认，我把第一阶段任务卡生成好了。你现在可以直接进入第一个任务开始执行。",
            "widgets": [
                {"type": "planning_progress_strip", "data": self._progress_data("DONE")},
                {
                    "type": "plan_card",
                    "data": {
                        "id": str(plan.id),
                        "name": plan.name,
                        "description": "按确认后的 7 天策略生成",
                        "subject": plan.subject,
                        "plan_id": str(plan.id),
                    },
                },
                {
                    "type": "task_list",
                    "data": {
                        "title": "已生成的阶段任务",
                        "tasks": [
                            {
                                "id": str(task.id),
                                "title": task.title,
                                "description": task.guide_content,
                                "guide_content": task.guide_content,
                                "estimated_minutes": task.estimated_minutes,
                                "status": task.status.value,
                                "type": task.type.value,
                                "plan_id": str(plan.id),
                            }
                            for task in created_tasks
                        ],
                    },
                },
            ],
            "metadata": self.runtime_adapter.build_response_metadata(runtime_state, surface_complete=True),
        }

    @staticmethod
    def _mastery_to_difficulty(mastery_score: float | None, phase_index: int) -> int:
        """Map per-node mastery (0-100) to task difficulty (1-5).

        Falls back to the old phase-based formula when mastery is unavailable.
        """
        if mastery_score is None:
            return min(5, 2 + phase_index)
        if mastery_score < 20:
            return 5
        if mastery_score < 40:
            return 4
        if mastery_score < 60:
            return 3
        if mastery_score < 80:
            return 2
        return 1

    @staticmethod
    def _classify_baseline_from_galaxy(avg_mastery: float | None) -> str:
        if avg_mastery is None:
            return ""
        if avg_mastery < 20:
            return "完全没学过"
        if avg_mastery < 50:
            return "上过课但没复习"
        return "已经学过一部分"

    def _is_ready_for_bottlenecks(self, session: PlanningSession, user_message: str) -> bool:
        if all(_strip(session.collected.get(field)) for field in self.REQUIRED_FIELDS):
            return True
        lowered = _strip(user_message).lower()
        if any(token in lowered for token in PLANNING_ENOUGH_PATTERNS):
            return True
        return session.turns_in_state >= 4

    def is_message_relevant_to_planning(
        self,
        session: PlanningSession,
        message: str,
        *,
        extracted_fields: dict[str, Any] | None = None,
    ) -> bool:
        text = _strip(message).lower()
        if not text:
            return False
        if any(
            token in text for token in PLANNING_CANCEL_PATTERNS + PLANNING_ENOUGH_PATTERNS + PLANNING_CONFIRM_PATTERNS
        ):
            return True
        if session.state == "CLARIFYING":
            if any(token in text for token in PLANNING_TASK_BYPASS_PATTERNS):
                return False
            collected = dict(extracted_fields or self._extract_clarifying_fields(message))
            return any(_strip(collected.get(field)) for field in self.REQUIRED_FIELDS)
        if session.state in {"AWAITING_CONFIRM", "STRATEGY_REVISION"}:
            return any(token in text for token in PLANNING_ADJUST_PATTERNS)
        return True

    def _next_clarifying_prompt(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> str:
        if aurora_state is not None:
            prompt, _ = self.runtime_adapter.build_next_prompt(aurora_state)
            if prompt:
                return prompt
        missing = [field for field in self.REQUIRED_FIELDS if not _strip(session.collected.get(field))]
        if "exam_scope" in missing and "knowledge_baseline" in missing:
            return "先帮我补两块最关键的信息：这次考试具体考哪些范围？你现在对这门课大概是完全没学过、上过课但没复习，还是已经学过一部分？"
        if "exam_scope" in missing:
            return "这次考试具体考哪些范围？如果你知道教材、章节或者老师给的考纲，直接告诉我就行。"
        if "knowledge_baseline" in missing:
            return "你现在对这门课的基础大概在哪个位置？比如完全没学过、上过课但没复习，或者已经学过一半。"
        return "你接下来这几天每天大概能拿出多少时间？有没有哪几天会特别忙或者完全学不了？"

    def _extract_clarifying_fields(self, user_message: str) -> dict[str, Any]:
        collected: dict[str, Any] = {}
        text = _strip(user_message)
        if not text:
            return collected
        lowered = text.lower()
        if not collected.get("exam_scope") and any(
            token in lowered
            for token in ("章", "教材", "课件", "考纲", "网络", "计网", "tcp", "udp", "传输层", "网络层")
        ):
            collected["exam_scope"] = text
        if not collected.get("knowledge_baseline"):
            if any(token in lowered for token in ("没学过", "零基础", "完全不会")):
                collected["knowledge_baseline"] = "完全没学过"
            elif any(token in lowered for token in ("上过课", "没复习", "忘了")):
                collected["knowledge_baseline"] = "上过课但没复习"
            elif any(token in lowered for token in ("学了一半", "有基础", "学过一些")):
                collected["knowledge_baseline"] = "已经学过一部分"
        if not collected.get("time_available"):
            time_match = re.search(r"(?P<hours>\d+(?:\.\d+)?)\s*(小时|h|hour)", lowered)
            minute_match = re.search(r"(?P<minutes>\d+)\s*分钟", lowered)
            if time_match:
                hours = int(float(time_match.group("hours")))
                collected["time_available"] = f"每天约 {hours} 小时"
                collected["daily_available_hours"] = hours
            elif minute_match:
                minutes = int(minute_match.group("minutes"))
                collected["time_available"] = f"每天约 {minutes} 分钟"
                collected["daily_available_hours"] = max(1, round(minutes / 60))
        if "没空" in lowered or "有课" in lowered:
            collected["blocked_days"] = text
        materials = list(collected.get("available_materials") or [])
        for token in ("真题", "课件", "教材", "笔记", "题库", "往年题"):
            if token in text and token not in materials:
                materials.append(token)
        if materials:
            collected["available_materials"] = materials

        day_match = re.search(r"(?P<days>\d+)\s*(天|day|days)", lowered)
        if day_match and not collected.get("time_constraint_days"):
            collected["time_constraint_days"] = int(day_match.group("days"))
        if not collected.get("subject"):
            subject_match = re.search(r"(计算机网络|计网|高数|线代|概率论|操作系统|数据库|英语)", text)
            if subject_match:
                collected["subject"] = subject_match.group(1)
        return collected

    def _merge_clarifying_fields(self, collected: dict[str, Any], user_message: str) -> None:
        collected.update(self._extract_clarifying_fields(user_message))

    def _strategy_actions(
        self,
        planning_session_id: str,
        *,
        adjust_label: str = "我想调整",
        adjust_prompt: str = "我想调整这个方案：",
    ) -> list[dict[str, Any]]:
        return [
            {
                "type": "prompt",
                "label": "确认这个方案",
                "payload": {
                    "prompt": "确认这个方案",
                    "planning_session_id": planning_session_id,
                },
            },
            {
                "type": "prompt",
                "label": adjust_label,
                "payload": {
                    "prompt": adjust_prompt,
                    "planning_session_id": planning_session_id,
                },
            },
        ]

    def _build_strategy_intro(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> str:
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "这次备考")
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        recent_detours = [item for item in list(brief.get("recent_detours") or []) if _strip(item)]
        if recent_detours:
            return f"我先把这次 {days} 天 {subject} 里最影响结果的瓶颈和推进策略整理出来，也把你刚才补充过的碎信息一起吃进去，你看看是否贴合你的实际情况。"
        return f"我先把这次 {days} 天 {subject} 里最影响结果的瓶颈和推进策略整理出来，你看看是否符合你的实际情况。"

    def _build_daily_task_contract(
        self,
        *,
        task_kind: str,
        sprint_mode: str,
        phase_label: str,
        focus: str,
        output: str,
        minimum_output: str,
        day_number: int | None,
    ) -> dict[str, Any]:
        day_prefix = f"Day {day_number}" if day_number else "今天"
        objective = f"{day_prefix}：{output or focus or phase_label}".strip()
        fallback = {
            "objective": objective,
            "output_action": f"完成一次明确输出：{minimum_output}",
            "success_criteria": f"完成 {minimum_output}，并能据此判断今天有没有推进。",
            "micro_contract": "如果开始这个任务，就先做闭卷提取，再决定要不要翻资料。",
            "fail_safe_rule": "如果状态差，就只保留一个最小输出动作，不继续加新内容。",
            "success_checklist": ["有一个明确输出", "能判断今天哪里会、哪里不会"],
            "method_steps": [
                "先闭卷提取，不要从阅读开始。",
                "只围绕今天的一个产出动作推进。",
                "最后用最小检查确认不是只是看懂了。",
            ],
        }

        if task_kind == "diagnostic_triage":
            return {
                "objective": f"{day_prefix}：产出一张保底 / 补强 / defer_or_skip 三栏清单。",
                "output_action": "先做 5 题探针或 8 分钟闭卷回忆，再整理一张「保底 / 补强 / defer_or_skip」三栏清单。",
                "success_criteria": "三栏清单里至少有 3 个保底项、2 个补强项、1 个 defer_or_skip 项，并明确今天只攻 1 个保底主线。",
                "micro_contract": "如果开始，就先做 5 题探针或 8 分钟闭卷回忆；没做完这一步，不允许直接翻资料。",
                "fail_safe_rule": "如果只剩 20 分钟，就保留探针结果和三栏清单，不再扩新内容。",
                "success_checklist": ["有三栏清单", "明确 1 个今天必保主线", "至少做过一次探针检查"],
                "method_steps": [
                    "先闭卷写出你认为最可能考的 5 个关键词，或者做 5 题探针，不查资料。",
                    "再只翻范围材料，把内容分到「保底 / 补强 / defer_or_skip」三栏。",
                    "从「保底」里挑今天必须拿下的 1 个模块，作为接下来 24 小时主线。",
                    f"最后用 {minimum_output} 再验一次，确认这个主线真的能提取。",
                ],
            }

        if task_kind == "retrieval_triage":
            return {
                "objective": f"{day_prefix}：闭卷写一页高频概念卡，并标出 2 个最危险漏洞。",
                "output_action": "闭卷写 1 页高频概念卡，再把 2 个不会的点转成补强条目。",
                "success_criteria": "至少闭卷写出 4 个高频概念的关键词或判断点，并形成 2 个具体补强条目。",
                "micro_contract": "如果开始，就先闭卷 6 分钟写概念卡；只补 2 个最危险漏洞，不切去新章节。",
                "fail_safe_rule": "如果卡住，不追全章覆盖，只补当前最危险的 1 个漏洞。",
                "success_checklist": ["有 1 页概念卡", "标出 2 个漏洞", "今天没有切到新章节"],
                "method_steps": [
                    "先闭卷写出高频概念、判断条件和容易混淆的点。",
                    "翻资料只补你刚才写不出的部分，不顺手扩展到新章节。",
                    "把最危险的 2 个漏洞改写成明天可继续追的补强条目。",
                    f"最后用 {minimum_output} 检查概念卡是不是能转成可提取内容。",
                ],
            }

        if task_kind == "retrieval_drill":
            return {
                "objective": f"{day_prefix}：独立完成 3 道代表题，并写出每道题的判断依据或错因。",
                "output_action": "不看答案先做 3 道代表题，并写下每道题的判断依据或错因。",
                "success_criteria": "至少完成 3 道代表题，其中至少 2 道能独立判断；错题需写出错因并重做 1 道同型题。",
                "micro_contract": "如果开始，就先不看答案做前 2 题；卡住超过 3 分钟才允许翻资料。",
                "fail_safe_rule": "如果状态差，就只保留 2 道代表题 + 1 条错因，不额外加新难题。",
                "success_checklist": ["完成至少 3 道代表题", "错题有错因", "至少重做 1 道同型题"],
                "method_steps": [
                    "先独立做题，不要先读解析。",
                    "每做完一题就写一句判断依据或为什么会错。",
                    "只追最影响分数的错误类型，直到同型题能做对。",
                    f"最后用 {minimum_output} 回看你是不是已经能独立提取关键判断点。",
                ],
            }

        if task_kind == "retrieval_repair":
            return {
                "objective": f"{day_prefix}：只补 1 类高频错误，并用 1 道同型题回测。",
                "output_action": "挑 1 类最高收益错误，补完后立刻用 1 道同型题回测。",
                "success_criteria": "能说出这类错误的触发点，并在 1 道同型题上完成纠正。",
                "micro_contract": "如果开始，就只选 1 类错误，不同时补多个洞。",
                "fail_safe_rule": "今天不追所有错题，只修最影响分数的 1 类。",
                "success_checklist": ["只处理 1 类错误", "有 1 道同型回测", "能说出触发点"],
                "method_steps": [
                    "先看最近一轮错题，选最影响得分的 1 类错误。",
                    "把这类错误改写成一句提醒语和一个判断步骤。",
                    "立刻做 1 道同型题回测，不让补强停留在看懂。",
                ],
            }

        if task_kind == "mock_review":
            return {
                "objective": f"{day_prefix}：完成一次限时自测，并写出最后 24 小时清单。",
                "output_action": "限时完成 15–20 题或半套题，并整理「最后 24 小时保留 / 补强 / 放弃」清单。",
                "success_criteria": "拿到一次限时结果，归纳 Top 3 失分类型，并形成最后 24 小时清单。",
                "micro_contract": "如果开始，就先开表计时并一次做完；做完前不来回翻资料。",
                "fail_safe_rule": "如果时间不够，就做 15 分钟压缩版自测，但也必须留下 Top 3 错误类型。",
                "success_checklist": ["有一次限时结果", "有 Top 3 失分类型", "有最后 24 小时清单"],
                "method_steps": [
                    "先按考试节奏限时完成一轮，不中途查答案。",
                    "做完后把错误分成概念混淆、题型不会、记忆断点三类。",
                    "只把最后时间留给最高收益的错误类型，明确哪些内容先放弃。",
                ],
            }

        if task_kind == "diagnostic_map":
            return {
                "objective": f"{day_prefix}：画一张知识地图，并用 5 题探针校准掌握度。",
                "output_action": "画一张知识地图，再完成 5 题探针题记录结果。",
                "success_criteria": "知识地图至少包含 3 条主线、2 个薄弱点，并留下 5 题探针结果。",
                "micro_contract": "如果开始，就先画主线再补细节；探针题只用来校准，不追难题。",
                "fail_safe_rule": "如果时间不够，至少保留知识地图主线和 3 题探针结果。",
                "success_checklist": ["有知识地图", "有 5 题或至少 3 题探针结果", "标出 2 个薄弱点"],
                "method_steps": [
                    "先不看细节，闭卷画出这门课的 3 条主线。",
                    "翻资料只修正主线和关键连接点，不展开到所有细枝末节。",
                    "做 5 题探针题，校准自评和真实掌握度的差距。",
                    "把暴露出来的薄弱点标成后续可 deep learn 或保底处理对象。",
                ],
            }

        if task_kind == "closed_book_map":
            return {
                "objective": f"{day_prefix}：闭卷重画框架，并补 2 个缺口。",
                "output_action": "闭卷重画一版框架图，再补 2 个关键缺口。",
                "success_criteria": "能不看资料写出核心链路，并标出 2 个下一轮必须复测的缺口。",
                "micro_contract": "如果开始，就先闭卷 10 分钟重画，再打开资料只补 2 处空白。",
                "fail_safe_rule": "如果卡住，不追求完整重建，只保住主链和最影响理解的 2 个缺口。",
                "success_checklist": ["有闭卷框架图", "补了 2 个缺口", "留下下轮复测点"],
                "method_steps": [
                    "先闭卷重画框架图，不查资料。",
                    "对照资料只补最关键的 2 个缺口，不把任务变成重新抄一遍。",
                    f"最后用 {minimum_output} 检查框架是不是已经能被提取出来。",
                ],
            }

        if task_kind == "deep_learn_retrieval":
            return {
                "objective": f"{day_prefix}：先复测旧点，再深学 1 个高权重难点。",
                "output_action": "先复测 6 个旧点，再对 1 个高权重难点做 limited deep learn，并完成 1 个例题或反例。",
                "success_criteria": "旧点至少 4/6 可提取；新难点能解释适用条件，并完成 1 个例题或反例。",
                "micro_contract": "如果开始，就先复测旧点；旧点没过，不追加第二个新难点。",
                "fail_safe_rule": "如果复测掉太多点，今天取消 deep learn，改成只修旧点和最小检查。",
                "success_checklist": ["复测了 6 个旧点", "只深学 1 个难点", "有 1 个例题或反例"],
                "method_steps": [
                    "先复测上一轮旧点，确认不是看过就算会。",
                    "只挑 1 个高权重、串联性强的难点做深学，不并行开第二个。",
                    "立刻用 1 个例题或反例检验 deep learn 是否转成可用理解。",
                ],
            }

        if task_kind == "spaced_retrieval":
            return {
                "objective": f"{day_prefix}：复测旧点，再把今天的新内容接到检索回路里。",
                "output_action": "复测前一天或上一轮的 6 个点，再记录今天新增的 2 个复测点。",
                "success_criteria": "旧点至少 4/6 可提取，并为今天的新内容留下 2 个下一轮复测点。",
                "micro_contract": "如果开始，就先复测旧点；没复测完，不进入新的阅读输入。",
                "fail_safe_rule": "如果没时间，至少保留旧点复测和 2 个下一轮复测点。",
                "success_checklist": ["复测了旧点", "记录 2 个下一轮复测点", "今天不是只阅读"],
                "method_steps": [
                    "先复测前一天或上一轮错点，不看资料作答。",
                    "只把今天的新内容学到能接入下一轮复测，不追求一次性完全吃透。",
                    f"最后用 {minimum_output} 把今天的新旧内容都收进检索闭环。",
                ],
            }

        if task_kind == "integration_retrieval":
            return {
                "objective": f"{day_prefix}：完成跨章节整合题，并更新下一轮复测名单。",
                "output_action": "完成 4 道跨章节整合题，并记录预测分与实际表现差距。",
                "success_criteria": "完成 4 道整合题，归纳至少 2 个跨章节混淆点，并更新下一轮复测名单。",
                "micro_contract": "如果开始，就先做整合题再回看资料，不要反过来。",
                "fail_safe_rule": "如果状态差，就保留 2 道整合题和 2 个混淆点，不再追加新难题。",
                "success_checklist": ["完成整合题", "有预测分与实际差距", "有下一轮复测名单"],
                "method_steps": [
                    "先做跨章节整合题，用题目暴露连接点是否真的建立起来。",
                    "记录你的预测表现和实际表现差距，识别高估区域。",
                    "把暴露出的混淆点写成下一轮 spaced retrieval 的复测名单。",
                ],
            }

        if task_kind == "stage_mock":
            return {
                "objective": f"{day_prefix}：完成一次阶段模拟，并生成下一轮优先级清单。",
                "output_action": "完成一次阶段模拟，并整理 Top 3 失分来源和下一轮 5 个复测点。",
                "success_criteria": "拿到阶段分数或正确率，写出 Top 3 失分来源，并明确下一轮 5 个复测点。",
                "micro_contract": "如果开始，就按正式节奏先做完整轮次；做完后再分析，不边做边补。",
                "fail_safe_rule": "如果时间不足，就做压缩版阶段模拟，但必须留下失分归因和下一轮复测点。",
                "success_checklist": ["有阶段结果", "有 Top 3 失分来源", "有下一轮 5 个复测点"],
                "method_steps": [
                    "先完成一轮阶段模拟，尽量贴近真实考试节奏。",
                    "把失分归因为知识漏洞、提取失败、审题判断问题三类。",
                    "根据失分归因生成下一轮优先级清单，不把最后几天继续堆成阅读任务。",
                ],
            }

        return fallback

    def _build_task_guide_json(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        phase_index: int,
        default_daily_hours: int,
        day_number: int | None = None,
        day_focus: str | None = None,
        day_spec: dict[str, Any] | None = None,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        phase_hours = _safe_int(phase.get("daily_hours")) or default_daily_hours or 2
        method = _strip(phase.get("method"))
        focus = _strip(day_focus or phase.get("focus"))
        output = _strip(phase.get("output"))
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        sprint_policy = _as_dict(phase.get("sprint_policy"))
        retrieval_policy = _as_dict(phase.get("retrieval_policy") or sprint_policy.get("retrieval_policy"))
        sprint_mode = _strip(sprint_policy.get("sprint_mode") or phase.get("sprint_mode") or "exam_sprint")
        minimum_output = _strip(retrieval_policy.get("minimum_output") or "闭卷复述或小测")
        task_kind = _strip((day_spec or {}).get("task_kind") or "retrieval_drill")
        contract = self._build_daily_task_contract(
            task_kind=task_kind,
            sprint_mode=sprint_mode,
            phase_label=_strip(phase.get("label") or "当前阶段"),
            focus=focus,
            output=output,
            minimum_output=minimum_output,
            day_number=day_number,
        )
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        materials = [
            item
            for item in list(brief.get("available_materials") or session.collected.get("available_materials") or [])
            if _strip(item)
        ]
        blocked_days = [
            item
            for item in list(brief.get("blocked_days") or session.collected.get("blocked_days") or [])
            if _strip(item)
        ]
        guide_steps = list(contract["method_steps"])
        if materials:
            guide_steps.insert(1, f"优先使用你手头已有的资料：{'、'.join(materials[:3])}。")
        guide_steps.insert(
            min(2, len(guide_steps)),
            f"执行时只围绕今天这一个明确产出动作推进：{contract['output_action']}",
        )
        if method:
            guide_steps.append(f"阶段方法提醒：{method}")
        if sprint_mode == "seven_day_survival":
            guide_steps.append("如果遇到低频且耗时的细节，先记录到 defer_or_skip，不在今天死磕。")
        elif sprint_mode == "fourteen_day_build_and_retrieve":
            guide_steps.append("把今天错过或卡住的点标成下一轮间隔复测对象，不靠一次阅读判断掌握。")
        if blocked_days:
            guide_steps.append(f"如果碰到这些忙碌时段，就把任务压缩成保底版：{'；'.join(blocked_days[:2])}。")
        key_points = [
            focus or f"{subject} 的阶段重点",
            contract["output_action"],
            contract["success_criteria"],
            f"检索优先：{minimum_output}",
        ]
        if materials:
            key_points.append(f"优先吃透手头资料里的高频材料：{'、'.join(materials[:2])}")
        if session.bottlenecks:
            key_points.extend(
                _strip(item.get("description")) for item in session.bottlenecks[:1] if _strip(item.get("description"))
            )
        common_mistakes = [
            _strip(item.get("specific_risk"))
            for item in (session.bottlenecks or [])[:2]
            if _strip(item.get("specific_risk"))
        ]
        if not common_mistakes:
            common_mistakes = ["只看内容不做自测，最后很难知道自己到底会不会。"]
        return {
            "objective": contract["objective"],
            "method_steps": guide_steps,
            "time_estimate_minutes": _safe_int((day_spec or {}).get("estimated_minutes")) or max(phase_hours * 60, 30),
            "output_action": contract["output_action"],
            "success_criteria": contract["success_criteria"],
            "key_points": key_points,
            "common_mistakes": common_mistakes,
            "retrieval_first": True,
            "sprint_mode": sprint_mode,
            "task_kind": task_kind,
            "minimum_output": minimum_output,
            "micro_contract": contract["micro_contract"],
            "success_checklist": contract["success_checklist"],
            "fail_safe_rule": contract["fail_safe_rule"],
        }

    def _build_task_ai_prompt(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        guide_json: dict[str, Any],
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> str:
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        baseline = _strip(session.collected.get("knowledge_baseline") or "基础不稳")
        daily_hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        motivation = _strip(session.collected.get("motivation"))
        phase_label = _strip(phase.get("label") or "当前阶段")
        sprint_policy = _as_dict(phase.get("sprint_policy"))
        sprint_mode = _strip(sprint_policy.get("sprint_mode") or phase.get("sprint_mode") or "exam_sprint")
        retrieval_policy = _as_dict(phase.get("retrieval_policy") or sprint_policy.get("retrieval_policy"))
        minimum_output = _strip(
            retrieval_policy.get("minimum_output") or guide_json.get("minimum_output") or "闭卷复述或小测"
        )
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        materials = [
            item
            for item in list(brief.get("available_materials") or session.collected.get("available_materials") or [])
            if _strip(item)
        ]
        blocked_days = [
            item
            for item in list(brief.get("blocked_days") or session.collected.get("blocked_days") or [])
            if _strip(item)
        ]
        latent_threads = [
            item for item in list(brief.get("latent_threads") or []) if _strip(item.get("context_snapshot"))
        ]
        materials_line = f"手头资料包括：{'、'.join(materials[:3])}。\n" if materials else ""
        blocked_days_line = f"已知忙碌时段：{'；'.join(blocked_days[:2])}。\n" if blocked_days else ""
        latent_line = f"还需要顺手照顾的潜在线索：{latent_threads[0]['context_snapshot']}。\n" if latent_threads else ""
        motivation_line = f"【核心驱动】{motivation}。\n" if motivation else ""
        output_action = _strip(guide_json.get("output_action"))
        micro_contract = _strip(guide_json.get("micro_contract"))
        fail_safe_rule = _strip(guide_json.get("fail_safe_rule"))
        return (
            f"【背景】我是学生，目标是 {session.goal_raw or f'在限定时间内完成 {subject} 备考'}。\n"
            f"{motivation_line}\n"
            f"【我的情况】科目是 {subject}，当前基础是 {baseline}，每天大概能投入 {daily_hours} 小时。\n"
            f"{materials_line}{blocked_days_line}{latent_line}\n"
            f"【冲刺策略】{sprint_mode}；本任务必须有输出动作：{minimum_output}。\n"
            f"【当前阶段】{phase_label}\n"
            f"重点：{_strip(phase.get('focus'))}\n"
            f"目标：{_strip(guide_json.get('objective'))}\n"
            f"今天的输出动作：{output_action}\n"
            f"完成标准：{_strip(guide_json.get('success_criteria'))}\n"
            f"启动约定：{micro_contract}\n"
            f"失手时降压规则：{fail_safe_rule}\n\n"
            "【请帮我】\n"
            "1. 先用一个闭卷问题检查我现在到底会不会，不要直接灌内容\n"
            "2. 再用最精炼的方式讲清当前阶段最关键的知识点\n"
            "3. 给我 3 个由浅到深的检查题，不要先给答案\n"
            "4. 优先围绕今天的输出动作设计推进路径，不要把任务变回泛泛地读章节\n"
            "5. 如果我说没搞懂、落后或没时间，先收窄成一个更轻、更具体的补强动作，不继续加难\n"
            "6. 告诉我这个阶段最容易踩的坑，以及哪些低 ROI 内容可以先放一放\n\n"
            "【风格要求】直接、结论先行、不说空话，我的时间很紧。"
        )

    async def _prefill_from_profile_context(self, context: dict[str, Any]) -> dict[str, Any]:
        profile_context = _as_dict(context.get("profile_context"))
        prefs = _as_dict(profile_context.get("preferences"))
        cold_start = _as_dict(prefs.get(PLANNING_PROFILE_KEYS["cold_start_context"]))
        galaxy_baseline = _as_dict(context.get("galaxy_baseline") or context.get("request_extra_context", {}).get("galaxy_baseline"))
        galaxy_avg = galaxy_baseline.get("avg_mastery") if galaxy_baseline else None
        galaxy_derived_baseline = self._classify_baseline_from_galaxy(galaxy_avg) if galaxy_avg is not None else None
        merged = {
            "goal_raw": _strip(cold_start.get("primary_goal_description")),
            "exam_scope": _strip(cold_start.get("exam_scope") or cold_start.get("subject")),
            "knowledge_baseline": _strip(cold_start.get("knowledge_baseline")) or galaxy_derived_baseline,
            "time_available": self._format_time_available(cold_start),
            "daily_available_hours": _safe_int(cold_start.get("daily_available_hours")),
            "blocked_days": cold_start.get("blocked_days") or [],
            "available_materials": cold_start.get("available_materials") or [],
            "subject": _strip(cold_start.get("subject")),
            "time_constraint_days": _safe_int(cold_start.get("time_constraint_days")),
            "avg_mastery_score": galaxy_avg,
            "weak_nodes": galaxy_baseline.get("weak_nodes") if galaxy_baseline else None,
            "motivation": _strip(
                cold_start.get("motivation") or cold_start.get("goal_motivation")
            ),
        }
        return {key: value for key, value in merged.items() if value not in (None, "", [], {})}

    def _build_bottlenecks(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> list[dict[str, Any]]:
        # Phase II: replace this V1 rule template with LLM-backed analysis once richer study signals are available.
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "这门课")
        baseline = _strip(session.collected.get("knowledge_baseline") or "基础不稳")
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        blocked_days = [
            item
            for item in list(brief.get("blocked_days") or session.collected.get("blocked_days") or [])
            if _strip(item)
        ]
        materials = [
            item
            for item in list(brief.get("available_materials") or session.collected.get("available_materials") or [])
            if _strip(item)
        ]
        open_tensions = list(brief.get("open_tensions") or [])
        return [
            {
                "id": "b1",
                "description": (
                    f"知识覆盖率不足：{subject} 需要在 {days} 天内完成压缩复习，但你当前只有每天约 {hours} 小时的有效时间。"
                    if not blocked_days
                    else f"知识覆盖率不足：{subject} 需要在 {days} 天内完成压缩复习，而你这几天还夹着忙碌时段（{'；'.join(blocked_days[:2])}）。"
                ),
                "severity": "high",
                "specific_risk": "如果前两天没有快速建立章节框架，后半程很容易只顾着赶进度，留不出完整模拟的时间。",
            },
            {
                "id": "b2",
                "description": f"理解成本偏高：你目前属于“{baseline}”状态，说明核心概念需要先用框架化方式补起来，而不能直接堆题。",
                "severity": "high",
                "specific_risk": f"像 {subject} 这类概念多、易混淆的科目，如果不先拉出对比框架，考试时会出现‘看着眼熟但不会判断’的问题。",
            },
            {
                "id": "b3",
                "description": (
                    "题感不足：当前信息里还没有看到你做过稳定的真题或自测，这意味着知识点可能学过却不会落到题型上。"
                    if not materials
                    else f"题感转化压力：你手头已经有 {'、'.join(materials[:2])}，但如果这些材料没被尽快转成自测回路，后面还是会只顾输入不顾检验。"
                ),
                "severity": "medium",
                "specific_risk": (
                    "后两天如果才第一次接触题目，会来不及暴露高频错误类型，冲刺效率会明显下降。"
                    if not open_tensions
                    else f"目前还有 {len(open_tensions)} 块信息缺口没完全闭合，如果不尽早用题目和资料一起校准，计划会越来越像按假设推进。"
                ),
            },
        ]

    def _build_exam_sprint_policy(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        materials = [
            _strip(item)
            for item in list(brief.get("available_materials") or session.collected.get("available_materials") or [])
            if _strip(item)
        ]
        cold_start = _as_dict(session.collected.get("cold_start_context"))
        policy = ExamSprintPolicyEngine.build(
            ExamSprintPolicyInput(
                total_days=days,
                subject=subject,
                exam_scope=_strip(session.collected.get("exam_scope")),
                knowledge_baseline=_strip(session.collected.get("knowledge_baseline")),
                time_available=_strip(session.collected.get("time_available")),
                daily_available_hours=hours,
                materials=tuple(materials),
                cold_start_context=cold_start,
                existing_signals={
                    "bottlenecks": session.bottlenecks or [],
                    "aurora_activity_profile": _as_dict(brief.get("activity_profile")),
                },
            )
        )
        return policy.to_dict()

    def _build_strategy(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        # Phase II: replace this V1 rule template with LLM-backed strategy generation for non-demo domains.
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        activity_profile = _as_dict(brief.get("activity_profile"))
        sprint_policy = self._build_exam_sprint_policy(session, aurora_state=aurora_state)
        policy_density = float(sprint_policy.get("task_density_hint") or 0.7)
        density_hint = min(policy_density, float(activity_profile.get("task_density_hint") or policy_density))
        density_delta = -1 if density_hint <= 0.4 else 1 if density_hint >= 0.85 else 0
        materials = [
            item
            for item in list(brief.get("available_materials") or session.collected.get("available_materials") or [])
            if _strip(item)
        ]
        blocked_days = [
            item
            for item in list(brief.get("blocked_days") or session.collected.get("blocked_days") or [])
            if _strip(item)
        ]
        open_tensions = list(brief.get("open_tensions") or [])
        latent_threads = list(brief.get("latent_threads") or [])
        ranges = self._phase_day_ranges(days)
        if sprint_policy.get("sprint_mode") == "seven_day_survival":
            templates = [
                {
                    "label": "诊断分诊",
                    "hour_delta": 0,
                    "focus": f"先把 {subject} 的考试范围切成高频保底、需要补强、可以暂缓三类。",
                    "method": "用考纲/课件/真题快速定位高频内容；每看完一块就闭卷写 3 个关键词，低 ROI 内容记入 defer_or_skip。",
                    "output": "知道哪些内容先保底，哪些内容暂缓，不再线性从第一页复习。",
                },
                {
                    "label": "检索攻克",
                    "hour_delta": 0,
                    "focus": "每天围绕高频基础分做闭卷输出 + 典型题验证，优先修补最影响及格线的漏洞。",
                    "method": "先闭卷复述，再做 3–5 道代表题；错题只追到能做对同型题，不扩展到低频细节。",
                    "output": "核心概念能说清，典型题能独立判断，薄弱点被转成补强任务。",
                },
                {
                    "label": "保底模拟",
                    "hour_delta": 1,
                    "focus": "用限时自测确认保底线，把最后时间集中在最可能提分的错误类型上。",
                    "method": "做一轮小模拟或半套真题；按概念混淆、题型不会、记忆断点归类，只补最高收益漏洞。",
                    "output": "完成接近考试的检索测试，明确最后 24 小时保留、补强和暂缓的内容。",
                },
            ]
        elif sprint_policy.get("sprint_mode") == "fourteen_day_build_and_retrieve":
            templates = [
                {
                    "label": "结构诊断",
                    "hour_delta": 0,
                    "focus": f"建立 {subject} 的知识框架，同时用探针题校准真实掌握度。",
                    "method": "先看范围和资料，再做少量诊断题；把高权重、串联性强的内容标为可深学对象。",
                    "output": "形成第一版知识地图，知道哪些点需要 deep learn，哪些只做识别保底。",
                },
                {
                    "label": "间隔再学",
                    "hour_delta": 1,
                    "focus": "用两轮复习把核心内容从看懂推进到能提取，穿插间隔检索防止假性掌握。",
                    "method": "今天学过的点隔天复测；错题以 successive relearning 方式做到再次独立答对。",
                    "output": "核心内容至少经历一次间隔复测，错题不只停留在看懂答案。",
                },
                {
                    "label": "模拟整合",
                    "hour_delta": 1,
                    "focus": "用阶段模拟整合题感，再把低信心节点回填到最后一轮复习。",
                    "method": "做阶段模拟或半套真题；根据预测分与实际分差距校准下一轮复习权重。",
                    "output": "完成阶段性模拟，能解释主要失分来源并形成最后冲刺清单。",
                },
            ]
        else:
            templates = [
                {
                    "label": "建立框架",
                    "hour_delta": 0,
                    "focus": f"先把 {subject} 的考查范围、章节框架和高频概念拉出来，不追求一开始就吃透全部细节。",
                    "method": "优先看老师课件/教材目录/考纲，把每章只记核心概念、关键词和常见问法；看完一章就用自己的话复述。",
                    "output": "能说清每章在考什么，知道最值得优先啃的 20% 内容。",
                },
                {
                    "label": "核心攻克",
                    "hour_delta": 1,
                    "focus": "围绕最容易丢分的核心知识点做理解 + 小量题目验证，尽快建立能解释、能判断的能力。",
                    "method": "每天只攻 1–2 个核心点：先学概念，再马上做对应选择题/典型题，最后复盘‘我为什么错’。",
                    "output": "对重点协议/概念能独立解释，常见题型不再完全靠猜。",
                },
                {
                    "label": "模拟冲刺",
                    "hour_delta": 1,
                    "focus": "通过自测或真题暴露薄弱点，再把最后时间砸到最值分的漏洞上。",
                    "method": "至少做 1 轮限时自测；把错误按‘概念混淆 / 不会判断 / 记忆断点’归类，最后只补最高频错误。",
                    "output": "能完成至少 1 轮接近考试的自测，知道最后 24 小时该补哪里。",
                },
            ]
        phases = []
        for index, day_range in enumerate(ranges, start=1):
            template = templates[index - 1]
            method = template["method"]
            if materials and index == 1:
                method = f"{method} 优先用你手头的 {'、'.join(materials[:2])} 来确认范围，而不是重新找资料。"
            if materials and index == len(ranges):
                method = f"{method} 把 {'、'.join(materials[:2])} 里的高频题先过一轮。"
            phases.append(
                {
                    "phase": index,
                    "start_day": day_range["start"],
                    "end_day": day_range["end"],
                    "days": self._format_day_range(day_range["start"], day_range["end"]),
                    "label": template["label"],
                    "daily_hours": max(1, hours + int(template["hour_delta"]) + density_delta),
                    "focus": template["focus"],
                    "method": method,
                    "output": template["output"],
                    "sprint_mode": sprint_policy.get("sprint_mode"),
                    "sprint_policy": sprint_policy,
                    "retrieval_policy": sprint_policy.get("retrieval_policy") or {},
                }
            )
        first_checkpoint = min(days, ranges[0]["end"])
        final_checkpoint = min(days, ranges[-1]["start"])
        checkpoint_tail = f" 同时避开这些忙碌时段：{'；'.join(blocked_days[:2])}。" if blocked_days else ""
        return {
            "total_days": days,
            "sprint_policy": sprint_policy,
            "daily_commitment_range": f"{max(1, hours - 1 + density_delta)}–{max(1, hours + 1 + density_delta)}小时",
            "phases": phases,
            "checkpoints": [
                {
                    "day": first_checkpoint,
                    "description": f"Day {first_checkpoint} 晚：做一轮 15–20 题的小自测，确认框架阶段是否真的建立起来。{checkpoint_tail}".strip(),
                },
                {
                    "day": final_checkpoint,
                    "description": f"Day {final_checkpoint}：冲刺前做半套题，判断还要不要压缩范围。",
                },
            ],
            "adjustment_triggers": [
                f"如果 Day {first_checkpoint} 自测低于 30%，说明基础理解成本比预期更高，后续每天只攻 1 个核心点。",
                "如果冲刺前半套题已经超过 60%，最后阶段优先做题感和高频陷阱纠偏。",
            ],
            "strategy_notes": sprint_policy.get("strategy_notes") or [],
            "user_context_digest": {
                "goal_raw": _strip(session.goal_raw),
                "blocked_days": blocked_days,
                "available_materials": materials,
                "open_tensions": open_tensions,
                "latent_threads": latent_threads,
            },
            "aurora_brief": brief,
        }

    def _phase_day_ranges(self, total_days: int) -> list[dict[str, int]]:
        days = max(1, int(total_days or 1))
        phase_count = 2 if days <= 4 else 3
        base = days // phase_count
        remainder = days % phase_count
        ranges: list[dict[str, int]] = []
        cursor = 1
        for index in range(phase_count):
            span = base + (1 if index < remainder else 0)
            start = cursor
            end = min(days, cursor + max(span, 1) - 1)
            ranges.append({"start": start, "end": end})
            cursor = end + 1
        return ranges

    def _format_day_range(self, start: int, end: int) -> str:
        if start == end:
            return f"Day {start}"
        return f"Day {start}–{end}"

    def _daily_task_specs(self, phase: dict[str, Any], *, phase_index: int) -> list[dict[str, Any]]:
        start_day = _safe_int(phase.get("start_day"))
        end_day = _safe_int(phase.get("end_day"))
        if start_day is None or end_day is None:
            day_match = re.search(r"Day\s+(?P<start>\d+)(?:[–-](?P<end>\d+))?", _strip(phase.get("days")))
            start_day = int(day_match.group("start")) if day_match else phase_index
            end_day = int(day_match.group("end") or start_day) if day_match else start_day
        focus = _strip(phase.get("focus"))
        label = _strip(phase.get("label") or "阶段推进")
        sprint_mode = _strip(phase.get("sprint_mode") or _as_dict(phase.get("sprint_policy")).get("sprint_mode"))
        retrieval_policy = _as_dict(
            phase.get("retrieval_policy") or _as_dict(phase.get("sprint_policy")).get("retrieval_policy")
        )
        minimum_output = _strip(retrieval_policy.get("minimum_output") or "闭卷复述或小测")
        phase_days = max(1, end_day - start_day + 1)
        specs: list[dict[str, Any]] = []
        for day in range(start_day, end_day + 1):
            offset = day - start_day
            task_kind = "retrieval_drill"
            title_focus = "闭卷检索"
            day_focus = f"{label}第 {offset + 1} 天：{focus}"
            if sprint_mode == "seven_day_survival":
                if phase_index == 1 and offset == 0:
                    task_kind = "diagnostic_triage"
                    title_focus = "诊断分诊"
                    day_focus = f"{label}第 {offset + 1} 天：用小测和资料确认高频保底范围，并标记 defer_or_skip 内容。"
                elif phase_index == 1:
                    task_kind = "retrieval_triage"
                    title_focus = "高频保底"
                    day_focus = f"{label}第 {offset + 1} 天：闭卷复述高频概念，再把不会的点转成补强清单。"
                elif phase_index == 2:
                    task_kind = "retrieval_drill"
                    title_focus = "典型题检索"
                    day_focus = f"{label}第 {offset + 1} 天：先闭卷输出，再做代表题验证，错题只追到同型题能做对。"
                else:
                    task_kind = "mock_review" if offset >= phase_days - 1 else "retrieval_repair"
                    title_focus = "限时自测" if task_kind == "mock_review" else "漏洞补强"
                    day_focus = f"{label}第 {offset + 1} 天：用限时自测暴露漏洞，只补最高收益错误类型。"
            elif sprint_mode == "fourteen_day_build_and_retrieve":
                if phase_index == 1:
                    task_kind = "diagnostic_map" if offset == 0 else "closed_book_map"
                    title_focus = "结构诊断" if offset == 0 else "闭卷复述"
                    day_focus = f"{label}第 {offset + 1} 天：建立知识框架后做探针题，校准自评和真实掌握度。"
                elif phase_index == 2:
                    task_kind = "deep_learn_retrieval" if offset == 0 else "spaced_retrieval"
                    title_focus = "深学+复测" if task_kind == "deep_learn_retrieval" else "间隔再学"
                    day_focus = (
                        f"{label}第 {offset + 1} 天：先复测上一轮旧点，再对 1 个高权重难点做 limited deep learn。"
                        if task_kind == "deep_learn_retrieval"
                        else f"{label}第 {offset + 1} 天：复测前一天或上一轮错点，再学习今天的高权重内容。"
                    )
                else:
                    task_kind = "stage_mock" if offset >= phase_days - 1 else "integration_retrieval"
                    title_focus = "阶段模拟" if task_kind == "stage_mock" else "整合检索"
                    day_focus = f"{label}第 {offset + 1} 天：用阶段题整合多个知识点，并记录预测分与实际分差距。"
            specs.append(
                {
                    "day": day,
                    "focus": day_focus,
                    "task_kind": task_kind,
                    "title_focus": title_focus,
                    "minimum_output": minimum_output,
                    "estimated_minutes": self._estimated_minutes_for_task(
                        task_kind=task_kind,
                        sprint_mode=sprint_mode,
                        base_minutes=max((_safe_int(phase.get("daily_hours")) or 1) * 60, 30),
                    ),
                }
            )
        return specs

    def _estimated_minutes_for_task(
        self,
        *,
        task_kind: str,
        sprint_mode: str,
        base_minutes: int,
    ) -> int:
        caps = {
            "diagnostic_triage": 55,
            "retrieval_triage": 55,
            "retrieval_drill": 75,
            "retrieval_repair": 50,
            "mock_review": 85,
            "diagnostic_map": 70,
            "closed_book_map": 65,
            "deep_learn_retrieval": 85,
            "spaced_retrieval": 75,
            "integration_retrieval": 85,
            "stage_mock": 110,
        }
        floors = {
            "seven_day_survival": 35,
            "fourteen_day_build_and_retrieve": 45,
        }
        floor = floors.get(sprint_mode, 30)
        cap = caps.get(task_kind, base_minutes)
        return max(floor, min(base_minutes, cap))

    def _progress_data(self, state: str) -> dict[str, Any]:
        current = {
            "CLARIFYING": 0,
            "BOTTLENECK": 1,
            "AWAITING_CONFIRM": 2,
            "GENERATING": 3,
            "DONE": 3,
        }.get(state, 0)
        return {
            "current_step": current,
            "steps": ["了解情况", "分析瓶颈", "确认策略", "生成计划"],
        }

    def _format_time_available(self, cold_start: dict[str, Any]) -> str:
        hours = _safe_int(cold_start.get("daily_available_hours"))
        if hours:
            return f"每天约 {hours} 小时"
        minutes = _safe_int(cold_start.get("study_time_minutes"))
        if minutes:
            return f"每天约 {minutes} 分钟"
        return ""

    def _build_cold_start_context(self, collected: dict[str, Any]) -> dict[str, Any]:
        fields = [
            bool(_strip(collected.get("goal_raw") or collected.get("primary_goal_description"))),
            bool(_strip(collected.get("subject") or collected.get("exam_scope"))),
            bool(_safe_int(collected.get("time_constraint_days"))),
            bool(_strip(collected.get("knowledge_baseline"))),
            bool(_safe_int(collected.get("daily_available_hours"))),
        ]
        completeness = round(sum(1 for item in fields if item) / len(fields), 2)
        return {
            "primary_goal_description": _strip(collected.get("goal_raw") or collected.get("primary_goal_description")),
            "goal_type": "exam",
            "subject": _strip(collected.get("subject")),
            "exam_scope": _strip(collected.get("exam_scope")),
            "time_constraint_days": _safe_int(collected.get("time_constraint_days")) or 7,
            "knowledge_baseline": _strip(collected.get("knowledge_baseline")),
            "daily_available_hours": _safe_int(collected.get("daily_available_hours")) or 0,
            "blocked_days": collected.get("blocked_days") or [],
            "available_materials": collected.get("available_materials") or [],
            "collected_at": _utcnow().isoformat(),
            "completeness": completeness,
        }

    async def _persist_profile_payload(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        key: str,
        value: Any,
    ) -> None:
        await ProfileWriteService(db, cache_service.redis).set_explicit_preference(
            user_id=user_id,
            pref_key=key,
            pref_value=value,
            evidence_refs=[{"type": "system", "id": "planning_workflow.v1"}],
            source_type="system",
            source="planning_workflow",
        )

    async def _load_onboarding_state(self, conversation_id: str) -> dict[str, Any]:
        if not self.redis:
            return {}
        raw = await self.redis.get(f"onboarding:modeling:{conversation_id}")
        if not raw:
            return {}
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        try:
            return _as_dict(json.loads(raw))
        except Exception:
            return {}

    async def _save_onboarding_state(self, conversation_id: str, payload: dict[str, Any]) -> None:
        if not self.redis or not conversation_id:
            return
        if not payload:
            await self.redis.delete(f"onboarding:modeling:{conversation_id}")
            return
        await self.redis.setex(
            f"onboarding:modeling:{conversation_id}",
            PLANNING_SESSION_TTL,
            json.dumps(payload, ensure_ascii=False),
        )

    def _update_onboarding_collected(self, collected: dict[str, Any], message: str, turn: int) -> None:
        text = _strip(message)
        lowered = text.lower()
        if turn == 1:
            collected["primary_goal_description"] = text
            if any(token in lowered for token in ("考", "期末", "备考", "考试")):
                collected["goal_type"] = "exam"
            elif any(token in lowered for token in ("项目", "demo", "项目")):
                collected["goal_type"] = "project"
            else:
                collected["goal_type"] = "skill"
            subject_match = re.search(r"(计算机网络|计网|高数|线代|概率论|操作系统|数据库|英语)", text)
            if subject_match:
                collected["subject"] = subject_match.group(1)
        elif turn == 2:
            day_match = re.search(r"(\d+)\s*(天|day|days|周)", lowered)
            if day_match:
                collected["time_constraint_days"] = int(day_match.group(1))
            if any(token in lowered for token in ("没学过", "零基础", "完全不会")):
                collected["knowledge_baseline"] = "zero"
            elif any(token in lowered for token in ("上过课", "没复习", "忘了")):
                collected["knowledge_baseline"] = "class_only"
            elif any(token in lowered for token in ("会一些", "学过一些", "一半")):
                collected["knowledge_baseline"] = "partial"
        elif turn == 3:
            time_match = re.search(r"(\d+(?:\.\d+)?)\s*(小时|h|hour)", lowered)
            minute_match = re.search(r"(\d+)\s*分钟", lowered)
            if time_match:
                collected["daily_available_hours"] = int(float(time_match.group(1)))
            elif minute_match:
                collected["daily_available_hours"] = max(1, round(int(minute_match.group(1)) / 60))
            if "没空" in lowered or "有课" in lowered:
                collected["blocked_days"] = [text]

    def _build_onboarding_question_two(self, collected: dict[str, Any]) -> str:
        goal_type = _strip(collected.get("goal_type"))
        subject = _strip(collected.get("subject") or "这件事")
        if goal_type == "exam":
            return f"{subject} 是多久后考？你目前对这门课大概是完全没学过，还是上过课但还没真正复习？"
        if goal_type == "project":
            return "这个项目什么时候要交？你现在最卡住的是哪一段？"
        return "你想把这件事推进到什么程度？现在已经会多少了？"

    def _build_onboarding_summary(self, collected: dict[str, Any]) -> str:
        subject = _strip(collected.get("subject") or "这个目标")
        baseline = _strip(collected.get("knowledge_baseline") or "当前基础")
        hours = _safe_int(collected.get("daily_available_hours")) or 0
        return (
            f"好，我大概了解了：你现在主要想推进的是「{subject}」，目前属于 {baseline} 状态，"
            f"每天大概能拿出 {hours} 小时。等你开始规划的时候，我会按这个节奏帮你定制方案。"
        )
