"""WT378-04 复核修复（wt379 轮2）：同一 explicit JSONB 行双写方丢更新.

轮1猎缺 + 轮2独立复核 CONFIRMED 的机制：P-03（proactive_suggestion_service）与
Aurora（aurora/runtime_v1/user_preferences.py）对**同一行**
``UserPreferencesCenter.explicit`` 各自做「SELECT（无锁）→ dict() 快照 → 改 →
整体覆写 → commit」。键集不相交但行级最后提交者胜出：两事务都先读到旧快照时，
后提交者用旧快照整列覆写，先提交者的键**整组蒸发**（显式 mute 蒸发 = 骚扰回归）。

修复契约（最小侵入、跨方言可测）：
1. 写侧读行 ``with_for_update()``——PostgreSQL 行锁串行化读改写（sqlite 忽略，无害）；
2. 版本守卫原子 UPDATE（``UPDATE ... WHERE version = 读时版本``）+ 冲突重读合并
   重试——读改写从「快照覆写」改为「CAS 合并」，sqlite/PG 均可验证。

并发建模说明（诚实口径）：本文件不用真双连接竞争窗口（sqlite 行锁不可测、
真时序不可稳定复现），而是用 SQLAlchemy identity map 的确定性等价物复现 READ
COMMITTED 交错——B 的会话先加载行快照（等价于 B 的 SELECT 发生在 A 提交前），
A 提交后再让 B 走真实服务代码写回。修前 B 以旧快照整列覆写 → 对方键蒸发（红）；
修后版本守卫逼 B 重读合并 → 双方键都存活（绿）。
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import BaseModel
from app.models.user import User
from app.models.user_preferences import UserPreferencesCenter

_SUGGESTION_KEY = "proactive_suggestion_muted"
_AURORA_KEY = "aurora_stimulation_mode"


def _two_makers(tmp_path: Path):
    """同一 sqlite 文件上的两个独立 engine/sessionmaker（各自持有独立连接）。"""
    url = f"sqlite+aiosqlite:///{tmp_path / 'prefs_race.db'}"
    maker = lambda engine: async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # noqa: E731
    engine_a, engine_b = create_async_engine(url), create_async_engine(url)
    return engine_a, maker(engine_a), engine_b, maker(engine_b)


async def _seed(engine_a, maker_a) -> str:
    """建表 + 用户 + 已有 Aurora 偏好行（version=1）。"""
    async with engine_a.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async with maker_a() as session:
        user = User(username="raceuser", email="race@example.com", hashed_password="hashed", photon_balance=0)
        session.add(user)
        await session.flush()
        session.add(UserPreferencesCenter(user_id=user.id, explicit={_AURORA_KEY: "standard"}, version=1))
        await session.commit()
        return str(user.id)


@pytest.mark.asyncio
async def test_aurora_write_does_not_erase_p03_mute_on_stale_snapshot(tmp_path) -> None:
    """交错方向 A：P-03 先提交 mute，Aurora 持旧快照写 → mute 键不得蒸发。"""
    engine_a, maker_a, engine_b, maker_b = _two_makers(tmp_path)
    try:
        user_id = await _seed(engine_a, maker_a)

        # B（Aurora）先持有行快照（等价于其 SELECT 发生在 A 提交之前）
        session_b_hold = maker_b()
        # 强引用握住已加载的 ORM 行：identity map 是弱引用容器，bare expression
        # 加载的行会被立即回收、快照失效。持有强引用才等价于「B 的 SELECT
        # 发生在 A 提交之前」的 READ COMMITTED 交错建模。
        held_b = (
            (
                await session_b_hold.execute(
                    select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
                )
            )
            .scalars()
            .one()
        )
        assert held_b is not None

        # A（P-03）读-改-写提交 mute
        async with maker_a() as session_a:
            from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

            await ProactiveSuggestionFeedbackService(session_a).record_mute(user_id, "comeback_nudge")

        # B（Aurora）持旧快照写 stimulation mode —— 走真实服务代码
        # （hold 会话首查已 autobegin，直接调用即可）
        from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService

        await AuroraUserPreferencesService(session_b_hold).update(user_id, {_AURORA_KEY: "low"})
        await session_b_hold.close()

        async with maker_a() as verify:
            row = (
                (await verify.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)))
                .scalars()
                .one()
            )
        assert row.explicit.get(_AURORA_KEY) == "low", "Aurora 自己的键必须写入"
        assert "comeback_nudge" in (
            row.explicit.get(_SUGGESTION_KEY) or {}
        ), f"P-03 mute 键被旧快照整列覆写蒸发：explicit={row.explicit!r}"
    finally:
        await engine_a.dispose()
        await engine_b.dispose()


@pytest.mark.asyncio
async def test_p03_write_does_not_erase_aurora_pref_on_stale_snapshot(tmp_path) -> None:
    """交错方向 B（镜像）：Aurora 先提交，P-03 持旧快照写 mute → aurora 键不得蒸发。"""
    engine_a, maker_a, engine_b, maker_b = _two_makers(tmp_path)
    try:
        user_id = await _seed(engine_a, maker_a)

        # A（P-03）先持有行快照
        session_a_hold = maker_a()
        # 同上：强引用握住快照（identity map 弱引用，bare expression 会被回收）
        held_a = (
            (
                await session_a_hold.execute(
                    select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)
                )
            )
            .scalars()
            .one()
        )
        assert held_a is not None

        # B（Aurora）提交 stimulation mode
        async with maker_b() as session_b:
            from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService

            await AuroraUserPreferencesService(session_b).update(user_id, {_AURORA_KEY: "low"})

        # A（P-03）持旧快照写 mute —— 走真实服务代码
        # （hold 会话首查已 autobegin，直接调用即可）
        from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

        await ProactiveSuggestionFeedbackService(session_a_hold).record_mute(user_id, "comeback_nudge")
        await session_a_hold.close()

        async with maker_a() as verify:
            row = (
                (await verify.execute(select(UserPreferencesCenter).where(UserPreferencesCenter.user_id == user_id)))
                .scalars()
                .one()
            )
        assert "comeback_nudge" in (row.explicit.get(_SUGGESTION_KEY) or {}), "P-03 自己的键必须写入"
        assert row.explicit.get(_AURORA_KEY) == "low", f"Aurora 偏好键被旧快照整列覆写蒸发：explicit={row.explicit!r}"
    finally:
        await engine_a.dispose()
        await engine_b.dispose()


class _RecordingSession:
    """只记录 execute 收到的语句的 session 替身（机制钉：读行须带 FOR UPDATE）。"""

    def __init__(self) -> None:
        self.statements: list = []

    async def execute(self, stmt):
        self.statements.append(stmt)

        class _Result:
            def scalar_one_or_none(self):
                return None

        return _Result()

    async def rollback(self) -> None:
        return None

    async def commit(self) -> None:
        return None

    def add(self, _obj) -> None:
        return None


def _has_for_update(stmt) -> bool:
    return getattr(stmt, "_for_update_arg", None) is not None


@pytest.mark.asyncio
async def test_row_lock_clause_present_on_both_writers():
    """机制钉：两个写方的行读取必须带 FOR UPDATE（PG 行锁；sqlite 忽略无害）。"""
    from sqlalchemy.dialects import postgresql

    from app.aurora.runtime_v1.user_preferences import AuroraUserPreferencesService
    from app.services.proactive_suggestion_service import ProactiveSuggestionFeedbackService

    user_id = uuid4()

    p03_session = _RecordingSession()
    await ProactiveSuggestionFeedbackService(p03_session).record_mute(user_id, "comeback_nudge")  # type: ignore[arg-type]
    assert p03_session.statements, "P-03 写路径应发出 SELECT"
    assert _has_for_update(p03_session.statements[0]), "P-03 写侧读行缺 FOR UPDATE 行锁子句"

    aurora_session = _RecordingSession()
    await AuroraUserPreferencesService(aurora_session).update(user_id, {_AURORA_KEY: "low"})  # type: ignore[arg-type]
    assert aurora_session.statements, "Aurora 写路径应发出 SELECT"
    assert _has_for_update(aurora_session.statements[0]), "Aurora 写侧读行缺 FOR UPDATE 行锁子句"

    compiled = str(aurora_session.statements[0].compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled.upper(), f"PG 方言下应渲染 FOR UPDATE，实际: {compiled}"
