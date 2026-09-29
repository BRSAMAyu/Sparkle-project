"""FIX-583 · Hybrid start 系统性挂死回归钉（Q01 G6 真端 3/3 复现的反例面）.

Q01 实证缺陷形态（真端 3/3 用户复现，见 wtQ01 v4/evidence/V4-Q01）：
注册→persona→材料就绪后 ``POST /journey/hybrid`` 100% 超网关 30s 代理超时
503；后端 handler 永不完成；run 永久 ``RUNNING/prep``（``agent_tool_calls``/
``hybrid_artifacts`` 零落库=工具成功后的推进从未提交）；僵尸事务
``idle in transaction`` 持该用户 ``agent_runs`` 行级锁，同用户后续请求排队
30s 后同样 503——一次挂死永久钉死该用户的 Hybrid。

本文件钉死三条结构性修复（任何一条被回退，对应测试可失败）：

1. **重活出请求事务**：prep 真实检索走 executor owned-session（db_session=
   None），请求事务在 prep 前显式收口——prep 挂起期间请求会话零开放事务、
   零行锁（原实现把 prep 检索跑在请求事务内）。
2. **prep 显式超时 + FAILED 补偿**：``asyncio.wait_for(PREP_TOOL_TIMEOUT_
   SECONDS)`` 超时后 run 诚实落 FAILED（error_category=prep_timeout）释放
   幂等键，请求拿到可重试失败——不再是「工具成功后挂死」的无界路径
   （wt392 F1 补偿只覆盖 prep 抛错路径，不覆盖本路径）。
3. **僵尸 run 启动自检回收**：幂等 resolve 命中超龄 ``RUNNING/prep`` 僵尸
   （Q01 实证形态）时补偿 FAILED（error_category=prep_zombie_reclaimed）
   开新 attempt——不再原样回放把「旅程卡死」当「旅程状态」返给用户；
   新鲜 ``RUNNING/prep`` 仍幂等回放（防过度回收的 mutation 反向钉）。

纪律：pytest + sqlite 口径（StaticPool 内存库）；fixture/种子复用
``test_j06_hybrid_journey``（同装配、零第二套 fixture，wt392 同法）。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_run import AgentRun
from app.models.task import Task
from app.models.user import User
from app.services.agent_run_service import AgentRunService, TransitionActor
from app.tools.base import ToolResult

pytestmark = pytest.mark.asyncio

# fixtures/种子复用 j06（同装配、零第二套 fixture；wt392 同法）
from tests.unit.test_j06_hybrid_journey import (  # noqa: F401
    _make_user,
    _seed_goal,
    _seed_materials,
    _seed_task,
    bus_stub_fixture,
    j06_db_fixture,
)

# ---------------------------------------------------------------------------
# 桩执行器（FIX-583 靶面只关心：会话归属 / 挂起时长 / 返回形状）
# ---------------------------------------------------------------------------


class _RecordingExecutor:
    """记录调用面（db_session 归属 + 调用时请求会话事务态）的桩执行器。

    - ``sleep_seconds``：模拟慢/挂 prep（> PREP_TOOL_TIMEOUT_SECONDS 触发超时）；
    - ``result``：超时后不触发的场景返回的 ToolResult；
    - ``request_db``：请求会话引用——在**调用时刻**采样其事务态（FIX-583
      合同①的核心窗口：prep 执行期间请求会话必须零开放事务）。
    """

    def __init__(
        self,
        result: ToolResult,
        *,
        sleep_seconds: float = 0.0,
        request_db: AsyncSession | None = None,
    ):
        self.result = result
        self.sleep_seconds = sleep_seconds
        self.request_db = request_db
        self.calls: list[dict[str, object]] = []

    async def execute_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        user_id: str,
        db_session: object,
        *,
        progress_callback: object = None,
        tool_call_id: str | None = None,
        compensation_call: dict | None = None,
        runtime_context: dict | None = None,
        idempotency_key: str | None = None,
        **_kwargs: object,
    ) -> ToolResult:
        self.calls.append(
            {
                "tool_name": tool_name,
                # FIX-583 合同①：prep 必须走 owned-session（None），不得是请求会话
                "db_session": db_session,
                "db_session_is_none": db_session is None,
                # FIX-583 合同①：调用时刻请求会话事务态（修前 prep 在请求事务内）
                "request_txn_open": None if self.request_db is None else self.request_db.in_transaction(),
                "idempotency_key": idempotency_key,
                "runtime_context": runtime_context,
            }
        )
        if self.sleep_seconds > 0:
            await asyncio.sleep(self.sleep_seconds)
        return self.result


def _prep_hit_result(chunk_ids: list[str], file_id: str) -> ToolResult:
    """真实检索命中的 ToolResult 形状（chunk 引用指向真实行）。"""
    return ToolResult(
        success=True,
        tool_name="retrieve_user_material",
        data={
            "query": "联邦学习",
            "retrieval_mode": "lexical_only_embedding_disabled",
            "scoped_file_count": 1,
            "results": [
                {
                    "chunk_id": chunk_id,
                    "file_id": file_id,
                    "file_name": "federated_learning_notes.pdf",
                    "chunk_index": index,
                    "section_title": "联邦学习",
                    "page_numbers": [index + 1],
                    "score": 0.9,
                    "snippet": f"chunk-{index}",
                }
                for index, chunk_id in enumerate(chunk_ids)
            ],
        },
    )


@pytest_asyncio.fixture(name="seeded_world")
async def seeded_world_fixture(j06_db: AsyncSession):  # noqa: F811
    """用户 + goal + task + 真实材料（prep 命中真源）。"""
    user = await _make_user(j06_db)
    await _seed_goal(j06_db, user)
    task = await _seed_task(j06_db, user)
    stored, _chunks = await _seed_materials(j06_db, user)
    await j06_db.commit()
    return user, task, stored


# ============================================================================
# 合同② · prep 显式超时 → FAILED 补偿 + 请求会话零钉死 + 重试开新 attempt
# ============================================================================


async def test_prep_hang_times_out_compensates_and_does_not_pin_request_session(
    j06_db, bus_stub, seeded_world, monkeypatch
):
    """prep 慢/挂不阻塞启动请求超时窗：显式超时 → FAILED 补偿 → 幂等键释放
    → 重试开新 attempt 成功；全程请求会话无开放事务、prep 不占请求会话。"""
    import app.services.hybrid_journey_service as hj

    user, task, stored = seeded_world
    monkeypatch.setattr(hj, "PREP_TOOL_TIMEOUT_SECONDS", 0.2)

    hang_executor = _RecordingExecutor(
        _prep_hit_result([str(uuid4())], str(stored.id)),
        sleep_seconds=3.0,  # 远超 0.2s 超时（修前：请求在此永久悬挂）
        request_db=j06_db,
    )

    with pytest.raises(hj.HybridJourneyStateError, match="timed out"):
        await hj.start_hybrid_journey(
            j06_db,
            user_id=user.id,
            task_id=task.id,
            tool_executor=hang_executor,  # type: ignore[arg-type]
        )

    # 合同①：prep 走 owned-session（None），不是请求会话；**调用时刻**请求
    # 会话事务已收口（修前：prep 在请求事务内，in_transaction()=True）。
    assert hang_executor.calls, "prep executor must be invoked"
    call = hang_executor.calls[0]
    assert call["db_session_is_none"] is True, "prep must run on executor-owned session, not the request session"
    assert call["request_txn_open"] is False, "request session must have no open transaction during prep"

    # 合同②：run 诚实落 FAILED（超时补偿），幂等键随之释放
    run_row = (await j06_db.execute(select(AgentRun).where(AgentRun.user_id == user.id))).scalars().one()
    assert str(run_row.status) == "FAILED"
    assert run_row.error_category == "prep_timeout"
    assert run_row.completed_at is not None

    # 幂等键已释放：重试（好执行器）开新 attempt 成功，不回放死 run
    good_executor = _RecordingExecutor(_prep_hit_result([str(uuid4())], str(stored.id)))
    retry = await hj.start_hybrid_journey(
        j06_db,
        user_id=user.id,
        task_id=task.id,
        tool_executor=good_executor,  # type: ignore[arg-type]
    )
    assert retry["run"]["run_id"] != str(run_row.id), "retry must open a fresh attempt, not replay the dead run"
    assert retry["run"]["status"] == "AWAITING_USER"
    assert retry["citations"], "retry prep must produce real citations"


# ============================================================================
# 合同③ · RUNNING/prep 超龄僵尸：启动自检回收 → FAILED → 新 attempt
# ============================================================================


async def _create_zombie_prep_run(
    j06_db: AsyncSession, user: User, task: Task, *, heartbeat_age_seconds: float
) -> AgentRun:
    """手工搭 Q01 僵尸形态：RUNNING + current_stage=prep + 心跳超龄。"""
    from app.services.hybrid_journey_service import JOURNEY_STEPS

    service = AgentRunService(j06_db)
    created = await service.create_run(
        user_id=user.id,
        objective="Hybrid 旅程：僵尸形态复刻",
        kind="system",
        trace_id="hybrid_journey",
        task_id=task.id,
        allowed_tools=["retrieve_user_material"],
        completion_condition={"kind": "user_confirmation", "description": "用户确认带引用交付"},
        risk_class="low",
        steps=JOURNEY_STEPS,
        idempotency_key=f"hybrid_journey:{task.id}",
        source="server_service",
    )
    await service.transition(
        created.run.id,
        "RUNNING",
        user_id=user.id,
        actor=TransitionActor.USER,
        current_stage="prep",
        source="server_service",
    )
    stale = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=heartbeat_age_seconds)
    await j06_db.execute(update(AgentRun).where(AgentRun.id == created.run.id).values(heartbeat_at=stale))
    await j06_db.commit()
    return created.run


async def test_stale_running_prep_zombie_reclaimed_on_start(j06_db, bus_stub, seeded_world):
    """Q01 钉死面：resolve 命中超龄 RUNNING/prep 僵尸 → 补偿 FAILED 开新
    attempt（修前：原样回放僵尸 run——旅程永久卡在 RUNNING/prep 无产物）。"""
    import app.services.hybrid_journey_service as hj
    from app.services.hybrid_journey_service import PREP_ZOMBIE_AFTER_SECONDS

    user, task, stored = seeded_world
    zombie = await _create_zombie_prep_run(j06_db, user, task, heartbeat_age_seconds=PREP_ZOMBIE_AFTER_SECONDS + 300)

    executor = _RecordingExecutor(_prep_hit_result([str(uuid4())], str(stored.id)))
    started = await hj.start_hybrid_journey(
        j06_db,
        user_id=user.id,
        task_id=task.id,
        tool_executor=executor,  # type: ignore[arg-type]
    )

    await j06_db.refresh(zombie)
    assert str(zombie.status) == "FAILED", "zombie must be compensated to a terminal state"
    assert zombie.error_category == "prep_zombie_reclaimed"

    assert started["run"]["run_id"] != str(zombie.id), "start must proceed on a fresh attempt, not replay the zombie"
    assert started["run"]["status"] == "AWAITING_USER"
    assert started["citations"], "fresh attempt must run prep for real"


async def test_fresh_running_prep_still_replays_idempotently(j06_db, bus_stub, seeded_world):
    """mutation 反向钉：新鲜 RUNNING/prep 不回收——活跃 run 仍幂等回放
    （双击/重开不重复建 run；wt392 F1 active-replay 语义零回退）。"""
    import app.services.hybrid_journey_service as hj

    user, task, stored = seeded_world
    executor = _RecordingExecutor(_prep_hit_result([str(uuid4())], str(stored.id)))
    started = await hj.start_hybrid_journey(
        j06_db,
        user_id=user.id,
        task_id=task.id,
        tool_executor=executor,  # type: ignore[arg-type]
    )
    assert started["run"]["status"] == "AWAITING_USER"

    # 把 run 拨回 RUNNING/prep 且心跳新鲜（复刻「prep 进行中」的活跃形态）
    await j06_db.execute(
        update(AgentRun)
        .where(AgentRun.id == uuid.UUID(started["run"]["run_id"]))
        .values(status="RUNNING", current_stage="prep", heartbeat_at=datetime.now(UTC).replace(tzinfo=None))
    )
    await j06_db.commit()

    replay_executor = _RecordingExecutor(_prep_hit_result([str(uuid4())], str(stored.id)))
    replay = await hj.start_hybrid_journey(
        j06_db,
        user_id=user.id,
        task_id=task.id,
        tool_executor=replay_executor,  # type: ignore[arg-type]
    )
    assert replay["run"]["run_id"] == started["run"]["run_id"], "active run must replay idempotently"
    assert replay["run"]["status"] == "RUNNING"
    assert replay_executor.calls == [], "replay must not re-run prep"
