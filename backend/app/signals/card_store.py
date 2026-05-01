"""
Core: execution
Phase: sense→execute→reflect
Stage: P2-1 Phase 2 — Card builders extracted from SpineOrchestrator.

"Divine moment" card builders: recovery card, context receipt, community hint.
Each builds a structured dict, persists to Redis with TTL, and returns it.
"""
from __future__ import annotations

import json
from typing import Any

from loguru import logger


class CardStore:
    """Redis-backed divine-moment card store."""

    def __init__(self, redis: Any, community_loops: Any = None) -> None:
        self.redis = redis
        self.community_loops = community_loops

    async def build_recovery_card(
        self,
        *,
        user_id: str,
        elapsed_minutes: float,
        last_task_id: str | None = None,
        last_task_status: str | None = None,
    ) -> dict[str, Any] | None:
        try:
            recovery_card: dict[str, Any] = {
                "type": "recovery_card",
                "user_id": user_id,
                "elapsed_minutes": elapsed_minutes,
                "last_task_id": last_task_id,
                "last_task_status": last_task_status,
                "options": [
                    {"label": "做完了，补记录", "value": "completed"},
                    {"label": "做了一半，卡住了", "value": "stuck"},
                    {"label": "没开始", "value": "not_started"},
                    {"label": "换个小任务", "value": "switch_task"},
                ],
            }

            if elapsed_minutes >= 120:
                recovery_card["urgency"] = "high"
                recovery_card["message"] = f"你离开了大约 {int(elapsed_minutes / 60)} 小时。"
            elif elapsed_minutes >= 60:
                recovery_card["urgency"] = "medium"
                recovery_card["message"] = f"你离开了大约 {int(elapsed_minutes)} 分钟。"
            else:
                recovery_card["urgency"] = "low"
                recovery_card["message"] = f"你离开了 {int(elapsed_minutes)} 分钟。"

            if last_task_id:
                recovery_card["message"] += " 上一张任务卡预计完成，但还没收到反馈。"

            await self.redis.set(
                f"spine:card:recovery:{user_id}:latest",
                json.dumps(recovery_card),
                ex=24 * 3600,
            )

            return recovery_card
        except Exception:
            logger.warning("build_recovery_card: failed", exc_info=True)
            return None

    async def build_context_receipt(
        self,
        *,
        user_id: str,
        used_sources: list[str] | None = None,
        excluded_sources: list[str] | None = None,
        reason: str = "",
        retrieval_mode: str = "auto",
    ) -> dict[str, Any]:
        receipt: dict[str, Any] = {
            "type": "context_receipt",
            "used": used_sources or [],
            "excluded": excluded_sources or [],
            "reason": reason,
            "retrieval_mode": retrieval_mode,
            "user_actions": [
                {"label": "按完整资料重讲", "value": "force_full_source"},
                {"label": "不要用这份资料", "value": "exclude_source"},
                {"label": "查看为什么", "value": "explain_decision"},
            ],
        }
        try:
            await self.redis.set(
                f"spine:card:context_receipt:{user_id}:latest",
                json.dumps(receipt),
                ex=2 * 3600,
            )
        except Exception:
            logger.warning("build_context_receipt: redis failed", exc_info=True)
        return receipt

    async def build_community_hint(
        self,
        *,
        user_id: str,
        knowledge_node: str,
        common_mistake: str,
        cohort_size: int,
    ) -> dict[str, Any] | None:
        try:
            if self.community_loops is not None:
                hint = self.community_loops.build_cohort_mistake_hint({
                    "knowledge_node_id": knowledge_node,
                    "common_misconception": common_mistake,
                    "cohort_size": cohort_size,
                })
                if hint is None:
                    return None
                message = hint.get("hint_text", "")
            else:
                message = ""

            card = {
                "type": "community_hint",
                "knowledge_node": knowledge_node,
                "common_mistake": common_mistake,
                "cohort_size": cohort_size,
                "message": message,
            }

            await self.redis.set(
                f"spine:card:community_hint:{user_id}:latest",
                json.dumps(card),
                ex=48 * 3600,
            )
            return card
        except Exception:
            logger.warning("build_community_hint: failed", exc_info=True)
            return None
