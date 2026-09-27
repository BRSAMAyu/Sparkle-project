"""WT651-D04 首批如实化守卫（V3-FIX-346 / V3-FIX-347）。

V3-FIX-346：``GET /stats/overview`` 的 ``streak_days`` 曾以
``current_user.flame_level`` 冒充连续学习天数（原行自注
``# Using flame_level as proxy``）——以无关字段冒充统计值违反
「不以 Mock 冒充统计结果」硬约束。真实连续天数由
``FocusService._calculate_current_streak``（``/focus/stats/*`` 的
``streak_days``）提供。裁决=删除冒充字段（该端点 mobile 零消费面）。

V3-FIX-347：``/predictive/engagement`` 与 ``/predictive/difficulty/{topic_id}``
曾在响应中硬编码 ``typical_weekdays/typical_hours/prediction_factors/
difficulty_factors`` 恒空列表，而 docstring 宣称返回「典型活跃日/典型活跃
时段/难度因素分析」——宣称面大于接线面（全仓零消费方）。裁决=删除未接线
承诺键并同步 docstring。
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.api.v1 import predictive_analytics as pa
from app.api.v1.statistics import get_stats_overview
from app.models.user import User
from app.services.predictive_service import DifficultyPrediction, EngagementForecast


async def test_overview_has_no_flame_proxy_streak_days(db_session):
    user = User(
        username=f"wt651-{uuid4().hex[:8]}",
        email=f"wt651-{uuid4().hex[:8]}@test.local",
        hashed_password="x",
        flame_level=7,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    result = await get_stats_overview(current_user=user, db=db_session)

    assert "streak_days" not in result, "streak_days 不得再以 flame_level 冒充"
    # flame 真实字段保留（值来自 User 本体，非代理伪造）
    assert result["flame_level"] == 7


class _StubPredictiveService:
    def __init__(self, db):
        self.db = db

    async def predict_engagement(self, user_id):
        return EngagementForecast(
            next_active_time=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
            confidence=0.5,
            recommended_intervention=None,
            risk_level="low",
        )

    async def predict_difficulty(self, user_id, topic_id):
        return DifficultyPrediction(
            topic_id=topic_id,
            topic_name="t",
            predicted_difficulty=0.4,
            suggested_prerequisites=[],
            estimated_time_hours=2.0,
        )


async def test_engagement_response_has_no_unwired_placeholder_keys(monkeypatch):
    monkeypatch.setattr(pa, "PredictiveService", _StubPredictiveService)
    user = User(id=uuid4())
    payload = await pa.get_engagement_forecast(current_user=user, db=None)

    assert payload["status"] == "success"
    for key in ("typical_weekdays", "typical_hours", "prediction_factors"):
        assert key not in payload["data"], f"未接线的承诺键 {key} 不得以空列表冒充"
    assert payload["data"]["dropout_risk"] == "low"


async def test_difficulty_response_has_no_unwired_placeholder_keys(monkeypatch):
    monkeypatch.setattr(pa, "PredictiveService", _StubPredictiveService)
    user = User(id=uuid4())
    topic_id = uuid4()
    payload = await pa.get_difficulty_prediction(topic_id, current_user=user, db=None)

    assert payload["status"] == "success"
    assert "difficulty_factors" not in payload["data"], "未接线的承诺键不得以空列表冒充"
    assert payload["data"]["difficulty_score"] == 0.4
