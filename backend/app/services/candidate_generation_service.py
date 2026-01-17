"""
Candidate Generation Service
Generates candidate actions from signals with 5 constraints

This service converts signals into actionable candidate suggestions
while enforcing guardrails to prevent over-intervention.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
from loguru import logger

from app.services.signal_generation_service import Signals, Signal
from app.core.cache import cache_service


@dataclass
class CandidateAction:
    """Enhanced candidate action (v2)"""
    id: str
    action_type: str  # "break", "review", "clarify", "plan_split"
    title: str
    reason: str  # "因为你刚刚..."
    confidence: float
    timing_hint: str  # "now", "in_5min", "after_current_task"
    payload_seed: str  # For strong model expansion
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "action_type": self.action_type,
            "title": self.title,
            "reason": self.reason,
            "confidence": self.confidence,
            "timing_hint": self.timing_hint,
            "payload_seed": self.payload_seed,
            "metadata": self.metadata,
        }


class CandidateGenerationService:
    """
    Generate candidate actions with 5 constraints

    Constraints:
    1. Cooldown time (30-60 min per action type)
    2. Confidence threshold (>65%)
    3. Daily budget (8 max interventions per day)
    4. Diversity control (no 3 consecutive same-type actions)
    5. Cost budget (P0 only - deferred in MVP)
    """

    # Constraint 1: Cooldown times (minutes)
    COOLDOWN_TIMES = {
        "break": 60,
        "review": 30,
        "clarify": 45,
        "plan_split": 60,
    }

    # Constraint 2: Confidence threshold
    MIN_CONFIDENCE = 0.65

    # Constraint 3: Daily budget
    MAX_DAILY_INTERVENTIONS = 8

    # Constraint 4: Max candidates per request
    MAX_CANDIDATES_PER_REQUEST = 3

    async def generate_candidates(
        self,
        user_id: str,
        signals: Signals
    ) -> List[CandidateAction]:
        """
        Generate candidate actions from signals with constraints.

        Applies all 5 constraints in order:
        1. Cooldown time
        2. Confidence threshold (already filtered in signal generation)
        3. Daily budget
        4. Diversity control
        5. Cost budget (P0 only - deferred)

        Args:
            user_id: User identifier
            signals: Signals from signal generation service

        Returns:
            List of candidate actions (max 3)
        """
        # Constraint 3: Check daily budget
        daily_count = await self._get_daily_intervention_count(user_id)
        if daily_count >= self.MAX_DAILY_INTERVENTIONS:
            logger.info(
                f"User {user_id} reached daily intervention budget: "
                f"{daily_count}/{self.MAX_DAILY_INTERVENTIONS}"
            )
            return []

        candidates = []

        # Map signals to candidate actions
        for signal in signals.signals:
            action_type = self._signal_to_action_type(signal.type)

            # Constraint 1: Check cooldown
            if await self._is_in_cooldown(user_id, action_type):
                logger.debug(
                    f"Skipping action {action_type} for user {user_id}: in cooldown"
                )
                continue

            # Constraint 2: Check confidence (redundant, signals already filtered)
            if signal.confidence < self.MIN_CONFIDENCE:
                continue

            # Generate candidate
            candidate = self._create_candidate(signal, action_type)
            candidates.append(candidate)

        # Constraint 4: Diversity control
        candidates = self._apply_diversity(candidates)

        # Update cooldowns for accepted candidates
        for candidate in candidates:
            await self._set_cooldown(user_id, candidate.action_type)

        # Update daily count
        if candidates:
            await self._increment_daily_count(user_id, len(candidates))

        logger.info(
            f"Generated {len(candidates)} candidates for user {user_id} "
            f"(daily: {daily_count + len(candidates)}/{self.MAX_DAILY_INTERVENTIONS})"
        )

        return candidates

    def _signal_to_action_type(self, signal_type: str) -> str:
        """
        Map signal type to action type.

        Signal types → Action types mapping:
        - needs_break → break
        - topic_stuck → clarify
        - high_comprehension_friction → clarify
        - risk_dropout_soon → plan_split
        - consecutive_failures → plan_split
        - session_too_short → plan_split
        - best_next_action_window → review
        """
        mapping = {
            "needs_break": "break",
            "topic_stuck": "clarify",
            "high_comprehension_friction": "clarify",
            "risk_dropout_soon": "plan_split",
            "consecutive_failures": "plan_split",
            "session_too_short": "plan_split",
            "best_next_action_window": "review",
        }
        return mapping.get(signal_type, "review")

    def _create_candidate(self, signal: Signal, action_type: str) -> CandidateAction:
        """
        Create candidate action from signal.

        Args:
            signal: Signal with confidence and reason
            action_type: Mapped action type

        Returns:
            CandidateAction with title, reason, and payload seed
        """
        # Action type templates
        templates = {
            "break": {
                "title": "休息一下",
                "payload_seed": "suggest_break_activity",
                "timing_hint": "now",
            },
            "clarify": {
                "title": "换个角度理解",
                "payload_seed": "suggest_alternative_explanation",
                "timing_hint": "now",
            },
            "plan_split": {
                "title": "拆小任务",
                "payload_seed": "breakdown_current_task",
                "timing_hint": "after_current_task",
            },
            "review": {
                "title": "复习巩固",
                "payload_seed": "suggest_review_topic",
                "timing_hint": "in_5min",
            },
        }

        template = templates.get(action_type, templates["review"])

        # Generate unique ID
        candidate_id = f"ca_{int(datetime.utcnow().timestamp() * 1000)}"

        return CandidateAction(
            id=candidate_id,
            action_type=action_type,
            title=template["title"],
            reason=f"因为{signal.reason}",
            confidence=signal.confidence,
            timing_hint=template["timing_hint"],
            payload_seed=template["payload_seed"],
            metadata=signal.metadata,
        )

    def _apply_diversity(self, candidates: List[CandidateAction]) -> List[CandidateAction]:
        """
        Constraint 4: Diversity control

        Rules:
        - Don't show 3 consecutive same-type actions
        - Limit to max 3 candidates per request
        - Shuffle to avoid bias

        Args:
            candidates: List of candidate actions

        Returns:
            Filtered and diversified list (max 3 candidates)
        """
        if len(candidates) <= 1:
            return candidates

        # Shuffle to avoid bias
        shuffled = candidates.copy()
        random.shuffle(shuffled)

        # Ensure diversity: no 3 consecutive same-type
        diversified = []
        for candidate in shuffled:
            # Check last 2 candidates
            if len(diversified) >= 2:
                last_two_types = [c.action_type for c in diversified[-2:]]
                if all(t == candidate.action_type for t in last_two_types):
                    # Would create 3 consecutive same-type, skip
                    logger.debug(
                        f"Skipping candidate {candidate.action_type} for diversity"
                    )
                    continue

            diversified.append(candidate)

            # Stop at max candidates
            if len(diversified) >= self.MAX_CANDIDATES_PER_REQUEST:
                break

        return diversified

    async def _is_in_cooldown(self, user_id: str, action_type: str) -> bool:
        """
        Check if action type is in cooldown.

        Args:
            user_id: User identifier
            action_type: Action type to check

        Returns:
            True if in cooldown, False otherwise
        """
        key = f"candidate_cooldown:{user_id}:{action_type}"
        value = await cache_service.get(key)
        return value is not None

    async def _set_cooldown(self, user_id: str, action_type: str):
        """
        Set cooldown for action type.

        Args:
            user_id: User identifier
            action_type: Action type to set cooldown for
        """
        key = f"candidate_cooldown:{user_id}:{action_type}"
        cooldown_minutes = self.COOLDOWN_TIMES.get(action_type, 60)
        cooldown_seconds = cooldown_minutes * 60

        await cache_service.set(key, "1", ttl=cooldown_seconds)

        logger.debug(
            f"Set cooldown for {action_type} (user {user_id}): {cooldown_minutes} min"
        )

    async def _get_daily_intervention_count(self, user_id: str) -> int:
        """
        Get today's intervention count for user.

        Args:
            user_id: User identifier

        Returns:
            Number of interventions today
        """
        today = datetime.utcnow().date().isoformat()
        key = f"daily_interventions:{user_id}:{today}"
        count = await cache_service.get(key)
        return int(count) if count else 0

    async def _increment_daily_count(self, user_id: str, count: int):
        """
        Increment daily intervention count.

        Args:
            user_id: User identifier
            count: Number to increment by
        """
        today = datetime.utcnow().date().isoformat()
        key = f"daily_interventions:{user_id}:{today}"
        current = await self._get_daily_intervention_count(user_id)
        new_count = current + count

        # TTL: 24 hours
        await cache_service.set(key, str(new_count), ttl=86400)

        logger.debug(
            f"Updated daily interventions for user {user_id}: "
            f"{current} → {new_count}/{self.MAX_DAILY_INTERVENTIONS}"
        )

    async def generate_from_dict(
        self,
        user_id: str,
        signals_dict: Dict[str, Any]
    ) -> List[CandidateAction]:
        """
        Generate candidates from signals dictionary.

        Args:
            user_id: User identifier
            signals_dict: Dictionary representation of Signals

        Returns:
            List of candidate actions
        """
        # Reconstruct Signals from dict
        from app.services.signal_generation_service import Signal, Signals

        signal_list = []
        for signal_data in signals_dict.get("signals", []):
            signal = Signal(
                type=signal_data.get("type", ""),
                confidence=signal_data.get("confidence", 0.0),
                reason=signal_data.get("reason", ""),
                metadata=signal_data.get("metadata", {}),
            )
            signal_list.append(signal)

        signals = Signals(
            version=signals_dict.get("version", "sig_v1"),
            signals=signal_list,
        )

        return await self.generate_candidates(user_id, signals)


# Singleton instance
candidate_generation_service = CandidateGenerationService()
