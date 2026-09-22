"""CTX-PACK：context_pack 召回静默缺失观测面（2026-09-22）。

MEM-AMNESIA 卡申报的症状：「召回有候选、prompt 面直接空」，排障时只有
semantic gating 的 embedding WARNING 可见，真切刀（M-05 selfcheck）零日志。
本卡在装配面加两级可观测标记，保证「有合法候选但不 surface」永不静默：

1. ``metadata["semantic_gating"][*]["fallback_reason"]`` 区分
   ``embedding_not_configured``（无任何供应商 key，治理性/配置性降级）与
   ``embedding_error:<Exc>``（运行时供应商故障）；
2. 有合法召回候选但三个 section 全空时，落
   ``metadata["memory_surface_downgrade"]``（候选数 / surface 数 /
   selfcheck reason_counts / gating fallbacks / embedding_unavailable）
   + 显式 WARNING 日志。

embed 缺失时召回本身走非向量路径（L0 SQL 列表 + 词法 rank）不变——
本文件只锁观测面，不改召回语义。
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from app.config import settings
from app.core.context_budget import ContextBudgetScheduler
from app.core.context_pack import ContextPackBuilder
from app.models.user import User
from app.services.aurora_stage19_kill_switch_service import AuroraStage19KillSwitchService
from app.services.memory_inferred_write_lane import MemoryInferredWriteLaneService


async def _make_user_with_episodic(db_session) -> User:
    user_id = uuid4()
    db_session.add(
        User(
            id=user_id,
            username=f"user_{user_id.hex[:8]}",
            email=f"{user_id.hex[:8]}@example.com",
            hashed_password="test",
        )
    )
    await db_session.commit()
    session_id = uuid4()
    service = MemoryInferredWriteLaneService(db_session)
    candidate = await service.process_chat_turn(
        user_id=user_id,
        session_id=session_id,
        user_message="TCP 流量控制有点难，明天还要考高数。",
        assistant_message="收到，我会记住这两个点。",
        user_message_id=str(uuid4()),
        assistant_message_id=str(uuid4()),
    )
    assert candidate is not None
    return await db_session.get(User, user_id)


async def _build_pack(db_session, user_id):
    scheduler = ContextBudgetScheduler(budgets={"chat": {"preferences": 200, "goals": 200, "episodic": 200}})
    return await ContextPackBuilder(db_session, scheduler=scheduler).build(
        user_id,
        intent="chat",
        query_text="帮我解释一下泰勒公式怎么用",
    )


async def test_embedding_not_configured_has_dedicated_fallback_reason(db_session, monkeypatch):
    """无供应商 key 属配置性降级：fallback_reason 必须与运行时故障可区分。"""
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
    monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))
    user = await _make_user_with_episodic(db_session)

    pack = await _build_pack(db_session, user.id)
    gating = (pack.metadata or {}).get("semantic_gating") or {}
    assert gating, "semantic gating metadata missing"
    episodic_fallback = gating.get("episodic", {}).get("fallback_reason")
    assert episodic_fallback == "embedding_not_configured"


async def test_empty_surface_with_legal_candidates_is_marked_not_silent(db_session, monkeypatch):
    """有合法召回候选但 prompt 面全空：metadata 标记 + 归因明细，不许静默。"""
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_WRITE_ENABLED", True, raising=False)
    monkeypatch.setattr(settings, "SPARKLE_MEMORY_INFERRED_DRY_RUN_ENABLED", False, raising=False)
    monkeypatch.setattr(AuroraStage19KillSwitchService, "is_enabled", AsyncMock(return_value=False))
    user = await _make_user_with_episodic(db_session)

    pack = await _build_pack(db_session, user.id)
    # 话题不相关 query：selfcheck 切割是正确行为，但必须留观测痕迹
    assert not pack.episodic_memories and not pack.goals and not pack.preferences
    downgrade = (pack.metadata or {}).get("memory_surface_downgrade")
    assert downgrade, "empty surface with legal candidates must carry memory_surface_downgrade marker"
    assert downgrade["candidate_counts"]["episodic"] >= 1
    assert downgrade["surfaced_counts"] == {"preferences": 0, "goals": 0, "episodic": 0}
    assert downgrade["selfcheck_reasons"], "selfcheck attribution missing"
    assert downgrade["embedding_unavailable"] is True
