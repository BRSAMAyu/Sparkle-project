"""
PlanExecutionRecordService - 方案执行记录持久化服务

负责将验证结果保存到数据库，并支持后续查询分析
"""
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan_execution_record import PlanExecutionRecord


class PlanExecutionRecordService:
    """方案执行记录服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_record(
        self,
        plan_id: UUID,
        user_id: UUID,
        validation_status: str,
        quality_score: float,
        criteria_results: dict[str, Any],
        tool_summary: dict[str, int],
        issues: list[str],
    ) -> PlanExecutionRecord:
        """
        创建执行记录

        Args:
            plan_id: 方案ID
            user_id: 用户ID
            validation_status: 验证状态 (passed/failed/partial)
            quality_score: 质量分数
            criteria_results: 标准检查结果
            tool_summary: 工具执行统计
            issues: 问题列表

        Returns:
            PlanExecutionRecord: 创建的记录
        """
        record = PlanExecutionRecord(
            plan_id=plan_id,
            user_id=user_id,
            validation_status=validation_status,
            quality_score=quality_score,
            criteria_results=criteria_results,
            total_tools=tool_summary.get("total", 0),
            successful_tools=tool_summary.get("successful", 0),
            failed_tools=tool_summary.get("failed", 0),
            issues=issues,
        )

        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        logger.info(
            f"Created execution record: plan_id={plan_id}, "
            f"status={validation_status}, score={quality_score:.2f}"
        )

        return record

    async def get_record_by_id(self, record_id: UUID) -> PlanExecutionRecord | None:
        """获取单个记录"""
        result = await self.db.execute(
            select(PlanExecutionRecord).where(PlanExecutionRecord.id == record_id)
        )
        return result.scalar_one_or_none()

    async def get_records_by_plan(
        self, plan_id: UUID, limit: int = 20
    ) -> list[PlanExecutionRecord]:
        """获取方案的所有执行记录"""
        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(PlanExecutionRecord.plan_id == plan_id)
            .order_by(PlanExecutionRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_records_by_user(
        self, user_id: UUID, days: int = 30, limit: int = 100
    ) -> list[PlanExecutionRecord]:
        """获取用户的执行记录"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(
                and_(
                    PlanExecutionRecord.user_id == user_id,
                    PlanExecutionRecord.created_at >= cutoff,
                )
            )
            .order_by(PlanExecutionRecord.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_user_execution_stats(
        self, user_id: UUID, days: int = 30
    ) -> dict[str, Any]:
        """
        获取用户执行统计

        Args:
            user_id: 用户ID
            days: 统计天数

        Returns:
            统计结果包含:
            - total: 总执行次数
            - avg_score: 平均质量分数
            - pass_rate: 通过率
            - status_breakdown: 状态分布
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(
                and_(
                    PlanExecutionRecord.user_id == user_id,
                    PlanExecutionRecord.created_at >= cutoff,
                )
            )
        )
        records = list(result.scalars().all())

        if not records:
            return {
                "total": 0,
                "avg_score": 0.0,
                "pass_rate": 0.0,
                "status_breakdown": {"passed": 0, "partial": 0, "failed": 0},
            }

        total = len(records)
        avg_score = sum(r.quality_score for r in records) / total
        passed = sum(1 for r in records if r.validation_status == "passed")
        partial = sum(1 for r in records if r.validation_status == "partial")
        failed = sum(1 for r in records if r.validation_status == "failed")

        return {
            "total": total,
            "avg_score": round(avg_score, 3),
            "pass_rate": round(passed / total, 3),
            "status_breakdown": {
                "passed": passed,
                "partial": partial,
                "failed": failed,
            },
        }

    async def get_plan_execution_stats(
        self, plan_id: UUID
    ) -> dict[str, Any]:
        """
        获取方案执行统计

        Args:
            plan_id: 方案ID

        Returns:
            统计结果
        """
        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(PlanExecutionRecord.plan_id == plan_id)
        )
        records = list(result.scalars().all())

        if not records:
            return {
                "total": 0,
                "avg_score": 0.0,
                "pass_rate": 0.0,
                "latest_status": None,
            }

        total = len(records)
        avg_score = sum(r.quality_score for r in records) / total
        passed = sum(1 for r in records if r.validation_status == "passed")

        # 获取最新状态
        latest = max(records, key=lambda r: r.created_at)

        return {
            "total": total,
            "avg_score": round(avg_score, 3),
            "pass_rate": round(passed / total, 3),
            "latest_status": latest.validation_status,
            "latest_score": latest.quality_score,
        }

    async def update_user_feedback(
        self,
        record_id: UUID,
        satisfaction: int,
        feedback: str | None = None,
    ) -> PlanExecutionRecord | None:
        """
        更新用户反馈

        Args:
            record_id: 记录ID
            satisfaction: 满意度 (1-5)
            feedback: 反馈文本

        Returns:
            更新后的记录
        """
        record = await self.get_record_by_id(record_id)
        if not record:
            return None

        record.user_satisfaction = satisfaction
        record.user_feedback = feedback

        await self.db.commit()
        await self.db.refresh(record)

        logger.info(
            f"Updated user feedback: record_id={record_id}, "
            f"satisfaction={satisfaction}"
        )

        return record

    async def mark_applied_to_learning(
        self, record_id: UUID
    ) -> PlanExecutionRecord | None:
        """
        标记记录已应用到学习系统

        Args:
            record_id: 记录ID

        Returns:
            更新后的记录
        """
        record = await self.get_record_by_id(record_id)
        if not record:
            return None

        record.applied_to_learning = True

        await self.db.commit()
        await self.db.refresh(record)

        return record

    async def get_unapplied_records(
        self, limit: int = 100
    ) -> list[PlanExecutionRecord]:
        """
        获取未应用到学习系统的记录

        用于批量处理学习反馈

        Args:
            limit: 限制数量

        Returns:
            未应用的记录列表
        """
        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(not PlanExecutionRecord.applied_to_learning)
            .order_by(PlanExecutionRecord.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_quality_trend(
        self, user_id: UUID, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        获取质量趋势数据

        Args:
            user_id: 用户ID
            days: 天数

        Returns:
            每日统计列表
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        result = await self.db.execute(
            select(PlanExecutionRecord)
            .where(
                and_(
                    PlanExecutionRecord.user_id == user_id,
                    PlanExecutionRecord.created_at >= cutoff,
                )
            )
            .order_by(PlanExecutionRecord.created_at.asc())
        )
        records = list(result.scalars().all())

        # 按日期分组
        daily_stats: dict[str, list[PlanExecutionRecord]] = {}
        for record in records:
            date_key = record.created_at.strftime("%Y-%m-%d")
            if date_key not in daily_stats:
                daily_stats[date_key] = []
            daily_stats[date_key].append(record)

        # 计算每日统计
        trend = []
        for date_key, day_records in daily_stats.items():
            count = len(day_records)
            avg_score = sum(r.quality_score for r in day_records) / count
            pass_rate = sum(1 for r in day_records if r.validation_status == "passed") / count

            trend.append({
                "date": date_key,
                "count": count,
                "avg_score": round(avg_score, 3),
                "pass_rate": round(pass_rate, 3),
            })

        return trend
