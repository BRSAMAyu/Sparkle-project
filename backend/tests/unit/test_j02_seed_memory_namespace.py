"""J-02 · guest example 与 real profile namespace 隔离——「seed 不进入真实
Memory」的本卡证据面.

卡面 Work 3「guest example 与 real profile namespace 隔离」与 Acceptance
「seed 不进入真实 Memory」。既有裁决（本卡不重建、只钉住为 J-02 回归锚）：

- V3-FIX-258：demo 轮整轮跳过记忆推断（``memory_inferred_write_lane`` 单点
  过滤，判据 ``llm_service.demo_mode``）——示例体验期间的对话轮不产出伪事实
  记忆；
- V3-FIX-257：guest 转正清洗种子伪造行为统计（四表 catalog 指纹+种子窗双闸，
  见 ``test_guest_upgrade_seed_statistics_cleanup.py``）；
- V3-FIX-142：种子内容带示例声明（``Plan.source="example"`` + 读侧
  ``is_example`` 透传）。

本文件补两个此前缺失的 J-02 级锚：

1. **结构隔离**：``seed_guest_user_data`` 对访客用户零 Memory 写入——
   ``memory_goals`` / ``episodic_memories`` 行数恒 0（种子只种演示内容面，
   从不触碰真实 Memory 域；``memory_goals`` 唯一写入口是
   ``MemoryService.create_goal`` 即 onboarding/用户陈述路径）。
2. **demo 轮不进记忆 lane**（V3-FIX-258 分支此前零测试覆盖）：
   ``llm_service.demo_mode=True`` 时 ``process_chat_turn`` 在抽取前整轮短路
   （返回 None + ``demo_skipped`` 计数），用户侧原文同轮一并跳过。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.business_metrics import MEMORY_INFERRED_EXTRACT_TOTAL
from app.models.memory import EpisodicMemory, MemoryGoal
from app.models.user import User
from app.services.guest_seed_service import seed_guest_user_data
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService


async def _guest_user(db_session) -> User:
    user = User(
        username=f"guest_j02_{uuid4().hex[:8]}",
        email=f"guest_j02_{uuid4().hex[:8]}@test.local",
        hashed_password="hashed",
        registration_source="guest",
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest.mark.asyncio
async def test_guest_seed_writes_zero_rows_into_real_memory_domain(db_session):
    """结构隔离：种子落满演示内容面后，真实 Memory 域仍为零行。"""
    user = await _guest_user(db_session)

    await seed_guest_user_data(db_session, user)
    await db_session.commit()

    goal_count = await db_session.scalar(
        select(func.count()).select_from(MemoryGoal).where(MemoryGoal.user_id == user.id)
    )
    episodic_count = await db_session.scalar(
        select(func.count()).select_from(EpisodicMemory).where(EpisodicMemory.user_id == user.id)
    )
    assert goal_count == 0, "种子不得写 memory_goals（真实 goal 真源只来自用户陈述）"
    assert episodic_count == 0, "种子不得写 episodic_memories（情节记忆域）"


@pytest.mark.asyncio
async def test_demo_chat_round_is_skipped_by_memory_inferred_lane(db_session, monkeypatch):
    """V3-FIX-258 分支钉（此前零覆盖）：demo 轮整轮短路，不产出记忆候选。"""
    from app.services import llm_service as llm_service_module

    service = MemoryInferredWriteLaneService(db_session)

    counter = MEMORY_INFERRED_EXTRACT_TOTAL.labels(mode="chat", status="demo_skipped")
    before = counter._value.get()

    monkeypatch.setattr(llm_service_module.llm_service, "demo_mode", True)
    result = await service.process_chat_turn(
        user_id=uuid4(),
        session_id=uuid4(),
        user_message="我下周要考高数，很焦虑",
        assistant_message="（demo 脚本回复）",
        user_message_id=str(uuid4()),
        assistant_message_id=str(uuid4()),
    )

    assert result is None, "demo 轮必须在抽取前短路（无候选、无写面）"
    assert counter._value.get() == before + 1, "短路必须打 demo_skipped 观测点"
