from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_fallback_utils import analysis_llm
from app.services.simulation.participant_generator import generate_participants
from app.services.simulation.scenario_templates import SCENARIOS
from app.services.simulation.simulation_state import LearningSimulationState
from app.services.system_update_service import SystemUpdateService, build_system_update


@dataclass
class SimulationSession:
    id: str
    scenario_key: str
    state: LearningSimulationState
    topic: str
    participants: list[dict[str, Any]]
    rounds: list[dict[str, Any]]
    insight_summary: str
    interaction_prompt: str = ""
    suggested_replies: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scenario_key": self.scenario_key,
            "state": self.state.value,
            "topic": self.topic,
            "participants": self.participants,
            "rounds": self.rounds,
            "insight_summary": self.insight_summary,
            "interaction_prompt": self.interaction_prompt,
            "suggested_replies": list(self.suggested_replies or []),
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
                        interaction_prompt=str(session_payload.get("interaction_prompt") or ""),
                        suggested_replies=list(session_payload.get("suggested_replies") or []),
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
            interaction_point = self._build_interaction_point(
                topic=topic,
                scenario_key=normalized_scenario_key,
                participants=participants,
                rounds=rounds,
            )
            yield "round", {
                "session_id": session_id,
                "state": LearningSimulationState.RUNNING.value,
                "progress": min(0.9, 0.25 + (0.6 * (len(rounds) / max(round_count, 1)))),
                "round": round_item,
                "rounds": rounds,
                "interaction_prompt": str(interaction_point.get("prompt") or ""),
                "suggested_replies": list(interaction_point.get("suggested_replies") or []),
            }

        insight_summary = self._summarize_rounds(topic, rounds)
        interaction_point = self._build_interaction_point(
            topic=topic,
            scenario_key=normalized_scenario_key,
            participants=participants,
            rounds=rounds,
            final_round=True,
        )
        session = SimulationSession(
            id=session_id,
            scenario_key=normalized_scenario_key,
            state=LearningSimulationState.COMPLETED,
            topic=topic,
            participants=participants,
            rounds=rounds,
            insight_summary=insight_summary,
            interaction_prompt=str(interaction_point.get("prompt") or ""),
            suggested_replies=list(interaction_point.get("suggested_replies") or []),
        )
        if user_id is not None:
            await self._persist_session_update(user_id=user_id, session=session)
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
        turn_plan = self._select_turn_plan(
            scenario_key=scenario_key,
            participants=participants,
            round_index=round_index,
            round_count=round_count,
            previous_rounds=previous_rounds,
        )
        speaker = str(turn_plan["speaker"])
        reply_target = turn_plan.get("reply_target")
        turn_goal = str(turn_plan["turn_goal"])
        fallback_message = self._fallback_round_message(
            topic=topic,
            scenario_key=scenario_key,
            participants=participants,
            round_index=round_index,
            previous_rounds=previous_rounds,
            speaker=speaker,
            reply_target=reply_target if isinstance(reply_target, dict) else None,
            turn_goal=turn_goal,
        )
        participant_prompt = "\n".join(
            (
                f"- {participant.get('name')}: "
                f"role_hint={participant.get('role_hint')}; "
                f"stance={participant.get('stance')}; "
                f"persona={participant.get('persona')}"
            )
            for participant in participants
        )
        transcript = "\n".join(
            f"Round {item['round']}: {item['speaker']} - {item['message']}" for item in previous_rounds
        ) or "No prior rounds yet."
        latest_exchange = self._latest_exchange(previous_rounds)
        reply_target_name = (
            str(reply_target.get("speaker") or "").strip()
            if isinstance(reply_target, dict)
            else ""
        )
        data = await analysis_llm.json_call(
            [
                {
                    "role": "system",
                    "content": (
                        "Return strict JSON with keys speaker, message, reply_to_speaker, and turn_goal. "
                        "Keep the turn short, grounded, and useful for a learning simulation. "
                        "This is a live multi-agent exchange, so each turn must either react to a previous point, "
                        "surface a disagreement, or synthesize what changed."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Scenario: {scenario_key}\n"
                        f"Description: {template.get('description')}\n"
                        f"Topic: {topic}\n"
                        f"Current round: {round_index + 1} / {round_count}\n"
                        f"Participants:\n{participant_prompt}\n"
                        f"Transcript so far:\n{transcript}\n"
                        f"Latest exchange:\n{latest_exchange}\n"
                        f"Preferred speaker: {speaker}\n"
                        f"Turn goal: {turn_goal}\n"
                        f"Reply target: {reply_target_name or 'open the discussion'}\n"
                        "Generate the next turn only. The message must sound like this speaker is actively responding "
                        "to the room instead of giving an isolated monologue."
                    ),
                },
            ],
            fallback={
                "speaker": speaker,
                "message": fallback_message,
                "reply_to_speaker": reply_target_name,
                "turn_goal": turn_goal,
            },
            temperature=0.45,
        )
        payload = data if isinstance(data, dict) else {}
        resolved_speaker = str(payload.get("speaker") or speaker).strip() or speaker
        participant_names = {str(item.get("name") or "").strip() for item in participants}
        if resolved_speaker not in participant_names:
            resolved_speaker = speaker
        return {
            "round": round_index + 1,
            "speaker": resolved_speaker,
            "message": str(payload.get("message") or "").strip() or fallback_message,
            "reply_to_speaker": str(payload.get("reply_to_speaker") or reply_target_name).strip(),
            "turn_goal": str(payload.get("turn_goal") or turn_goal).strip() or turn_goal,
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
        previous_rounds: list[dict[str, Any]],
        speaker: str,
        reply_target: dict[str, Any] | None,
        turn_goal: str,
    ) -> str:
        participant = participants[round_index % len(participants)]
        role_hint = participant.get("role_hint") or participant["name"]
        anchor = participant.get("context_anchor")
        if reply_target:
            target_speaker = str(reply_target.get("speaker") or "上一位发言者")
            target_message = str(reply_target.get("message") or "").strip()
            if scenario_key == "knowledge_debate":
                return (
                    f"我想回应 {target_speaker} 刚才关于“{topic}”的判断。"
                    f" 如果只停在“{target_message[:24]}”，会忽略这个概念真正的适用边界。"
                )
            if scenario_key == "socratic_dialogue":
                return (
                    f"顺着 {target_speaker} 刚才那句话，我会继续追问："
                    f"“{topic}”里最不能默认成立的前提到底是什么？"
                )
            if turn_goal == "synthesize":
                return (
                    f"回应前面的讨论，我想先帮大家收束一下：围绕“{topic}”，"
                    f" 现在已经形成的共识是什么，还缺哪一步证据。"
                )
            return (
                f"接着 {target_speaker} 刚才的观点，我想把“{topic}”再往前推一步，"
                f" 重点补上最容易被忽略的解释链。"
            )
        if scenario_key == "socratic_dialogue":
            return f"如果从 {role_hint} 的角度追问“{topic}”，你会先验证哪个前提为什么成立？"
        if scenario_key == "knowledge_debate":
            return f"从 {role_hint} 立场出发，我认为“{topic}”最值得争论的是它成立的条件与适用边界。"
        if scenario_key == "historical_roleplay" and anchor:
            return f"结合 {anchor}，我会把“{topic}”放回当时语境里重新理解它为何重要。"
        if previous_rounds:
            return f"基于前面已经出现的分歧，我想从 {role_hint} 视角继续推进“{topic}”的下一步判断。"
        return f"围绕“{topic}”，我想先从 {role_hint} 视角解释最关键的一步。"

    def _summarize_rounds(self, topic: str, rounds: list[dict[str, Any]]) -> str:
        if not rounds:
            return f"围绕 {topic} 的模拟还没有形成有效洞察。"
        speakers = "、".join(dict.fromkeys(str(item.get("speaker") or "") for item in rounds if item.get("speaker")))
        return f"本次模拟围绕“{topic}”由 {speakers} 逐轮展开，适合复盘分歧点、论据强度与下一步练习方向。"

    def _build_interaction_point(
        self,
        *,
        topic: str,
        scenario_key: str,
        participants: list[dict[str, Any]],
        rounds: list[dict[str, Any]],
        final_round: bool = False,
    ) -> dict[str, Any]:
        if not rounds:
            return {}

        latest = rounds[-1]
        latest_speaker = str(latest.get("speaker") or "刚才的发言者").strip() or "刚才的发言者"
        latest_message = str(latest.get("message") or "").strip()
        topic_label = topic.strip() or "当前主题"
        participant_names = [
            str(item.get("name") or "").strip()
            for item in participants
            if str(item.get("name") or "").strip()
        ]
        other_speaker = next((name for name in reversed(participant_names) if name != latest_speaker), latest_speaker)

        if scenario_key == "knowledge_debate":
            prompt = (
                f"{latest_speaker} 刚才强调“{latest_message[:28]}”。"
                f" 如果换成你，你会更支持哪一边，还是会补一个第三种解释？"
            )
            suggested = [
                f"我更认同 {latest_speaker}，因为这一步先抓住了“{topic_label}”的核心边界。",
                f"我更想回应 {other_speaker}，因为“{topic_label}”还缺一个反例来验证。",
                f"我会先补一个具体题目，看看“{topic_label}”在什么条件下最容易出错。",
            ]
        elif scenario_key == "socratic_dialogue":
            prompt = (
                f"围绕“{topic_label}”，对话已经追问到“{latest_message[:28]}”。"
                " 如果下一个问题由你来提，你会继续追哪一个前提？"
            )
            suggested = [
                f"我会先追问“{topic_label}”成立前最容易被忽略的前提是什么。",
                f"我想把“{topic_label}”换成一道具体例题，看看哪里开始失真。",
                f"我会反问：如果这个前提不成立，当前结论还剩下多少有效性？",
            ]
        else:
            if final_round and len(rounds) >= 2:
                prompt = (
                    f"这轮仿真已经收束。现在轮到你：面对“{topic_label}”，"
                    " 你准备采纳哪条建议作为自己的下一步行动？"
                )
            else:
                prompt = (
                    f"{latest_speaker} 刚把讨论推进到“{latest_message[:28]}”。"
                    f" 如果你现在加入这场讨论，会先怎么回应“{topic_label}”？"
                )
            suggested = [
                f"我会先把“{topic_label}”拆成两步，先补最卡的前置概念。",
                f"我更想追问一个具体例子，确认刚才的结论能不能落到题目里。",
                f"我会先总结共识，再给自己定一个 20 分钟的小练习验证理解。",
            ]

        return {
            "prompt": prompt,
            "suggested_replies": suggested,
        }

    def _select_turn_plan(
        self,
        *,
        scenario_key: str,
        participants: list[dict[str, Any]],
        round_index: int,
        round_count: int,
        previous_rounds: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not participants:
            return {"speaker": "学习伙伴", "reply_target": None, "turn_goal": "open"}

        if not previous_rounds:
            return {
                "speaker": str(participants[0].get("name") or "学习伙伴"),
                "reply_target": None,
                "turn_goal": "open",
            }

        last_round = previous_rounds[-1]
        speaker_counts: dict[str, int] = {}
        for item in previous_rounds:
            name = str(item.get("speaker") or "").strip()
            if name:
                speaker_counts[name] = speaker_counts.get(name, 0) + 1

        def participant_order_key(participant: dict[str, Any]) -> tuple[int, int]:
            name = str(participant.get("name") or "").strip()
            return (
                speaker_counts.get(name, 0),
                1 if name == str(last_round.get("speaker") or "").strip() else 0,
            )

        ordered_participants = sorted(participants, key=participant_order_key)
        chosen = ordered_participants[0]
        chosen_name = str(chosen.get("name") or "学习伙伴")
        reply_target = self._pick_reply_target(previous_rounds, speaker_name=chosen_name)
        final_round = round_index == max(round_count - 1, 0)

        if scenario_key == "knowledge_debate":
            turn_goal = "challenge" if str(chosen.get("stance") or "").strip() == "opposing" else "extend"
        elif scenario_key == "socratic_dialogue":
            turn_goal = "probe"
        else:
            turn_goal = "extend"
        if final_round:
            turn_goal = "synthesize"

        return {
            "speaker": chosen_name,
            "reply_target": reply_target,
            "turn_goal": turn_goal,
        }

    @staticmethod
    def _pick_reply_target(previous_rounds: list[dict[str, Any]], *, speaker_name: str) -> dict[str, Any] | None:
        for item in reversed(previous_rounds):
            if str(item.get("speaker") or "").strip() != speaker_name:
                return item
        return previous_rounds[-1] if previous_rounds else None

    @staticmethod
    def _latest_exchange(previous_rounds: list[dict[str, Any]], limit: int = 2) -> str:
        if not previous_rounds:
            return "No exchange yet."
        recent = previous_rounds[-max(limit, 1):]
        return "\n".join(
            f"Round {item.get('round')}: {item.get('speaker')} -> {item.get('message')}"
            for item in recent
        )

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
                    "deep_link": f"/simulation?{urlencode({'topic': session.topic, 'scenario_key': session.scenario_key})}",
                    "interaction_prompt": session.interaction_prompt,
                    "suggested_replies": list(session.suggested_replies or []),
                },
            ),
        )
