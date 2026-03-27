from app.core.execution_router import ExecutionRouter
from app.core.execution_trust import ExecutionTrustEngine
from app.models.execution_intent import ExecutionMode, ExecutionTargetEnv, TrustLevel


def test_execution_router_returns_human_when_openclaw_disabled() -> None:
    router = ExecutionRouter(openclaw_enabled=False)

    decision = router.classify(
        task_type="OCR",
        goal="整理网页资料并总结",
    )

    assert decision.execution_mode == ExecutionMode.HUMAN
    assert decision.reason == "openclaw_disabled"


def test_execution_router_blocks_learning_tasks() -> None:
    router = ExecutionRouter(openclaw_enabled=True)

    decision = router.classify(
        task_type="LEARNING",
        goal="复习线性代数概念",
    )

    assert decision.execution_mode == ExecutionMode.HUMAN
    assert decision.reason == "task_type_excluded:learning"


def test_execution_router_routes_low_risk_readonly_tasks_to_agent() -> None:
    router = ExecutionRouter(openclaw_enabled=True)

    decision = router.classify(
        task_type="OCR",
        goal="搜索网页并整理 PDF 摘要",
        has_side_effects=False,
    )

    assert decision.execution_mode == ExecutionMode.AGENT
    assert decision.target_env == ExecutionTargetEnv.BROWSER


def test_execution_router_routes_side_effect_tasks_with_clear_criteria_to_hybrid() -> None:
    router = ExecutionRouter(openclaw_enabled=True)

    decision = router.classify(
        task_type="PLANNING",
        goal="调用 API 更新任务状态",
        has_side_effects=True,
        has_clear_criteria=True,
    )

    assert decision.execution_mode == ExecutionMode.HYBRID
    assert decision.target_env == ExecutionTargetEnv.API
    assert "requires_user_approval" in decision.risk_flags


def test_execution_trust_engine_rejects_empty_results() -> None:
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={},
        success_criteria={},
        result_contract={},
    )

    assert evaluation.trust_level == TrustLevel.RAW
    assert evaluation.reasons == ["empty_result"]


def test_execution_trust_engine_validates_structured_output() -> None:
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={
            "title": "日报摘要",
            "summary": "今天整理了三篇资料。",
            "parsed_output": {"title": "日报摘要", "summary": "今天整理了三篇资料。"},
        },
        success_criteria={"type": "structured_output", "required_fields": ["title", "summary"]},
        result_contract={"required_fields": ["title", "summary"]},
    )

    assert evaluation.trust_level == TrustLevel.VALIDATED
    assert evaluation.validation_passed == 2
    assert evaluation.validation_total == 2
    assert evaluation.can_update_task is True


def test_execution_trust_engine_blocks_sensitive_content() -> None:
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={"output": "token=abc123"},
        success_criteria={"type": "non_empty"},
        result_contract={},
    )

    assert evaluation.trust_level == TrustLevel.RAW
    assert evaluation.blocked_fields == ["sensitive_content:token"]


def test_execution_trust_engine_allows_token_usage_metadata() -> None:
    engine = ExecutionTrustEngine()

    evaluation = engine.evaluate(
        raw_result={
            "output": "整理完成",
            "token_usage": {"input_tokens": 10, "output_tokens": 20},
        },
        success_criteria={"type": "non_empty"},
        result_contract={},
    )

    assert evaluation.trust_level == TrustLevel.VALIDATED
