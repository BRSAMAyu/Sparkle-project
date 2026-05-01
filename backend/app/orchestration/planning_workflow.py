from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.aurora.runtime_v1 import AuroraRuntimePlanningAdapter, AuroraRuntimePlanningState
from app.core.cache import cache_service
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.task import Task, TaskStatus
from app.models.task_resources import TaskKnowledgeLink
from app.models.user_preferences import UserPreferencesCenter
from app.orchestration.adaptive_replanner import AdaptiveReplanner
from app.orchestration.exam_sprint_policy import ExamSprintPolicyEngine, ExamSprintPolicyInput
from app.schemas.plan import PlanCreate
from app.schemas.task import TaskCreate, coerce_task_type
from app.services.galaxy_service import GalaxyService
from app.services.plan_service import PlanService
from app.services.profile_write_service import ProfileWriteService
from app.services.task_service import TaskService
from app.sprint_packs.last_24h_mode import (
    apply_last_24h_policy_overrides,
    calculate_days_left,
    extract_exam_date,
    is_last_24h_window,
)
from app.sprint_packs.sprint_pack_loader import (
    get_archetypes_by_nodes,
    get_mistake_by_nodes,
    load_pack,
    query_nodes_by_priority,
)

PLANNING_SESSION_TTL = 2 * 60 * 60
PLANNING_SESSION_PREFIX = "planning:session:"
EXAM_SPRINT_GROWTH_ARCHIVE_KEY = "exam_sprint_growth_archive"
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
HISTORY_MASTERED_THRESHOLD = 0.7
HISTORY_WEAK_THRESHOLD = 0.4
EXAM_SPRINT_DEADLINE_RE = re.compile(
    r"(?:[一二两三四五六七八九十\d]+)\s*(?:天|日|周)\s*(?:后|内)?\s*(?:考|考试|期末|备考|复习|冲刺)"
    r"|(?:考|考试|期末|备考|复习|冲刺).{0,12}(?:[一二两三四五六七八九十\d]+)\s*(?:天|日|周)",
    re.IGNORECASE,
)
EXAM_SPRINT_FAST_TRACK_FLAG = "fast_track_exam_sprint"
_SPRINT_PACK_LAYER_LABELS = {
    "architecture": "网络体系结构",
    "physical": "物理层",
    "data_link": "数据链路层",
    "network": "网络层",
    "transport": "传输层",
    "application": "应用层",
    "security": "网络安全",
    "security_performance": "安全与性能",
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _strip(value: Any) -> str:
    return str(value or "").strip()


def _listish(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list | tuple | set):
        return [item for item in value if item not in (None, "")]
    return [value] if value not in (None, "") else []


def _safe_int(value: Any) -> int | None:
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _match_seed_nodes_to_focus(seed_nodes: list[str], focus: str) -> list[str]:
    """Match seed library node IDs against focus text by token overlap.

    E.g. node ID "cn.tcp_flow" yields tokens ["tcp", "flow"];
    if focus contains "tcp", the node is considered a match.
    """
    if not focus:
        return []
    focus_lower = focus.lower()
    matched: list[str] = []
    for node_id in seed_nodes:
        parts = node_id.split(".")
        tokens = [t.lower() for part in parts for t in part.split("_") if len(t) > 1]
        if any(token in focus_lower for token in tokens):
            matched.append(node_id)
    return matched


def _sprint_pack_domain_hints(pack: dict[str, Any], *, limit: int = 6) -> list[str]:
    """Return compact domain hints from a Sprint Pack without exposing the full node list."""
    seen: set[str] = set()
    hints: list[str] = []
    for node in list(pack.get("knowledge_nodes") or []):
        if not isinstance(node, dict):
            continue
        layer = _strip(node.get("layer"))
        layer = _SPRINT_PACK_LAYER_LABELS.get(layer, layer)
        if not layer or layer in seen:
            continue
        seen.add(layer)
        hints.append(layer)
        if len(hints) >= limit:
            break
    return hints


def _format_sprint_pack_scope(pack: dict[str, Any], subject: str) -> str:
    pack_subject = _strip(pack.get("subject")) or subject
    hints = _sprint_pack_domain_hints(pack)
    if hints:
        return f"{pack_subject}（Sprint Pack 默认范围：{'、'.join(hints)}）"
    description = _strip(pack.get("description"))
    if description:
        return f"{pack_subject}（Sprint Pack 默认范围：{description[:80]}）"
    return pack_subject


def _subject_to_error_book_code(subject: str) -> str | None:
    text = _strip(subject).lower()
    if not text:
        return None
    if any(token in text for token in ("计算机", "计网", "computer", "network", "操作系统", "数据库")):
        return "computer"
    if any(token in text for token in ("英语", "english")):
        return "english"
    if any(token in text for token in ("高数", "数学", "math")):
        return "math"
    if any(token in text for token in ("物理", "physics")):
        return "physics"
    return None


def _task_type_for_day_spec(day_spec: dict[str, Any]) -> str:
    task_kind = _strip(day_spec.get("task_kind")).lower()
    if task_kind in {"retrieval_repair", "error_review", "error_fix"}:
        return "error_fix"
    if task_kind in {"mock_review", "stage_mock", "short_mock", "training"}:
        return "training"
    return "learning"


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
    MOTIVATION_FIELD = "motivation_context"
    CLARIFYING_FIELDS = (*REQUIRED_FIELDS, MOTIVATION_FIELD)

    def __init__(self, redis_client=None, runtime_adapter: AuroraRuntimePlanningAdapter | None = None) -> None:
        self.redis = redis_client or cache_service.redis
        self.runtime_adapter = runtime_adapter or AuroraRuntimePlanningAdapter(redis_client=self.redis)

    def build_exam_sprint_fast_track_context(self, message: str) -> dict[str, Any] | None:
        """Build deterministic Sprint Pack prefill for cold-start exam sprint requests."""
        text = _strip(message)
        if not text:
            return None

        lowered = text.lower()
        if not EXAM_SPRINT_DEADLINE_RE.search(text) and not any(
            token in lowered for token in ("备考", "冲刺", "突击", "cram", "sprint")
        ):
            return None

        extracted = self._extract_clarifying_fields(text)
        subject = _strip(extracted.get("subject"))
        pack = load_pack(subject or text)
        if not pack:
            return None

        pack_subject = _strip(pack.get("subject")) or subject or text
        pack_id = _strip(pack.get("id")) or _strip(pack.get("name")) or pack_subject
        domain_hints = _sprint_pack_domain_hints(pack)
        prefilled_scope = _format_sprint_pack_scope(pack, pack_subject)
        collected = {
            EXAM_SPRINT_FAST_TRACK_FLAG: True,
            "goal_type": "exam",
            "subject": pack_subject,
            "exam_scope": prefilled_scope,
            "sprint_pack_id": pack_id,
            "sprint_pack_subject": pack_subject,
            "pre_filled_domain_hints": domain_hints,
            "cold_start_context": {
                EXAM_SPRINT_FAST_TRACK_FLAG: True,
                "goal_type": "exam",
                "subject": pack_subject,
                "exam_scope": prefilled_scope,
                "sprint_pack_id": pack_id,
                "sprint_pack_subject": pack_subject,
                "pre_filled_domain_hints": domain_hints,
            },
        }
        for key in ("knowledge_baseline", "time_available", "daily_available_hours", "time_constraint_days"):
            value = extracted.get(key)
            if value not in (None, "", [], {}):
                collected[key] = value
                collected["cold_start_context"][key] = value

        return {
            "intent": "exam_sprint",
            "subject": pack_subject,
            "pack": pack,
            "sprint_pack_id": pack_id,
            "pre_filled_scope": prefilled_scope,
            "pre_filled_domain_hints": domain_hints,
            "collected": collected,
        }

    @staticmethod
    def is_fast_track_exam_sprint_session(session: PlanningSession | None) -> bool:
        if session is None:
            return False
        collected = _as_dict(session.collected)
        cold_start = _as_dict(collected.get("cold_start_context"))
        return bool(
            collected.get(EXAM_SPRINT_FAST_TRACK_FLAG)
            or collected.get("sprint_pack_id")
            or cold_start.get(EXAM_SPRINT_FAST_TRACK_FLAG)
            or cold_start.get("sprint_pack_id")
        )

    @staticmethod
    def is_modeling_complete_bridge_session(session: PlanningSession | None) -> bool:
        if session is None:
            return False
        collected = _as_dict(session.collected)
        cold_start = _as_dict(collected.get("cold_start_context"))
        return bool(collected.get("from_modeling_complete") or cold_start.get("from_modeling_complete"))

    def detect_planning_intent(self, message: str, context: dict[str, Any] | None = None) -> bool:
        text = _strip(message).lower()
        if not text:
            return False
        ctx = _as_dict(context)
        if _as_dict(ctx.get("exam_sprint_fast_track")) or self.build_exam_sprint_fast_track_context(message):
            return True
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
                "from_modeling_complete": True,
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
                    cold_start.get("time_available") or cold_start.get("time") or user_model.get("time_available")
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
                    cold_start.get("motivation")
                    or cold_start.get("motivation_context")
                    or user_model.get("motivation")
                    or user_model.get("goal_motivation")
                ),
                "motivation_context": _strip(
                    cold_start.get("motivation_context")
                    or cold_start.get("motivation")
                    or user_model.get("motivation_context")
                    or user_model.get("motivation")
                    or user_model.get("goal_motivation")
                ),
                "calendar_context": _as_dict(
                    modeling_output.get("calendar_context")
                    or cold_start.get("calendar_context")
                    or user_model.get("calendar_context")
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
        context = dict(context or {})
        fast_track_context = _as_dict(context.get("exam_sprint_fast_track"))
        if not fast_track_context:
            detected_fast_track = self.build_exam_sprint_fast_track_context(message)
            if detected_fast_track:
                fast_track_context = detected_fast_track
                context["exam_sprint_fast_track"] = fast_track_context
        profile_context = _as_dict(context.get("profile_context"))
        calendar_context = self._extract_calendar_context(context)
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
            if fast_track_context.get("collected"):
                for key, value in _as_dict(fast_track_context["collected"]).items():
                    if value and not session.collected.get(key):
                        session.collected[key] = value
            if bridge.get("collected"):
                for key, value in _as_dict(bridge["collected"]).items():
                    if value and not session.collected.get(key):
                        session.collected[key] = value
        if calendar_context:
            session.collected["calendar_context"] = calendar_context
            cold_start = _as_dict(session.collected.get("cold_start_context")).copy()
            cold_start["calendar_context"] = calendar_context
            session.collected["cold_start_context"] = cold_start

        if not session.collected.get("previous_exam_weak_nodes"):
            previous_weak_nodes = await self._load_previous_exam_weak_nodes_for_session(
                db=db,
                user_id=user_id,
                session=session,
                profile_context=profile_context,
                message=message,
            )
            if previous_weak_nodes:
                session.collected["previous_exam_weak_nodes"] = previous_weak_nodes

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
        if session.state in {"AWAITING_CONFIRM", "PLANNING"}:
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
        for key, value in extracted_fields.items():
            if (
                key == "exam_scope"
                and self.is_fast_track_exam_sprint_session(session)
                and _strip(session.collected.get("exam_scope"))
            ):
                continue
            session.collected[key] = value
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
            await self._enrich_cross_sprint_mastery_from_galaxy(
                db=db,
                user_id=user_id,
                session=session,
                aurora_state=runtime_state,
            )
            session.bottlenecks = await self._build_bottlenecks(session, aurora_state=runtime_state)
            strategy = self._build_strategy(session, aurora_state=runtime_state)
            await self._refresh_study_material_context(
                db=db,
                user_id=user_id,
                session=session,
                strategy=strategy,
            )
            session.confirmed_strategy = strategy
            auto_generate_from_modeling = self.is_modeling_complete_bridge_session(session)
            session.state = (
                "PLANNING"
                if self.is_fast_track_exam_sprint_session(session) or auto_generate_from_modeling
                else "AWAITING_CONFIRM"
            )
            if db is not None:
                await self._persist_profile_payload(
                    db=db,
                    user_id=user_id,
                    key=PLANNING_PROFILE_KEYS["cold_start_context"],
                    value=self._build_cold_start_context(session.collected),
                )
            if auto_generate_from_modeling:
                return await self._handle_generating(
                    db=db,
                    user_id=user_id,
                    session=session,
                    runtime_state=runtime_state,
                    profile_context=profile_context,
                )
            await self.save_session(session)
            return {
                "message": self._build_strategy_intro(session, runtime_state),
                "widgets": [
                    {"type": "planning_progress_strip", "data": self._progress_data(session.state)},
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
        await self._enrich_cross_sprint_mastery_from_galaxy(
            db=db,
            user_id=user_id,
            session=session,
            aurora_state=runtime_state,
        )
        if not strategy:
            strategy = self._build_strategy(session, aurora_state=runtime_state)
            session.confirmed_strategy = strategy
        await self._refresh_study_material_context(
            db=db,
            user_id=user_id,
            session=session,
            strategy=strategy,
        )

        days = _safe_int(strategy.get("total_days")) or _safe_int(session.collected.get("time_constraint_days")) or 7
        daily_hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "考试科目")
        sprint_policy = _as_dict(strategy.get("sprint_policy"))
        last_24h_mode = bool(sprint_policy.get("last_24h_mode"))
        last_24h_error_clusters = (
            await self._load_last_24h_error_clusters(db=db, user_id=user_id, subject=subject) if last_24h_mode else []
        )
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
        galaxy_weak_nodes = list(session.collected.get("galaxy_weak_nodes") or [])
        phases = list(strategy.get("phases") or [])

        # Signal-to-Action Spine: fetch active directives for this user
        spine = None
        plan_directive = None
        try:
            from app.signals.spine_orchestrator import SpineOrchestrator
            spine = SpineOrchestrator(cache_service.redis)
            plan_directive = await spine.get_plan_directive(str(user_id))
            if plan_directive:
                logger.info("Spine plan_directive active for user {}: action={} constraints={}", user_id, plan_directive.plan_action, list(plan_directive.constraints.keys()))
        except Exception as _spine_exc:
            logger.debug("Spine directive fetch skipped: {}", _spine_exc)

        # Apply PlanDirective constraints to the planning flow
        if plan_directive is not None:
            constraints = plan_directive.constraints
            if constraints.get("do_not_rebuild_entire_plan") and phases:
                # local_replan: only adjust recent days, preserve existing structure
                logger.info("PlanDirective: local_replan — preserving existing plan structure")
            if constraints.get("insert_recovery_task") and phases:
                # Insert a recovery task as day 1 of first phase
                recovery_task = {
                    "day": 1,
                    "focus": "恢复节奏",
                    "task_kind": "recovery_review",
                    "estimated_minutes": 25,
                    "difficulty": 2,
                }
                phases[0]["tasks"] = [recovery_task] + list(phases[0].get("tasks") or [])
                logger.info("PlanDirective: inserted recovery task at day 1")
            if constraints.get("insert_practice_task") and phases:
                practice_task = {
                    "day": 1,
                    "focus": "巩固练习",
                    "task_kind": "worked_example_then_drill",
                    "estimated_minutes": 25,
                    "difficulty": 2,
                }
                phases[0]["tasks"] = [practice_task] + list(phases[0].get("tasks") or [])
                logger.info("PlanDirective: inserted practice task at day 1")
            if constraints.get("insert_easy_win") and phases:
                easy_task = {
                    "day": 1,
                    "focus": "轻松切入",
                    "task_kind": "light_review",
                    "estimated_minutes": 15,
                    "difficulty": 1,
                }
                phases[0]["tasks"] = [easy_task] + list(phases[0].get("tasks") or [])
                logger.info("PlanDirective: inserted easy-win task at day 1")
            if constraints.get("recovery_task") and phases:
                rec_task = {
                    "day": 1,
                    "focus": "任务恢复",
                    "task_kind": "recovery_review",
                    "estimated_minutes": 20,
                    "difficulty": 2,
                }
                phases[0]["tasks"] = [rec_task] + list(phases[0].get("tasks") or [])
                logger.info("PlanDirective: inserted missed-task recovery")

        for index, phase in enumerate(phases, start=1):
            for day_spec in self._daily_task_specs(
                phase,
                phase_index=index,
                session=session,
                error_clusters=last_24h_error_clusters,
                galaxy_weak_nodes=galaxy_weak_nodes or None,
            ):
                # Signal-to-Action Spine: apply directive constraints + audit
                if spine is not None:
                    try:
                        day_spec, _spine_audit = await spine.apply_directive_to_task_spec(
                            str(user_id), day_spec,
                        )
                        if _spine_audit and not _spine_audit.applied:
                            logger.warning("Spine audit violation: {}", _spine_audit.violations)
                        spine = None  # directive consumed once
                    except Exception as _spine_exc:
                        logger.debug("Spine apply_directive skipped: {}", _spine_exc)

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
                # guide_json is already sync-enriched by _build_task_guide_json (enrich_sync path).
                # LLM enrichment (_enrich_task_guide_with_ai) is a background post-creation step
                # and must NOT block the per-task creation loop — see P1 constraint.
                subject_strategy = _as_dict(day_spec.get("subject_strategy"))
                review_mode = _strip(subject_strategy.get("review_mode") or day_spec.get("review_mode"))
                min_estimated_minutes = 10 if review_mode == "skip_or_light_review" else 30
                task = await TaskService.create(
                    db=db,
                    obj_in=TaskCreate(
                        title=(
                            f"Day {day_spec['day']} · {_strip(phase.get('label'))}"
                            f" - {self._task_title_focus(day_spec)}"
                        ),
                        type=coerce_task_type(_task_type_for_day_spec(day_spec)),
                        plan_id=plan.id,
                        estimated_minutes=max(
                            _safe_int(day_spec.get("estimated_minutes"))
                            or (_safe_int(phase.get("daily_hours")) or daily_hours) * 60,
                            min_estimated_minutes,
                        ),
                        difficulty=min(
                            5,
                            self._mastery_to_difficulty(session.collected.get("avg_mastery_score"), index)
                            + (1 if day_spec.get("galaxy_weak") or day_spec.get("previous_exam_weak") else 0),
                        ),
                        energy_cost=self._mastery_to_difficulty(session.collected.get("avg_mastery_score"), index),
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
                            _strip(sprint_policy.get("sprint_mode") or "exam_sprint"),
                            _strip(day_spec.get("task_kind") or "retrieval"),
                        ],
                    ),
                    user_id=user_id,
                )
                task.order_index = int(day_spec["day"]) * 1000 + (_safe_int(day_spec.get("order_index_offset")) or 0)
                created_tasks.append(task)
        if created_tasks:
            first_day_tasks = [
                task for task in created_tasks if int(task.order_index or 0) // 1000 == 1
            ] or created_tasks[:1]
            material_context = _as_dict(session.collected.get("study_material_context"))
            material_gaps = self._dedupe_text(
                [
                    _strip(_as_dict(task.guide_json).get("material_gap"))
                    for task in created_tasks
                    if _strip(_as_dict(task.guide_json).get("material_gap"))
                ],
                limit=6,
            )
            if last_24h_mode:
                recommendation = "今天不再学新内容：先过高频知识点，再按错因回看错题，最后完成 30 分钟短模拟。"
            else:
                recommendation = await self._build_first_day_recommendation(
                    session=session,
                    subject=subject,
                    tasks=first_day_tasks,
                )
            plan.source_metadata = {
                **_as_dict(plan.source_metadata),
                "day_highlights": {
                    "day": 1,
                    "recommendation": recommendation,
                },
                "study_materials": {
                    "available_materials": list(material_context.get("available_materials") or []),
                    "documents": list(material_context.get("documents") or [])[:5],
                    "material_gaps": material_gaps,
                },
            }
            if last_24h_mode:
                plan.source_metadata.update(
                    {
                        "last_24h_mode": True,
                        "last_24h_strategy": _as_dict(sprint_policy.get("last_24h_strategy")),
                        "last_24h_error_clusters": last_24h_error_clusters,
                    }
                )
            await db.commit()

        session.state = "DONE"
        await self.save_session(session)
        runtime_state.current_intent = {"intent_type": "wait", "target_tension_id": None, "payload": {}}
        await self.runtime_adapter.save_state(runtime_state, db=db)
        return {
            "message": "方案已经确认，我先把今天聚焦成第一天任务；后面的 Day 2–7 可以在计划详情里展开看。",
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

    async def _insert_repair_task(
        self,
        *,
        db: AsyncSession,
        plan_id: UUID,
        next_day: int | date | datetime | None,
        error_node_id: UUID | str,
        error_cause_category: str | None,
    ) -> Task | None:
        """Insert or merge a short next-day repair task for a fresh error signal."""
        plan = await db.get(Plan, plan_id)
        if plan is None:
            return None

        day_number, due_date = self._normalize_repair_day(next_day)
        node_uuid = _coerce_uuid(error_node_id)
        node_label = await self._repair_node_label(
            db=db,
            subject=_strip(plan.subject),
            error_node_id=error_node_id,
            node_uuid=node_uuid,
        )
        node_ref = str(node_uuid or error_node_id)
        title = f"修复昨日错题：{node_label}"
        output_action = "闭卷复述错因 + 1 道同类题独立完成"
        repair_spec = {
            "day": day_number,
            "focus": title,
            "task_kind": "targeted_repair",
            "title_focus": node_label,
            "estimated_minutes": 15,
            "node_id": node_ref,
            "knowledge_node_ids": [node_ref],
            "error_cause_category": _strip(error_cause_category) or "unknown",
            "priority": "highest",
            "output_action": output_action,
        }
        repair_guide = self._build_repair_task_guide_json(
            node_label=node_label,
            node_ref=node_ref,
            error_cause_category=error_cause_category,
            daily_spec=repair_spec,
        )

        plan_tasks = list(
            (
                await db.execute(
                    select(Task)
                    .where(Task.plan_id == plan.id, Task.user_id == plan.user_id)
                    .where(Task.status.in_((TaskStatus.PENDING, TaskStatus.IN_PROGRESS)))
                    .order_by(Task.order_index.asc(), Task.created_at.asc())
                )
            )
            .scalars()
            .all()
        )
        task_ids = [task.id for task in plan_tasks]
        linked_node_refs = await self._linked_node_refs_for_tasks(db=db, task_ids=task_ids)
        day_tasks = [
            task for task in plan_tasks if self._task_matches_repair_day(task, day_number=day_number, due_date=due_date)
        ]

        existing = next(
            (
                task
                for task in day_tasks
                if self._task_refs_node(
                    task,
                    node_ref=node_ref,
                    node_uuid=node_uuid,
                    linked_node_refs=linked_node_refs.get(task.id, set()),
                )
            ),
            None,
        )

        if existing is not None:
            await self._move_task_to_first_slot(
                db=db,
                tasks=day_tasks,
                target_task=existing,
                day_number=day_number,
            )
            self._apply_repair_task_payload(
                existing,
                title=title,
                day_number=day_number,
                due_date=due_date,
                node_uuid=node_uuid,
                tags=self._repair_task_tags(day_number, node_ref, error_cause_category),
                guide_json=repair_guide,
            )
            await self._ensure_repair_task_link(db=db, task=existing, node_uuid=node_uuid)
            await db.commit()
            await db.refresh(existing)
            return existing

        await self._shift_day_tasks_for_insert(db=db, tasks=day_tasks, day_number=day_number)
        task = await TaskService.create(
            db=db,
            obj_in=TaskCreate(
                title=title,
                type=coerce_task_type("error_fix"),
                plan_id=plan.id,
                tags=self._repair_task_tags(day_number, node_ref, error_cause_category),
                estimated_minutes=15,
                difficulty=2,
                energy_cost=1,
                guide_content=repair_guide["objective"],
                guide_json=repair_guide,
                ai_prompt=self._build_repair_task_ai_prompt(
                    subject=_strip(plan.subject) or "当前科目",
                    node_label=node_label,
                    error_cause_category=error_cause_category,
                    output_action=output_action,
                ),
                priority=100,
                due_date=due_date,
                knowledge_node_id=node_uuid,
                success_criteria=repair_guide["success_criteria"],
            ),
            user_id=plan.user_id,
        )
        task.order_index = day_number * 1000
        await self._ensure_repair_task_link(db=db, task=task, node_uuid=node_uuid)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    def _normalize_repair_day(next_day: int | date | datetime | None) -> tuple[int, date | None]:
        if isinstance(next_day, datetime):
            return 2, next_day.date()
        if isinstance(next_day, date):
            return 2, next_day
        day_number = _safe_int(next_day) or 2
        return max(day_number, 1), (_utcnow() + timedelta(days=1)).date()

    async def _repair_node_label(
        self,
        *,
        db: AsyncSession,
        subject: str,
        error_node_id: UUID | str,
        node_uuid: UUID | None,
    ) -> str:
        if node_uuid is not None:
            node = await db.get(KnowledgeNode, node_uuid)
            if node is not None and _strip(node.name):
                return _strip(node.name)

        node_ref = _strip(error_node_id)
        pack_label = self._pack_node_label(subject=subject, node_ref=node_ref)
        if pack_label:
            return pack_label
        if node_ref == "cn.tcp_flow":
            return "TCP 滑动窗口机制"
        if node_ref:
            return node_ref
        return "这个知识点"

    @staticmethod
    def _pack_node_label(*, subject: str, node_ref: str) -> str:
        if not node_ref:
            return ""
        lookup_ref = "cn.tcp_flow_control" if node_ref == "cn.tcp_flow" else node_ref
        pack = load_pack(subject or "计算机网络")
        if not pack:
            return ""
        for node in pack.get("knowledge_nodes", []):
            if _strip(node.get("node_id")) == lookup_ref:
                label = _strip(node.get("label"))
                if node_ref == "cn.tcp_flow":
                    return "TCP 滑动窗口机制"
                return label
        return ""

    @staticmethod
    def _build_repair_task_guide_json(
        *,
        node_label: str,
        node_ref: str,
        error_cause_category: str | None,
        daily_spec: dict[str, Any],
    ) -> dict[str, Any]:
        output_action = "闭卷复述错因 + 1 道同类题独立完成"
        cause = _strip(error_cause_category) or "unknown"
        return {
            "objective": f"用 15 分钟修复昨日错题：{node_label}。",
            "method_steps": [
                "先不看资料，闭卷说出昨天为什么错。",
                "把错因压成一句提醒语，并写出下次遇到同类题的判断步骤。",
                "独立完成 1 道同类题；做完后再对答案。",
            ],
            "time_estimate_minutes": 15,
            "estimated_minutes": 15,
            "output_action": output_action,
            "success_criteria": "能闭卷说清错因，并独立做对 1 道同类题。",
            "key_points": [node_label, f"错因类型：{cause}", output_action],
            "common_mistakes": ["把补强任务做成重新学一遍，导致真正的错因没有被修掉。"],
            "retrieval_first": True,
            "task_kind": "targeted_repair",
            "repair_node_id": node_ref,
            "knowledge_node_ids": [node_ref],
            "error_cause_category": cause,
            "minimum_output": output_action,
            "micro_contract": "如果开始，就只修昨天暴露的一个错因，不扩展新内容。",
            "success_checklist": ["闭卷说清错因", "写出下次判断步骤", "独立完成 1 道同类题"],
            "fail_safe_rule": "如果只剩 5 分钟，就保留闭卷错因复述和一句提醒语。",
            "why_now": f"昨天在「{node_label}」上暴露的漏洞现在最适合短补强，先修错因比重新铺开学习更省力。",
            "daily_spec": daily_spec,
        }

    @staticmethod
    def _build_repair_task_ai_prompt(
        *,
        subject: str,
        node_label: str,
        error_cause_category: str | None,
        output_action: str,
    ) -> str:
        cause = _strip(error_cause_category) or "unknown"
        return (
            f"【背景】我在 {subject} 的「{node_label}」上昨天做错了一题，错因类型是 {cause}。\n"
            "【目标】不要重新学完整章节，只做 15 分钟 targeted repair。\n"
            f"【输出动作】{output_action}。\n"
            "请先问我一个闭卷复述问题，再给 1 道同类题，不要直接给答案。"
        )

    @staticmethod
    def _repair_task_tags(day_number: int, node_ref: str, error_cause_category: str | None) -> list[str]:
        return [
            "规划生成",
            "错题补强",
            "targeted_repair",
            f"day:{day_number}",
            f"repair_node:{node_ref}",
            f"error_cause:{_strip(error_cause_category) or 'unknown'}",
        ]

    @staticmethod
    def _task_day_from_task(task: Task) -> int:
        try:
            order_value = int(task.order_index or 0)
        except (TypeError, ValueError):
            order_value = 0
        if order_value >= 1000:
            return max(1, order_value // 1000)
        for tag in list(task.tags or []):
            text = _strip(tag)
            if not text.startswith("day:"):
                continue
            parsed = _safe_int(text.split(":", 1)[1])
            if parsed:
                return parsed
        return 1

    def _task_matches_repair_day(self, task: Task, *, day_number: int, due_date: date | None) -> bool:
        if self._task_day_from_task(task) == day_number:
            return True
        return due_date is not None and task.due_date == due_date

    @staticmethod
    async def _linked_node_refs_for_tasks(
        *,
        db: AsyncSession,
        task_ids: list[UUID],
    ) -> dict[UUID, set[str]]:
        if not task_ids:
            return {}
        rows = (
            await db.execute(
                select(TaskKnowledgeLink.task_id, TaskKnowledgeLink.knowledge_node_id).where(
                    TaskKnowledgeLink.task_id.in_(task_ids)
                )
            )
        ).all()
        refs: dict[UUID, set[str]] = {}
        for task_id, node_id in rows:
            refs.setdefault(task_id, set()).add(str(node_id))
        return refs

    @staticmethod
    def _task_refs_node(
        task: Task,
        *,
        node_ref: str,
        node_uuid: UUID | None,
        linked_node_refs: set[str],
    ) -> bool:
        candidates = {node_ref, *linked_node_refs}
        if node_uuid is not None:
            candidates.add(str(node_uuid))
            if task.knowledge_node_id == node_uuid:
                return True
        guide = _as_dict(task.guide_json)
        nested_daily_spec = _as_dict(guide.get("daily_spec"))
        for value in (
            guide.get("repair_node_id"),
            guide.get("node_id"),
            nested_daily_spec.get("node_id"),
        ):
            if _strip(value) in candidates:
                return True
        for raw_list in (
            guide.get("knowledge_node_ids"),
            nested_daily_spec.get("knowledge_node_ids"),
            _as_dict(guide.get("subject_strategy")).get("node_ids"),
        ):
            if any(_strip(item) in candidates for item in _listish(raw_list)):
                return True
        return False

    @staticmethod
    async def _shift_day_tasks_for_insert(
        *,
        db: AsyncSession,
        tasks: list[Task],
        day_number: int,
    ) -> None:
        base_order = day_number * 1000
        for task in sorted(tasks, key=lambda item: int(item.order_index or 0), reverse=True):
            if int(task.order_index or 0) >= base_order:
                task.order_index = int(task.order_index or 0) + 1
        await db.flush()

    async def _move_task_to_first_slot(
        self,
        *,
        db: AsyncSession,
        tasks: list[Task],
        target_task: Task,
        day_number: int,
    ) -> None:
        base_order = day_number * 1000
        if int(target_task.order_index or 0) == base_order:
            return
        for task in sorted(tasks, key=lambda item: int(item.order_index or 0), reverse=True):
            if task.id == target_task.id:
                continue
            if int(task.order_index or 0) >= base_order:
                task.order_index = int(task.order_index or 0) + 1
        target_task.order_index = base_order
        await db.flush()

    @staticmethod
    def _apply_repair_task_payload(
        task: Task,
        *,
        title: str,
        day_number: int,
        due_date: date | None,
        node_uuid: UUID | None,
        tags: list[str],
        guide_json: dict[str, Any],
    ) -> None:
        task.title = title[:255]
        task.type = coerce_task_type("error_fix")
        task.tags = tags
        task.estimated_minutes = 15
        task.difficulty = min(int(task.difficulty or 2), 2)
        task.energy_cost = 1
        task.priority = max(int(task.priority or 0), 100)
        task.due_date = due_date
        task.knowledge_node_id = node_uuid or task.knowledge_node_id
        task.guide_content = guide_json["objective"]
        task.guide_json = guide_json
        task.success_criteria = guide_json["success_criteria"]
        task.order_index = day_number * 1000

    @staticmethod
    async def _ensure_repair_task_link(
        *,
        db: AsyncSession,
        task: Task,
        node_uuid: UUID | None,
    ) -> None:
        if node_uuid is None:
            return
        existing = (
            await db.execute(
                select(TaskKnowledgeLink).where(
                    TaskKnowledgeLink.task_id == task.id,
                    TaskKnowledgeLink.knowledge_node_id == node_uuid,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            return
        db.add(
            TaskKnowledgeLink(
                task_id=task.id,
                knowledge_node_id=node_uuid,
                relation_type="repair_focus",
                is_primary=True,
            )
        )
        await db.flush()

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
            if self.is_fast_track_exam_sprint_session(session):
                return True
            return bool(_strip(session.collected.get(self.MOTIVATION_FIELD) or session.collected.get("motivation")))
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
            return any(_strip(collected.get(field)) for field in self.CLARIFYING_FIELDS)
        if session.state in {"AWAITING_CONFIRM", "PLANNING", "STRATEGY_REVISION"}:
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
        if not _strip(session.collected.get(self.MOTIVATION_FIELD) or session.collected.get("motivation")):
            return "最后一个问题：这次考试对你来说意味着什么？是一定要过还是想尽量考高分？"
        return "你接下来这几天每天大概能拿出多少时间？有没有哪几天会特别忙或者完全学不了？"

    @staticmethod
    def _extract_motivation_context(text: str) -> str:
        lowered = _strip(text).lower()
        if not lowered:
            return ""
        if any(token in lowered for token in ("必须过", "一定要过", "不能挂", "不挂科", "不想挂", "保底", "过线")):
            return "必须过"
        if any(token in lowered for token in ("想拿高分", "尽量考高分", "考高分", "冲高分", "高分", "拿高分")):
            return "想拿高分"
        if any(token in lowered for token in ("探索兴趣", "探索", "兴趣", "想了解")):
            return "探索兴趣"
        return ""

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
        motivation = self._extract_motivation_context(text)
        if motivation:
            collected["motivation_context"] = motivation
            collected["motivation"] = motivation
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

        if task_kind == "compressed_recovery":
            return {
                "objective": objective,
                "output_action": f"围绕 1 个核心点完成 {minimum_output}。",
                "success_criteria": f"完成 {minimum_output}，今天就算把主线接回来了。",
                "micro_contract": "如果开始，就只做这 1 个核心任务；完成前不追加第二个任务。",
                "fail_safe_rule": "进度落后时只保留 1 个核心任务和 1 个最小输出。",
                "success_checklist": ["只有 1 个核心任务", "有 1 个最小输出", "没有追加可选任务"],
                "method_steps": [
                    "先锁定今天唯一的核心点。",
                    f"只完成这个最小输出：{minimum_output}。",
                    "结束时写一句明天从哪里继续。",
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

    @staticmethod
    def _material_match_keys(values: list[Any]) -> list[str]:
        keys: list[str] = []
        for raw in values:
            text = _strip(raw).lower()
            if not text:
                continue
            parts = re.findall(r"[a-z0-9_]+|[\u4e00-\u9fff]+", text)
            for candidate in [text, *parts]:
                normalized = candidate.strip("_ ").lower()
                if len(normalized) < 2 or normalized in keys:
                    continue
                keys.append(normalized)
        return keys

    def _material_text_score(self, text: Any, query_keys: list[str]) -> int:
        haystack = _strip(text).lower()
        if not haystack or not query_keys:
            return 0
        score = 0
        haystack_keys = self._material_match_keys([haystack])
        for key in query_keys:
            if key in haystack:
                score += 3
                continue
            if any(key == hay_key or key in hay_key or hay_key in key for hay_key in haystack_keys):
                score += 2
        return score

    def _material_anchor_from_attachment(
        self,
        *,
        doc: dict[str, Any],
        attachment: dict[str, Any],
        section_lookup: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        section_titles = [_strip(item) for item in list(attachment.get("section_titles") or []) if _strip(item)]
        chapter_ref = section_titles[0] if section_titles else _strip(attachment.get("node_name"))
        section_meta = _as_dict(section_lookup.get(chapter_ref))
        estimated_minutes = _safe_int(section_meta.get("estimated_read_minutes")) or _safe_int(
            attachment.get("estimated_read_minutes")
        )
        return {
            "file_id": _strip(doc.get("file_id")),
            "file_name": _strip(doc.get("file_name")),
            "chapter_ref": chapter_ref,
            "node_id": _strip(attachment.get("node_id")),
            "node_name": _strip(attachment.get("node_name")),
            "mastery_score": attachment.get("mastery_score"),
            "estimated_read_minutes": estimated_minutes,
            "page_numbers": list(section_meta.get("page_numbers") or []),
            "chunk_count": _safe_int(section_meta.get("chunk_count")) or _safe_int(attachment.get("chunk_count")) or 0,
        }

    def _material_anchor_from_section(self, *, doc: dict[str, Any], section: dict[str, Any]) -> dict[str, Any]:
        return {
            "file_id": _strip(doc.get("file_id")),
            "file_name": _strip(doc.get("file_name")),
            "chapter_ref": _strip(section.get("section_title")),
            "node_id": "",
            "node_name": "",
            "mastery_score": None,
            "estimated_read_minutes": _safe_int(section.get("estimated_read_minutes")) or 0,
            "page_numbers": list(section.get("page_numbers") or []),
            "chunk_count": _safe_int(section.get("chunk_count")) or 0,
        }

    def _material_anchor_score(
        self,
        *,
        anchor: dict[str, Any],
        query_keys: list[str],
        doc_preferred: bool,
    ) -> int:
        score = 4 if doc_preferred else 0
        score += self._material_text_score(anchor.get("node_name"), query_keys) * 5
        score += self._material_text_score(anchor.get("chapter_ref"), query_keys) * 4
        score += self._material_text_score(anchor.get("file_name"), query_keys)
        mastery = _optional_float(anchor.get("mastery_score"))
        if mastery is not None:
            score += max(0, int(round((100.0 - mastery) / 10.0)))
        if _safe_int(anchor.get("estimated_read_minutes")):
            score += 1
        return score

    def _build_material_anchors_for_spec(
        self,
        *,
        session: PlanningSession,
        spec: dict[str, Any],
        phase: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str | None]:
        material_context = _as_dict(session.collected.get("study_material_context"))
        documents = [
            dict(item)
            for item in list(material_context.get("documents") or [])
            if isinstance(item, dict) and _strip(item.get("file_name"))
        ]
        if not documents:
            return [], None

        subject_strategy = _as_dict(spec.get("subject_strategy"))
        topic_values = [
            spec.get("title_focus"),
            spec.get("focus"),
            phase.get("focus"),
            subject_strategy.get("primary_node_label"),
            *list(subject_strategy.get("node_labels") or []),
            session.collected.get("subject"),
            session.collected.get("exam_scope"),
        ]
        query_keys = self._material_match_keys(topic_values)
        if not query_keys:
            query_keys = self._material_match_keys([session.goal_raw])

        candidates: list[dict[str, Any]] = []
        for doc in documents:
            section_lookup = {
                _strip(section.get("section_title")): dict(section)
                for section in list(doc.get("sections") or [])
                if isinstance(section, dict) and _strip(section.get("section_title"))
            }
            preferred = bool(doc.get("preferred"))
            for attachment in list(doc.get("node_attachments") or []):
                if not isinstance(attachment, dict):
                    continue
                anchor = self._material_anchor_from_attachment(doc=doc, attachment=attachment, section_lookup=section_lookup)
                score = self._material_anchor_score(anchor=anchor, query_keys=query_keys, doc_preferred=preferred)
                if score <= 0:
                    continue
                candidates.append({**anchor, "score": score})

            for section in list(doc.get("sections") or []):
                if not isinstance(section, dict):
                    continue
                anchor = self._material_anchor_from_section(doc=doc, section=section)
                score = self._material_anchor_score(anchor=anchor, query_keys=query_keys, doc_preferred=preferred)
                if score <= 0:
                    continue
                candidates.append({**anchor, "score": score})

        if not candidates and len(documents) == 1:
            doc = documents[0]
            first_section = next(
                (
                    dict(section)
                    for section in list(doc.get("sections") or [])
                    if isinstance(section, dict) and _strip(section.get("section_title"))
                ),
                None,
            )
            if first_section is not None:
                fallback_anchor = self._material_anchor_from_section(doc=doc, section=first_section)
                fallback_anchor["score"] = 1
                candidates.append(fallback_anchor)

        deduped: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str]] = set()
        for anchor in sorted(candidates, key=lambda item: (-int(item.get("score") or 0), _strip(item.get("chapter_ref")))):
            dedupe_key = (_strip(anchor.get("file_id")), _strip(anchor.get("chapter_ref")) or _strip(anchor.get("node_name")))
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            deduped.append(anchor)
            if len(deduped) >= 2:
                break

        if deduped:
            return deduped, None

        topic_summary = self._format_compact_list(
            [_strip(item) for item in list(subject_strategy.get("node_labels") or []) if _strip(item)]
        ) or _strip(spec.get("title_focus")) or _strip(spec.get("focus"))
        if topic_summary:
            return [], f"你上传的资料里还没有能直接覆盖 {topic_summary} 的章节材料。"
        return [], "你上传的资料还没有和今天任务直接对齐的章节材料。"

    def _attach_material_anchors_to_specs(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        annotated: list[dict[str, Any]] = []
        for raw_spec in specs:
            spec = dict(raw_spec)
            anchors, gap_note = self._build_material_anchors_for_spec(session=session, spec=spec, phase=phase)
            if anchors:
                spec["material_anchors"] = anchors
                spec["primary_material_anchor"] = anchors[0]
            if gap_note:
                spec["material_gap_note"] = gap_note
            annotated.append(spec)
        return annotated

    @staticmethod
    def _material_anchor_short_label(anchor: dict[str, Any]) -> str:
        file_name = _strip(anchor.get("file_name"))
        chapter_ref = _strip(anchor.get("chapter_ref"))
        if file_name and chapter_ref:
            return f"{file_name} · {chapter_ref}"
        return file_name or chapter_ref

    def _format_material_anchor(self, anchor: dict[str, Any]) -> str:
        label = self._material_anchor_short_label(anchor)
        minutes = _safe_int(anchor.get("estimated_read_minutes"))
        if label and minutes:
            return f"{label}（约 {minutes} 分钟）"
        return label

    def _task_title_focus(self, day_spec: dict[str, Any]) -> str:
        title_focus = _strip(day_spec.get("title_focus") or day_spec.get("task_kind") or "检索推进")
        primary_material = _as_dict(day_spec.get("primary_material_anchor"))
        material_label = self._material_anchor_short_label(primary_material)
        if material_label and material_label not in title_focus:
            return f"{title_focus}（{material_label}）"
        return title_focus

    @staticmethod
    def _build_why_this_task(
        *,
        node_labels: list[str],
        error_clusters: list[dict[str, Any]],
        pack_why_now: str | None,
        sprint_mode: str,
        focus: str | None,
        subject: str,
    ) -> str:
        why_parts: list[str] = []
        if node_labels:
            why_parts.append(f"直接针对考试高频节点：{'、'.join(node_labels[:4])}")
        if error_clusters:
            cluster_names = "、".join(_strip(e.get("label", "")) for e in error_clusters[:2] if _strip(e.get("label", "")))
            if cluster_names:
                why_parts.append(f"修复已发现的错因：{cluster_names}")
        if pack_why_now:
            why_parts.append(pack_why_now)
        if sprint_mode == "seven_day_survival":
            why_parts.append("七天冲刺模式，按收益/掌握度/可训练性排任务")
        elif sprint_mode == "fourteen_day_build_and_retrieve":
            why_parts.append("14天建基+检索模式，先建再测")
        if not why_parts:
            why_parts.append(f"推进 {(focus or subject)} 的阶段目标")
        return "；".join(why_parts)

    @staticmethod
    def _build_materials_protocol(
        *,
        primary_material: dict[str, Any],
        material_label: str,
        material_anchors: list[dict[str, Any]],
        materials: list[str],
        material_gap_note: str | None,
    ) -> dict[str, Any]:
        protocol: dict[str, Any] = {}
        if primary_material:
            protocol["primary"] = {"label": material_label, "anchor": primary_material}
        if material_anchors:
            protocol["anchors"] = material_anchors
        if materials:
            protocol["available"] = materials
        if material_gap_note:
            protocol["gap_note"] = material_gap_note
        return protocol

    @staticmethod
    def _build_updates_after_completion(
        *,
        sprint_mode: str,
        node_labels: list[str],
    ) -> list[str]:
        updates = [
            "knowledge_node_mastery",
            "error_cluster_counts",
            "achievement_streak",
            "galaxy_node_coverage",
        ]
        if sprint_mode == "seven_day_survival":
            updates.append("sprint_pack_progress")
        if node_labels:
            updates.append("node_mastery_scores")
        return updates

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
        subject_strategy = _as_dict((day_spec or {}).get("subject_strategy"))
        sprint_policy = _as_dict(phase.get("sprint_policy"))
        retrieval_policy = _as_dict(phase.get("retrieval_policy") or sprint_policy.get("retrieval_policy"))
        sprint_mode = _strip(sprint_policy.get("sprint_mode") or phase.get("sprint_mode") or "exam_sprint")
        minimum_output = _strip(
            (day_spec or {}).get("minimum_output") or retrieval_policy.get("minimum_output") or "闭卷复述或小测"
        )
        task_kind = _strip((day_spec or {}).get("task_kind") or "retrieval_drill")
        material_anchors = [
            dict(item)
            for item in list((day_spec or {}).get("material_anchors") or [])
            if isinstance(item, dict) and _strip(item.get("file_name") or item.get("chapter_ref"))
        ]
        primary_material = _as_dict((day_spec or {}).get("primary_material_anchor") or (material_anchors[0] if material_anchors else {}))
        material_gap_note = _strip((day_spec or {}).get("material_gap_note"))
        material_label = self._format_material_anchor(primary_material) if primary_material else ""
        contract = self._build_daily_task_contract(
            task_kind=task_kind,
            sprint_mode=sprint_mode,
            phase_label=_strip(phase.get("label") or "当前阶段"),
            focus=focus,
            output=output,
            minimum_output=minimum_output,
            day_number=day_number,
        )
        node_labels = [item for item in list(subject_strategy.get("node_labels") or []) if _strip(item)]
        related_archetypes = [item for item in list(subject_strategy.get("related_archetypes") or []) if _strip(item)]
        common_mistakes_to_watch = [
            item for item in list(subject_strategy.get("common_mistakes_to_watch") or []) if _strip(item)
        ]
        error_clusters = [
            dict(item)
            for item in list(subject_strategy.get("error_clusters") or [])
            if isinstance(item, dict) and _strip(item.get("label"))
        ]
        must_not_include = [
            _strip(item) for item in list(subject_strategy.get("must_not_include") or []) if _strip(item)
        ]
        pack_why_now = _strip(subject_strategy.get("why_now"))
        if task_kind == "diagnostic_triage":
            output_action = _strip((day_spec or {}).get("output_action")) or contract["output_action"]
        else:
            output_action = (
                _strip((day_spec or {}).get("output_action"))
                or _strip(subject_strategy.get("output_action"))
                or contract["output_action"]
            )
        # F19: Bridge seed library with sprint pack — recommend matching seeds as materials.
        seed_library_nodes = [nid for nid in list(session.collected.get("seed_library_nodes") or []) if _strip(nid)]
        if seed_library_nodes and focus:
            matched_seeds = _match_seed_nodes_to_focus(seed_library_nodes, focus)
            if matched_seeds:
                seed_names = "、".join(matched_seeds[:3])
                output_action = f"{output_action}（可使用你的种子库中的 {seed_names}）"
        if task_kind == "diagnostic_triage":
            success_criteria = _strip((day_spec or {}).get("success_criteria")) or contract["success_criteria"]
        else:
            success_criteria = (
                _strip((day_spec or {}).get("success_criteria"))
                or _strip(subject_strategy.get("success_criteria"))
                or contract["success_criteria"]
            )
        if _strip((day_spec or {}).get("objective")):
            objective = _strip((day_spec or {}).get("objective"))
        elif node_labels and task_kind != "diagnostic_triage":
            node_summary = self._format_compact_list(node_labels)
            objective = f"Day {day_number or '?'}：优先拿下 {node_summary} 这些考试收益最高的节点。"
        else:
            objective = contract["objective"]
        if material_label and material_label not in objective:
            objective = f"{objective} 直接对着你上传的 {material_label} 推进。"
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
        guide_steps = [
            _strip(item)
            for item in list((day_spec or {}).get("method_steps") or contract["method_steps"])
            if _strip(item)
        ]
        if node_labels:
            guide_steps.insert(0, f"今天优先节点：{self._format_compact_list(node_labels)}。")
        if material_label:
            guide_steps.insert(1 if node_labels else 0, f"优先材料锚点：{material_label}。")
        for action in [item for item in list(subject_strategy.get("recommended_actions") or []) if _strip(item)][:2]:
            action_line = action if action.endswith("。") else f"{action}。"
            guide_steps.insert(len(guide_steps), action_line)
        if error_clusters:
            cluster_line = "、".join(
                f"{_strip(item.get('label'))} x{int(item.get('count') or 0)}" for item in error_clusters[:3]
            )
            guide_steps.insert(len(guide_steps), f"优先回看这些高频错因：{cluster_line}。")
        if related_archetypes:
            guide_steps.append(f"最后用这些高频题型回测：{'、'.join(related_archetypes[:3])}。")
        if materials:
            guide_steps.insert(1, f"优先使用你手头已有的资料：{'、'.join(materials[:3])}。")
        guide_steps.insert(
            min(2, len(guide_steps)),
            f"执行时只围绕今天这一个明确产出动作推进：{output_action}",
        )
        if material_gap_note:
            guide_steps.append(material_gap_note if material_gap_note.endswith("。") else f"{material_gap_note}。")
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
            output_action,
            success_criteria,
            f"检索优先：{minimum_output}",
        ]
        if node_labels:
            key_points.append(f"今天覆盖节点：{self._format_compact_list(node_labels)}")
        if related_archetypes:
            key_points.append(f"重点题型：{'、'.join(related_archetypes[:2])}")
        if error_clusters:
            key_points.append(
                "错因聚类："
                + "、".join(
                    f"{_strip(item.get('label'))} x{int(item.get('count') or 0)}" for item in error_clusters[:2]
                )
            )
        if materials:
            key_points.append(f"优先吃透手头资料里的高频材料：{'、'.join(materials[:2])}")
        if material_label:
            key_points.append(f"材料锚点：{material_label}")
        if material_gap_note:
            key_points.append(material_gap_note)
        if session.bottlenecks:
            key_points.extend(
                _strip(item.get("description")) for item in session.bottlenecks[:1] if _strip(item.get("description"))
            )
        common_mistakes = [
            _strip(item.get("specific_risk"))
            for item in (session.bottlenecks or [])[:2]
            if _strip(item.get("specific_risk"))
        ]
        if common_mistakes_to_watch:
            common_mistakes = common_mistakes_to_watch
        if not common_mistakes:
            common_mistakes = ["只看内容不做自测，最后很难知道自己到底会不会。"]
        guide_json = {
            "objective": objective,
            "method_steps": guide_steps,
            "time_estimate_minutes": _safe_int((day_spec or {}).get("estimated_minutes")) or max(phase_hours * 60, 30),
            "output_action": output_action,
            "success_criteria": success_criteria,
            "key_points": key_points,
            "common_mistakes": common_mistakes,
            "retrieval_first": True,
            "sprint_mode": sprint_mode,
            "task_kind": task_kind,
            "minimum_output": minimum_output,
            "micro_contract": contract["micro_contract"],
            "success_checklist": contract["success_checklist"],
            "fail_safe_rule": _strip((day_spec or {}).get("fail_safe_rule")) or contract["fail_safe_rule"],
            # ── P0-3: Task card 8-field protocol ──────────────────────
            "why_this_task": self._build_why_this_task(
                node_labels=node_labels,
                error_clusters=error_clusters,
                pack_why_now=pack_why_now,
                sprint_mode=sprint_mode,
                focus=focus,
                subject=subject,
            ),
            "materials_protocol": self._build_materials_protocol(
                primary_material=primary_material,
                material_label=material_label,
                material_anchors=material_anchors,
                materials=materials,
                material_gap_note=material_gap_note,
            ),
            "stuck_protocol": {
                "cant_understand_rules": {
                    "trigger": "用户反馈看不懂规则/概念",
                    "action": "graph_only",
                    "retrieval": "source_slice_definition",
                },
                "knows_rules_cant_solve": {
                    "trigger": "会规则但不会做题",
                    "action": "worked_example",
                    "retrieval": "mistake_cluster",
                },
                "cant_follow_steps": {
                    "trigger": "步骤跟不上",
                    "action": "step_by_step_trace",
                    "retrieval": None,
                },
                "not_enough_time": {
                    "trigger": "时间不够",
                    "action": "shrink_task",
                    "retrieval": None,
                },
                "low_state": {
                    "trigger": "状态不行/情绪低落",
                    "action": "recovery_task",
                    "retrieval": "affective_support",
                },
            },
            "updates_after_completion": self._build_updates_after_completion(
                sprint_mode=sprint_mode,
                node_labels=node_labels,
            ),
            "daily_spec": {
                key: value
                for key, value in dict(day_spec or {}).items()
                if key
                in {
                    "day",
                    "focus",
                    "title_focus",
                    "task_kind",
                    "estimated_minutes",
                    "minimum_output",
                    "primary_target",
                    "optional_tasks",
                    "compressed",
                    "compression_reason",
                    "scheduled_start_time",
                    "scheduled_end_time",
                    "calendar_avoidance",
                    "target_date",
                    "date",
                }
            },
        }
        if (day_spec or {}).get("calendar_avoidance"):
            guide_json["calendar_avoidance"] = _as_dict((day_spec or {}).get("calendar_avoidance"))
            guide_json["scheduled_start_time"] = _strip((day_spec or {}).get("scheduled_start_time"))
            guide_json["scheduled_end_time"] = _strip((day_spec or {}).get("scheduled_end_time"))
        if (day_spec or {}).get("compressed"):
            guide_json["compressed"] = True
            guide_json["compression_reason"] = _strip((day_spec or {}).get("compression_reason"))
            guide_json["primary_target"] = _strip((day_spec or {}).get("primary_target"))
            guide_json["optional_tasks"] = []
        if subject_strategy:
            guide_json["related_archetypes"] = related_archetypes
            guide_json["common_mistakes_to_watch"] = common_mistakes_to_watch
            guide_json["knowledge_nodes"] = node_labels
            guide_json["knowledge_node_ids"] = [
                item for item in list(subject_strategy.get("node_ids") or []) if _strip(item)
            ]
            guide_json["sprint_pack_nodes"] = [
                dict(item)
                for item in list((day_spec or {}).get("sprint_pack_nodes") or [])
                if isinstance(item, dict) and _strip(item.get("node_id"))
            ] or [
                {"node_id": node_id, "label": label}
                for node_id, label in zip(
                    list(subject_strategy.get("node_ids") or []),
                    list(subject_strategy.get("node_labels") or []),
                    strict=False,
                )
                if _strip(node_id)
            ]
            guide_json["path_mode"] = _strip(subject_strategy.get("path_mode"))
            guide_json["last_24h_mode"] = bool(subject_strategy.get("last_24h_mode"))
            if subject_strategy.get("review_mode"):
                guide_json["review_mode"] = _strip(subject_strategy.get("review_mode"))
            if subject_strategy.get("previous_mastery_summary"):
                guide_json["previous_mastery_summary"] = _as_dict(subject_strategy.get("previous_mastery_summary"))
            if error_clusters:
                guide_json["error_clusters"] = error_clusters
            if must_not_include:
                guide_json["must_not_include"] = must_not_include
            if subject_strategy.get("focus_nodes"):
                guide_json["focus_nodes"] = list(subject_strategy.get("focus_nodes") or [])
        if material_anchors:
            guide_json["material_anchors"] = material_anchors
            guide_json["primary_material"] = primary_material
            guide_json["material_coverage_status"] = "anchored"
        elif material_gap_note:
            guide_json["material_gap"] = material_gap_note
            guide_json["material_coverage_status"] = "gap"
        raw_weak_nodes = session.collected.get("galaxy_weak_nodes")
        if raw_weak_nodes is None:
            raw_weak_nodes = session.collected.get("weak_nodes")
        weak_nodes = [item for item in _listish(raw_weak_nodes) if item]
        previous_exam_weak_nodes = [
            item for item in _listish(session.collected.get("previous_exam_weak_nodes")) if item
        ]
        weak_nodes.extend(item for item in previous_exam_weak_nodes if item not in weak_nodes)
        if not weak_nodes and node_labels:
            weak_nodes = node_labels
        knowledge_state = {
            "overall_mastery": session.collected.get("avg_mastery_score"),
            "weak_nodes": weak_nodes,
            "recommended_path": _strip(session.collected.get("recommended_path") or guide_json.get("path_mode")),
        }
        aurora_control_signal = _as_dict(brief.get("activity_profile"))
        from app.orchestration.task_guide_enricher import TaskGuideEnricher

        _enricher = TaskGuideEnricher()
        enriched = _enricher.enrich_sync(
            guide_json=guide_json,
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            bottlenecks=session.bottlenecks,
            knowledge_state=knowledge_state,
            aurora_control_signal=aurora_control_signal,
        )
        if pack_why_now:
            enriched["why_now"] = pack_why_now
        return enriched

    async def _enrich_task_guide_with_ai(
        self,
        *,
        guide_json: dict[str, Any],
        session: PlanningSession,
        day_spec: dict[str, Any],
        subject: str,
    ) -> dict[str, Any]:
        from app.orchestration.task_guide_enricher import TaskGuideEnricher

        task_kind = _strip(day_spec.get("task_kind") or guide_json.get("task_kind") or "retrieval_drill")
        focus = _strip(day_spec.get("focus") or guide_json.get("objective"))
        return await TaskGuideEnricher().enrich(
            guide_json=guide_json,
            task_kind=task_kind,
            subject=subject,
            focus=focus,
            bottlenecks=session.bottlenecks,
            knowledge_state={
                "overall_mastery": session.collected.get("avg_mastery_score"),
                "weak_nodes": (
                    session.collected.get("galaxy_weak_nodes")
                    or session.collected.get("weak_nodes")
                    or session.collected.get("previous_exam_weak_nodes")
                    or []
                ),
                "recommended_path": _strip(session.collected.get("recommended_path")),
            },
            use_llm=True,
        )

    def _strategy_material_hints(self, *, session: PlanningSession, strategy: dict[str, Any]) -> list[str]:
        hints = [
            session.collected.get("subject"),
            session.collected.get("exam_scope"),
            session.goal_raw,
        ]
        for phase in list(strategy.get("phases") or []):
            if not isinstance(phase, dict):
                continue
            hints.extend(
                [
                    phase.get("focus"),
                    phase.get("label"),
                    phase.get("output"),
                ]
            )
        return [item for item in self._material_match_keys(hints) if item]

    async def _refresh_study_material_context(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        session: PlanningSession,
        strategy: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if db is None:
            return {}
        preferred_file_ids = [
            raw
            for raw in (
                _listish(session.collected.get("scope_file_ids"))
                + _listish(_as_dict(session.collected.get("cold_start_context")).get("scope_file_ids"))
            )
            if raw
        ]
        topic_hints = (
            self._strategy_material_hints(session=session, strategy=strategy or {})
            if strategy
            else self._material_match_keys(
                [
                    session.collected.get("subject"),
                    session.collected.get("exam_scope"),
                    session.goal_raw,
                ]
            )
        )

        summary = await GalaxyService(db).summarize_study_materials_for_planning(
            user_id=user_id,
            topic_hints=topic_hints,
            preferred_file_ids=preferred_file_ids,
        )
        session.collected["study_material_context"] = summary

        existing_materials = [_strip(item) for item in _listish(session.collected.get("available_materials")) if _strip(item)]
        for filename in list(summary.get("available_materials") or []):
            label = _strip(filename)
            if label and label not in existing_materials:
                existing_materials.append(label)
        if existing_materials:
            session.collected["available_materials"] = existing_materials
        return summary

    async def _build_first_day_recommendation(
        self,
        *,
        session: PlanningSession,
        subject: str,
        tasks: list[Task],
    ) -> str:
        fallback = self._first_day_recommendation_fallback(subject=subject, task_count=len(tasks))
        try:
            from app.services.llm_service import llm_service

            task_summaries = [
                {
                    "title": task.title,
                    "estimated_minutes": task.estimated_minutes,
                    "why_now": _as_dict(task.guide_json).get("why_now"),
                }
                for task in tasks[:4]
            ]
            result = await llm_service.reason_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个温和但务实的学习教练。为计划详情页生成一句第一天引导语。"
                            "只输出 JSON，不讲方法论，不制造压力。"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "goal": session.goal_raw,
                                "subject": subject,
                                "task_count": len(tasks),
                                "tasks": task_summaries,
                                "output_schema": {"recommendation": "一句话，鼓励用户今天只聚焦这些任务"},
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                temperature=0.4,
            )
            if isinstance(result, dict):
                recommendation = self._clean_short_sentence(result.get("recommendation")) or fallback
                return self._decorate_first_day_recommendation(session=session, recommendation=recommendation)
        except Exception as exc:
            logger.warning("first day recommendation LLM failed: {}", exc)
        return self._decorate_first_day_recommendation(session=session, recommendation=fallback)

    @staticmethod
    def _first_day_recommendation_fallback(*, subject: str, task_count: int) -> str:
        thing_label = f"这 {max(1, task_count)} 件事" if task_count != 1 else "这 1 件事"
        subject_label = _strip(subject)
        if subject_label:
            return f"今天先做好{thing_label}，{subject_label} 的第一步就稳下来了。"
        return f"今天先做好{thing_label}，你已经走在正确路上了。"

    def _decorate_first_day_recommendation(self, *, session: PlanningSession, recommendation: str) -> str:
        text = self._clean_short_sentence(recommendation)
        note = self._previous_exam_weak_recommendation_note(session)
        if not note:
            return text
        if not text:
            return note
        if note in text:
            return text
        return f"{note}{text}"

    def _previous_exam_weak_recommendation_note(self, session: PlanningSession) -> str:
        weak_nodes = [item for item in _listish(session.collected.get("previous_exam_weak_nodes")) if item]
        if not weak_nodes:
            return ""
        topic = self._previous_exam_weak_topic_label(weak_nodes)
        if not topic:
            return ""
        return f"根据你上次的考后复盘，{topic}需要额外加强，我已经把相关节点的优先级提高了。"

    def _previous_exam_weak_topic_label(self, weak_nodes: list[Any]) -> str:
        labels: list[str] = []
        raw_keys: list[str] = []
        for item in weak_nodes:
            payload = _as_dict(item)
            label = _strip(payload.get("node_name") or payload.get("label"))
            node_id = _strip(payload.get("node_id"))
            if label and label not in labels:
                labels.append(label)
            if node_id:
                raw_keys.append(self._pack_match_key(node_id))
            if label:
                raw_keys.append(self._pack_match_key(label))
        joined_keys = " ".join(raw_keys)
        if "tcp" in joined_keys:
            return "TCP 相关部分"
        if "udp" in joined_keys:
            return "UDP 相关部分"
        if len(labels) == 1:
            return f"{labels[0]}这部分"
        if len(labels) >= 2:
            return f"{'、'.join(labels[:2])}这些点"
        return ""

    @staticmethod
    def _clean_short_sentence(value: Any) -> str:
        text = _strip(value)
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        first_sentence = re.split(r"(?<=[。！？!?])", text, maxsplit=1)[0].strip()
        if first_sentence:
            text = first_sentence
        if len(text) > 80:
            text = text[:80].rstrip("，,；;：: ") + "。"
        if text[-1] not in "。！？!?":
            text = f"{text}。"
        return text

    @staticmethod
    def _build_motivation_tone_line(motivation: str) -> str:
        text = _strip(motivation)
        if not text:
            return ""
        if text == "必须过" or any(token in text for token in ("一定要过", "不能挂", "不挂科", "保底", "过线")):
            return "【角色语气】这是过线优先的保底规划：先稳住压力，任务必须留安全边际，优先必拿分、高频题和可检查输出，不做高风险加码。\n"
        if text == "想拿高分" or any(token in text for token in ("尽量考高分", "考高分", "冲高分", "高分")):
            return (
                "【角色语气】这是冲高分规划：语气可以更任务导向，核心稳定后允许 deep learn、拔高题和更细的错因追踪。\n"
            )
        if text == "探索兴趣" or any(token in text for token in ("探索", "兴趣", "想了解")):
            return "【角色语气】这是兴趣探索型规划：保持好奇和解释感，难度递进要轻，允许用例子帮我判断是否值得深入。\n"
        return "【角色语气】根据这个核心驱动调整语气和任务强度，先保证计划可执行，再决定是否加深。\n"

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
        motivation = _strip(session.collected.get("motivation_context") or session.collected.get("motivation"))
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
        motivation_tone_line = self._build_motivation_tone_line(motivation)
        output_action = _strip(guide_json.get("output_action"))
        micro_contract = _strip(guide_json.get("micro_contract"))
        fail_safe_rule = _strip(guide_json.get("fail_safe_rule"))
        must_not_include = [_strip(item) for item in list(guide_json.get("must_not_include") or []) if _strip(item)]
        last_24h_line = ""
        if guide_json.get("last_24h_mode"):
            last_24h_line = "【考前冲刺模式】今天不再学新内容，只做高频速览、错题回看和短模拟。\n"
        must_not_line = f"【禁止引入】{'、'.join(must_not_include[:4])}。\n" if must_not_include else ""
        history_summary = _as_dict(
            guide_json.get("previous_mastery_summary") or session.collected.get("cross_sprint_mastery_summary")
        )
        history_note = _strip(history_summary.get("history_note"))
        history_line = f"【历史掌握度】{history_note}\n" if history_note else ""
        return (
            f"【背景】我是学生，目标是 {session.goal_raw or f'在限定时间内完成 {subject} 备考'}。\n"
            f"{motivation_line}{motivation_tone_line}\n"
            f"【我的情况】科目是 {subject}，当前基础是 {baseline}，每天大概能投入 {daily_hours} 小时。\n"
            f"{materials_line}{blocked_days_line}{latent_line}{history_line}\n"
            f"{last_24h_line}{must_not_line}"
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
        seed_library_context = _as_dict(context.get("seed_library"))
        seed_library_nodes = _listish(
            seed_library_context.get("seed_library_nodes")
            or context.get("seed_library_nodes")
            or cold_start.get("seed_library_nodes")
            or []
        )
        knowledge_gaps = prefs.get(PLANNING_PROFILE_KEYS["knowledge_gaps"])
        galaxy_baseline = _as_dict(
            context.get("galaxy_baseline") or context.get("request_extra_context", {}).get("galaxy_baseline")
        )
        galaxy_avg = galaxy_baseline.get("avg_mastery") if galaxy_baseline else None
        galaxy_derived_baseline = self._classify_baseline_from_galaxy(galaxy_avg) if galaxy_avg is not None else None
        subject = _strip(cold_start.get("subject"))
        archive_weak_nodes = self._extract_previous_exam_weak_nodes(
            archive_payload=prefs.get(EXAM_SPRINT_GROWTH_ARCHIVE_KEY),
            subject=subject or _strip(cold_start.get("exam_scope")),
        )
        merged = {
            "goal_raw": _strip(cold_start.get("primary_goal_description")),
            "exam_scope": _strip(cold_start.get("exam_scope") or cold_start.get("subject")),
            "knowledge_baseline": _strip(cold_start.get("knowledge_baseline")) or galaxy_derived_baseline,
            "time_available": self._format_time_available(cold_start),
            "daily_available_hours": _safe_int(cold_start.get("daily_available_hours")),
            "blocked_days": cold_start.get("blocked_days") or [],
            "available_materials": cold_start.get("available_materials") or [],
            "subject": subject,
            "exam_date": _strip(cold_start.get("exam_date")),
            "time_constraint_days": _safe_int(cold_start.get("time_constraint_days")),
            "avg_mastery_score": galaxy_avg,
            "weak_nodes": galaxy_baseline.get("weak_nodes") if galaxy_baseline else None,
            "galaxy_weak_nodes": (
                cold_start.get("galaxy_weak_nodes") or (galaxy_baseline.get("weak_nodes") if galaxy_baseline else None)
            ),
            "diagnostic_estimated_score": cold_start.get("diagnostic_estimated_score"),
            "recommended_path": _strip(cold_start.get("recommended_path")),
            "sprint_pack_id": _strip(cold_start.get("sprint_pack_id")),
            "sprint_pack_subject": _strip(cold_start.get("sprint_pack_subject")),
            "pre_filled_domain_hints": cold_start.get("pre_filled_domain_hints") or [],
            EXAM_SPRINT_FAST_TRACK_FLAG: bool(cold_start.get(EXAM_SPRINT_FAST_TRACK_FLAG)),
            "knowledge_gaps": knowledge_gaps if isinstance(knowledge_gaps, list) else [],
            "motivation": _strip(
                cold_start.get("motivation")
                or cold_start.get("motivation_context")
                or cold_start.get("goal_motivation")
            ),
            "motivation_context": _strip(
                cold_start.get("motivation_context")
                or cold_start.get("motivation")
                or cold_start.get("goal_motivation")
            ),
            "seed_library_nodes": seed_library_nodes,
            "previous_exam_weak_nodes": cold_start.get("previous_exam_weak_nodes") or archive_weak_nodes,
            "cold_start_context": cold_start,
            "strongest_nodes": cold_start.get("strongest_nodes") or [],
            "persistent_weak_nodes": cold_start.get("persistent_weak_nodes") or [],
            "previous_sprint_summary": cold_start.get("previous_sprint_summary") or {},
            "mastery_snapshot": cold_start.get("mastery_snapshot") or {},
        }
        return {key: value for key, value in merged.items() if value not in (None, "", [], {})}

    async def _enrich_cross_sprint_mastery_from_galaxy(
        self,
        *,
        db: AsyncSession | None,
        user_id: UUID,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None,
    ) -> None:
        if db is None:
            return
        cold_start = self._session_cold_start_context(session, aurora_state=aurora_state)
        sprint_pack_id = _strip(cold_start.get("sprint_pack_id") or session.collected.get("sprint_pack_id"))
        has_history_hint = any(
            cold_start.get(key) not in (None, "", [], {})
            for key in (
                "previous_sprint_summary",
                "mastery_snapshot",
                "strongest_nodes",
                "persistent_weak_nodes",
                "galaxy_weak_nodes",
            )
        )
        if not sprint_pack_id or not has_history_hint:
            return

        pack_subject = _strip(cold_start.get("sprint_pack_subject"))
        version = "v1"
        if "@" in sprint_pack_id:
            pack_subject, version = sprint_pack_id.split("@", 1)
        subject = pack_subject or _strip(session.collected.get("subject") or session.collected.get("exam_scope"))
        pack = load_pack(subject, version)
        if not pack:
            return
        pack_node_ids = [
            _strip(node.get("node_id"))
            for node in list(pack.get("knowledge_nodes") or [])
            if isinstance(node, dict) and _strip(node.get("node_id"))
        ]
        if not pack_node_ids:
            return

        try:
            from app.services.galaxy_service import GalaxyService

            summary = await GalaxyService(db).get_sprint_mastery_rollup(
                user_id=user_id,
                pack_node_ids=pack_node_ids,
            )
        except Exception as exc:
            logger.warning("Failed to load cross-sprint mastery summary: {}", exc)
            return

        if summary.get("mastery_snapshot"):
            session.collected["galaxy_sprint_mastery_summary"] = summary

    async def _load_previous_exam_weak_nodes_for_session(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        session: PlanningSession,
        profile_context: dict[str, Any],
        message: str,
    ) -> list[dict[str, Any]]:
        subject = self._subject_for_growth_archive(session=session, message=message)
        if not subject:
            return []

        prefs = _as_dict(profile_context.get("preferences"))
        weak_nodes = self._extract_previous_exam_weak_nodes(
            archive_payload=prefs.get(EXAM_SPRINT_GROWTH_ARCHIVE_KEY),
            subject=subject,
        )
        if weak_nodes:
            return weak_nodes

        try:
            result = await db.execute(
                select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id)
            )
        except Exception as exc:
            logger.warning("Failed to load exam sprint growth archive for planning: {}", exc)
            return []
        explicit = result.scalar_one_or_none()
        if explicit is None:
            try:
                fallback_result = await db.execute(select(UserPreferencesCenter.user_id, UserPreferencesCenter.explicit))
                for pref_user_id, pref_explicit in fallback_result.all():
                    if str(pref_user_id) == str(user_id):
                        explicit = pref_explicit
                        break
            except Exception as exc:
                logger.warning("Fallback exam sprint growth archive lookup failed: {}", exc)
        explicit_payload = explicit if isinstance(explicit, dict) else {}
        return self._extract_previous_exam_weak_nodes(
            archive_payload=explicit_payload.get(EXAM_SPRINT_GROWTH_ARCHIVE_KEY),
            subject=subject,
        )

    def _subject_for_growth_archive(self, *, session: PlanningSession, message: str) -> str:
        collected = _as_dict(session.collected)
        subject = _strip(collected.get("subject") or collected.get("exam_scope"))
        if subject:
            return subject
        extracted = self._extract_clarifying_fields(message)
        subject = _strip(extracted.get("subject") or extracted.get("exam_scope"))
        if subject:
            return subject
        return _strip(session.goal_raw)

    def _extract_previous_exam_weak_nodes(
        self,
        *,
        archive_payload: Any,
        subject: str,
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        archive = _as_dict(archive_payload)
        entries = [entry for entry in list(archive.get("entries") or []) if isinstance(entry, dict)]
        if not entries or not _strip(subject):
            return []

        subject_key = self._subject_archive_key(subject)
        weak_nodes: list[dict[str, Any]] = []
        seen: set[str] = set()

        for entry in reversed(entries):
            entry_subject = _strip(entry.get("subject"))
            if subject_key and self._subject_archive_key(entry_subject) != subject_key:
                continue

            raw_nodes = list(entry.get("persistent_weak_nodes") or [])
            if not raw_nodes:
                raw_nodes = list(entry.get("underprepared_topics") or [])

            for raw in raw_nodes:
                node = _as_dict(raw)
                node_id = _strip(node.get("node_id"))
                node_name = _strip(node.get("node_name") or node.get("label") or node.get("title") or node_id)
                dedupe_key = node_id or self._pack_match_key(node_name)
                if not dedupe_key or dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                weak_nodes.append(
                    {
                        "node_id": node_id or None,
                        "node_name": node_name or node_id,
                        "source": node.get("source") or "exam_sprint_growth_archive",
                        "source_review_id": _strip(entry.get("review_id")),
                        "reviewed_at": _strip(entry.get("reviewed_at")),
                    }
                )
                if len(weak_nodes) >= limit:
                    return weak_nodes

        return weak_nodes

    def _subject_archive_key(self, subject: str) -> str:
        text = _strip(subject)
        if not text:
            return ""
        pack = load_pack(text)
        if pack:
            pack_id = _strip(pack.get("id"))
            if pack_id:
                return pack_id.split("@", 1)[0]
            pack_subject = _strip(pack.get("subject"))
            if pack_subject:
                return self._pack_match_key(pack_subject)
        return self._pack_match_key(text)

    async def _build_bottlenecks(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> list[dict[str, Any]]:
        from app.orchestration.bottleneck_analyzer import bottleneck_analyzer

        def _listish(value: Any) -> list[Any]:
            if value is None:
                return []
            if isinstance(value, list | tuple | set):
                return [item for item in value if _strip(item)]
            return [value] if _strip(value) else []

        def _safe_float(value: Any, default: float) -> float:
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                return default
            return parsed if parsed > 0 else default

        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "这门课")
        baseline = _strip(session.collected.get("knowledge_baseline") or "基础不稳")
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_float(session.collected.get("daily_available_hours"), 2.0)
        brief = self.runtime_adapter.build_strategy_brief(aurora_state) if aurora_state is not None else {}
        galaxy_baseline = session.collected.get("avg_mastery_score")
        if galaxy_baseline is not None and "掌握度" not in baseline:
            baseline = f"{baseline}；知识星图平均掌握度 {galaxy_baseline}"
        raw_weak_nodes = session.collected.get("galaxy_weak_nodes")
        if raw_weak_nodes is None:
            raw_weak_nodes = session.collected.get("weak_nodes")
        weak_nodes = _listish(raw_weak_nodes)
        weak_nodes.extend(
            item for item in _listish(session.collected.get("previous_exam_weak_nodes")) if item not in weak_nodes
        )
        blocked_days = [
            _strip(item) for item in _listish(brief.get("blocked_days") or session.collected.get("blocked_days"))
        ]
        materials = [
            _strip(item)
            for item in _listish(brief.get("available_materials") or session.collected.get("available_materials"))
        ]
        open_tensions = [_strip(item) for item in _listish(brief.get("open_tensions"))]
        analysis_kwargs = {
            "subject": subject,
            "knowledge_baseline": baseline,
            "time_constraint_days": days,
            "daily_available_hours": hours,
            "galaxy_weak_nodes": weak_nodes,
            "available_materials": materials,
            "blocked_days": blocked_days,
            "open_tensions": open_tensions,
        }

        try:
            analysis = await bottleneck_analyzer.analyze(**analysis_kwargs)
        except Exception as exc:
            logger.warning("_build_bottlenecks LLM analysis failed, using rule fallback: {}", exc)
            analysis = bottleneck_analyzer._rule_fallback(**analysis_kwargs)

        return [asdict(item) for item in analysis.bottlenecks]

    def _resolve_exam_date(self, session: PlanningSession) -> Any:
        cold_start = _as_dict(session.collected.get("cold_start_context"))
        return extract_exam_date(session.collected, cold_start)

    def _resolved_days_left(self, session: PlanningSession) -> int:
        exam_date = self._resolve_exam_date(session)
        resolved = calculate_days_left(exam_date)
        if resolved is not None:
            return max(resolved, 1)
        return _safe_int(session.collected.get("time_constraint_days")) or 7

    def _is_last_24h_mode(self, session: PlanningSession) -> bool:
        return is_last_24h_window(
            exam_date=self._resolve_exam_date(session),
            days_left=_safe_int(session.collected.get("time_constraint_days")),
        )

    async def _load_previous_exam_weak_nodes_for_session(
        self,
        *,
        db: AsyncSession | None,
        user_id: UUID,
        session: PlanningSession,
        profile_context: dict[str, Any] | None,
        message: str,
    ) -> list[Any]:
        subject = self._subject_for_growth_archive(session=session, message=message)
        prefs = _as_dict(_as_dict(profile_context or {}).get("preferences"))
        archive_weak_nodes = self._extract_previous_exam_weak_nodes(
            archive_payload=prefs.get(EXAM_SPRINT_GROWTH_ARCHIVE_KEY),
            subject=subject,
        )
        if archive_weak_nodes:
            return archive_weak_nodes
        if db is not None:
            try:
                result = await db.execute(
                    select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_id)
                )
                explicit_payloads = [payload for payload in result.scalars().all() if isinstance(payload, dict)]
            except Exception as exc:
                await db.rollback()
                logger.warning("Failed to load exam sprint growth archive for planning: {}", exc)
                explicit_payloads = []
            for explicit in explicit_payloads:
                archive_weak_nodes = self._extract_previous_exam_weak_nodes(
                    archive_payload=_as_dict(explicit).get(EXAM_SPRINT_GROWTH_ARCHIVE_KEY),
                    subject=subject,
                )
                if archive_weak_nodes:
                    return archive_weak_nodes

        cold_start = _as_dict(_as_dict(profile_context or {}).get("cold_start_context"))
        preference_cold_start = _as_dict(
            _as_dict(_as_dict(profile_context or {}).get("preferences")).get("cold_start_context")
        )
        seed_nodes: list[str] = []
        for source in (session.collected, cold_start, preference_cold_start):
            for key in (
                "previous_exam_weak_nodes",
                "persistent_weak_nodes",
                "confirmed_weak_nodes",
                "galaxy_weak_nodes",
                "weak_nodes",
            ):
                seed_nodes.extend(str(item) for item in _listish(source.get(key)) if _strip(item))
        if seed_nodes:
            return self._dedupe_text(seed_nodes, limit=12)
        if db is None:
            return []

        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or message)
        stmt = select(ErrorRecord).where(
            ErrorRecord.user_id == user_id,
            ErrorRecord.is_deleted.is_(False),
            ErrorRecord.mastery_level < 0.65,
        )
        subject_code = _subject_to_error_book_code(subject)
        if subject_code:
            stmt = stmt.where(ErrorRecord.subject_code == subject_code)
        stmt = stmt.order_by(
            ErrorRecord.mastery_level.asc(),
            ErrorRecord.next_review_at.asc().nullslast(),
            ErrorRecord.created_at.desc(),
        ).limit(24)

        try:
            records = (await db.execute(stmt)).scalars().all()
        except Exception as exc:
            await db.rollback()
            logger.warning("Failed to load previous exam weak nodes for user=%s error=%s", user_id, exc)
            return []

        weak_nodes: list[str] = []
        for record in records:
            if record.affected_node_id:
                weak_nodes.append(str(record.affected_node_id))
            weak_nodes.extend(str(item) for item in _listish(record.linked_knowledge_node_ids) if _strip(item))
            weak_nodes.extend(str(item) for item in _listish(record.suggested_concepts) if _strip(item))
            if record.chapter:
                weak_nodes.append(str(record.chapter))
        return self._dedupe_text(weak_nodes, limit=12)

    async def _load_last_24h_error_clusters(
        self,
        *,
        db: AsyncSession | None,
        user_id: UUID,
        subject: str,
    ) -> list[dict[str, Any]]:
        if db is None:
            return []

        stmt = select(ErrorRecord).where(
            ErrorRecord.user_id == user_id,
            ErrorRecord.is_deleted.is_(False),
        )
        subject_code = _subject_to_error_book_code(subject)
        if subject_code:
            stmt = stmt.where(ErrorRecord.subject_code == subject_code)
        stmt = stmt.order_by(
            ErrorRecord.next_review_at.asc().nullslast(),
            ErrorRecord.mastery_level.asc(),
            ErrorRecord.created_at.desc(),
        ).limit(40)

        records = (await db.execute(stmt)).scalars().all()
        if not records:
            return []

        grouped: dict[str, dict[str, Any]] = {}
        for record in records:
            analysis = _as_dict(record.latest_analysis)
            label = _strip(analysis.get("error_type_label") or analysis.get("error_type") or "高频错因")
            cluster = grouped.setdefault(
                label,
                {
                    "label": label,
                    "count": 0,
                    "chapters": [],
                    "focus_points": [],
                    "examples": [],
                    "lowest_mastery": 1.0,
                },
            )
            cluster["count"] += 1
            cluster["lowest_mastery"] = min(float(cluster["lowest_mastery"]), float(record.mastery_level or 0.0))

            chapter = _strip(record.chapter)
            if chapter and chapter not in cluster["chapters"] and len(cluster["chapters"]) < 3:
                cluster["chapters"].append(chapter)

            for focus_point in list(analysis.get("recommended_knowledge") or []):
                text = _strip(focus_point)
                if text and text not in cluster["focus_points"] and len(cluster["focus_points"]) < 4:
                    cluster["focus_points"].append(text)

            root_cause = _strip(analysis.get("root_cause"))
            if root_cause and root_cause not in cluster["examples"] and len(cluster["examples"]) < 2:
                cluster["examples"].append(root_cause[:80])

        clusters = sorted(
            grouped.values(),
            key=lambda item: (-int(item["count"]), float(item["lowest_mastery"]), _strip(item["label"])),
        )
        for cluster in clusters:
            chapters = list(cluster.get("chapters") or [])
            focus_points = list(cluster.get("focus_points") or [])
            focus_summary = "、".join(chapters[:2] or focus_points[:2])
            if focus_summary:
                cluster["focus_summary"] = focus_summary
            else:
                cluster["focus_summary"] = "回看最近最容易重复出错的题"
            cluster["lowest_mastery"] = int(round(float(cluster["lowest_mastery"]) * 100))
        return clusters[:3]

    def _build_exam_sprint_policy(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        days = self._resolved_days_left(session)
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
        payload = policy.to_dict()
        retrieval_policy = _as_dict(payload.get("retrieval_policy"))
        if retrieval_policy.get("fail_safe") and not payload.get("fail_safe"):
            payload["fail_safe"] = retrieval_policy.get("fail_safe")
        if retrieval_policy.get("minimum_output") and not payload.get("minimum_output"):
            payload["minimum_output"] = retrieval_policy.get("minimum_output")
        exam_date = self._resolve_exam_date(session)
        payload["days_left"] = days
        if exam_date is not None:
            payload["exam_date"] = exam_date.isoformat()
        if self._is_last_24h_mode(session):
            payload = apply_last_24h_policy_overrides(
                payload,
                subject=subject,
                exam_date=exam_date,
                days_left=days,
            )
        return payload

    def _build_strategy(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        # Phase II: replace this V1 rule template with LLM-backed strategy generation for non-demo domains.
        days = self._resolved_days_left(session)
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
        history_pack = load_pack(subject)
        history_summary = self._build_cross_sprint_mastery_summary(
            session,
            pack=history_pack,
            aurora_state=aurora_state,
        )
        if history_summary:
            session.collected["cross_sprint_mastery_summary"] = history_summary
        history_note = _strip(history_summary.get("history_note"))
        history_notes = [history_note] if history_note else []
        if sprint_policy.get("last_24h_mode"):
            last_24h_strategy = _as_dict(sprint_policy.get("last_24h_strategy"))
            focus_labels = [
                _strip(item.get("label") or item.get("node_id"))
                for item in list(last_24h_strategy.get("focus") or [])
                if isinstance(item, dict) and _strip(item.get("label") or item.get("node_id"))
            ]
            mock_exam = _as_dict(last_24h_strategy.get("mock_exam"))
            focus_summary = self._format_compact_list(focus_labels[:4]) if focus_labels else "高频高收益知识点"
            phase = {
                "phase": 1,
                "start_day": 1,
                "end_day": 1,
                "days": "Day 1",
                "label": "考前冲刺模式",
                "daily_hours": max(1, min(hours, 4)),
                "focus": f"今天不再学新内容，只复习 {focus_summary}，并把时间留给错题回看和短模拟。",
                "method": ("先做高频节点速览，再按错因聚类回看最近最容易丢分的题，最后用短模拟确认最后失分点。"),
                "output": (
                    f"完成一次高频速览、一次错题错因回看，以及 {mock_exam.get('duration_minutes') or 30} 分钟短模拟。"
                ),
                "sprint_mode": sprint_policy.get("sprint_mode"),
                "sprint_policy": sprint_policy,
                "retrieval_policy": sprint_policy.get("retrieval_policy") or {},
            }
            recommendation = "今天不再学新内容，只做高频速览、错题回看和 30 分钟短模拟。"
            return {
                "total_days": 1,
                "actual_days_left": days,
                "sprint_policy": sprint_policy,
                "daily_commitment_range": f"{max(1, min(hours, 4))}–{max(1, min(hours + 1, 4))}小时",
                "phases": [phase],
                "checkpoints": [
                    {
                        "day": 1,
                        "description": "今天结束前确认：高频节点是否还能闭卷提取，错题高频错因是否过了一轮，短模拟是否完成。",
                    },
                ],
                "adjustment_triggers": [
                    "如果高频速览时仍有大片空白，就继续压缩范围，只保留最常考和最容易补回的点。",
                    "如果短模拟暴露出重复错因，优先回看同类错题，不再切去新章节。",
                ],
                "strategy_notes": [
                    recommendation,
                    *history_notes,
                    *list(sprint_policy.get("strategy_notes") or []),
                ],
                "cross_sprint_mastery": history_summary,
                "user_context_digest": {
                    "goal_raw": _strip(session.goal_raw),
                    "blocked_days": blocked_days,
                    "available_materials": materials,
                    "open_tensions": open_tensions,
                    "latent_threads": latent_threads,
                    "cross_sprint_mastery": history_summary,
                },
                "aurora_brief": brief,
            }
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
            focus = template["focus"]
            if history_note and index == 1:
                focus = f"{focus} {history_note}"
            phases.append(
                {
                    "phase": index,
                    "start_day": day_range["start"],
                    "end_day": day_range["end"],
                    "days": self._format_day_range(day_range["start"], day_range["end"]),
                    "label": template["label"],
                    "daily_hours": max(1, hours + int(template["hour_delta"]) + density_delta),
                    "focus": focus,
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
            "strategy_notes": [*history_notes, *list(sprint_policy.get("strategy_notes") or [])],
            "cross_sprint_mastery": history_summary,
            "user_context_digest": {
                "goal_raw": _strip(session.goal_raw),
                "blocked_days": blocked_days,
                "available_materials": materials,
                "open_tensions": open_tensions,
                "latent_threads": latent_threads,
                "cross_sprint_mastery": history_summary,
            },
            "aurora_brief": brief,
        }

    def _phase_day_ranges(self, total_days: int) -> list[dict[str, int]]:
        days = max(1, int(total_days or 1))
        phase_count = 1 if days == 1 else 2 if days <= 4 else 3
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

    @staticmethod
    def _pack_match_key(value: Any) -> str:
        return re.sub(r"\s+", "", _strip(value).lower())

    @staticmethod
    def _normalize_mastery_ratio(value: Any) -> float | None:
        try:
            mastery = float(value)
        except (TypeError, ValueError):
            return None
        if mastery < 0:
            return None
        if mastery > 1.0:
            mastery = mastery / 100.0
        return max(0.0, min(mastery, 1.0))

    @staticmethod
    def _format_compact_list(items: list[str], *, limit: int = 3, suffix: str = "个点") -> str:
        cleaned = [_strip(item) for item in items if _strip(item)]
        if not cleaned:
            return ""
        if len(cleaned) <= limit:
            return "、".join(cleaned)
        return f"{'、'.join(cleaned[:limit])} 等{len(cleaned)}{suffix}"

    @staticmethod
    def _dedupe_text(items: list[str], *, limit: int = 4) -> list[str]:
        deduped: list[str] = []
        seen: set[str] = set()
        for item in items:
            text = _strip(item)
            if not text or text in seen:
                continue
            seen.add(text)
            deduped.append(text)
            if len(deduped) >= limit:
                break
        return deduped

    def _coerce_history_node_ids(self, value: Any) -> list[str]:
        node_ids: list[str] = []
        for item in _listish(value):
            if isinstance(item, dict):
                candidates = (
                    item.get("node_id"),
                    item.get("id"),
                    item.get("slug"),
                    item.get("node_slug"),
                    item.get("knowledge_node_id"),
                    item.get("value"),
                    item.get("name"),
                    item.get("label"),
                )
                node_id = next((_strip(candidate) for candidate in candidates if _strip(candidate)), "")
            else:
                node_id = _strip(item)
            if node_id and node_id not in node_ids:
                node_ids.append(node_id)
        return node_ids

    def _coerce_history_mastery_snapshot(self, value: Any) -> dict[str, float]:
        snapshot: dict[str, float] = {}
        if isinstance(value, dict):
            iterable = value.items()
            for raw_node_id, raw_mastery in iterable:
                node_id = _strip(raw_node_id)
                if isinstance(raw_mastery, dict):
                    node_id = _strip(
                        raw_mastery.get("node_id")
                        or raw_mastery.get("id")
                        or raw_mastery.get("slug")
                        or raw_mastery.get("node_slug")
                        or node_id
                    )
                    raw_mastery = (
                        raw_mastery.get("mastery")
                        or raw_mastery.get("mastery_score")
                        or raw_mastery.get("score")
                        or raw_mastery.get("current_mastery")
                    )
                mastery = self._normalize_mastery_ratio(raw_mastery)
                if node_id and mastery is not None:
                    snapshot[node_id] = mastery
            return snapshot

        for item in _listish(value):
            if not isinstance(item, dict):
                continue
            node_id = _strip(
                item.get("node_id")
                or item.get("id")
                or item.get("slug")
                or item.get("node_slug")
                or item.get("knowledge_node_id")
                or item.get("name")
                or item.get("label")
            )
            mastery = self._normalize_mastery_ratio(
                item.get("mastery")
                or item.get("mastery_score")
                or item.get("score")
                or item.get("current_mastery")
                or item.get("new_mastery")
            )
            if node_id and mastery is not None:
                snapshot[node_id] = mastery
        return snapshot

    def _session_cold_start_context(
        self,
        session: PlanningSession,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        cold_start: dict[str, Any] = {}
        if aurora_state is not None:
            state_cold_start = _as_dict(getattr(aurora_state, "cold_start_context", None))
            snapshot = _as_dict(getattr(aurora_state, "user_model_snapshot", None))
            prefs = _as_dict(snapshot.get("preferences"))
            for source in (
                _as_dict(prefs.get(PLANNING_PROFILE_KEYS["cold_start_context"])),
                _as_dict(snapshot.get("cold_start_context")),
                state_cold_start,
            ):
                for key, value in source.items():
                    if value not in (None, "", [], {}):
                        cold_start[key] = value
        for source in (
            _as_dict(session.collected.get("cold_start_context")),
            session.collected,
        ):
            for key in (
                "sprint_pack_id",
                "sprint_pack_subject",
                "galaxy_weak_nodes",
                "strongest_nodes",
                "persistent_weak_nodes",
                "previous_sprint_summary",
                "mastery_snapshot",
                "galaxy_sprint_mastery_summary",
                "sprint_mastery_summary",
            ):
                value = source.get(key)
                if value not in (None, "", [], {}):
                    cold_start[key] = value
        return cold_start

    def _build_cross_sprint_mastery_summary(
        self,
        session: PlanningSession,
        *,
        pack: dict[str, Any] | None = None,
        aurora_state: AuroraRuntimePlanningState | None = None,
    ) -> dict[str, Any]:
        cold_start = self._session_cold_start_context(session, aurora_state=aurora_state)
        previous_summary = _as_dict(cold_start.get("previous_sprint_summary"))
        service_summary = _as_dict(
            cold_start.get("galaxy_sprint_mastery_summary") or cold_start.get("sprint_mastery_summary")
        )
        strongest_nodes = self._dedupe_text(
            [
                *self._coerce_history_node_ids(previous_summary.get("strongest_nodes")),
                *self._coerce_history_node_ids(cold_start.get("strongest_nodes")),
                *self._coerce_history_node_ids(service_summary.get("strongest_nodes")),
            ],
            limit=20,
        )
        persistent_weak_nodes = self._dedupe_text(
            [
                *self._coerce_history_node_ids(previous_summary.get("persistent_weak_nodes")),
                *self._coerce_history_node_ids(cold_start.get("persistent_weak_nodes")),
                *self._coerce_history_node_ids(service_summary.get("persistent_weak_nodes")),
            ],
            limit=20,
        )
        mastery_snapshot: dict[str, float] = {}
        for raw_snapshot in (
            previous_summary.get("mastery_snapshot"),
            cold_start.get("mastery_snapshot"),
            service_summary.get("mastery_snapshot"),
        ):
            mastery_snapshot.update(self._coerce_history_mastery_snapshot(raw_snapshot))

        for node_id in strongest_nodes:
            mastery_snapshot.setdefault(node_id, 0.8)
        for node_id in persistent_weak_nodes:
            mastery_snapshot.setdefault(node_id, 0.25)

        pack_nodes = list((pack or {}).get("knowledge_nodes") or [])
        pack_node_ids = {
            _strip(node.get("node_id")) for node in pack_nodes if isinstance(node, dict) and _strip(node.get("node_id"))
        }
        if pack_node_ids:
            mastery_snapshot = {
                node_id: mastery for node_id, mastery in mastery_snapshot.items() if node_id in pack_node_ids
            }
            strongest_nodes = [node_id for node_id in strongest_nodes if node_id in pack_node_ids]
            persistent_weak_nodes = [node_id for node_id in persistent_weak_nodes if node_id in pack_node_ids]

        mastered_ids = [
            node_id for node_id, mastery in mastery_snapshot.items() if mastery > HISTORY_MASTERED_THRESHOLD
        ]
        weak_ids = [node_id for node_id, mastery in mastery_snapshot.items() if mastery < HISTORY_WEAK_THRESHOLD]
        mastered_ids = self._dedupe_text([*strongest_nodes, *mastered_ids], limit=20)
        weak_ids = self._dedupe_text([*persistent_weak_nodes, *weak_ids], limit=20)
        weak_ids = [node_id for node_id in weak_ids if node_id not in set(mastered_ids)]
        if not mastered_ids and not weak_ids:
            return {}

        labels_by_id = {
            _strip(node.get("node_id")): _strip(node.get("label") or node.get("node_id"))
            for node in pack_nodes
            if isinstance(node, dict) and _strip(node.get("node_id"))
        }
        mastered_labels = [labels_by_id.get(node_id, node_id) for node_id in mastered_ids]
        weak_labels = [labels_by_id.get(node_id, node_id) for node_id in weak_ids]
        history_note = self._format_cross_sprint_history_note(
            mastered_labels=mastered_labels,
            weak_labels=weak_labels,
        )
        return {
            "sprint_pack_id": _strip(cold_start.get("sprint_pack_id") or (pack or {}).get("id")),
            "mastery_snapshot": mastery_snapshot,
            "skip_or_light_review_nodes": mastered_ids,
            "skip_or_light_review_labels": mastered_labels,
            "priority_boost_nodes": weak_ids,
            "priority_boost_labels": weak_labels,
            "strongest_nodes": mastered_ids,
            "persistent_weak_nodes": weak_ids,
            "history_note": history_note,
        }

    def _format_cross_sprint_history_note(
        self,
        *,
        mastered_labels: list[str],
        weak_labels: list[str],
    ) -> str:
        parts: list[str] = []
        if mastered_labels:
            parts.append(
                f"上次已掌握：{self._format_compact_list(mastered_labels, limit=3)}，本轮只快速过一遍或跳过重学"
            )
        if weak_labels:
            parts.append(f"本轮重点投入：{self._format_compact_list(weak_labels, limit=3)}")
        return "；".join(parts) + ("。" if parts else "")

    def _build_light_review_pack_spec(
        self,
        *,
        history_summary: dict[str, Any],
        pack: dict[str, Any],
        path_mode: str,
    ) -> dict[str, Any] | None:
        mastered_ids = [
            node_id for node_id in list(history_summary.get("skip_or_light_review_nodes") or []) if _strip(node_id)
        ][:3]
        if not mastered_ids:
            return None
        nodes_by_id = {
            _strip(node.get("node_id")): node
            for node in pack.get("knowledge_nodes", [])
            if isinstance(node, dict) and _strip(node.get("node_id"))
        }
        node_labels = [_strip((nodes_by_id.get(node_id) or {}).get("label") or node_id) for node_id in mastered_ids]
        node_summary = self._format_compact_list(node_labels, limit=3)
        return {
            "day": 1,
            "focus": f"上次已掌握：快速过一遍 {node_summary}，确认还能闭卷提取，不展开重学。",
            "task_kind": "light_review",
            "title_focus": "上次已掌握速览",
            "estimated_minutes": min(20, max(10, 8 * len(mastered_ids))),
            "order_index_offset": 1,
            "subject_strategy": {
                "pack_id": _strip(pack.get("id")),
                "path_mode": path_mode,
                "node_ids": mastered_ids,
                "node_labels": node_labels,
                "review_mode": "skip_or_light_review",
                "why_now": (
                    f"根据上次备考记录，{node_summary} 已经掌握得不错；今天只做轻量复习，把主时间留给薄弱节点。"
                ),
                "output_action": f"闭卷快速复述 {node_summary} 的关键判断点，每个点只留 1 句确认。",
                "success_criteria": f"{node_summary} 能闭卷说出关键点即可，不做完整重学。",
                "previous_mastery_summary": history_summary,
            },
        }

    def _pack_mastery_map(self, *, session: PlanningSession, pack: dict[str, Any]) -> dict[str, float]:
        nodes = list(pack.get("knowledge_nodes") or [])
        avg_mastery = self._normalize_mastery_ratio(
            session.collected.get("avg_mastery_score") or session.collected.get("diagnostic_estimated_score")
        )
        mastery_map: dict[str, float] = {
            _strip(node.get("node_id")): avg_mastery
            for node in nodes
            if _strip(node.get("node_id")) and avg_mastery is not None
        }
        node_lookup: dict[str, str] = {}
        for node in nodes:
            node_id = _strip(node.get("node_id"))
            label = _strip(node.get("label"))
            for candidate in (node_id, label):
                key = self._pack_match_key(candidate)
                if key:
                    node_lookup[key] = node_id

        raw_sources: list[Any] = []
        for key in ("galaxy_weak_nodes", "weak_nodes", "previous_exam_weak_nodes"):
            raw_value = session.collected.get(key)
            if isinstance(raw_value, list):
                raw_sources.extend(raw_value)
            elif raw_value:
                raw_sources.append(raw_value)

        weak_default = max(0.0, (avg_mastery or 0.25) - 0.18)
        for raw in raw_sources:
            if isinstance(raw, dict):
                candidates = (
                    raw.get("node_id"),
                    raw.get("id"),
                    raw.get("slug"),
                    raw.get("name"),
                    raw.get("node_name"),
                    raw.get("title"),
                    raw.get("label"),
                )
                node_id = ""
                for candidate in candidates:
                    matched_id = node_lookup.get(self._pack_match_key(candidate))
                    if matched_id:
                        node_id = matched_id
                        break
                if not node_id:
                    continue
                mastery = self._normalize_mastery_ratio(
                    raw.get("mastery_score")
                    or raw.get("mastery")
                    or raw.get("score")
                    or raw.get("avg_mastery")
                    or raw.get("current_mastery")
                    or raw.get("new_mastery")
                )
                if mastery is None:
                    mastery = weak_default
                mastery_map[node_id] = mastery
                continue

            node_id = node_lookup.get(self._pack_match_key(raw))
            if node_id:
                mastery_map[node_id] = min(mastery_map.get(node_id, weak_default), weak_default)

        history_summary = _as_dict(session.collected.get("cross_sprint_mastery_summary"))
        if not history_summary:
            history_summary = self._build_cross_sprint_mastery_summary(session, pack=pack)
        for raw_node_id, mastery in self._coerce_history_mastery_snapshot(
            history_summary.get("mastery_snapshot")
        ).items():
            node_id = node_lookup.get(self._pack_match_key(raw_node_id)) or _strip(raw_node_id)
            if (
                node_id in node_lookup.values()
                or node_id in mastery_map
                or any(_strip(node.get("node_id")) == node_id for node in nodes if isinstance(node, dict))
            ):
                mastery_map[node_id] = mastery

        return mastery_map

    def _select_pack_strategy_preset(self, pack: dict[str, Any], *, total_days: int) -> dict[str, Any]:
        presets = _as_dict(pack.get("strategy_presets"))
        if total_days <= 7 and _as_dict(presets.get("7d")):
            return _as_dict(presets.get("7d"))
        if total_days <= 14 and _as_dict(presets.get("14d")):
            return _as_dict(presets.get("14d"))
        return _as_dict(presets.get("14d") or presets.get("7d"))

    def _match_pack_phase_hint(self, phase_plan: list[dict[str, Any]], *, day: int) -> dict[str, Any]:
        for phase in phase_plan:
            day_range = _strip(phase.get("days"))
            match = re.search(r"(?P<start>\d+)(?:\s*[-–]\s*(?P<end>\d+))?", day_range)
            if not match:
                continue
            start = int(match.group("start"))
            end = int(match.group("end") or start)
            if start <= day <= end:
                return phase
        return {}

    @staticmethod
    def _format_pack_mistake(mistake: dict[str, Any]) -> str:
        label = _strip(mistake.get("label"))
        repair = _strip(mistake.get("repair_strategy"))
        if label and repair:
            return f"{label}：{repair}"
        return label or repair

    def _build_pack_why_now(
        self,
        *,
        primary_node: dict[str, Any],
        mastery: float | None,
        path_mode: str,
    ) -> str:
        label = _strip(primary_node.get("label") or "这个节点")
        exam_weight = float(primary_node.get("exam_weight", 0.0))
        mastery_ratio = mastery if mastery is not None else 0.0
        mastery_pct = int(round(mastery_ratio * 100))
        gap_pct = max(0, 100 - mastery_pct)
        path_hint = "保底路线" if path_mode == "minimum_pass" else "提分路线"
        weight_hint = "高权重" if exam_weight >= 0.7 else "中高权重"
        return (
            f"先做{label}，因为它属于 {path_hint} 里的{weight_hint}节点（权重 {exam_weight:.2f}），"
            f"你当前掌握度约 {mastery_pct}%，还有 {gap_pct}% 的掌握缺口，现在补它最容易换分。"
        )

    def _build_pack_output_action(
        self,
        *,
        actions: list[str],
        archetypes: list[str],
        phase_output: str,
        node_labels: list[str],
    ) -> str:
        clean_actions = self._dedupe_text(actions, limit=2)
        if clean_actions:
            action_line = "；".join(clean_actions)
        else:
            action_line = f"闭卷拿下 {self._format_compact_list(node_labels, limit=2, suffix='个节点')}"
        if archetypes:
            action_line = f"{action_line}；再做 1 道{archetypes[0]}验证"
        elif phase_output:
            action_line = f"{action_line}；最后对照阶段目标：{phase_output}"
        action_line = action_line.rstrip("。")
        return f"{action_line}。"

    def _build_pack_success_criteria(
        self,
        *,
        node_labels: list[str],
        archetypes: list[str],
        mistakes: list[str],
    ) -> str:
        node_target = min(max(len(node_labels), 1), 2)
        parts = [f"至少完成 {node_target} 个高优先节点的闭卷输出"]
        if archetypes:
            parts.append(f"并能独立完成 1 道{archetypes[0]}")
        if mistakes:
            parts.append(f"复盘时明确避开「{mistakes[0].split('：', 1)[0]}」")
        return "，".join(parts).rstrip("。") + "。"

    @staticmethod
    def _fallback_last_24h_clusters() -> list[dict[str, Any]]:
        return [
            {
                "label": "最近高频错因",
                "count": 0,
                "focus_summary": "回看最近 3 道最容易重复出错的题",
                "chapters": [],
                "examples": [],
                "lowest_mastery": 0,
            }
        ]

    def _build_last_24h_custom_tasks(
        self,
        *,
        subject: str,
        last_24h_strategy: dict[str, Any],
        error_clusters: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        focus_nodes = [
            dict(item)
            for item in list(last_24h_strategy.get("focus") or [])
            if isinstance(item, dict) and _strip(item.get("label") or item.get("node_id"))
        ]
        focus_labels = [
            _strip(item.get("label") or item.get("node_id"))
            for item in focus_nodes
            if _strip(item.get("label") or item.get("node_id"))
        ]
        high_yield_labels = focus_labels[:4]
        high_yield_summary = self._format_compact_list(high_yield_labels) if high_yield_labels else "高频高收益节点"
        top_clusters = list(error_clusters or self._fallback_last_24h_clusters())[:3]
        cluster_labels = [
            f"{_strip(item.get('label'))} x{int(item.get('count') or 0)}"
            for item in top_clusters
            if _strip(item.get("label"))
        ]
        mock_exam = _as_dict(last_24h_strategy.get("mock_exam"))
        mock_minutes = _safe_int(mock_exam.get("duration_minutes")) or 30
        mock_instruction = _strip(mock_exam.get("instruction") or "做一轮压缩模拟，做完只归因，不展开新章节。")
        forbidden_actions = [
            _strip(item) for item in list(last_24h_strategy.get("forbidden_actions") or []) if _strip(item)
        ]

        return [
            {
                "day": 1,
                "focus": f"考前冲刺：只复习 {high_yield_summary}，今天不再学新内容。",
                "task_kind": "retrieval_triage",
                "title_focus": "高频知识点速览",
                "estimated_minutes": 35,
                "order_index_offset": 1,
                "subject_strategy": {
                    "node_ids": [
                        _strip(item.get("node_id")) for item in focus_nodes[:4] if _strip(item.get("node_id"))
                    ],
                    "node_labels": high_yield_labels,
                    "why_now": f"明天就考试了，先把 {high_yield_summary} 这些高频高收益节点压成可提取的闭卷输出，比开新章节更值分。",
                    "output_action": f"闭卷速览 {high_yield_summary}，每个点至少说出 1 个关键判断或流程。",
                    "success_criteria": "至少 4 个高频节点能闭卷提取，并明确今天不再开新章节。",
                    "recommended_actions": [
                        _strip(item.get("recommended_action"))
                        for item in focus_nodes[:3]
                        if _strip(item.get("recommended_action"))
                    ],
                    "must_not_include": ["new_chapter_introduction", *forbidden_actions],
                    "last_24h_mode": True,
                    "focus_nodes": focus_nodes[:6],
                },
            },
            {
                "day": 1,
                "focus": "考前冲刺：按错因聚类回看自己的错题，只修最容易重复丢分的错误类型。",
                "task_kind": "retrieval_repair",
                "title_focus": "错题错因回看",
                "estimated_minutes": 40,
                "order_index_offset": 2,
                "subject_strategy": {
                    "node_ids": [
                        _strip(item.get("node_id")) for item in focus_nodes[:2] if _strip(item.get("node_id"))
                    ],
                    "node_labels": high_yield_labels[:2],
                    "why_now": "最后一天最值钱的是把已经暴露过的错因再修一轮，避免同类错误在考场上重复出现。",
                    "output_action": (
                        f"按错因聚类回看最近错题：{'、'.join(cluster_labels[:3]) or '回看最近 3 道错题'}，"
                        "每类至少写 1 句触发提醒。"
                    ),
                    "success_criteria": "至少完成 2 类高频错因回看，并写出对应的触发提醒或判断步骤。",
                    "common_mistakes_to_watch": cluster_labels,
                    "error_clusters": top_clusters,
                    "must_not_include": ["new_chapter_introduction", *forbidden_actions],
                    "last_24h_mode": True,
                },
            },
            {
                "day": 1,
                "focus": f"考前冲刺：完成 {mock_minutes} 分钟短模拟卷，只校准失分点，不再深挖新内容。",
                "task_kind": "mock_review",
                "title_focus": "30分钟短模拟卷",
                "estimated_minutes": mock_minutes,
                "order_index_offset": 3,
                "subject_strategy": {
                    "node_ids": [
                        _strip(item.get("node_id")) for item in focus_nodes[:5] if _strip(item.get("node_id"))
                    ],
                    "node_labels": high_yield_labels,
                    "why_now": "短模拟能在最短时间里暴露最后还会丢分的点，收益比开新章节高得多。",
                    "output_action": f"{mock_instruction} 做完后只整理 Top 3 失分来源。",
                    "success_criteria": f"完成 {mock_minutes} 分钟短模拟，并写出 Top 3 失分来源和最后回看顺序。",
                    "related_archetypes": [
                        _strip(item) for item in list(mock_exam.get("coverage_labels") or []) if _strip(item)
                    ],
                    "must_not_include": ["new_chapter_introduction", *forbidden_actions],
                    "last_24h_mode": True,
                },
            },
        ]

    def _build_pack_daily_specs(
        self,
        *,
        session: PlanningSession,
        total_days: int,
        daily_minutes: int,
        error_clusters: list[dict[str, Any]] | None = None,
    ) -> dict[int, dict[str, Any]]:
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope"))
        pack = load_pack(subject)
        if not pack:
            return {}

        if self._is_last_24h_mode(session):
            sprint_policy = self._build_exam_sprint_policy(session)
            last_24h_strategy = _as_dict(sprint_policy.get("last_24h_strategy") or pack.get("last_24h_strategy"))
            if not last_24h_strategy:
                return {}
            return {
                1: {
                    "custom_tasks": self._build_last_24h_custom_tasks(
                        subject=subject,
                        last_24h_strategy=last_24h_strategy,
                        error_clusters=error_clusters,
                    ),
                }
            }

        path_mode = _strip(session.collected.get("recommended_path")).lower()
        if path_mode not in {"minimum_pass", "score_max"}:
            path_mode = "minimum_pass"

        history_summary = self._build_cross_sprint_mastery_summary(session, pack=pack)
        if history_summary:
            session.collected["cross_sprint_mastery_summary"] = history_summary
        mastery_map = self._pack_mastery_map(session=session, pack=pack)
        prioritized_nodes = query_nodes_by_priority(
            pack,
            current_mastery=mastery_map,
            days_left=total_days,
            path_mode=path_mode,
        )
        if not prioritized_nodes:
            return {}
        nodes_by_id = {_strip(node.get("node_id")): node for node in pack.get("knowledge_nodes", [])}

        if total_days <= 7:
            high_weight = [node for node in prioritized_nodes if float(node.get("exam_weight", 0.0)) > 0.7]
            other_nodes = [node for node in prioritized_nodes if float(node.get("exam_weight", 0.0)) <= 0.7]
            prioritized_nodes = high_weight + other_nodes

        mastered_ids = {
            _strip(node_id)
            for node_id in list(history_summary.get("skip_or_light_review_nodes") or [])
            if _strip(node_id)
        }
        priority_boost_ids = {
            _strip(node_id) for node_id in list(history_summary.get("priority_boost_nodes") or []) if _strip(node_id)
        }
        if mastered_ids:
            prioritized_nodes = [node for node in prioritized_nodes if _strip(node.get("node_id")) not in mastered_ids]
        if priority_boost_ids:
            prioritized_ids = {_strip(node.get("node_id")) for node in prioritized_nodes if _strip(node.get("node_id"))}
            missing_boosted_nodes = [
                nodes_by_id[node_id]
                for node_id in priority_boost_ids
                if node_id not in prioritized_ids and nodes_by_id.get(node_id)
            ]
            boosted_nodes = [node for node in prioritized_nodes if _strip(node.get("node_id")) in priority_boost_ids]
            other_nodes = [node for node in prioritized_nodes if _strip(node.get("node_id")) not in priority_boost_ids]
            prioritized_nodes = missing_boosted_nodes + boosted_nodes + other_nodes

        preset = self._select_pack_strategy_preset(pack, total_days=total_days)
        daily_targets = _as_dict(preset.get("daily_targets"))
        phase_plan = list(preset.get("phase_plan") or [])
        max_new_nodes = _safe_int(daily_targets.get("max_new_nodes")) or max(1, daily_minutes // 35)
        max_new_nodes = max(1, min(max_new_nodes, 5))
        recent_node_ids: list[str] = []
        cursor = 0
        day_specs: dict[int, dict[str, Any]] = {}

        for day in range(1, max(total_days, 1) + 1):
            remaining_budget = daily_minutes
            selected_nodes: list[dict[str, Any]] = []

            while cursor < len(prioritized_nodes):
                candidate = prioritized_nodes[cursor]
                node_minutes = max(15, min(int(float(candidate.get("time_cost", 25))), 60))
                if selected_nodes and (
                    len(selected_nodes) >= max_new_nodes or remaining_budget < min(node_minutes, 25)
                ):
                    break
                selected_nodes.append(candidate)
                remaining_budget -= node_minutes
                cursor += 1
                if remaining_budget <= 15:
                    break

            if not selected_nodes and cursor < len(prioritized_nodes):
                selected_nodes.append(prioritized_nodes[cursor])
                cursor += 1

            if not selected_nodes and recent_node_ids:
                selected_nodes = [nodes_by_id[node_id] for node_id in recent_node_ids[-3:] if nodes_by_id.get(node_id)]

            if not selected_nodes:
                continue

            node_ids = [_strip(node.get("node_id")) for node in selected_nodes if _strip(node.get("node_id"))]
            node_labels = [_strip(node.get("label")) for node in selected_nodes if _strip(node.get("label"))]
            recent_node_ids.extend(node_ids[:2])
            phase_hint = self._match_pack_phase_hint(phase_plan, day=day)
            phase_focus = _strip(phase_hint.get("focus"))
            phase_output = _strip(phase_hint.get("output"))
            archetypes = self._dedupe_text(
                [_strip(item.get("label")) for item in get_archetypes_by_nodes(pack, node_ids)],
                limit=4,
            )
            mistakes = self._dedupe_text(
                [self._format_pack_mistake(item) for item in get_mistake_by_nodes(pack, node_ids)],
                limit=4,
            )
            actions = self._dedupe_text(
                [_strip(node.get("recommended_action")) for node in selected_nodes],
                limit=3,
            )
            primary_node = selected_nodes[0]
            primary_node_id = _strip(primary_node.get("node_id"))
            primary_label = _strip(primary_node.get("label") or "高优先节点")
            primary_mastery = mastery_map.get(primary_node_id)
            why_now = self._build_pack_why_now(
                primary_node=primary_node,
                mastery=primary_mastery,
                path_mode=path_mode,
            )
            node_summary = self._format_compact_list(node_labels)
            focus_prefix = f"{phase_focus}：" if phase_focus else ""
            focus = (
                f"{focus_prefix}优先拿下 {node_summary}，先把 {primary_label} 这类高收益节点变成今天能闭卷输出的内容。"
            )
            output_action = self._build_pack_output_action(
                actions=actions,
                archetypes=archetypes,
                phase_output=phase_output,
                node_labels=node_labels,
            )
            success_criteria = self._build_pack_success_criteria(
                node_labels=node_labels,
                archetypes=archetypes,
                mistakes=mistakes,
            )
            estimated_minutes = min(
                daily_minutes,
                max(30, sum(max(15, min(int(float(node.get("time_cost", 25))), 60)) for node in selected_nodes) + 10),
            )
            day_specs[day] = {
                "focus": focus,
                "title_focus": primary_label if len(node_labels) == 1 else f"{primary_label} 等{len(node_labels)}个点",
                "estimated_minutes": estimated_minutes,
                "sprint_pack_nodes": [
                    {"node_id": node_id, "label": label}
                    for node_id, label in zip(node_ids, node_labels, strict=False)
                    if node_id
                ],
                "subject_strategy": {
                    "pack_id": _strip(pack.get("id")),
                    "path_mode": path_mode,
                    "node_ids": node_ids,
                    "node_labels": node_labels,
                    "primary_node_id": primary_node_id,
                    "primary_node_label": primary_label,
                    "primary_node_exam_weight": float(primary_node.get("exam_weight", 0.0)),
                    "primary_node_mastery": int(round((primary_mastery or 0.0) * 100)),
                    "why_now": why_now,
                    "phase_focus": phase_focus,
                    "phase_output": phase_output,
                    "output_action": output_action,
                    "success_criteria": success_criteria,
                    "related_archetypes": archetypes,
                    "common_mistakes_to_watch": mistakes,
                    "recommended_actions": actions,
                    "previous_mastery_summary": history_summary,
                },
            }

        light_review_spec = self._build_light_review_pack_spec(
            history_summary=history_summary,
            pack=pack,
            path_mode=path_mode,
        )
        if light_review_spec:
            existing_day_one = day_specs.get(1)
            if existing_day_one:
                existing_copy = dict(existing_day_one)
                existing_copy["day"] = 1
                existing_copy["order_index_offset"] = max(
                    _safe_int(existing_copy.get("order_index_offset")) or 0,
                    2,
                )
                day_specs[1] = {"custom_tasks": [light_review_spec, existing_copy]}
            else:
                day_specs[1] = light_review_spec

        return day_specs

    def _default_daily_task_specs(self, phase: dict[str, Any], *, phase_index: int) -> list[dict[str, Any]]:
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

    def _generate_next_day_plan(
        self,
        *,
        day_spec: dict[str, Any],
        sprint_policy: dict[str, Any],
        completion_rate: float | None,
        calendar_context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        days_left = sprint_policy.get("days_left")
        if days_left is None:
            days_left = sprint_policy.get("actual_days_left")
        if AdaptiveReplanner.should_compress(
            completion_rate=completion_rate,
            days_left=days_left,
            calendar_context=calendar_context,
            source_daily_spec=day_spec,
        ):
            return [
                AdaptiveReplanner.build_compressed_sprint_day_spec(
                    day_number=_safe_int(day_spec.get("day")) or 1,
                    completion_rate=float(completion_rate or 0.0),
                    sprint_policy=sprint_policy,
                    source_daily_spec=day_spec,
                    calendar_context=calendar_context,
                )
            ]
        return [day_spec]

    def _apply_next_day_adaptive_generation(
        self,
        *,
        phase: dict[str, Any],
        session: PlanningSession,
        specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        collected_context = _as_dict(
            session.collected.get("adaptive_replan") or session.collected.get("adaptive_compression")
        )
        phase_context = _as_dict(phase.get("adaptive_replan") or phase.get("adaptive_compression"))
        context = {**collected_context, **phase_context}
        completion_rate = _optional_float(context.get("completion_rate") or context.get("previous_day_completion_rate"))
        target_day = _safe_int(context.get("day_number") or context.get("next_day") or context.get("target_day"))
        if completion_rate is None or target_day is None:
            return specs

        sprint_policy = _as_dict(phase.get("sprint_policy"))
        if not sprint_policy:
            return specs
        calendar_context = self._adaptive_calendar_context(session=session, phase=phase, context=context)

        generated: list[dict[str, Any]] = []
        for spec in specs:
            if int(spec.get("day") or 0) == target_day:
                generated.extend(
                    self._generate_next_day_plan(
                        day_spec=spec,
                        sprint_policy=sprint_policy,
                        completion_rate=completion_rate,
                        calendar_context=calendar_context,
                    )
                )
            else:
                generated.append(spec)
        return generated

    def _adaptive_calendar_context(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        for raw in (
            context.get("calendar_context"),
            session.collected.get("calendar_context"),
            _as_dict(session.collected.get("cold_start_context")).get("calendar_context"),
            phase.get("calendar_context"),
        ):
            payload = _as_dict(raw)
            if payload:
                return payload
        return {}

    @staticmethod
    def _extract_calendar_context(context: dict[str, Any] | None) -> dict[str, Any]:
        ctx = _as_dict(context)
        for raw in (
            ctx.get("calendar_context"),
            _as_dict(ctx.get("cognitive_context")).get("calendar_context"),
            _as_dict(ctx.get("user_context")).get("calendar_context"),
        ):
            payload = _as_dict(raw)
            if payload:
                return payload
        return {}

    def _apply_calendar_schedule_to_specs(
        self,
        *,
        phase: dict[str, Any],
        session: PlanningSession,
        specs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        calendar_context = self._adaptive_calendar_context(session=session, phase=phase, context={})
        if not calendar_context:
            return specs

        today = _utcnow().date()
        scheduled_specs: list[dict[str, Any]] = []
        for raw_spec in specs:
            spec = dict(raw_spec)
            day_number = _safe_int(spec.get("day")) or 1
            target_date = _strip(spec.get("target_date") or spec.get("date"))
            if not target_date:
                target_date = (today + timedelta(days=max(day_number - 1, 0))).isoformat()
                spec["target_date"] = target_date
            if spec.get("scheduled_start_time") and spec.get("scheduled_end_time"):
                scheduled_specs.append(spec)
                continue
            slot = AdaptiveReplanner._select_calendar_safe_slot(
                calendar_context=calendar_context,
                source_daily_spec=spec,
                estimated_minutes=_safe_int(spec.get("estimated_minutes")) or 60,
            )
            if slot:
                note = f"参考日程：避开当日考试/上课等日历占用，建议安排在 {slot['start']}-{slot['end']}。"
                spec["scheduled_start_time"] = slot["start"]
                spec["scheduled_end_time"] = slot["end"]
                spec["calendar_avoidance"] = {
                    "applied": True,
                    "reason": note,
                    "conflicts": slot.get("conflicts", []),
                }
                method_steps = [_strip(item) for item in list(spec.get("method_steps") or []) if _strip(item)]
                if note not in method_steps:
                    method_steps.append(note)
                if method_steps:
                    spec["method_steps"] = method_steps
            scheduled_specs.append(spec)
        return scheduled_specs

    def _weak_node_match_keys(self, raw_nodes: Any) -> list[str]:
        keys: list[str] = []
        for raw in _listish(raw_nodes):
            if isinstance(raw, dict):
                values = [
                    raw.get("node_id"),
                    raw.get("node_name"),
                    raw.get("label"),
                    raw.get("title"),
                ]
                node_id = _strip(raw.get("node_id"))
                if node_id:
                    values.append(node_id.rsplit(".", 1)[-1].replace("_", " "))
            else:
                values = [raw]
            for value in values:
                key = self._pack_match_key(value)
                if key and key not in keys:
                    keys.append(key)
        return keys

    def _spec_matches_weak_node_keys(
        self,
        spec: dict[str, Any],
        phase: dict[str, Any],
        weak_keys: list[str],
    ) -> bool:
        if not weak_keys:
            return False
        subject_strategy = _as_dict(spec.get("subject_strategy"))
        values: list[Any] = [
            spec.get("focus"),
            spec.get("title_focus"),
            phase.get("focus"),
            subject_strategy.get("primary_node_id"),
            subject_strategy.get("primary_node_label"),
        ]
        values.extend(list(subject_strategy.get("node_ids") or []))
        values.extend(list(subject_strategy.get("node_labels") or []))
        target_keys = [self._pack_match_key(value) for value in values if self._pack_match_key(value)]
        for weak_key in weak_keys:
            for target_key in target_keys:
                if weak_key == target_key or weak_key in target_key or target_key in weak_key:
                    return True
        return False

    def _daily_task_specs(
        self,
        phase: dict[str, Any],
        *,
        phase_index: int,
        session: PlanningSession | None = None,
        error_clusters: list[dict[str, Any]] | None = None,
        galaxy_weak_nodes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        specs = self._default_daily_task_specs(phase, phase_index=phase_index)
        if session is None or not specs:
            return specs

        total_days = self._resolved_days_left(session) or max(spec["day"] for spec in specs)
        daily_minutes = max((_safe_int(phase.get("daily_hours")) or 1) * 60, 30)
        pack_specs = self._build_pack_daily_specs(
            session=session,
            total_days=total_days,
            daily_minutes=daily_minutes,
            error_clusters=error_clusters,
        )

        merged_specs: list[dict[str, Any]] = []
        if not pack_specs:
            merged_specs = [dict(spec) for spec in specs]
        else:
            for spec in specs:
                pack_spec = _as_dict(pack_specs.get(int(spec["day"])))
                if not pack_spec:
                    merged_specs.append(spec)
                    continue
                custom_tasks = list(pack_spec.get("custom_tasks") or [])
                if custom_tasks:
                    merged_specs.extend(
                        [dict(item) for item in custom_tasks if isinstance(item, dict) and _safe_int(item.get("day"))]
                    )
                    continue
                merged_spec = dict(spec)
                is_first_day_diagnostic = (
                    int(spec.get("day") or 0) == 1 and _strip(spec.get("task_kind")) == "diagnostic_triage"
                )
                if not is_first_day_diagnostic:
                    merged_spec["focus"] = _strip(pack_spec.get("focus")) or merged_spec["focus"]
                    merged_spec["title_focus"] = _strip(pack_spec.get("title_focus")) or merged_spec["title_focus"]
                merged_spec["estimated_minutes"] = (
                    _safe_int(pack_spec.get("estimated_minutes")) or merged_spec["estimated_minutes"]
                )
                subject_strategy = _as_dict(pack_spec.get("subject_strategy"))
                if subject_strategy:
                    merged_spec["subject_strategy"] = subject_strategy
                merged_specs.append(merged_spec)

        # F16: Annotate specs whose focus matches Galaxy weak nodes for sprint priority.
        if galaxy_weak_nodes:
            weak_lower = [n.lower().strip() for n in galaxy_weak_nodes if isinstance(n, str) and n.strip()]
            for spec in merged_specs:
                focus_text = (spec.get("focus") or "").lower()
                phase_focus = _strip(phase.get("focus") or "").lower()
                if any(weak in focus_text or weak in phase_focus for weak in weak_lower):
                    spec["galaxy_weak"] = True
                    if "Galaxy 标记的弱点" not in spec.get("focus", ""):
                        spec["focus"] = f"{spec['focus']}（Galaxy 标记的弱点）"

        previous_weak_keys = self._weak_node_match_keys(session.collected.get("previous_exam_weak_nodes"))
        if previous_weak_keys:
            for spec in merged_specs:
                if not self._spec_matches_weak_node_keys(spec, phase, previous_weak_keys):
                    continue
                spec["previous_exam_weak"] = True
                current_minutes = _safe_int(spec.get("estimated_minutes")) or 30
                spec["estimated_minutes"] = max(current_minutes + 10, int(round(current_minutes * 1.2)))
                if "上次考后复盘标记的弱点" not in spec.get("focus", ""):
                    spec["focus"] = f"{spec['focus']}（上次考后复盘标记的弱点）"

        adapted_specs = self._apply_next_day_adaptive_generation(phase=phase, session=session, specs=merged_specs)
        scheduled_specs = self._apply_calendar_schedule_to_specs(phase=phase, session=session, specs=adapted_specs)
        return self._attach_material_anchors_to_specs(session=session, phase=phase, specs=scheduled_specs)

    def _estimated_minutes_for_task(
        self,
        *,
        task_kind: str,
        sprint_mode: str,
        base_minutes: int,
        max_duration_min: int | None = None,
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
        result = max(floor, min(base_minutes, cap))
        if max_duration_min is not None:
            result = min(result, max_duration_min)
        return result

    def _progress_data(self, state: str) -> dict[str, Any]:
        current = {
            "CLARIFYING": 0,
            "PLANNING": 2,
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
            "exam_date": _strip(collected.get("exam_date")),
            "time_constraint_days": _safe_int(collected.get("time_constraint_days")) or 7,
            "knowledge_baseline": _strip(collected.get("knowledge_baseline")),
            "daily_available_hours": _safe_int(collected.get("daily_available_hours")) or 0,
            "blocked_days": collected.get("blocked_days") or [],
            "available_materials": collected.get("available_materials") or [],
            "motivation_context": _strip(collected.get("motivation_context") or collected.get("motivation")),
            "motivation": _strip(collected.get("motivation") or collected.get("motivation_context")),
            "sprint_pack_id": _strip(collected.get("sprint_pack_id")),
            "sprint_pack_subject": _strip(collected.get("sprint_pack_subject")),
            "strongest_nodes": collected.get("strongest_nodes") or [],
            "persistent_weak_nodes": collected.get("persistent_weak_nodes") or [],
            "previous_exam_weak_nodes": collected.get("previous_exam_weak_nodes") or [],
            "previous_sprint_summary": collected.get("previous_sprint_summary") or {},
            "mastery_snapshot": collected.get("mastery_snapshot") or {},
            "cross_sprint_mastery_summary": collected.get("cross_sprint_mastery_summary") or {},
            "pre_filled_domain_hints": collected.get("pre_filled_domain_hints") or [],
            EXAM_SPRINT_FAST_TRACK_FLAG: bool(collected.get(EXAM_SPRINT_FAST_TRACK_FLAG)),
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
