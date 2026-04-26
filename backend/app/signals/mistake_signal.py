"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine M3

Mistake Signal Detector — 检测同一知识节点上的重复错误。
连续 N 次同一节点的错题 → transfer_failure → avoid_new_chapter + worked_example。

用户可见变化：下一张任务卡自动改为错因修复，不推进新章节。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid

_MISTAKE_HISTORY_KEY = "spine:mistake_history:{user_id}:{node_id}"
_NODE_MISTAKE_SIGNAL_KEY = "spine:mistake_signal:{user_id}:{node_id}"
_CONSECUTIVE_MISTAKES_TRIGGER = 3  # 连续 3 次同节点错题触发
_SIGNAL_TTL_HOURS = 72
_MISTAKE_HISTORY_TTL = 7 * 24 * 3600  # 7 days
_MAX_HISTORY = 20


class MistakeSignalDetector:
    """检测同一知识节点上的重复错误，生成 transfer_failure 信号。"""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def on_error_created(
        self,
        *,
        user_id: str,
        error_id: str,
        linked_node_ids: list[str],
        error_type: str | None = None,
    ) -> list[ActionableSignal]:
        """
        错题创建事件处理。检查每个关联节点是否达到重复错误阈值。

        Returns:
            List of ActionableSignals (one per triggering node).
        """
        signals = []
        for node_id in linked_node_ids:
            signal = await self._check_node_mistakes(
                user_id=user_id,
                error_id=error_id,
                node_id=node_id,
                error_type=error_type,
            )
            if signal:
                signals.append(signal)
        return signals

    async def _check_node_mistakes(
        self,
        *,
        user_id: str,
        error_id: str,
        node_id: str,
        error_type: str | None,
    ) -> ActionableSignal | None:
        # 记录本次错误
        key = _MISTAKE_HISTORY_KEY.format(user_id=user_id, node_id=node_id)
        entry = json.dumps({
            "error_id": error_id,
            "error_type": error_type,
            "node_id": node_id,
        })
        await self.redis.lpush(key, entry)
        await self.redis.ltrim(key, 0, _MAX_HISTORY - 1)
        await self.redis.expire(key, _MISTAKE_HISTORY_TTL)

        # 检查连续错误次数
        entries = await self.redis.lrange(key, 0, _CONSECUTIVE_MISTAKES_TRIGGER + 5)
        consecutive = 0
        for raw in entries:
            try:
                e = json.loads(raw)
                consecutive += 1
            except (json.JSONDecodeError, TypeError):
                continue

        if consecutive < _CONSECUTIVE_MISTAKES_TRIGGER:
            return None

        # 达到阈值 → 检查是否已经有活跃信号（避免重复生成）
        signal_key = _NODE_MISTAKE_SIGNAL_KEY.format(user_id=user_id, node_id=node_id)
        existing = await self.redis.get(signal_key)
        if existing:
            return None

        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[error_id],
            source_system="error_book",
            state_key="knowledge_transfer",
            claim="transfer_failure",
            confidence=min(0.5 + consecutive * 0.12, 0.92),
            scope="current_sprint",
            ttl_hours=_SIGNAL_TTL_HOURS,
            evidence_summary=(
                f"知识节点 {node_id} 连续 {consecutive} 次出错"
                f"（最近一次错因类型：{error_type or '未知'}），"
                f"判断为知识迁移失败，需要 worked_example 修复。"
            ),
            possible_effects=[
                "avoid_new_chapter",
                "require_worked_example",
                "reduce_task_difficulty",
            ],
            priority="high",
        )

        # 标记此节点已有活跃信号
        await self.redis.set(signal_key, signal.signal_id, ex=_SIGNAL_TTL_HOURS * 3600)

        logger.info(
            "MistakeSignal: node={} consecutive={} signal={}",
            node_id, consecutive, signal.signal_id,
        )
        return signal
