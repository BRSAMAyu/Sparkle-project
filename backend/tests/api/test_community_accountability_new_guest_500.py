"""N-5 回归：/experience/community-accountability 对新访客 500。

现象（Android round-2 实测 + 网关日志 23:12:48/23:14:19）：
新注册访客（guest 种子数据带 1 条 ACTIVE accountability partnership）
请求该接口稳定 500，detail =
``can't compare offset-naive and offset-aware datetimes``。

根因：Alembic 线上 schema 中 ``accountability_checkin.created_at`` 为
``timestamptz``（timestamp with time zone），而 SQLAlchemy 模型
``BaseModel.created_at`` 声明为 naive ``DateTime``；asyncpg 对 timestamptz
列返回 **tz-aware** datetime。endpoint 内
``last_partner_checkin < now - timedelta(...)`` 把 aware 值与 naive 的
``_utcnow()`` 直接比较 → TypeError → 500。
（无 partnership 的用户不进循环，因此旧的 fieldtester20 不触发，掩盖了该 bug。）

修复：比较前把 DB 返回的 datetime 归一化为 naive UTC（与代码库 canonical
时间形态一致，见 app/core/time_utils.utcnow）。

本测试用脚本化 FakeDB 模拟 asyncpg 的 aware 返回值，不依赖真实数据库。
"""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.models.accountability import AccountabilityStatus
from app.models.user import User

_COMMUNITY_ROUTER = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "api"
    / "v1"
    / "experience"
    / "community_router.py"
)


def _load_router():
    spec = importlib.util.spec_from_file_location(
        "app.api.v1.experience_closeout_community_router_test",
        _COMMUNITY_ROUTER,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _make_user() -> User:
    suffix = uuid4().hex[:8]
    return User(
        username=f"n5_guest_{suffix}",
        email=f"n5_guest_{suffix}@example.com",
        hashed_password="hashed",
        registration_source="guest",
        is_active=True,
    )


class _FakeResult:
    """按调用脚本化返回的 SQLAlchemy Result 桩。"""

    def __init__(
        self,
        *,
        scalars_all=None,
        scalar_one_or_none=None,
        scalar_one=None,
    ) -> None:
        self._scalars_all = scalars_all if scalars_all is not None else []
        self._scalar_one_or_none = scalar_one_or_none
        self._scalar_one = scalar_one

    class _Scalars:
        def __init__(self, items) -> None:
            self._items = items

        def all(self):
            return list(self._items)

    def scalars(self):
        return _FakeResult._Scalars(self._scalars_all)

    def scalar_one_or_none(self):
        return self._scalar_one_or_none

    def scalar_one(self):
        assert self._scalar_one is not None, "unexpected scalar_one() call"
        return self._scalar_one


class _FakeDB:
    """按顺序弹出脚本的 AsyncSession 桩。"""

    def __init__(self, results) -> None:
        self._results = list(results)

    async def execute(self, _query):  # noqa: ANN001
        assert self._results, "more queries than scripted results"
        return self._results.pop(0)


def _build_client() -> TestClient:
    module = _load_router()
    app = FastAPI()
    app.include_router(module.router)

    me = _make_user()
    partner_user = SimpleNamespace(nickname="伙伴甲", full_name=None, username="partner_a")
    other_id = uuid4()
    partnership = SimpleNamespace(
        id=uuid4(),
        initiator_id=other_id,
        partner_id=me.id,
        status=AccountabilityStatus.ACTIVE,
        initiator_goal="顺利通过期末考试",
        partner_goal="陪我复盘错题",
        check_in_days=3,
        updated_at=datetime(2026, 9, 18),
        initiator=partner_user,
        partner=me,
    )

    # asyncpg 对 timestamptz 列返回 tz-aware datetime —— 复现线上形态。
    aware_last_checkin = datetime.now(UTC).replace(tzinfo=UTC)

    fake_db = _FakeDB(
        [
            _FakeResult(scalars_all=[partnership]),  # partnerships 查询
            _FakeResult(scalars_all=[]),  # pending commitments（episodic）
            _FakeResult(scalar_one_or_none=None),  # partner 今日打卡
            _FakeResult(scalar_one_or_none=None),  # 我的今日打卡
            _FakeResult(scalar_one_or_none=aware_last_checkin),  # 最近一次打卡（timestamptz → aware）
            _FakeResult(scalar_one=2),  # 周打卡计数
            _FakeResult(scalar_one_or_none=None),  # my_commitments 兜底分支：今日打卡
        ]
    )

    async def _override_db():
        yield fake_db

    async def _override_user():
        return me

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    return TestClient(app)


def test_new_guest_with_seeded_partnership_gets_empty_ok_not_500():
    client = _build_client()
    response = client.get("/experience/community-accountability")

    assert response.status_code == 200, (
        f"期望 200，实际 {response.status_code}: {response.text[:300]}"
    )
    payload = response.json()
    # 无 pending commitment 时回退用 ACTIVE partnership 生成 1 张承诺卡；
    # 当前用户是 partner 侧，goal 取 partner_goal（见 _my_goal）
    assert len(payload["my_commitments"]) == 1
    assert payload["my_commitments"][0]["summary"] == "陪我复盘错题"
    # 伙伴今日未打卡 → 出现在 helpable；最近打卡在 2 天冷却阈值内/外由
    # 数据决定，这里只断言结构完整。
    assert isinstance(payload["squad_risks"], list)
    assert isinstance(payload["partner_progress"], list)
    assert len(payload["partner_progress"]) == 1


def test_aware_last_checkin_is_compared_against_naive_now_safely():
    """直接钉住根因：aware 值参与冷却判断不再抛 TypeError。"""
    module = _load_router()
    aware = datetime.now(UTC).replace(tzinfo=UTC)
    naive_now = datetime(2026, 9, 18, 12, 0, 0)

    normalized = module._as_naive_utc(aware)
    # 不抛 "can't compare offset-naive and offset-aware datetimes"
    assert (normalized < naive_now) or (normalized >= naive_now)
    assert normalized.tzinfo is None

    # naive 值原样通过
    naive = datetime(2026, 9, 18, 11, 0, 0)
    assert module._as_naive_utc(naive) == naive

    # None 原样通过（冷却逻辑依赖 None 语义）
    assert module._as_naive_utc(None) is None

    # aware 归一化保留真实时刻（UTC 换算，不是简单剥 tzinfo）
    aware_cst = datetime(2026, 9, 18, 20, 0, 0, tzinfo=timezone(timedelta(hours=8)))
    assert module._as_naive_utc(aware_cst) == naive_now
