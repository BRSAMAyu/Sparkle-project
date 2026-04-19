"""
TokenTracker - Token 使用量追踪器

负责:
1. 记录每次请求的 Token 使用量
2. 实时配额检查
3. 生成使用统计和报表
4. 异步持久化到数据库
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.core.llm_router import llm_router


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
        cost: float | None = None,
        reasoning_mode: str | None = None,
        model_tier: str | None = None,
        chat_mode: str | None = None,
        timing_stats: dict[str, Any] | None = None,
        success: bool = True,
        fallback_used: bool = False,
        outcome_stats: dict[str, Any] | None = None,
        utilization_metrics: dict[str, Any] | None = None,
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
            "reasoning_mode": reasoning_mode or "balanced",
            "model_tier": model_tier or "",
            "chat_mode": chat_mode or "standard",
            "timing_stats": timing_stats or {},
            "success": bool(success),
            "fallback_used": bool(fallback_used),
            "outcome_stats": outcome_stats or {},
            "utilization_metrics": utilization_metrics or {},
            "timestamp": timestamp,
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

        mode = self._normalize_mode(reasoning_mode)
        mode_tokens_key = f"user:daily_ai_mode_tokens:{user_id}:{today}:{mode}"
        await self.redis.incrby(mode_tokens_key, total_tokens)
        await self.redis.expire(mode_tokens_key, 86400)

        mode_requests_key = f"user:daily_ai_mode_requests:{user_id}:{today}:{mode}"
        await self.redis.incr(mode_requests_key)
        await self.redis.expire(mode_requests_key, 86400)

        if cost is not None:
            mode_cost_key = f"user:daily_ai_mode_cost_micro_usd:{user_id}:{today}:{mode}"
            await self.redis.incrby(mode_cost_key, int(round(float(cost) * 1_000_000)))
            await self.redis.expire(mode_cost_key, 86400)

        if timing_stats:
            total_duration_ms = self._safe_int(timing_stats.get("total_duration_ms"))
            first_token_ms = self._safe_int(timing_stats.get("first_token_ms"))
            stream_duration_ms = self._safe_int(timing_stats.get("stream_duration_ms"))

            await self._record_timing_metric(
                key=f"user:daily_ai_mode_total_duration_ms:{user_id}:{today}:{mode}",
                value=total_duration_ms,
            )
            await self._record_timing_metric(
                key=f"user:daily_ai_mode_first_token_ms:{user_id}:{today}:{mode}",
                value=first_token_ms,
            )
            await self._record_timing_metric(
                key=f"user:daily_ai_mode_stream_duration_ms:{user_id}:{today}:{mode}",
                value=stream_duration_ms,
            )

            aggregate_key = f"ai:daily_timing:{today}:{mode}:{chat_mode or 'standard'}"
            await self.redis.hincrby(aggregate_key, "requests", 1)
            if total_duration_ms > 0:
                await self.redis.hincrby(aggregate_key, "total_duration_ms_sum", total_duration_ms)
            if first_token_ms > 0:
                await self.redis.hincrby(aggregate_key, "first_token_ms_sum", first_token_ms)
            if stream_duration_ms > 0:
                await self.redis.hincrby(aggregate_key, "stream_duration_ms_sum", stream_duration_ms)
            await self.redis.expire(aggregate_key, 86400 * 14)

        ops_key = f"user:ai_ops:{user_id}:{today}:{mode}:{chat_mode or 'standard'}"
        await self.redis.hincrby(ops_key, "requests_total", 1)
        await self.redis.hincrby(ops_key, "requests_success", 1 if success else 0)
        await self.redis.hincrby(ops_key, "requests_failed", 0 if success else 1)
        if fallback_used:
            await self.redis.hincrby(ops_key, "fallback_count", 1)
        await self.redis.hincrby(ops_key, "total_tokens_sum", total_tokens)
        if cost is not None:
            await self.redis.hincrby(ops_key, "total_cost_micro_usd", int(round(float(cost) * 1_000_000)))
        if timing_stats:
            if total_duration_ms > 0:
                await self.redis.hincrby(ops_key, "total_duration_ms_sum", total_duration_ms)
            if first_token_ms > 0:
                await self.redis.hincrby(ops_key, "first_token_ms_sum", first_token_ms)
            if stream_duration_ms > 0:
                await self.redis.hincrby(ops_key, "stream_duration_ms_sum", stream_duration_ms)
        outcome_stats = outcome_stats or {}
        task_count = self._safe_int(outcome_stats.get("task_count"))
        plan_count = self._safe_int(outcome_stats.get("plan_count"))
        execution_count = self._safe_int(outcome_stats.get("execution_count"))
        if task_count > 0:
            await self.redis.hincrby(ops_key, "task_count_sum", task_count)
            await self.redis.hincrby(ops_key, "task_request_count", 1)
        if plan_count > 0:
            await self.redis.hincrby(ops_key, "plan_count_sum", plan_count)
            await self.redis.hincrby(ops_key, "plan_request_count", 1)
        if execution_count > 0:
            await self.redis.hincrby(ops_key, "execution_count_sum", execution_count)
            await self.redis.hincrby(ops_key, "execution_request_count", 1)
        for metric_name in ("prompt_utilization", "inference_utilization"):
            metric_payload = (utilization_metrics or {}).get(metric_name)
            if isinstance(metric_payload, dict):
                await self._record_utilization_metric(
                    key=ops_key,
                    metric_name=metric_name,
                    metric_payload=metric_payload,
                )
        await self.redis.expire(ops_key, 86400 * 30)

        # 5. 记录到历史明细（可选，用于详细分析）
        detail_key = f"user:details:{user_id}:{today}"
        detail = {
            "request_id": request_id,
            "session_id": session_id,
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": total_tokens,
            "model": model,
            "model_tier": model_tier,
            "reasoning_mode": mode,
            "chat_mode": chat_mode or "standard",
            "timing_stats": timing_stats or {},
            "success": bool(success),
            "fallback_used": bool(fallback_used),
            "outcome_stats": outcome_stats or {},
            "utilization_metrics": utilization_metrics or {},
            "timestamp": timestamp,
        }
        await self.redis.rpush(detail_key, json.dumps(detail))
        await self.redis.expire(detail_key, 86400)  # 保留24小时

        logger.debug(
            f"Recorded usage for user {user_id}: " f"{prompt_tokens} + {completion_tokens} = {total_tokens} tokens"
        )

        return total_tokens

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return max(0, int(float(value)))
        except (TypeError, ValueError):
            return 0

    async def _record_timing_metric(self, *, key: str, value: int) -> None:
        if value <= 0:
            return
        await self.redis.incrby(key, value)
        await self.redis.expire(key, 86400 * 14)

    async def _record_utilization_metric(
        self,
        *,
        key: str,
        metric_name: str,
        metric_payload: dict[str, Any],
    ) -> None:
        status = str(metric_payload.get("status") or "unknown").strip().lower()
        numerator = self._safe_int(metric_payload.get("numerator"))
        denominator = self._safe_int(metric_payload.get("denominator"))
        ratio_value = metric_payload.get("ratio")
        ratio_basis_points = 0
        if ratio_value is not None:
            try:
                ratio_basis_points = max(0, int(round(float(ratio_value) * 10_000)))
            except (TypeError, ValueError):
                ratio_basis_points = 0

        await self.redis.hincrby(key, f"{metric_name}_numerator_sum", numerator)
        await self.redis.hincrby(key, f"{metric_name}_denominator_sum", denominator)
        if status == "known" and denominator > 0:
            await self.redis.hincrby(key, f"{metric_name}_known_count", 1)
            await self.redis.hincrby(key, f"{metric_name}_ratio_basis_points_sum", ratio_basis_points)
        elif status == "not_applicable":
            await self.redis.hincrby(key, f"{metric_name}_not_applicable_count", 1)
        else:
            await self.redis.hincrby(key, f"{metric_name}_unknown_count", 1)

    @staticmethod
    def _normalize_mode(value: str | None) -> str:
        normalized = str(value or "balanced").strip().lower()
        if normalized in {"fast", "balanced", "deep"}:
            return normalized
        return "balanced"

    async def get_daily_usage(self, user_id: str, date: str | None = None) -> int:
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
        if not result:
            return 0
        try:
            return int(result)
        except (TypeError, ValueError):
            return 0

    async def check_quota(self, user_id: str, daily_limit: int = 100000, date: str | None = None) -> dict[str, Any]:
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
            "percentage": f"{usage_rate * 100:.1f}%",
        }

    async def get_usage_breakdown(self, user_id: str, days: int = 7) -> dict[str, int]:
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

    async def get_model_stats(self, model: str, days: int = 7) -> dict[str, Any]:
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
            "breakdown": breakdown,
        }

    async def get_top_users(self, days: int = 7, limit: int = 10) -> list[dict[str, Any]]:
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
                except (TypeError, ValueError):
                    continue

        # 排序并返回 Top N
        sorted_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [{"user_id": uid, "total_tokens": tokens} for uid, tokens in sorted_users]

    async def get_user_details(self, user_id: str, date: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
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
            except (json.JSONDecodeError, TypeError):
                continue

        return details

    async def get_total_stats(self) -> dict[str, Any]:
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
        async for _key in self.redis.scan_iter(match="user:daily_tokens:*:today"):
            active_users += 1

        return {
            "date": today,
            "total_tokens": int(total),
            "model_distribution": {"gpt-4": int(gpt4), "gpt-3.5-turbo": int(gpt35)},
            "active_users": active_users,
        }

    async def estimate_cost(self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4") -> float:
        """
        估算成本（基于 OpenAI 定价）

        Args:
            prompt_tokens: 输入 Token
            completion_tokens: 输出 Token
            model: 模型

        Returns:
            估算成本（美元）
        """
        router_models = getattr(llm_router, "_available_models", {})
        if model in router_models:
            config = router_models[model]
            cost = (prompt_tokens + completion_tokens) * float(getattr(config, "cost_per_1k_tokens", 0.0)) / 1000.0
            return round(cost, 6)

        # Legacy OpenAI 定价兜底
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # per 1k tokens
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
        }

        if model not in pricing:
            model = "gpt-4"

        p = pricing[model]
        cost = (prompt_tokens * p["input"] + completion_tokens * p["output"]) / 1000

        return round(cost, 6)

    async def get_mode_usage_summary(
        self,
        user_id: str,
        mode: str,
        *,
        date: str | None = None,
        request_limit: int = 0,
    ) -> dict[str, Any]:
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        normalized_mode = self._normalize_mode(mode)

        (
            requests_raw,
            tokens_raw,
            cost_raw,
            total_duration_raw,
            first_token_raw,
            stream_duration_raw,
        ) = await self.redis.mget(
            f"user:daily_ai_mode_requests:{user_id}:{date}:{normalized_mode}",
            f"user:daily_ai_mode_tokens:{user_id}:{date}:{normalized_mode}",
            f"user:daily_ai_mode_cost_micro_usd:{user_id}:{date}:{normalized_mode}",
            f"user:daily_ai_mode_total_duration_ms:{user_id}:{date}:{normalized_mode}",
            f"user:daily_ai_mode_first_token_ms:{user_id}:{date}:{normalized_mode}",
            f"user:daily_ai_mode_stream_duration_ms:{user_id}:{date}:{normalized_mode}",
        )
        requests_used = int(requests_raw or 0)
        total_tokens = int(tokens_raw or 0)
        total_cost_usd = round(int(cost_raw or 0) / 1_000_000.0, 6)
        total_duration_ms = int(total_duration_raw or 0)
        total_first_token_ms = int(first_token_raw or 0)
        total_stream_duration_ms = int(stream_duration_raw or 0)
        remaining = max(0, request_limit - requests_used) if request_limit > 0 else 0
        avg_total_duration_ms = round(total_duration_ms / requests_used, 2) if requests_used > 0 else 0.0
        avg_first_token_ms = round(total_first_token_ms / requests_used, 2) if requests_used > 0 else 0.0
        avg_stream_duration_ms = round(total_stream_duration_ms / requests_used, 2) if requests_used > 0 else 0.0

        return {
            "mode": normalized_mode,
            "label": {"fast": "敏捷", "balanced": "均衡", "deep": "深思"}[normalized_mode],
            "requests_used": requests_used,
            "requests_limit": request_limit,
            "requests_remaining": remaining,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost_usd,
            "total_duration_ms": total_duration_ms,
            "avg_total_duration_ms": avg_total_duration_ms,
            "avg_first_token_ms": avg_first_token_ms,
            "avg_stream_duration_ms": avg_stream_duration_ms,
        }

    async def get_ai_usage_summary(
        self,
        user_id: str,
        *,
        mode_limits: dict[str, int],
        date: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            await self.get_mode_usage_summary(
                user_id,
                mode,
                date=date,
                request_limit=int(limit),
            )
            for mode, limit in mode_limits.items()
        ]

    async def get_chat_mode_timing_summary(
        self,
        *,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            pattern = f"ai:daily_timing:{date}:*"
            async for key in self.redis.scan_iter(pattern):
                decoded_key = key.decode() if isinstance(key, bytes) else str(key)
                parts = decoded_key.split(":")
                if len(parts) < 5:
                    continue
                _, _, key_date, mode, chat_mode = parts[:5]
                raw = await self.redis.hgetall(decoded_key)
                if not raw:
                    continue
                requests = int(raw.get("requests") or 0)
                total_duration = int(raw.get("total_duration_ms_sum") or 0)
                first_token = int(raw.get("first_token_ms_sum") or 0)
                stream_duration = int(raw.get("stream_duration_ms_sum") or 0)
                summaries.append(
                    {
                        "date": key_date,
                        "mode": mode,
                        "chat_mode": chat_mode,
                        "requests": requests,
                        "avg_total_duration_ms": round(total_duration / requests, 2)
                        if requests > 0
                        else 0.0,
                        "avg_first_token_ms": round(first_token / requests, 2)
                        if requests > 0
                        else 0.0,
                        "avg_stream_duration_ms": round(stream_duration / requests, 2)
                        if requests > 0
                        else 0.0,
                    }
                )
        summaries.sort(
            key=lambda item: (
                item["date"],
                item["mode"],
                item["chat_mode"],
            ),
            reverse=True,
        )
        return summaries

    async def get_ai_ops_summary(
        self,
        user_id: str,
        *,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        buckets: dict[str, dict[str, Any]] = {}
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            pattern = f"user:ai_ops:{user_id}:{date}:*"
            async for key in self.redis.scan_iter(match=pattern):
                decoded_key = key.decode() if isinstance(key, bytes) else str(key)
                parts = decoded_key.split(":")
                if len(parts) < 6:
                    continue
                reasoning_mode = parts[4]
                chat_mode = parts[5]
                raw = await self.redis.hgetall(decoded_key)
                if not raw:
                    continue
                bucket = buckets.setdefault(
                    chat_mode,
                    {
                        "chat_mode": chat_mode,
                        "requests_total": 0,
                        "requests_success": 0,
                        "requests_failed": 0,
                        "fallback_count": 0,
                        "total_tokens": 0,
                        "total_cost_usd": 0.0,
                        "total_duration_ms": 0,
                        "first_token_ms_sum": 0,
                        "stream_duration_ms_sum": 0,
                        "task_count": 0,
                        "plan_count": 0,
                        "execution_count": 0,
                        "task_request_count": 0,
                        "plan_request_count": 0,
                        "execution_request_count": 0,
                        "prompt_utilization_known_count": 0,
                        "prompt_utilization_unknown_count": 0,
                        "prompt_utilization_not_applicable_count": 0,
                        "prompt_utilization_ratio_basis_points_sum": 0,
                        "prompt_utilization_numerator_sum": 0,
                        "prompt_utilization_denominator_sum": 0,
                        "inference_utilization_known_count": 0,
                        "inference_utilization_unknown_count": 0,
                        "inference_utilization_not_applicable_count": 0,
                        "inference_utilization_ratio_basis_points_sum": 0,
                        "inference_utilization_numerator_sum": 0,
                        "inference_utilization_denominator_sum": 0,
                        "reasoning_mode_breakdown": {},
                    },
                )
                requests_total = int(raw.get("requests_total") or 0)
                requests_success = int(raw.get("requests_success") or 0)
                requests_failed = int(raw.get("requests_failed") or 0)
                fallback_count = int(raw.get("fallback_count") or 0)
                total_tokens = int(raw.get("total_tokens_sum") or 0)
                total_cost_micro = int(raw.get("total_cost_micro_usd") or 0)
                total_duration_ms = int(raw.get("total_duration_ms_sum") or 0)
                first_token_ms = int(raw.get("first_token_ms_sum") or 0)
                stream_duration_ms = int(raw.get("stream_duration_ms_sum") or 0)
                task_count = int(raw.get("task_count_sum") or 0)
                plan_count = int(raw.get("plan_count_sum") or 0)
                execution_count = int(raw.get("execution_count_sum") or 0)
                task_request_count = int(raw.get("task_request_count") or 0)
                plan_request_count = int(raw.get("plan_request_count") or 0)
                execution_request_count = int(raw.get("execution_request_count") or 0)
                prompt_known_count = int(raw.get("prompt_utilization_known_count") or 0)
                prompt_unknown_count = int(raw.get("prompt_utilization_unknown_count") or 0)
                prompt_not_applicable_count = int(raw.get("prompt_utilization_not_applicable_count") or 0)
                prompt_ratio_basis_points_sum = int(raw.get("prompt_utilization_ratio_basis_points_sum") or 0)
                prompt_numerator_sum = int(raw.get("prompt_utilization_numerator_sum") or 0)
                prompt_denominator_sum = int(raw.get("prompt_utilization_denominator_sum") or 0)
                inference_known_count = int(raw.get("inference_utilization_known_count") or 0)
                inference_unknown_count = int(raw.get("inference_utilization_unknown_count") or 0)
                inference_not_applicable_count = int(raw.get("inference_utilization_not_applicable_count") or 0)
                inference_ratio_basis_points_sum = int(raw.get("inference_utilization_ratio_basis_points_sum") or 0)
                inference_numerator_sum = int(raw.get("inference_utilization_numerator_sum") or 0)
                inference_denominator_sum = int(raw.get("inference_utilization_denominator_sum") or 0)
                bucket["requests_total"] += requests_total
                bucket["requests_success"] += requests_success
                bucket["requests_failed"] += requests_failed
                bucket["fallback_count"] += fallback_count
                bucket["total_tokens"] += total_tokens
                bucket["total_cost_usd"] += total_cost_micro / 1_000_000.0
                bucket["total_duration_ms"] += total_duration_ms
                bucket["first_token_ms_sum"] += first_token_ms
                bucket["stream_duration_ms_sum"] += stream_duration_ms
                bucket["task_count"] += task_count
                bucket["plan_count"] += plan_count
                bucket["execution_count"] += execution_count
                bucket["task_request_count"] += task_request_count
                bucket["plan_request_count"] += plan_request_count
                bucket["execution_request_count"] += execution_request_count
                bucket["prompt_utilization_known_count"] += prompt_known_count
                bucket["prompt_utilization_unknown_count"] += prompt_unknown_count
                bucket["prompt_utilization_not_applicable_count"] += prompt_not_applicable_count
                bucket["prompt_utilization_ratio_basis_points_sum"] += prompt_ratio_basis_points_sum
                bucket["prompt_utilization_numerator_sum"] += prompt_numerator_sum
                bucket["prompt_utilization_denominator_sum"] += prompt_denominator_sum
                bucket["inference_utilization_known_count"] += inference_known_count
                bucket["inference_utilization_unknown_count"] += inference_unknown_count
                bucket["inference_utilization_not_applicable_count"] += inference_not_applicable_count
                bucket["inference_utilization_ratio_basis_points_sum"] += inference_ratio_basis_points_sum
                bucket["inference_utilization_numerator_sum"] += inference_numerator_sum
                bucket["inference_utilization_denominator_sum"] += inference_denominator_sum
                reasoning_bucket = bucket["reasoning_mode_breakdown"].setdefault(
                    reasoning_mode,
                    {
                        "requests_total": 0,
                        "requests_success": 0,
                        "fallback_count": 0,
                        "total_cost_usd": 0.0,
                    },
                )
                reasoning_bucket["requests_total"] += requests_total
                reasoning_bucket["requests_success"] += requests_success
                reasoning_bucket["fallback_count"] += fallback_count
                reasoning_bucket["total_cost_usd"] += total_cost_micro / 1_000_000.0

        summaries: list[dict[str, Any]] = []
        for chat_mode, bucket in buckets.items():
            requests_total = int(bucket["requests_total"])
            requests_success = int(bucket["requests_success"])
            fallback_count = int(bucket["fallback_count"])
            task_request_count = int(bucket["task_request_count"])
            plan_request_count = int(bucket["plan_request_count"])
            execution_request_count = int(bucket["execution_request_count"])
            summaries.append(
                {
                    "chat_mode": chat_mode,
                    "requests_total": requests_total,
                    "requests_success": requests_success,
                    "requests_failed": int(bucket["requests_failed"]),
                    "success_rate_percent": round((requests_success / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "fallback_rate_percent": round((fallback_count / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "total_tokens": int(bucket["total_tokens"]),
                    "total_cost_usd": round(float(bucket["total_cost_usd"]), 6),
                    "avg_total_duration_ms": round(int(bucket["total_duration_ms"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "avg_first_token_ms": round(int(bucket["first_token_ms_sum"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "avg_stream_duration_ms": round(int(bucket["stream_duration_ms_sum"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "task_count": int(bucket["task_count"]),
                    "plan_count": int(bucket["plan_count"]),
                    "execution_count": int(bucket["execution_count"]),
                    "task_conversion_rate_percent": round((task_request_count / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "plan_conversion_rate_percent": round((plan_request_count / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "execution_conversion_rate_percent": round((execution_request_count / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "prompt_utilization_known_count": int(bucket["prompt_utilization_known_count"]),
                    "prompt_utilization_unknown_count": int(bucket["prompt_utilization_unknown_count"]),
                    "prompt_utilization_not_applicable_count": int(bucket["prompt_utilization_not_applicable_count"]),
                    "avg_prompt_utilization_percent": round(
                        int(bucket["prompt_utilization_ratio_basis_points_sum"])
                        / max(int(bucket["prompt_utilization_known_count"]), 1)
                        / 100,
                        2,
                    )
                    if int(bucket["prompt_utilization_known_count"]) > 0
                    else None,
                    "prompt_utilization_numerator_sum": int(bucket["prompt_utilization_numerator_sum"]),
                    "prompt_utilization_denominator_sum": int(bucket["prompt_utilization_denominator_sum"]),
                    "inference_utilization_known_count": int(bucket["inference_utilization_known_count"]),
                    "inference_utilization_unknown_count": int(bucket["inference_utilization_unknown_count"]),
                    "inference_utilization_not_applicable_count": int(bucket["inference_utilization_not_applicable_count"]),
                    "avg_inference_utilization_percent": round(
                        int(bucket["inference_utilization_ratio_basis_points_sum"])
                        / max(int(bucket["inference_utilization_known_count"]), 1)
                        / 100,
                        2,
                    )
                    if int(bucket["inference_utilization_known_count"]) > 0
                    else None,
                    "inference_utilization_numerator_sum": int(bucket["inference_utilization_numerator_sum"]),
                    "inference_utilization_denominator_sum": int(bucket["inference_utilization_denominator_sum"]),
                    "reasoning_mode_breakdown": [
                        {
                            "mode": mode,
                            "requests_total": int(mode_bucket["requests_total"]),
                            "requests_success": int(mode_bucket["requests_success"]),
                            "fallback_count": int(mode_bucket["fallback_count"]),
                            "total_cost_usd": round(float(mode_bucket["total_cost_usd"]), 6),
                        }
                        for mode, mode_bucket in sorted(bucket["reasoning_mode_breakdown"].items())
                    ],
                }
            )
        summaries.sort(key=lambda item: item["requests_total"], reverse=True)
        return summaries

    async def get_ai_ops_trend_summary(
        self,
        user_id: str,
        *,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        buckets: dict[tuple[str, str], dict[str, Any]] = {}
        for day_offset in range(days):
            date = (datetime.now() - timedelta(days=day_offset)).strftime("%Y-%m-%d")
            pattern = f"user:ai_ops:{user_id}:{date}:*"
            async for key in self.redis.scan_iter(match=pattern):
                decoded_key = key.decode() if isinstance(key, bytes) else str(key)
                parts = decoded_key.split(":")
                if len(parts) < 6:
                    continue
                reasoning_mode = parts[4]
                chat_mode = parts[5]
                raw = await self.redis.hgetall(decoded_key)
                if not raw:
                    continue
                bucket = buckets.setdefault(
                    (date, chat_mode),
                    {
                        "date": date,
                        "chat_mode": chat_mode,
                        "requests_total": 0,
                        "requests_success": 0,
                        "requests_failed": 0,
                        "fallback_count": 0,
                        "total_cost_usd": 0.0,
                        "total_duration_ms": 0,
                        "first_token_ms_sum": 0,
                        "stream_duration_ms_sum": 0,
                        "execution_request_count": 0,
                        "prompt_utilization_known_count": 0,
                        "prompt_utilization_ratio_basis_points_sum": 0,
                        "inference_utilization_known_count": 0,
                        "inference_utilization_ratio_basis_points_sum": 0,
                        "reasoning_modes": set(),
                    },
                )
                requests_total = int(raw.get("requests_total") or 0)
                requests_success = int(raw.get("requests_success") or 0)
                requests_failed = int(raw.get("requests_failed") or 0)
                fallback_count = int(raw.get("fallback_count") or 0)
                total_cost_micro = int(raw.get("total_cost_micro_usd") or 0)
                total_duration_ms = int(raw.get("total_duration_ms_sum") or 0)
                first_token_ms = int(raw.get("first_token_ms_sum") or 0)
                stream_duration_ms = int(raw.get("stream_duration_ms_sum") or 0)
                execution_request_count = int(raw.get("execution_request_count") or 0)
                prompt_utilization_known_count = int(raw.get("prompt_utilization_known_count") or 0)
                prompt_utilization_ratio_basis_points_sum = int(raw.get("prompt_utilization_ratio_basis_points_sum") or 0)
                inference_utilization_known_count = int(raw.get("inference_utilization_known_count") or 0)
                inference_utilization_ratio_basis_points_sum = int(raw.get("inference_utilization_ratio_basis_points_sum") or 0)
                bucket["requests_total"] += requests_total
                bucket["requests_success"] += requests_success
                bucket["requests_failed"] += requests_failed
                bucket["fallback_count"] += fallback_count
                bucket["total_cost_usd"] += total_cost_micro / 1_000_000.0
                bucket["total_duration_ms"] += total_duration_ms
                bucket["first_token_ms_sum"] += first_token_ms
                bucket["stream_duration_ms_sum"] += stream_duration_ms
                bucket["execution_request_count"] += execution_request_count
                bucket["prompt_utilization_known_count"] += prompt_utilization_known_count
                bucket["prompt_utilization_ratio_basis_points_sum"] += prompt_utilization_ratio_basis_points_sum
                bucket["inference_utilization_known_count"] += inference_utilization_known_count
                bucket["inference_utilization_ratio_basis_points_sum"] += inference_utilization_ratio_basis_points_sum
                bucket["reasoning_modes"].add(reasoning_mode)

        summaries: list[dict[str, Any]] = []
        for (_date, _chat_mode), bucket in buckets.items():
            requests_total = int(bucket["requests_total"])
            requests_success = int(bucket["requests_success"])
            fallback_count = int(bucket["fallback_count"])
            execution_request_count = int(bucket["execution_request_count"])
            summaries.append(
                {
                    "date": bucket["date"],
                    "chat_mode": bucket["chat_mode"],
                    "requests_total": requests_total,
                    "requests_success": requests_success,
                    "requests_failed": int(bucket["requests_failed"]),
                    "success_rate_percent": round((requests_success / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "fallback_rate_percent": round((fallback_count / requests_total) * 100, 2)
                    if requests_total > 0
                    else 0.0,
                    "total_cost_usd": round(float(bucket["total_cost_usd"]), 6),
                    "avg_total_duration_ms": round(int(bucket["total_duration_ms"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "avg_first_token_ms": round(int(bucket["first_token_ms_sum"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "avg_stream_duration_ms": round(int(bucket["stream_duration_ms_sum"]) / requests_total, 2)
                    if requests_total > 0
                    else 0.0,
                    "execution_conversion_rate_percent": round(
                        (execution_request_count / requests_total) * 100,
                        2,
                    )
                    if requests_total > 0
                    else 0.0,
                    "avg_prompt_utilization_percent": round(
                        int(bucket["prompt_utilization_ratio_basis_points_sum"])
                        / max(int(bucket["prompt_utilization_known_count"]), 1)
                        / 100,
                        2,
                    )
                    if int(bucket["prompt_utilization_known_count"]) > 0
                    else None,
                    "avg_inference_utilization_percent": round(
                        int(bucket["inference_utilization_ratio_basis_points_sum"])
                        / max(int(bucket["inference_utilization_known_count"]), 1)
                        / 100,
                        2,
                    )
                    if int(bucket["inference_utilization_known_count"]) > 0
                    else None,
                    "reasoning_modes": sorted(bucket["reasoning_modes"]),
                }
            )
        summaries.sort(key=lambda item: (item["chat_mode"], item["date"]))
        return summaries


# 单例实例
_token_tracker_instance = None


def get_token_tracker(redis_client: redis.Redis | None = None) -> TokenTracker:
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
