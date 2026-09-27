"""WT656-D04b2 如实化守卫（V3-FIX-353）。

V3-FIX-353：``AnalyticsService.get_user_profile_summary`` 曾读
``UserDailyMetric`` 预聚合表，而该表生产零写入方
（``calculate_daily_metrics`` 全仓零调用方，api/orchestration/agents/
tasks 全扫），读恒空表后把「Total Focus Time: 0 minutes /
Recent Anxiety Index: 0.00」等结构性零当真实测量值格式化进 LLM 上下文
（chat.py 主链 / cognitive_service / unified_analysis_service /
aurora signal_aggregator 四个活消费方，FIX-330 同形态第三例）。

裁决=真接线：读侧改为实时聚合真实数据源——已完成任务的
``actual_minutes``（任务完成真轨）与 ``CognitiveFragment`` 情绪
（认知碎片真轨），均由生产链路真实写入；窗口按 V3-FIX-37 用户本地日切。
``UserDailyMetric`` 表与 ``calculate_daily_metrics`` 按 FIX-330 先例
保留不删（零读者后无冒充面，删表需 Alembic 迁移面超出本卡范围）。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.models.cognitive import CognitiveFragment
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.services.analytics_service import AnalyticsService


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


async def _create_user(db_session) -> User:
    suffix = uuid4().hex[:8]
    user = User(
        username=f"wt656-{suffix}",
        email=f"wt656-{suffix}@test.local",
        hashed_password="x",
        flame_level=3,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def test_summary_measures_real_tasks_even_when_metric_table_empty(db_session):
    """UserDailyMetric 空表（生产常态）时，摘要必须给出真实测量值而非结构性零。

    修前：摘要只读 UserDailyMetric → 空表恒「Total Focus Time: 0 minutes」
    冒充测量值 → 本用例红；修后：实时聚合已完成任务 actual_minutes → 绿。
    """
    user = await _create_user(db_session)
    now = _utcnow()
    db_session.add(
        Task(
            user_id=user.id,
            title="t1",
            type=TaskType.LEARNING,
            estimated_minutes=45,
            actual_minutes=45,
            status=TaskStatus.COMPLETED,
            completed_at=now - timedelta(hours=2),
        )
    )
    db_session.add(
        Task(
            user_id=user.id,
            title="t2",
            type=TaskType.TRAINING,
            estimated_minutes=15,
            actual_minutes=15,
            status=TaskStatus.COMPLETED,
            completed_at=now - timedelta(hours=1),
        )
    )
    await db_session.commit()

    summary = await AnalyticsService(db_session).get_user_profile_summary(user.id)

    assert "Total Focus Time: 60" in summary, f"空表期不得冒充零，应给出真实测量值：{summary}"
    assert "Tasks Completed: 2" in summary
    assert "Total Focus Time: 0 " not in summary, f"结构性零冒充仍在：{summary}"


async def test_summary_anxiety_index_measured_from_real_fragments(db_session):
    """焦虑指数必须测自真实 CognitiveFragment（1/2 anxious = 0.50），而非空表恒 0.00。"""
    user = await _create_user(db_session)
    db_session.add(
        CognitiveFragment(
            user_id=user.id,
            source_type="capsule",
            content="worried about the exam",
            sentiment="anxious",
        )
    )
    db_session.add(
        CognitiveFragment(
            user_id=user.id,
            source_type="capsule",
            content="calm review session",
            sentiment="neutral",
        )
    )
    await db_session.commit()

    summary = await AnalyticsService(db_session).get_user_profile_summary(user.id)

    assert "Recent Anxiety Index: 0.50" in summary, f"焦虑指数未测自真实碎片：{summary}"


async def test_summary_zero_activity_is_true_zero_from_real_tables(db_session):
    """无任何活动记录的用户：零值来自真实表扫描（真测量零），格式保持完整。

    该用例修前后均绿——它固定「零值语义=真实无活动」与「摘要格式稳定」，
    与上面两例的冒充面（表空但真源有数据）互为补集。
    """
    user = await _create_user(db_session)

    summary = await AnalyticsService(db_session).get_user_profile_summary(user.id)

    assert "User Profile Analysis" in summary
    assert "[Recent Activity (Last 7 Days)]" in summary
    assert "Total Focus Time: 0 minutes" in summary
    assert "Tasks Completed: 0" in summary
    assert "Recent Anxiety Index: 0.00" in summary
