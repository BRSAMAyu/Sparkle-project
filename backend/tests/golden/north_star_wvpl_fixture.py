"""D-06 · WVPL 固定 fixture（服务测试与 golden 共享，单份事实源防漂移）。

时间全部锚在 ``_AS_OF``、**所有实体 id 固定**（golden 事实 JSON 内嵌
task/user/plan/goal ref，随机 id 永远无法逐字节复现——冻结 fixture 的身份
必须同步冻结）。数据库为 conftest 的 sqlite 隔离引擎。

用户阵容：
- alice：窗口内 2 个 loop（file 证据 / focus 覆盖）+ 1 个非 goal-linked 完成 +
  1 个窗口外旧 loop + 聊天信号；
- bob：窗口内 1 个 goal-linked actual 完成但**无 state update 腿**（非 loop）+ 聊天信号；
- carol：仅 context pack 信号（分母）；
- dave：无任何信号（分母对照）；
- seed（registration_source="seed"）：窗口内完整 loop（demo face，绝不进生产数字）。
"""

from __future__ import annotations

import itertools
import uuid
from datetime import datetime, timedelta
from uuid import UUID

_AUTO_NAME = itertools.count(1)

from app.core.action_plan import ACTION_PLAN_SCHEMA_VERSION
from app.models.chat import ChatMessage, MessageRole
from app.models.context_pack import ContextPackRun
from app.models.file_storage import StoredFile
from app.models.focus import FocusSession, FocusStatus
from app.models.galaxy import StudyRecord
from app.models.goal import Goal
from app.models.plan import Plan, PlanType
from app.models.task import Task, TaskStatus, TaskType
from app.models.task_document import TaskDocument
from app.models.user import User

#: 幂等锚点（naive UTC）；golden 与全部断言都由此派生。
AS_OF = datetime(2026, 9, 20, 10, 0, 0)
WINDOW_START = AS_OF - timedelta(days=7)

_REGISTERED_AT = AS_OF - timedelta(days=40)  # 全体用户固定注册时间（golden 确定性）


def _fid(n: int) -> UUID:
    """fixture 固定 id：00000000-0000-4000-8000-<12 位十六进制 n>。"""
    return UUID(f"00000000-0000-4000-8000-{n:012x}")


