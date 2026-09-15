from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from loguru import logger

from app.core.event_bus import TraitsColdstartCompleted, event_bus
from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService
from app.services.evidence.belief_state import BeliefVariable
from app.services.evidence.unified_evidence import EvidenceTarget
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


TRAIT_TO_BELIEF_PRIOR_WEIGHTS: dict[str, dict[EvidenceTarget, float]] = {
    "conscientiousness": {
        EvidenceTarget.EXECUTION_CAPACITY: 0.18,
        EvidenceTarget.GOAL_CLARITY: 0.14,
        EvidenceTarget.TASK_AVERSION: -0.12,
    },
    "neuroticism": {
        EvidenceTarget.EMOTIONAL_BLOCK: 0.18,
        EvidenceTarget.COGNITIVE_LOAD: 0.10,
        EvidenceTarget.EXECUTION_CAPACITY: -0.10,
    },
    "openness": {
        EvidenceTarget.GOAL_CLARITY: 0.06,
        EvidenceTarget.COGNITIVE_LOAD: -0.04,
    },
    "extraversion": {
        EvidenceTarget.EMOTIONAL_BLOCK: -0.05,
        EvidenceTarget.EXECUTION_CAPACITY: 0.05,
    },
    "agreeableness": {
        EvidenceTarget.SYSTEM_DISSATISFACTION: -0.08,
    },
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def derive_belief_priors_from_traits(traits: BigFiveTraits) -> dict[EvidenceTarget, tuple[float, float]]:
    """
    Translate cold-start Big Five traits into conservative BeliefState priors.

    These are not treated as observations or training labels. They only provide a
    softer cold-start anchor until real conversational/task evidence arrives.
    """
    deltas: dict[EvidenceTarget, float] = {}
    confidence_mass: dict[EvidenceTarget, float] = {}
    for dim in BigFiveTraits.DIMENSIONS:
        dimension = getattr(traits, dim, None)
        if dimension is None:
            continue
        weights = TRAIT_TO_BELIEF_PRIOR_WEIGHTS.get(dim)
        if not weights:
            continue
        value = max(-1.0, min(1.0, float(dimension.value or 0.0)))
        confidence = max(0.0, min(0.35, float(dimension.confidence or 0.0)))
        if confidence <= 0.0 or value == 0.0:
            continue
        confidence_scale = min(1.0, confidence / 0.2)
        for target, weight in weights.items():
            deltas[target] = deltas.get(target, 0.0) + weight * value * confidence_scale
            confidence_mass[target] = max(confidence_mass.get(target, 0.0), confidence)

    priors: dict[EvidenceTarget, tuple[float, float]] = {}
    for target, delta in deltas.items():
        variance = max(0.16, 0.22 - confidence_mass.get(target, 0.0) * 0.2)
        priors[target] = (_clamp01(0.5 + delta), variance)
    return priors


class TraitsColdStartService:
    def __init__(self, db, redis=None) -> None:
        self.redis = redis
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
        evidence_count: dict[str, int] = dict.fromkeys(BigFiveTraits.DIMENSIONS, 0)
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
        traits = BigFiveTraits.model_validate(traits_payload)
        await self._seed_belief_priors(user_id=user_id, traits=traits)
        return traits

    async def _seed_belief_priors(self, *, user_id: UUID, traits: BigFiveTraits) -> None:
        if self.redis is None:
            return
        priors = derive_belief_priors_from_traits(traits)
        if not priors:
            return
        try:
            from app.services.evidence import FusionEngine

            engine = FusionEngine(str(user_id))
            state = await engine.load_state(self.redis, str(user_id))
            for target, (mean, variance) in priors.items():
                variable = state.variables.get(target.value)
                if variable is not None and variable.evidence_count > 0:
                    continue
                state.variables[target.value] = BeliefVariable(
                    target=target,
                    mean=mean,
                    variance=variance,
                    evidence_count=0,
                    source_breakdown={"traits_coldstart_prior": 1},
                    last_evidence_ids=[f"traits_coldstart:{target.value}"],
                    last_updated=_utcnow(),
                )
            state.scope_metadata = {
                **dict(state.scope_metadata or {}),
                "belief_prior_source": "traits_coldstart.v1",
                "belief_prior_applied_at": _utcnow().isoformat(),
            }
            await engine.save_state(self.redis, state)
        except Exception as exc:
            logger.debug("Failed to seed cold-start belief priors for user {}: {}", user_id, exc)
            return
