"""SIDECAR-JOURNEY · 单元/集成层：sidecar / fast-track 多轮「真实键语义」回归钉。

钉死 wt190（bef7ae07）修复不被回退：`save_session` 始终以
`planning:session:{user_id}:{chat_session_id}` 落键（planning_workflow.py:47,445-450），
orchestrator 的 `_attach_aurora_planning_sidecar` 与 `_fast_track_exam_sprint`
必须带 user_id 读同一命名空间。回退（读键不带 user）即：真实 Redis 下键恒 miss，
多轮规划旁路与冲刺续聊退化为重新开场（wt190 前 9/10 失败的真实产品缺陷）。

层位说明：本文件在 orchestrator 调用点粒度直接驱动（`__new__` 最小实例 + 内存
Redis 桩），不重复 `test_orchestrator_process_stream_integration.py` 已覆盖的
process_stream 管线级断言；旅程级（gRPC API 级三轮）见
`tests/northstar_eval/sidecar_journey.py`。零产品改动。
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock

import pytest

from app.aurora.runtime_v1 import AuroraRuntimeV1Service
from app.aurora.runtime_v1.decision_loop import AuroraDecision
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.orchestrator import ChatOrchestrator
from app.orchestration.planning_workflow import (
    EXAM_SPRINT_FAST_TRACK_FLAG,
    PLANNING_SESSION_PREFIX,
    PlanningSession,
    PlanningWorkflowManager,
)
from app.orchestration.statechart_engine import WorkflowState

DIGRESSION_MESSAGE = "等等，先帮我查一下这个任务完成没有"
RETURN_ADJUST_MESSAGE = "回到规划，把节奏调轻一点"
STRATEGY_REVISION_REPLY = "我按你的反馈把策略收紧了一版，你确认后我就开始生成任务卡。"


class FakeRedis:
    """内存桩：save_session / aurora runtime state 只需 get/setex/delete。"""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.ttls[key] = ttl

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.store:
                self.store.pop(key)
                self.ttls.pop(key, None)
                removed += 1
        return removed


def user_scoped_key(user_id: str, chat_session_id: str) -> str:
    """save_session 的唯一键形制（写读必须同形，wt190 的全部内容）。"""
    return f"{PLANNING_SESSION_PREFIX.format(user_id=f'{user_id}:')}{chat_session_id}"


def unscoped_key(chat_session_id: str) -> str:
    """修复前的错误读键形制（永不该被写入、更不该被读到）。"""
    return f"{PLANNING_SESSION_PREFIX.format(user_id='')}{chat_session_id}"


def make_manager(redis: FakeRedis) -> PlanningWorkflowManager:
    return PlanningWorkflowManager(redis_client=redis)


def make_orchestrator(manager: PlanningWorkflowManager, service: AuroraRuntimeV1Service) -> ChatOrchestrator:
    """最小实例：只装配两个被测调用点真正消费的协作对象。"""
    orchestrator = ChatOrchestrator.__new__(ChatOrchestrator)
    orchestrator.planning_workflow_manager = manager
    orchestrator.aurora_runtime_v1 = service
    orchestrator._persist_assistant_message = AsyncMock(return_value=None)
    return orchestrator


def planning_session_payload(chat_session_id: str, user_id: str) -> str:
    session = PlanningSession(
        planning_session_id=str(uuid.uuid4()),
        chat_session_id=chat_session_id,
        user_id=user_id,
        state="CLARIFYING",
        goal_raw="7天后考计算机网络，帮我规划一下",
    )
    return json.dumps(session.to_dict(), ensure_ascii=False)


@pytest.fixture
def no_bottleneck_llm(monkeypatch):
    """与 wt190 既有用例同款：强制 bottleneck_analyzer 走确定性 fallback，
    避免 ready→瓶颈路径触碰外部依赖（db=None 下本就不可达真实分析）。"""
    from app.orchestration import bottleneck_analyzer as bottleneck_module

    monkeypatch.setattr(
        bottleneck_module.bottleneck_analyzer,
        "analyze",
        AsyncMock(side_effect=RuntimeError("force deterministic fallback")),
    )


@pytest.mark.asyncio
async def test_planning_session_persists_user_scoped_key_and_multiturn_resume_does_not_reopen(
    no_bottleneck_llm,
) -> None:
    """多轮主链：turn1 建会话（键带 user 域）→ turn2 离题旁路不推进 → turn3 续聊
    恢复同一会话、不重新开场。全称只允许存在一把 planning:session 键。"""
    redis = FakeRedis()
    manager = make_manager(redis)
    user_id = str(uuid.uuid4())
    chat_session_id = f"chat-{uuid.uuid4()}"

    turn1 = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=chat_session_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    assert turn1 is not None and not turn1.get("bypass_planning")
    # 键形制钉死：写入方永远带 {user_id}: 前缀；无作用域键不存在。
    assert user_scoped_key(user_id, chat_session_id) in redis.store
    assert unscoped_key(chat_session_id) not in redis.store
    persisted = await manager.get_active_session(chat_session_id, user_id)
    assert persisted is not None and persisted.state == "CLARIFYING"
    owner_planning_session_id = persisted.planning_session_id
    opening_prompt = str(turn1.get("message") or "")
    assert opening_prompt  # turn1 是澄清开场

    # turn2：规划离题（任务查询）→ 旁路，不推进澄清状态，不重新开场。
    turn2 = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=chat_session_id,
        message=DIGRESSION_MESSAGE,
        context={},
    )
    assert turn2 == {"bypass_planning": True}
    persisted = await manager.get_active_session(chat_session_id, user_id)
    assert persisted is not None
    assert persisted.planning_session_id == owner_planning_session_id
    assert persisted.state == "CLARIFYING"

    # turn3：回归提问 → 续聊命中同一会话，信息被吸收，不重复开场白。
    turn3 = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=chat_session_id,
        message="考传输层、网络层和应用层，我完全没学过，每天2小时，一定要过",
        context={},
    )
    assert turn3 is not None and not turn3.get("bypass_planning")
    resumed = await manager.get_active_session(chat_session_id, user_id)
    assert resumed is not None
    assert resumed.planning_session_id == owner_planning_session_id
    assert resumed.collected["knowledge_baseline"] == "完全没学过"
    assert resumed.collected["time_available"] == "每天约 2 小时"
    assert str(turn3.get("message") or "") != opening_prompt
    planning_keys = [key for key in redis.store if key.startswith("planning:session:")]
    assert planning_keys == [user_scoped_key(user_id, chat_session_id)]


def frame_collector(frames: list):
    async def _callback(response) -> None:
        frames.append(response)

    return _callback


@pytest.mark.asyncio
async def test_fast_track_second_turn_continues_session_without_reopening(no_bottleneck_llm) -> None:
    """orchestrator `_fast_track_exam_sprint` 调用点钉（wt190 第 2 处）：
    turn1 冲刺开场 → turn2 续聊必须读回 user 域会话、走策略修订，
    而不是重新发起冲刺开场。修复回退时本测试必红。"""
    redis = FakeRedis()
    manager = make_manager(redis)
    service = AuroraRuntimeV1Service(redis)
    orchestrator = make_orchestrator(manager, service)
    user_id = str(uuid.uuid4())
    chat_session_id = f"chat-{uuid.uuid4()}"

    async def collect(frames: list):
        async def _callback(response) -> None:
            frames.append(response)

        return _callback

    turn1_frames: list = []
    handled_turn1 = await orchestrator._fast_track_exam_sprint(
        active_db=None,  # type: ignore[arg-type]
        user_id=user_id,
        session_id=chat_session_id,
        user_message="7天后考计算机网络，没学过，每天2小时",
        request_extra_context={},
        user_context_payload={},
        stream_callback=frame_collector(turn1_frames),
    )
    assert handled_turn1 is True
    content_turn1 = [frame for frame in turn1_frames if frame.full_text]
    terminal_turn1 = [frame for frame in turn1_frames if frame.finish_reason]
    assert content_turn1
    assert terminal_turn1[-1].finish_reason == agent_service_pb2.STOP
    assert terminal_turn1[-1].full_text == ""
    opening_text = content_turn1[-1].full_text
    assert content_turn1[-1].metadata["planning_fast_track"] == "exam_sprint"

    session_after_turn1 = await manager.get_active_session(chat_session_id, user_id)
    assert session_after_turn1 is not None
    assert session_after_turn1.state == "PLANNING"
    assert session_after_turn1.collected[EXAM_SPRINT_FAST_TRACK_FLAG] is True
    owner_planning_session_id = session_after_turn1.planning_session_id
    assert user_scoped_key(user_id, chat_session_id) in redis.store
    assert unscoped_key(chat_session_id) not in redis.store

    turn2_frames: list = []
    handled_turn2 = await orchestrator._fast_track_exam_sprint(
        active_db=None,  # type: ignore[arg-type]
        user_id=user_id,
        session_id=chat_session_id,
        user_message=RETURN_ADJUST_MESSAGE,
        request_extra_context={},
        user_context_payload={},
        stream_callback=frame_collector(turn2_frames),
    )
    # 修复在：读回既有会话 → 续聊处理；修复回退：会话 miss → 重建冲刺开场。
    assert handled_turn2 is True
    content_turn2 = [frame for frame in turn2_frames if frame.full_text]
    assert content_turn2, "fast-track 续聊必须先发内容帧再发终端帧"
    assert content_turn2[-1].full_text == STRATEGY_REVISION_REPLY
    assert content_turn2[-1].full_text != opening_text
    assert content_turn2[-1].metadata["planning_fast_track"] == "exam_sprint"

    resumed = await manager.get_active_session(chat_session_id, user_id)
    assert resumed is not None
    assert resumed.planning_session_id == owner_planning_session_id
    assert resumed.state == "AWAITING_CONFIRM"
    assert resumed.confirmed_strategy is not None
    # 两轮后仍只有一把会话键（续聊没有另开新会话）。
    planning_keys = [key for key in redis.store if key.startswith("planning:session:")]
    assert planning_keys == [user_scoped_key(user_id, chat_session_id)]
    assert orchestrator._persist_assistant_message.await_count == 2


@pytest.mark.asyncio
async def test_sidecar_attach_hits_user_scoped_key_and_mounts_once(no_bottleneck_llm) -> None:
    """orchestrator `_attach_aurora_planning_sidecar` 调用点钉（wt190 第 1 处）：
    离题轮 sidecar 必须读回 user 域规划会话并挂载一次；键命中以精确键形制断言。"""
    redis = FakeRedis()
    manager = make_manager(redis)
    service = AuroraRuntimeV1Service(redis)
    service.decision_loop.decide = AsyncMock(
        return_value=AuroraDecision(
            action="soft_return_topic",
            chat_directive={
                "intent": "recover_planning_naturally",
                "brief": "Answer the current task first, then recover planning naturally.",
            },
        )
    )
    orchestrator = make_orchestrator(manager, service)
    user_id = str(uuid.uuid4())
    chat_session_id = f"chat-{uuid.uuid4()}"

    turn1 = await manager.process_planning_turn(
        db=None,  # type: ignore[arg-type]
        user_id=uuid.UUID(user_id),
        chat_session_id=chat_session_id,
        message="7天后考计算机网络，帮我规划一下",
        context={},
    )
    assert turn1 is not None

    payload: dict = {}
    state = WorkflowState()
    action = await orchestrator._attach_aurora_planning_sidecar(
        active_db=None,  # type: ignore[arg-type]
        user_id=user_id,
        session_id=chat_session_id,
        request_id=f"req-{uuid.uuid4()}",
        user_message=DIGRESSION_MESSAGE,
        request_extra_context={},
        conversation_context={},
        user_context_payload=payload,
        state=state,
    )

    assert action == "soft_return_topic"
    sidecar = payload.get("aurora_planning_sidecar")
    assert isinstance(sidecar, dict)
    assert sidecar["source"] == "aurora_decision_loop"
    assert sidecar["decision"]["action"] == "soft_return_topic"
    assert sidecar["bypass_planning"] is True
    assert state.context_data["aurora_planning_sidecar"]["source"] == "aurora_decision_loop"
    scaffold = dict(sidecar.get("scaffold") or {})
    assert scaffold.get("top_latent_thread") is not None or scaffold.get("open_tensions")
    # 键命中证据：读的就是写入方那把 user 域键；无作用域键从未存在。
    assert user_scoped_key(user_id, chat_session_id) in redis.store
    assert unscoped_key(chat_session_id) not in redis.store


@pytest.mark.asyncio
async def test_sidecar_reads_strictly_user_scoped_no_legacy_key_fallback() -> None:
    """设计钉（wt190 裁决 B：拒绝双键兜底）：只有无作用域遗留键时，
    sidecar 不得读取——跨租户安全优先于「能读到就行」。"""
    redis = FakeRedis()
    manager = make_manager(redis)
    service = AuroraRuntimeV1Service(redis)
    orchestrator = make_orchestrator(manager, service)
    chat_session_id = f"chat-{uuid.uuid4()}"
    legacy_user_id = str(uuid.uuid4())
    redis.store[unscoped_key(chat_session_id)] = planning_session_payload(chat_session_id, user_id="")

    payload: dict = {}
    action = await orchestrator._attach_aurora_planning_sidecar(
        active_db=None,  # type: ignore[arg-type]
        user_id=legacy_user_id,
        session_id=chat_session_id,
        request_id=f"req-{uuid.uuid4()}",
        user_message=DIGRESSION_MESSAGE,
        request_extra_context={},
        conversation_context={},
        user_context_payload=payload,
        state=WorkflowState(),
    )
    assert action == ""
    assert "aurora_planning_sidecar" not in payload


@pytest.mark.asyncio
async def test_sidecar_and_fast_track_do_not_leak_across_users() -> None:
    """多租户隔离：同一 chat_session_id，非属主用户既触发不了 sidecar，
    也续不进他人的 fast-track 会话；属主会话不被触碰。"""
    redis = FakeRedis()
    manager = make_manager(redis)
    service = AuroraRuntimeV1Service(redis)
    orchestrator = make_orchestrator(manager, service)
    owner_id = str(uuid.uuid4())
    intruder_id = str(uuid.uuid4())
    chat_session_id = f"chat-{uuid.uuid4()}"
    redis.store[user_scoped_key(owner_id, chat_session_id)] = planning_session_payload(
        chat_session_id, user_id=owner_id
    )

    payload: dict = {}
    action = await orchestrator._attach_aurora_planning_sidecar(
        active_db=None,  # type: ignore[arg-type]
        user_id=intruder_id,
        session_id=chat_session_id,
        request_id=f"req-{uuid.uuid4()}",
        user_message=DIGRESSION_MESSAGE,
        request_extra_context={},
        conversation_context={},
        user_context_payload=payload,
        state=WorkflowState(),
    )
    assert action == ""
    assert "aurora_planning_sidecar" not in payload

    handled = await orchestrator._fast_track_exam_sprint(
        active_db=None,  # type: ignore[arg-type]
        user_id=intruder_id,
        session_id=chat_session_id,
        user_message=RETURN_ADJUST_MESSAGE,
        request_extra_context={},
        user_context_payload={},
        stream_callback=AsyncMock(),
    )
    assert handled is False

    owner_session = await manager.get_active_session(chat_session_id, owner_id)
    assert owner_session is not None
    assert owner_session.user_id == owner_id
    assert owner_session.state == "CLARIFYING"
    assert await manager.get_active_session(chat_session_id, intruder_id) is None
