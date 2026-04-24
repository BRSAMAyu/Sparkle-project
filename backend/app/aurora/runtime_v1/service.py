from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import UserPreferencesCenter

AURORA_SURFACE_MODELING = "aurora_modeling"
AURORA_RUNTIME_MODE_SURFACES = {
    "onboarding_modeling": AURORA_SURFACE_MODELING,
    "aurora_modeling": AURORA_SURFACE_MODELING,
    "aurora_planning": "aurora_planning",
    "aurora_checkpoint": "aurora_checkpoint",
}
AURORA_RUNTIME_STATE_KEY_TEMPLATE = "aurora:runtime:{user_id}:{surface}:{conversation_id}"
AURORA_RUNTIME_STATE_TTL_SECONDS = 24 * 60 * 60

_DEFAULT_ACTIVITY_PROFILE = {
    "proactive_intensity": 0.6,
    "next_wake_at": None,
    "conversation_style": "exploratory",
    "agenda_priority": None,
    "task_density_hint": 0.35,
}


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(slots=True)
class AuroraRuntimeTurnPlan:
    surface: str
    messages: list[str]
    surface_complete: bool
    modeling_complete: bool
    activity_profile: dict[str, Any] = field(default_factory=dict)
    hard_boundaries: dict[str, Any] = field(default_factory=dict)
    informational_tensions: list[dict[str, Any]] = field(default_factory=list)


