from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import get_current_user
from app.api.v1.plans import router as plans_router
from app.db.session import get_db
from app.models.plan import Plan, PlanPriority, PlanStage, PlanType
from app.models.plan_state import PlanState, PlanStateStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import PushPreference, User


@pytest.fixture
def plans_client(db_session):
    app = FastAPI()
    app.include_router(plans_router, prefix="/plans")

    state = {"current_user": None}

    async def _override_get_db():
        yield db_session

    def _override_get_current_user():
        return state["current_user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as client:
        yield client, state


@pytest.mark.asyncio
async def test_growth_archive_restore_round_trip_does_not_raise(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_growth_user",
        email="plan_growth_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="长期计划",
        type=PlanType.GROWTH,
        description="测试成长计划归档与恢复",
        plan_stage=PlanStage.REVIEW,
        target_date=date(2026, 7, 1),
        daily_available_minutes=45,
        total_estimated_hours=40,
        subject="系统设计",
        mastery_level=0.4,
        progress=0.6,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
        )
    )
    await db_session.commit()
    await db_session.refresh(plan)
    state["current_user"] = user

    archive_response = client.post(f"/plans/{plan.id}/archive")
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == PlanStateStatus.ARCHIVED.value

    await db_session.refresh(plan)
    assert plan.is_active is False

    restore_response = client.post(f"/plans/{plan.id}/restore")
    assert restore_response.status_code == 200
    assert restore_response.json()["status"] == PlanStateStatus.ACTIVE.value

    await db_session.refresh(plan)
    assert plan.is_active is True


@pytest.mark.asyncio
async def test_plan_list_and_detail_include_mobile_required_fields(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_contract_user",
        email="plan_contract_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="成长计划契约",
        type=PlanType.GROWTH,
        description="检查移动端依赖字段",
        plan_stage=PlanStage.DAILY,
        target_date=date(2026, 8, 1),
        daily_available_minutes=50,
        total_estimated_hours=60,
        subject="分布式系统",
        mastery_level=0.3,
        progress=0.2,
        is_active=True,
        priority=PlanPriority.NORMAL,
        source="learning_path",
        source_metadata={"target_node_id": "node-1"},
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="任务 1",
            type=TaskType.LEARNING,
            tags=["plan"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            priority=2,
        )
    )
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 1, "total": 4, "avg_completion_rate": 0.25},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    list_response = client.get("/plans")
    assert list_response.status_code == 200
    item = list_response.json()["data"][0]
    for required_key in (
        "user_id",
        "daily_available_minutes",
        "updated_at",
        "plan_stage",
        "source",
        "source_metadata",
        "health_score",
        "health_status",
    ):
        assert required_key in item
    assert item["health_score"] is not None

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["health_score"] is not None
    assert detail["health_status"] in {"healthy", "warning", "critical"}
    assert detail["tasks"] is not None
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["plan_id"] == str(plan.id)


@pytest.mark.asyncio
async def test_plan_today_exposes_compressed_recovery_task(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_today_compressed_user",
        email="plan_today_compressed_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="7天计网冲刺",
        type=PlanType.SPRINT,
        description='{"strategy": {"total_days": 7}}',
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=3),
        daily_available_minutes=120,
        total_estimated_hours=14,
        subject="计算机网络",
        mastery_level=0.3,
        progress=0.3,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()

    reason = "前一天完成率只有 30%，低于 50%，而距离考试只剩 5 天；所以 Day 5 自动压缩为保底版。"
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="Day 5 · 压缩保底 - TCP 拥塞控制",
            type=TaskType.LEARNING,
            tags=["day:5", "compressed_recovery"],
            estimated_minutes=35,
            difficulty=1,
            energy_cost=1,
            status=TaskStatus.PENDING,
            priority=2,
            order_index=5000,
            guide_json={
                "compressed": True,
                "compression_reason": reason,
                "task_kind": "compressed_recovery",
                "daily_spec": {"day": 5, "compressed": True},
            },
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}/today")

    assert response.status_code == 200
    payload = response.json()
    assert payload["day"] == 5
    assert payload["compressed"] is True
    assert payload["compression_reason"] == reason
    assert payload["tasks"][0]["compressed"] is True
    assert payload["tasks"][0]["compression_reason"] == reason


