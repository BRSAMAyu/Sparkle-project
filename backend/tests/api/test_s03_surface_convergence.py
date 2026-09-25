"""卡 S-03（v2）· Squad/Sprint/Check-in 产品表面收敛 —— headless 验收测试。

验收口径（headless）与现状定性：

1. 四入口真实可达且各自有真实数据流断言（非空壳）：
   小队（/community/squads）→ 冲刺（/community/squads/{id}/sprint-progress，
   口径唯一来自 sprint_task_ledger）→ 今日 check-in（/community/checkin，
   火苗入群火堆）→ 成果反馈（/community/share → 群资源列表 → peer 反馈 →
   主人采纳为 Goal outcome evidence）。一条链走完，全部断真实请求-响应。

2. feed 降级断言：/community/feed 路径仍可达（真实帖子 200 可读）；
   同时小队协作动作（打卡/共享/反馈/采纳）**零 Post 行**——群协作留在
   小队表面，不泄漏进公共 feed（降级语义的真源级断言）。
   上面四入口测试里这些动作已发生，此处只读校验。

3. Flame 与付费/积分零耦合的负向测试：
   - 打卡火苗↑ ≠ 光子变动（photon_balance / PhotonTransactionHistory 不动）；
   - 光子发放（PhotonService.grant_photons）≠ 火苗变动（user.flame_level /
     flame_brightness / member.flame_contribution / group.total_flame_power 不动）；
   - 付费权益（users.entitlement free→pro）≠ 火苗面变动；反向（flame 永不
     参与权益判级）由 O-04 既有守卫钉死，此处补火苗读面方向的对照。

现状定性（诚实标注）：S-01/S-04/D-COMM-3 已把四个真源与端点建齐，O-04 已
立 flame×entitlement 解耦守卫——本文件三项在基线 83ed09ee 上预期为
**基线即绿**（契约锁），唯一真红面在 mobile 壳层标签/内容错位
（community_main_surface_convergence_test.dart，见该文件头注）。
本文件锁死收敛契约，防止后续回退。

DATABASE_URL 口径：sqlite+aiosqlite:///:memory:（conftest 统一注入）。
"""

from __future__ import annotations

import uuid as uuid_mod
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.community import Group, GroupMember, GroupRole, Post
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.shop import PhotonTransactionHistory
from app.models.task import Task, TaskStatus, TaskType
from app.models.user import User
from app.schemas.community import FeedbackVerdict
from app.services.community_feedback_service import SharedResourceFeedbackService
from app.services.photon_service import PhotonService

COMMUNITY_PREFIX = "/api/v1/community"
SQUAD_PREFIX = f"{COMMUNITY_PREFIX}/squads"


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
async def _make_user(db: AsyncSession, prefix: str) -> User:
    user = User(
        username=f"{prefix}_{uuid_mod.uuid4().hex[:10]}",
        email=f"{prefix}_{uuid_mod.uuid4().hex[:10]}@t.example",
        hashed_password="x",
        photon_balance=0,
    )
    db.add(user)
    await db.flush()
    return user


def _squad_payload(name: str) -> dict:
    return {
        "name": name,
        "deadline": (datetime.now(UTC) + timedelta(days=5)).isoformat(),
        "max_members": 4,
        "sprint_goal": "期末周冲完计网",
    }


async def _owner_goal_plan_task(db: AsyncSession, owner: User) -> tuple[Goal, Plan, Task]:
    """真源造数：Goal → Plan（双向外链）→ Task（plan_id 挂链，已完成）。"""
    goal = Goal(user_id=owner.id, title="S-03 目标：完成作品集", status="active", mastery=0.2, progress=0.1)
    db.add(goal)
    await db.flush()
    plan = Plan(user_id=owner.id, goal_id=goal.id, name="作品集计划", type=PlanType.SPRINT)
    db.add(plan)
    await db.flush()
    goal.plan_id = plan.id
    db.add(goal)
    await db.flush()
    task = Task(
        user_id=owner.id,
        plan_id=plan.id,
        title="作品集第一章",
        type=TaskType.LEARNING,
        estimated_minutes=45,
        status=TaskStatus.COMPLETED,
    )
    db.add(task)
    await db.flush()
    return goal, plan, task


