from app.orchestration.task_decomposition_contract import (
    build_task_decomposition_contract,
    generate_contract_clarification_questions,
)


def test_build_contract_extracts_core_fields() -> None:
    contract = build_task_decomposition_contract(
        message=(
            "我想在8周内通过算法面试，每天2小时，先补数据结构再刷题，"
            "目标是周测正确率达到85%，我担心时间不够。"
        ),
        intent="create_plan",
        extracted_entities={},
        conversation_context=[],
    )

    assert contract.goal
    assert contract.constraints
    assert contract.milestones
    assert contract.acceptance_criteria
    assert contract.score > 0.45


def test_build_contract_flags_missing_goal() -> None:
    contract = build_task_decomposition_contract(
        message="",
        intent="create_plan",
        extracted_entities={},
        conversation_context=[],
    )
    assert "missing_goal" in contract.gaps


def test_generate_questions_from_gaps() -> None:
    questions = generate_contract_clarification_questions(
        ["missing_goal", "missing_constraints", "missing_acceptance_criteria"]
    )
    assert len(questions) == 3