# ---------------------------------------------------------------------------
# TOUR 回归钉：直创路径重复 sprint goal（同 user+subject+target_date 的 active
# sprint 命中 uq_plans_user_sprint_goal_active）此前裸 500 IntegrityError——
# intake 路径已在 INTAKE-IDX 收敛，直创 handler 漏了同款关闸（v3-output/TOUR
# 活栈实证）。归一 409 SPRINT_GOAL_DUPLICATE。
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_duplicate_active_sprint_goal_direct_create_returns_409(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="plan_dup_sprint_user",
        email="plan_dup_sprint_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.commit()
    state["current_user"] = user

    target = date.today() + timedelta(days=5)
    body = {
        "name": "直创冲刺计划",
        "type": "sprint",
        "subject": "直创科目",
        "target_date": target.isoformat(),
        "daily_available_minutes": 60,
    }
    first = client.post("/plans", json=body)
    assert first.status_code == 201, first.text

    second = client.post("/plans", json={**body, "name": "直创冲刺计划二"})
    assert second.status_code == 409, second.text
    detail = second.json().get("detail")
    assert isinstance(detail, dict) and detail.get("error_code") == "SPRINT_GOAL_DUPLICATE"


# ---------------------------------------------------------------------------
# WT313 · comeback 引擎侧重校准（wt303 J-07 交接的 C 线卡）
#
# 三缺陷复现钉（main 基线上全部红）：
#   缺陷 1/2 — `_build_day_highlights` 恒推 Day 1 且不感知日期
#     （plans.py:342 `highlight_day = 1 if day_groups.get(1) else min(day_groups)`），
#     回归用户离开 N 天回来看到的重点永远是第一天、文案永远「今天先做好…」。
#   缺陷 3 — health `recommended_action:"replan"` 有标签无执行端点
#     （POST /plans/{id}/replan 在 main 上 404）。
#   缺陷 4 — health 无「离开」维度：days_since_last_activity 字段缺失，
#     mobile 的 staleness 判定（kPlanComebackStaleDays=3）没有服务端真源可选依据。
# ---------------------------------------------------------------------------


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# wt559 · UTC 钟对齐（V3-FIX-233/250/251 既有测试收口）：产品「今天」已切
# 用户本地日（PushPreference.timezone 标量直查，缺省 Asia/Shanghai）。测试
# 若继续用宿主机 date.today() 播种/推导，UTC 宿主钟下与用户本地日错位一天
# （CI run 36253679384 attempt#2 六红层）。沿双冻结钟族判例
# （tests/unit/test_task_snooze_due_date_local_day.py）：冻结服务器 UTC 钟
# 到日界已跨的位置——
#   FROZEN_UTC_NOW = 2026-09-25 20:00 naive UTC → 上海本地 2026-09-26 04:00，
#   与 UTC 宿主日 09-25 可区分；用户显式钉 Asia/Shanghai，产品「今天」恒为
#   USER_LOCAL_TODAY = 09-26，期望值一律按 09-26 手工推导，与宿主机 TZ 无关。
# ---------------------------------------------------------------------------
FROZEN_UTC_NOW = datetime(2026, 9, 25, 20, 0)
USER_LOCAL_TODAY = date(2026, 9, 26)  # FROZEN_UTC_NOW + 8h 落在上海 09-26 日界


def _pin_shanghai_user_local_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    """冻结 plans 模块的 utcnow（_user_local_today 的唯一时刻来源）。"""
    monkeypatch.setattr("app.api.v1.plans.utcnow", lambda: FROZEN_UTC_NOW, raising=False)


async def _make_comeback_plan(
    db_session,
    *,
    username: str,
    description: str,
    target_date: date | None,
    created_days_ago: int,
    plan_type: PlanType = PlanType.SPRINT,
    plan_stage: PlanStage = PlanStage.SPRINT,
):
    """回归者计划：开始日钉在 N 天前（日期感知以 plan 开始日 + 今天推当天日次）。"""
    user = User(username=username, email=f"{username}@example.com", hashed_password="hashed")
    db_session.add(user)
    await db_session.flush()
    plan = Plan(
        user_id=user.id,
        name="7天计网冲刺",
        type=plan_type,
        description=description,
        plan_stage=plan_stage,
        target_date=target_date,
        daily_available_minutes=120,
        total_estimated_hours=14,
        subject="计算机网络",
        progress=0.0,
        is_active=True,
        priority=PlanPriority.HIGH,
    )
    db_session.add(plan)
    await db_session.flush()
    started_at = _utcnow_naive() - timedelta(days=created_days_ago)
    plan.created_at = started_at
    plan.updated_at = started_at
    await db_session.commit()
    await db_session.refresh(plan)
    return user, plan


def _add_day_task(db_session, user, plan, *, day: int, completed: bool = False, completed_days_ago: int = 0) -> None:
    task = Task(
        user_id=user.id,
        plan_id=plan.id,
        title=f"Day {day} · 计网任务",
        type=TaskType.LEARNING,
        tags=[f"day:{day}"],
        estimated_minutes=35,
        difficulty=2,
        energy_cost=2,
        status=TaskStatus.COMPLETED if completed else TaskStatus.PENDING,
        priority=2,
        order_index=day * 1000,
    )
    if completed:
        task.updated_at = _utcnow_naive() - timedelta(days=completed_days_ago)
    db_session.add(task)


@pytest.mark.asyncio
async def test_day_highlights_follow_plan_start_date_not_day_one(db_session, plans_client, monkeypatch):
    """缺陷 1 复现钉：计划 5 天前开始、7 天跨度（剩 2 天），任务在 Day 1/2/6。

    当天日次按「开始日 + 今天」推 = Day 6，重点必须跟日期走；main 上恒推 Day 1 → 红。

    wt559 UTC 钟对齐：冻结服务器 UTC 钟 09-25 20:00Z（上海本地 09-26 04:00），
    用户显式钉 Asia/Shanghai → 产品「今天」= 09-26。期望推导：
    target = 09-26 + 2 = 09-28（剩 2 天）；initial_days = 7（strategy.total_days）
    → today_day = 7 − 2 + 1 = 6（派生日落在任务网格内 → today 档）。
    """
    _pin_shanghai_user_local_clock(monkeypatch)
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_dateaware_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=USER_LOCAL_TODAY + timedelta(days=2),  # 09-28：剩 2 天
        created_days_ago=5,
    )
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))
    for day in (1, 2, 6):
        _add_day_task(db_session, user, plan, day=day)
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}")
    assert response.status_code == 200
    highlights = response.json()["day_highlights"]
    assert highlights is not None
    assert highlights["day"] == 6, f"expected derived Day 6, got {highlights['day']}"
    assert highlights["degraded"] is False
    assert highlights["today_day"] == 6
    assert "今天" in highlights["recommendation"]
    assert all("day:6" in task.get("tags", []) for task in highlights["tasks"])


