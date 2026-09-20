"""GET /api/v1/insights/understanding-dimensions API 测试（D-03）。

覆盖：可解释 summary 结构（无单一百分比）、unknown 维不给出值、漂移红维
value 扣发、coverage 校准 map 应用、无行用户的诚实空态。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.api.v1.insights import router as insights_router
from app.models.understanding_dimensions import UnderstandingCalibrationRun, UnderstandingDimensionDaily


class _FakeUser:
    def __init__(self, user_id) -> None:
        self.id = user_id


def _build_app(session: AsyncSession, user_id) -> FastAPI:
    app = FastAPI()
    app.include_router(insights_router, prefix="/insights")

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = lambda: _FakeUser(user_id)
    return app


async def _seed_row(session: AsyncSession, user_id, *, drift_correctness: bool = False, with_calib: bool = True):
    dimensions = {
        "coverage": {
            "status": "ok",
            "value": 1.0,
            "samples": 5,
            "detail": {"top_missing": ["relevant_memory_present"]},
        },
        "correctness": {"status": "ok", "value": 1.0 if not drift_correctness else 0.1, "samples": 7, "detail": {}},
        "scope_precision": {
            "status": "unknown",
            "value": None,
            "samples": 0,
            "detail": {"unknown_reason": "scope feedback channel dark in window"},
        },
        "freshness": {
            "status": "unknown",
            "value": None,
            "samples": 0,
            "detail": {"unknown_reason": "no state-changing corrections in window"},
        },
        "utility": {
            "status": "unknown",
            "value": None,
            "samples": 0,
            "detail": {"unknown_reason": "decisive feedback 0 < 3"},
        },
    }
    session.add(
        UnderstandingDimensionDaily(
            user_id=user_id,
            metric_date=datetime.utcnow().date(),
            dimensions=dimensions,
            anchors={"coverage": {"anchor_value": 0.9, "anchor_samples": 10}},
            window_days=7,
        )
    )
    if with_calib:
        drift = {
            "correctness": {
                "status": "drift" if drift_correctness else "aligned",
                "recent_error": 0.9,
                "baseline_error": 0.0,
            }
        }
        session.add(
            UnderstandingCalibrationRun(
                user_id=user_id,
                ran_at=datetime.utcnow(),
                window_days=14,
                coverage_map={"a": 1.0, "b": -0.25, "applied": True, "mae_before": 0.3, "mae_after": 0.05},
                drift_report=drift,
                overall_status="red" if drift_correctness else "green",
            )
        )
    await session.commit()


@pytest.mark.asyncio
async def test_summary_structure_and_unknown_semantics(db_session):
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    await _seed_row(db_session, user_id)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-dimensions")

    assert resp.status_code == 200
    body = resp.json()["data"]
    assert set(body["dimensions"]) == {"coverage", "correctness", "scope_precision", "freshness", "utility"}
    # unknown 维如实 unknown，不给值
    for dim in ("scope_precision", "freshness", "utility"):
        entry = body["dimensions"][dim]
        assert entry["status"] == "unknown"
        assert entry["value"] is None
        assert entry["note"]
    # coverage 有值且经校准 map 重标定：1.0 → 1.0*1.0-0.25 = 0.75
    cov = body["dimensions"]["coverage"]
    assert cov["value"] == pytest.approx(0.75)
    assert cov["band"] == "sufficient"
    assert cov["top_missing"] == ["relevant_memory_present"]
    # overall 无单一百分比，只有证据面计数
    assert body["overall"]["ok_dimensions"] == 2
    assert body["overall"]["unknown_dimensions"] == 3
    assert body["overall"]["evidence"] == "insufficient_evidence"
    assert "calibration" in body
    assert body["calibration"]["coverage_map"]["applied"] is True


@pytest.mark.asyncio
async def test_drifted_dimension_withholds_value(db_session):
    """卡面 work3：漂移红的维度不显示未校准值。"""
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    await _seed_row(db_session, user_id, drift_correctness=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-dimensions")

    assert resp.status_code == 200
    entry = resp.json()["data"]["dimensions"]["correctness"]
    assert entry["value"] is None
    assert "calibration_drift" in entry["note"]
    # 漂移维不计入 ok
    assert resp.json()["data"]["overall"]["ok_dimensions"] == 1


@pytest.mark.asyncio
async def test_no_rows_returns_honest_empty(db_session):
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-dimensions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] is None
    assert "no understanding rows" in body["meta"]["note"]


@pytest.mark.asyncio
async def test_legacy_understanding_depth_endpoint_untouched(db_session):
    """回归面：既有 /understanding-depth 端点行为不变（D-03 不动旧基线）。"""
    user_id = uuid4()
    app = _build_app(db_session, user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/insights/understanding-depth", params={"days": 7})
    assert resp.status_code == 200
    assert resp.json()["meta"]["definition_version"] == "v0.1"
