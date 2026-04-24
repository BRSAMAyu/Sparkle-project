from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.cache import cache_service
from app.models.plan import PlanPriority, PlanStage, PlanType
from app.models.task import Task
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
    expires_at: str = field(
        default_factory=lambda: (_utcnow() + timedelta(seconds=PLANNING_SESSION_TTL)).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PlanningSession":
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

    def __init__(self, redis_client=None) -> None:
        self.redis = redis_client or cache_service.redis

    def detect_planning_intent(self, message: str, context: dict[str, Any] | None = None) -> bool:
        text = _strip(message).lower()
        if not text:
            return False
        ctx = _as_dict(context)
        if ctx.get("plan_id"):
            return False
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
        mentions_existing_plan = any(token in text for token in ("更新这个计划", "调整这个计划", "已有计划", "这个计划"))

        if mentions_existing_plan:
            return False

        return has_timebox and (has_planning_verb or has_goal_commitment or (asks_for_help and (has_goal or has_subject)))

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

    async def process_planning_turn(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        chat_session_id: str,
        message: str,
        context: dict[str, Any],
    ) -> dict[str, Any] | None:
        session = await self.get_active_session(chat_session_id)
        if session is None:
            if not self.detect_planning_intent(message, context):
                return None
            session = await self.create_session(
                chat_session_id=chat_session_id,
                user_id=str(user_id),
                goal_raw=message,
            )
            session.collected.update(await self._prefill_from_profile_context(context))
            return await self._handle_clarifying(db=db, user_id=user_id, session=session, user_message=message)

        context_session_id = _strip(context.get("planning_session_id"))
        if context_session_id and context_session_id != session.planning_session_id:
            return {"bypass_planning": True}

        lowered = _strip(message).lower()
        if any(token in lowered for token in PLANNING_CANCEL_PATTERNS):
            await self.abandon_session(session)
            return {
                "message": "好的，先退出这轮规划。我会保留已经了解的信息，之后你想继续时我们可以直接接上。",
                "widgets": [],
            }

        if not self.is_message_relevant_to_planning(session, message):
            return {"bypass_planning": True}

        if session.state == "CLARIFYING":
            return await self._handle_clarifying(db=db, user_id=user_id, session=session, user_message=message)
        if session.state == "AWAITING_CONFIRM":
            if any(token in lowered for token in PLANNING_CONFIRM_PATTERNS):
                return await self._handle_generating(db=db, user_id=user_id, session=session)
            return await self._handle_strategy_revision(session=session, user_message=message)
        if session.state == "STRATEGY_REVISION":
            return await self._handle_strategy_revision(session=session, user_message=message)
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
    ) -> dict[str, Any]:
        self._merge_clarifying_fields(session.collected, user_message)
        session.collected.setdefault("goal_raw", session.goal_raw)
        session.turns_in_state += 1
        if self._is_ready_for_bottlenecks(session, user_message):
            session.state = "BOTTLENECK"
            session.bottlenecks = self._build_bottlenecks(session)
            strategy = self._build_strategy(session)
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
                "message": "我先把这次 7 天备考里最影响结果的瓶颈和推进策略整理出来，你看看是否符合你的实际情况。",
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
            }

        prompt = self._next_clarifying_prompt(session)
        await self.save_session(session)
        return {
            "message": prompt,
            "widgets": [{"type": "planning_progress_strip", "data": self._progress_data("CLARIFYING")}],
        }

    async def _handle_strategy_revision(self, *, session: PlanningSession, user_message: str) -> dict[str, Any]:
        strategy = _as_dict(session.confirmed_strategy)
        if strategy:
            first_phase = strategy.get("phases", [{}])[0]
            if "真题" in user_message:
                first_phase["method"] = f"{_strip(first_phase.get('method'))} 优先把真题和课件一起使用。".strip()
            if "轻一点" in user_message or "时间少" in user_message:
                strategy["daily_commitment_range"] = "1–3小时"
            if "重一点" in user_message or "更猛" in user_message:
                strategy["daily_commitment_range"] = "3–5小时"
            strategy["adjustment_note"] = user_message.strip()
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
        }

    async def _handle_generating(
        self,
        *,
        db: AsyncSession,
        user_id: UUID,
        session: PlanningSession,
    ) -> dict[str, Any]:
        strategy = _as_dict(session.confirmed_strategy)
        if not strategy:
            strategy = self._build_strategy(session)
            session.confirmed_strategy = strategy

        days = _safe_int(strategy.get("total_days")) or _safe_int(session.collected.get("time_constraint_days")) or 7
        daily_hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "考试科目")
        plan = await PlanService.create(
            db=db,
            obj_in=PlanCreate(
                name=f"{days}天{subject}冲刺",
                type=PlanType.SPRINT,
                description=json.dumps({"strategy": strategy, "bottlenecks": session.bottlenecks or []}, ensure_ascii=False),
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
                )
                task = await TaskService.create(
                    db=db,
                    obj_in=TaskCreate(
                        title=f"Day {day_spec['day']} · {_strip(phase.get('label'))}",
                        type=coerce_task_type("learning"),
                        plan_id=plan.id,
                        estimated_minutes=max((_safe_int(phase.get("daily_hours")) or daily_hours) * 60, 30),
                        difficulty=min(5, 2 + index),
                        energy_cost=min(5, 2 + index),
                        guide_content=_strip(guide_json.get("objective") or day_spec["focus"]),
                        guide_json=guide_json,
                        ai_prompt=self._build_task_ai_prompt(
                            session=session,
                            phase={**phase, "focus": day_spec["focus"]},
                            guide_json=guide_json,
                        ),
                        source_planning_session_id=session.planning_session_id,
                        phase_index=index,
                        success_criteria=_strip(guide_json.get("success_criteria") or phase.get("output")),
                        tags=["规划生成", subject, f"phase:{index}", f"day:{day_spec['day']}"],
                    ),
                    user_id=user_id,
                )
                created_tasks.append(task)

        session.state = "DONE"
        await self.save_session(session)
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
        }

    def _is_ready_for_bottlenecks(self, session: PlanningSession, user_message: str) -> bool:
        if all(_strip(session.collected.get(field)) for field in self.REQUIRED_FIELDS):
            return True
        lowered = _strip(user_message).lower()
        if any(token in lowered for token in PLANNING_ENOUGH_PATTERNS):
            return True
        return session.turns_in_state >= 4

    def is_message_relevant_to_planning(self, session: PlanningSession, message: str) -> bool:
        text = _strip(message).lower()
        if not text:
            return False
        if any(token in text for token in PLANNING_CANCEL_PATTERNS + PLANNING_ENOUGH_PATTERNS + PLANNING_CONFIRM_PATTERNS):
            return True
        if session.state == "CLARIFYING":
            if any(token in text for token in PLANNING_TASK_BYPASS_PATTERNS):
                return False
            collected = {}
            self._merge_clarifying_fields(collected, message)
            return any(_strip(collected.get(field)) for field in self.REQUIRED_FIELDS)
        if session.state in {"AWAITING_CONFIRM", "STRATEGY_REVISION"}:
            return any(token in text for token in PLANNING_ADJUST_PATTERNS)
        return True

    def _next_clarifying_prompt(self, session: PlanningSession) -> str:
        missing = [field for field in self.REQUIRED_FIELDS if not _strip(session.collected.get(field))]
        if "exam_scope" in missing and "knowledge_baseline" in missing:
            return "先帮我补两块最关键的信息：这次考试具体考哪些范围？你现在对这门课大概是完全没学过、上过课但没复习，还是已经学过一部分？"
        if "exam_scope" in missing:
            return "这次考试具体考哪些范围？如果你知道教材、章节或者老师给的考纲，直接告诉我就行。"
        if "knowledge_baseline" in missing:
            return "你现在对这门课的基础大概在哪个位置？比如完全没学过、上过课但没复习，或者已经学过一半。"
        return "你接下来这几天每天大概能拿出多少时间？有没有哪几天会特别忙或者完全学不了？"

    def _merge_clarifying_fields(self, collected: dict[str, Any], user_message: str) -> None:
        text = _strip(user_message)
        if not text:
            return
        lowered = text.lower()
        if not collected.get("exam_scope") and any(token in lowered for token in ("章", "教材", "课件", "考纲", "网络", "计网", "tcp", "udp", "传输层", "网络层")):
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

        day_match = re.search(r"(?P<days>\d+)\s*(天|day|days)", lowered)
        if day_match and not collected.get("time_constraint_days"):
            collected["time_constraint_days"] = int(day_match.group("days"))
        if not collected.get("subject"):
            subject_match = re.search(r"(计算机网络|计网|高数|线代|概率论|操作系统|数据库|英语)", text)
            if subject_match:
                collected["subject"] = subject_match.group(1)

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

    def _build_task_guide_json(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        phase_index: int,
        default_daily_hours: int,
        day_number: int | None = None,
        day_focus: str | None = None,
    ) -> dict[str, Any]:
        phase_hours = _safe_int(phase.get("daily_hours")) or default_daily_hours or 2
        method = _strip(phase.get("method"))
        focus = _strip(day_focus or phase.get("focus"))
        output = _strip(phase.get("output"))
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        day_label = f"Day {day_number} " if day_number else ""
        guide_steps = [
            f"先用 15 分钟扫一遍和「{_strip(phase.get('label'))}」相关的课件/教材目录，只标记最容易失分的部分。",
            f"围绕这个阶段的重点执行：{method or focus}",
            f"最后留 15 分钟做一次自测或复述，确认你是否已经达到「{output or focus}」。",
        ]
        key_points = [
            focus or f"{subject} 的阶段重点",
            output or "把知识点转成能说清、能做题的状态",
        ]
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
            "objective": f"{day_label}{output or focus or f'完成 {subject} 的第 {phase_index} 阶段推进'}".strip(),
            "method_steps": guide_steps,
            "time_estimate_minutes": max(phase_hours * 60, 30),
            "success_criteria": output or f"完成 {phase_index} 阶段并能复述核心内容。",
            "key_points": key_points,
            "common_mistakes": common_mistakes,
        }

    def _build_task_ai_prompt(
        self,
        *,
        session: PlanningSession,
        phase: dict[str, Any],
        guide_json: dict[str, Any],
    ) -> str:
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        baseline = _strip(session.collected.get("knowledge_baseline") or "基础不稳")
        daily_hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        phase_label = _strip(phase.get("label") or "当前阶段")
        return (
            f"【背景】我是学生，目标是 {session.goal_raw or f'在限定时间内完成 {subject} 备考'}。\n\n"
            f"【我的情况】科目是 {subject}，当前基础是 {baseline}，每天大概能投入 {daily_hours} 小时。\n\n"
            f"【当前阶段】{phase_label}\n"
            f"重点：{_strip(phase.get('focus'))}\n"
            f"目标：{_strip(guide_json.get('objective'))}\n"
            f"完成标准：{_strip(guide_json.get('success_criteria'))}\n\n"
            "【请帮我】\n"
            "1. 用最精炼的方式讲清当前阶段最关键的知识点\n"
            "2. 给我 3 个由浅到深的检查题，不要先给答案\n"
            "3. 告诉我这个阶段最容易踩的坑\n\n"
            "【风格要求】直接、结论先行、不说空话，我的时间很紧。"
        )

    async def _prefill_from_profile_context(self, context: dict[str, Any]) -> dict[str, Any]:
        profile_context = _as_dict(context.get("profile_context"))
        prefs = _as_dict(profile_context.get("preferences"))
        cold_start = _as_dict(prefs.get(PLANNING_PROFILE_KEYS["cold_start_context"]))
        merged = {
            "goal_raw": _strip(cold_start.get("primary_goal_description")),
            "exam_scope": _strip(cold_start.get("exam_scope") or cold_start.get("subject")),
            "knowledge_baseline": _strip(cold_start.get("knowledge_baseline")),
            "time_available": self._format_time_available(cold_start),
            "daily_available_hours": _safe_int(cold_start.get("daily_available_hours")),
            "blocked_days": cold_start.get("blocked_days") or [],
            "subject": _strip(cold_start.get("subject")),
            "time_constraint_days": _safe_int(cold_start.get("time_constraint_days")),
        }
        return {key: value for key, value in merged.items() if value not in (None, "", [], {})}

    def _build_bottlenecks(self, session: PlanningSession) -> list[dict[str, Any]]:
        # Phase II: replace this V1 rule template with LLM-backed analysis once richer study signals are available.
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "这门课")
        baseline = _strip(session.collected.get("knowledge_baseline") or "基础不稳")
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        return [
            {
                "id": "b1",
                "description": f"知识覆盖率不足：{subject} 需要在 {days} 天内完成压缩复习，但你当前只有每天约 {hours} 小时的有效时间。",
                "severity": "high",
                "specific_risk": f"如果前两天没有快速建立章节框架，后半程很容易只顾着赶进度，留不出完整模拟的时间。",
            },
            {
                "id": "b2",
                "description": f"理解成本偏高：你目前属于“{baseline}”状态，说明核心概念需要先用框架化方式补起来，而不能直接堆题。",
                "severity": "high",
                "specific_risk": f"像 {subject} 这类概念多、易混淆的科目，如果不先拉出对比框架，考试时会出现‘看着眼熟但不会判断’的问题。",
            },
            {
                "id": "b3",
                "description": f"题感不足：当前信息里还没有看到你做过稳定的真题或自测，这意味着知识点可能学过却不会落到题型上。",
                "severity": "medium",
                "specific_risk": "后两天如果才第一次接触题目，会来不及暴露高频错误类型，冲刺效率会明显下降。",
            },
        ]

    def _build_strategy(self, session: PlanningSession) -> dict[str, Any]:
        # Phase II: replace this V1 rule template with LLM-backed strategy generation for non-demo domains.
        days = _safe_int(session.collected.get("time_constraint_days")) or 7
        hours = _safe_int(session.collected.get("daily_available_hours")) or 2
        subject = _strip(session.collected.get("subject") or session.collected.get("exam_scope") or "当前科目")
        ranges = self._phase_day_ranges(days)
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
            phases.append(
                {
                    "phase": index,
                    "start_day": day_range["start"],
                    "end_day": day_range["end"],
                    "days": self._format_day_range(day_range["start"], day_range["end"]),
                    "label": template["label"],
                    "daily_hours": max(1, hours + int(template["hour_delta"])),
                    "focus": template["focus"],
                    "method": template["method"],
                    "output": template["output"],
                }
            )
        first_checkpoint = min(days, ranges[0]["end"])
        final_checkpoint = min(days, ranges[-1]["start"])
        return {
            "total_days": days,
            "daily_commitment_range": f"{max(1, hours - 1)}–{hours + 1}小时",
            "phases": phases,
            "checkpoints": [
                {
                    "day": first_checkpoint,
                    "description": f"Day {first_checkpoint} 晚：做一轮 15–20 题的小自测，确认框架阶段是否真的建立起来。",
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
        return [
            {
                "day": day,
                "focus": f"{label}第 {day - start_day + 1} 天：{focus}",
            }
            for day in range(start_day, end_day + 1)
        ]

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