@pytest.mark.asyncio
async def test_day_highlights_resume_first_pending_day_when_today_done(db_session, plans_client, monkeypatch):
    """诚实降级 A：派生日（Day 6）任务已全部完成、Day 5 仍未完成。

    焦点应「接上」第一个未完成日 Day 5，degraded=True，文案不得冒充「今天」；
    main 上恒推 Day 1 且无 degraded/today_day 字段 → 红。

    wt559 UTC 钟对齐：同上冻结 09-25 20:00Z + 显式 Asia/Shanghai →
    「今天」= 09-26；target = 09-26 + 2 = 09-28 → today_day = 7 − 2 + 1 = 6，
    Day 6 全完成 → 降级接 Day 5。
    """
    _pin_shanghai_user_local_clock(monkeypatch)
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_resume_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=USER_LOCAL_TODAY + timedelta(days=2),  # 09-28：剩 2 天
        created_days_ago=5,
    )
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))
    _add_day_task(db_session, user, plan, day=5)
    _add_day_task(db_session, user, plan, day=6, completed=True, completed_days_ago=1)
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}")
    assert response.status_code == 200
    highlights = response.json()["day_highlights"]
    assert highlights is not None
    assert highlights["day"] == 5
    assert highlights["degraded"] is True
    assert highlights["today_day"] == 6
    assert "今天先" not in highlights["recommendation"]
    assert all("day:5" in task.get("tags", []) for task in highlights["tasks"])


