"""
Core: execution
Phase: reflect→adapt
Stage: Signal-to-Action Spine P2-3 RelationshipModel (D4 Hybrid)

用户-AI 关系模型 — FSM stance + 连续维度，影响策略表达方式。

D4 裁定：
- 6-stance FSM: new → calibrating → trusted → strained → repairing → cooldown
- 5 连续维度: directness_tolerance, autonomy_preference, explanation_need,
              pressure_sensitivity, trust_in_strategy
- 不直接展示给用户
- 只影响语气、确认、频率、挑战强度

核心原则：
- 只建模可改变下一步策略的关系状态
- trust_level 有明确上下界
- 用户纠正降低信任并提升解释证据
- 不写长期人格，只写当前关系策略状态
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from loguru import logger

_RELATIONSHIP_KEY = "spine:relationship:{user_id}"
_MIN_TRUST = 0.1
_MAX_TRUST = 1.0
_DEFAULT_TRUST = 0.5
_VALID_INTERACTION_TYPES = {"confirmed", "corrected", "dismissed", "expanded", "ignored"}
_VALID_BEHAVIORAL_SIGNALS = {"task_completed", "task_abandoned", "streak_maintained", "streak_broken", "session_engaged", "session_idle"}
_VALID_STANCES = {"new", "calibrating", "trusted", "strained", "repairing", "cooldown"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class RelationshipState:
    """Current user-AI relationship state used for policy adjustment.

    D4 hybrid model: FSM stance + 5 continuous dimensions.
    """

    user_id: str
    trust_level: float
    interaction_style: str
    correction_frequency: float
    engagement_depth: str
    last_interaction_at: str
    total_interactions: int = 0
    total_corrections: int = 0
    total_confirmations: int = 0
    total_tasks_completed: int = 0
    total_tasks_abandoned: int = 0
    current_streak: int = 0
    longest_streak: int = 0
    preferences: dict[str, Any] = field(default_factory=dict)
    # D4: FSM stance
    stance: str = "new"
    # D4: Continuous dimensions (0.0 - 1.0)
    directness_tolerance: float = 0.5
    autonomy_preference: float = 0.5
    explanation_need: float = 0.5
    pressure_sensitivity: float = 0.5
    trust_in_strategy: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "trust_level": self.trust_level,
            "interaction_style": self.interaction_style,
            "correction_frequency": self.correction_frequency,
            "engagement_depth": self.engagement_depth,
            "last_interaction_at": self.last_interaction_at,
            "total_interactions": self.total_interactions,
            "total_corrections": self.total_corrections,
            "total_confirmations": self.total_confirmations,
            "total_tasks_completed": self.total_tasks_completed,
            "total_tasks_abandoned": self.total_tasks_abandoned,
            "current_streak": self.current_streak,
            "longest_streak": self.longest_streak,
            "preferences": self.preferences,
            "stance": self.stance,
            "directness_tolerance": self.directness_tolerance,
            "autonomy_preference": self.autonomy_preference,
            "explanation_need": self.explanation_need,
            "pressure_sensitivity": self.pressure_sensitivity,
            "trust_in_strategy": self.trust_in_strategy,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RelationshipState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class RelationshipModelService:
    """Manage relationship state and expose strategy adjustments."""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def get_or_create(self, user_id: str) -> RelationshipState:
        """Load relationship state or create the default 0.5-trust state."""
        raw = await self.redis.get(_RELATIONSHIP_KEY.format(user_id=user_id))
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return RelationshipState.from_dict(json.loads(raw))

        state = RelationshipState(
            user_id=user_id,
            trust_level=_DEFAULT_TRUST,
            interaction_style="exploratory",
            correction_frequency=0.0,
            engagement_depth="surface",
            last_interaction_at=_now(),
        )
        await self._save(state)
        return state

    async def update_from_interaction(self, user_id: str, interaction_type: str) -> RelationshipState:
        """Update relationship from one user interaction."""
        if interaction_type not in _VALID_INTERACTION_TYPES:
            raise ValueError(f"Unsupported interaction_type: {interaction_type}")

        state = await self.get_or_create(user_id)
        state.total_interactions += 1
        state.last_interaction_at = _now()

        counts = dict(state.preferences.get("interaction_counts", {}))
        counts[interaction_type] = int(counts.get(interaction_type, 0)) + 1
        state.preferences["interaction_counts"] = counts
        state.preferences["last_interaction_type"] = interaction_type

        if interaction_type == "confirmed":
            state.total_confirmations += 1
            state.trust_level = min(_MAX_TRUST, state.trust_level + 0.02)
        elif interaction_type == "corrected":
            state.total_corrections += 1
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.05)
        elif interaction_type == "dismissed":
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.01)
        elif interaction_type == "expanded":
            state.trust_level = min(_MAX_TRUST, state.trust_level + 0.01)
        elif interaction_type == "ignored":
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.005)

        state.trust_level = round(state.trust_level, 4)
        state.correction_frequency = self._compute_correction_frequency(state)
        state.interaction_style = self._infer_interaction_style(state)
        state.engagement_depth = self._infer_engagement_depth(state)

        # D4: Update continuous dimensions
        self._update_dimensions(state, interaction_type)
        # D4: FSM stance transition
        state.stance = self._compute_stance(state)

        await self._save(state)
        logger.info(
            "Relationship updated: user={} interaction={} trust={:.2f} style={}",
            user_id,
            interaction_type,
            state.trust_level,
            state.interaction_style,
        )
        return state

    async def update_from_behavioral_signal(
        self, user_id: str, signal_type: str, metadata: dict[str, Any] | None = None,
    ) -> RelationshipState:
        """Update relationship from behavioral events (task completion, streaks, etc.).

        Trust changes are smaller than interaction-based changes to avoid
        overwhelming the signal from direct user feedback.
        """
        if signal_type not in _VALID_BEHAVIORAL_SIGNALS:
            raise ValueError(f"Unsupported behavioral signal: {signal_type}")

        state = await self.get_or_create(user_id)
        state.last_interaction_at = _now()

        meta = metadata or {}
        behavioral_counts = dict(state.preferences.get("behavioral_counts", {}))
        behavioral_counts[signal_type] = int(behavioral_counts.get(signal_type, 0)) + 1
        state.preferences["behavioral_counts"] = behavioral_counts

        if signal_type == "task_completed":
            state.total_tasks_completed += 1
            state.trust_level = min(_MAX_TRUST, state.trust_level + 0.015)
        elif signal_type == "task_abandoned":
            state.total_tasks_abandoned += 1
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.01)
        elif signal_type == "streak_maintained":
            streak_len = int(meta.get("streak_length", 0))
            state.current_streak = max(state.current_streak, streak_len)
            state.longest_streak = max(state.longest_streak, streak_len)
            # Streak bonus scales with length, capped
            bonus = min(0.03, 0.005 * streak_len)
            state.trust_level = min(_MAX_TRUST, state.trust_level + bonus)
        elif signal_type == "streak_broken":
            state.current_streak = 0
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.02)
        elif signal_type == "session_engaged":
            state.trust_level = min(_MAX_TRUST, state.trust_level + 0.005)
        elif signal_type == "session_idle":
            state.trust_level = max(_MIN_TRUST, state.trust_level - 0.005)

        state.trust_level = round(state.trust_level, 4)
        state.engagement_depth = self._infer_engagement_depth(state)

        await self._save(state)
        logger.info(
            "Relationship behavioral: user={} signal={} trust={:.2f} streak={}",
            user_id, signal_type, state.trust_level, state.current_streak,
        )
        return state

    async def get_strategy_adjustment(self, user_id: str) -> dict[str, Any]:
        """Get strategy adjustments based on relationship state.

        D4: Uses FSM stance + continuous dimensions for richer adjustments.
        """
        state = await self.get_or_create(user_id)

        # Base adjustment from FSM stance
        stance = state.stance
        if stance == "new":
            adjustment: dict[str, Any] = {
                "tone_adjustment": "gentle_exploratory",
                "proactivity_level": "confirm_before_acting",
                "explanation_depth": "brief",
                "requires_confirmation": True,
            }
        elif stance == "calibrating":
            adjustment = {
                "tone_adjustment": "calm_direct",
                "proactivity_level": "balanced",
                "explanation_depth": "medium",
                "requires_confirmation": False,
            }
        elif stance == "trusted":
            adjustment = {
                "tone_adjustment": "confident",
                "proactivity_level": "act_first",
                "explanation_depth": "summary",
                "requires_confirmation": False,
            }
        elif stance == "strained":
            adjustment = {
                "tone_adjustment": "cautious",
                "proactivity_level": "confirm_before_acting",
                "explanation_depth": "evidence_first",
                "requires_confirmation": True,
            }
        elif stance == "repairing":
            adjustment = {
                "tone_adjustment": "transparent",
                "proactivity_level": "balanced",
                "explanation_depth": "medium_with_evidence",
                "requires_confirmation": True,
            }
        elif stance == "cooldown":
            adjustment = {
                "tone_adjustment": "minimal",
                "proactivity_level": "low_frequency",
                "explanation_depth": "brief",
                "requires_confirmation": True,
            }
        else:
            adjustment = {
                "tone_adjustment": "calm_direct",
                "proactivity_level": "balanced",
                "explanation_depth": "medium",
                "requires_confirmation": False,
            }

        adjustment.update(
            {
                "stance": stance,
                "interaction_style": state.interaction_style,
                "engagement_depth": state.engagement_depth,
                "trust_level": state.trust_level,
                # D4 continuous dimensions
                "directness_tolerance": round(state.directness_tolerance, 3),
                "autonomy_preference": round(state.autonomy_preference, 3),
                "explanation_need": round(state.explanation_need, 3),
                "pressure_sensitivity": round(state.pressure_sensitivity, 3),
                "trust_in_strategy": round(state.trust_in_strategy, 3),
            }
        )

        if state.interaction_style == "corrective":
            adjustment["include_why_evidence"] = True
            adjustment["explanation_depth"] = "brief_with_evidence" if state.trust_level < 0.3 else "evidence_first"
        else:
            adjustment["include_why_evidence"] = False

        if state.interaction_style == "passive":
            adjustment["proactivity_level"] = "low_frequency"
            adjustment["frequency_adjustment"] = "reduced"
            adjustment["incentive_level"] = "increased"

        return adjustment

    async def _save(self, state: RelationshipState) -> None:
        await self.redis.set(
            _RELATIONSHIP_KEY.format(user_id=state.user_id),
            json.dumps(state.to_dict()),
            ex=30 * 24 * 3600,  # 30-day TTL — resets each sprint, no permanent personality
        )

    def _compute_correction_frequency(self, state: RelationshipState) -> float:
        if state.total_interactions <= 0:
            return 0.0
        return round((state.total_corrections / state.total_interactions) * 10, 4)

    def _infer_interaction_style(self, state: RelationshipState) -> str:
        counts = state.preferences.get("interaction_counts", {})
        total = max(state.total_interactions, 1)
        passive_count = int(counts.get("dismissed", 0)) + int(counts.get("ignored", 0))
        expanded_count = int(counts.get("expanded", 0))

        if state.correction_frequency >= 2.0:
            return "corrective"
        if state.total_interactions >= 3 and passive_count / total >= 0.5:
            return "passive"
        if state.total_interactions < 3 or expanded_count / total >= 0.25:
            return "exploratory"
        return "directive"

    def _infer_engagement_depth(self, state: RelationshipState) -> str:
        counts = state.preferences.get("interaction_counts", {})
        total = max(state.total_interactions, 1)
        expanded_count = int(counts.get("expanded", 0))

        if expanded_count >= 3 or (state.total_interactions >= 8 and expanded_count / total >= 0.3):
            return "deep"
        if state.total_interactions >= 3 or expanded_count >= 1:
            return "moderate"
        return "surface"

    def _update_dimensions(self, state: RelationshipState, interaction_type: str) -> None:
        """D4: Update continuous dimensions based on interaction."""
        step = 0.03
        if interaction_type == "confirmed":
            state.trust_in_strategy = min(1.0, state.trust_in_strategy + step)
            state.directness_tolerance = min(1.0, state.directness_tolerance + step * 0.5)
        elif interaction_type == "corrected":
            state.trust_in_strategy = max(0.0, state.trust_in_strategy - step * 2)
            state.explanation_need = min(1.0, state.explanation_need + step)
            state.pressure_sensitivity = min(1.0, state.pressure_sensitivity + step * 0.5)
        elif interaction_type == "expanded":
            state.autonomy_preference = min(1.0, state.autonomy_preference + step)
            state.explanation_need = max(0.0, state.explanation_need - step * 0.3)
        elif interaction_type == "dismissed":
            state.pressure_sensitivity = min(1.0, state.pressure_sensitivity + step)
            state.directness_tolerance = max(0.0, state.directness_tolerance - step)
        elif interaction_type == "ignored":
            state.pressure_sensitivity = min(1.0, state.pressure_sensitivity + step * 0.5)
            state.autonomy_preference = min(1.0, state.autonomy_preference + step * 0.3)

    def _compute_stance(self, state: RelationshipState) -> str:
        """D4: Compute FSM stance from current state."""
        if state.total_interactions == 0:
            return "new"
        if state.stance == "cooldown":
            # Cooldown: stay until trust recovers
            if state.trust_level >= 0.4:
                return "calibrating"
            return "cooldown"

        if state.correction_frequency >= 3.0:
            if state.stance in ("strained", "repairing"):
                return "cooldown"
            return "strained"

        if state.trust_level >= 0.7 and state.correction_frequency < 1.0:
            return "trusted"

        if state.stance == "strained" and state.trust_level >= 0.4:
            return "repairing"

        if state.total_interactions >= 3 and state.trust_level >= 0.4:
            return "calibrating"

        return state.stance if state.stance in _VALID_STANCES else "calibrating"
