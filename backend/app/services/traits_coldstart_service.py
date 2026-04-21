from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.config import settings
from app.core.event_bus import TraitsColdstartCompleted, event_bus
from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService
from app.services.personalization.preference_service import PreferenceService
from app.services.traits_metrics import TRAITS_COLDSTART_TOTAL


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


COLDSTART_QUESTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "q1",
        "title": "开始新目标时，你更像哪种方式？",
        "dimensions": ("openness", "conscientiousness"),
        "options": (
            {"id": "structured", "label": "先搭结构再行动", "effects": {"conscientiousness": 0.7, "openness": -0.2}},
            {"id": "mixed", "label": "先有框架，再边做边调", "effects": {"conscientiousness": 0.3, "openness": 0.2}},
            {"id": "explore", "label": "先试试看，让方向自己浮现", "effects": {"openness": 0.7, "conscientiousness": -0.2}},
            {"id": "skip", "label": "跳过", "effects": {}},
        ),
    },
    {
        "id": "q2",
        "title": "遇到难题时，你更容易从哪里补能量？",
        "dimensions": ("extraversion", "agreeableness"),
        "options": (
            {"id": "solo", "label": "先自己想清楚", "effects": {"extraversion": -0.7}},
            {"id": "small_group", "label": "找一两个人讨论", "effects": {"extraversion": 0.2, "agreeableness": 0.4}},
            {"id": "group", "label": "边聊边想最有感觉", "effects": {"extraversion": 0.7, "agreeableness": 0.3}},
            {"id": "skip", "label": "跳过", "effects": {}},
        ),
    },
    {
        "id": "q3",
        "title": "当计划被打乱时，你通常最先出现什么反应？",
        "dimensions": ("neuroticism", "conscientiousness"),
        "options": (
            {"id": "replan", "label": "马上重排，尽快回正", "effects": {"conscientiousness": 0.6, "neuroticism": -0.2}},
            {"id": "pause", "label": "会卡一下，但能慢慢拉回来", "effects": {"neuroticism": 0.1}},
            {"id": "swing", "label": "情绪和节奏都会受影响", "effects": {"neuroticism": 0.7, "conscientiousness": -0.2}},
            {"id": "skip", "label": "跳过", "effects": {}},
        ),
    },
)


class TraitsColdStartService:
    def __init__(self, db, redis=None) -> None:
        self.pref_service = PreferenceService(db, redis)
        self.kill_switch = AuroraStage28TraitsKillSwitchService()

    async def submit_answers(self, user_id: UUID, answers: dict[str, str]) -> BigFiveTraits:
        if await self.kill_switch.get_mode() == "off" or await self.kill_switch.get_coldstart_mode() == "off":
            TRAITS_COLDSTART_TOTAL.labels(outcome="disabled").inc()
            return BigFiveTraits()

        now = _utcnow()
        if not answers or all(str(value or "").strip().lower() == "skip" for value in answers.values()):
            await self.pref_service.update_traits(
                user_id,
                traits_prior={},
                trait_observation_state={"latest_evidence_ids": {}},
                traits_coldstart_completed_at=now,
            )
            TRAITS_COLDSTART_TOTAL.labels(outcome="skipped").inc()
            await event_bus.publish(
                "coldstart_completed",
                TraitsColdstartCompleted(user_id=str(user_id), completed_at=now.isoformat()).to_dict(),
            )
            return BigFiveTraits()

        aggregates: dict[str, list[float]] = {dim: [] for dim in BigFiveTraits.DIMENSIONS}
        evidence_count: dict[str, int] = {dim: 0 for dim in BigFiveTraits.DIMENSIONS}
        for question in COLDSTART_QUESTIONS:
            selected_option = str(answers.get(question["id"]) or "").strip().lower()
            if not selected_option or selected_option == "skip":
                continue
            option = next(
                (item for item in question["options"] if item["id"] == selected_option),
                None,
            )
            if option is None:
                continue
            for dim, effect in dict(option["effects"]).items():
                aggregates[dim].append(float(effect))
                evidence_count[dim] += 1

        traits_payload: dict[str, dict[str, Any]] = {}
        for dim in BigFiveTraits.DIMENSIONS:
            samples = aggregates[dim]
            if not samples:
                continue
            value = sum(samples) / len(samples)
            confidence = min(0.2, 0.12 + 0.03 * len(samples))
            traits_payload[dim] = BigFiveDimension(
                value=value,
                confidence=confidence,
                evidence_count=evidence_count[dim],
                last_observed_at=now.isoformat(),
                source="coldstart",
            ).model_dump(mode="json")

        trait_state = {
            "latest_evidence_ids": {
                dim: f"coldstart:{question['id']}"
                for question in COLDSTART_QUESTIONS
                for dim in question["dimensions"]
                if dim in traits_payload
            }
        }
        await self.pref_service.update_traits(
            user_id,
            traits_prior=traits_payload,
            trait_observation_state=trait_state,
            traits_coldstart_completed_at=now,
        )
        TRAITS_COLDSTART_TOTAL.labels(outcome="completed").inc()
        await event_bus.publish(
            "coldstart_completed",
            TraitsColdstartCompleted(user_id=str(user_id), completed_at=now.isoformat()).to_dict(),
        )
        return BigFiveTraits.model_validate(traits_payload)
