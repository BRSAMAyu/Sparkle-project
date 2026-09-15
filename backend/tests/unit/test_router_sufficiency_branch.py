from app.config import settings
from app.orchestration.routing_engine import RoutingEngineMixin
from app.state_aggregator.schema import SufficiencySummaryValue


class _RoutingHarness(RoutingEngineMixin):
    pass


def test_router_sufficiency_branch_only_uses_task_score(monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", True, raising=False)
    harness = _RoutingHarness()

    follow_up_question, context_caveat = harness._build_stage20_prompt_additions(
        task_summary=SufficiencySummaryValue(
            score=0.42,
            top_missing_dimensions=("target_object_resolved", "constraint_explicit"),
        ),
        context_summary=SufficiencySummaryValue(
            score=0.2,
            top_missing_dimensions=("recent_user_state_known", "social_context_loaded"),
        ),
    )

    assert follow_up_question is not None
    assert "近期的活跃节奏" in context_caveat
    assert "社交背景" in context_caveat


def test_router_sufficiency_branch_stays_off_when_flag_is_disabled(monkeypatch):
    monkeypatch.setattr(settings, "SPARKLE_ROUTER_SUFFICIENCY_BRANCH_ENABLED", False, raising=False)
    harness = _RoutingHarness()

    follow_up_question, context_caveat = harness._build_stage20_prompt_additions(
        task_summary=SufficiencySummaryValue(
            score=0.3,
            top_missing_dimensions=("intent_clarity",),
        ),
        context_summary=SufficiencySummaryValue(
            score=0.4,
            top_missing_dimensions=("relevant_memory_present",),
        ),
    )

    assert follow_up_question is None
    assert "记忆线索" in context_caveat
