from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_fallback_utils import analysis_llm
from app.services.simulation.participant_generator import generate_participants
from app.services.simulation.scenario_templates import SCENARIOS
from app.services.simulation.simulation_state import LearningSimulationState


@dataclass
class SimulationSession:
    id: str
    scenario_key: str
    state: LearningSimulationState
    topic: str
    participants: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    insight_summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_key": self.scenario_key,
            "state": self.state.value,
            "topic": self.topic,
            "participants": self.participants,
            "rounds": self.rounds,
            "insight_summary": self.insight_summary,
        }


class SimulationEngine:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def run(
        self,
        *,
        topic: str,
        scenario_key: str,
        user_id: UUID | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> SimulationSession:
        final_session: SimulationSession | None = None
        async for event_name, payload in self.stream(
            topic=topic,
            scenario_key=scenario_key,
            user_id=user_id,
            user_context=user_context,
        ):
            if event_name == "complete":
                session_payload = payload.get("session")
                if isinstance(session_payload, dict):
                    final_session = SimulationSession(
                        id=str(session_payload.get("id") or ""),
                        scenario_key=str(session_payload.get("scenario_key") or scenario_key),
                        state=LearningSimulationState(str(session_payload.get("state") or LearningSimulationState.COMPLETED.value)),
                        topic=str(session_payload.get("topic") or topic),
                        participants=list(session_payload.get("participants") or []),
                        rounds=list(session_payload.get("rounds") or []),
                        insight_summary=str(session_payload.get("insight_summary") or ""),
                    )
        if final_session is None:
            raise RuntimeError("Simulation stream completed without a final session payload")
        return final_session

    async def stream(
        self,
        *,
        topic: str,
        scenario_key: str,
        user_id: UUID | None = None,
        user_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        session_id = str(uuid4())
        normalized_scenario_key = scenario_key if scenario_key in SCENARIOS else "study_group"
        template = dict(SCENARIOS.get(normalized_scenario_key) or SCENARIOS["study_group"])

        yield "status", {
            "session_id": session_id,
            "state": LearningSimulationState.PREPARING.value,
            "progress": 0.1,
            "topic": topic,
            "scenario_key": normalized_scenario_key,
        }

        participants = await generate_participants(
            scenario_key=normalized_scenario_key,
            participant_names=list(template.get("participants") or ["学习伙伴"]),
            user_context=user_context,
            db=self.db,
            user_id=user_id,
            topic=topic,
            participants_from=str(template.get("participants_from") or "") or None,
        )
        yield "participants", {
            "session_id": session_id,
            "state": LearningSimulationState.RUNNING.value,
            "progress": 0.25,
            "participants": participants,
        }

        rounds: list[dict[str, Any]] = []
        round_count = self._resolve_round_count(template.get("rounds"))
        for index in range(round_count):
            round_item = await self._generate_round(
                topic=topic,
                scenario_key=normalized_scenario_key,
                participants=participants,
                round_index=index,
                round_count=round_count,
                previous_rounds=rounds,
                template=template,
            )
            rounds.append(round_item)
            yield "round", {
                "session_id": session_id,
                "state": LearningSimulationState.RUNNING.value,
                "progress": min(0.9, 0.25 + (0.6 * (len(rounds) / max(round_count, 1)))),
                "round": round_item,
                "rounds": rounds,
            }

        insight_summary = self._summarize_rounds(topic, rounds)
        session = SimulationSession(
            id=session_id,
            scenario_key=normalized_scenario_key,
            state=LearningSimulationState.COMPLETED,
            topic=topic,
            participants=participants,
            rounds=rounds,
            insight_summary=insight_summary,
        )
        yield "complete", {
            "session_id": session_id,
            "state": LearningSimulationState.COMPLETED.value,
            "progress": 1.0,
            "session": session.to_dict(),
        }

    async def _generate_round(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[dict[str, Any]],
        round_index: int,
        round_count: int,
        previous_rounds: list[dict[str, Any]],
        template: dict[str, object],
    ) -> dict[str, Any]:
        speaker = participants[round_index % len(participants)]["name"]
        fallback_message = self._fallback_round_message(
            topic=topic,
            scenario_key=scenario_key,
            participants=participants,
            round_index=round_index,
        )
        transcript = "\n".join(
            f"Round {item['round']}: {item['speaker']} - {item['message']}" for item in previous_rounds
        ) or "No prior rounds yet."
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with keys speaker and message. "
                        "Keep the turn short, grounded, and useful for a learning simulation."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Scenario: {scenario_key}\n"
                        f"Description: {template.get('description')}\n"
                        f"Topic: {topic}\n"
                        f"Current round: {round_index + 1} / {round_count}\n"
                        f"Participants: {participants}\n"
                        f"Transcript so far:\n{transcript}\n"
                        f"Preferred speaker: {speaker}\n"
                        "Generate the next turn only."
                    ),
                },
            ],
            fallback={"speaker": speaker, "message": fallback_message},
            temperature=0.45,
        )
        return {
            "round": round_index + 1,
            "speaker": str((data or {}).get("speaker") or speaker),
            "message": str((data or {}).get("message") or "").strip() or fallback_message,
        }

    def _resolve_round_count(self, rounds: object) -> int:
        if str(rounds) == "dynamic":
            return 4
        return max(2, min(int(rounds or 3), 6))

    def _fallback_round_message(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[dict[str, Any]],
        round_index: int,
    ) -> str:
        participant = participants[round_index % len(participants)]
        role_hint = participant.get("role_hint") or participant["name"]
        anchor = participant.get("context_anchor")
        if scenario_key == "socratic_dialogue":
            return f"如果从 {role_hint} 的角度追问“{topic}”，你会先验证哪个前提为什么成立？"
        if scenario_key == "knowledge_debate":
            return f"从 {role_hint} 立场出发，我认为“{topic}”最值得争论的是它成立的条件与适用边界。"
        if scenario_key == "historical_roleplay" and anchor:
            return f"结合 {anchor}，我会把“{topic}”放回当时语境里重新理解它为何重要。"
        return f"围绕“{topic}”，我想先从 {role_hint} 视角解释最关键的一步。"

    def _summarize_rounds(self, topic: str, rounds: list[dict[str, Any]]) -> str:
        if not rounds:
            return f"围绕 {topic} 的模拟还没有形成有效洞察。"
        speakers = "、".join(dict.fromkeys(str(item.get("speaker") or "") for item in rounds if item.get("speaker")))
        return f"本次模拟围绕“{topic}”由 {speakers} 逐轮展开，适合复盘分歧点、论据强度与下一步练习方向。"