@pytest.mark.asyncio
async def test_day_highlights_all_completed_report_completion_honestly(db_session, plans_client):
    """诚实降级 B：全部任务已完成 → 呈现完成事实，不冒充「今天先做好…」。

    main 上兜底 Day 1 + 「今天先做好这 1 件事」→ 红。
    """
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_done_user",
        description="测试全部完成后的诚实降级",
        target_date=None,
        created_days_ago=9,
        plan_type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
    )
    _add_day_task(db_session, user, plan, day=1, completed=True, completed_days_ago=2)
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}")
    assert response.status_code == 200
    highlights = response.json()["day_highlights"]
    assert highlights is not None
    assert highlights["degraded"] is True
    assert "今天先" not in highlights["recommendation"]
    assert "完成" in highlights["recommendation"]


@pytest.mark.asyncio
async def test_replan_reanchors_expired_plan_target(db_session, plans_client, monkeypatch):
    """缺陷 3 复现钉：超期计划的 replan 执行端点。main 上 POST /plans/{id}/replan 404。

    语义 = 基于现状重校准：未完成日 1..7 全未完成 → 7 天跨度，
    重锚 target = 今天 + 7，落 last_replan 回执进 source_metadata，
    不删任务、不重建计划。

    wt559 UTC 钟对齐：冻结 09-25 20:00Z + 显式 Asia/Shanghai → replan 的
    「今天」= 09-26（V3-FIX-250 replan 写侧同源）。期望推导：
    previous = 09-26 − 4 = 09-22（< 今天，判定超期）；未完成日 1..7 跨度 7
    → new_target = 09-26 + 7 = 10-03；days_shifted = 10-03 − 09-22 = 11。
    """
    _pin_shanghai_user_local_clock(monkeypatch)
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_replan_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=USER_LOCAL_TODAY - timedelta(days=4),  # 09-22：已超期
        created_days_ago=5,
    )
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))
    for day in (1, 2, 3, 4, 5, 6, 7):
        _add_day_task(db_session, user, plan, day=day)
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{plan.id}/replan")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["replanned"] is True
    previous_target = USER_LOCAL_TODAY - timedelta(days=4)  # 09-22
    expected_target = USER_LOCAL_TODAY + timedelta(days=7)  # 09-26 + 7 = 10-03
    assert date.fromisoformat(payload["new_target_date"]) == expected_target
    assert date.fromisoformat(payload["previous_target_date"]) == previous_target
    assert payload["days_shifted"] == (expected_target - previous_target).days  # 11

    await db_session.refresh(plan)
    assert plan.target_date == expected_target
    # 任务不被删库重来：7 天任务全数保留
    task_result = await db_session.execute(select(Task).where(Task.plan_id == plan.id))
    assert len(list(task_result.scalars().all())) == 7
    receipt = (plan.source_metadata or {}).get("last_replan")
    assert receipt is not None
    assert receipt["new_target_date"] == expected_target.isoformat()
    assert receipt["previous_target_date"] == previous_target.isoformat()


