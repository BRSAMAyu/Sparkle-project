"""SimulationEngine db=None 流式契约守卫（V3-FIX-415）。

wt670 在 mypy 棘轮批三（87e3cf24）为行为上下文 enrich 补 self.db 非空卫时
暴露并留档：SimulationEngine 以 db=None 构造时的流式输出契约未钉死。

裁决（详见 v3-output/WT712-SIMCONTRACT/notes.md）：db=None 是合法形态
（纯内存模拟，诚实降级）——本类 6 处既有 db 缺席守卫（391/429/483/1526/
1675/1700 行口径）与测试直接用法（test_theater_seed_and_accuracy 等 8 处）
即既成事实；生产调用方（api/v1/simulation.py、tools/simulation_tool.py）
恒传真 db。显式拒绝反而破坏既有能力。

本文件钉死三态契约：
- C1 纯内存态（db=None + user_id=None）：流式全链诚实完成，锚点回退
  no_anchor，不因外部设施缺席崩溃。
- C2 混合态（db=None + user_id≠None）：运行不可持久化
  （_persist_checkpoint_to_db 同口径拒绝），完成路径不得发出以
  「已沉淀」为前提的持久性下游信号（SimulationGapRevealed / 系统更新），
  否则重启后 deep_link 404、信号成为幽灵引用。
- C3 完成路径 cache 清理与同路径 get/set 同为 best-effort：Redis 抖动
  不得让整条流在 complete 事件前崩掉。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from app.core.cache import cache_service
from app.services.simulation.simulation_engine import (
    ModeratorDecision,
    SimulationEngine,
)
from app.services.system_update_service import SystemUpdateService

TEST_USER_ID = "11111111-1111-1111-1111-111111111111"


def _install_stream_stubs(monkeypatch, *, should_end: bool = True) -> None:
    """钉住 LLM 依赖，使 stream 只检验 db=None 契约本身。"""

    async def fake_generate_participants(**kwargs):
        del kwargs
        return [
            {"name": "优等生", "role_hint": "先搭框架", "stance": "supportive", "persona": {}},
            {"name": "提问者", "role_hint": "追问盲点", "stance": "challenging", "persona": {}},
        ]

    async def fake_moderate_next_turn(self, **kwargs):
        del kwargs
        return ModeratorDecision(
            speaker="优等生",
            reply_target="",
            turn_goal="open",
            real_time_insight="先建立一个共同框架。",
            round_target=3,
            should_pause_for_user=False,
            should_end=should_end,
        )

    async def fake_generate_agent_round(self, **kwargs):
        moderator_decision = kwargs["moderator_decision"]
        return {
            "round": len(kwargs["rounds"]) + 1,
            "speaker": moderator_decision.speaker,
            "message": f"{moderator_decision.speaker} 围绕当前思路继续推进。",
            "reply_to_speaker": "",
            "turn_goal": moderator_decision.turn_goal,
            "speaker_type": "agent",
        }

    async def fake_summarize_rounds(self, topic, rounds):
        del topic, rounds
        return json.dumps(
            {
                "key_arguments": ["先把定义与几何意义分开。"],
                "unresolved_disagreements": [],
                "user_contributions": "用户确认了拆解顺序。",
                "knowledge_gaps_revealed": ["把特征值和对角线元素直接等同"],
                "suggested_next_steps": ["用 2x2 矩阵验证。"],
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(
        "app.services.simulation.simulation_engine.generate_participants",
        fake_generate_participants,
    )
    monkeypatch.setattr(SimulationEngine, "_moderate_next_turn", fake_moderate_next_turn)
    monkeypatch.setattr(SimulationEngine, "_generate_agent_round", fake_generate_agent_round)
    monkeypatch.setattr(SimulationEngine, "_summarize_rounds", fake_summarize_rounds)


async def _collect(stream):
    return [event async for event in stream]


@pytest.mark.asyncio
async def test_db_none_stream_pure_memory_completes_with_honest_anchor(monkeypatch):
    """C1：db=None + user_id=None 纯内存态——全链完成，锚点诚实回退 no_anchor。"""

    _install_stream_stubs(monkeypatch)
    engine = SimulationEngine(db=None)

    events = await _collect(engine.stream(topic="特征值", scenario_key="study_group", await_user_input=False))
    names = [name for name, _ in events]
    assert names[0] == "status"
    assert events[0][1]["anchor_status"] == "no_anchor"
    assert names[-1] == "complete"
    assert events[-1][1]["state"] == "COMPLETED"
    assert events[-1][1]["session"]["rounds"]


@pytest.mark.asyncio
async def test_db_none_stream_with_user_id_does_not_emit_durable_signals(monkeypatch):
    """C2：db=None + user_id 混合态——运行不可持久化，完成路径不得发出
    幽灵盲区事件与「仿真已完成」系统更新；但运行本身仍诚实完成。"""

    _install_stream_stubs(monkeypatch)
    engine = SimulationEngine(db=None)
    publish = AsyncMock(return_value="evt-1")
    monkeypatch.setattr(engine.event_bus_reliable, "publish", publish)
    enqueue = AsyncMock(return_value=True)
    monkeypatch.setattr(SystemUpdateService, "enqueue", enqueue)

    events = await _collect(
        engine.stream(
            topic="特征值",
            scenario_key="study_group",
            user_id=UUID(TEST_USER_ID),
            await_user_input=False,
        )
    )

    names = [name for name, _ in events]
    assert names[-1] == "complete"
    assert events[-1][1]["state"] == "COMPLETED"
    assert publish.await_count == 0, "db=None 运行不可持久化，不得发布 SimulationGapRevealed 幽灵事件"
    assert enqueue.await_count == 0, "db=None 运行不可持久化，不得入队 simulation_session_ready 系统更新"


@pytest.mark.asyncio
async def test_db_none_stream_survives_cache_cleanup_failure(monkeypatch):
    """C3：完成路径 cache 清理是 best-effort——Redis 抖动不得打断 complete。"""

    _install_stream_stubs(monkeypatch)
    engine = SimulationEngine(db=None)

    async def broken_delete(key):
        del key
        raise RuntimeError("redis connection lost")

    monkeypatch.setattr(cache_service, "delete", broken_delete)

    events = await _collect(engine.stream(topic="特征值", scenario_key="study_group", await_user_input=False))
    names = [name for name, _ in events]
    assert names[-1] == "complete"
    assert events[-1][1]["state"] == "COMPLETED"


@pytest.mark.asyncio
async def test_db_none_continue_stream_unknown_session_raises_value_error(monkeypatch):
    """db=None 续跑未知会话：DB 加载守卫回退后诚实抛 ValueError（API 404 语义）。"""

    _install_stream_stubs(monkeypatch)
    engine = SimulationEngine(db=None)

    with pytest.raises(ValueError, match="not found or expired"):
        await engine.continue_run(
            session_id=f"missing-{uuid4()}",
            user_response="我会先画图再推导",
            user_id=UUID(TEST_USER_ID),
        )