@pytest.fixture(name="community_app")
async def community_app_fixture(db_session: AsyncSession):
    """挂 community 主路由 + squads 路由的测试 app（依赖覆盖到 fixture 会话）。"""
    from app.api.v1.community import router as community_router
    from app.api.v1.community_squad import router as squad_router

    app = FastAPI()
    app.include_router(community_router, prefix=COMMUNITY_PREFIX)
    app.include_router(squad_router, prefix=COMMUNITY_PREFIX)

    current = {"user": None}

    async def _override_get_db():
        yield db_session

    async def _override_get_current_user():
        return current["user"]

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    # 打卡端点的 streak 后台刷新任务依赖进程级 engine/redis，与本测试无关，
    # 置 no-op 保证确定性（火苗/连击语义在 CheckinService 内已完成）。
    import app.api.v1.community as community_api

    async def _no_op_streak(_user_id: UUID) -> None:
        return None

    community_api._refresh_streak_signals = _no_op_streak  # type: ignore[method-assign]

    yield app, current

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. 四入口收敛走链（真实请求-响应数据流）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_four_entries_converged_walk_with_real_data_flows(db_session: AsyncSession, community_app):
    app, current = community_app
    owner = await _make_user(db_session, "walk_owner")
    mate = await _make_user(db_session, "walk_mate")
    goal, _plan, _task = await _owner_goal_plan_task(db_session, owner)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # ── 入口①小队：创建（201）→ 伙伴加入 → 成员列表真实 2 人 ──
        current["user"] = owner
        create_resp = await ac.post(SQUAD_PREFIX, json=_squad_payload("七日高数冲刺"))
        assert create_resp.status_code == 201, create_resp.text
        squad = create_resp.json()
        squad_id = squad["id"]
        assert squad["my_role"] == "owner"
        assert squad["sprint_goal"] == "期末周冲完计网"

        current["user"] = mate
        assert (await ac.post(f"{SQUAD_PREFIX}/{squad_id}/join")).status_code == 200
        members_resp = await ac.get(f"{SQUAD_PREFIX}/{squad_id}/members")
        assert members_resp.status_code == 200
        assert len(members_resp.json()) == 2

        # ── 入口②冲刺：完成度聚合真实来自 ledger（owner 已完成 1/1 → 1.0）──
        progress_resp = await ac.get(f"{SQUAD_PREFIX}/{squad_id}/sprint-progress")
        assert progress_resp.status_code == 200
        progress = progress_resp.json()
        assert progress["squad_id"] == squad_id
        assert progress["sprint_active"] is True
        by_user = {m["user_id"]: m for m in progress["members"]}
        assert str(owner.id) in by_user and str(mate.id) in by_user
        owner_stat = by_user[str(owner.id)]
        assert owner_stat["stats"]["total"] == 1
        assert owner_stat["stats"]["completed"] == 1
        assert owner_stat["stats"]["completion_rate"] == 1.0
        mate_stat = by_user[str(mate.id)]
        assert mate_stat["stats"]["total"] == 0
        assert mate_stat["stats"]["completion_rate"] == 0.0  # 空账本诚实 0，不伪装

        # ── 入口③今日 check-in：打卡 → 火苗真实入群火堆 ──
        current["user"] = owner
        checkin_resp = await ac.post(
            f"{COMMUNITY_PREFIX}/checkin",
            json={
                "group_id": squad_id,
                "today_duration_minutes": 60,
                "message": "今天刷完一章",
                "goal_id": str(goal.id),
            },
        )
        assert checkin_resp.status_code == 200, checkin_resp.text
        checkin = checkin_resp.json()
        assert checkin["success"] is True
        assert checkin["flame_earned"] > 0
        assert checkin["new_streak"] == 1
        assert checkin["goal_id"] == str(goal.id)  # GJ16 回链锚点

        flame_resp = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/flame")
        assert flame_resp.status_code == 200
        flame = flame_resp.json()
        assert flame["total_power"] == checkin["flame_earned"]
        assert len(flame["flames"]) == 2  # 两个成员都有火苗位（mate 未打卡 → 0）
        flame_by_user = {str(f["user_id"]): f for f in flame["flames"]}
        assert flame_by_user[str(owner.id)]["flame_power"] == checkin["flame_earned"]
        assert flame_by_user[str(mate.id)]["flame_power"] == 0

        # ── 入口④成果反馈：共享 → 群资源面可见 → peer 反馈 → 主人采纳为 Goal evidence ──
        task_row = (
            await db_session.execute(select(Task).where(Task.user_id == owner.id, Task.title == "作品集第一章"))
        ).scalar_one()
        share_resp = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task_row.id),
                "target_group_id": squad_id,
                "permission": "view",
                "comment": "求伙伴看看这个产出",
            },
        )
        # /share 端点契约即 200（无 201 装饰）。
        assert share_resp.status_code == 200, share_resp.text
        shared_resource_id = share_resp.json()["id"]  # SharedResourceInfo.id 即反馈/采纳句柄

        # peer 视角：群资源列表真实可见（反馈计数 0）
        current["user"] = mate
        resources_resp = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/resources")
        assert resources_resp.status_code == 200
        resources = resources_resp.json()
        assert any(r["id"] == shared_resource_id for r in resources)
        target_resource = next(r for r in resources if r["id"] == shared_resource_id)
        assert target_resource["feedback_count"] == 0

        # peer 反馈（helpful）
        feedback_resp = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value, "comment": "第一章结构很清楚"},
        )
        assert feedback_resp.status_code == 201, feedback_resp.text
        feedback_id = feedback_resp.json()["id"]

        # 反馈计数真实更新
        resources_resp2 = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/resources")
        target_resource2 = next(
            r for r in resources_resp2.json() if r["id"] == shared_resource_id
        )
        assert target_resource2["feedback_count"] == 1

        # 主人采纳 → Goal receipt（outcome evidence 真实落库）
        current["user"] = owner
        adopt_resp = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback/{feedback_id}/adopt",
            json={"goal_id": str(goal.id)},
        )
        assert adopt_resp.status_code == 200, adopt_resp.text
        adopt = adopt_resp.json()
        assert adopt["success"] is True
        assert adopt["goal_id"] == str(goal.id)

        await db_session.refresh(goal)
        receipts = (goal.metadata_payload or {}).get("community_evidence") or []
        assert any(
            r.get("feedback_id") == str(feedback_id) and r.get("verdict") == "helpful" for r in receipts
        ), f"goal receipt missing: {goal.metadata_payload}"

        # Forbidden 守卫：采纳 ≠ mastery（反馈/采纳不自动改 mastery/progress）
        assert goal.mastery == 0.2
        assert goal.progress == 0.1