@pytest.mark.asyncio
async def test_replan_is_idempotent_noop_when_target_still_valid(db_session, plans_client):
    """幂等：终点仍有效时 replan 为无变更 no-op（重复点击不无限续期）。"""
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_idem_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=date.today() + timedelta(days=3),
        created_days_ago=1,
    )
    _add_day_task(db_session, user, plan, day=1)
    await db_session.commit()
    state["current_user"] = user

    first = client.post(f"/plans/{plan.id}/replan")
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["replanned"] is False
    assert first_payload["new_target_date"] == (date.today() + timedelta(days=3)).isoformat()

    second = client.post(f"/plans/{plan.id}/replan")
    assert second.status_code == 200
    assert second.json() == first_payload

    await db_session.refresh(plan)
    assert plan.target_date == date.today() + timedelta(days=3)
    assert (plan.source_metadata or {}).get("last_replan") is None


@pytest.mark.asyncio
async def test_replan_requires_owner(db_session, plans_client):
    """鉴权对齐：非属主 replan → 404（与既有 get_by_id 属主过滤一致）。"""
    client, state = plans_client
    owner, plan = await _make_comeback_plan(
        db_session,
        username="wt313_owner_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=date.today() - timedelta(days=2),
        created_days_ago=5,
    )
    _add_day_task(db_session, owner, plan, day=1)
    stranger = User(username="wt313_stranger_user", email="wt313_stranger_user@example.com", hashed_password="hashed")
    db_session.add(stranger)
    await db_session.commit()
    state["current_user"] = stranger

    response = client.post(f"/plans/{plan.id}/replan")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_plan_health_reports_days_since_last_activity(db_session, plans_client):
    """缺陷 4 复现钉：health 缺「离开」维度。最后一次活动 6 天前（≥3 天阈值）→
    health_metrics.days_since_last_activity == 6 且 health_reasons 含
    days_since_last_activity。main 上两者皆无 → 红。
    """
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_stale_user",
        description="测试离开维度",
        target_date=None,
        created_days_ago=9,
        plan_type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
    )
    _add_day_task(db_session, user, plan, day=1, completed=True, completed_days_ago=6)
    _add_day_task(db_session, user, plan, day=2)
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 1, "total": 2, "avg_completion_rate": 0.5},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["health_metrics"]["days_since_last_activity"] == 6
    assert "days_since_last_activity" in detail["health_reasons"]
    assert detail["health_status"] == "warning"


