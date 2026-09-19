"""A-04 · Spine L2 升格点完整联合链接入测试（生产决策点证据）。

证明卡面「至少一个生产决策点走完整联合链」可执行而非纸上谈兵：

    L2 escalation（spine pipeline 真实形态）
      → 因子装配投影（joint_factor_projection：L2 提名 + L0 quiet_hours）
      → decide_joint_two_step（A-02 policy × X-02 allocation × D4 再分配）
      → build_joint_contract（A-01 契约 + P3-8 allocation_ref 回填）
      → feed_aurora_decision（S-01：spine:aurora_decisions:* 真通道）
      → decision_event 可观测（occurrence_id / decision_id / 归因随行）

四 pattern 实测语义（真实联合核驱动，非 mock）：
- exam_underwater / execution_collapse → rescope/hybrid（D1 直选）；
- burnout_risk → pause/hybrid（系统面镜像）；
- knowledge_crisis → no_action + D3 归因（学习锚 user_core × rescope 需
  hybrid 的确定性裁决——分配事实优先；报告登记为 reviewer 挑战点）。

韧性面：非 UUID user_id 降级（联合记录保留、契约面跳过）；内部异常 →
None（主管道零破坏）；只记录/只喂入（不改本轮策略选择的接线纪律由
pipeline_context 装配面保证——on_chat_turn 层不在本文件 scope）。
"""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest

from app.aurora.joint_decision import read_decision_contract
from app.signals.spine_orchestrator import SpineOrchestrator


class ListBackedFakeRedis:
    """带真实 list 存储的 redis 替身（feed_aurora_decisions 通道可断言）。"""

    def __init__(self):
        self.lists: dict[str, list[str]] = {}
        self.kv: dict[str, str] = {}

    async def rpush(self, key: str, *values: str):
        self.lists.setdefault(key, []).extend(values)
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int):
        bucket = self.lists.get(key)
        if bucket is not None:
            self.lists[key] = bucket[start:] if stop == -1 else bucket[start : stop + 1]
        return True

    async def expire(self, key: str, ttl: int):
        return True

    async def lrange(self, key: str, start: int, stop: int):
        bucket = self.lists.get(key, [])
        if stop == -1:
            return bucket[start:]
        return bucket[start : stop + 1]

    async def get(self, key: str):
        return self.kv.get(key)

    async def set(self, key: str, value: str, **kwargs):
        self.kv[key] = value
        return True


def _escalation(pattern: str, matched: list[str], intervention: str, reason: str) -> dict[str, Any]:
    return {
        "pattern_name": pattern,
        "intervention": intervention,
        "reason": reason,
        "matched_states": matched,
        "energy_level": "L2",
    }


_EXAM_UNDERWATER = _escalation(
    "exam_underwater",
    ["deadline_pressure", "execution_consistency"],
    "adaptive_replan",
    "High deadline pressure + execution issues — emergency replan",
)
_KNOWLEDGE_CRISIS = _escalation(
    "knowledge_crisis",
    ["knowledge_bottleneck", "transfer_failure"],
    "error_replan_bridge",
    "Knowledge bottleneck detected — trigger worked example repair",
)
_BURNOUT = _escalation(
    "burnout_risk",
    ["affective_pressure"],
    "reduce_load",
    "Burnout risk detected — reduce task load immediately",
)


def _l0(state_key: str):
    return type("L0", (), {"state_key": state_key})()


@pytest.fixture
def redis():
    return ListBackedFakeRedis()


@pytest.fixture
def orchestrator(redis):
    return SpineOrchestrator(redis)