# ---------------------------------------------------------------------------
# 2. feed 降级：路径可达 + 群协作零泄漏进公共 feed
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feed_demoted_but_reachable_and_group_collab_stays_out_of_public_feed(
    db_session: AsyncSession, community_app
):
    app, current = community_app
    owner = await _make_user(db_session, "feed_owner")
    mate = await _make_user(db_session, "feed_mate")
    await db_session.commit()
    current["user"] = owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 公共 feed 路径仍可达：真实 Post 行 200 可读（不因降级而不可达）。
        db_session.add(Post(user_id=owner.id, content="一条普通公共帖子", visibility="public"))
        await db_session.commit()
        feed_resp = await ac.get(f"{COMMUNITY_PREFIX}/feed")
        assert feed_resp.status_code == 200
        feed = feed_resp.json()
        assert len(feed) == 1
        assert feed[0]["content"] == "一条普通公共帖子"
        public_post_count_before = (
            await db_session.execute(select(func.count(Post.id)))
        ).scalar()

        # 群协作四面动作（小队/打卡/共享/反馈）在四入口走链测试中已发生；
        # 此处断言这些动作零 Post 行——群协作留在小队表面，不进公共 feed。
        squad = await ac.post(SQUAD_PREFIX, json=_squad_payload("降级语义小队"))
        assert squad.status_code == 201
        squad_id = squad.json()["id"]
        checkin = await ac.post(
            f"{COMMUNITY_PREFIX}/checkin",
            json={"group_id": squad_id, "today_duration_minutes": 30, "message": "打卡"},
        )
        assert checkin.status_code == 200
        task_row = Task(user_id=owner.id, title="分享任务", type=TaskType.LEARNING, estimated_minutes=20)
        db_session.add(task_row)
        await db_session.flush()
        share = await ac.post(
            f"{COMMUNITY_PREFIX}/share",
            json={
                "resource_type": "task",
                "resource_id": str(task_row.id),
                "target_group_id": squad_id,
                "permission": "view",
            },
        )
        assert share.status_code == 200
        shared_resource_id = share.json()["id"]
        # 反馈由真实同伴给出（自反馈 400 守卫是既有红线，不绕）。
        current["user"] = mate
        assert (await ac.post(f"{SQUAD_PREFIX}/{squad_id}/join")).status_code == 200
        fb = await ac.post(
            f"{COMMUNITY_PREFIX}/shared-resources/{shared_resource_id}/feedback",
            json={"verdict": FeedbackVerdict.HELPFUL.value},
        )
        assert fb.status_code == 201
        current["user"] = owner

        await db_session.commit()
        public_post_count_after = (
            await db_session.execute(select(func.count(Post.id)))
        ).scalar()
        assert public_post_count_after == public_post_count_before  # 零新增 Post

        feed_resp2 = await ac.get(f"{COMMUNITY_PREFIX}/feed")
        assert len(feed_resp2.json()) == 1  # feed 内容不变：打卡/共享/反馈不入流


