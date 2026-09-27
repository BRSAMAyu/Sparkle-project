"""V3-FIX-307：execution_trust 缺省通过必须如实标注（红→绿实录）。

wt587 F6 / wt591 二轮复核存活项：空契约（0 项 schema 校验）与未知
criteria_type 双缺省通过时，reasons 仍自称 "schema_and_criteria_passed"，
而该标签经 execution_service 信任通道（trust_level 落库 / trust_bucket
审批策略）被当作"已验证"消费。

修法边界（卡片明令）：只修自称文案——reasons 如实标注 skipped/unknown；
VALIDATED 缺省通过语义本身不变（不把缺省改成拒绝）。
"""

from app.core.execution_trust import ExecutionTrustEngine
from app.models.execution_intent import TrustLevel


def _rich_result() -> dict:
    # 5 键 output：richness 拿满 0.3，配合 criteria 0.3 越过 0.3 门槛
    return {"output": {f"key_{i}": i for i in range(5)}}


def test_empty_contract_and_criteria_no_longer_claims_passed() -> None:
    """空契约 + 无 criteria：VALIDATED 保留，但不得自称 schema_and_criteria_passed。"""
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result=_rich_result(),
        success_criteria={},
        result_contract={},
    )

    # 缺省通过语义不动（修的是自称文案，不是改拒绝）
    assert evaluation.trust_level == TrustLevel.VALIDATED
    assert evaluation.validation_total == 0

    # 如实标注：0 项 schema 校验 + criteria 未指定
    assert "schema_not_evaluated" in evaluation.reasons
    assert "criteria_not_specified" in evaluation.reasons
    assert "schema_and_criteria_passed" not in evaluation.reasons


def test_unknown_criteria_type_annotated_not_claimed() -> None:
    """未知 criteria_type（含拼写错误）：零告警缺省通过必须标注，不得自称 passed。"""
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result=_rich_result(),
        success_criteria={"type": "structured_ouput", "required_fields": ["missing_field"]},
        result_contract={},
    )

    # 语义不动：拼错 type 不翻转为拒绝（消费面裁决超出本卡）
    assert evaluation.trust_level == TrustLevel.VALIDATED
    # required_fields 根本没被检查的事实必须如实入 reasons
    assert any(r.startswith("criteria_unknown_type:") for r in evaluation.reasons)
    assert "schema_and_criteria_passed" not in evaluation.reasons


def test_fully_specified_checks_still_claim_passed() -> None:
    """契约与 criteria 齐备且已知类型：VALIDATED + 自称 passed 原样保留（回归守护）。"""
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        # criteria 按既有语义对 raw_result 顶层字段检查（非 output 嵌套）
        raw_result={"output": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5}, "a": 1, "b": 2},
        success_criteria={"type": "structured_output", "required_fields": ["a", "b"]},
        result_contract={"required_fields": ["output"]},
    )

    assert evaluation.trust_level == TrustLevel.VALIDATED
    assert evaluation.validation_passed == 1
    assert evaluation.validation_total == 1
    assert "schema_and_criteria_passed" in evaluation.reasons
    assert not any(
        r.startswith(("schema_not_evaluated", "criteria_not_specified", "criteria_unknown_type"))
        for r in evaluation.reasons
    )
