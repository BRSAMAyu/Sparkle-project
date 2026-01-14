"""
LLM 成本控制与配额管理模块

功能:
1. 每日 Token 配额限制
2. 用户级费用控制
3. 断路器保护 (防止级联故障)
4. 使用统计与告警

作者: Claude Code (Opus 4.5)
创建时间: 2026-01-03
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from dataclasses import dataclass

try:
    from circuitbreaker import circuit
except ImportError:
    def circuit(*_args, **_kwargs):
        def decorator(func):
            return func
        return decorator
import redis.asyncio as redis
from app.config import settings
from app.core.redis_utils import resolve_redis_password

logger = logging.getLogger(__name__)


@dataclass
class QuotaConfig:
    """配额配置"""
    daily_token_limit: int = 100_000  # 每日 Token 限额
    warning_threshold: float = 0.8    # 警告阈值 (80%)
    emergency_mode: bool = False      # 紧急模式 (管理员可临时提升)
    emergency_multiplier: float = 2.0  # 紧急模式倍数

    # Token 估算参数
    CHINESE_CHAR_TOKEN_RATIO = 2.0    # 中文字符:token 比例
    ENGLISH_CHAR_TOKEN_RATIO = 4.0    # 英文字符:token 比例


@dataclass
class QuotaCheckResult:
    """配额检查结果"""
    allowed: bool
    current_usage: int
    limit: int
    remaining: int
    percentage: float
    message: Optional[str] = None


class QuotaExceededError(Exception):
    """Raised when an LLM quota check fails."""


@dataclass
class UserStats:
    """用户使用统计"""
    user_id: str
    today_usage: int
    daily_limit: int
    weekly_usage: int
    total_calls: int
    avg_tokens_per_call: float
    last_call_time: Optional[datetime]


class LLMCostGuard:
    """
    LLM 成本守卫 - 防止费用失控

    工作流程:
    1. 估算请求 Token 数量
    2. 检查用户当日配额
    3. 允许/拒绝请求
    4. 记录实际使用量
    5. 触发告警 (如果需要)
    """

    # Redis Key 模板
    KEY_DAILY_USAGE = "llm_tokens:{user_id}:{date}"
    KEY_WEEKLY_USAGE = "llm_tokens:{user_id}:week:{year}:{week}"
    KEY_TOTAL_CALLS = "llm_calls:{user_id}:{date}"
    KEY_EMERGENCY_MODE = "llm_emergency_mode"

    def __init__(
        self,
        redis_client: redis.Redis,
        config: Optional[QuotaConfig] = None
    ):
        """
        初始化成本守卫

        Args:
            redis_client: Redis 异步客户端
            config: 配额配置
        """
        self.redis = redis_client
        self.config = config or QuotaConfig()

        logger.info(
            f"LLMCostGuard initialized - "
            f"Daily limit: {self.config.daily_token_limit:,} tokens, "
            f"Warning at: {self.config.warning_threshold * 100}%"
        )

    async def check_quota(
        self,
        user_id: str,
        estimated_tokens: int,
        check_only: bool = False
    ) -> QuotaCheckResult:
        """
        检查用户配额

        Args:
            user_id: 用户ID
            estimated_tokens: 预估 Token 数量
            check_only: 仅检查,不扣减配额

        Returns:
            QuotaCheckResult: 配额检查结果
        """
        today = datetime.now().date()
        daily_key = self.KEY_DAILY_USAGE.format(user_id=user_id, date=today)

        # 获取当前使用量
        current_usage = int(await self.redis.get(daily_key) or 0)

        # 检查紧急模式
        emergency_mode = await self._is_emergency_mode()
        limit = self.config.daily_token_limit
        if emergency_mode:
            limit = int(limit * self.config.emergency_multiplier)

        # 计算剩余配额
        remaining = limit - current_usage
        percentage = current_usage / limit if limit > 0 else 1.0

        # 检查是否允许
        allowed = remaining >= estimated_tokens

        # 构建结果
        result = QuotaCheckResult(
            allowed=allowed,
            current_usage=current_usage,
            limit=limit,
            remaining=remaining,
            percentage=percentage
        )

        if not allowed:
            result.message = (
                f"配额不足: 已使用 {current_usage:,}/{limit:,} tokens "
                f"({percentage*100:.1f}%), 需要 {estimated_tokens:,}, "
                f"剩余 {remaining:,}"
            )
            logger.warning(f"用户 {user_id} 配额超限: {result.message}")

            # 触发告警
            await self._trigger_quota_alert(user_id, current_usage, limit)

        elif percentage >= self.config.warning_threshold:
            result.message = (
                f"配额警告: 已使用 {current_usage:,}/{limit:,} tokens "
                f"({percentage*100:.1f}%)"
            )
            logger.warning(f"用户 {user_id} 配额警告: {result.message}")

        if not check_only and allowed:
            # 扣减配额 (实际使用时更新)
            await self._increment_usage(daily_key, estimated_tokens)

        return result

    async def record_usage(
        self,
        user_id: str,
        actual_tokens: int,
        model: str = "unknown"
    ) -> None:
        """
        记录实际 Token 使用量

        Args:
            user_id: 用户ID
            actual_tokens: 实际 Token 数量
            model: 使用的模型
        """
        today = datetime.now().date()
        daily_key = self.KEY_DAILY_USAGE.format(user_id=user_id, date=today)
        weekly_key = self._get_weekly_key(user_id)
        calls_key = self.KEY_TOTAL_CALLS.format(user_id=user_id, date=today)

        # 使用 Redis 管道保证原子性
        pipe = self.redis.pipeline()
        pipe.incrby(daily_key, actual_tokens)
        pipe.incrby(weekly_key, actual_tokens)
        pipe.incr(calls_key)
        pipe.expire(daily_key, 86400)  # 24小时
        pipe.expire(weekly_key, 7 * 86400)  # 7天
        pipe.expire(calls_key, 86400)

        await pipe.execute()

        logger.debug(
            f"记录使用量 - User: {user_id}, "
            f"Tokens: {actual_tokens}, Model: {model}"
        )

    async def get_user_stats(self, user_id: str) -> UserStats:
        """
        获取用户使用统计

        Args:
            user_id: 用户ID

        Returns:
            UserStats: 用户统计信息
        """
        today = datetime.now().date()
        daily_key = self.KEY_DAILY_USAGE.format(user_id=user_id, date=today)
        weekly_key = self._get_weekly_key(user_id)
        calls_key = self.KEY_TOTAL_CALLS.format(user_id=user_id, date=today)

        # 批量获取数据
        pipe = self.redis.pipeline()
        pipe.get(daily_key)
        pipe.get(weekly_key)
        pipe.get(calls_key)
        results = await pipe.execute()

        today_usage = int(results[0] or 0)
        weekly_usage = int(results[1] or 0)
        total_calls = int(results[2] or 0)

        # 计算平均值
        avg_tokens = today_usage / total_calls if total_calls > 0 else 0.0

        # 获取最后调用时间 (可选,需要额外存储)
        last_call = None  # 可以通过另一个 key 存储

        return UserStats(
            user_id=user_id,
            today_usage=today_usage,
            daily_limit=self.config.daily_token_limit,
            weekly_usage=weekly_usage,
            total_calls=total_calls,
            avg_tokens_per_call=avg_tokens,
            last_call_time=last_call
        )

    def estimate_tokens(self, text: str, is_chinese_heavy: bool = True) -> int:
        """
        估算文本的 Token 数量

        注意: 这是一个粗略估算,实际 Token 数可能因模型而异

        Args:
            text: 文本内容
            is_chinese_heavy: 是否主要是中文 (默认 True,针对中文场景)

        Returns:
            int: 估算的 Token 数量
        """
        if not text:
            return 0

        # 统计字符类型
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars

        if is_chinese_heavy:
            # 中文场景: 中文约 2 字符/token,英文约 4 字符/token
            estimated = (chinese_chars / self.config.CHINESE_CHAR_TOKEN_RATIO) + \
                       (other_chars / self.config.ENGLISH_CHAR_TOKEN_RATIO)
        else:
            # 英文场景: 统一按 4 字符/token
            estimated = len(text) / self.config.ENGLISH_CHAR_TOKEN_RATIO

        # 加上安全边际 (1.2倍)
        return int(estimated * 1.2)

    async def _increment_usage(self, key: str, amount: int) -> None:
        """原子性增加使用量"""
        await self.redis.incrby(key, amount)

    async def _is_emergency_mode(self) -> bool:
        """检查是否处于紧急模式"""
        mode = await self.redis.get(self.KEY_EMERGENCY_MODE)
        return mode == b"1" or mode == "1"

    async def enable_emergency_mode(self, duration_minutes: int = 60) -> None:
        """
        启用紧急模式 (管理员操作)

        Args:
            duration_minutes: 持续时间(分钟)
        """
        await self.redis.setex(
            self.KEY_EMERGENCY_MODE,
            duration_minutes * 60,
            "1"
        )
        logger.critical(
            f"紧急模式已启用,持续 {duration_minutes} 分钟, "
            f"配额将提升 {self.config.emergency_multiplier} 倍"
        )

    async def disable_emergency_mode(self) -> None:
        """禁用紧急模式"""
        await self.redis.delete(self.KEY_EMERGENCY_MODE)
        logger.info("紧急模式已禁用")

    async def _trigger_quota_alert(self, user_id: str, usage: int, limit: int) -> None:
        """
        触发配额告警

        这里可以集成到 Prometheus, Slack, Email 等
        """
        # 记录到 Redis 用于监控
        alert_key = f"llm_alerts:{datetime.now().date()}:{user_id}"
        await self.redis.setex(alert_key, 86400, f"Quota exceeded: {usage}/{limit}")

        # 可以在这里集成外部告警系统
        # await self._send_slack_alert(user_id, usage, limit)
        # await self._send_email_alert(user_id, usage, limit)

        logger.error(
            f"配额告警 - User: {user_id}, "
            f"Usage: {usage:,}/{limit:,} "
            f"({usage/limit*100:.1f}%)"
        )

    def _get_weekly_key(self, user_id: str) -> str:
        """获取周配额 Key"""
        now = datetime.now()
        year, week, _ = now.isocalendar()
        return self.KEY_WEEKLY_USAGE.format(
            user_id=user_id,
            year=year,
            week=week
        )

    async def get_daily_stats(self, user_id: str) -> Dict:
        """获取每日统计 (用于 API 返回)"""
        stats = await self.get_user_stats(user_id)
        return {
            "user_id": user_id,
            "today_usage": stats.today_usage,
            "daily_limit": stats.daily_limit,
            "remaining": stats.daily_limit - stats.today_usage,
            "percentage": round(stats.today_usage / stats.daily_limit * 100, 2) if stats.daily_limit > 0 else 100,
            "total_calls": stats.total_calls,
            "avg_tokens_per_call": round(stats.avg_tokens_per_call, 2),
            "emergency_mode": await self._is_emergency_mode(),
        }


# 断路器装饰器 - 防止 LLM 服务级联故障
@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
async def protected_llm_call(llm_service_func, *args, **kwargs):
    """
    带断路器保护的 LLM 调用

    使用示例:
        result = await protected_llm_call(
            llm_service.chat,
            messages=messages,
            model=model
        )

    断路器规则:
    - 5次失败后触发
    - 60秒后尝试恢复
    - 自动熔断防止级联故障
    """
    try:
        return await llm_service_func(*args, **kwargs)
    except Exception as e:
        logger.error(f"LLM 调用失败: {str(e)}")
        raise


# 单例实例 (需要在应用启动时注入 Redis)
cost_guard: Optional[LLMCostGuard] = None


async def init_cost_guard(redis_url: str = "redis://localhost:6379/1"):
    """初始化成本守卫"""
    global cost_guard
    resolved_password, _ = resolve_redis_password(redis_url, settings.REDIS_PASSWORD)
    redis_client = redis.from_url(redis_url, password=resolved_password)
    cost_guard = LLMCostGuard(redis_client)
    return cost_guard


# 使用示例
if __name__ == "__main__":
    import asyncio
    import os

    async def demo():
        # 连接 Redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/1")
        guard = await init_cost_guard(redis_url)

        user_id = "test_user_123"

        # 估算 Token
        text = "你好，这是一个测试问题。Hello, this is a test question."
        estimated = guard.estimate_tokens(text)
        print(f"文本: {text}")
        print(f"估算 Token: {estimated}")

        # 检查配额
        result = await guard.check_quota(user_id, estimated, check_only=True)
        print(f"\n配额检查: {result}")

        # 记录使用量
        await guard.record_usage(user_id, estimated, model="gpt-4")

        # 获取统计
        stats = await guard.get_daily_stats(user_id)
        print(f"\n用户统计: {stats}")

        # 模拟超限
        huge_text = "test " * 50000
        huge_tokens = guard.estimate_tokens(huge_text)
        result = await guard.check_quota(user_id, huge_tokens, check_only=True)
        print(f"\n超限测试: {result}")

    asyncio.run(demo())
