from __future__ import annotations

from collections import Counter, OrderedDict
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import cache_service
from app.core.event_bus import event_bus_reliable
from app.models.error_book import ErrorRecord
from app.models.galaxy import KnowledgeNode, UserNodeStatus
from app.services.simulation.simulation_run_store import SimulationRunStore
from app.services.llm_fallback_utils import analysis_llm
from app.services.predictive_service import PredictiveService
from app.services.simulation.participant_generator import generate_participants
from app.services.simulation.scenario_templates import SCENARIOS
from app.services.simulation.simulation_state import LearningSimulationState
from app.services.system_update_service import SystemUpdateService, build_system_update


@dataclass
class AgentParticipant:
    name: str
    role_hint: str
    persona: dict[str, Any]
    stance: str
    source: str
    source_node_name: str | None = None
    context_anchor: str | None = None
    strategy: str = "clarify"
    response_policy: str = "reply_when_addressed"
    memory: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_public_dict(cls, payload: dict[str, Any]) -> AgentParticipant:
        return cls(
            name=str(payload.get("name") or "学习伙伴"),
            role_hint=str(payload.get("role_hint") or ""),
            persona=dict(payload.get("persona") or {}),
            stance=str(payload.get("stance") or "supportive"),
            source=str(payload.get("source") or "template"),
            source_node_name=str(payload.get("source_node_name") or "").strip() or None,
            context_anchor=str(payload.get("context_anchor") or "").strip() or None,
            strategy=str(payload.get("strategy") or ""),
            response_policy=str(payload.get("response_policy") or ""),
            memory=list(payload.get("memory") or []),
        )

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "role_hint": self.role_hint,
            "persona": self.persona,
            "stance": self.stance,
            "source": self.source,
            "source_node_name": self.source_node_name,
            "context_anchor": self.context_anchor,
            "strategy": self.strategy,
            "response_policy": self.response_policy,
        }

    def remember(self, entry: dict[str, Any], *, limit: int = 8) -> None:
        self.memory.append(entry)
        if len(self.memory) > limit:
            self.memory = self.memory[-limit:]


@dataclass
class UserInteractionPoint:
    id: str
    interaction_type: str
    prompt: str
    suggested_replies: list[str]
    options: list[str]
    target_round: int
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "interaction_type": self.interaction_type,
            "prompt": self.prompt,
            "suggested_replies": self.suggested_replies,
            "options": self.options,
            "target_round": self.target_round,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> UserInteractionPoint:
        return cls(
            id=str(payload.get("id") or uuid4()),
            interaction_type=str(payload.get("interaction_type") or "choice"),
            prompt=str(payload.get("prompt") or ""),
            suggested_replies=[
                str(item).strip() for item in list(payload.get("suggested_replies") or []) if str(item).strip()
            ],
            options=[str(item).strip() for item in list(payload.get("options") or []) if str(item).strip()],
            target_round=int(payload.get("target_round") or 0),
            status=str(payload.get("status") or "pending"),
        )


@dataclass
class ModeratorDecision:
    speaker: str
    reply_target: str
    turn_goal: str
    real_time_insight: str
    round_target: int
    should_pause_for_user: bool = False
    should_end: bool = False
    interaction_type: str = "choice"
    interaction_prompt: str = ""
    interaction_options: list[str] = field(default_factory=list)
    suggested_replies: list[str] = field(default_factory=list)


@dataclass
class SimulationSession:
    id: str
    scenario_key: str
    state: LearningSimulationState
    topic: str
    participants: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    insight_summary: str
    anchor_material: str = ""
    anchor_type: str | None = None
    anchor_id: str | None = None
    anchor_status: str = "resolved"
    learning_objective: str | None = None
    interaction_prompt: str = ""
    suggested_replies: list[str] | None = None
    interaction_type: str = "choice"
    interaction_options: list[str] | None = None
    planned_round_count: int = 0
    pending_interaction: dict[str, Any] | None = None
    facilitation_style: str = "balanced"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_key": self.scenario_key,
            "state": self.state.value,
            "topic": self.topic,
            "participants": self.participants,
            "rounds": self.rounds,
            "insight_summary": self.insight_summary,
            "anchor_material": self.anchor_material,
            "anchor_type": self.anchor_type,
            "anchor_id": self.anchor_id,
            "anchor_status": self.anchor_status,
            "learning_objective": self.learning_objective,
            "interaction_prompt": self.interaction_prompt,
            "suggested_replies": list(self.suggested_replies or []),
            "interaction_type": self.interaction_type,
            "interaction_options": list(self.interaction_options or []),
            "planned_round_count": self.planned_round_count,
            "pending_interaction": self.pending_interaction,
            "facilitation_style": self.facilitation_style,
        }


