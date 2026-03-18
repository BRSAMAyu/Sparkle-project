"""
决策记录服务 - 记录系统决策及使用的偏好版本
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.decision_record import DecisionRecord as DecisionRecordModel


class DecisionRecordService:
    """决策记录服务"""

    def __init__(self, db: AsyncSession | None):
        self.db = db

    async def record_decision(
        self,
        user_id: UUID,
        module: str,
        action: str,
        preference_version: int,
        preferences_snapshot: dict[str, Any],
        outcome: str,
    ) -> None:
        """记录一次决策"""
        if self.db is None:
            logger.warning("DecisionRecordService called without db session; skipping record")
            return
        record = DecisionRecordModel(
            user_id=user_id,
            module=module,
            action=action,
            preference_version=preference_version,
            preferences_snapshot=preferences_snapshot,
            outcome=outcome,
        )
        self.db.add(record)
        await self.db.commit()

    async def get_recent_records(
        self,
        user_id: UUID,
        limit: int = 10
    ) -> list[DecisionRecordModel]:
        """获取最近的决策记录"""
        result = await self.db.execute(
            select(DecisionRecordModel)
            .where(DecisionRecordModel.user_id == user_id)
            .order_by(DecisionRecordModel.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
