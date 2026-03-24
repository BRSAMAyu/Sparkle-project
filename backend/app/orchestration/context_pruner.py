"""
ContextPruner - 上下文修剪器

负责管理和优化 LLM 上下文窗口，防止 Token 爆炸和上下文溢出。

策略:
1. Sliding Window: 对短历史保留全部消息
2. Importance Compression: 中等长度历史使用规则压缩
3. Sync Summarization: 长历史使用 FAST 模型同步总结
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import redis.asyncio as redis
from loguru import logger


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
                    fallback_messages = self._compress_with_importance(history)
                    return {"messages": fallback_messages, "summary": None}

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
        high_priority_keywords = ["计划", "任务", "阶段", "里程碑", "目标", "记住", "注意", "修改", "变更"]
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
                    logger.warning(f"Failed to parse message: {msg}")
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
    **kwargs
) -> ContextPruner:
    global context_pruner_instance

    if context_pruner_instance is None:
        if redis_client is None:
            raise ValueError("Redis client is required for first initialization")
        context_pruner_instance = ContextPruner(redis_client, **kwargs)

    return context_pruner_instance
