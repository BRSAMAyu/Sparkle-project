"""
Core: execution
Phase: sense
Stage: Signal-to-Action Spine M2

Material Signal Detector — 检测用户上传的课件是否被 RAG 利用。
如果课件上传后连续 N 轮对话未被引用，产生 "material_underutilized" 信号。

用户可见变化：Aurora 会主动告知用户有课件可用并调整检索策略。
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.signals.types import ActionableSignal, _uid

_MATERIAL_SIGNAL_STATE_KEY = "material_utilization"
_UNUTILIZED_CLAIM = "material_underutilized"
_MATERIAL_HISTORY_KEY = "spine:material_history:{user_id}"
_MATERIAL_FILE_KEY = "spine:material_files:{user_id}"
_TURN_THRESHOLD = 3  # 连续 N 轮未引用课件后触发
_SIGNAL_TTL_HOURS = 48


class MaterialSignalDetector:
    """检测课件是否被充分利用。"""

    def __init__(self, redis_client: Any):
        self.redis = redis_client

    async def register_uploaded_file(
        self,
        *,
        user_id: str,
        file_id: str,
        filename: str,
        node_ids: list[str] | None = None,
    ) -> None:
        """记录用户上传的课件文件。"""
        key = _MATERIAL_FILE_KEY.format(user_id=user_id)
        entry = json.dumps({
            "file_id": file_id,
            "filename": filename,
            "node_ids": node_ids or [],
        })
        await self.redis.hset(key, file_id, entry)
        await self.redis.expire(key, 7 * 24 * 3600)  # 7 days

    async def on_turn_completed(
        self,
        *,
        user_id: str,
        context_receipt: dict[str, Any] | None = None,
    ) -> ActionableSignal | None:
        """
        每轮对话完成后检查课件利用情况。

        Args:
            context_receipt: 本轮 context_receipt（来自 orchestrator metadata）。
                包含 used_count, excluded_count, decision_reason 等。

        Returns:
            ActionableSignal if material is underutilized, None otherwise.
        """
        # 检查是否有已上传的课件
        files_key = _MATERIAL_FILE_KEY.format(user_id=user_id)
        files_raw = await self.redis.hgetall(files_key)
        if not files_raw:
            return None

        uploaded_files = []
        for raw_entry in files_raw.values():
            try:
                uploaded_files.append(json.loads(raw_entry))
            except (json.JSONDecodeError, TypeError):
                continue

        if not uploaded_files:
            return None

        # 检查本轮是否使用了课件
        used_count = 0
        if context_receipt:
            used_count = context_receipt.get("used_count", 0)

        # 记录本轮利用情况
        history_key = _MATERIAL_HISTORY_KEY.format(user_id=user_id)
        entry = json.dumps({"used_count": used_count, "had_receipt": context_receipt is not None})
        await self.redis.lpush(history_key, entry)
        await self.redis.ltrim(history_key, 0, _TURN_THRESHOLD + 2)
        await self.redis.expire(history_key, _SIGNAL_TTL_HOURS * 3600)

        # 如果本轮使用了课件，不触发
        if used_count > 0:
            return None

        # 检查连续未使用轮数
        consecutive_unused = await self._get_consecutive_unused(user_id)
        if consecutive_unused < _TURN_THRESHOLD:
            return None

        # 达到阈值 → 生成信号
        filenames = [f.get("filename", "?") for f in uploaded_files[:3]]
        signal = ActionableSignal(
            signal_id=_uid("sig"),
            source_event_ids=[f.get("file_id", "") for f in uploaded_files[:3]],
            source_system="material_signal",
            state_key=_MATERIAL_SIGNAL_STATE_KEY,
            claim=_UNUTILIZED_CLAIM,
            confidence=min(0.5 + consecutive_unused * 0.1, 0.85),
            scope="current_session",
            ttl_hours=_SIGNAL_TTL_HOURS,
            evidence_summary=(
                f"用户上传了 {len(uploaded_files)} 份课件（{', '.join(filenames)}），"
                f"但最近 {consecutive_unused} 轮对话均未引用。"
            ),
            possible_effects=[
                "prefer_targeted_source_rag",
                "suggest_material_review",
                "adjust_retrieval_mode",
            ],
            priority="medium",
        )
        logger.info("MaterialSignal: {}", signal.signal_id)
        return signal

    async def _get_consecutive_unused(self, user_id: str) -> int:
        key = _MATERIAL_HISTORY_KEY.format(user_id=user_id)
        entries = await self.redis.lrange(key, 0, _TURN_THRESHOLD + 1)
        consecutive = 0
        for raw in entries:
            try:
                entry = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if entry.get("used_count", 0) == 0 and entry.get("had_receipt"):
                consecutive += 1
            else:
                break
        return consecutive
