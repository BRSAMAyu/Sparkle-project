from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.config import settings
from app.core.agent_profiles import AgentRole, ModelTier, TaskType
from app.core.user_insight_state import BigFiveDimension, BigFiveTraits
from app.models.chat import ChatMessage, MessageRole
from app.services.aurora_stage28_traits_kill_switch_service import AuroraStage28TraitsKillSwitchService
from app.services.llm_service import get_configured_llm_service_for_tier
from app.services.personalization.preference_service import PreferenceService
from app.services.traits_bias_calibration import CALIBRATION_SAMPLES
from app.services.traits_merge_service import TraitObservation
from app.services.traits_metrics import TRAITS_NLP_OBSERVATION_TOTAL


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class TraitsNlpObserverService:
    def __init__(self, db, redis=None) -> None:
        self.db = db
        self.pref_service = PreferenceService(db, redis)
        self.kill_switch = AuroraStage28TraitsKillSwitchService()

    async def collect_recent_user_texts(
        self,
        user_id: UUID,
        *,
        days: int | None = None,
        now: datetime | None = None,
        limit: int = 40,
    ) -> list[str]:
        reference = now or _utcnow()
        day_window = max(1, min(int(days or settings.AURORA_TRAITS_NLP_MAX_DAYS), 30))
        stmt = (
            select(ChatMessage.content)
            .where(
                ChatMessage.user_id == user_id,
                ChatMessage.role == MessageRole.USER,
                ChatMessage.created_at >= reference - timedelta(days=day_window),
            )
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = await self.db.execute(stmt)
        return [str(item).strip() for item in rows.scalars().all() if str(item).strip()]

    async def observe_user(
        self,
        user_id: UUID,
        *,
        texts: list[str] | None = None,
        now: datetime | None = None,
        window_days: int = 30,
    ) -> TraitObservation | None:
        if await self.kill_switch.get_mode() == "off" or await self.kill_switch.get_nlp_mode() == "off":
            TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="disabled").inc()
            return None

        reference = now or _utcnow()
        prefs = await self.pref_service.get_preferences(user_id)
        observation_state = dict(prefs.trait_observation_state or {})
        last_observed_at_raw = observation_state.get("last_nlp_observed_at")
        if last_observed_at_raw:
            last_observed_at = datetime.fromisoformat(str(last_observed_at_raw))
            if reference - last_observed_at < timedelta(hours=settings.AURORA_TRAITS_NLP_COOLDOWN_HOURS):
                TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="cooldown").inc()
                return None

        corpus = list(texts or await self.collect_recent_user_texts(user_id, days=window_days, now=reference))
        if not corpus:
            TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="empty").inc()
            return None

        started_at = time.perf_counter()
        candidate = await self._call_llm_candidate(corpus)
        if not candidate:
            candidate = self._heuristic_candidate(corpus)
        elapsed_ms = (time.perf_counter() - started_at) * 1000.0

        evidence_id = f"traits-nlp:{user_id}:{int(reference.timestamp())}"
        observation = self._build_observation(
            user_id=user_id,
            evidence_id=evidence_id,
            observed_at=reference.isoformat(),
            window_days=min(window_days, 30),
            payload=candidate,
        )
        if elapsed_ms > settings.AURORA_TRAITS_NLP_P95_MS_BUDGET:
            TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="slow").inc()
        return observation

    async def validate_bias_calibration(self) -> dict[str, Any]:
        mismatches = 0
        total = 0
        for sample in CALIBRATION_SAMPLES:
            observation = self._build_observation(
                user_id=UUID(int=0),
                evidence_id=f"calibration:{sample.language}:{sample.style}",
                observed_at=_utcnow().isoformat(),
                window_days=30,
                payload=self._heuristic_candidate([sample.text]),
            )
            for dim, expected_direction in sample.expected_directions.items():
                total += 1
                actual = getattr(observation, dim)
                actual_direction = 0
                if actual is not None and actual.value > 0:
                    actual_direction = 1
                elif actual is not None and actual.value < 0:
                    actual_direction = -1
                if actual_direction != int(expected_direction):
                    mismatches += 1
        bias_rate = mismatches / max(total, 1)
        if bias_rate > float(settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD):
            TRAITS_NLP_OBSERVATION_TOTAL.labels(outcome="bias_detected").inc()
        return {
            "sample_count": len(CALIBRATION_SAMPLES),
            "mismatches": mismatches,
            "total_checks": total,
            "bias_rate": round(bias_rate, 4),
            "passed": bias_rate <= float(settings.AURORA_TRAITS_NLP_BIAS_THRESHOLD),
        }

    async def _call_llm_candidate(self, texts: list[str]) -> dict[str, Any] | None:
        try:
            llm = await get_configured_llm_service_for_tier(
                AgentRole.GENERATION,
                force_tier=ModelTier.FAST,
                task_type=TaskType.STANDARD_RESPONSE,
                reasoning_mode="fast",
            )
            return await llm.chat_json(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Return a JSON object with optional Big Five deltas only. "
                            "No diagnosis labels. Use keys openness, conscientiousness, extraversion, "
                            "agreeableness, neuroticism. Each key may contain value in [-1,1]."
                        ),
                    },
                    {"role": "user", "content": "\n".join(texts[-12:])},
                ],
                temperature=0.2,
            )
        except Exception:
            return None

    def _build_observation(
        self,
        *,
        user_id: UUID,
        evidence_id: str,
        observed_at: str,
        window_days: int,
        payload: dict[str, Any],
    ) -> TraitObservation:
        dims: dict[str, BigFiveDimension] = {}
        for dim in BigFiveTraits.DIMENSIONS:
            raw = payload.get(dim)
            if raw is None:
                continue
            if isinstance(raw, dict):
                value = float(raw.get("value") or 0.0)
                confidence = min(0.1, max(0.01, float(raw.get("confidence") or 0.05)))
            else:
                value = float(raw)
                confidence = 0.05
            if value == 0:
                continue
            dims[dim] = BigFiveDimension(
                value=max(-0.2, min(0.2, value)),
                confidence=confidence,
                evidence_count=1,
                last_observed_at=observed_at,
                source="nlp_observed",
            )
        return TraitObservation(
            user_id=str(user_id),
            evidence_id=evidence_id,
            observed_at=observed_at,
            source="nlp_observed",
            confidence_delta=0.05,
            text_window_days=window_days,
            **dims,
        )

    def _heuristic_candidate(self, texts: list[str]) -> dict[str, Any]:
        combined = " ".join(texts).lower()
        payload: dict[str, Any] = {}

        def _set(dim: str, value: float, confidence: float = 0.05) -> None:
            payload[dim] = {"value": value, "confidence": confidence}

        if any(token in combined for token in ("清单", "步骤", "plan", "checklist", "constante", "ثابت")):
            _set("conscientiousness", 0.12)
        if any(token in combined for token in ("试试看", "new ideas", "新しい", "explore", "creative", "想法")):
            _set("openness", 0.12)
        if any(token in combined for token in ("一起", "brainstorm", "talking", "讨论", "الآخرين", "people")):
            _set("extraversion", 0.12)
        if any(token in combined for token in ("团队", "others", "warm", "帮助", "calm", "الحفاظ", "people")):
            _set("agreeableness", 0.1)
        if any(token in combined for token in ("goal", "目标明确", "واضح", "clear")):
            _set("conscientiousness", 0.1)
        if any(token in combined for token in ("焦虑", "panic", "受影响", "alterarme", "急かされる")):
            _set("neuroticism", 0.12)
        if any(token in combined for token in ("不太会慌", "not usually", "calm", "保持冷静", "不容易慌", "no suelo alterarme")):
            _set("neuroticism", -0.1)
        if any(token in combined for token in ("一个人", "alone", "solo", "静か", "quiet")):
            _set("extraversion", -0.1)

        return payload
