from __future__ import annotations

from app.orchestration.clarification_voi_service import ClarificationVOIService
from app.orchestration.idea_crystallization_service import IdeaCrystallizationService


def test_idea_crystallization_generates_contract_and_profile() -> None:
    service = IdeaCrystallizationService()
    result = service.crystallize(
        message="我想做一个12周学习计划，先打基础再刷题，目标是考试90分",
        intent="study_plan",
        extracted_entities={"goal": "考试90分"},
        conversation_context=[{"role": "user", "content": "每天可投入2小时"}],
    )
    assert result.intent_hypotheses
    assert isinstance(result.draft_goal_contract, dict)
    assert "goal" in result.draft_goal_contract
    assert isinstance(result.ambiguity_profile, dict)
    ambiguity_score = float(result.ambiguity_profile.get("ambiguity_score", 0.0) or 0.0)
    assert 0.0 <= ambiguity_score <= 1.0


def test_clarification_voi_ranks_points_by_expected_gain() -> None:
    service = ClarificationVOIService()
    result = service.rank(
        contract={
            "gaps": [
                "missing_constraints",
                "missing_acceptance_criteria",
                "missing_goal_hierarchy",
            ],
        },
        ambiguity_profile={"ambiguity_score": 0.7},
        uncertainty_score=0.6,
        max_questions=3,
    )
    assert 0.0 <= result.voi_score <= 1.0
    assert 1 <= len(result.clarification_priority_points) <= 3
    gains = [float(item.get("expected_gain", 0.0)) for item in result.clarification_priority_points]
    assert gains == sorted(gains, reverse=True)
