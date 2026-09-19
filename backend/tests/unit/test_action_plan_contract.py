"""X-01 · ActionPlan V3 契约（app/core/action_plan.py）的封闭词表与校验面测试。

对应任务卡验收：
- Human/Agent/Hybrid 可表达（三模式各构造一条合法记录）；
- 关键字段不能仅自然语言携带（类型化 evidence / typed useful_because / 封闭 ref scheme）；
- 旧记录全兼容（action_schema_version NULL = legacy，重构返回 None）。
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.action_plan import (
    ACTION_PLAN_SCHEMA_VERSION,
    ACTION_SOURCE_REF_SCHEMES,
    ActionPlanContract,
    CognitiveOwnership,
    CompletionEvidenceSpec,
    EvidenceKind,
    RiskClass,
    SmallestUsefulStep,
    UsefulStepReason,
    action_plan_from_task,
    normalize_execution_mode,
)
from app.models.execution_intent import ExecutionMode, TrustLevel


def _legal_contract(execution_mode: ExecutionMode) -> ActionPlanContract:
    """三模式通用的最小合法 V3 契约。"""
    return ActionPlanContract(
        desired_outcome="能独立讲清楚贝叶斯更新的适用条件",
        smallest_useful_step=SmallestUsefulStep(
            description="用自己的话写 3 条适用条件并各配 1 个反例",
            useful_because=(UsefulStepReason.BUILDS_CAPABILITY, UsefulStepReason.REDUCES_UNCERTAINTY),
        ),
        completion_evidence=(
            CompletionEvidenceSpec(evidence_kind=EvidenceKind.ARTIFACT, ref="document://abc-123"),
            CompletionEvidenceSpec(evidence_kind=EvidenceKind.USER_CONFIRMATION),
        ),
        execution_mode=execution_mode,
        cognitive_ownership=CognitiveOwnership.USER_CORE,
        source_refs=(f"goal://{uuid4()}", "memory://episodic/00000000-0000-0000-0000-000000000001"),
        risk_class=RiskClass.LOW,
        reversible=True,
    )


class TestVocabularyClosure:
    def test_schema_version_is_v1(self):
        assert ACTION_PLAN_SCHEMA_VERSION == "action_plan.v1"

    def test_execution_mode_reuses_frozen_execution_intent_enum(self):
        """Action 唯一协议 = ExecutionIntent（B-06 §1.5）：execution_mode 词表必须直接复用，
        禁止第二套 HUMAN/AGENT/HYBRID 枚举。"""
        assert {m.value for m in ExecutionMode} == {"human", "agent", "hybrid"}

    def test_cognitive_ownership_first_version_d13(self):
        assert {m.value for m in CognitiveOwnership} == {"user_core", "shared", "delegated"}

    def test_risk_class_grading(self):
        assert {m.value for m in RiskClass} == {"low", "medium", "high", "critical"}

    def test_evidence_kinds_cover_action_doc_section4(self):
        assert {m.value for m in EvidenceKind} == {
            "artifact",
            "file",
            "code",
            "quiz_result",
            "user_confirmation",
            "self_report",
            "system_event",
        }

    def test_useful_step_reasons_cover_action_doc_section2(self):
        assert {m.value for m in UsefulStepReason} == {
            "produces_artifact",
            "reduces_uncertainty",
            "builds_capability",
            "unblocks_dependency",
            "enables_decision",
            "advances_goal",
        }

    def test_source_ref_schemes_closed_and_c01_aligned(self):
        """C-01 decision_context.v1 的 5 个 scheme 必须原样包含（ref 语义对齐），
        其余为 action 域扩展。"""
        c01_schemes = {"memory", "user_state", "plan", "document", "profile"}
        assert c01_schemes <= ACTION_SOURCE_REF_SCHEMES
        assert ACTION_SOURCE_REF_SCHEMES - c01_schemes == {"goal", "task", "subtask", "chat", "decision", "run"}


class TestThreeExecutionModesAreExpressible:
    @pytest.mark.parametrize("mode", list(ExecutionMode))
    def test_each_mode_constructs_a_legal_contract(self, mode: ExecutionMode):
        contract = _legal_contract(mode)
        assert contract.validate() == ()
        columns = contract.to_task_columns()
        assert columns["execution_mode"] == mode.value
        assert columns["action_schema_version"] == ACTION_PLAN_SCHEMA_VERSION

    @pytest.mark.parametrize("mode", list(ExecutionMode))
    def test_each_mode_maps_to_trust_levels_of_execution_intent(self, mode: ExecutionMode):
        """HUMAN/AGENT/HYBRID 与 TrustLevel（RAW/VALIDATED/TRUSTED）可组合表达执行语义。"""
        for trust in TrustLevel:
            contract = _legal_contract(mode)
            assert contract.validate() == ()
            assert trust.value in {"raw", "validated", "trusted"}


class TestValidationRejectsUnstructuredOrInvalidPayloads:
    def _invalid(self, **overrides):
        """从合法模板构造非法契约（frozen dataclass：直接构造，不 mutate）。"""
        base = _legal_contract(ExecutionMode.HUMAN)
        from dataclasses import replace

        return replace(base, **overrides)

    def test_free_text_completion_evidence_without_kind_is_rejected(self):
        """守卫核心：completion_evidence 不能是自由文本一列了事——必须类型化。"""
        contract = self._invalid(
            completion_evidence=(CompletionEvidenceSpec(evidence_kind=None, description="用户说做完了"),),  # type: ignore[arg-type]
        )
        violations = contract.validate()
        assert any("evidence_kind" in v for v in violations)

    def test_empty_completion_evidence_is_rejected(self):
        contract = self._invalid(completion_evidence=())
        assert any("completion_evidence" in v for v in contract.validate())

    def test_useful_step_without_reason_is_rejected(self):
        contract = self._invalid(
            smallest_useful_step=SmallestUsefulStep(description="打开 IDE 看一眼", useful_because=())
        )
        violations = contract.validate()
        assert any("useful_because" in v for v in violations)

    def test_unknown_source_ref_scheme_is_rejected(self):
        contract = self._invalid(source_refs=("ftp://random-host/file",))
        assert any("source ref" in v for v in contract.validate())

    def test_non_uri_source_ref_is_rejected(self):
        contract = self._invalid(source_refs=("只是一个描述字符串",))
        assert any("source ref" in v for v in contract.validate())

    def test_unknown_execution_mode_value_is_rejected_by_normalizer(self):
        assert normalize_execution_mode("robot") is None
        assert normalize_execution_mode("") is None
        assert normalize_execution_mode(None) is None

    def test_schema_version_mismatch_is_reported(self):
        contract = self._invalid(schema_version="action_plan.v999")
        assert any("schema_version" in v for v in contract.validate())


class TestExecutionModeNormalization:
    """tasks.execution_mode 是 String(20) 既有镜像列：历史写入大小写不一经 DTO 归一。"""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("human", ExecutionMode.HUMAN),
            ("HUMAN", ExecutionMode.HUMAN),
            ("Human", ExecutionMode.HUMAN),
            ("agent", ExecutionMode.AGENT),
            ("AGENT", ExecutionMode.AGENT),
            ("hybrid", ExecutionMode.HYBRID),
            (ExecutionMode.HYBRID, ExecutionMode.HYBRID),
        ],
    )
    def test_normalize(self, raw, expected):
        assert normalize_execution_mode(raw) is expected


class TestLegacyTaskCompat:
    def test_legacy_row_without_schema_version_yields_none(self):
        from app.models.task import Task

        task = Task(title="旧任务", type="LEARNING")
        # 未走 ORM 持久化，直接以实例属性模拟 legacy 行
        assert action_plan_from_task(task) is None

    def test_v3_row_roundtrips_through_task_columns(self):
        from app.models.task import Task

        contract = _legal_contract(ExecutionMode.HYBRID)
        task = Task(title="V3 任务", type="LEARNING")
        contract.apply_to_task(task)
        restored = action_plan_from_task(task)
        assert restored is not None
        assert restored.to_task_columns() == contract.to_task_columns()
        assert restored.validate() == ()
