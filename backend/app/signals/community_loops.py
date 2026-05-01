"""
Core: execution
Phase: sense→clarify→plan
Stage: Signal-to-Action Spine P1-4 CommunityDirective 3 Loops

Community feedback loops turn aggregate/partner/resource inputs into bounded,
privacy-preserving patches for the Signal-to-Action Spine.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


class CommunityLoopManager:
    """3 community feedback loops + partner accountability loop."""

    # Loop 1: cohort_mistake → anonymous hint
    def build_cohort_mistake_hint(self, pattern: dict[str, Any]) -> dict[str, Any] | None:
        """Convert cohort mistake pattern to an anonymous hint card."""
        cohort_size = int(pattern.get("cohort_size", 0) or 0)
        if cohort_size < 3:
            return None

        subject = str(pattern.get("subject", "当前科目"))
        topic = str(
            pattern.get("topic")
            or pattern.get("knowledge_node_title")
            or pattern.get("knowledge_node_id")
            or "这个知识点"
        )
        mistake_type = str(pattern.get("mistake_type", "理解"))
        misconception = str(pattern.get("common_misconception", "")).strip()
        tip = f"先检查这个常见误解：{misconception}" if misconception else "先回到定义和例题，对照检查关键条件。"

        return {
            "hint_type": "cohort_mistake",
            "title": "同伴易错提醒",
            "anonymous_summary": f"有{cohort_size}位同学在{subject}的{topic}上容易犯{mistake_type}错误",
            "affected_nodes": [str(pattern.get("knowledge_node_id", topic))],
            "tip": tip,
            "privacy": "anonymous_aggregate_only",
        }

    # Loop 2: partner_observation → strategy adjustment
    def apply_partner_feedback(self, feedback: dict[str, Any]) -> dict[str, Any] | None:
        """Process an accountability partner observation without writing personal state."""
        observation_type = str(feedback.get("observation_type", ""))
        if observation_type not in {"pacing", "focus", "difficulty", "morale"}:
            return None

        target_area = str(feedback.get("target_area", "") or "current_goal")
        observation_text = str(feedback.get("observation_text", "")).strip()
        sanitized_summary = observation_text[:240] if observation_text else "partner observation"

        if observation_type == "pacing":
            direction = self._infer_pacing_direction(observation_text)
            claim = "pacing_too_fast" if direction == "slow_down" else "pacing_too_slow"
            return {
                "adjustment_type": "pace_adjustment",
                "strategy_patch": {
                    "pace_direction": direction,
                    "target_area": target_area,
                    "use_next_48h_replan": True,
                },
                "scope": "next_48h",
                "state_key": "community_partner_feedback",
                "claim": claim,
                "evidence_summary": sanitized_summary,
            }

        if observation_type == "focus":
            return {
                "adjustment_type": "topic_refocus",
                "strategy_patch": {
                    "target_area": target_area,
                    "reduce_context_switching": True,
                },
                "scope": "current_sprint",
                "state_key": "community_partner_feedback",
                "claim": "focus_refocus_needed",
                "evidence_summary": sanitized_summary,
            }

        if observation_type == "difficulty":
            direction = self._infer_difficulty_direction(observation_text)
            return {
                "adjustment_type": "difficulty_shift",
                "strategy_patch": {
                    "difficulty_direction": direction,
                    "target_area": target_area,
                },
                "scope": "next_48h",
                "state_key": "community_partner_feedback",
                "claim": "difficulty_shift_needed",
                "evidence_summary": sanitized_summary,
            }

        return {
            "adjustment_type": "encouragement",
            "strategy_patch": {
                "target_area": target_area,
                "tone": "encouraging_low_pressure",
            },
            "scope": "this_turn",
            "state_key": "community_partner_feedback",
            "claim": "morale_encouragement_needed",
            "evidence_summary": sanitized_summary,
        }

    # Loop 3: resource_quality → recommendation optimization
    def score_resource_quality(self, resource_data: dict[str, Any]) -> dict[str, Any]:
        """Score a shared resource for recommendation quality."""
        usage_count = int(resource_data.get("usage_count", 0) or 0)
        if usage_count < 3:
            return {
                "resource_id": resource_data.get("resource_id"),
                "quality_score": None,
                "recommendation_level": "too_few_data",
                "reason": "too_few_data",
            }

        ratings = [self._clamp(float(r)) for r in resource_data.get("peer_ratings", [])]
        average_rating = sum(ratings) / len(ratings) if ratings else 0.0
        completion_rate = self._clamp(float(resource_data.get("completion_rate", 0.0) or 0.0))
        relevance_score = self._clamp(float(resource_data.get("relevance_score", 0.0) or 0.0))
        quality_score = round(average_rating * 0.5 + completion_rate * 0.3 + relevance_score * 0.2, 3)

        if quality_score >= 0.8:
            recommendation_level = "high"
        elif quality_score >= 0.5:
            recommendation_level = "medium"
        else:
            recommendation_level = "low"

        return {
            "resource_id": resource_data.get("resource_id"),
            "quality_score": quality_score,
            "recommendation_level": recommendation_level,
            "reason": (
                f"peer_rating={average_rating:.2f}, "
                f"completion={completion_rate:.2f}, relevance={relevance_score:.2f}"
            ),
        }

    @staticmethod
    def _infer_pacing_direction(observation_text: str) -> str:
        lowered = observation_text.lower()
        slow_down_markers = ("fast", "rush", "rushed", "overwhelmed", "too much", "太快", "赶", "压力")
        speed_up_markers = ("slow", "stuck", "stalled", "drag", "太慢", "拖", "停滞")
        if any(marker in lowered for marker in slow_down_markers):
            return "slow_down"
        if any(marker in lowered for marker in speed_up_markers):
            return "speed_up"
        return "slow_down"

    @staticmethod
    def _infer_difficulty_direction(observation_text: str) -> str:
        lowered = observation_text.lower()
        if any(marker in lowered for marker in ("hard", "difficult", "too much", "难", "吃力")):
            return "easier"
        if any(marker in lowered for marker in ("easy", "bored", "简单", "无聊")):
            return "harder"
        return "easier"

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, value))

    # Loop 4: partner accountability — check-in milestone tracking

    async def record_partner_checkin(
        self,
        redis_client: Any,
        *,
        user_id: str,
        partner_id: str,
        checkin_type: str,  # "encouragement" | "nudge" | "celebration" | "check_in"
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a partner check-in event and update accountability state."""
        key = f"spine:partner_accountability:{user_id}"
        raw = await redis_client.get(key)
        state: dict[str, Any] = json.loads(raw) if raw else {
            "partner_id": partner_id,
            "total_checkins": 0,
            "checkin_types": {},
            "last_checkin_at": None,
            "streak_days": 0,
        }

        state["total_checkins"] = int(state.get("total_checkins", 0)) + 1
        state["last_checkin_at"] = _now_iso()
        types = dict(state.get("checkin_types", {}))
        types[checkin_type] = int(types.get(checkin_type, 0)) + 1
        state["checkin_types"] = types

        await redis_client.set(key, json.dumps(state), ex=30 * 24 * 3600)

        # Generate accountability signal if threshold reached
        signal = None
        total = state["total_checkins"]
        if total >= 3:
            signal = {
                "state_key": "partner_accountability_active",
                "claim": f"partner_has_{total}_checkins",
                "confidence": min(0.9, 0.5 + 0.05 * total),
                "scope": "current_sprint",
                "ttl_hours": 168,
                "evidence_summary": f"Partner {checkin_type} (total: {total})",
                "priority": "medium" if total < 7 else "high",
            }

        logger.info(
            "PartnerAccountability: user={} partner={} type={} total={}",
            user_id, partner_id, checkin_type, state["total_checkins"],
        )

        return {"recorded": True, "total_checkins": total, "signal": signal}

    async def get_accountability_state(
        self, redis_client: Any, user_id: str,
    ) -> dict[str, Any]:
        """Get current accountability state for a user."""
        key = f"spine:partner_accountability:{user_id}"
        raw = await redis_client.get(key)
        if not raw:
            return {"active": False, "total_checkins": 0}
        state = json.loads(raw)
        state["active"] = state.get("total_checkins", 0) >= 3
        return state


def _now_iso() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
