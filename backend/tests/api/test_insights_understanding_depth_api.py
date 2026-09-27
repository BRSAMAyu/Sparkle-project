"""GET /api/v1/insights/understanding-depth API 测试。

覆盖：趋势返回结构（data+meta.latest）、7/30 天窗口语义、days 参数校验、
未活动用户返回空趋势。DB 走 conftest sqlite 内存基座（主库只读纪律），
HTTP 用 httpx ASGITransport（与 db_session 同一事件循环）。
"""

from __future__ import annotations

import datetime as dt
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.insights import router as insights_router
from app.models.understanding_depth import UnderstandingDepthDaily

# V3-FIX-321 族C 冻结钟纪律：锚定当日 12:00 UTC（上海 20:00，UTC 日=用户本地日
# 同日；正午锚使 ±小时偏移永不跨日界）。消费面 get_trend 的窗口端点走
# understanding_depth_metric_service.datetime.utcnow()，冻结后种子/窗口同钟，
# 宿主机时钟/时区全脱钩；断言与期望值零改动。
FROZEN_NOW = dt.datetime(2026, 9, 25, 12, 0)
FROZEN_TODAY = FROZEN_NOW.date()


@pytest.fixture
def frozen_clock(monkeypatch):
    class _FrozenDatetime(dt.datetime):
        @classmethod
        def utcnow(cls) -> dt.datetime:
            return FROZEN_NOW

    monkeypatch.setattr("app.services.understanding_depth_metric_service.datetime", _FrozenDatetime)


class _FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _build_app(session: AsyncSession, user_id) -> FastAPI:
    app = FastAPI()
    # 主应用挂载：api_router.include_router(insights.router, prefix="/insights")
    app.include_router(insights_router, prefix="/insights")

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser(user_id)
    return app


async def _seed(session: AsyncSession, user_id, days: int = 3) -> None:
    base = FROZEN_TODAY
    for offset in range(days):
        session.add(
            UnderstandingDepthDaily(
                user_id=user_id,
                metric_date=base - dt.timedelta(days=offset),
                score=round(0.1 + 0.1 * offset, 2),
                components={"memory_injection": 0.2 * offset, "personalization": 0.5},
                context_pack_runs=offset,
                chat_turns=offset + 1,
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_understanding_depth_returns_trend_with_latest(db_session, frozen_clock):
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    await _seed(db_session, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-depth", params={"days": 7})

    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["window_days"] == 7
    assert body["meta"]["definition_version"] == "v0.1"
    assert body["meta"]["total"] == 3
    assert len(body["data"]) == 3
    assert body["meta"]["latest"]["score"] == 0.1  # 升序 → latest 是今天（种子 offset=0）
    assert [row["score"] for row in body["data"]] == [0.3, 0.2, 0.1]  # 升序：旧→新
    first = body["data"][0]
    assert {"date", "score", "components", "context_pack_runs", "chat_turns"} <= set(first)


@pytest.mark.asyncio
async def test_understanding_depth_30_day_window_mapping(db_session, frozen_clock):
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    await _seed(db_session, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp30 = await ac.get("/insights/understanding-depth", params={"days": 30})
        resp_default = await ac.get("/insights/understanding-depth")

    assert resp30.status_code == 200
    assert resp30.json()["meta"]["window_days"] == 30
    assert resp_default.json()["meta"]["window_days"] == 7  # 缺省 7 天


@pytest.mark.asyncio
async def test_understanding_depth_rejects_out_of_range_days(db_session):
    app = _build_app(db_session, uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.get("/insights/understanding-depth", params={"days": 3})).status_code == 422
        assert (await ac.get("/insights/understanding-depth", params={"days": 60})).status_code == 422


@pytest.mark.asyncio
async def test_understanding_depth_empty_trend_for_new_user(db_session, frozen_clock):
    app = _build_app(db_session, uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-depth", params={"days": 30})
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["meta"]["latest"] is None and body["meta"]["total"] == 0
