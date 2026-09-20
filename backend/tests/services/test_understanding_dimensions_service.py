"""D-03 · UnderstandingDimensionsService 集成测试（sqlite，真实表取数）。

钉死的行为面：
- 五维全部从真实表行计算（aurora_judgment_records / context_pack_runs /
  memory_corrections / unresolved_conflicts / chat_messages / memory 三表）；
- 缺数据 = unknown（dark channel 不假装）；
- 纠正/错误使用合理降低 correctness / scope_precision（端到端）；
- 滚动窗口边界与用户隔离；
- 幂等 upsert；无活动不落行。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.aurora_stage20 import AuroraJudgmentRecord, UnresolvedConflict
from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.memory import EpisodicMemory, MemoryCorrection, MemoryPreference
from app.models.understanding_dimensions import UnderstandingDimensionDaily
from app.services.understanding_dimensions_service import (
    UnderstandingDimensionsService,
    window_bounds,
)

METRIC_DAY = datetime(2026, 9, 19).date()


@pytest_asyncio.fixture(name="other_user")
async def _other_user_fixture(db_session):
    from app.models.user import User

    user = User(username="otheruser", email="other@example.com", hashed_password="hashed", photon_balance=0)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _ts(day_offset: float) -> datetime:
    """metric_day 当日 12:00 起，day_offset 天偏移（负=窗口内，正=窗口外）。"""
    return datetime(2026, 9, 19, 12) + timedelta(days=day_offset)


async def _seed_judgments(
    db, user_id, *, count: int = 3, ctx_score: float = 1.0, task_score: float = 1.0, offset: float = -1.0
):
    for i in range(count):
        db.add(
            AuroraJudgmentRecord(
                user_id=user_id,
                task_sufficiency_score=task_score,
                task_missing_dimensions=["intent_clarity"] if i == 0 else [],
                context_sufficiency_score=ctx_score,
                context_missing_dimensions=["relevant_memory_present"] if i == 0 else [],
                computed_at=_ts(offset),
                created_at=_ts(offset),
                updated_at=_ts(offset),
            )
        )


async def _seed_pack_run(db, user_id, *, memory_counts: dict | None, offset: float = -1.0):
    db.add(
        ContextPackRun(
            user_id=user_id,
            intent="chat",
            budgets={},
            token_usage={},
            memory_counts=memory_counts or {},
            created_at=_ts(offset),
            updated_at=_ts(offset),
        )
    )


async def _seed_preference(db, user_id, *, created_offset: float = -40.0):
    record = MemoryPreference(
        user_id=user_id,
        pref_key=f"pref_{uuid4().hex[:8]}",
        pref_value={"v": 1},
        version=1,
        created_at=_ts(created_offset),
        updated_at=_ts(created_offset),
    )
    db.add(record)
    await db.flush()  # 生成 id，供 correction 关联
    return record


async def _seed_correction(db, user_id, record, *, action: str, memory_type: str = "preference", offset: float = -1.0):
    db.add(
        MemoryCorrection(
            user_id=user_id,
            memory_type=memory_type,
            memory_id=record.id,
            action=action,
            created_at=_ts(offset),
            updated_at=_ts(offset),
        )
    )


# ---------------------------------------------------------------------------
# 窗口边界
# ---------------------------------------------------------------------------


def test_window_bounds_rolling_seven_days():
    start, end = window_bounds(METRIC_DAY, 7)
    assert start == datetime(2026, 9, 13)
    assert end == datetime(2026, 9, 20)


# ---------------------------------------------------------------------------
# 真实表取数 → 五维
# ---------------------------------------------------------------------------


async def test_dimensions_computed_from_real_tables(db_session, test_user):
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, test_user.id, count=3)
    await _seed_pack_run(db_session, test_user.id, memory_counts={"preferences": 2})
    await db_session.commit()

    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload is not None
    assert payload["coverage"]["status"] == "ok"
    assert payload["coverage"]["value"] == pytest.approx(1.0)
    assert payload["coverage"]["samples"] == 3
    assert set(payload["coverage"]["detail"]["top_missing"]) == {"relevant_memory_present", "intent_clarity"}
    assert payload["correctness"]["status"] == "ok"
    assert payload["correctness"]["value"] == pytest.approx(1.0)  # 0 negatives / 1 usage
    # 反馈通道无数据 → unknown（不假装）
    assert payload["scope_precision"]["status"] == "unknown"
    assert payload["utility"]["status"] == "unknown"
    assert payload["freshness"]["status"] == "unknown"

    row = await service.get_latest_row(user_id=test_user.id)
    assert row is not None and row.metric_date == METRIC_DAY
    assert row.anchors["coverage"]["anchor_value"] is None  # 无 chat 消息 → 锚点 insufficient


async def test_corrections_lower_correctness_end_to_end(db_session, test_user, other_user):
    """验收②端到端：同样使用量下，纠正多的用户 correctness 更低。"""
    service = UnderstandingDimensionsService(db_session)
    for user in (test_user, other_user):
        await _seed_judgments(db_session, user.id, count=3)
        for _ in range(4):
            await _seed_pack_run(db_session, user.id, memory_counts={"goals": 1})
    clean_pref = await _seed_preference(db_session, test_user.id)
    corrected_pref = await _seed_preference(db_session, other_user.id)
    await _seed_correction(db_session, other_user.id, corrected_pref, action="reject")
    await _seed_correction(db_session, test_user.id, clean_pref, action="confirm")
    await db_session.commit()

    clean = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    corrected = await service.compute_daily_for_user(user_id=other_user.id, day=METRIC_DAY)
    assert clean["correctness"]["value"] == pytest.approx(1.0)
    # 1 negative / 4 usage = 0.25 → 1 - 0.25/0.5 = 0.5
    assert corrected["correctness"]["value"] == pytest.approx(0.5)
    assert corrected["correctness"]["detail"]["negative_corrections"] == 1


async def test_conflicts_also_lower_correctness(db_session, test_user):
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, test_user.id, count=3)
    for _ in range(4):
        await _seed_pack_run(db_session, test_user.id, memory_counts={"episodic": 1})
    db_session.add(
        UnresolvedConflict(
            user_id=test_user.id,
            conflict_key=f"ck_{uuid4().hex[:8]}",
            left_summary="a",
            right_summary="b",
            left_lane="direct_capture",
            right_lane="rule",
            status="pending_user",
            surfaced_at=_ts(-1),
            created_at=_ts(-1),
            updated_at=_ts(-1),
        )
    )
    await db_session.commit()
    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload["correctness"]["value"] == pytest.approx(0.5)
    assert payload["correctness"]["detail"]["unresolved_conflicts"] == 1


async def test_scope_misuse_lowers_scope_precision(db_session, test_user):
    """验收②端到端：scope 误用反馈压低 scope_precision（dark→ok→降低）。"""
    service = UnderstandingDimensionsService(db_session)
    pref = await _seed_preference(db_session, test_user.id)
    # 8 accepted + 2 corrected → 误用率 0.2 → 1 - 0.2/0.25 = 0.2
    for _ in range(8):
        await _seed_correction(db_session, test_user.id, pref, action="memory_reference_accepted")
    for _ in range(2):
        await _seed_correction(db_session, test_user.id, pref, action="memory_reference_corrected")
    await db_session.commit()
    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload["scope_precision"]["status"] == "ok"
    assert payload["scope_precision"]["value"] == pytest.approx(0.2)
    assert payload["utility"]["status"] == "ok"  # 10 decisive ≥ 3
    assert payload["utility"]["value"] == pytest.approx(0.8)


async def test_freshness_lag_from_record_created_at(db_session, test_user):
    """40 天前建的 preference 今天被删 → lag=41 天 → freshness=0（>30 容忍）。"""
    service = UnderstandingDimensionsService(db_session)
    pref = await _seed_preference(db_session, test_user.id, created_offset=-40.0)
    await _seed_correction(db_session, test_user.id, pref, action="delete", offset=0.0)  # 当日
    await db_session.commit()
    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload["freshness"]["status"] == "ok"
    # created at (D-40 12:00), corrected at (D 12:00) → 40 days
    assert payload["freshness"]["detail"]["mean_lag_days"] == pytest.approx(40.0)
    assert payload["freshness"]["value"] == pytest.approx(0.0)


async def test_rolling_window_excludes_old_rows(db_session, test_user):
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, test_user.id, count=3, offset=-30.0)  # 窗口外
    await _seed_pack_run(db_session, test_user.id, memory_counts={"preferences": 1}, offset=-30.0)
    await db_session.commit()
    inputs = await service.collect_window_inputs(user_id=test_user.id, day=METRIC_DAY)
    assert inputs.context_scores == []
    assert inputs.usage_opportunities == 0
    assert not inputs.has_any_activity
    assert await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY) is None
    rows = (
        (
            await db_session.execute(
                select(UnderstandingDimensionDaily).where(UnderstandingDimensionDaily.user_id == test_user.id)
            )
        )
        .scalars()
        .all()
    )
    assert rows == []  # 无活动不落行


async def test_user_isolation(db_session, test_user, other_user):
    """另一用户的 judgment/纠正不得进入本用户窗口。"""
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, other_user.id, count=5)
    pref = await _seed_preference(db_session, other_user.id)
    await _seed_correction(db_session, other_user.id, pref, action="delete")
    await _seed_pack_run(db_session, test_user.id, memory_counts={"preferences": 1})
    await db_session.commit()
    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload["coverage"]["status"] == "unknown"  # 只有自己的 judgment 才算
    assert payload["correctness"]["value"] == pytest.approx(1.0)
    assert payload["correctness"]["detail"]["negative_corrections"] == 0


async def test_daily_upsert_idempotent(db_session, test_user):
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, test_user.id, count=3)
    await _seed_pack_run(db_session, test_user.id, memory_counts={"preferences": 1})
    await db_session.commit()

    first = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    second = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert first == second
    rows = (
        (
            await db_session.execute(
                select(UnderstandingDimensionDaily).where(UnderstandingDimensionDaily.user_id == test_user.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].dimensions == first


async def test_coverage_anchor_from_repeat_questions(db_session, test_user):
    """coverage 锚点 = 1 - 重复提问率（独立行为流）。"""
    service = UnderstandingDimensionsService(db_session)
    await _seed_judgments(db_session, test_user.id, count=3)
    for content, n in (("帮我制定考研复习计划", 2), ("今天天气怎么样", 1)):
        for _ in range(n):
            db_session.add(
                ChatMessage(
                    user_id=test_user.id,
                    session_id=uuid4(),
                    role=MessageRole.USER,
                    content=content,
                    tokens_used=0,
                    model_name="test",
                    created_at=_ts(-1),
                    updated_at=_ts(-1),
                )
            )
    await db_session.commit()
    row_inputs = await service.collect_window_inputs(user_id=test_user.id, day=METRIC_DAY)
    assert len(row_inputs.user_messages) == 3
    await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    # eligible: '帮我制定考研复习计划' x2 (9字>4), '今天天气怎么样' (7字>4) → 3 eligible, 1 dup
    # rate = 1/3 → anchor = 2/3
    row = await service.get_latest_row(user_id=test_user.id)
    assert row.anchors["coverage"]["anchor_value"] == pytest.approx(1 - 1 / 3, abs=1e-3)


async def test_episodic_lag_join_and_unknown_memory_type(db_session, test_user):
    """episodic 类型 lag join 可用；未知 memory_type 的 correction 不进 lag 样本也不炸。"""
    service = UnderstandingDimensionsService(db_session)
    await _seed_pack_run(db_session, test_user.id, memory_counts={"episodic": 1})  # correctness 有分母
    episodic = EpisodicMemory(
        user_id=test_user.id,
        summary="s" * 20,
        source_type="chat_turn",
        occurred_at=_ts(-10),
        confidence=0.5,
        created_at=_ts(-10),
        updated_at=_ts(-10),
    )
    db_session.add(episodic)
    await db_session.flush()
    await _seed_correction(db_session, test_user.id, episodic, action="retract", memory_type="episodic")
    await _seed_correction(db_session, test_user.id, episodic, action="delete", memory_type="mystery_type")
    await db_session.commit()
    payload = await service.compute_daily_for_user(user_id=test_user.id, day=METRIC_DAY)
    assert payload["freshness"]["status"] == "ok"
    assert payload["freshness"]["detail"]["lag_sample_count"] == 1  # 未知类型被忽略
    assert payload["correctness"]["detail"]["negative_corrections"] == 2  # retract+delete 都算否定
