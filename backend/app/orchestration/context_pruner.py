"""
ContextPruner - 上下文修剪器

负责管理和优化 LLM 上下文窗口，防止 Token 爆炸和上下文溢出。

策略:
1. Sliding Window: 只保留最近 N 轮对话
2. Summarization: 超过阈值时触发异步总结
3. Token Counting: 精确计算 token 数量（可选）
"""

import json
import time
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

import redis.asyncio as redis


class ContextPruner:
    """
    上下文修剪器 - 管理和优化 LLM 上下文窗口

    核心功能:
    - 从 Redis 加载聊天历史
    - 应用滑动窗口策略
    - 触发异步总结任务
    - 返回优化后的上下文
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        max_history_messages: int = 10,
        summary_threshold: int = 20,
        summary_cache_ttl: int = 3600
    ):
        """
        初始化 ContextPruner

        Args:
            redis_client: Redis 客户端实例
            max_history_messages: 滑动窗口保留的最大消息数
            summary_threshold: 触发总结的历史消息阈值
            summary_cache_ttl: 总结缓存的 TTL（秒）
        """
        self.redis = redis_client
        self.max_history_messages = max_history_messages
        self.summary_threshold = summary_threshold
        self.summary_cache_ttl = summary_cache_ttl

        logger.info(
            f"ContextPruner initialized: max_history={max_history_messages}, "
            f"summary_threshold={summary_threshold}, cache_ttl={summary_cache_ttl}"
        )

    async def get_pruned_history(
        self,
        session_id: str,
        user_id: str,
        force_summary: bool = False
    ) -> Dict[str, Any]:
        """
        获取修剪后的聊天历史

        策略:
        1. 历史 <= max_history: 直接返回全部
        2. max_history < 历史 <= summary_threshold: 滑动窗口
        3. 历史 > summary_threshold: 触发总结 + 滑动窗口

        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            force_summary: 强制触发总结（即使未达到阈值）

        Returns:
            {
                "messages": [...],  # 最近的消息（用于上下文）
                "summary": "前情提要...",  # 历史总结（如果有）
                "original_count": 50,  # 原始消息数
                "pruned_count": 10,  # 修剪后消息数
                "summary_used": True/False  # 是否使用了总结
            }
        """
        start_time = time.time()

        # 1. 从 Redis 加载历史
        history = await self._load_chat_history(session_id)

        if not history:
            logger.debug(f"No history found for session {session_id}")
            return {
                "messages": [],
                "summary": None,
                "original_count": 0,
                "pruned_count": 0,
                "summary_used": False
            }

        original_count = len(history)

        # 2. 如果历史记录很少，直接返回
        if original_count <= self.max_history_messages:
            logger.debug(
                f"Session {session_id}: {original_count} messages, "
                f"no pruning needed (took {time.time() - start_time:.3f}s)"
            )
            return {
                "messages": history,
                "summary": None,
                "original_count": original_count,
                "pruned_count": original_count,
                "summary_used": False
            }

        # 3. 检查是否需要总结
        need_summary = force_summary or original_count > self.summary_threshold

        if need_summary:
            summary_result = await self._get_summarized_history(
                session_id, history, user_id
            )

            logger.info(
                f"Session {session_id}: {original_count} messages -> "
                f"pruned to {len(summary_result['messages'])} + summary, "
                f"took {time.time() - start_time:.3f}s"
            )

            return {
                "messages": summary_result["messages"],
                "summary": summary_result["summary"],
                "original_count": original_count,
                "pruned_count": len(summary_result["messages"]),
                "summary_used": True
            }
        else:
            # 4. 使用滑动窗口
            pruned_messages = history[-self.max_history_messages:]

            logger.debug(
                f"Session {session_id}: {original_count} messages -> "
                f"sliding window to {len(pruned_messages)}, "
                f"took {time.time() - start_time:.3f}s"
            )

            return {
                "messages": pruned_messages,
                "summary": None,
                "original_count": original_count,
                "pruned_count": len(pruned_messages),
                "summary_used": False
            }

    async def _get_summarized_history(
        self,
        session_id: str,
        history: List[Dict],
        user_id: str
    ) -> Dict[str, Any]:
        """
        获取带总结的历史

        1. 检查缓存
        2. 如果缓存存在，返回缓存的总结 + 最近消息
        3. 如果缓存不存在，触发异步总结任务
        4. 返回最近消息作为 fallback
        """
        # 检查缓存
        cache_key = f"summary:{session_id}"
        cached_summary = await self.redis.get(cache_key)

        if cached_summary:
            logger.debug(f"Summary cache hit for session {session_id}")
            return {
                "messages": history[-5:],  # 保留最近5条
                "summary": cached_summary.decode("utf-8")
            }

        # 触发异步总结任务
        await self._trigger_summary(session_id, history, user_id)

        # 返回最近几条消息作为 fallback
        return {
            "messages": history[-5:],
            "summary": None
        }

    async def _trigger_summary(
        self,
        session_id: str,
        history: List[Dict],
        user_id: str
    ):
        """
        异步触发总结任务

        将总结任务推送到 Redis 队列，由后台 worker 处理
        """
        # 准备任务数据
        # 只总结除最近5条外的历史，保留最新上下文
        history_to_summarize = history[:-5] if len(history) > 5 else history

        task = {
            "session_id": session_id,
            "history": history_to_summarize,
            "user_id": user_id,
            "timestamp": time.time(),
            "priority": "high"
        }

        # 推送到队列
        queue_key = "queue:summarization"
        await self.redis.rpush(queue_key, json.dumps(task))

        logger.info(
            f"Triggered summarization task for session {session_id}, "
            f"history size: {len(history_to_summarize)}"
        )

    async def _load_chat_history(self, session_id: str) -> List[Dict]:
        """
        从 Redis 加载聊天历史

        期望的历史格式:
        {
            "role": "user" | "assistant",
            "content": "...",
            "timestamp": 1234567890
        }
        """
        cache_key = f"chat:history:{session_id}"

        try:
            # 获取所有消息
            messages = await self.redis.lrange(cache_key, 0, -1)

            # 解析 JSON
            history = []
            for msg in messages:
                try:
                    parsed = json.loads(msg)
                    # 确保有必要的字段
                    if "role" in parsed and "content" in parsed:
                        history.append(parsed)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {msg}")
                    continue

            return history

        except Exception as e:
            logger.error(f"Failed to load chat history for session {session_id}: {e}")
            return []

    async def get_summary_status(self, session_id: str) -> Dict[str, Any]:
        """
        获取总结状态（用于监控和调试）
        """
        cache_key = f"summary:{session_id}"
        exists = await self.redis.exists(cache_key)

        if exists:
            ttl = await self.redis.ttl(cache_key)
            summary = await self.redis.get(cache_key)
            return {
                "has_summary": True,
                "ttl_seconds": ttl,
                "summary_preview": summary.decode("utf-8")[:100] + "..." if summary else None
            }
        else:
            return {
                "has_summary": False,
                "ttl_seconds": 0,
                "summary_preview": None
            }

    async def clear_summary(self, session_id: str) -> bool:
        """
        清除会话的总结缓存（用于测试或重置）
        """
        cache_key = f"summary:{session_id}"
        result = await self.redis.delete(cache_key)
        logger.info(f"Cleared summary cache for session {session_id}")
        return result > 0


# 单例实例
context_pruner_instance = None


def get_context_pruner(
    redis_client: Optional[redis.Redis] = None,
    **kwargs
) -> ContextPruner:
    """
    获取 ContextPruner 单例实例

    Args:
        redis_client: Redis 客户端（如果未提供，需要在首次调用时设置）
        **kwargs: 传递给 ContextPruner 构造函数的其他参数

    Returns:
        ContextPruner 实例
    """
    global context_pruner_instance

    if context_pruner_instance is None:
        if redis_client is None:
            raise ValueError("Redis client is required for first initialization")
        context_pruner_instance = ContextPruner(redis_client, **kwargs)

    return context_pruner_instance