# ---------------------------------------------------------------------------
# 3. Flame 与付费/积分零耦合（负向测试）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_flame_zero_coupling_with_payment_and_points(db_session: AsyncSession, community_app):
    app, current = community_app
    owner = await _make_user(db_session, "flame_owner")
    squad_payload = _squad_payload("火堆解耦小队")
    await db_session.commit()
    current["user"] = owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        squad = await ac.post(SQUAD_PREFIX, json=squad_payload)
        squad_id = squad.json()["id"]
        checkin = await ac.post(
            f"{COMMUNITY_PREFIX}/checkin",
            json={"group_id": squad_id, "today_duration_minutes": 90, "message": "冲"},
        )
        assert checkin.status_code == 200
        flame_earned = checkin.json()["flame_earned"]
        assert flame_earned > 0

        # ① 打卡火苗 ↑ ≠ 光子变动：余额不动、无任何光子流水行。
        await db_session.refresh(owner)
        assert owner.photon_balance == 0
        tx_count = (
            await db_session.execute(select(func.count(PhotonTransactionHistory.id)))
        ).scalar()
        assert tx_count == 0

        member_row = (
            await db_session.execute(
                select(GroupMember).where(
                    GroupMember.group_id == UUID(squad_id), GroupMember.user_id == owner.id
                )
            )
        ).scalar_one()
        group_row = await db_session.get(Group, UUID(squad_id))
        assert member_row.flame_contribution == flame_earned
        assert group_row.total_flame_power == flame_earned
        flame_level_after_checkin = owner.flame_level
        flame_brightness_after_checkin = owner.flame_brightness

        # ② 光子发放（含流水落库）≠ 火苗变动：四个火苗字段逐项不动。
        photon_svc = PhotonService(db_session)
        grant = await photon_svc.grant_photons(
            user_id=str(owner.id),
            amount=500,
            source="test:s03_negative_coupling",
            record_history=True,
        )
        assert grant["new_balance"] == 500
        await db_session.commit()
        await db_session.refresh(owner)
        await db_session.refresh(member_row)
        await db_session.refresh(group_row)
        assert owner.photon_balance == 500  # 光子真的动了（对照有效性）
        assert owner.flame_level == flame_level_after_checkin
        assert owner.flame_brightness == flame_brightness_after_checkin
        assert member_row.flame_contribution == flame_earned
        assert group_row.total_flame_power == flame_earned

        # 光子流出方向同样不回写火苗（deduct 只动余额）。
        deduct = await photon_svc.deduct_photons(
            user_id=str(owner.id), amount=200, reason="test:s03_negative_coupling_spend"
        )
        assert deduct["new_balance"] == 300
        await db_session.commit()
        await db_session.refresh(owner)
        await db_session.refresh(member_row)
        await db_session.refresh(group_row)
        assert owner.flame_level == flame_level_after_checkin
        assert member_row.flame_contribution == flame_earned
        assert group_row.total_flame_power == flame_earned

        # ③ 付费权益翻转 ≠ 火苗读面：entitlement free→pro 后火堆状态逐字节同形。
        owner.entitlement = "pro"
        await db_session.commit()
        flame_resp = await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/flame")
        assert flame_resp.status_code == 200
        flame_pro = flame_resp.json()
        assert flame_pro["total_power"] == flame_earned
        assert {str(f["user_id"]): f["flame_power"] for f in flame_pro["flames"]} == {
            str(owner.id): flame_earned,
        }

        # 反向对照（O-04 同向补读面）：火苗高 ≠ 权益。flame_level 拉满 +
        # entitlement free → 判级仍是 free（宁降不升）。
        from app.core.entitlement import entitlement_effective

        owner.entitlement = "free"
        owner.flame_level = 15
        await db_session.commit()
        assert entitlement_effective(owner.entitlement) == "free"

        # 未知/缺失 entitlement 一律 free（火苗/光子都不得抬级）。
        assert entitlement_effective(None) == "free"
        assert entitlement_effective("premium") == "free"


# ---------------------------------------------------------------------------
# 孤儿守卫：无孤儿 id 断言占位（防止未来重排时 import 面漂移）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_squad_member_feedback_surfaces_do_not_depend_on_feed(db_session: AsyncSession, community_app):
    """收敛面（squads/checkin/feedback）在 feed 为空时全部照常工作。"""
    app, current = community_app
    owner = await _make_user(db_session, "nofeed_owner")
    await db_session.commit()
    current["user"] = owner

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await db_session.execute(select(func.count(Post.id)))).scalar() == 0

        squad = await ac.post(SQUAD_PREFIX, json=_squad_payload("空 feed 收敛面"))
        squad_id = squad.json()["id"]
        assert squad.status_code == 201
        assert (await ac.get(SQUAD_PREFIX)).json()[0]["id"] == squad_id
        assert (
            await ac.post(
                f"{COMMUNITY_PREFIX}/checkin",
                json={"group_id": squad_id, "today_duration_minutes": 15},
            )
        ).status_code == 200
        assert (await ac.get(f"{COMMUNITY_PREFIX}/groups/{squad_id}/resources")).status_code == 200
        assert (await ac.get(f"{COMMUNITY_PREFIX}/feed")).json() == []  # feed 空但可达