class AuroraRuntimeV1Service:
    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def plan_turn(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        request_extra_context: dict[str, Any] | None,
        conversation_context: dict[str, Any] | None,
        user_context_payload: dict[str, Any] | None,
    ) -> AuroraRuntimeTurnPlan:
        request_extra_context = dict(request_extra_context or {})
        conversation_context = dict(conversation_context or {})
        user_context_payload = dict(user_context_payload or {})

        hard_boundaries = await self._read_hard_boundaries(active_db=active_db, user_id=user_id)
        activity_profile = self._build_activity_profile(
            surface=surface,
            user_message=user_message,
            request_extra_context=request_extra_context,
        )
        agenda_priority = str(activity_profile.get("agenda_priority") or "").strip() or None
        privacy_boundaries = {
            str(item).strip().lower()
            for item in (hard_boundaries.get("privacy_boundaries") or [])
            if str(item).strip()
        }
        if agenda_priority and agenda_priority.lower() in privacy_boundaries:
            activity_profile["agenda_priority"] = None
            agenda_priority = None

        surface_complete = bool(request_extra_context.get("surface_complete"))
        modeling_complete = bool(request_extra_context.get("modeling_complete"))
        if surface == AURORA_SURFACE_MODELING and not modeling_complete:
            modeling_complete = self._looks_like_modeling_complete(user_message)
        if surface == AURORA_SURFACE_MODELING and not surface_complete:
            surface_complete = modeling_complete

        messages = self._build_message_plan(
            surface=surface,
            user_message=user_message,
            agenda_priority=agenda_priority,
            modeling_complete=modeling_complete,
        )
        if not messages:
            messages = ["我先接住你刚刚说的这部分。你不用一次讲得很完整，我们可以一点点把它捋清。"]

        informational_tensions = []
        if agenda_priority:
            informational_tensions.append(
                {
                    "domain": agenda_priority,
                    "status": "open",
                    "description": f"需要继续补齐 {agenda_priority} 相关线索",
                    "priority": 0.7,
                }
            )

        plan = AuroraRuntimeTurnPlan(
            surface=surface,
            messages=messages,
            surface_complete=surface_complete,
            modeling_complete=modeling_complete,
            activity_profile=activity_profile,
            hard_boundaries=hard_boundaries,
            informational_tensions=informational_tensions,
        )
        await self._persist_runtime_state(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
            request_id=request_id,
            user_message=user_message,
            conversation_context=conversation_context,
            user_context_payload=user_context_payload,
            plan=plan,
        )
        return plan

    async def _read_hard_boundaries(
        self,
        *,
        active_db: AsyncSession | None,
        user_id: str,
    ) -> dict[str, Any]:
        if active_db is None:
            return {}
        try:
            user_uuid = UUID(str(user_id))
        except (TypeError, ValueError):
            return {}

        try:
            explicit_payload = (
                await active_db.execute(
                    select(UserPreferencesCenter.explicit).where(UserPreferencesCenter.user_id == user_uuid)
                )
            ).scalar_one_or_none()
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to read hard boundaries: {}", exc)
            return {}

        if not isinstance(explicit_payload, dict):
            return {}
        aurora_preferences = explicit_payload.get("aurora_preferences")
        return dict(aurora_preferences) if isinstance(aurora_preferences, dict) else {}

    def _build_activity_profile(
        self,
        *,
        surface: str,
        user_message: str,
        request_extra_context: dict[str, Any],
    ) -> dict[str, Any]:
        agenda_priority = self._infer_agenda_priority(user_message)
        profile = dict(_DEFAULT_ACTIVITY_PROFILE)
        profile["agenda_priority"] = agenda_priority
        if surface == AURORA_SURFACE_MODELING:
            profile["conversation_style"] = "exploratory"
            profile["task_density_hint"] = 0.25
        if any(token in str(user_message or "") for token in ("赶", "来不及", "很多事", "好忙")):
            profile["task_density_hint"] = 0.15
        if request_extra_context.get("conversation_style") in {"warm", "structured", "exploratory"}:
            profile["conversation_style"] = request_extra_context["conversation_style"]
        return profile

    def _infer_agenda_priority(self, user_message: str) -> str | None:
        message = str(user_message or "").strip().lower()
        if not message:
            return None
        if any(token in message for token in ("时间", "作息", "节奏", "schedule", "busy", "忙")):
            return "schedule"
        if any(token in message for token in ("考试", "目标", "想要", "plan", "goal", "方向")):
            return "goal"
        if any(token in message for token in ("情绪", "焦虑", "motivation", "状态", "没动力", "怕")):
            return "motivation"
        if any(token in message for token in ("任务", "todo", "安排", "清单", "执行")):
            return "task_density"
        return "baseline"

    def _looks_like_modeling_complete(self, user_message: str) -> bool:
        message = str(user_message or "").strip().lower()
        if not message:
            return False
        completion_markers = ("就这些", "差不多了", "说完了", "没别的了", "that's all", "done")
        return any(marker in message for marker in completion_markers)

    def _build_message_plan(
        self,
        *,
        surface: str,
        user_message: str,
        agenda_priority: str | None,
        modeling_complete: bool,
    ) -> list[str]:
        if surface != AURORA_SURFACE_MODELING:
            return [
                "我先接住你刚刚补进来的信息。",
                "这轮我会按这个方向继续往下走；如果你想改重点，也可以直接打断我。",
            ]

        if modeling_complete:
            return [
                "我大概已经抓到你的轮廓了，先把目前这些线索收住。",
                "接下来我会带着这些理解继续陪你往下走；如果你想补充，随时都可以接着说。",
            ]

        follow_up_by_agenda = {
            "schedule": "如果只先补一个关键空缺，你一天里最容易卡住的是哪个时段？",
            "goal": "如果先只抓一件你最想改变的事，那件事会是什么？",
            "motivation": "最近最容易把你往下拉的念头或情绪，通常会在什么情境里冒出来？",
            "task_density": "你更舒服的推进方式，是轻一点但持续，还是短时间更密一点？",
            "baseline": "如果让我先理解一个最关键的面向，你更想让我先弄清你的目标、卡点，还是日常节奏？",
        }
        focus_by_agenda = {
            "schedule": "我先把“日常节奏怎么影响你”记成当前最重要的线索。",
            "goal": "我先把“你真正想往哪走”记成当前最重要的线索。",
            "motivation": "我先把“什么在拉扯你的状态”记成当前最重要的线索。",
            "task_density": "我先把“你适合什么推进密度”记成当前最重要的线索。",
            "baseline": "我会先用比较轻的方式把你的整体轮廓慢慢补齐。",
        }

        messages = [
            "谢谢你先把这部分告诉我。你不用一次讲得很完整，我会边听边帮你把线索捋清。",
            focus_by_agenda.get(agenda_priority or "baseline", focus_by_agenda["baseline"]),
            follow_up_by_agenda.get(agenda_priority or "baseline", follow_up_by_agenda["baseline"]),
        ]
        if str(user_message or "").strip():
            messages[0] = "谢谢你把这部分先交给我。你不用现在就组织得很完整，我会边听边帮你理出重点。"
        return messages

    async def _persist_runtime_state(
        self,
        *,
        user_id: str,
        surface: str,
        conversation_id: str,
        request_id: str,
        user_message: str,
        conversation_context: dict[str, Any],
        user_context_payload: dict[str, Any],
        plan: AuroraRuntimeTurnPlan,
    ) -> None:
        if self.redis is None:
            return
        runtime_key = AURORA_RUNTIME_STATE_KEY_TEMPLATE.format(
            user_id=user_id,
            surface=surface,
            conversation_id=conversation_id,
        )
        profile_context = user_context_payload.get("profile_context")
        if not isinstance(profile_context, dict):
            profile_context = {}

        runtime_state = {
            "user_id": user_id,
            "surface": surface,
            "conversation_id": conversation_id,
            "runtime_session_id": request_id,
            "user_model_snapshot": profile_context,
            "informational_tensions": plan.informational_tensions,
            "current_intent": {
                "intent_type": "confirm_understanding" if plan.surface_complete else "pursue_tension",
                "target_tension_id": plan.activity_profile.get("agenda_priority"),
            },
            "latent_threads": [],
            "activity_profile": plan.activity_profile,
            "self_scheduled_wakes": [],
            "streaming_status": "waiting_user",
            "ingress_events": [{"type": "user_message", "content": str(user_message or "")}],
            "last_decision_at": _utcnow().isoformat(),
            "updated_at": _utcnow().isoformat(),
            "messages": plan.messages,
            "hard_boundaries": plan.hard_boundaries,
            "history_size": len(conversation_context.get("messages") or []),
        }
        try:
            await self.redis.setex(
                runtime_key,
                AURORA_RUNTIME_STATE_TTL_SECONDS,
                json.dumps(runtime_state, ensure_ascii=False, default=str),
            )
        except Exception as exc:
            logger.warning("Aurora runtime v1 failed to persist Redis runtime state: {}", exc)