@pytest.mark.asyncio
async def test_plan_health_no_inactivity_reason_for_active_plan(db_session, plans_client):
    """新鲜计划（活动在阈值内）不误报离开维度：metric=0、reason 不在。"""
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_fresh_user",
        description="测试新鲜计划不误报",
        target_date=None,
        created_days_ago=0,
        plan_type=PlanType.GROWTH,
        plan_stage=PlanStage.DAILY,
    )
    _add_day_task(db_session, user, plan, day=1)
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 0, "total": 1, "avg_completion_rate": 0.0},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    response = client.get(f"/plans/{plan.id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["health_metrics"]["days_since_last_activity"] == 0
    assert "days_since_last_activity" not in detail["health_reasons"]
    assert detail["health_status"] == "healthy"


# ---------------------------------------------------------------------------
# WT334 · plan subject 内部 token 残留清洗（红测先行）：
# feature_tour S7 以 f"TOUR科目-{run}" 填计划 subject（subject 参与唯一键，
# token 是评测合法去重手段，不改库）；详情 subject 字段 / day_highlights 推荐
# 文案 / 任务 why_now 等展示面不得原样透出 token。正常科目零改写。
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_plan_detail_scrubs_internal_token_from_subject_surfaces(db_session, plans_client):
    client, state = plans_client
    user = User(
        username="wt334_token_user",
        email="wt334_token_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="真题冲刺周",
        type=PlanType.SPRINT,
        description="评测 harness 遗留的 tokened subject（存量脏行，读取面兜底）",
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        subject="TOUR科目-d91d5df0-10-5dc70d",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    # 钉开始日 = 今天本地日（ naïve），使派生日 = Day 1「today」档——
    # subject_tail 文案只在该档出现（今天先做好…{subject} 的第一步就稳下来了）。
    started_at = datetime.combine(date.today(), datetime.min.time())
    plan.created_at = started_at
    plan.updated_at = started_at
    await db_session.flush()
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="真题演练与错因回看",
            type=TaskType.LEARNING,
            tags=["day:1"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            priority=2,
            guide_json={"task_kind": "diagnostic_map"},
        )
    )
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 0, "total": 1, "avg_completion_rate": 0.0},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert "TOUR科目" not in str(detail["subject"])
    recommendation = str((detail.get("day_highlights") or {}).get("recommendation") or "")
    assert recommendation, "day_highlights recommendation must still be present"
    assert "TOUR科目" not in recommendation and "d91d5df0" not in recommendation
    why_now = str(((detail["tasks"][0].get("guide_json") or {}).get("why_now")) or "")
    assert "TOUR科目" not in why_now and "d91d5df0" not in why_now

    list_response = client.get("/plans")
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json()["data"] if item["id"] == str(plan.id))
    assert "TOUR科目" not in str(listed["subject"])


