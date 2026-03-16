"""Smart Schedule Service - 智能排程服务"""
import random
from datetime import date, datetime, timedelta
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_event import CalendarEvent
from app.schemas.smart_schedule import (
    SmartScheduleRequest,
    SmartScheduleResponse,
    TimeSlotQuality,
    TimeSlotSuggestion,
)


class SmartScheduleService:
    """智能排程服务"""

    # 默认高效时段配置
    DEFAULT_PEAK_HOURS = {
        "morning": (6, 12),    # 6:00-12:00
        "afternoon": (12, 18),  # 12:00-18:00
        "evening": (18, 23),    # 18:00-23:00
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def suggest_time_slots(
        self,
        user_id: UUID,
        request: SmartScheduleRequest,
    ) -> SmartScheduleResponse:
        """
        生成智能时间槽建议

        算法:
        1. 加载用户已有事件（排除冲突）
        2. 获取用户认知模式（如有）
        3. 生成可用时间槽
        4. 根据任务参数评分
        5. 返回 Top 3 建议
        """
        target_date = request.preferred_date or date.today()

        # 1. 获取用户已有事件
        existing_events = await self._get_existing_events(user_id, target_date)

        # 2. 获取认知模式（可选增强）
        cognitive_patterns = await self._get_cognitive_patterns(user_id)

        # 3. 生成可用时间槽
        available_slots = self._generate_available_slots(
            target_date,
            existing_events,
            request.exclude_event_ids,
        )

        # 4. 评分排序
        scored_slots = []
        for slot in available_slots:
            score = self._score_time_slot(
                slot,
                request.energy_cost,
                request.difficulty,
                cognitive_patterns,
            )
            scored_slots.append((slot, score))

        scored_slots.sort(key=lambda x: x[1], reverse=True)

        # 5. 构建响应
        suggestions = [
            self._build_suggestion(slot, score, target_date)
            for slot, score in scored_slots[:3]
        ]

        return SmartScheduleResponse(
            suggestions=suggestions,
            cognitive_insights=cognitive_patterns.get("insights"),
            fallback_used=cognitive_patterns.get("fallback", False),
        )

    async def _get_existing_events(
        self,
        user_id: UUID,
        target_date: date,
    ) -> list[CalendarEvent]:
        """获取用户指定日期的已有事件"""
        day_start = datetime.combine(target_date, datetime.min.time())
        day_end = datetime.combine(target_date, datetime.max.time())

        query = select(CalendarEvent).where(
            CalendarEvent.user_id == user_id,
            CalendarEvent.deleted_at.is_(None),
            CalendarEvent.start_time >= day_start,
            CalendarEvent.end_time <= day_end,
        ).order_by(CalendarEvent.start_time)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _get_cognitive_patterns(self, user_id: UUID) -> dict:
        """获取用户认知模式（可选增强）"""
        try:
            from app.services.cognitive_service import CognitiveService

            cognitive_service = CognitiveService(self.db)
            # Try to get user patterns if available
            # Note: This is a placeholder - actual implementation depends on
            # the cognitive service's get_user_patterns method
            patterns = await self._try_get_user_patterns(cognitive_service, user_id)

            if patterns:
                return {
                    "insights": {
                        "focus_period": patterns.get("focus_period"),
                        "energy_pattern": patterns.get("energy_pattern"),
                    },
                    "fallback": False,
                }
        except Exception as e:
            logger.warning(f"Failed to get cognitive patterns: {e}")

        return {"fallback": True}

    async def _try_get_user_patterns(
        self,
        cognitive_service,
        user_id: UUID,
    ) -> dict | None:
        """尝试获取用户模式（带异常处理）"""
        try:
            # Check if method exists
            if hasattr(cognitive_service, "get_user_patterns"):
                return await cognitive_service.get_user_patterns(user_id)
        except Exception:
            pass
        return None

    def _generate_available_slots(
        self,
        target_date: date,
        existing_events: list[CalendarEvent],
        exclude_ids: list[str] | None,
    ) -> list[tuple[int, int]]:
        """
        生成可用时间槽

        Returns:
            List of (start_hour, end_hour) tuples
        """
        # 生成工作时段内的候选槽位（6:00-23:00）
        slots = []
        for hour in range(6, 23):
            slots.append((hour, hour + 1))

        # 排除已占用时段
        for event in existing_events:
            if exclude_ids and str(event.id) in exclude_ids:
                continue
            start_hour = event.start_time.hour
            end_hour = min(23, event.end_time.hour + (1 if event.end_time.minute > 0 else 0))
            slots = [(s, e) for s, e in slots if not (s >= start_hour and e <= end_hour)]

        return slots

    def _score_time_slot(
        self,
        slot: tuple[int, int],
        energy_cost: int,
        difficulty: int,
        cognitive_patterns: dict,
    ) -> float:
        """
        评分时间槽

        评分因素:
        - 时段质量 (40%): 高效时段 vs 低效时段
        - 任务匹配 (30%): 高能耗/高难度任务匹配高效时段
        - 认知模式 (20%): 用户个人模式
        - 随机因子 (10%): 避免过于机械
        """
        start_hour, _ = slot

        # 基础分数
        score = 0.5

        # 1. 时段质量评分 (40%)
        if 9 <= start_hour <= 11:  # 上午高峰
            score += 0.4
        elif 14 <= start_hour <= 17:  # 下午高效
            score += 0.3
        elif 6 <= start_hour <= 8:  # 早晨
            score += 0.2
        elif 18 <= start_hour <= 21:  # 晚间
            score += 0.15
        else:  # 低效时段
            score += 0.05

        # 2. 任务匹配评分 (30%)
        task_intensity = (energy_cost + difficulty) / 10  # 0.2-1.0
        if task_intensity > 0.6 and 9 <= start_hour <= 17:
            score += 0.3  # 高强度任务匹配高效时段
        elif task_intensity <= 0.4 and start_hour >= 18:
            score += 0.2  # 低强度任务适合晚间

        # 3. 认知模式评分 (20%)
        if cognitive_patterns.get("insights"):
            focus_period = cognitive_patterns["insights"].get("focus_period")
            if focus_period == "morning" and 6 <= start_hour <= 12:
                score += 0.2
            elif focus_period == "afternoon" and 12 <= start_hour <= 18:
                score += 0.2
            elif focus_period == "evening" and 18 <= start_hour <= 23:
                score += 0.2

        # 4. 随机因子 (10%)
        score += random.uniform(0, 0.1)

        return min(score, 1.0)

    def _build_suggestion(
        self,
        slot: tuple[int, int],
        score: float,
        target_date: date,
    ) -> TimeSlotSuggestion:
        """构建时间槽建议"""
        start_hour, end_hour = slot

        # 确定质量等级
        if score >= 0.8:
            quality = TimeSlotQuality.PEAK
        elif score >= 0.5:
            quality = TimeSlotQuality.NORMAL
        else:
            quality = TimeSlotQuality.LOW

        # 生成推荐理由
        if 9 <= start_hour <= 11:
            reason = "上午高效期，适合专注工作"
        elif 14 <= start_hour <= 17:
            reason = "下午稳定期，适合常规任务"
        elif 6 <= start_hour <= 8:
            reason = "清晨清醒期，适合轻度任务"
        elif 18 <= start_hour <= 21:
            reason = "晚间放松期，适合复习回顾"
        else:
            reason = "可用时段"

        return TimeSlotSuggestion(
            start_time=f"{start_hour:02d}:00",
            end_time=f"{end_hour:02d}:00",
            date=target_date,
            quality=quality,
            score=round(score, 2),
            confidence=0.7 + (score * 0.2),
            reason=reason,
        )
