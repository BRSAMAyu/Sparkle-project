"""
Core: execution
Phase: sense→clarify→plan→execute→reflect
Stage: Aurora ↔ Spine Bridge

Bidirectional bridge between Aurora Runtime v1 and Signal-to-Action Spine.

Spine → Aurora: Active directives, state packet, risk flags inject into DashboardReadout
Aurora → Spine: Decision outcomes feed back into Spine's outcome recorder
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger


class SpineAuroraBridge:
    """Bridge between Aurora decision loop and Signal Spine.

    Two-way data flow:
    1. Spine → Aurora: Fetch active directives/state → inject into DashboardReadout
    2. Aurora → Spine: Feed decision outcomes back for attribution tracking
    """

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def get_context_for_aurora(self, user_id: str) -> dict[str, Any]:
        """Fetch Spine context for Aurora's DashboardReadout.

        Returns a dict with:
        - active_directive: Current active directive (if any)
        - risk_flags: Active risk flags from state register
        - recent_outcomes: Summary of recent intervention outcomes
        - relationship: Trust level and interaction style from relationship model
        """
        context: dict[str, Any] = {
            "active_directive": None,
            "risk_flags": [],
            "recent_outcomes_summary": None,
            "relationship_trust": None,
        }

        try:
            # Fetch active directive
            directive_raw = await self.redis.get(f"spine:directive:active:{user_id}")
            if directive_raw:
                directive = json.loads(directive_raw if isinstance(directive_raw, str) else directive_raw.decode())
                context["active_directive"] = {
                    "type": directive.get("directive_type"),
                    "strategy": directive.get("strategy_key"),
                    "reason": directive.get("user_visible_reason"),
                    "constraints": directive.get("execution_constraints"),
                }

            # Fetch state entries for risk flags
            state_keys_raw = await self.redis.smembers(f"spine:state:keys:{user_id}")
            risk_flags: list[str] = []
            for key in state_keys_raw:
                key_str = key if isinstance(key, str) else key.decode()
                state_raw = await self.redis.get(f"spine:state:{user_id}:{key_str}")
                if state_raw:
                    state = json.loads(state_raw if isinstance(state_raw, str) else state_raw.decode())
                    if state.get("confidence", 0) >= 0.7 and "risk" in state.get("scope", ""):
                        risk_flags.append(state.get("value", ""))
            context["risk_flags"] = risk_flags

            # Fetch recent outcome summary
            effects_raw = await self.redis.lrange(f"spine:effects:{user_id}", 0, 4)
            if effects_raw:
                outcomes: list[dict[str, Any]] = []
                for raw in effects_raw:
                    raw_str = raw if isinstance(raw, str) else raw.decode()
                    effects_data = json.loads(raw_str)
                    outcomes.append({
                        "strategy": effects_data.get("strategy_key"),
                        "effectiveness": effects_data.get("effectiveness"),
                    })
                context["recent_outcomes_summary"] = outcomes

            # Fetch relationship trust level
            rel_raw = await self.redis.get(f"spine:relationship:{user_id}")
            if rel_raw:
                rel = json.loads(rel_raw if isinstance(rel_raw, str) else rel_raw.decode())
                context["relationship_trust"] = rel.get("trust_level")

        except Exception as e:
            logger.debug(f"SpineAuroraBridge.get_context_for_aurora skipped: {e}")

        return context

    async def feed_aurora_decision(
        self,
        *,
        user_id: str,
        action: str,
        surface: str,
        chat_directive: dict[str, Any] | None = None,
    ) -> None:
        """Feed Aurora's decision back to Spine for attribution tracking."""
        try:
            event = {
                "source": "aurora_decision",
                "user_id": user_id,
                "action": action,
                "surface": surface,
                "chat_directive_summary": None,
            }
            if chat_directive:
                event["chat_directive_summary"] = {
                    "intent": chat_directive.get("intent"),
                    "target_domain": chat_directive.get("target_domain"),
                }

            await self.redis.rpush(
                f"spine:aurora_decisions:{user_id}",
                json.dumps(event),
            )
            await self.redis.ltrim(f"spine:aurora_decisions:{user_id}", -50, -1)
            await self.redis.expire(f"spine:aurora_decisions:{user_id}", 30 * 24 * 3600)
        except Exception as e:
            logger.debug(f"SpineAuroraBridge.feed_aurora_decision skipped: {e}")

    async def get_spine_directive_for_prompt(self, user_id: str) -> dict[str, Any] | None:
        """Get the active Spine directive formatted for prompt injection.

        Returns None if no active directive exists.
        """
        try:
            directive_raw = await self.redis.get(f"spine:directive:active:{user_id}")
            if not directive_raw:
                return None
            d = json.loads(directive_raw if isinstance(directive_raw, str) else directive_raw.decode())
            return {
                "strategy_key": d.get("strategy_key"),
                "user_visible_reason": d.get("user_visible_reason"),
                "directive_type": d.get("directive_type"),
                "constraints": d.get("execution_constraints"),
            }
        except Exception:
            return None
