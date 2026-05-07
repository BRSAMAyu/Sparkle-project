"""Bridge: L3 SessionClosure → SpineOrchestrator.close_aurora_session().

Phase-3 Execution Wire — closes the loop between Aurora L3 interactive
modeling sessions and the Causal Control Spine.

Before this module:
  l3_full_core.produce_closure() → SessionClosure (returned, never consumed)
  spine_orchestrator.close_aurora_session() ← expects raw dicts (never called from L3)

After this module:
  AuroraCoreSessionService.close_session() → produce_closure() → bridge → close_aurora_session()
  State patches + policy changes flow through the Spine's audit trail.
  Regenerated directives alter the next task card.

The bridge is a standalone function (not a mixin or base-class override) so
it can be composed into the existing service without modifying its source.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.cache import cache_service
from app.services.fme_strategy_change_emitter import emit_strategy_change_card
from app.signals.aurora_core_session import SessionClosure
from app.signals.spine_orchestrator import SpineOrchestrator, get_spine_orchestrator


async def apply_l3_closure_to_spine(
    user_id: str,
    closure: SessionClosure,
) -> dict[str, Any] | None:
    """Consume an L3 SessionClosure and propagate it through the Spine.

    Returns the close_aurora_session result (contains regenerated_directives)
    or None if the spine was unavailable.
    """
    if not closure.state_patches and not closure.policy_changes:
        logger.debug(
            "L3 closure bridge: nothing to apply (session={})",
            closure.session_id,
        )
        return None

    spine: SpineOrchestrator | None = None
    try:
        spine = get_spine_orchestrator(cache_service.redis)
    except Exception:
        logger.warning("L3 closure bridge: SpineOrchestrator init failed", exc_info=True)
        return None

    patch_dicts = [p.__dict__ if hasattr(p, "__dict__") else dict(p) for p in closure.state_patches]
    change_dicts = [c.__dict__ if hasattr(c, "__dict__") else dict(c) for c in closure.policy_changes]

    try:
        result = await spine.close_aurora_session(
            closure.session_id,
            state_patches=patch_dicts,
            policy_changes=change_dicts,
            user_summary=closure.user_visible_summary,
        )
        if result and result.get("regenerated_directives"):
            directives = result["regenerated_directives"]
            logger.info(
                "L3 closure bridge: session={} → {} directives regenerated for user={}",
                closure.session_id,
                len(directives),
                user_id,
            )
            old_strategy = (
                (change_dicts[0].get("previous_strategy") if change_dicts else None)
                or "unknown"
            )
            new_strategy = (
                directives[0].get("strategy") if directives else None
            ) or str(directives[0]) if directives else "unknown"
            reason = closure.user_visible_summary or ""
            await emit_strategy_change_card(
                user_id,
                old_strategy=old_strategy,
                new_strategy=new_strategy,
                reason=reason,
            )
        return result
    except Exception:
        logger.warning(
            "L3 closure bridge: close_aurora_session failed for session={}",
            closure.session_id,
            exc_info=True,
        )
        return None