class SimulationEngine:
    SESSION_KEY_PREFIX = "simulation:session:"
    SESSION_TTL_SECONDS = 60 * 60 * 6
    MAX_LOCAL_CHECKPOINTS = 128
    _local_checkpoints: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self.event_bus_reliable = event_bus_reliable

    async def get_session(
        self,
        *,
        session_id: str,
        user_id: UUID | None = None,
    ) -> SimulationSession:
        payload = await self._load_checkpoint(
            session_id=session_id,
            user_id=user_id,
        )
        return self._session_from_payload(
            payload,
            fallback_topic=str(payload.get("topic") or "学习讨论"),
            fallback_scenario=str(payload.get("scenario_key") or "study_group"),
        )

    async def run(
        self,
        *,
        topic: str,
        scenario_key: str,
        planned_round_count: int | None = None,
        participant_names: list[str] | None = None,
        facilitation_style: str = "balanced",
        anchor_material: str | None = None,
        anchor_type: str | None = None,
        anchor_id: str | None = None,
        learning_objective: str | None = None,
        user_id: UUID | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> SimulationSession:
        final_session: SimulationSession | None = None
        async for event_name, payload in self.stream(
            topic=topic,
            scenario_key=scenario_key,
            planned_round_count=planned_round_count,
            participant_names=participant_names,
            facilitation_style=facilitation_style,
            anchor_material=anchor_material,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            learning_objective=learning_objective,
            user_id=user_id,
            user_context=user_context,
            await_user_input=False,
        ):
            if event_name == "complete":
                session_payload = payload.get("session")
                if isinstance(session_payload, dict):
                    final_session = self._session_from_payload(
                        session_payload,
                        fallback_topic=topic,
                        fallback_scenario=scenario_key,
                    )
        if final_session is None:
            raise RuntimeError("Simulation stream completed without a final session payload")
        return final_session

    async def preview(
        self,
        *,
        topic: str,
        scenario_key: str,
        anchor_material: str | None = None,
        anchor_type: str | None = None,
        anchor_id: str | None = None,
        learning_objective: str | None = None,
        user_id: UUID | None = None,
        user_context: dict[str, Any] | None = None,
        max_rounds: int = 3,
    ) -> SimulationSession:
        normalized_scenario_key = scenario_key if scenario_key in SCENARIOS else "study_group"
        template = dict(SCENARIOS.get(normalized_scenario_key) or SCENARIOS["study_group"])
        anchor_context = await self._resolve_anchor_context(
            user_id=user_id,
            topic=topic,
            anchor_material=anchor_material,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
        )
        raw_participants = await generate_participants(
            scenario_key=normalized_scenario_key,
            participant_names=list(template.get("participants") or ["学习伙伴"]),
            user_context=user_context,
            anchor_material=anchor_context["anchor_material"],
            anchor_type=anchor_context["anchor_type"],
            db=self.db,
            user_id=user_id,
            topic=topic,
            participants_from=str(template.get("participants_from") or "") or None,
        )
        participants = self._build_agent_participants(
            raw_participants,
            scenario_key=normalized_scenario_key,
        )
        planned_round_count = max(2, min(max_rounds, 4))
        rounds: list[dict[str, Any]] = []
        latest_insight = f"围绕“{topic}”的讨论刚开始，先用一段轻量预览帮你看到主要分歧。"

        while len(rounds) < planned_round_count:
            fallback = self._fallback_moderator_decision(
                topic=topic,
                scenario_key=normalized_scenario_key,
                participants=participants,
                rounds=rounds,
                planned_round_count=planned_round_count,
            )
            speaker_name = str(fallback.get("speaker") or "").strip()
            speaker = next(
                (participant for participant in participants if participant.name == speaker_name),
                participants[0]
                if participants
                else AgentParticipant(
                    name="学习伙伴",
                    role_hint="学习伙伴",
                    persona={},
                    stance="supportive",
                    source="template",
                ),
            )
            round_item = {
                "round": len(rounds) + 1,
                "speaker": speaker.name,
                "message": self._fallback_round_message(
                    topic=topic,
                    scenario_key=normalized_scenario_key,
                    speaker=speaker,
                    reply_target=str(fallback.get("reply_target") or "").strip(),
                    turn_goal=str(fallback.get("turn_goal") or "extend").strip() or "extend",
                    rounds=rounds,
                ),
                "reply_to_speaker": str(fallback.get("reply_target") or "").strip(),
                "turn_goal": str(fallback.get("turn_goal") or "extend").strip() or "extend",
                "speaker_type": "agent",
            }
            rounds.append(round_item)
            latest_insight = str(fallback.get("real_time_insight") or latest_insight).strip() or latest_insight
            self._update_memories_after_round(
                participants=participants,
                round_item=round_item,
                moderator_insight=latest_insight,
            )

        return SimulationSession(
            id=str(uuid4()),
            scenario_key=normalized_scenario_key,
            state=LearningSimulationState.COMPLETED,
            topic=topic,
            participants=[participant.to_public_dict() for participant in participants],
            rounds=rounds,
            insight_summary=await self._summarize_rounds(topic, rounds),
            anchor_material=anchor_context["anchor_material"],
            anchor_type=anchor_context["anchor_type"],
            anchor_id=anchor_context["anchor_id"],
            anchor_status=anchor_context["anchor_status"],
            learning_objective=learning_objective,
            planned_round_count=planned_round_count,
            interaction_prompt="",
            suggested_replies=[],
            interaction_options=[],
            pending_interaction=None,
        )

    async def continue_run(
        self,
        *,
        session_id: str,
        user_response: str,
        updated_planned_round_count: int | None = None,
        user_id: UUID | None = None,
    ) -> SimulationSession:
        final_session: SimulationSession | None = None
        async for event_name, payload in self.continue_stream(
            session_id=session_id,
            user_response=user_response,
            updated_planned_round_count=updated_planned_round_count,
            user_id=user_id,
            await_user_input=False,
        ):
            if event_name == "complete":
                session_payload = payload.get("session")
                if isinstance(session_payload, dict):
                    final_session = self._session_from_payload(
                        session_payload,
                        fallback_topic="",
                        fallback_scenario="study_group",
                    )
        if final_session is None:
            raise RuntimeError("Simulation continue stream completed without a final session payload")
        return final_session

    async def _resolve_anchor_context(
        self,
        *,
        user_id: UUID | None,
        topic: str,
        anchor_material: str | None,
        anchor_type: str | None,
        anchor_id: str | None,
    ) -> dict[str, Any]:
        explicit_anchor = str(anchor_material or "").strip()
        if explicit_anchor:
            return {
                "anchor_material": explicit_anchor,
                "anchor_type": str(anchor_type or "concept").strip() or "concept",
                "anchor_id": str(anchor_id or "").strip() or None,
                "anchor_status": "provided",
            }
        if self.db is None or user_id is None or not str(topic or "").strip():
            return {
                "anchor_material": "",
                "anchor_type": str(anchor_type or "").strip() or None,
                "anchor_id": str(anchor_id or "").strip() or None,
                "anchor_status": "no_anchor",
            }
        error_rows = await self._find_related_error_anchors(user_id=user_id, topic=topic, limit=3)
        if error_rows:
            return {
                "anchor_material": "\n\n".join(error_rows),
                "anchor_type": str(anchor_type or "error_record").strip() or "error_record",
                "anchor_id": str(anchor_id or "").strip() or None,
                "anchor_status": "resolved",
            }
        concept_rows = await self._find_related_concept_anchors(user_id=user_id, topic=topic, limit=3)
        if concept_rows:
            return {
                "anchor_material": "\n\n".join(concept_rows),
                "anchor_type": str(anchor_type or "concept").strip() or "concept",
                "anchor_id": str(anchor_id or "").strip() or None,
                "anchor_status": "resolved",
            }
        return {
            "anchor_material": "",
            "anchor_type": str(anchor_type or "").strip() or None,
            "anchor_id": str(anchor_id or "").strip() or None,
            "anchor_status": "no_anchor",
        }

    async def _find_related_error_anchors(
        self,
        *,
        user_id: UUID,
        topic: str,
        limit: int,
    ) -> list[str]:
        topic_lower = str(topic or "").strip().lower()
        if not topic_lower:
            return []
        rows = (
            await self.db.execute(
                select(
                    ErrorRecord.id,
                    ErrorRecord.chapter,
                    ErrorRecord.question_text,
                    ErrorRecord.user_answer,
                    ErrorRecord.correct_answer,
                    ErrorRecord.latest_analysis,
                )
                .where(ErrorRecord.user_id == user_id, ErrorRecord.is_deleted.is_(False))
                .order_by(ErrorRecord.updated_at.desc(), ErrorRecord.created_at.desc())
                .limit(40)
            )
        ).all()
        anchors: list[str] = []
        for error_id, chapter, question_text, user_answer, correct_answer, latest_analysis in rows:
            haystack = " ".join(
                [
                    str(chapter or ""),
                    str(question_text or ""),
                    str(user_answer or ""),
                    str(correct_answer or ""),
                    json.dumps(latest_analysis, ensure_ascii=False)
                    if isinstance(latest_analysis, dict)
                    else str(latest_analysis or ""),
                ]
            ).lower()
            if topic_lower not in haystack:
                continue
            anchors.append(

                    f"错题锚点 {error_id}："
                    f"题目={str(question_text or chapter or '').strip()}；"
                    f"你的答案={str(user_answer or '未记录').strip()}；"
                    f"正确答案={str(correct_answer or '未记录').strip()}；"
                    f"分析={str((latest_analysis or {}).get('root_cause') if isinstance(latest_analysis, dict) else latest_analysis or '').strip() or '未记录'}"

            )
            if len(anchors) >= limit:
                break
        return anchors

    async def _find_related_concept_anchors(
        self,
        *,
        user_id: UUID,
        topic: str,
        limit: int,
    ) -> list[str]:
        topic_lower = str(topic or "").strip().lower()
        if not topic_lower:
            return []
        rows = (
            await self.db.execute(
                select(
                    KnowledgeNode.id,
                    KnowledgeNode.name,
                    KnowledgeNode.description,
                    UserNodeStatus.mastery_score,
                )
                .outerjoin(
                    UserNodeStatus,
                    (UserNodeStatus.node_id == KnowledgeNode.id) & (UserNodeStatus.user_id == user_id),
                )
                .where(
                    (KnowledgeNode.name.ilike(f"%{topic_lower}%"))
                    | (KnowledgeNode.description.ilike(f"%{topic_lower}%"))
                )
                .order_by(UserNodeStatus.mastery_score.asc().nullsfirst(), KnowledgeNode.created_at.desc())
                .limit(limit)
            )
        ).all()
        return [
            (
                f"概念锚点 {node_id}："
                f"{str(name or '').strip()}；"
                f"说明={str(description or '').strip() or '暂无描述'}；"
                f"掌握度={('[数据不足]' if mastery_score is None else f'{round(float(mastery_score or 0.0))}%')}"
            )
            for node_id, name, description, mastery_score in rows
            if str(name or "").strip()
        ]

    async def stream(
        self,
        *,
        topic: str,
        scenario_key: str,
        planned_round_count: int | None = None,
        participant_names: list[str] | None = None,
        facilitation_style: str = "balanced",
        anchor_material: str | None = None,
        anchor_type: str | None = None,
        anchor_id: str | None = None,
        learning_objective: str | None = None,
        user_id: UUID | None = None,
        user_context: dict[str, Any] | None = None,
        await_user_input: bool = True,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        session_id = str(uuid4())
        normalized_scenario_key = scenario_key if scenario_key in SCENARIOS else "study_group"
        template = dict(SCENARIOS.get(normalized_scenario_key) or SCENARIOS["study_group"])
        normalized_facilitation_style = self._normalize_facilitation_style(facilitation_style)
        anchor_context = await self._resolve_anchor_context(
            user_id=user_id,
            topic=topic,
            anchor_material=anchor_material,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
        )
        resolved_participant_names = self._resolve_participant_names(
            participant_names=participant_names,
            template=template,
        )

        yield (
            "status",
            {
                "session_id": session_id,
                "state": LearningSimulationState.PREPARING.value,
                "progress": 0.08,
                "topic": topic,
                "scenario_key": normalized_scenario_key,
                "planned_round_count": planned_round_count,
                "facilitation_style": normalized_facilitation_style,
                "anchor_status": anchor_context["anchor_status"],
            },
        )

        raw_participants = await generate_participants(
            scenario_key=normalized_scenario_key,
            participant_names=resolved_participant_names,
            user_context=user_context,
            anchor_material=anchor_context["anchor_material"],
            anchor_type=anchor_context["anchor_type"],
            db=self.db,
            user_id=user_id,
            topic=topic,
            participants_from=str(template.get("participants_from") or "") or None,
        )
        participants = self._build_agent_participants(raw_participants, scenario_key=normalized_scenario_key)
        yield (
            "participants",
            {
                "session_id": session_id,
                "state": LearningSimulationState.RUNNING.value,
                "progress": 0.18,
                "participants": [participant.to_public_dict() for participant in participants],
            },
        )

        async for item in self._stream_from_checkpoint(
            session_id=session_id,
            topic=topic,
            scenario_key=normalized_scenario_key,
            participants=participants,
            rounds=[],
            planned_round_count=self._initial_round_target(
                template.get("rounds"),
                requested_rounds=planned_round_count,
                scenario_key=normalized_scenario_key,
            ),
            facilitation_style=normalized_facilitation_style,
            anchor_material=anchor_context["anchor_material"],
            anchor_type=anchor_context["anchor_type"],
            anchor_id=anchor_context["anchor_id"],
            anchor_status=anchor_context["anchor_status"],
            learning_objective=learning_objective,
            user_id=user_id,
            await_user_input=await_user_input,
        ):
            yield item

    async def continue_stream(
        self,
        *,
        session_id: str,
        user_response: str,
        updated_planned_round_count: int | None = None,
        user_id: UUID | None = None,
        await_user_input: bool = True,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        checkpoint = await self._load_checkpoint(session_id=session_id, user_id=user_id)
        participants = [
            AgentParticipant.from_public_dict(item)
            for item in list(checkpoint.get("participants") or [])
            if isinstance(item, dict)
        ]
        rounds = [dict(item) for item in list(checkpoint.get("rounds") or []) if isinstance(item, dict)]
        topic = str(checkpoint.get("topic") or "")
        scenario_key = str(checkpoint.get("scenario_key") or "study_group")
        planned_round_count = max(int(checkpoint.get("planned_round_count") or 0), 3)
        if updated_planned_round_count is not None:
            planned_round_count = max(
                len(rounds) + 2,
                self._normalize_round_target(
                    updated_planned_round_count,
                    current_rounds=0,
                    scenario_key=scenario_key,
                ),
            )
        facilitation_style = self._normalize_facilitation_style(
            str(checkpoint.get("facilitation_style") or "balanced"),
        )
        anchor_material = str(checkpoint.get("anchor_material") or "")
        anchor_type = str(checkpoint.get("anchor_type") or "").strip() or None
        anchor_id = str(checkpoint.get("anchor_id") or "").strip() or None
        anchor_status = str(checkpoint.get("anchor_status") or "resolved")
        learning_objective = str(checkpoint.get("learning_objective") or "").strip() or None

        if user_response.strip():
            user_round = {
                "round": len(rounds) + 1,
                "speaker": "你",
                "message": user_response.strip(),
                "reply_to_speaker": self._pending_interaction_target_speaker(checkpoint.get("pending_interaction")),
                "turn_goal": "user_response",
                "speaker_type": "user",
            }
            rounds.append(user_round)
            self._update_memories_after_round(
                participants=participants,
                round_item=user_round,
                moderator_insight="用户明确给出了自己的判断，这能帮助下一轮讨论更贴近真实学习决策。",
            )
            yield (
                "round",
                {
                    "session_id": session_id,
                    "state": LearningSimulationState.RUNNING.value,
                    "progress": min(0.55, 0.22 + len(rounds) * 0.08),
                    "round": user_round,
                    "rounds": rounds,
                },
            )

        async for item in self._stream_from_checkpoint(
            session_id=session_id,
            topic=topic,
            scenario_key=scenario_key,
            participants=participants,
            rounds=rounds,
            planned_round_count=max(planned_round_count, len(rounds) + 2),
            facilitation_style=facilitation_style,
            anchor_material=anchor_material,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            anchor_status=anchor_status,
            learning_objective=learning_objective,
            user_id=user_id,
            await_user_input=await_user_input,
        ):
            yield item

    async def _stream_from_checkpoint(
        self,
        *,
        session_id: str,
        topic: str,
        scenario_key: str,
        participants: list[AgentParticipant],
        rounds: list[dict[str, Any]],
        planned_round_count: int,
        facilitation_style: str,
        anchor_material: str,
        anchor_type: str | None,
        anchor_id: str | None,
        anchor_status: str,
        learning_objective: str | None,
        user_id: UUID | None,
        await_user_input: bool,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        behavioral_context: dict[str, Any] | None = None
        if user_id is not None:
            try:
                predictive_service = PredictiveService(self.db)
                behavioral_context = {
                    "mastery_gaps": await self._get_user_mastery_gaps(user_id),
                    "next_intent_forecast": await predictive_service.get_next_intent_forecast(
                        user_id,
                    ),
                    "dropout_risk": await predictive_service.detect_dropout_risk(
                        user_id,
                    ),
                }
            except Exception:
                behavioral_context = None

        while len(rounds) < max(planned_round_count, 2):
            moderator_decision = await self._moderate_next_turn(
                topic=topic,
                scenario_key=scenario_key,
                participants=participants,
                rounds=rounds,
                planned_round_count=planned_round_count,
                facilitation_style=facilitation_style,
                anchor_material=anchor_material,
                anchor_type=anchor_type,
                learning_objective=learning_objective,
                behavioral_context=behavioral_context,
            )
            planned_round_count = self._normalize_round_target(
                moderator_decision.round_target,
                current_rounds=len(rounds),
                scenario_key=scenario_key,
            )
            round_item = await self._generate_agent_round(
                topic=topic,
                scenario_key=scenario_key,
                participants=participants,
                rounds=rounds,
                moderator_decision=moderator_decision,
                facilitation_style=facilitation_style,
                anchor_material=anchor_material,
                learning_objective=learning_objective,
            )
            rounds.append(round_item)
            self._update_memories_after_round(
                participants=participants,
                round_item=round_item,
                moderator_insight=moderator_decision.real_time_insight,
            )
            progress = min(0.92, 0.18 + (0.62 * (len(rounds) / max(planned_round_count, 1))))
            yield (
                "round",
                {
                    "session_id": session_id,
                    "state": LearningSimulationState.RUNNING.value,
                    "progress": progress,
                    "round": round_item,
                    "rounds": rounds,
                },
            )
            yield (
                "insight",
                {
                    "session_id": session_id,
                    "state": LearningSimulationState.RUNNING.value,
                    "progress": progress,
                    "message": moderator_decision.real_time_insight,
                },
            )

            interaction = await self._build_user_interaction_point(
                topic=topic,
                participants=participants,
                rounds=rounds,
                moderator_decision=moderator_decision,
                anchor_material=anchor_material,
            )
            if await_user_input and interaction is not None and not moderator_decision.should_end:
                session = SimulationSession(
                    id=session_id,
                    scenario_key=scenario_key,
                    state=LearningSimulationState.WAITING_FOR_USER,
                    topic=topic,
                    participants=[participant.to_public_dict() for participant in participants],
                    rounds=rounds,
                    insight_summary=moderator_decision.real_time_insight,
                    anchor_material=anchor_material,
                    anchor_type=anchor_type,
                    anchor_id=anchor_id,
                    anchor_status=anchor_status,
                    learning_objective=learning_objective,
                    interaction_prompt=interaction.prompt,
                    suggested_replies=interaction.suggested_replies,
                    interaction_type=interaction.interaction_type,
                    interaction_options=interaction.options,
                    planned_round_count=planned_round_count,
                    pending_interaction=interaction.to_dict(),
                    facilitation_style=facilitation_style,
                )
                await self._persist_checkpoint(
                    user_id=user_id,
                    session=session,
                    participants=participants,
                )
                yield (
                    "interaction",
                    {
                        "session_id": session_id,
                        "state": LearningSimulationState.WAITING_FOR_USER.value,
                        "progress": progress,
                        "interaction": interaction.to_dict(),
                        "participants": [participant.to_public_dict() for participant in participants],
                        "rounds": rounds,
                    },
                )
                yield (
                    "complete",
                    {
                        "session_id": session_id,
                        "state": LearningSimulationState.WAITING_FOR_USER.value,
                        "progress": progress,
                        "session": session.to_dict(),
                    },
                )
                return

            if moderator_decision.should_end and len(rounds) >= 2:
                break

        insight_summary = await self._summarize_rounds(topic, rounds)
        session = SimulationSession(
            id=session_id,
            scenario_key=scenario_key,
            state=LearningSimulationState.COMPLETED,
            topic=topic,
            participants=[participant.to_public_dict() for participant in participants],
            rounds=rounds,
            insight_summary=insight_summary,
            anchor_material=anchor_material,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            anchor_status=anchor_status,
            learning_objective=learning_objective,
            planned_round_count=planned_round_count,
            facilitation_style=facilitation_style,
        )
        await cache_service.delete(f"{self.SESSION_KEY_PREFIX}{session_id}")
        if user_id is not None:
            await self._persist_simulation_insights(session=session, user_id=str(user_id))
            await self._persist_session_update(user_id=user_id, session=session)
        yield (
            "complete",
            {
                "session_id": session_id,
                "state": LearningSimulationState.COMPLETED.value,
                "progress": 1.0,
                "session": session.to_dict(),
            },
        )

    def _build_agent_participants(
        self,
        raw_participants: list[dict[str, Any]],
        *,
        scenario_key: str,
    ) -> list[AgentParticipant]:
        participants: list[AgentParticipant] = []
        for index, item in enumerate(raw_participants):
            participant = AgentParticipant.from_public_dict(item)
            participant.strategy = participant.strategy or self._resolve_strategy(
                scenario_key=scenario_key,
                participant=participant,
                index=index,
            )
            participant.response_policy = self._resolve_response_policy(
                scenario_key=scenario_key,
                participant=participant,
                index=index,
            )
            participants.append(participant)
        return participants

    def _resolve_strategy(self, *, scenario_key: str, participant: AgentParticipant, index: int) -> str:
        if scenario_key == "knowledge_debate":
            return ["defend", "challenge", "moderate"][min(index, 2)]
        if scenario_key == "socratic_dialogue":
            return "probe"
        if scenario_key == "historical_roleplay":
            return ["immerse", "contextualize", "reflect"][min(index, 2)]
        if scenario_key == "case_analysis":
            return ["frame_case", "diagnose", "ground_in_action"][min(index, 2)]
        if scenario_key == "what_if_path":
            return ["project_baseline", "push_upside", "surface_risk"][min(index, 2)]
        if scenario_key == "concept_map_build":
            return ["structure", "bridge", "stress_test"][min(index, 2)]
        if scenario_key == "error_diagnosis":
            return ["trace_root_cause", "coach_fix", "verify_transfer"][min(index, 2)]
        if participant.stance == "challenging":
            return "diagnose"
        if participant.stance == "supportive":
            return "scaffold"
        return "clarify"

    def _resolve_response_policy(
        self,
        *,
        scenario_key: str,
        participant: AgentParticipant,
        index: int,
    ) -> str:
        if scenario_key == "socratic_dialogue":
            return "always_reply_with_question"
        if scenario_key == "knowledge_debate":
            return "speak_on_conflict"
        if scenario_key == "case_analysis":
            return "anchor_on_evidence"
        if scenario_key == "what_if_path":
            return "compare_tradeoffs"
        if scenario_key == "concept_map_build":
            return "add_dependency_or_gap"
        if scenario_key == "error_diagnosis":
            return "only_speak_when_root_cause_or_fix_is_clear"
        if participant.stance in {"challenging", "opposing"}:
            return "enter_when_claim_is_weak"
        if index == 0:
            return "open_then_synthesize"
        return "reply_when_addressed"

    async def _moderate_next_turn(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[AgentParticipant],
        rounds: list[dict[str, Any]],
        planned_round_count: int,
        facilitation_style: str,
        anchor_material: str,
        anchor_type: str | None = None,
        learning_objective: str | None = None,
        behavioral_context: dict[str, Any] | None = None,
    ) -> ModeratorDecision:
        fallback = self._fallback_moderator_decision(
            topic=topic,
            scenario_key=scenario_key,
            participants=participants,
            rounds=rounds,
            planned_round_count=planned_round_count,
            facilitation_style=facilitation_style,
        )
        participant_prompt = (
            "\n".join(
                (
                    f"- {participant.name}: role={participant.role_hint}; stance={participant.stance}; "
                    f"strategy={participant.strategy}; response_policy={participant.response_policy}; "
                    f"memory={participant.memory[-5:]}"
                )
                for participant in participants
            )
            or "- 学习伙伴"
        )
        transcript = self._latest_exchange(rounds, limit=4)
        behavioral_context_block = self._format_behavioral_context(
            behavioral_context,
        )
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是一场多 Agent 学习仿真的主持人。\n"
                        "你的目标不是让讨论好看，而是帮助用户发现自己的理解盲区。\n\n"
                        "你是苏格拉底式学习引导者。请围绕锚点材料设计下一步认知探测。\n\n"
                        "## 决策标准\n"
                        "- speaker: 选择当前最适合暴露理解偏差的角色。\n"
                        "- should_pause_for_user: 当需要检测用户理解深度、验证用户是否识别误解时设为 true。\n"
                        "- should_end: 只有在已经清楚暴露出盲区或用户已经完成一次有效的深度解释时才设为 true。\n"
                        "- interaction_type: 优先选择能检测理解深度的提问方式。\n\n"
                        "## 认知探测原则\n"
                        "- 提出与锚点相关的不同角度或解释。\n"
                        "- 可以故意引入常见误解，看用户是否能识别。\n"
                        "- 用户发言后优先追问“为什么”，而不是追求讨论流畅。\n"
                        "- 如果用户理解有偏差，不直接纠正，而是通过反例、迁移或追问让用户自己发现。\n"
                        "- 如果用户理解较扎实，就提高难度，引入边界案例或迁移场景。\n\n"
                        "## 场景适配\n"
                        "- study_group: 更强调协作式整合\n"
                        "- knowledge_debate: 放大分歧并要求依据\n"
                        "- socratic_dialogue: 用连续追问加深思考\n"
                        "- case_analysis: 紧贴具体案例与决策节点\n"
                        "- what_if_path: 对比不同选择的后果\n"
                        "- concept_map_build: 重点说清概念依赖与连接\n"
                        "- error_diagnosis: 优先锁定根因与修补动作\n\n"
                        "## 展开风格\n"
                        "- balanced: 平衡不同角度，但仍以检测理解为优先\n"
                        "- debate: 放大冲突与误解，用反例逼近真实理解边界\n"
                        "- guided: 更像导师拆解概念，连续追问用户的依据\n"
                        "- practical: 优先把概念应用到具体情境或题目上\n\n"
                        "## 语言要求\n"
                        "- real_time_insight、interaction_prompt、interaction_options、suggested_replies 必须使用自然、简体中文。\n"
                        "- speaker、reply_target、turn_goal、interaction_type 保持机器可读格式，不要翻译成中文键值。\n"
                        "- 不要输出英文教学腔，不要使用生硬直译。\n\n"
                        "只返回严格 JSON，键必须包含 speaker, reply_target, turn_goal, real_time_insight, "
                        "round_target, should_pause_for_user, should_end, interaction_type, interaction_prompt, "
                        "interaction_options, suggested_replies。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"主题：{topic}\n"
                        f"当前学习锚点：{anchor_material or '[暂无锚点]'}\n"
                        f"锚点类型：{anchor_type or 'unknown'}\n"
                        f"学习目标：{learning_objective or '未提供'}\n"
                        f"场景：{scenario_key}\n"
                        f"展开风格：{facilitation_style}\n"
                        f"当前轮次：{len(rounds)}\n"
                        f"计划轮次：{planned_round_count}\n"
                        f"参与者：\n{participant_prompt}\n"
                        f"最近讨论：\n{transcript}\n"
                        f"{behavioral_context_block}"
                        "请判断下一位发言者、是否该邀请用户加入，以及讨论是否已经可以收束。"
                    ),
                },
            ],
            fallback=fallback,
            temperature=0.25,
        )
        payload = data if isinstance(data, dict) else fallback
        participant_names = {participant.name for participant in participants}
        speaker = str(payload.get("speaker") or fallback["speaker"]).strip() or fallback["speaker"]
        if speaker not in participant_names:
            speaker = fallback["speaker"]
        reply_target = str(payload.get("reply_target") or fallback["reply_target"]).strip()
        if reply_target and reply_target not in participant_names and reply_target != "你":
            reply_target = fallback["reply_target"]
        return ModeratorDecision(
            speaker=speaker,
            reply_target=reply_target,
            turn_goal=str(payload.get("turn_goal") or fallback["turn_goal"]).strip() or fallback["turn_goal"],
            real_time_insight=str(payload.get("real_time_insight") or fallback["real_time_insight"]).strip()
            or fallback["real_time_insight"],
            round_target=self._normalize_round_target(
                payload.get("round_target"),
                current_rounds=len(rounds),
                scenario_key=scenario_key,
            ),
            should_pause_for_user=bool(payload.get("should_pause_for_user")),
            should_end=bool(payload.get("should_end")),
            interaction_type=str(payload.get("interaction_type") or fallback["interaction_type"]).strip()
            or fallback["interaction_type"],
            interaction_prompt=str(payload.get("interaction_prompt") or fallback["interaction_prompt"]).strip()
            or fallback["interaction_prompt"],
            interaction_options=self._string_list(payload.get("interaction_options"))
            or list(fallback["interaction_options"]),
            suggested_replies=self._string_list(payload.get("suggested_replies"))
            or list(fallback["suggested_replies"]),
        )

    def _fallback_moderator_decision(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[AgentParticipant],
        rounds: list[dict[str, Any]],
        planned_round_count: int,
        facilitation_style: str = "balanced",
    ) -> dict[str, Any]:
        if not participants:
            return {
                "speaker": "学习伙伴",
                "reply_target": "",
                "turn_goal": "open",
                "real_time_insight": f"围绕“{topic}”的讨论刚开始，还需要先建立共同问题。",
                "round_target": max(planned_round_count, 3),
                "should_pause_for_user": False,
                "should_end": False,
                "interaction_type": "choice",
                "interaction_prompt": "",
                "interaction_options": [],
                "suggested_replies": [],
            }

        speaker_counts = Counter(str(item.get("speaker") or "").strip() for item in rounds if item.get("speaker"))
        last_speaker = str(rounds[-1].get("speaker") or "").strip() if rounds else ""
        ordered = sorted(
            participants,
            key=lambda item: (speaker_counts.get(item.name, 0), 1 if item.name == last_speaker else 0),
        )
        chosen = ordered[0]
        reply_target = next(
            (
                str(item.get("speaker") or "").strip()
                for item in reversed(rounds)
                if str(item.get("speaker") or "").strip() != chosen.name
            ),
            "",
        )
        should_pause = len(rounds) >= 1 and all(str(item.get("speaker") or "") != "你" for item in rounds[-2:])
        interaction_prompt = (
            f"讨论已经推进到“{topic}”的关键分歧点。现在轮到你：你会支持哪种理解，还是补一个自己的判断？"
            if should_pause
            else ""
        )
        real_time_insight = f"{chosen.name} 更适合在这一轮接棒，因为当前讨论还缺少“{chosen.strategy}”视角。"
        if facilitation_style == "debate":
            real_time_insight = f"{chosen.name} 这一轮会把争议点挑明，逼近“{topic}”里最站不住脚的前提。"
        elif facilitation_style == "guided":
            real_time_insight = f"{chosen.name} 这一轮更适合把“{topic}”拆小，让用户更容易跟上推理链。"
        elif facilitation_style == "practical":
            real_time_insight = f"{chosen.name} 这一轮会把讨论拉回应用与验证，避免“{topic}”停在抽象表述。"
        return {
            "speaker": chosen.name,
            "reply_target": reply_target,
            "turn_goal": "synthesize"
            if len(rounds) + 1 >= planned_round_count
            else ("probe" if scenario_key == "socratic_dialogue" else "extend"),
            "real_time_insight": real_time_insight,
            "round_target": max(planned_round_count, 3 + int(len(rounds) >= 2)),
            "should_pause_for_user": should_pause,
            "should_end": len(rounds) + 1 >= planned_round_count and len(rounds) >= 2,
            "interaction_type": "forced_choice" if scenario_key != "socratic_dialogue" else "open_question",
            "interaction_prompt": interaction_prompt,
            "interaction_options": [participant.name for participant in participants[:3]],
            "suggested_replies": [
                f"我会先把“{topic}”拆成两步，再判断哪一步最值得先补。",
                f"我更想追问 {reply_target or chosen.name} 刚才那条判断为什么成立。",
                "我会先给自己定一个 20 分钟的小练习验证当前结论。",
            ],
        }

    async def _generate_agent_round(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[AgentParticipant],
        rounds: list[dict[str, Any]],
        moderator_decision: ModeratorDecision,
        facilitation_style: str = "balanced",
        anchor_material: str = "",
        learning_objective: str | None = None,
    ) -> dict[str, Any]:
        speaker = next(
            (participant for participant in participants if participant.name == moderator_decision.speaker), None
        )
        if speaker is None:
            speaker = participants[0]
        fallback_message = self._fallback_round_message(
            topic=topic,
            scenario_key=scenario_key,
            speaker=speaker,
            reply_target=moderator_decision.reply_target,
            turn_goal=moderator_decision.turn_goal,
            rounds=rounds,
            anchor_material=anchor_material,
        )
        room_state = (
            "\n".join(f"- {participant.name}: memory={participant.memory[-5:]}" for participant in participants)
            or "No room state yet."
        )
        cross_agent_summary = self._cross_agent_summary(
            participants=participants,
            speaker_name=speaker.name,
        )
        transcript = self._latest_exchange(rounds, limit=5)
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是学习仿真中的一个参与角色。"
                        "请只返回严格 JSON，包含 message, reply_to_speaker, turn_goal 三个键。"
                        "其中 message 必须使用自然、简体中文，语气像真实讨论，不要写成英文或翻译腔。"
                        "reply_to_speaker 保持参与者名字；turn_goal 保持机器可读的内部标识。"
                        "你的发言必须围绕锚点材料，2-4 句话，每句话都要有信息量。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"讨论锚点（所有发言必须围绕此材料）：{anchor_material or speaker.context_anchor or '暂无锚点'}\n"
                        f"学习目标：{learning_objective or '未提供'}\n"
                        f"主题：{topic}\n"
                        f"场景：{scenario_key}\n"
                        f"展开风格：{facilitation_style}\n"
                        f"发言角色：{speaker.name}\n"
                        f"角色提示：{speaker.role_hint}\n"
                        f"立场：{speaker.stance}\n"
                        f"策略：{speaker.strategy}\n"
                        f"回应策略：{speaker.response_policy}\n"
                        f"语境锚点：{speaker.context_anchor or '无'}\n"
                        f"个人记忆：{speaker.memory[-5:]}\n"
                        f"房间状态：\n{room_state}\n"
                        f"其他角色最近观点：\n{cross_agent_summary or '暂无'}\n"
                        f"最近讨论：\n{transcript}\n"
                        f"回应对象：{moderator_decision.reply_target or '全场'}\n"
                        f"本轮目标：{moderator_decision.turn_goal}\n"
                        "请生成直接回应锚点材料的中文发言。"
                    ),
                },
            ],
            fallback={
                "message": fallback_message,
                "reply_to_speaker": moderator_decision.reply_target,
                "turn_goal": moderator_decision.turn_goal,
            },
            temperature=0.4,
        )
        payload = data if isinstance(data, dict) else {}
        return {
            "round": len(rounds) + 1,
            "speaker": speaker.name,
            "message": str(payload.get("message") or fallback_message).strip() or fallback_message,
            "reply_to_speaker": str(payload.get("reply_to_speaker") or moderator_decision.reply_target).strip(),
            "turn_goal": str(payload.get("turn_goal") or moderator_decision.turn_goal).strip()
            or moderator_decision.turn_goal,
            "speaker_type": "agent",
        }

    def _fallback_round_message(
        self,
        *,
        topic: str,
        scenario_key: str,
        speaker: AgentParticipant,
        reply_target: str,
        turn_goal: str,
        rounds: list[dict[str, Any]],
        anchor_material: str = "",
    ) -> str:
        anchor_hint = f"锚点材料是：{anchor_material[:80]}。" if anchor_material else ""
        if reply_target:
            if speaker.strategy in {"challenge", "diagnose", "defend"}:
                return (
                    f"{anchor_hint}我想回应 {reply_target} 刚才关于“{topic}”的说法。"
                    f" 如果只停在那个结论上，还没有解释清楚它为什么成立，或者何时会失效。"
                )
            if speaker.strategy == "probe":
                return (
                    f"{anchor_hint}顺着 {reply_target} 的说法，我会继续追问：在“{topic}”里最不能默认成立的前提是什么？"
                )
        if turn_goal == "synthesize":
            return f"{anchor_hint}如果先把围绕“{topic}”已经形成的共识收束一下，下一步最值得验证的就是哪条解释真正能落到题目里。"
        if scenario_key == "what_if_path":
            return f"{anchor_hint}如果把“{topic}”换一条走法，我会先比较节奏、风险和最先见效的环节。"
        if scenario_key == "concept_map_build":
            return f"{anchor_hint}围绕“{topic}”，我想先指出一个前置依赖和一个最容易断掉的连接。"
        if scenario_key == "error_diagnosis":
            return f"{anchor_hint}我会先把“{topic}”里最像表面错误的现象拆开，看看真正根因是不是前置概念没有稳住。"
        if scenario_key == "historical_roleplay" and speaker.context_anchor:
            return f"{anchor_hint}把“{topic}”放回 {speaker.context_anchor} 这个语境里，你会更容易看清它为什么重要。"
        if rounds:
            return f"{anchor_hint}基于前面已经出现的分歧，我想从 {speaker.role_hint or speaker.name} 的角度继续检验“{topic}”的理解。"
        return f"{anchor_hint}围绕“{topic}”，我想先从 {speaker.role_hint or speaker.name} 的角度解释最关键的一步。"

    async def _build_user_interaction_point(
        self,
        *,
        topic: str,
        participants: list[AgentParticipant],
        rounds: list[dict[str, Any]],
        moderator_decision: ModeratorDecision,
        anchor_material: str = "",
    ) -> UserInteractionPoint | None:
        if not moderator_decision.should_pause_for_user:
            return None
        transcript_summary = self._latest_exchange(rounds, limit=4)
        fallback_prompt = moderator_decision.interaction_prompt.strip() or (
            f"把“{topic}”应用到一个新情境里：如果关键条件变了，你觉得结论还成立吗？为什么？"
        )
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你要设计一个能检测用户理解深度的问题。只返回严格 JSON，包含 prompt, suggested_replies。"
                        "问题不能只靠回忆回答，必须要求用户做迁移、比较、解释反直觉现象，或预测条件变化。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"当前讨论锚点：{anchor_material or '[暂无锚点]'}\n"
                        f"主题：{topic}\n"
                        f"到目前的讨论进展：\n{transcript_summary}\n"
                        "请设计一个诊断性提问，优先暴露用户可能没真正理解的地方。"
                    ),
                },
            ],
            fallback={
                "prompt": fallback_prompt,
                "suggested_replies": moderator_decision.suggested_replies,
            },
            temperature=0.2,
        )
        payload = data if isinstance(data, dict) else {}
        prompt = str(payload.get("prompt") or fallback_prompt).strip() or fallback_prompt
        options = moderator_decision.interaction_options or [participant.name for participant in participants[:3]]
        suggested = (
            self._string_list(payload.get("suggested_replies"))
            or moderator_decision.suggested_replies
            or [
                "我会先说明这个结论在什么条件下成立。",
                "我会用一个新例子测试这条解释能不能迁移。",
            ]
        )
        return UserInteractionPoint(
            id=str(uuid4()),
            interaction_type=moderator_decision.interaction_type or "choice",
            prompt=prompt,
            suggested_replies=suggested[:3],
            options=options[:3],
            target_round=len(rounds),
        )

    @staticmethod
    def _cross_agent_summary(
        *,
        participants: list[AgentParticipant],
        speaker_name: str,
    ) -> str:
        lines: list[str] = []
        for participant in participants:
            if participant.name == speaker_name or not participant.memory:
                continue
            latest = participant.memory[-1]
            latest_message = str(
                latest.get("message") or latest.get("insight") or latest.get("turn_goal") or ""
            ).strip()
            if latest_message:
                lines.append(f"- {participant.name} 最近观点: {latest_message}")
        return "\n".join(lines)

    def _update_memories_after_round(
        self,
        *,
        participants: list[AgentParticipant],
        round_item: dict[str, Any],
        moderator_insight: str,
    ) -> None:
        speaker_name = str(round_item.get("speaker") or "").strip()
        message = str(round_item.get("message") or "").strip()
        for participant in participants:
            if participant.name == speaker_name:
                participant.remember(
                    {
                        "kind": "self_turn",
                        "round": round_item.get("round"),
                        "message": message,
                        "turn_goal": round_item.get("turn_goal"),
                    }
                )
            else:
                participant.remember(
                    {
                        "kind": "observed_turn",
                        "speaker": speaker_name,
                        "round": round_item.get("round"),
                        "message": message[:120],
                        "insight": moderator_insight[:120],
                    }
                )

    def _initial_round_target(
        self,
        configured_rounds: object,
        *,
        scenario_key: str,
        requested_rounds: int | None = None,
    ) -> int:
        if requested_rounds is not None:
            return self._normalize_round_target(
                requested_rounds,
                current_rounds=0,
                scenario_key=scenario_key,
            )
        if str(configured_rounds) == "dynamic":
            return 4
        return self._normalize_round_target(
            configured_rounds,
            current_rounds=0,
            scenario_key=scenario_key,
        )

    @staticmethod
    def _normalize_facilitation_style(style: str | None) -> str:
        normalized = str(style or "").strip().lower()
        if normalized in {"debate", "guided", "practical"}:
            return normalized
        return "balanced"

    @staticmethod
    def _resolve_participant_names(
        *,
        participant_names: list[str] | None,
        template: dict[str, Any],
    ) -> list[str]:
        cleaned = [str(item).strip() for item in list(participant_names or []) if str(item).strip()]
        deduped = list(dict.fromkeys(cleaned))
        if deduped:
            return deduped[:6]
        return [
            str(item).strip() for item in list(template.get("participants") or ["学习伙伴"]) if str(item).strip()
        ] or ["学习伙伴"]

    def _normalize_round_target(
        self,
        requested: object,
        *,
        current_rounds: int,
        scenario_key: str = "study_group",
    ) -> int:
        try:
            requested_int = int(requested or 4)
        except (TypeError, ValueError):
            requested_int = 4
        scenario_max = {
            "study_group": 10,
            "knowledge_debate": 12,
            "historical_roleplay": 12,
            "socratic_dialogue": 9,
            "case_analysis": 12,
            "what_if_path": 10,
            "concept_map_build": 10,
            "error_diagnosis": 12,
        }.get(str(scenario_key or "study_group"), 10)
        return max(current_rounds + 1, min(max(requested_int, 3), scenario_max))

    async def _summarize_rounds(self, topic: str, rounds: list[dict[str, Any]]) -> str:
        if not rounds:
            return f"围绕 {topic} 的模拟还没有形成有效洞察。"
        transcript = "\n".join(
            f"第 {int(item.get('round') or index + 1)} 轮 | "
            f"{str(item.get('speaker') or '未知角色').strip() or '未知角色'}: "
            f"{str(item.get('message') or '').strip()}"
            for index, item in enumerate(rounds)
            if str(item.get("message") or "").strip()
        )
        fallback_summary = self._fallback_round_summary(rounds)
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "你是一名学习模拟记录员。请基于完整讨论记录提炼结构化总结。"
                        "只返回严格 JSON，不要输出 Markdown。"
                        "JSON 必须包含 key_arguments, unresolved_disagreements, user_contributions, "
                        "knowledge_gaps_revealed, suggested_next_steps 五个键。"
                        "其中 key_arguments, unresolved_disagreements, knowledge_gaps_revealed, suggested_next_steps "
                        "必须是字符串数组；user_contributions 必须是字符串。"
                        "内容必须使用自然、简体中文，且只总结轮次中实际出现的信息，不要臆造。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"主题：{topic}\n"
                        "完整轮次记录如下：\n"
                        f"{transcript}\n"
                        "请提炼核心论点、尚未解决的分歧、用户贡献、暴露出的知识盲区，以及建议下一步。"
                    ),
                },
            ],
            fallback={},
            temperature=0.2,
        )
        if isinstance(data, dict) and any(
            data.get(key)
            for key in (
                "key_arguments",
                "unresolved_disagreements",
                "user_contributions",
                "knowledge_gaps_revealed",
                "suggested_next_steps",
            )
        ):
            summary = {
                "key_arguments": self._string_list(data.get("key_arguments")),
                "unresolved_disagreements": self._string_list(
                    data.get("unresolved_disagreements"),
                ),
                "user_contributions": str(data.get("user_contributions") or "").strip(),
                "knowledge_gaps_revealed": self._string_list(
                    data.get("knowledge_gaps_revealed"),
                ),
                "suggested_next_steps": self._string_list(
                    data.get("suggested_next_steps"),
                ),
            }
            return json.dumps(summary, ensure_ascii=False)
        return fallback_summary

    def _fallback_round_summary(self, rounds: list[dict[str, Any]]) -> str:
        last_messages: dict[str, str] = {}
        for item in rounds:
            speaker = str(item.get("speaker") or "").strip()
            message = str(item.get("message") or "").strip()
            if speaker and message:
                last_messages[speaker] = message
        if not last_messages:
            return "本次模拟暂未形成可复用的总结。"
        return "；".join(f"{speaker}最后强调：{message}" for speaker, message in last_messages.items())

    @staticmethod
    def _latest_exchange(rounds: list[dict[str, Any]], limit: int = 3) -> str:
        if not rounds:
            return "讨论还没有开始。"
        recent = rounds[-max(limit, 1) :]
        return "\n".join(
            f"第 {item.get('round')} 轮：{item.get('speaker')} -> {item.get('message')}" for item in recent
        )

    async def _get_user_mastery_gaps(self, user_id: UUID) -> list[str]:
        result = await self.db.execute(
            select(KnowledgeNode.name)
            .join(UserNodeStatus, UserNodeStatus.node_id == KnowledgeNode.id)
            .where(
                UserNodeStatus.user_id == user_id,
                UserNodeStatus.mastery_score < 60,
            )
            .order_by(UserNodeStatus.mastery_score.asc())
            .limit(5)
        )
        return [str(name).strip() for name in result.scalars().all() if str(name).strip()]

    def _format_behavioral_context(
        self,
        behavioral_context: dict[str, Any] | None,
    ) -> str:
        if not behavioral_context:
            return ""
        mastery_gaps = [
            str(item).strip() for item in list(behavioral_context.get("mastery_gaps") or []) if str(item).strip()
        ]
        intent_forecast = dict(
            behavioral_context.get("next_intent_forecast") or {},
        )
        dropout_risk = dict(behavioral_context.get("dropout_risk") or {})
        next_intent = (
            str(intent_forecast.get("summary") or "").strip()
            or str(intent_forecast.get("title") or "").strip()
            or str(intent_forecast.get("predicted_action_type") or "").strip()
            or "暂无明确预测"
        )
        risk_level = str(dropout_risk.get("risk_level") or "unknown").strip()
        risk_note = (
            "辍学风险为 high/medium，请给出更具体、可立即执行的建议。"
            if risk_level in {"high", "medium"}
            else "风险暂不高，可以保持探索，但建议仍要有明确落点。"
        )
        return (
            "行为上下文：\n"
            f"- 用户知识薄弱点：{('、'.join(mastery_gaps) if mastery_gaps else '暂无显著薄弱点')}\n"
            f"- 用户下一步学习倾向：{next_intent}\n"
            f"- 辍学风险等级：{risk_level or 'unknown'}\n"
            f"- 主持策略提示：{risk_note}\n"
        )

    @staticmethod
    def _string_list(raw: Any) -> list[str]:
        if isinstance(raw, list):
            items = raw
        elif raw is None:
            items = []
        else:
            items = [raw]
        return [str(item).strip() for item in items if str(item).strip()]

    @staticmethod
    def _pending_interaction_target_speaker(pending_interaction: Any) -> str:
        if isinstance(pending_interaction, dict):
            prompt = str(pending_interaction.get("prompt") or "").strip()
            if "回应 " in prompt:
                return prompt.split("回应 ", 1)[-1].split(" ", 1)[0].strip()
        return ""

    async def _persist_checkpoint(
        self,
        *,
        user_id: UUID | None,
        session: SimulationSession,
        participants: list[AgentParticipant],
    ) -> None:
        payload = session.to_dict()
        payload["user_id"] = str(user_id) if user_id else None
        payload["last_active_at"] = datetime.now(UTC).isoformat()
        payload["participants"] = [participant.to_public_dict() for participant in participants]
        payload["participant_runtime"] = [
            {
                "name": participant.name,
                "memory": participant.memory,
                "strategy": participant.strategy,
                "response_policy": participant.response_policy,
            }
            for participant in participants
        ]
        self._local_checkpoints[session.id] = payload
        self._local_checkpoints.move_to_end(session.id)
        while len(self._local_checkpoints) > self.MAX_LOCAL_CHECKPOINTS:
            self._local_checkpoints.popitem(last=False)
        try:
            await cache_service.set(
                f"{self.SESSION_KEY_PREFIX}{session.id}",
                payload,
                ttl=self.SESSION_TTL_SECONDS,
            )
        except Exception:
            logger.warning("Simulation checkpoint cache write failed for session {}", session.id)
        await self._persist_checkpoint_to_db(user_id=user_id, payload=payload)

    async def _load_checkpoint(
        self,
        *,
        session_id: str,
        user_id: UUID | None,
    ) -> dict[str, Any]:
        payload: Any = None
        try:
            payload = await cache_service.get(f"{self.SESSION_KEY_PREFIX}{session_id}")
        except Exception:
            payload = None
        if not isinstance(payload, dict):
            payload = self._local_checkpoints.get(session_id)
        if not isinstance(payload, dict):
            payload = await self._load_checkpoint_from_db(session_id=session_id, user_id=user_id)
            if isinstance(payload, dict):
                self._local_checkpoints[session_id] = payload
                self._local_checkpoints.move_to_end(session_id)
                while len(self._local_checkpoints) > self.MAX_LOCAL_CHECKPOINTS:
                    self._local_checkpoints.popitem(last=False)
                try:
                    await cache_service.set(
                        f"{self.SESSION_KEY_PREFIX}{session_id}",
                        payload,
                        ttl=self.SESSION_TTL_SECONDS,
                    )
                except Exception:
                    logger.warning("Simulation checkpoint cache backfill failed for session {}", session_id)
        if not isinstance(payload, dict):
            raise ValueError("Simulation session not found or expired")
        owner_id = str(payload.get("user_id") or "").strip()
        if owner_id and user_id is not None and owner_id != str(user_id):
            raise ValueError("Simulation session does not belong to the current user")
        runtime_by_name = {
            str(item.get("name") or ""): item
            for item in list(payload.get("participant_runtime") or [])
            if isinstance(item, dict)
        }
        for participant in list(payload.get("participants") or []):
            if not isinstance(participant, dict):
                continue
            runtime = runtime_by_name.get(str(participant.get("name") or ""))
            if runtime:
                participant["memory"] = list(runtime.get("memory") or [])
                participant["strategy"] = runtime.get("strategy")
                participant["response_policy"] = runtime.get("response_policy")
        return payload

    async def _persist_checkpoint_to_db(self, *, user_id: UUID | None, payload: dict[str, Any]) -> None:
        if user_id is None or self.db is None:
            return
        try:
            from app.core.celery_app import schedule_long_task

            schedule_long_task(
                "app.core.celery_tasks.persist_simulation_run",
                kwargs={"user_id": str(user_id), "payload": payload},
                queue="low_priority",
            )
            return
        except Exception as exc:
            logger.warning("Simulation checkpoint async persist fallback for user {}: {}", user_id, exc)

        try:
            await SimulationRunStore(self.db).persist_payload(user_id=user_id, payload=payload)
        except Exception as exc:
            logger.warning("Simulation checkpoint DB persist failed for user {}: {}", user_id, exc)

    async def _load_checkpoint_from_db(
        self,
        *,
        session_id: str,
        user_id: UUID | None,
    ) -> dict[str, Any] | None:
        if user_id is None or self.db is None:
            return None
        try:
            return await SimulationRunStore(self.db).load_payload(session_id=session_id, user_id=user_id)
        except Exception as exc:
            logger.warning("Simulation checkpoint DB load failed for user {}: {}", user_id, exc)
            return None

    @staticmethod
    def _insight_summary_payload(insight_summary: Any) -> dict[str, Any] | None:
        if isinstance(insight_summary, dict):
            return insight_summary
        if not isinstance(insight_summary, str):
            return None
        try:
            parsed = json.loads(insight_summary)
        except (TypeError, ValueError):
            return None
        return parsed if isinstance(parsed, dict) else None

    async def _persist_simulation_insights(self, *, session: SimulationSession, user_id: str) -> None:
        payload = self._insight_summary_payload(session.insight_summary)
        if not payload:
            return

        knowledge_gaps = self._string_list(payload.get("knowledge_gaps_revealed"))
        if not knowledge_gaps:
            return

        for gap in knowledge_gaps:
            try:
                await self.event_bus_reliable.publish(
                    "SimulationGapRevealed",
                    {
                        "event_type": "SimulationGapRevealed",
                        "user_id": user_id,
                        "topic": session.topic,
                        "gap_description": gap,
                        "simulation_session_id": session.id,
                        "source": "simulation",
                    },
                )
            except Exception:
                continue

    async def _persist_session_update(self, *, user_id: UUID, session: SimulationSession) -> None:
        await SystemUpdateService().enqueue(
            user_id,
            build_system_update(
                update_type="simulation_session_ready",
                category="learning_insight",
                title=f"学习仿真已完成「{session.topic}」",
                description=session.insight_summary,
                priority="medium",
                metadata={
                    "session_payload": session.to_dict(),
                    "deep_link": f"/simulation?{urlencode({'topic': session.topic, 'scenario_key': session.scenario_key, 'simulation_session_id': session.id})}",
                    "interaction_prompt": session.interaction_prompt,
                    "suggested_replies": list(session.suggested_replies or []),
                    "interaction_type": session.interaction_type,
                    "interaction_options": list(session.interaction_options or []),
                    "facilitation_style": session.facilitation_style,
                },
            ),
        )

    @staticmethod
    def _session_from_payload(
        payload: dict[str, Any],
        *,
        fallback_topic: str,
        fallback_scenario: str,
    ) -> SimulationSession:
        return SimulationSession(
            id=str(payload.get("id") or ""),
            scenario_key=str(payload.get("scenario_key") or fallback_scenario),
            state=LearningSimulationState(str(payload.get("state") or LearningSimulationState.COMPLETED.value)),
            topic=str(payload.get("topic") or fallback_topic),
            participants=list(payload.get("participants") or []),
            rounds=list(payload.get("rounds") or []),
            insight_summary=str(payload.get("insight_summary") or ""),
            anchor_material=str(payload.get("anchor_material") or ""),
            anchor_type=str(payload.get("anchor_type") or "").strip() or None,
            anchor_id=str(payload.get("anchor_id") or "").strip() or None,
            anchor_status=str(payload.get("anchor_status") or "resolved"),
            learning_objective=str(payload.get("learning_objective") or "").strip() or None,
            interaction_prompt=str(payload.get("interaction_prompt") or ""),
            suggested_replies=list(payload.get("suggested_replies") or []),
            interaction_type=str(payload.get("interaction_type") or "choice"),
            interaction_options=list(payload.get("interaction_options") or []),
            planned_round_count=int(payload.get("planned_round_count") or 0),
            pending_interaction=payload.get("pending_interaction")
            if isinstance(payload.get("pending_interaction"), dict)
            else None,
            facilitation_style=str(payload.get("facilitation_style") or "balanced"),
        )
