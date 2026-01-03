"""
TokenTracker - Token 使用量追踪器

负责:
1. 记录每次请求的 Token 使用量
2. 实时配额检查
3. 生成使用统计和报表
4. 异步持久化到数据库
"""

import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from loguru import logger

import redis.asyncio as redis


class TokenTracker:
    """
    Token 使用量追踪器

    核心功能:
    - 实时记录 Token 使用
    - 每日配额管理
    - 使用统计查询
    - 异步记账队列
    """

    def __init__(self, redis_client: redis.Redis):
        """
        初始化 TokenTracker

        Args:
            redis_client: Redis 客户端实例
        """
        self.redis = redis_client
        logger.info("TokenTracker initialized")

    async def record_usage(
        self,
        user_id: str,
        session_id: str,
        request_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4",
        cost: Optional[float] = None
    ) -> int:
        """
        记录 Token 使用量

        Args:
            user_id: 用户 ID
            session_id: 会话 ID
            request_id: 请求 ID
            prompt_tokens: 输入 Token 数
            completion_tokens: 输出 Token 数
            model: 模型名称
            cost: 估算成本（可选）

        Returns:
            总 Token 数
        """
        total_tokens = prompt_tokens + completion_tokens
        timestamp = time.time()

        # 1. 记录到计费队列（异步持久化）
        usage_record = {
            "user_id": user_id,
            "session_id": session_id,
            "request_id": request_id,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model": model,
            "cost": cost,
            "timestamp": timestamp
        }

        await self.redis.rpush("queue:billing", json.dumps(usage_record))

        # 2. 更新用户当日累计
        today = datetime.now().strftime("%Y-%m-%d")
        daily_key = f"user:daily_tokens:{user_id}:{today}"
        await self.redis.incrby(daily_key, total_tokens)
        await self.redis.expire(daily_key, 86400)  # 24小时过期

        # 3. 更新会话累计
        session_key = f"session:tokens:{session_id}"
        await self.redis.incrby(session_key, total_tokens)

        # 4. 更新模型统计
        model_key = f"model:tokens:{model}:{today}"
        await self.redis.incrby(model_key, total_tokens)
        await self.redis.expire(model_key, 86400)

        # 5. 记录到历史明细（可选，用于详细分析）
        detail_key = f"user:details:{user_id}:{today}"
        detail = {
            "request_id": request_id,
            "session_id": session_id,
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens,
            "model": model,
            "timestamp": timestamp
        }
        await self.redis.rpush(detail_key, json.dumps(detail))
        await self.redis.expire(detail_key, 86400)  # 保留24小时

        logger.debug(
            f"Recorded usage for user {user_id}: "
            f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens"
        )

        return total_tokens

    async def get_daily_usage(self, user_id: str, date: Optional[str] = None) -> int:
        """
        获取用户某日的 Token 使用量

        Args:
            user_id: 用户 ID
            date: 日期 (YYYY-MM-DD)，默认为今天

        Returns:
            Token 使用量
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        key = f"user:daily_tokens:{user_id}:{date}"
        result = await self.redis.get(key)
        return int(result) if result else 0

    async def check_quota(
        self,
        user_id: str,
        daily_limit: int = 100000,
        date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检查用户配额

        Args:
            user_id: 用户 ID
            daily_limit: 每日配额限制
            date: 日期

        Returns:
            {
                "within_quota": bool,
                "used": int,
                "limit": int,
                "remaining": int,
                "usage_rate": float
            }
        """
        used = await self.get_daily_usage(user_id, date)
        remaining = daily_limit - used
        usage_rate = used / daily_limit if daily_limit > 0 else 0

        return {
            "within_quota": used < daily_limit,
            "used": used,
            "limit": daily_limit,
            "remaining": max(0, remaining),
            "usage_rate": usage_rate,
            "percentage": f"{usage_rate * 100:.1f}%"
        }

    async def get_usage_breakdown(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, int]:
        """
        获取用户最近 N 天的使用明细

        Args:
            user_id: 用户 ID
            days: 天数

        Returns:
            {date: tokens, ...}
        """
        breakdown = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            usage = await self.get_daily_usage(user_id, date)
            breakdown[date] = usage

        return breakdown

    async def get_session_usage(self, session_id: str) -> int:
        """
        获取会话累计 Token

        Args:
            session_id: 会话 ID

        Returns:
            Token 使用量
        """
        key = f"session:tokens:{session_id}"
        result = await self.redis.get(key)
        return int(result) if result else 0

    async def get_model_stats(
        self,
        model: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取模型使用统计

        Args:
            model: 模型名称
            days: 天数

        Returns:
            统计信息
        """
        breakdown = {}
        total = 0

        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            key = f"model:tokens:{model}:{date}"
            usage = await self.redis.get(key)
            tokens = int(usage) if usage else 0
            breakdown[date] = tokens
            total += tokens

        return {
            "model": model,
            "total_tokens": total,
            "daily_average": total / days if days > 0 else 0,
            "breakdown": breakdown
        }

    async def get_top_users(
        self,
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取 Token 使用量最高的用户

        Args:
            days: 统计天数
            limit: 返回数量

        Returns:
            [{user_id: ..., total_tokens: ...}, ...]
        """
        # 使用 Redis SCAN 查找所有用户
        pattern = "user:daily_tokens:*"
        user_totals = {}

        async for key in self.redis.scan_iter(match=pattern):
            # key 格式: user:daily_tokens:{user_id}:{date}
            parts = key.decode("utf-8").split(":")
            if len(parts) >= 4:
                user_id = parts[2]
                date = parts[3]

                # 只统计指定天数内的
                try:
                    key_date = datetime.strptime(date, "%Y-%m-%d")
                    days_ago = (datetime.now() - key_date).days

                    if 0 <= days_ago < days:
                        usage = await self.redis.get(key)
                        if usage:
                            user_totals[user_id] = user_totals.get(user_id, 0) + int(usage)
                except:
                    continue

        # 排序并返回 Top N
        sorted_users = sorted(
            user_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]

        return [
            {"user_id": uid, "total_tokens": tokens}
            for uid, tokens in sorted_users
        ]

    async def get_user_details(
        self,
        user_id: str,
        date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        获取用户详细使用记录

        Args:
            user_id: 用户 ID
            date: 日期
            limit: 返回记录数

        Returns:
            详细记录列表
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        key = f"user:details:{user_id}:{date}"
        messages = await self.redis.lrange(key, -limit, -1)

        details = []
        for msg in messages:
            try:
                detail = json.loads(msg)
                details.append(detail)
            except:
                continue

        return details

    async def get_total_stats(self) -> Dict[str, Any]:
        """
        获取系统整体统计

        Returns:
            系统统计信息
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # 总 Token 使用
        total_key = f"system:tokens:{today}"
        total = await self.redis.get(total_key) or 0

        # 模型分布
        gpt4_key = f"model:tokens:gpt-4:{today}"
        gpt4 = await self.redis.get(gpt4_key) or 0

        gpt35_key = f"model:tokens:gpt-3.5-turbo:{today}"
        gpt35 = await self.redis.get(gpt35_key) or 0

        # 活跃用户数
        active_users = 0
        async for key in self.redis.scan_iter(match="user:daily_tokens:*:today"):
            active_users += 1

        return {
            "date": today,
            "total_tokens": int(total),
            "model_distribution": {
                "gpt-4": int(gpt4),
                "gpt-3.5-turbo": int(gpt35)
            },
            "active_users": active_users
        }

    async def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-4"
    ) -> float:
        """
        估算成本（基于 OpenAI 定价）

        Args:
            prompt_tokens: 输入 Token
            completion_tokens: 输出 Token
            model: 模型

        Returns:
            估算成本（美元）
        """
        # OpenAI 定价（2024年）
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # per 1k tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
        }

        if model not in pricing:
            model = "gpt-4"

        p = pricing[model]
        cost = (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1000

        return round(cost, 6)


# 单例实例
_token_tracker_instance = None


def get_token_tracker(redis_client: Optional[redis.Redis] = None) -> TokenTracker:
    """
    获取 TokenTracker 单例

    Args:
        redis_client: Redis 客户端（首次调用时需要）

    Returns:
        TokenTracker 实例
    """
    global _token_tracker_instance

    if _token_tracker_instance is None:
        if redis_client is None:
            raise ValueError("Redis client required for first initialization")
        _token_tracker_instance = TokenTracker(redis_client)

    return _token_tracker_instance
