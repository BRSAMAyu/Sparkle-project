"""V4-U10 · ``/learning-journey`` REST 入口守卫（装配/检验入口/判分提交）。

覆盖：
- 旅程装配直通：服务层视图原样出（HTTP 200 + view + warnings）；
- 对象不存在 / 跨用户 → 404（不泄露存在性，house runs.py 先例）；
- 检验入口：证据不支持 → 200 + ``check_available=False`` + HOLD（不推进）；
- 出题证据门（R1 F-1）：未到检验段 → GET 无 ``view.check`` 题面 + submit 拒判分；
- 判分提交：判分面零答案材料（响应不含 ``answer`` 键或答案文本）。
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1.learning_journey import router as learning_journey_router
from app.db.session import get_db

pytestmark = pytest.mark.asyncio


@pytest.fixture(name="api")
def _api(db_session):
    app = FastAPI()
    app.include_router(learning_journey_router)

    async def _override_get_db():
        yield db_session

    caller = SimpleNamespace(id=None)

    def _override_user():
        return caller

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as test_client:
        test_client.caller = caller  # type: ignore[attr-defined]
        yield test_client


async def test_journey_endpoint_assembles_and_404s_cross_user(db_session, api):
    from tests.services.test_learning_journey_service import _make_task, _make_user

    user = await _make_user(db_session)
    stranger = await _make_user(db_session)
    task = await _make_task(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/learning-journey/tasks/{task.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["reason_code"] == "ok"
    assert body["view"]["goal"]["task_id"] == str(task.id)

    # 反（可失败面）：跨用户按 404 语义，不泄露存在性。
    api.caller.id = stranger.id
    resp = api.get(f"/learning-journey/tasks/{task.id}")
    assert resp.status_code == 404


async def test_check_submit_response_has_no_answer_material(db_session, api):
    from tests.services.test_learning_journey_service import (
        _CHECK_ANSWER,
        _make_task,
        _make_user,
    )

    user = await _make_user(db_session)
    # 独立检验链终点（I07 脚手架 stage=independent_check）→ 判分放行。
    task = await _make_task(
        db_session,
        user,
        guide_json={
            "v4_hybrid_policy": {
                "schema_version": "hybrid_policy.v1",
                "goal_purpose": "mastery",
                "human_required": True,
                "scaffold": {"stage": "independent_check", "hint_level": "none"},
                "independent_check": {
                    "kind": "independent_check",
                    "question": "独立解释：为什么滑动摩擦力与接触面积无关？",
                    "answer": _CHECK_ANSWER,
                },
            }
        },
    )
    api.caller.id = user.id

    resp = api.post(f"/learning-journey/tasks/{task.id}/check/submit", json={"answer": "错误答案"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["graded"] is True
    assert body["view"]["correct"] is False
    # 反（可失败面）：判分面零答案材料。
    assert _CHECK_ANSWER not in body["view"].get("feedback", "")
    assert "answer" not in body["view"]

    # 缺 body 字段 → 422（契约校验面）。
    resp = api.post(f"/learning-journey/tasks/{task.id}/check/submit", json={})
    assert resp.status_code == 422


async def test_check_enter_holds_without_evidence_and_never_serves_question(db_session, api):
    from tests.services.test_learning_journey_service import (
        _make_task,
        _make_user,
    )

    user = await _make_user(db_session)
    node_id = uuid4()
    task = await _make_task(
        db_session,
        user,
        guide_json={
            "v4_hybrid_policy": {
                "schema_version": "hybrid_policy.v1",
                "goal_purpose": "mastery",
                "human_required": True,
                "scaffold": {"stage": "attempt", "hint_level": "full"},
                "independent_check": {
                    "kind": "independent_check",
                    "question": "Q?",
                    "answer": "A",
                },
            }
        },
        node_id=node_id,
    )
    api.caller.id = user.id

    resp = api.post(f"/learning-journey/tasks/{task.id}/check/enter")
    assert resp.status_code == 200
    body = resp.json()
    # 反（可失败面）：无练习证据 → HOLD 暂缓，不出题、不推进脚手架。
    assert body["view"]["check_available"] is False
    assert body["view"]["hold_reason"] == "HOLD.evidence_not_supported"
    assert body["scaffold_persisted"] is False
    assert "question" not in body["view"]


async def test_check_face_and_grading_gated_until_check_stage(db_session, api):
    """R1 F-1 契约面钉死：出题证据门覆盖 GET 读模型与判分面。

    反：stage=example（从未 enter）→ GET 无 ``view.check`` 题面 + submit 拒判分
    （无 correct 裁决）；正：脚手架到检验段后 GET/submit 照常。
    """
    from tests.services.test_learning_journey_service import (
        _CHECK_ANSWER,
        _make_task,
        _make_user,
    )

    user = await _make_user(db_session)

    def _guide(stage: str) -> dict:
        return {
            "v4_hybrid_policy": {
                "schema_version": "hybrid_policy.v1",
                "goal_purpose": "mastery",
                "human_required": True,
                "scaffold": {"stage": stage, "hint_level": "full"},
                "independent_check": {
                    "kind": "independent_check",
                    "question": "独立解释：为什么滑动摩擦力与接触面积无关？",
                    "answer": _CHECK_ANSWER,
                },
            }
        }

    api.caller.id = user.id
    early = await _make_task(db_session, user, guide_json=_guide("example"))

    # 反（可失败面）：GET 读模型不带题面。
    resp = api.get(f"/learning-journey/tasks/{early.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["scaffold"]["stage"] == "example"
    assert body["view"]["check"] is None

    # 反（可失败面）：submit 不判分（正确答案也拿不到 correct=true）。
    resp = api.post(f"/learning-journey/tasks/{early.id}/check/submit", json={"answer": _CHECK_ANSWER})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["graded"] is False
    assert body["view"]["correct"] is None
    assert body["view"]["reason"] == "HOLD.scaffold_not_at_check"
    assert _CHECK_ANSWER not in str(body["view"])

    # 正：脚手架到检验段后（enter_check 写回后的权威位），GET/submit 照常。
    reached = await _make_task(db_session, user, guide_json=_guide("independent_check"))
    resp = api.get(f"/learning-journey/tasks/{reached.id}")
    assert resp.status_code == 200
    assert resp.json()["view"]["check"] == {"question": "独立解释：为什么滑动摩擦力与接触面积无关？"}

    resp = api.post(f"/learning-journey/tasks/{reached.id}/check/submit", json={"answer": _CHECK_ANSWER})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["graded"] is True
    assert body["view"]["correct"] is True
    assert "answer" not in body["view"]
