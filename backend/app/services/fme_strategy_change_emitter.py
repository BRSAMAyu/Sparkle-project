"""Emit a Causal Timeline card when a task strategy changes.

Phase-4 Causal Visibility — when the PolicyEngine produces a different
strategy than the previous one (because of belief bias, user correction,
or L3 session closure), this emitter pushes a `task_strategy_change`
timeline card through the event bus so the user sees "why did my task
change" in real-time.

The emitter is a standalone function designed to be called from
SpineOrchestrator when it detects a directive regeneration that changed
the task_type or strategy.

Timeline card shape (consumed by causal_timeline_panel.dart):
{
    "card_type": "task_strategy_change",
    "headline": "为什么今天任务变了",
    "summary": "昨天你连续两次在TCP窗口题中卡住...",
    "evidence_chain": [
        {"type": "outcome", "summary": "昨天任务失败×2"},
        {"type": "user_correction", "summary": "你反馈：不是没时间，是不会做"},
        {"type": "policy_change", "summary": "策略从 shrink_task 改为 worked_example_first"}
    ]
}
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.core.cache import cache_service


async def emit_strategy_change_card(
    user_id: str,
    *,
    old_strategy: str,
    new_strategy: str,
    reason: str = "",
    evidence_steps: list[dict[str, str]] | None = None,
) -> None:
    """Push a task_strategy_change card into the user's timeline.

    The card is stored in Redis under the user's causal timeline key so
    the Flutter CausalTimelinePanel can pick it up on next load.
    """
    if old_strategy == new_strategy:
        return

    from app.core.event_bus import event_bus

    chain = list(evidence_steps or [])
    if not chain:
        chain.append({"type": "policy_change", "summary": f"策略从 {old_strategy} 改为 {new_strategy}"})
    if reason:
        chain.append({"type": "reason", "summary": reason})

    card = {
        "card_type": "task_strategy_change",
        "headline": "为什么今天任务变了",
        "summary": reason or f"策略已从 {old_strategy} 调整为 {new_strategy}，以更贴合你的实际学习状况。",
        "evidence_chain": chain[:5],
    }

    try:
        await event_bus.publish(
            "CausalTimelineUpdated",
            {
                "user_id": user_id,
                "card": card,
            },
        )
        logger.info(
            "Strategy change card emitted for user={}: {} → {}",
            user_id, old_strategy, new_strategy,
        )
    except Exception:
        logger.debug("Strategy change card emit skipped", exc_info=True)
