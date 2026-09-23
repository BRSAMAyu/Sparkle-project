"""GAIN-FIX 红旗3 守卫：USE_CONTEXT_PACK=False legacy 分支必须可走通。

基线（80f5db3d）上该分支在 `not Plan.is_completed` 处 AttributeError（Plan 无此
列），异常被外层 except 静默吞掉——plans/knowledge_stats 段整体丢失，总开关
处于「半坏」态。本守卫钉住：legacy 路径四段（recent_tasks/active_plans/
knowledge_stats）在零数据与有数据用户上都完整产出。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.plan import Plan, PlanType
from app.models.user import User


@pytest.mark.asyncio
async def test_legacy_user_context_survives_zero_data_user(db_session: AsyncSession, test_user: User):
    """零数据用户：legacy 分支不得中途夭折，各段返回诚实空结构。"""
    from app.api.v1.chat import get_user_context

    saved = settings.USE_CONTEXT_PACK
    try:
        settings.USE_CONTEXT_PACK = False
        context = await get_user_context(db_session, test_user.id, None)
    finally:
        settings.USE_CONTEXT_PACK = saved

    assert context["recent_tasks"] == []
    assert context["active_plans"] == []
    # 关键：knowledge_stats 必须被真实装配（基线上此键因 AttributeError 停留在默认 {}）
    assert context["knowledge_stats"] == {"total_nodes": 0, "mastered_nodes": 0, "learning_nodes": 0}


@pytest.mark.asyncio
async def test_legacy_user_context_maps_plan_rows_with_real_columns(db_session: AsyncSession, test_user: User):
    """有数据用户：活跃计划查询/映射使用真实列（is_active/name/type）可走通。"""
    from app.api.v1.chat import get_user_context

    db_session.add(
        Plan(
            user_id=test_user.id,
            name="期末冲刺计划",
            type=PlanType.SPRINT,
            is_active=True,
            progress=0.25,
        )
    )
    await db_session.commit()

    saved = settings.USE_CONTEXT_PACK
    try:
        settings.USE_CONTEXT_PACK = False
        context = await get_user_context(db_session, test_user.id, None)
    finally:
        settings.USE_CONTEXT_PACK = saved

    plans = context["active_plans"]
    assert len(plans) == 1
    assert plans[0]["title"] == "期末冲刺计划"
    assert plans[0]["progress"] == 0.25
    assert context["knowledge_stats"]["total_nodes"] >= 0
