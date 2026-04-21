from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
import re
from typing import Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.event_bus import EventBus
from app.event_publishers.srl_events import publish_srl_event
from app.models.card_protocol import ArtifactType, Card, CardCreatedBy, CardType
from app.models.plan import PlanType
from app.schemas.plan import PlanCreate
from app.services.card_protocol.global_compass_manager import GlobalCompassManager
from app.services.card_protocol.phase_service import PhaseService
from app.services.plan_service import PlanService
from app.services.planning_artifact_service import PlanningArtifactService

DISCOVERY_WORKFLOW_STATE = "DISCOVERY_ACTIVE"
COMPASS_REVIEW_WORKFLOW_STATE = "COMPASS_REVIEW"
PHASE_SKETCH_REVIEW_WORKFLOW_STATE = "PHASE_SKETCH_REVIEW"
PHASE_DESIGN_WORKFLOW_STATE = "PHASE_DESIGN"


@dataclass
class DiscoveryState:
    """Tracks structured planning discovery state across multiple turns."""

    goal_statement: str | None = None
    motivation: str | None = None
    timeline: str | None = None
    constraints: list[str] = field(default_factory=list)
    prior_attempts: list[str] = field(default_factory=list)
    current_situation: str | None = None
    values: list[str] = field(default_factory=list)
    available_time: str | None = None
    collected_data_points: int = 0
    sufficiency_score: float = 0.0
    missing_dimensions: list[str] = field(default_factory=list)
    turns: list[dict[str, str]] = field(default_factory=list)
    session_started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class DiscoveryManager:
    """Multi-turn discovery pipeline for long-horizon plan initialization."""

    MIN_DATA_POINTS = 5
    SUFFICIENCY_THRESHOLD = 0.7
    SESSION_TTL_SECONDS = 60 * 60
    CACHE_PREFIX = "phase_d:discovery:"

    def __init__(self, db: AsyncSession, event_bus: EventBus | None = None):
        self.db = db
        self.event_bus = event_bus
        self.artifact_service = PlanningArtifactService(db, event_bus)
        self.phase_service = PhaseService(db, event_bus)
        self.global_compass_manager = GlobalCompassManager(db, event_bus)

    async def start_discovery(self, *, user_id: UUID, initial_message: str) -> dict[str, Any]:
        session_id = str(uuid4())
        state = DiscoveryState()
        self._ingest_message(state, initial_message, role="user")
        await self._save_session(user_id, session_id, state)
        return self._build_response(session_id, state)

    async def process_discovery_turn(
        self,
        *,
        user_id: UUID,
        session_id: str,
        user_message: str,
    ) -> dict[str, Any]:
        state = await self._load_session(user_id, session_id)
        if state is None:
            raise ValueError("Discovery session not found or expired")

        self._ingest_message(state, user_message, role="user")
        await self._save_session(user_id, session_id, state)
        return self._build_response(session_id, state)

    async def finalize_discovery(
        self,
        *,
        user_id: UUID,
        session_id: str,
        plan_overrides: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = await self._load_session(user_id, session_id)
        if state is None:
            raise ValueError("Discovery session not found or expired")
        if state.sufficiency_score < self.SUFFICIENCY_THRESHOLD or state.collected_data_points < self.MIN_DATA_POINTS:
            raise ValueError("Discovery is not yet sufficient to finalize")

        plan_in = self._build_plan_create(state, plan_overrides or {})
        plan = await PlanService.create(
            db=self.db,
            obj_in=plan_in,
            user_id=user_id,
            skip_quota_check=False,
            redis_client=cache_service.redis,
        )

        plan_card = await self.phase_service.get_plan_card_by_legacy_plan(plan.id, user_id)
        if plan_card is None:
            raise ValueError("Plan card projection unavailable after discovery finalization")

        dossier_payload = self._build_dossier_payload(state)
        dossier_artifact = await self.artifact_service.create_artifact(
            plan_card_id=plan_card.id,
            artifact_type=ArtifactType.DISCOVERY_DOSSIER,
            payload=dossier_payload,
            created_by_agent="discovery_manager",
        )
        await self.artifact_service.propose_artifact(dossier_artifact.id)
        approved_dossier = await self.artifact_service.auto_approve_artifact(dossier_artifact.id)
        dossier_artifact = approved_dossier or dossier_artifact

        compass_artifact = await self.global_compass_manager.build_compass_from_dossier(
            plan_card_id=plan_card.id,
            dossier=dossier_artifact,
            user_id=user_id,
        )
        await self._sync_plan_workflow_state(
            plan_card=plan_card,
            workflow_state=COMPASS_REVIEW_WORKFLOW_STATE,
            patch={
                "discovery_session_id": session_id,
                "discovery_dossier_artifact_id": str(dossier_artifact.id),
                "discovery_dossier_version": dossier_artifact.version,
            },
        )

        await self._delete_session(user_id, session_id)

        if self.event_bus:
            from app.core.event_bus import PlanCreatedEvent

            await self.event_bus.publish(
                "planning.discovery.finalized",
                {
                    "user_id": str(user_id),
                    "plan_id": str(plan.id),
                    "plan_card_id": str(plan_card.id),
                    "dossier_artifact_id": str(dossier_artifact.id),
                    "compass_artifact_id": str(compass_artifact.id),
                },
            )
            plan_created = PlanCreatedEvent(
                user_id=str(user_id),
                plan_id=str(plan.id),
                evidence_id=str(dossier_artifact.id),
                source="discovery_manager",
                metadata={
                    "plan_card_id": str(plan_card.id),
                    "compass_artifact_id": str(compass_artifact.id),
                },
            )
            await self.event_bus.publish("plan.created", plan_created.to_dict())
            await publish_srl_event(
                user_id=user_id,
                trigger_event_type="plan.created",
                evidence_id=str(plan.id),
                metadata={"plan_id": str(plan.id), "plan_card_id": str(plan_card.id)},
            )

        return {
            "workflow_state": COMPASS_REVIEW_WORKFLOW_STATE,
            "plan_id": str(plan.id),
            "plan_card_id": str(plan_card.id),
            "dossier_artifact_id": str(dossier_artifact.id),
            "dossier_version": dossier_artifact.version,
            "compass_artifact_id": str(compass_artifact.id),
            "compass_version": compass_artifact.version,
            "plan_preview": {
                "name": plan.name,
                "type": plan.type.value,
                "daily_available_minutes": plan.daily_available_minutes,
                "description": plan.description,
            },
            "compass_preview": dict(compass_artifact.payload or {}),
        }

    async def _load_session(self, user_id: UUID, session_id: str) -> DiscoveryState | None:
        payload = await cache_service.get(self._session_key(user_id, session_id))
        if not isinstance(payload, dict):
            return None
        return DiscoveryState(**payload)

    async def _save_session(self, user_id: UUID, session_id: str, state: DiscoveryState) -> None:
        await cache_service.set(
            self._session_key(user_id, session_id),
            asdict(state),
            ttl=self.SESSION_TTL_SECONDS,
        )

    async def _delete_session(self, user_id: UUID, session_id: str) -> None:
        await cache_service.delete(self._session_key(user_id, session_id))

    def _session_key(self, user_id: UUID, session_id: str) -> str:
        return f"{self.CACHE_PREFIX}{user_id}:{session_id}"

    def _ingest_message(self, state: DiscoveryState, message: str, *, role: str) -> None:
        clean_message = " ".join(str(message or "").strip().split())
        if not clean_message:
            return
        state.turns.append({"role": role, "message": clean_message})

        lowered = clean_message.lower()
        if state.goal_statement is None and len(clean_message) >= 8:
            state.goal_statement = clean_message

        if state.timeline is None:
            timeline = self._extract_timeline(clean_message)
            if timeline:
                state.timeline = timeline

        if state.available_time is None:
            available_time = self._extract_available_time(clean_message)
            if available_time:
                state.available_time = available_time

        if state.motivation is None and any(token in clean_message for token in ("想", "希望", "目标", "意义", "为了")):
            state.motivation = clean_message

        if state.current_situation is None and any(
            token in clean_message for token in ("现在", "目前", "最近", "基础", "水平", "状态", "工作", "学校")
        ):
            state.current_situation = clean_message

        if any(token in clean_message for token in ("限制", "约束", "没时间", "时间少", "通勤", "工作忙", "孩子", "考试")):
            self._append_unique(state.constraints, clean_message)

        if any(token in clean_message for token in ("以前", "之前", "试过", "尝试过", "失败", "半途而废")):
            self._append_unique(state.prior_attempts, clean_message)

        for value in self._extract_values(clean_message):
            self._append_unique(state.values, value)

        if state.goal_statement is None and any(token in lowered for token in ("learn", "study", "build", "improve")):
            state.goal_statement = clean_message

        state.collected_data_points = self._count_data_points(state)
        state.sufficiency_score = self._compute_sufficiency(state)
        state.missing_dimensions = self._missing_dimensions(state)

    def _build_response(self, session_id: str, state: DiscoveryState) -> dict[str, Any]:
        ready = (
            state.sufficiency_score >= self.SUFFICIENCY_THRESHOLD
            and state.collected_data_points >= self.MIN_DATA_POINTS
        )
        next_question = None if ready else self._generate_next_question(state)
        return {
            "session_id": session_id,
            "workflow_state": DISCOVERY_WORKFLOW_STATE,
            "ready": ready,
            "sufficiency_score": round(state.sufficiency_score, 4),
            "collected_data_points": state.collected_data_points,
            "missing_dimensions": list(state.missing_dimensions),
            "next_question": next_question,
            "discovery_summary": {
                "goal_statement": state.goal_statement,
                "motivation": state.motivation,
                "timeline": state.timeline,
                "constraints": list(state.constraints),
                "prior_attempts": list(state.prior_attempts),
                "current_situation": state.current_situation,
                "values": list(state.values),
                "available_time": state.available_time,
            },
            "compass_preview": self._build_compass_preview(state) if ready else None,
        }

    def _build_dossier_payload(self, state: DiscoveryState) -> dict[str, Any]:
        return {
            "goal_statement": state.goal_statement,
            "motivation": state.motivation,
            "timeline": state.timeline,
            "constraints": list(state.constraints),
            "prior_attempts": list(state.prior_attempts),
            "current_situation": state.current_situation,
            "values": list(state.values),
            "available_time": state.available_time,
            "collected_data_points": state.collected_data_points,
            "sufficiency_score": state.sufficiency_score,
            "missing_dimensions": list(state.missing_dimensions),
            "conversation_turns": list(state.turns),
            "summary": self._build_summary(state),
        }

    def _build_compass_preview(self, state: DiscoveryState) -> dict[str, Any]:
        return {
            "north_star": state.goal_statement or "",
            "success_criteria": self._derive_success_criteria(state),
            "values": list(state.values),
            "hard_constraints": {
                "time_constraints": list(state.constraints),
                "available_time": state.available_time,
            },
            "pacing_philosophy": self._derive_pacing_philosophy(state),
            "risk_tolerance": self._derive_risk_tolerance(state),
        }

    def _build_summary(self, state: DiscoveryState) -> str:
        bits = [
            state.goal_statement or "",
            state.motivation or "",
            state.current_situation or "",
        ]
        return " | ".join(bit for bit in bits if bit)

    def _compute_sufficiency(self, state: DiscoveryState) -> float:
        dimension_scores = {
            "goal_statement": 1.0 if state.goal_statement else 0.0,
            "motivation": 1.0 if state.motivation else 0.0,
            "timeline": 1.0 if state.timeline else 0.0,
            "constraints": 1.0 if state.constraints else 0.0,
            "current_situation": 1.0 if state.current_situation else 0.0,
            "available_time": 1.0 if state.available_time else 0.0,
        }
        weighted = (
            dimension_scores["goal_statement"] * 0.25
            + dimension_scores["motivation"] * 0.15
            + dimension_scores["timeline"] * 0.15
            + dimension_scores["constraints"] * 0.15
            + dimension_scores["current_situation"] * 0.15
            + dimension_scores["available_time"] * 0.15
        )
        if state.collected_data_points < self.MIN_DATA_POINTS:
            weighted *= 0.85
        return min(1.0, weighted)

    def _missing_dimensions(self, state: DiscoveryState) -> list[str]:
        missing = []
        if not state.goal_statement:
            missing.append("goal_statement")
        if not state.motivation:
            missing.append("motivation")
        if not state.timeline:
            missing.append("timeline")
        if not state.constraints:
            missing.append("constraints")
        if not state.current_situation:
            missing.append("current_situation")
        if not state.available_time:
            missing.append("available_time")
        return missing

    def _generate_next_question(self, state: DiscoveryState) -> str:
        if "goal_statement" in state.missing_dimensions:
            return "你最想在这段规划里真正达成的结果是什么？尽量说成一个清晰的目标。"
        if "motivation" in state.missing_dimensions:
            return "这个目标为什么现在对你重要？如果做成了，最想改变你生活里的什么？"
        if "timeline" in state.missing_dimensions:
            return "你希望大概在多久内看到明显进展？是一两个月、半年，还是一年以上？"
        if "constraints" in state.missing_dimensions:
            return "现实里最可能卡住你的约束是什么？比如时间、精力、工作、考试、家庭或基础。"
        if "current_situation" in state.missing_dimensions:
            return "你现在的基础和状态大概怎样？已经做到哪一步了，最大的短板是什么？"
        if "available_time" in state.missing_dimensions:
            return "你稳定能投入的时间大概是多少？例如每天多久、每周几天。"
        return "还有什么你觉得系统必须知道，否则这条路线很容易设计错的？"

    def _count_data_points(self, state: DiscoveryState) -> int:
        points = 0
        points += 1 if state.goal_statement else 0
        points += 1 if state.motivation else 0
        points += 1 if state.timeline else 0
        points += 1 if state.constraints else 0
        points += 1 if state.current_situation else 0
        points += 1 if state.available_time else 0
        points += min(len(state.values), 2)
        points += min(len(state.prior_attempts), 2)
        return points

    def _build_plan_create(self, state: DiscoveryState, overrides: dict[str, Any]) -> PlanCreate:
        timeline = self._extract_timeline_date(state.timeline)
        inferred_type = PlanType.SPRINT if timeline and timeline <= (date.today() + timedelta(days=120)) else PlanType.GROWTH
        daily_available_minutes = overrides.get("daily_available_minutes")
        if daily_available_minutes is None:
            daily_available_minutes = self._derive_daily_minutes(state.available_time)

        subject = overrides.get("subject") or self._derive_subject(state.goal_statement)
        description_parts = [state.motivation, state.current_situation]
        return PlanCreate(
            name=overrides.get("name") or self._derive_plan_name(state.goal_statement),
            type=overrides.get("type") or inferred_type,
            description=overrides.get("description") or " | ".join(part for part in description_parts if part) or state.goal_statement,
            subject=subject,
            target_date=overrides.get("target_date") or timeline,
            daily_available_minutes=int(daily_available_minutes or 60),
            total_estimated_hours=overrides.get("total_estimated_hours"),
            priority=overrides.get("priority"),
            plan_stage=overrides.get("plan_stage"),
        )

    def _derive_plan_name(self, goal_statement: str | None) -> str:
        if not goal_statement:
            return "Discovery Plan"
        plain = goal_statement.strip()
        if len(plain) <= 48:
            return plain
        return f"{plain[:45].rstrip()}..."

    def _derive_subject(self, goal_statement: str | None) -> str | None:
        if not goal_statement:
            return None
        tokens = re.split(r"[，。,.;；:\\s]+", goal_statement)
        return tokens[0][:100] if tokens and tokens[0] else None

    def _derive_daily_minutes(self, available_time: str | None) -> int:
        if not available_time:
            return 60
        text = str(available_time)
        hour_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:小时|h|hour)", text, re.IGNORECASE)
        if hour_match:
            return max(15, int(float(hour_match.group(1)) * 60))
        minute_match = re.search(r"(\d+)\s*(?:分钟|min)", text, re.IGNORECASE)
        if minute_match:
            return max(15, int(minute_match.group(1)))
        return 60

    def _derive_success_criteria(self, state: DiscoveryState) -> list[str]:
        criteria = []
        if state.goal_statement:
            criteria.append(f"Make visible progress toward: {state.goal_statement}")
        if state.timeline:
            criteria.append(f"Reach a meaningful milestone within {state.timeline}")
        if state.available_time:
            criteria.append(f"Stay executable within {state.available_time}")
        return criteria[:3]

    def _derive_pacing_philosophy(self, state: DiscoveryState) -> str:
        available = (state.available_time or "").lower()
        if any(token in available for token in ("30", "半小时", "45", "40")):
            return "steady"
        if state.timeline and any(token in state.timeline for token in ("30天", "60天", "3个月")):
            return "sprint"
        return "adaptive"

    def _derive_risk_tolerance(self, state: DiscoveryState) -> str:
        prior = " ".join(state.prior_attempts).lower()
        if any(token in prior for token in ("失败", "放弃", "burnout", "quit")):
            return "cautious"
        if state.timeline and any(token in state.timeline for token in ("30天", "60天")):
            return "aggressive"
        return "moderate"

    def _extract_timeline(self, message: str) -> str | None:
        patterns = [
            r"(\d+\s*(?:天|周|个月|月|年))",
            r"(this\s+\w+\s+month)",
            r"(in\s+\d+\s+(?:days|weeks|months|years))",
            r"(\d+\s*(?:days|weeks|months|years))",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_timeline_date(self, timeline: str | None) -> date | None:
        if not timeline:
            return None
        iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", timeline)
        if iso_match:
            try:
                return date.fromisoformat(iso_match.group(1))
            except ValueError:
                return None
        count_match = re.search(r"(\d+)\s*(天|周|个月|月|年|days|weeks|months|years)", timeline, re.IGNORECASE)
        if not count_match:
            return None
        amount = int(count_match.group(1))
        unit = count_match.group(2).lower()
        if unit in {"天", "days"}:
            return date.today() + timedelta(days=amount)
        if unit in {"周", "weeks"}:
            return date.today() + timedelta(weeks=amount)
        if unit in {"个月", "月", "months"}:
            return date.today() + timedelta(days=amount * 30)
        if unit in {"年", "years"}:
            return date.today() + timedelta(days=amount * 365)
        return None

    def _extract_available_time(self, message: str) -> str | None:
        patterns = [
            r"(每天\d+(?:\.\d+)?\s*(?:小时|分钟))",
            r"(每周\d+(?:\.\d+)?\s*(?:小时|分钟))",
            r"(\d+(?:\.\d+)?\s*(?:小时|分钟)\s*每天)",
            r"(\d+(?:\.\d+)?\s*(?:hours?|minutes?)\s*(?:per day|daily|per week|weekly))",
        ]
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_values(self, message: str) -> list[str]:
        values = []
        mapping = {
            "consistency": ("坚持", "稳定", "持续"),
            "meaning": ("意义", "价值"),
            "health": ("健康", "身体"),
            "career": ("职业", "工作", "晋升"),
            "mastery": ("掌握", "精通", "深入"),
        }
        lowered = message.lower()
        for label, tokens in mapping.items():
            if any(token in message or token in lowered for token in tokens):
                values.append(label)
        return values

    def _append_unique(self, items: list[str], value: str) -> None:
        if value not in items:
            items.append(value)

    async def _sync_plan_workflow_state(
        self,
        *,
        plan_card: Card,
        workflow_state: str,
        patch: dict[str, Any] | None = None,
    ) -> None:
        metadata = dict(plan_card.metadata_ or {})
        metadata["workflow_state"] = workflow_state
        if patch:
            metadata.update(patch)
        plan_card.metadata_ = metadata
        plan_card.version += 1
        plan_card.updated_by = CardCreatedBy.SYSTEM
        await self.db.flush()
        logger.info("DiscoveryManager: plan {} moved to workflow {}", plan_card.id, workflow_state)