async def make_user(db_session, *, registration_source: str = "email", uid: int | None = None) -> User:
    tag = uuid_hex(uid) if uid is not None else f"auto{next(_AUTO_NAME)}"
    user = User(
        id=_fid(uid) if uid is not None else None,
        username=f"u{tag}",
        email=f"{tag}@fixture.test",
        hashed_password="x",
        registration_source=registration_source,
        created_at=_REGISTERED_AT,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def uuid_hex(uid: int | None) -> str:
    return f"{uid:012x}" if uid is not None else ""


async def make_goal_plan(
    db_session, user: User, *, bound: bool = True, gid: int | None = None, pid: int | None = None
) -> tuple[Goal, Plan]:
    goal = Goal(
        id=_fid(gid) if gid is not None else None,
        user_id=user.id,
        title="目标",
        status="active",
    )
    db_session.add(goal)
    await db_session.flush()
    plan = Plan(
        id=_fid(pid) if pid is not None else None,
        user_id=user.id,
        name="计划",
        type=PlanType.SPRINT,
        goal_id=goal.id if bound else None,
    )
    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(plan)
    return goal, plan


def task(user_id, *, plan_id=None, completed_at=None, actual_minutes=30, tid: int | None = None, **extra) -> Task:
    # V3 action_plan 字段齐备：X-01 投影门不降级，declared completion_evidence 才可解析
    return Task(
        id=_fid(tid) if tid is not None else None,
        user_id=user_id,
        title="任务",
        type=TaskType.LEARNING,
        estimated_minutes=30,
        plan_id=plan_id,
        status=TaskStatus.COMPLETED if completed_at else TaskStatus.PENDING,
        completed_at=completed_at,
        actual_minutes=actual_minutes if completed_at else None,
        action_schema_version=ACTION_PLAN_SCHEMA_VERSION,
        desired_outcome="完成并留下证据",
        smallest_useful_step={"description": "产出", "useful_because": ["produces_artifact"]},
        execution_mode="human",
        cognitive_ownership="user_core",
        **extra,
    )


def focus(user_id, *, task_id=None, duration=25, end=None, fid: int | None = None) -> FocusSession:
    end = end or AS_OF - timedelta(days=1)
    return FocusSession(
        id=_fid(fid) if fid is not None else None,
        user_id=user_id,
        task_id=task_id,
        start_time=end - timedelta(minutes=duration),
        end_time=end,
        duration_minutes=duration,
        status=FocusStatus.COMPLETED,
    )


def echo(user_id, *, task_id, at=None, sid: int | None = None) -> StudyRecord:
    return StudyRecord(
        id=_fid(sid) if sid is not None else None,
        user_id=user_id,
        node_id=_fid(sid + 100000) if sid is not None else uuid.uuid4(),
        task_id=task_id,
        study_minutes=20,
        mastery_delta=4.0,
        record_type="task_complete",  # ECHO_STUDY_RECORD_TYPES 成员
        created_at=at or AS_OF - timedelta(days=1),
    )


async def file_evidence(
    db_session, user: User, task: Task, *, lifecycle_status="active", erased_at=None, fid: int | None = None
):
    """declared document:// 证据 + StoredFile 就绪 + TaskDocument 显式挂载（actual 三条件）。"""
    file_id = _fid(fid) if fid is not None else uuid.uuid4()
    db_session.add(
        StoredFile(
            id=file_id,
            user_id=user.id,
            file_name="notes.pdf",
            mime_type="application/pdf",
            file_size=1024,
            bucket="docs",
            object_key=f"obj-{file_id}",
            status="uploaded",
            lifecycle_status=lifecycle_status,
            erased_at=erased_at,
        )
    )
    task.completion_evidence = [{"evidence_kind": "artifact", "ref": f"document://{file_id}", "description": "笔记"}]
    db_session.add(TaskDocument(task_id=task.id, file_id=file_id))
    await db_session.commit()


async def chat_signal(user: User, *, at=None, content="hi", cid: int | None = None):
    return ChatMessage(
        id=_fid(cid) if cid is not None else None,
        user_id=user.id,
        session_id=_fid(cid + 200000) if cid is not None else uuid.uuid4(),
        role=MessageRole.USER,
        content=content,
        created_at=at or AS_OF - timedelta(days=1),
    )


async def pack_signal(user: User, *, at=None, pid: int | None = None):
    return ContextPackRun(
        id=_fid(pid) if pid is not None else None,
        user_id=user.id,
        intent="chat",
        budgets={},
        token_usage={},
        memory_counts={},
        created_at=at or AS_OF - timedelta(days=1),
    )


async def build_standard_fixture(db_session) -> dict:
    """标准五用户 fixture（数字口径见 test_north_star_wvpl_service.py 断言）。"""
    alice = await make_user(db_session, uid=1)
    bob = await make_user(db_session, uid=2)
    carol = await make_user(db_session, uid=3)
    await make_user(db_session, uid=4)  # dave：完全无活动（分母对照）
    seed = await make_user(db_session, registration_source="seed", uid=5)

    alice_goal, alice_plan = await make_goal_plan(db_session, alice, gid=101, pid=201)
    _, unbound_plan = await make_goal_plan(db_session, alice, bound=False, gid=102, pid=202)
    bob_goal, bob_plan = await make_goal_plan(db_session, bob, gid=103, pid=203)
    seed_goal, seed_plan = await make_goal_plan(db_session, seed, gid=104, pid=204)

    # alice · T1：窗口内 goal-linked actual（declared file 证据）+ 回声 → LOOP
    t1 = task(alice.id, plan_id=alice_plan.id, completed_at=AS_OF - timedelta(days=1, hours=1), tid=301)
    db_session.add(t1)
    await db_session.flush()
    await file_evidence(db_session, alice, t1, fid=401)
    db_session.add(echo(alice.id, task_id=t1.id, sid=501))

    # alice · T2：窗口内 goal-linked actual（focus 覆盖 25min ≥ max(10, 0.5*30)=15）+ 两条回声
    t2 = task(alice.id, plan_id=alice_plan.id, completed_at=AS_OF - timedelta(days=3), tid=302)
    db_session.add(t2)
    await db_session.flush()
    db_session.add(focus(alice.id, task_id=t2.id, duration=25, end=AS_OF - timedelta(days=3), fid=601))
    db_session.add(echo(alice.id, task_id=t2.id, sid=502))
    db_session.add(echo(alice.id, task_id=t2.id, sid=503))  # 第二条回声：重复 event 不双计

    # alice · T3：窗口内完成但 plan 未绑 goal → 非 goal-linked（truth coverage 里 self_reported）
    db_session.add(task(alice.id, plan_id=unbound_plan.id, completed_at=AS_OF - timedelta(days=2), tid=303))

    # alice · T4：窗口外（10 天前）的旧 loop（declared file 证据 + 回声）→ 只进有界全史
    t4 = task(alice.id, plan_id=alice_plan.id, completed_at=AS_OF - timedelta(days=10), tid=304)
    db_session.add(t4)
    await db_session.flush()
    await file_evidence(db_session, alice, t4, fid=402)
    db_session.add(echo(alice.id, task_id=t4.id, at=AS_OF - timedelta(days=10), sid=504))

    # bob · T5：窗口内 goal-linked actual（focus 覆盖）但**无 state update 腿**（无 study_record）
    t5 = task(bob.id, plan_id=bob_plan.id, completed_at=AS_OF - timedelta(days=2, hours=1), tid=305)
    db_session.add(t5)
    await db_session.flush()
    db_session.add(focus(bob.id, task_id=t5.id, duration=25, end=AS_OF - timedelta(days=2, hours=1), fid=602))

    # engagement 信号：alice/bob 聊天、carol context pack
    db_session.add(await chat_signal(alice, cid=701))
    db_session.add(await chat_signal(bob, cid=702))
    db_session.add(await pack_signal(carol, pid=801))

    # seed 用户：窗口内完整 loop（demo face，绝不进生产数字）
    t6 = task(seed.id, plan_id=seed_plan.id, completed_at=AS_OF - timedelta(days=2), tid=306)
    db_session.add(t6)
    await db_session.flush()
    await file_evidence(db_session, seed, t6, fid=403)
    db_session.add(echo(seed.id, task_id=t6.id, sid=505))

    await db_session.commit()
    return {
        "alice": alice,
        "bob": bob,
        "carol": carol,
        "seed": seed,
        "alice_goal": alice_goal,
        "bob_goal": bob_goal,
        "seed_goal": seed_goal,
        "t1": t1,
        "t2": t2,
        "t4": t4,
        "t5": t5,
        "t6": t6,
    }
