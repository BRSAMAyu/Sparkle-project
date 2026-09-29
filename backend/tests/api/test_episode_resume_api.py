"""V4-I01 · ``GET /episode-resume/tasks/{task_id}`` REST 入口守卫。

覆盖：
- 组成直通：服务层视图原样出（HTTP 200 + view）；
- 对象不存在 / 跨用户 → 404（不泄露存在性，house runs.py 先例）；
- 无 receipt ref / scheme 不符 → 200 + 类型化 ``context_receipt_missing``
  （不造伪 receipt、不出半真视图）；
- goal 终态 → 200 + ``goal_changed_requires_calibration``（旧计划不强推）。
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.v1.episode_resume import router as episode_resume_router
from app.db.session import get_db
from app.services.episode_resume_service import EpisodeResumeService

pytestmark = pytest.mark.asyncio

_NOW = datetime(2026, 9, 28, 8, 55, 0)
_RECEIPT = "context_selection://csr_i01_api"


@pytest.fixture(name="api")
def _api(db_session):
    app = FastAPI()
    app.include_router(episode_resume_router)

    async def _override_get_db():
        yield db_session

    caller = SimpleNamespace(id=None)  # 由各用例置为真实 user id

    def _override_user():
        return caller

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_user
    with TestClient(app) as test_client:
        test_client.caller = caller  # type: ignore[attr-defined]
        yield test_client


async def test_endpoint_returns_view(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"]["schema_version"] == "episode_resume_view.v1"
    assert body["view"]["task_ref"] == f"task://{task.id}"
    assert body["reason_code"] is None


async def test_endpoint_404_on_missing_and_cross_user(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    owner = await _make_user(db_session, suffix="o")
    outsider = await _make_user(db_session, suffix="x")
    _, task = await _make_episode(db_session, owner)

    # 不存在
    api.caller.id = owner.id
    resp = api.get(f"/episode-resume/tasks/{uuid4()}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 404
    # 跨用户（不泄露存在性）
    api.caller.id = outsider.id
    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 404


async def test_endpoint_missing_receipt_is_typed_not_fatal(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"] is None
    assert body["reason_code"] == "context_receipt_missing"


async def test_endpoint_goal_closed_returns_calibration(db_session, api):
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user, goal_status="cancelled")
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["view"] is None
    assert body["reason_code"] == "goal_changed_requires_calibration"


async def test_service_is_read_only_surface():
    """读模型纪律锚：服务类不暴露任何写方法名（防漂移为第二真值写面）。"""
    write_forbidden = ("save", "create", "update", "delete", "insert", "commit", "upsert", "write")
    methods = [name for name in dir(EpisodeResumeService) if not name.startswith("_")]
    assert methods == ["build_resume_view"]
    assert not any(any(w in name.lower() for w in write_forbidden) for name in methods)


# ---------------------------------------------------------------------------
# FIX-567 · resume_view 角色回执生产（B05 §2：receipt 在 resume view 返回之前）
# ---------------------------------------------------------------------------


async def _resume_receipt_rows(db_session, user_id):
    from app.models.context_selection_receipt import ContextSelectionReceiptRow

    result = await db_session.execute(
        select(ContextSelectionReceiptRow).where(ContextSelectionReceiptRow.user_id == user_id)
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
async def test_endpoint_produces_resume_view_receipt_in_live_mode(db_session, api, monkeypatch):
    """FIX-567 正例：视图成功返回 → ``resume_view`` 角色回执真实产生（角色值+载荷
    字段逐断言）；I06 latest 读面（客户端唯一下发面，角色是 payload 字段值）以此
    角色透传 + 来源验证 join 真源双 resolved。"""
    from app.api.v1.experience_readouts import get_latest_context_receipt
    from app.config import settings
    from app.core.action_command import version_token
    from app.orchestration.context_receipt_assembly import SELECTOR_VERSION_RESUME_VIEW

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "live", raising=False)
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    goal, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    assert resp.json()["view"] is not None

    rows = await _resume_receipt_rows(db_session, user.id)
    assert len(rows) == 1
    row = rows[0]
    # 角色值：U01 消费面 episode_resume_provider 角色门唯一放行值
    assert row.selection_role == "resume_view"
    assert row.schema_version == "context_selection_receipt.v1"
    assert row.receipt_id.startswith("csr_")
    assert row.decision_id is None
    # 载荷：候选 = 视图依据权威（task + goal，selected；无臆造 rejected）
    assert [(c["ref"], c["status"], c["reason_code"]) for c in row.candidates] == [
        (f"task://{task.id}", "selected", None),
        (f"goal://{goal.id}", "selected", None),
    ]
    # input_versions：真实读数锚（版本 token + epoch；policy 未读 → null）
    assert row.input_versions["selector_version"] == SELECTOR_VERSION_RESUME_VIEW
    assert row.input_versions["task_version"] == version_token(task.updated_at)
    assert row.input_versions["goal_version"] == version_token(goal.updated_at)
    assert isinstance(row.input_versions["memory_epoch"], int)
    assert row.input_versions["policy_version"] is None
    assert row.why_now is None
    assert row.budget == {"candidate_scan_limit": 2, "selected_max": 2, "clarifications_used": 0}

    # 下发面：I06 latest 读面把 resume_view 角色回执原样透传（客户端契约形状）
    payload = await get_latest_context_receipt(current_user=user, db=db_session)
    assert payload["mode"] == "live"
    assert payload["receipt"]["selection_role"] == "resume_view"
    assert payload["receipt"]["receipt_id"] == row.receipt_id
    assert payload["receipt"]["schema_version"] == "context_selection_receipt.v1"
    # 来源验证（E4）：task/goal 双 ref join 真源属主 → resolved，不可悬空
    resolutions = {entry["ref"]: entry["resolution"] for entry in payload["source_verification"]}
    assert resolutions == {f"task://{task.id}": "resolved", f"goal://{goal.id}": "resolved"}
    assert payload["resolved_selected_count"] == 2


@pytest.mark.asyncio
async def test_endpoint_off_mode_produces_no_receipt(db_session, api, monkeypatch):
    """反例：mode=off → 零回执落库（V3 路径零变化），视图照常返回。"""
    from app.config import settings

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "off", raising=False)
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    assert resp.json()["view"] is not None
    assert await _resume_receipt_rows(db_session, user.id) == []


@pytest.mark.asyncio
async def test_endpoint_degraded_view_produces_no_receipt(db_session, api, monkeypatch):
    """反例：无选择发生不产生回执（B05 §2）——receipt ref 缺失（视图不出）与
    goal 终态（校准退回，视图不出）均不落 resume_view 回执。"""
    from app.config import settings

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "live", raising=False)
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    _, closed_task = await _make_episode(db_session, user, goal_status="cancelled")
    api.caller.id = user.id

    resp = api.get(f"/episode-resume/tasks/{task.id}")  # 无 ref → context_receipt_missing
    assert resp.status_code == 200
    assert resp.json()["view"] is None
    resp = api.get(f"/episode-resume/tasks/{closed_task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    assert resp.json()["view"] is None
    assert await _resume_receipt_rows(db_session, user.id) == []


@pytest.mark.asyncio
async def test_latest_receipt_flips_to_resume_view_role_after_resume_flow(db_session, api, monkeypatch):
    """角色分流：chat_context 回执在场时，resume 流回执后 latest 翻转为 resume_view
    ——U01 EpisodeResumeStrip 的可见性由角色（而非仅 recency）决定。"""
    from app.config import settings
    from app.core.context_selection_receipt import (
        ContextSelectionReceipt,
        ReceiptBudget,
        ReceiptInputVersions,
        new_receipt_id,
    )
    from app.services.context_selection_receipt_service import latest_receipt, record_receipt

    monkeypatch.setattr(settings, "CONTEXT_SELECTION_RECEIPT_MODE", "live", raising=False)
    from tests.services.test_episode_resume_service import _make_episode, _make_user

    user = await _make_user(db_session)
    _, task = await _make_episode(db_session, user)
    api.caller.id = user.id

    # 前置：chat 面既有生产链落一条 chat_context 角色回执（唯一历史生产者）
    chat_receipt = ContextSelectionReceipt(
        receipt_id=new_receipt_id(),
        selection_role="chat_context",
        input_versions=ReceiptInputVersions(selector_version="context_pack.v4-i06.v1"),
        candidates=[],
        budget=ReceiptBudget(candidate_scan_limit=0, selected_max=0),
    )
    assert await record_receipt(db_session, user_id=user.id, receipt=chat_receipt) is not None

    loaded, _ = await latest_receipt(db_session, user.id)
    assert loaded is not None and loaded.selection_role == "chat_context"  # 修复前恒此态

    resp = api.get(f"/episode-resume/tasks/{task.id}", params={"context_receipt_ref": _RECEIPT})
    assert resp.status_code == 200
    assert resp.json()["view"] is not None

    loaded, _ = await latest_receipt(db_session, user.id)
    assert loaded is not None
    assert loaded.selection_role == "resume_view"  # 修复后 latest 翻转（latest 不分角色，客户端按角色门消费）
    assert loaded.input_versions.selector_version != "context_pack.v4-i06.v1"