@pytest.mark.asyncio
async def test_plan_detail_normal_subject_zero_rewrite(db_session, plans_client, monkeypatch):
    """正常科目「离散数学」在详情 subject / day_highlights 文案 / why_now 零改写。

    wt559 UTC 钟对齐：subject_tail 文案只在派生日 = Day 1「today」档出现，
    而派生日由用户本地日驱动（V3-FIX-233）——宿主机 date.today() 播种在
    UTC 钟下会漂到 resume 档、文案丢失科目（CI 红层）。冻结 09-25 20:00Z
    + 显式 Asia/Shanghai → 「今天」= 09-26。期望推导：
    started = 09-26 00:00（用户本地日开始）、target = 09-26 + 5 = 10-01
    → initial_days = (10-01 − 09-26) = 5、days_left = 5 → today_day = 1。
    """
    _pin_shanghai_user_local_clock(monkeypatch)
    client, state = plans_client
    user = User(
        username="wt334_clean_user",
        email="wt334_clean_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="考研冲刺",
        type=PlanType.SPRINT,
        description="正常科目零改写",
        plan_stage=PlanStage.SPRINT,
        target_date=USER_LOCAL_TODAY + timedelta(days=5),  # 10-01
        daily_available_minutes=60,
        subject="离散数学",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    db_session.add(PushPreference(user_id=user.id, timezone="Asia/Shanghai"))
    started_at = datetime.combine(USER_LOCAL_TODAY, datetime.min.time())  # 09-26 00:00
    plan.created_at = started_at
    plan.updated_at = started_at
    await db_session.flush()
    db_session.add(
        Task(
            user_id=user.id,
            plan_id=plan.id,
            title="图论基础复习",
            type=TaskType.LEARNING,
            tags=["day:1"],
            estimated_minutes=30,
            difficulty=2,
            energy_cost=2,
            status=TaskStatus.PENDING,
            priority=2,
            guide_json={"task_kind": "diagnostic_map"},
        )
    )
    db_session.add(
        PlanState(
            user_id=user.id,
            plan_id=plan.id,
            status=PlanStateStatus.ACTIVE.value,
            version=1,
            task_index={"completed": 0, "total": 1, "avg_completion_rate": 0.0},
            task_summaries=[],
        )
    )
    await db_session.commit()
    state["current_user"] = user

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["subject"] == "离散数学"
    recommendation = str((detail.get("day_highlights") or {}).get("recommendation") or "")
    assert "离散数学" in recommendation
    why_now = str(((detail["tasks"][0].get("guide_json") or {}).get("why_now")) or "")
    assert "离散数学" in why_now


@pytest.mark.asyncio
async def test_plan_galaxy_concept_extraction_drops_tokened_subject_tag():
    """WT334 · 生成侧：里程碑触发的星图更新不把内部科目 token 带进节点 tags。"""
    from types import SimpleNamespace

    from app.core.celery_app import _extract_plan_galaxy_concepts as _extract_plan_concepts

    plan = SimpleNamespace(
        name="真题冲刺周",
        description="冲刺描述",
        subject="TOUR科目-d91d5df0-10-5dc70d",
    )
    concepts = await _extract_plan_concepts(plan, None)
    assert len(concepts) == 1
    assert concepts[0]["tags"] == []

    clean_plan = SimpleNamespace(name="真题冲刺周", description="冲刺描述", subject="离散数学")
    clean_concepts = await _extract_plan_concepts(clean_plan, None)
    assert clean_concepts[0]["tags"] == ["离散数学"]


# ---------------------------------------------------------------------------
# WT337 · plan name「TOUR 冲刺 {run}」第三形态 token 清洗（wt334 遗留）：
# feature_tour.py S7 以 f"TOUR 冲刺 {run}" 填计划 name。列表/详情 name 字段、
# 状态通知文案、任务派生 topic、星图概念节点名等展示面不得透出 token。
# 纯 token 名按创建日兜底命名「冲刺计划·M月D日」；正常冲刺命名零改写。
# ---------------------------------------------------------------------------

WT337_EVIDENCE_PLAN_NAME = "TOUR 冲刺 d91d5df0-10-5dc70d"
WT337_TOKENED_CREATED_AT = datetime(2026, 9, 25, 10, 0, 0)
WT337_FALLBACK_NAME = "冲刺计划·9月25日"


@pytest.mark.asyncio
async def test_plan_detail_scrubs_internal_token_from_name_surfaces(db_session, plans_client):
    """存量脏 name（读取面兜底，不改库）：详情/列表 name 走兜底命名，无 token。"""
    client, state = plans_client
    user = User(
        username="wt337_token_name_user",
        email="wt337_token_name_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name=WT337_EVIDENCE_PLAN_NAME,
        type=PlanType.SPRINT,
        description="评测 harness 遗留的 tokened name（存量脏行，读取面兜底）",
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        subject="离散数学",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    plan.created_at = WT337_TOKENED_CREATED_AT
    plan.updated_at = WT337_TOKENED_CREATED_AT
    await db_session.flush()
    await db_session.commit()
    state["current_user"] = user

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["name"] == WT337_FALLBACK_NAME
    assert "d91d5df0" not in str(detail["name"]) and "TOUR" not in str(detail["name"])
    assert detail["subject"] == "离散数学", "正常科目不受 name 清洗波及"

    list_response = client.get("/plans")
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json()["data"] if item["id"] == str(plan.id))
    assert listed["name"] == WT337_FALLBACK_NAME


@pytest.mark.asyncio
async def test_plan_detail_normal_sprint_name_zero_rewrite(db_session, plans_client):
    """正常冲刺命名零改写：「7天冲刺计划」原样透出。"""
    client, state = plans_client
    user = User(
        username="wt337_clean_name_user",
        email="wt337_clean_name_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name="7天冲刺计划",
        type=PlanType.SPRINT,
        description="正常冲刺命名零改写",
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        subject="计算机网络",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.commit()
    state["current_user"] = user

    detail_response = client.get(f"/plans/{plan.id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["name"] == "7天冲刺计划"

    list_response = client.get("/plans")
    assert list_response.status_code == 200
    listed = next(item for item in list_response.json()["data"] if item["id"] == str(plan.id))
    assert listed["name"] == "7天冲刺计划"


@pytest.mark.asyncio
async def test_plan_archive_notification_scrubs_internal_token_from_name(db_session, plans_client, monkeypatch):
    """归档通知 toast（「已归档计划：{name}」）不吃内部 token 名。"""
    client, state = plans_client
    user = User(
        username="wt337_archive_user",
        email="wt337_archive_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name=WT337_EVIDENCE_PLAN_NAME,
        type=PlanType.GROWTH,
        description="归档通知文案兜底",
        plan_stage=PlanStage.REVIEW,
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    plan.created_at = WT337_TOKENED_CREATED_AT
    plan.updated_at = WT337_TOKENED_CREATED_AT
    await db_session.flush()
    await db_session.commit()
    state["current_user"] = user

    captured: dict = {}

    async def _capture(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("app.api.v1.plans.state_notification_service.notify_plan_archived", _capture)

    response = client.post(f"/plans/{plan.id}/archive")
    assert response.status_code == 200
    assert captured, "notify_plan_archived must be called"
    assert captured.get("plan_name") == WT337_FALLBACK_NAME


@pytest.mark.asyncio
async def test_generate_tasks_topic_scrubs_internal_token_from_name(db_session, plans_client, monkeypatch):
    """任务派生 topic：subject 与 name 双双为 token 时按创建日兜底命名。"""
    from types import SimpleNamespace

    client, state = plans_client
    user = User(
        username="wt337_topic_user",
        email="wt337_topic_user@example.com",
        hashed_password="hashed",
    )
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        user_id=user.id,
        name=WT337_EVIDENCE_PLAN_NAME,
        type=PlanType.SPRINT,
        description="任务派生 topic 兜底",
        plan_stage=PlanStage.SPRINT,
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        subject="TOUR科目-d91d5df0-10-5dc70d",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    plan.created_at = WT337_TOKENED_CREATED_AT
    plan.updated_at = WT337_TOKENED_CREATED_AT
    await db_session.flush()
    await db_session.commit()
    state["current_user"] = user

    from app.orchestration.executor import ToolExecutor

    captured: dict = {}

    async def _capture(self, **kwargs):
        captured.update(kwargs)
        return SimpleNamespace(success=True, data={"tasks": []}, error_message=None)

    monkeypatch.setattr(ToolExecutor, "execute_tool_call", _capture)

    response = client.post(f"/plans/{plan.id}/generate-tasks", json={"count": 3})
    assert response.status_code == 200
    assert captured, "ToolExecutor.execute_tool_call must be called"
    topic = str((captured.get("arguments") or {}).get("topic") or "")
    assert topic == WT337_FALLBACK_NAME
    assert "d91d5df0" not in topic and "TOUR" not in topic


@pytest.mark.asyncio
async def test_plan_galaxy_concept_extraction_drops_tokened_name():
    """生成侧：纯 token 计划名不造「TOUR 冲刺-…」概念节点（也不造兜底名噪声星）。"""
    from types import SimpleNamespace

    from app.core.celery_app import _extract_plan_galaxy_concepts as _extract_plan_concepts

    tokened = SimpleNamespace(name=WT337_EVIDENCE_PLAN_NAME, description="冲刺描述", subject="离散数学")
    assert await _extract_plan_concepts(tokened, None) == []

    tokened_with_milestone = SimpleNamespace(name=WT337_EVIDENCE_PLAN_NAME, description="冲刺描述", subject="离散数学")
    concepts = await _extract_plan_concepts(
        tokened_with_milestone, {"name": "里程碑A", "description": "描述", "tags": []}
    )
    assert [c["name"] for c in concepts] == ["里程碑A"]

    clean = SimpleNamespace(name="真题冲刺周", description="冲刺描述", subject="离散数学")
    clean_concepts = await _extract_plan_concepts(clean, None)
    assert clean_concepts[0]["name"] == "真题冲刺周"
