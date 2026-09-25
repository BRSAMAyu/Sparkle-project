"""
ContextPruner - 上下文修剪器

负责管理和优化 LLM 上下文窗口，防止 Token 爆炸和上下文溢出。

策略 (C-06 起默认路径零 LLM):
1. Sliding Window: 对短历史保留全部消息
2. Importance Compression: 中等长度历史使用规则压缩（关键类消息豁免截断）
3. Deterministic Compaction: 长历史确定性压缩（conversation_compaction.py，
   保序保留 correction/decision/unresolved/action_result/goal_state）；
   LLM 同步总结降级为可选档（ENABLE_LLM_SESSION_SUMMARY，默认关），
   开启后失败仍回落确定性压缩。
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.config import settings
from app.orchestration.conversation_compaction import (
    KEY_SALIENCE,
    classify_message,
    compact_history,
)


class ContextPruner:
    """
    上下文修剪器 - 管理和优化 LLM 上下文窗口

    三层策略:
    - 第 1 层: <= max_history_messages，完整保留
    - 第 2 层: <= importance_threshold，规则压缩
    - 第 3 层: > importance_threshold，同步总结 + 锚点保留
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_history_messages: int = 10,
        summary_threshold: int = 20,
        summary_cache_ttl: int = 3600
    ):
        self.redis = redis_client
        self.max_history_messages = max_history_messages
        self.summary_threshold = summary_threshold
        self.summary_cache_ttl = summary_cache_ttl
        self.importance_threshold = max(summary_threshold, 30)
        self.importance_recent_window = 6
        self.summary_recent_window = 4

        logger.info(
            f"ContextPruner initialized: max_history={max_history_messages}, "
            f"summary_threshold={summary_threshold}, cache_ttl={summary_cache_ttl}"
        )

    async def get_pruned_history(
        self,
        session_id: str,
        user_id: str,
        force_summary: bool = False
    ) -> dict[str, Any]:
        start_time = time.time()
        history = await self._load_chat_history(session_id)

        if not history:
            logger.debug(f"No history found for session {session_id}")
            return {
                "messages": [],
                "summary": None,
                "original_count": 0,
                "pruned_count": 0,
                "summary_used": False,
            }

        original_count = len(history)
        if original_count <= self.max_history_messages:
            return {
                "messages": history,
                "summary": None,
                "original_count": original_count,
                "pruned_count": original_count,
                "summary_used": False,
            }

        if not force_summary and original_count <= self.importance_threshold:
            messages = self._compress_with_importance(history)
            logger.debug(
                f"Session {session_id}: tier2 compression {original_count} -> {len(messages)} "
                f"(took {time.time() - start_time:.3f}s)"
            )
            return {
                "messages": messages,
                "summary": None,
                "original_count": original_count,
                "pruned_count": len(messages),
                "summary_used": False,
            }

        # C-06：默认路径 = 确定性 compaction（零 LLM、保序保关键类）。
        # LLM 同步总结仅在 ENABLE_LLM_SESSION_SUMMARY（或显式 force_summary）
        # 时作为可选档回归；其失败/空摘要回落不再是二层截断，而是确定性
        # compaction（RB-07 语义升级：中间消息仍不静默丢）。
        llm_summary_enabled = bool(
            getattr(settings, "ENABLE_LLM_SESSION_SUMMARY", False) or force_summary
        )
        if not getattr(settings, "ENABLE_DETERMINISTIC_COMPACTION", True) and not llm_summary_enabled:
            # 确定性压缩被关且 LLM 档未开：维持历史行为（二层压缩）作兜底。
            messages = self._compress_with_importance(history)
            logger.debug(
                f"Session {session_id}: tier2 fallback compression {original_count} -> {len(messages)} "
                f"(took {time.time() - start_time:.3f}s)"
            )
            return {
                "messages": messages,
                "summary": None,
                "original_count": original_count,
                "pruned_count": len(messages),
                "summary_used": False,
            }
        if not llm_summary_enabled:
            compaction = compact_history(
                history,
                recent_window=int(getattr(settings, "COMPACTION_RECENT_WINDOW", 6) or 6),
                key_message_cap_tokens=int(
                    getattr(settings, "COMPACTION_KEY_MESSAGE_CAP_TOKENS", 220) or 220
                ),
            )
            logger.info(
                f"Session {session_id}: tier3 deterministic compaction {original_count} -> "
                f"{compaction.pruned_count} (compressed_ordinary={compaction.metadata.get('compressed_ordinary')} "
                f"key_preserved={len(compaction.metadata.get('key_preserved', []))} "
                f"dropped_key={len(compaction.metadata.get('dropped_key', []))}, "
                f"took {time.time() - start_time:.3f}s)"
            )
            return compaction.to_pruner_payload()

        summary_result = await self._get_summarized_history(session_id, history, user_id)
        logger.info(
            f"Session {session_id}: tier3 compression {original_count} -> "
            f"{len(summary_result['messages'])} + summary, "
            f"took {time.time() - start_time:.3f}s"
        )
        return {
            "messages": summary_result["messages"],
            "summary": summary_result["summary"],
            "original_count": original_count,
            "pruned_count": len(summary_result["messages"]),
            "summary_used": bool(summary_result["summary"]),
        }

    async def _get_summarized_history(
        self,
        session_id: str,
        history: list[dict],
        user_id: str,
    ) -> dict[str, Any]:
        del user_id  # 保留参数位，后续可用于个性化总结

        recent_messages = history[-self.summary_recent_window :]
        earlier_messages = history[:-self.summary_recent_window]
        anchor_messages = [msg for msg in earlier_messages if self._is_anchor_message(msg)]
        summary_messages = [msg for msg in earlier_messages if msg not in anchor_messages]

        summary = None
        if summary_messages:
            cache_key = self._summary_cache_key(session_id, summary_messages)
            cached_summary = await self.redis.get(cache_key)
            if cached_summary:
                summary = self._decode_redis_value(cached_summary)
                logger.debug(f"Summary cache hit for session {session_id}")
            else:
                try:
                    summary = await self._summarize_sync(summary_messages)
                    if summary:
                        await self.redis.setex(cache_key, self.summary_cache_ttl, summary)
                        await self.redis.setex(
                            f"summary:{session_id}:latest",
                            self.summary_cache_ttl,
                            json.dumps({"cache_key": cache_key, "summary": summary}, ensure_ascii=False),
                        )
                except Exception as exc:
                    logger.warning(f"Sync summarization failed for session {session_id}: {exc}")
                    # C-06：LLM 档失败回落确定性 compaction（关键类不丢），
                    # 二层截断只是最后兜底。
                    if getattr(settings, "ENABLE_DETERMINISTIC_COMPACTION", True):
                        compaction = compact_history(
                            history,
                            recent_window=int(getattr(settings, "COMPACTION_RECENT_WINDOW", 6) or 6),
                            key_message_cap_tokens=int(
                                getattr(settings, "COMPACTION_KEY_MESSAGE_CAP_TOKENS", 220) or 220
                            ),
                        )
                        return {"messages": compaction.messages, "summary": compaction.summary}
                    fallback_messages = self._compress_with_importance(history)
                    return {"messages": fallback_messages, "summary": None}

        if summary_messages and not str(summary or "").strip():
            # RB-07: 空摘要（FAST 模型空响应/拒答）视为总结失败，退回压缩，
            # 避免 anchor/recent 之外的中间消息被静默丢弃。C-06：优先确定性
            # compaction（correction/decision/unresolved/action results 保序
            # 保留），二层截断仅作开关关闭时的兜底。
            logger.warning(f"Empty sync summary for session {session_id}; falling back to compression")
            if getattr(settings, "ENABLE_DETERMINISTIC_COMPACTION", True):
                compaction = compact_history(
                    history,
                    recent_window=int(getattr(settings, "COMPACTION_RECENT_WINDOW", 6) or 6),
                    key_message_cap_tokens=int(
                        getattr(settings, "COMPACTION_KEY_MESSAGE_CAP_TOKENS", 220) or 220
                    ),
                )
                return {"messages": compaction.messages, "summary": compaction.summary}
            return {"messages": self._compress_with_importance(history), "summary": None}

        messages = self._dedupe_messages(anchor_messages + recent_messages)
        return {"messages": messages, "summary": summary}

    async def _summarize_sync(self, messages: list[dict[str, Any]]) -> str:
        """用 FAST 模型同步总结，优先保障首次进入长上下文时的信息完整性。"""
        if not messages:
            return ""

        from app.core.agent_profiles import AgentRole, ModelTier, TaskType
        from app.services.llm_service import get_configured_llm_service_for_tier

        summarizer = await get_configured_llm_service_for_tier(
            AgentRole.RETRIEVAL,
            ModelTier.FAST,
            task_type=TaskType.ROUTING,
        )

        prompt = (
            "用中文简洁总结以下对话的关键信息（100字以内）。\n"
            "要求：1. 用户核心目标 2. 已完成事项 3. 当前阶段 4. 关键决策。\n\n"
            f"{self._format_messages_for_summary(messages)}"
        )
        result = await summarizer.chat(
            messages=[
                {"role": "system", "content": "你是对话总结助手。只输出总结，不加前缀。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return str(result or "").strip()

    def _compress_with_importance(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        recent_messages = history[-self.importance_recent_window :]
        earlier_messages = history[:-self.importance_recent_window]

        compressed: list[dict[str, Any]] = []
        for message in earlier_messages:
            if self._is_high_importance_message(message):
                compressed.append(message)
            else:
                compressed.append(self._compress_message(message))

        return compressed + recent_messages

    def _compress_message(self, message: dict[str, Any]) -> dict[str, Any]:
        compressed = dict(message)
        content = str(message.get("content") or "").strip()
        role = str(message.get("role") or "assistant")

        # C-06：关键类（correction/decision/unresolved/action_result/
        # goal_state）豁免 150 字符硬截断——基线 B1：纠错的操作性尾部
        # （"请以这次说的为准…"）在关键词未命中时被截掉。长关键消息只做
        # 头部预算截断（COMPACTION_KEY_MESSAGE_CAP_TOKENS，默认 220 token），
        # 并保留显式标记；普通消息维持原二层行为。
        if classify_message(message) in KEY_SALIENCE:
            cap_tokens = int(getattr(settings, "COMPACTION_KEY_MESSAGE_CAP_TOKENS", 220) or 220)
            if cap_tokens > 0 and len(content) > 150:
                from app.orchestration.conversation_compaction import _truncate_content

                compressed["content"] = _truncate_content(content, cap_tokens)
                compressed["compacted_truncated"] = compressed["content"] != content
            compressed["salience"] = classify_message(message)
            return compressed

        if self._is_low_signal_message(message):
            compressed["content"] = f"[{role}简述] {self._summarize_low_signal(content)}"
        elif len(content) > 150:
            compressed["content"] = content[:150].rstrip() + "..."
        else:
            compressed["content"] = content

        compressed["compressed"] = True
        return compressed

    def _summarize_low_signal(self, content: str) -> str:
        stripped = str(content or "").strip()
        if not stripped:
            return "简短确认。"
        return stripped[:40].rstrip() + ("..." if len(stripped) > 40 else "")

    def _is_low_signal_message(self, message: dict[str, Any]) -> bool:
        content = str(message.get("content") or "").strip().lower()
        if not content:
            return True
        low_signal_values = {
            "好的", "好", "嗯", "嗯嗯", "收到", "明白", "ok", "okay", "谢谢", "好的，谢谢",
            "可以", "行", "继续", "继续吧",
        }
        return content in low_signal_values or len(content) <= 12

    def _is_high_importance_message(self, message: dict[str, Any]) -> bool:
        if message.get("tool_calls") or message.get("tool_results"):
            return True
        content = str(message.get("content") or "")
        high_priority_keywords = [
            "计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更",
            "焦虑", "压力", "紧张", "担心", "害怕", "崩溃", "烦躁", "失落",
            "开心", "高兴", "激动", "兴奋", "成就感",
            "卡住", "不理解", "不懂", "迷茫", "困惑",
            "想放弃", "放弃", "坚持", "动力",
        ]
        return any(keyword in content for keyword in high_priority_keywords)

    def _is_anchor_message(self, message: dict[str, Any]) -> bool:
        if message.get("tool_calls") or message.get("tool_results"):
            return True
        content = str(message.get("content") or "")
        anchor_keywords = ["计划已创建", "任务完成", "阶段", "里程碑", "目标确认", "关键决策", "修改计划"]
        return any(keyword in content for keyword in anchor_keywords) or self._is_high_importance_message(message)

    def _format_messages_for_summary(self, messages: list[dict[str, Any]]) -> str:
        formatted: list[str] = []
        for message in messages:
            role = "用户" if message.get("role") == "user" else "助手"
            content = str(message.get("content") or "").strip()
            if len(content) > 200:
                content = content[:200].rstrip() + "..."
            formatted.append(f"{role}: {content}")
        return "\n".join(formatted)

    def _summary_cache_key(self, session_id: str, messages: list[dict[str, Any]]) -> str:
        digest = hashlib.sha1(
            json.dumps(messages, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        return f"summary:{session_id}:{digest}"

    def _dedupe_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for message in messages:
            marker = json.dumps(
                {
                    "role": message.get("role"),
                    "content": message.get("content"),
                    "timestamp": message.get("timestamp"),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
            if marker in seen:
                continue
            seen.add(marker)
            deduped.append(message)
        return deduped

    @staticmethod
    def _decode_redis_value(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)

    async def _load_chat_history(self, session_id: str) -> list[dict]:
        cache_key = f"chat:history:{session_id}"
        try:
            messages = await self.redis.lrange(cache_key, 0, -1)
            history = []
            for msg in messages:
                try:
                    parsed = json.loads(msg)
                    if "role" in parsed and "content" in parsed:
                        history.append(parsed)
                except json.JSONDecodeError:
                    # Q-05 红队修复（P1）：损坏行可能含用户正文，告警不得回显原文
                    logger.warning(
                        f"Failed to parse cached chat history entry for session {session_id}; "
                        f"skipped malformed entry ({len(msg)} chars)"
                    )
            return history
        except Exception as e:
            logger.error(f"Failed to load chat history for session {session_id}: {e}")
            return []

    async def get_summary_status(self, session_id: str) -> dict[str, Any]:
        latest_key = f"summary:{session_id}:latest"
        latest = await self.redis.get(latest_key)
        if not latest:
            return {
                "has_summary": False,
                "ttl_seconds": 0,
                "summary_preview": None,
            }

        ttl = await self.redis.ttl(latest_key)
        payload = json.loads(self._decode_redis_value(latest))
        summary = str(payload.get("summary") or "")
        return {
            "has_summary": True,
            "ttl_seconds": ttl,
            "summary_preview": summary[:100] + "..." if len(summary) > 100 else summary,
        }

    async def clear_summary(self, session_id: str) -> bool:
        deleted = 0
        async for key in self.redis.scan_iter(match=f"summary:{session_id}:*"):
            deleted += await self.redis.delete(key)
        logger.info(f"Cleared summary cache for session {session_id}")
        return deleted > 0


context_pruner_instance = None


def get_context_pruner(
    redis_client: redis.Redis | None = None,
    **kwargs,
) -> ContextPruner:
    global context_pruner_instance

    if context_pruner_instance is None:
        if redis_client is None:
            raise ValueError("Redis client is required for first initialization")
        context_pruner_instance = ContextPruner(redis_client, **kwargs)
    elif redis_client is not None and context_pruner_instance.redis is not redis_client:
        # Re-initialize with new Redis client on reconnection
        context_pruner_instance.redis = redis_client

    return context_pruner_instance
