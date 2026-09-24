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
from app.models.user import User


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
async def test_day_highlights_follow_plan_start_date_not_day_one(db_session, plans_client):
    """缺陷 1 复现钉：计划 5 天前开始、7 天跨度（剩 2 天），任务在 Day 1/2/6。

    当天日次按「开始日 + 今天」推 = Day 6，重点必须跟日期走；main 上恒推 Day 1 → 红。
    """
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_dateaware_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=date.today() + timedelta(days=2),
        created_days_ago=5,
    )
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
async def test_day_highlights_resume_first_pending_day_when_today_done(db_session, plans_client):
    """诚实降级 A：派生日（Day 6）任务已全部完成、Day 5 仍未完成。

    焦点应「接上」第一个未完成日 Day 5，degraded=True，文案不得冒充「今天」；
    main 上恒推 Day 1 且无 degraded/today_day 字段 → 红。
    """
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_resume_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=date.today() + timedelta(days=2),
        created_days_ago=5,
    )
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
async def test_replan_reanchors_expired_plan_target(db_session, plans_client):
    """缺陷 3 复现钉：超期计划的 replan 执行端点。main 上 POST /plans/{id}/replan 404。

    语义 = 基于现状重校准：未完成日 1..7 全未完成 → 7 天跨度，
    重锚 target = 今天 + 7，落 last_replan 回执进 source_metadata，
    不删任务、不重建计划。
    """
    client, state = plans_client
    user, plan = await _make_comeback_plan(
        db_session,
        username="wt313_replan_user",
        description='{"strategy": {"total_days": 7}}',
        target_date=date.today() - timedelta(days=4),
        created_days_ago=5,
    )
    for day in (1, 2, 3, 4, 5, 6, 7):
        _add_day_task(db_session, user, plan, day=day)
    await db_session.commit()
    state["current_user"] = user

    response = client.post(f"/plans/{plan.id}/replan")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["replanned"] is True
    expected_target = date.today() + timedelta(days=7)
    assert date.fromisoformat(payload["new_target_date"]) == expected_target
    assert date.fromisoformat(payload["previous_target_date"]) == date.today() - timedelta(days=4)
    assert payload["days_shifted"] == 11

    await db_session.refresh(plan)
    assert plan.target_date == expected_target
    # 任务不被删库重来：7 天任务全数保留
    task_result = await db_session.execute(select(Task).where(Task.plan_id == plan.id))
    assert len(list(task_result.scalars().all())) == 7
    receipt = (plan.source_metadata or {}).get("last_replan")
    assert receipt is not None
    assert receipt["new_target_date"] == expected_target.isoformat()
    assert receipt["previous_target_date"] == (date.today() - timedelta(days=4)).isoformat()


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
async def test_plan_detail_normal_subject_zero_rewrite(db_session, plans_client):
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
        target_date=date.today() + timedelta(days=5),
        daily_available_minutes=60,
        subject="离散数学",
        is_active=True,
        priority=PlanPriority.NORMAL,
    )
    db_session.add(plan)
    await db_session.flush()
    started_at = datetime.combine(date.today(), datetime.min.time())
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
