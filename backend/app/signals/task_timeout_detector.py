"""
Core: execution
Phase: sense→clarify
Stage: Signal-to-Action Spine M1-Step2

Task Timeout Signal Detector — 固定规则：连续2次任务超时 → task_granularity_fit=too_large。

不要一上来 LLM 推断。先用规则检测，证明链路可用。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid

_TIMEOUT_THRESHOLD = 1.4          # actual > 140% of estimated = timeout
_CONSECUTIVE_TIMEOUTS_TRIGGER = 2  # 连续 2 次超时触发信号
_SIGNAL_TTL_HOURS = 72
_SIGNAL_SCOPE = "current_sprint"
_SIGNAL_STATE_KEY = "task_granularity_fit"
_SIGNAL_CLAIM = "recent_task_too_large"
_USER_TIMEOUT_HISTORY_KEY = "spine:timeout_history:{user_id}"
_MAX_HISTORY = 10


class TaskTimeoutDetector:
    """检测连续任务超时，生成 ActionableSignal。"""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def on_task_completed(
        self,
        *,
        user_id: str,
        task_id: str,
        estimated_minutes: int,
        actual_minutes: int,
        plan_id: str | None = None,
    ) -> ActionableSignal | None:
        """
        检查任务完成事件是否构成超时，并判断是否达到连续触发阈值。

        Returns:
            ActionableSignal if triggered, None otherwise.
        """
        if estimated_minutes <= 0:
            return None

        is_timeout = actual_minutes > estimated_minutes * _TIMEOUT_THRESHOLD
        completion_rate = actual_minutes / estimated_minutes

        # 记录到用户超时历史
        await self._record_outcome(
            user_id=user_id,
            task_id=task_id,
            estimated=estimated_minutes,
            actual=actual_minutes,
            is_timeout=is_timeout,
            plan_id=plan_id,
        )

        if not is_timeout:
            return None

        # 检查连续超时次数
        consecutive = await self._get_consecutive_timeouts(user_id)
        logger.info(
            "task timeout detected: user={} task={} est={} act={} rate={:.1%} consecutive={}",
            user_id, task_id, estimated_minutes, actual_minutes, completion_rate, consecutive,
        )

        if consecutive < _CONSECUTIVE_TIMEOUTS_TRIGGER:
            return None

        # 达到阈值 → 生成 ActionableSignal
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[task_id],
            source_system="task_service",
            state_key=_SIGNAL_STATE_KEY,
            claim=_SIGNAL_CLAIM,
            confidence=min(0.5 + consecutive * 0.15, 0.95),
            scope=_SIGNAL_SCOPE,
            ttl_hours=_SIGNAL_TTL_HOURS,
            evidence_summary=(
                f"连续 {consecutive} 次任务实际耗时超过预估 {_TIMEOUT_THRESHOLD:.0%}"
                f"（最近一次：预估 {estimated_minutes} 分钟，实际 {actual_minutes} 分钟）"
            ),
            possible_effects=[
                "cap_task_duration",
                "avoid_new_chapter",
                "prefer_worked_example",
            ],
            priority="high",
        )
        logger.info("ActionableSignal generated: {}", signal.signal_id)
        return signal

    # ── Private helpers ───────────────────────────────────────────────

    async def _record_outcome(
        self,
        *,
        user_id: str,
        task_id: str,
        estimated: int,
        actual: int,
        is_timeout: bool,
        plan_id: str | None,
    ) -> None:
        key = _USER_TIMEOUT_HISTORY_KEY.format(user_id=user_id)
        entry = json.dumps({
            "task_id": task_id,
            "estimated": estimated,
            "actual": actual,
            "is_timeout": is_timeout,
            "plan_id": plan_id,
        })
        await self.redis.lpush(key, entry)
        await self.redis.ltrim(key, 0, _MAX_HISTORY - 1)
        await self.redis.expire(key, _SIGNAL_TTL_HOURS * 3600)

    async def _get_consecutive_timeouts(self, user_id: str) -> int:
        key = _USER_TIMEOUT_HISTORY_KEY.format(user_id=user_id)
        entries = await self.redis.lrange(key, 0, _MAX_HISTORY - 1)
        consecutive = 0
        for raw in entries:
            entry = json.loads(raw)
            if entry.get("is_timeout"):
                consecutive += 1
            else:
                break
        return consecutive
