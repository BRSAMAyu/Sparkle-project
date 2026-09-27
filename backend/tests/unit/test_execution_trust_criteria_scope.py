"""V3-FIX-316：execution_trust criteria/schema 契约只读 raw_result 顶层——裁决 (a) 钉住。

wt601 登记：载荷嵌在 output 键下时 structured_output criteria 测不到嵌套字段，
"顶层契约是设计还是巧合"待消费面裁决。wt614 裁决=顶层契约是设计：

- 生产唯一评估入口 execution_ingestor._evaluate（app/services/execution_ingestor.py）
  传入的 raw_result = _build_evaluation_input(parsed)：ResultParser 标准化形状里
  output 恒为 str（消息文本），结构化载荷恒在 parsed_output，评估前由
  _build_evaluation_input 把 parsed_output 键 setdefault 提升到顶层——
  模板契约（execution_template_service）success_criteria.required_fields 与
  result_contract.parsed_output_schema.required 同名字段正是按此设计可达顶层。
- 原始边界 fail-closed：若执行器真的把 dict 塞进 raw 响应的 output，
  ResultParser.parse 走 parse_error 分支（success=False），不会进入信任评估。
- 嵌套形状只存在于手工构造的测试夹具；若 criteria 下探 output 嵌套，
  反而会绕过 parsed_output_schema 的实际 schema 校验放行未验证载荷。

本文件钉住：criteria/schema 只读顶层（嵌套 fail-closed）+ 生产提升链可达顶层
（设计契约），防止未来被当 bug"修"成下探查询。
"""

from __future__ import annotations

from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.openclaw.result_parser import ResultParser
from app.core.execution_trust import ExecutionTrustEngine
from app.models.execution_intent import TrustLevel
from app.services.execution_ingestor import ExecutionIngestor

_CRITERIA = {
    "type": "structured_output",
    "required_fields": ["summary", "key_findings", "sources"],
}


def _hoisting_ingestor() -> ExecutionIngestor:
    """仅调 _build_evaluation_input（纯 dict 运算），db 永不被触碰——哑占位即可。"""
    return ExecutionIngestor(db=cast("AsyncSession", object()), redis=None)


def test_structured_output_criteria_never_probe_output_nesting() -> None:
    """wt601 踩中形状钉死为设计：载荷嵌 output 键时 criteria 必须不通过（fail-closed）。

    空契约隔离出 criteria 分支：唯一拒绝原因应为 success_criteria_not_met，
    且绝不因嵌套载荷字段名与 required_fields 撞名而放行。
    """
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={"output": {"summary": "s", "key_findings": ["a"], "sources": ["x"]}},
        success_criteria=_CRITERIA,
        result_contract={},
    )

    assert evaluation.trust_level == TrustLevel.RAW
    assert "success_criteria_not_met" in evaluation.reasons
    assert "schema_and_criteria_passed" not in evaluation.reasons


def test_schema_contract_required_fields_also_top_level_only() -> None:
    """schema 契约（result_contract.required_fields）同样只读顶层：嵌套字段不计入校验。"""
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={"output": {"summary": "s", "key_findings": ["a"], "sources": ["x"]}},
        success_criteria={},
        result_contract={"required_fields": ["summary", "key_findings", "sources"]},
    )

    assert evaluation.trust_level == TrustLevel.RAW
    assert evaluation.validation_total == 3
    assert evaluation.validation_passed == 0
    assert "schema_validation_below_50pct" in evaluation.reasons


def test_production_payload_reaches_criteria_via_parsed_output_hoisting() -> None:
    """生产链契约钉住：载荷经 parsed_output 提升到顶层后 criteria/schema 均可达。

    ResultParser 标准化形状（output=str、载荷在 parsed_output）→
    _build_evaluation_input 提升 → 顶层校验通过 VALIDATED。
    """
    parser = ResultParser()
    parsed = parser.parse(
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"summary": "s", "key_findings": ["a"], "sources": ["x"]}',
                        }
                    ],
                }
            ],
            "usage": {"input_tokens": 1},
        }
    )
    assert parsed["success"] is True
    assert isinstance(parsed["output"], str)
    assert parsed["parsed_output"] is not None

    ingestor = _hoisting_ingestor()
    evaluation_input = ingestor._build_evaluation_input(parsed)

    engine = ExecutionTrustEngine()
    evaluation = engine.evaluate(
        raw_result=evaluation_input,
        success_criteria=_CRITERIA,
        result_contract={"required_fields": _CRITERIA["required_fields"]},
    )

    assert evaluation.trust_level == TrustLevel.VALIDATED
    assert evaluation.validation_passed == 3
    assert evaluation.validation_total == 3
    assert "schema_and_criteria_passed" in evaluation.reasons


def test_hoisting_never_lets_nested_payload_override_top_level_output() -> None:
    """提升契约：parsed_output 同名键不覆盖顶层（setdefault）——嵌套载荷不能劫持 output。"""
    ingestor = _hoisting_ingestor()

    evaluation_input = ingestor._build_evaluation_input(
        {"output": "顶层文本", "parsed_output": {"output": "嵌套载荷", "summary": "s"}}
    )

    assert evaluation_input["output"] == "顶层文本"
    assert evaluation_input["summary"] == "s"