class TestFullJointChainAtL2:
    @pytest.mark.asyncio
    async def test_exam_underwater_full_chain_feeds_spine(self, orchestrator, redis):
        """完整链：联合决策 → A-01 契约（P3-8 ref 回填）→ spine 真通道。"""
        user = str(uuid4())
        event = await orchestrator._run_l2_joint_decision(user, _EXAM_UNDERWATER, [_l0("deadline_pressure")])

        assert event is not None
        joint = event["joint"]
        assert joint["selected"] == "rescope"
        assert joint["mode"] == "hybrid"
        assert "D1.first_legal_joint_nominee" in joint["why"]
        assert joint["occurrence_id"]

        contract = event.get("contract")
        assert contract is not None
        rebuilt, violations = read_decision_contract(contract)
        assert rebuilt is not None and violations == ()  # 读门全过（live+validate+一致性）
        assert rebuilt.intervention_type == "rescope"
        assert rebuilt.execution_mode is not None and rebuilt.execution_mode.value == "hybrid"
        assert rebuilt.allocation_ref and rebuilt.allocation_ref.startswith("decision://alloc_")

        # S-01 喂入真通道：spine:aurora_decisions:<user> 收到决策事件
        key = f"spine:aurora_decisions:{user}"
        assert key in redis.lists
        fed = json.loads(redis.lists[key][-1])
        assert fed["source"] == "aurora_decision"
        assert fed["action"] == "rescope"
        assert fed["surface"] == "l2_escalation"
        assert fed["decision"]["joint"]["selected"] == "rescope"
        assert fed["decision"]["contract"]["intervention_type"] == "rescope"

    @pytest.mark.asyncio
    async def test_burnout_risk_pause_system_surface(self, orchestrator):
        """burnout → pause（系统面干预，mode 镜像目录标称 hybrid，无
        allocation_ref——不绑任务步执行权）。"""
        event = await orchestrator._run_l2_joint_decision(
            str(uuid4()), _BURNOUT, []
        )
        assert event is not None
        assert event["joint"]["selected"] == "pause"
        assert event["joint"]["mode"] == "hybrid"
        contract, violations = read_decision_contract(event["contract"])
        assert contract is not None and violations == ()
        assert contract.allocation_ref is None  # 系统面边界

    @pytest.mark.asyncio
    async def test_knowledge_crisis_conflict_adjudicated_with_attribution(self, orchestrator):
        """对抗面生产实例：学习锚分配（human）× rescope 需 hybrid → 分配
        事实优先（D3），no_action 落锤，归因完整（联合排除 + allocation why）。"""
        event = await orchestrator._run_l2_joint_decision(
            str(uuid4()), _KNOWLEDGE_CRISIS, []
        )
        assert event is not None
        joint = event["joint"]
        assert joint["selected"] == "no_action"
        assert "D3.conflict_allocation_precedence" in joint["why"]
        exclusion = next(e for e in joint["exclusions"] if e["target"] == "rescope")
        assert exclusion["reason"] == "J1.delivery_mode_incompatible"
        assert exclusion["allocation_mode"] == "human"
        # no_action 契约面：inert 携带封闭 no_action_reason
        contract, violations = read_decision_contract(event["contract"])
        assert contract is not None and violations == ()
        assert contract.allocation_ref is None


class TestWiringResilience:
    @pytest.mark.asyncio
    async def test_non_uuid_user_keeps_joint_record_without_contract(self, orchestrator):
        """非 UUID user_id：契约面跳过（A-01 user_id 硬类型），联合记录与
        spine 喂入照常（降级不丢决策事实）。"""
        user = "legacy-user-id"
        event = await orchestrator._run_l2_joint_decision(user, _EXAM_UNDERWATER, [])
        assert event is not None
        assert event["joint"]["selected"] == "rescope"
        assert "contract" not in event
        key = f"spine:aurora_decisions:{user}"
        assert key in redis_lists(orchestrator)

    @pytest.mark.asyncio
    async def test_internal_failure_degrades_to_none(self, orchestrator, monkeypatch):
        """内部异常 → None（主管道零破坏；外层防御）。"""

        def _boom(*args, **kwargs):
            raise RuntimeError("projection exploded")

        monkeypatch.setattr(
            "app.aurora.joint_factor_projection.project_joint_factors", _boom
        )
        event = await orchestrator._run_l2_joint_decision(str(uuid4()), _EXAM_UNDERWATER, [])
        assert event is None

    @pytest.mark.asyncio
    async def test_quiet_hours_l0_fact_projected(self, orchestrator):
        """L0 quiet_hours 事实进投影面（suppress 门开着与否由 A-02 R6 裁决；
        本例 rescope 非 proactive 不受 R6 压制——接线事实面到位即可观测）。"""
        event = await orchestrator._run_l2_joint_decision(
            str(uuid4()), _EXAM_UNDERWATER, [_l0("quiet_hours_active"), _l0("deadline_pressure")]
        )
        assert event is not None
        assert event["joint"]["selected"] == "rescope"  # 非 proactive：静默时段不压制

    @pytest.mark.asyncio
    async def test_projection_notes_carried_in_event(self, orchestrator):
        """投影溯源随行：materiality_defaulted（spine 侧无 Aurora snapshot）
        必须登记（可审计：哪个字段是投影缺省）。"""
        event = await orchestrator._run_l2_joint_decision(str(uuid4()), _EXAM_UNDERWATER, [])
        assert event is not None
        assert event["projection"].get("materiality_defaulted") is True


def redis_lists(orchestrator: SpineOrchestrator) -> dict[str, list[str]]:
    return orchestrator.redis.lists
