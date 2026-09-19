"""A-01 · L2InterventionEngine → AuroraDecisionContract 接线测试（示范性升级）。

证明 RUNTIME_MAP 的映射可执行而非纸上谈兵：
- 命中路径：``check_escalation`` 结果携带 ``aurora_decision`` 契约载荷，
  重构后 ``validate() == ()``，intervention_type 落在 L2_INTERVENTION_TO_CATALOG；
- 全结局路径：``decide()`` 对 命中/无命中/冷却/空输入 均给出合法契约
  （no_action 携带封闭原因码）；
- legacy 面不变：pattern_name/intervention/reason/matched_states 键原样保留，
  非 UUID user_id 时行为与接线前完全一致（无契约键）；
- 决策确定性：同输入同契约 id（shadow/live 对比锚点）。

接线变异必红：去掉契约挂载、改映射表、映射到词表外类型都会使本文件失败
（变异验证记录见 v3-output/A-01/REPORT.md）。
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.aurora.runtime_v1.l2_intervention import (
    L2_INTERVENTION_TO_CATALOG,
    L2InterventionEngine,
    _ESCALATION_PATTERNS,
)
from app.core.aurora_decision import AURORA_INTERVENTION_TYPES, aurora_decision_from_dict


def _state(key: str, confidence: float, value: str, scope: str = "session") -> dict:
    return {"state_key": key, "confidence": confidence, "value": value, "scope": scope}


def _fresh_redis() -> AsyncMock:
    redis = AsyncMock()
    redis.get.return_value = None  # 无冷却记录
    return redis


_UUID_USER = str(uuid4())


class TestMappingDiscipline:
    def test_every_escalation_pattern_has_catalog_mapping(self):
        """冻结纪律：新增 _ESCALATION_PATTERNS 干预必须同步登记目录映射。"""
        pattern_interventions = {str(pattern["intervention"]) for pattern in _ESCALATION_PATTERNS}
        assert pattern_interventions <= set(L2_INTERVENTION_TO_CATALOG)

    def test_catalog_mapping_lands_in_contract_vocabulary(self):
        assert set(L2_INTERVENTION_TO_CATALOG.values()) <= AURORA_INTERVENTION_TYPES


class TestFiredPathContract:
    @pytest.mark.asyncio
    async def test_knowledge_crisis_carries_valid_contract(self):
        engine = L2InterventionEngine(_fresh_redis())
        result = await engine.check_escalation(
            _UUID_USER,
            [
                _state("knowledge_bottleneck", 0.82, "tcp_congestion"),
                _state("transfer_failure", 0.75, "negative_transfer"),
            ],
        )
        assert result is not None
        # legacy 面原样保留（matched_states 同样源自 list(set())，集合等价断言）
        assert result["pattern_name"] == "knowledge_crisis"
        assert result["intervention"] == "error_replan_bridge"
        assert sorted(result["matched_states"]) == ["knowledge_bottleneck", "transfer_failure"]
        assert result["energy_level"] == "L2"

        # 契约面存在且合法
        payload = result.get("aurora_decision")
        assert isinstance(payload, dict)
        contract = aurora_decision_from_dict(payload)
        assert contract is not None
        assert contract.validate() == ()
        assert contract.intervention_type == "rescope"
        assert contract.execution_mode is not None and contract.execution_mode.value == "hybrid"
        assert contract.cognition_tier == "l2_intervention"
        assert contract.governance_mode == "live"
        # P2-1（R2 返修）：evidence_refs 源自 legacy _get_matched_states 的 list(set())，
        # 顺序依赖 str hash——断言必须集合等价（PYTHONHASHSEED 无关），不得精确有序。
        assert sorted(contract.evidence_refs) == sorted(
            ("signal://knowledge_bottleneck", "signal://transfer_failure")
        )
        assert contract.annotations["l2_intervention"] == "error_replan_bridge"
        assert contract.annotations["pattern"] == "knowledge_crisis"
        assert contract.no_action_reason is None

    @pytest.mark.asyncio
    async def test_burnout_maps_to_pause(self):
        engine = L2InterventionEngine(_fresh_redis())
        result = await engine.check_escalation(
            _UUID_USER, [_state("affective_pressure", 0.8, "burnout_risk")]
        )
        assert result is not None
        contract = aurora_decision_from_dict(result["aurora_decision"])
        assert contract is not None
        assert contract.validate() == ()
        assert contract.intervention_type == "pause"


class TestDecideAllOutcomes:
    @pytest.mark.asyncio
    async def test_decide_fired_returns_actionable_contract(self):
        engine = L2InterventionEngine(_fresh_redis())
        contract = await engine.decide(
            _UUID_USER,
            [_state("knowledge_bottleneck", 0.82, "tcp_congestion"), _state("transfer_failure", 0.75, "x")],
        )
        assert contract is not None and contract.validate() == ()
        assert contract.intervention_type == "rescope"

    @pytest.mark.asyncio
    async def test_decide_no_match_returns_no_action(self):
        engine = L2InterventionEngine(_fresh_redis())
        contract = await engine.decide(_UUID_USER, [_state("random_state", 0.9, "whatever")])
        assert contract is not None and contract.validate() == ()
        assert contract.intervention_type == "no_action"
        assert contract.no_action_reason == "no_matching_pattern"
        assert contract.execution_mode is None

    @pytest.mark.asyncio
    async def test_decide_empty_states_returns_no_action(self):
        engine = L2InterventionEngine(_fresh_redis())
        contract = await engine.decide(_UUID_USER, [])
        assert contract is not None and contract.validate() == ()
        assert contract.no_action_reason == "no_active_states"

    @pytest.mark.asyncio
    async def test_decide_cooldown_returns_no_action_with_evidence(self):
        redis = _fresh_redis()
        redis.get.return_value = "1"  # 冷却中
        engine = L2InterventionEngine(redis)
        contract = await engine.decide(
            _UUID_USER,
            [_state("knowledge_bottleneck", 0.82, "tcp_congestion"), _state("transfer_failure", 0.75, "x")],
        )
        assert contract is not None and contract.validate() == ()
        assert contract.intervention_type == "no_action"
        assert contract.no_action_reason == "cooldown_active"
        # 冷却压制仍保留证据（可观测被压制的干预量）；P2-1：集合等价断言（set 派生无序）。
        assert sorted(contract.evidence_refs) == sorted(
            ("signal://knowledge_bottleneck", "signal://transfer_failure")
        )
        assert contract.annotations["pattern"] == "knowledge_crisis"

    @pytest.mark.asyncio
    async def test_decide_non_uuid_user_returns_none(self):
        engine = L2InterventionEngine(_fresh_redis())
        assert await engine.decide("user_abc", [_state("knowledge_bottleneck", 0.9, "x")]) is None

    @pytest.mark.asyncio
    async def test_decide_deterministic_id_same_input(self):
        engine = L2InterventionEngine(_fresh_redis())
        states = [_state("knowledge_bottleneck", 0.82, "tcp_congestion"), _state("transfer_failure", 0.75, "x")]
        first = await engine.decide(_UUID_USER, states)
        second = await engine.decide(_UUID_USER, states)
        assert first is not None and second is not None
        assert first.decision_id_or_compute() == second.decision_id_or_compute()


class TestLegacyFaceUnchanged:
    @pytest.mark.asyncio
    async def test_non_uuid_user_keeps_pure_legacy_dict(self):
        """既有单测用 "user_abc" 这类非 UUID id：接线后行为必须与接线前一致。"""
        engine = L2InterventionEngine(_fresh_redis())
        result = await engine.check_escalation(
            "user_abc",
            [
                _state("knowledge_bottleneck", 0.82, "tcp_congestion"),
                _state("transfer_failure", 0.75, "negative_transfer"),
            ],
        )
        assert result is not None
        assert result["pattern_name"] == "knowledge_crisis"
        assert "aurora_decision" not in result  # 前置不满足 → 纯 legacy（不炸、不半挂）

    @pytest.mark.asyncio
    async def test_no_pattern_still_returns_none(self):
        engine = L2InterventionEngine(_fresh_redis())
        assert await engine.check_escalation(_UUID_USER, [_state("random", 0.9, "x")]) is None

    @pytest.mark.asyncio
    async def test_empty_states_still_returns_none(self):
        engine = L2InterventionEngine(_fresh_redis())
        assert await engine.check_escalation(_UUID_USER, []) is None


class TestDecisionIdObservability:
    """P2-3（R2 返修）：契约决策的最小生产可观测点——两条 decision_id 结构化日志。

    模块用 loguru（非 stdlib logging），caplog 捕不到；挂临时 sink 断言。
    """

    @pytest.mark.asyncio
    async def test_check_escalation_logs_decision_id(self):
        from loguru import logger as loguru_logger

        engine = L2InterventionEngine(_fresh_redis())
        states = [
            _state("knowledge_bottleneck", 0.82, "tcp_congestion"),
            _state("transfer_failure", 0.75, "negative_transfer"),
        ]
        messages: list[str] = []
        sink_id = loguru_logger.add(messages.append, level="INFO")
        try:
            outcome = await engine.check_escalation(_UUID_USER, states)
        finally:
            loguru_logger.remove(sink_id)
        assert outcome is not None
        contract = aurora_decision_from_dict(outcome["aurora_decision"])
        assert contract is not None
        logged = [message for message in messages if "aurora_decision_id=" in message]
        assert logged, "check_escalation 必须留下 decision_id 结构化日志"
        assert contract.decision_id_or_compute() in logged[0]
        assert "catalog=rescope" in logged[0]

    @pytest.mark.asyncio
    async def test_decide_fired_logs_decision_id(self):
        from loguru import logger as loguru_logger

        engine = L2InterventionEngine(_fresh_redis())
        states = [
            _state("knowledge_bottleneck", 0.82, "tcp_congestion"),
            _state("transfer_failure", 0.75, "negative_transfer"),
        ]
        messages: list[str] = []
        sink_id = loguru_logger.add(messages.append, level="INFO")
        try:
            contract = await engine.decide(_UUID_USER, states)
        finally:
            loguru_logger.remove(sink_id)
        assert contract is not None and contract.validate() == ()
        logged = [message for message in messages if "aurora_decision_id=" in message]
        assert logged, "decide() 必须留下 decision_id 结构化日志"
        assert contract.decision_id_or_compute() in logged[0]
