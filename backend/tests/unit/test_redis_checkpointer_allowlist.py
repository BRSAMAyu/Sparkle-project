"""PROD-LOG #7 契约测试：checkpoint 允许清单收敛.

背景（v3-output/PROD-LOG/REPORT.md ②-7）：
- 旧实现硬编码豁免 ``["db_session", "stream_callback", "tools_schema"]``，
  新增的运行期依赖 key（run_ledger / transparency_generator / emit_transparency_event /
  redis_client / grounding_validator）每次存档都打 WARNING，5 天 585 条，是引擎
  日志最大噪音簇。
- 契约：已知运行期依赖（模块级常量 ``KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS``）
  静默跳过（DEBUG）；清单外 key 序列化失败仍 WARNING；可序列化 key 正常入档。
"""

from __future__ import annotations

import json

import pytest
from loguru import logger

from app.checkpoint.redis_checkpointer import (
    KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS,
    RedisCheckpointer,
)
from app.orchestration.statechart_engine import WorkflowState


class _RecordingRedis:
    def __init__(self) -> None:
        self.stored: dict[str, str] = {}

    async def set(self, key, value, ex=None):
        self.stored[key] = value
        return True


class _RuntimeObject:
    """模拟 redis client / db session 一类不可序列化的运行期对象."""

    def __repr__(self) -> str:  # pragma: no cover
        return "<runtime-object>"


@pytest.fixture
def checkpoint_records():
    records: list = []
    sink_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    yield records
    logger.remove(sink_id)


def _state(context_data: dict) -> WorkflowState:
    return WorkflowState(
        messages=[],
        context_data=context_data,
        next_step=None,
        errors=[],
        is_finished=False,
    )


def test_allowlist_covers_production_observed_runtime_keys():
    """允许清单必须对齐当前代码面：旧 3 key + 生产日志实证的 5 个新 key."""
    assert {
        "db_session",
        "stream_callback",
        "tools_schema",
        "run_ledger",
        "transparency_generator",
        "emit_transparency_event",
        "redis_client",
        "grounding_validator",
    } <= KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS


def test_allowlist_covers_prodfix4_plan_context_working_keys():
    """PROD-LOG2 ②-5（PROD-FIX-4）：二轮巡检新暴露的 4 个 key 必须登记.

    生产证据（wt208 09:10 实例 88min 窗口）：snapshot×10 / user_context×7 /
    focused_memory×7 / executable_plan×7 条 WARNING。写入点核实：
    - snapshot: execution_engine.py（StateSnapshotManager.create_snapshot 产物，
      StateSnapshot pydantic 对象）注入 context_data
    - executable_plan: execution_engine.py / standard_workflow.py（LangGraph
      计划对象，Python 对象不可 json.dumps；清理位写 None 可序列化）
    - user_context / focused_memory: session_state_mixin.py 合并上下文 dict，
      内嵌运行期对象（episodic memories / context_pack 等）序列化必炸
    """
    assert {
        "snapshot",
        "user_context",
        "focused_memory",
        "executable_plan",
    } <= KNOWN_NON_SERIALIZABLE_CONTEXT_KEYS


@pytest.mark.asyncio
async def test_prodfix4_plan_context_working_keys_saved_silently(checkpoint_records: list):
    """PROD-FIX-4：4 个计划/上下文工作面 key 静默跳过（DEBUG），不产生 WARNING."""
    rdb = _RecordingRedis()
    checkpointer = RedisCheckpointer(rdb)

    state = _state(
        {
            "session_id": "s3",
            "request_id": "r3",
            "snapshot": _RuntimeObject(),
            "executable_plan": _RuntimeObject(),
            "user_context": {"preferences": {"style": "concise"}, "raw": _RuntimeObject()},
            "focused_memory": {"episodic_memories": [_RuntimeObject()]},
            "answer": "可序列化内容",
        }
    )

    await checkpointer.save(state, "node_3")

    warnings = [r for r in checkpoint_records if r["level"].name == "WARNING"]
    assert warnings == [], f"已登记 key 不得产生 WARNING: {[r['message'] for r in warnings]}"

    payload = json.loads(rdb.stored["checkpoint:s3"])
    assert payload["context_data"] == {"session_id": "s3", "request_id": "r3", "answer": "可序列化内容"}
    debug_msgs = [r["message"] for r in checkpoint_records if r["level"].name == "DEBUG"]
    assert any("snapshot" in m for m in debug_msgs), "已知 key 跳过应留 DEBUG 痕迹"


@pytest.mark.asyncio
async def test_known_runtime_keys_saved_silently(checkpoint_records: list):
    """已知运行期 key：静默（至多 DEBUG）跳过，不产生 WARNING；可序列化 key 照常入档."""
    rdb = _RecordingRedis()
    checkpointer = RedisCheckpointer(rdb)

    state = _state(
        {
            "session_id": "s1",
            "request_id": "r1",
            "run_ledger": _RuntimeObject(),
            "transparency_generator": _RuntimeObject(),
            "emit_transparency_event": lambda *a, **k: None,
            "redis_client": _RuntimeObject(),
            "grounding_validator": _RuntimeObject(),
            "db_session": _RuntimeObject(),
            "stream_callback": lambda *a, **k: None,
            "tools_schema": _RuntimeObject(),
            "answer": "可序列化内容",
        }
    )

    await checkpointer.save(state, "node_1")

    warnings = [r for r in checkpoint_records if r["level"].name == "WARNING"]
    assert warnings == [], f"已知 key 不得产生 WARNING: {[r['message'] for r in warnings]}"

    payload = json.loads(rdb.stored["checkpoint:s1"])
    assert payload["context_data"] == {"session_id": "s1", "request_id": "r1", "answer": "可序列化内容"}
    debug_msgs = [r["message"] for r in checkpoint_records if r["level"].name == "DEBUG"]
    assert any("run_ledger" in m for m in debug_msgs), "已知 key 跳过应留 DEBUG 痕迹"


@pytest.mark.asyncio
async def test_unknown_non_serializable_key_still_warns(checkpoint_records: list):
    """清单外 key 序列化失败：保持 WARNING（真坏对象/未登记新依赖的信号）."""
    rdb = _RecordingRedis()
    checkpointer = RedisCheckpointer(rdb)

    state = _state(
        {
            "session_id": "s2",
            "brand_new_runtime_thing": _RuntimeObject(),
        }
    )

    await checkpointer.save(state, "node_1")

    warning_msgs = [
        r["message"] for r in checkpoint_records if r["level"].name == "WARNING"
    ]
    assert any("brand_new_runtime_thing" in m for m in warning_msgs)
