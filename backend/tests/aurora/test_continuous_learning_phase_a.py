from __future__ import annotations

from uuid import uuid4

import pytest

from app.aurora.schemas import DistilledStrategy, DistilledStrategyLifecycle, ProjectionPolicy, Shareability
from app.learning.attributor import AttributionSignalBundle, detect_successful_attribution
from app.learning.deidentifier import deidentify_text
from app.learning.distiller import DistillationInput, distill_strategy
from app.learning.pipeline import review_distilled_strategy, run_continuous_learning_pipeline
from app.learning.quality_gate import evaluate_strategy_quality
from app.learning.retrieval import RetrievalQueryInput, build_distilled_strategy_refs
from app.learning.seed_bridge import import_seed_library_content
from app.learning.strategy_store import InMemoryDistilledStrategyStore, StrategyLifecycleError, StrategyQuery


def _bundle(**overrides):
    payload = {
        "user_id": uuid4(),
        "scenario_pack_id": "exam_prep_14d",
        "goal_achieved": True,
        "task_completion_streak": 4,
        "positive_feedback_score": 0.8,
        "behavioral_improvement_score": 0.7,
        "outcome_summary": "通过把复习切成 25 分钟最小行动，用户连续 4 天保持节奏。",
        "interventions": ["25 分钟最小行动", "晚间固定复盘"],
        "context_excerpt": "一个东北大三学生在备考期通过最小行动重新找回节奏。",
        "subject_tags": ["英语", "备考"],
        "source_refs": ["task:1", "feedback:1"],
    }
    payload.update(overrides)
    return AttributionSignalBundle(**payload)


def _strategy() -> DistilledStrategy:
    imported = import_seed_library_content()
    return imported[0]


def test_strategy_store_crud_and_lifecycle_transitions() -> None:
    strategy = _strategy().model_copy(update={"status": DistilledStrategyLifecycle.DISTILLED})
    store = InMemoryDistilledStrategyStore()
    created = store.create(strategy)
    assert created.status == DistilledStrategyLifecycle.DISTILLED

    reviewed = store.transition(strategy.id, DistilledStrategyLifecycle.USER_REVIEWED, user_authorization=True)
    assert reviewed.status == DistilledStrategyLifecycle.USER_REVIEWED
    assert reviewed.user_authorization is True

    community_shared = store.transition(strategy.id, DistilledStrategyLifecycle.COMMUNITY_SHARED)
    assert community_shared.status == DistilledStrategyLifecycle.COMMUNITY_SHARED
    assert store.list(StrategyQuery(statuses=(DistilledStrategyLifecycle.COMMUNITY_SHARED,)))[0].id == strategy.id

    with pytest.raises(StrategyLifecycleError):
        store.transition(strategy.id, DistilledStrategyLifecycle.DISTILLED)


def test_attribution_detector_identifies_successful_outcome() -> None:
    candidate = detect_successful_attribution(_bundle())
    assert candidate is not None
    assert candidate.success_score >= 0.7


def test_quality_gate_rejects_low_evidence() -> None:
    strategy = _strategy().model_copy(
        update={
            "evidence_strength": 0.3,
            "diversity_score": 0.15,
            "deidentification_verified": False,
            "safety_audit": {"deidentified": False, "reviewed": False, "safe": True},
        }
    )
    decision = evaluate_strategy_quality(strategy)
    assert not decision.passed
    assert "evidence_strength_below_threshold" in decision.reasons


def test_deidentifier_removes_sensitive_markers() -> None:
    result = deidentify_text("东北大三学生在2026年4月备考期，因为妈妈生病只能晚上学习。")
    assert result.passed
    assert "东北" not in result.sanitized_text
    assert "大三" not in result.sanitized_text
    assert "妈妈" not in result.sanitized_text


def test_pipeline_stops_when_deidentifier_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARKLE_WS7_DISTILLER_ENABLED", "true")
    bundle = _bundle(context_excerpt="请联系 13800138000 获取该用户更多信息。")
    store = InMemoryDistilledStrategyStore()
    result = run_continuous_learning_pipeline(bundle, store)
    assert result.status == "blocked_by_deidentifier"
    assert store.list() == []


def test_pipeline_creates_reviewable_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARKLE_WS7_DISTILLER_ENABLED", "true")
    bundle = _bundle()
    store = InMemoryDistilledStrategyStore()
    result = run_continuous_learning_pipeline(bundle, store)
    assert result.status == "created"
    assert result.strategy is not None
    assert result.strategy.status == DistilledStrategyLifecycle.DISTILLED
    reviewed = review_distilled_strategy(result.strategy.id, store, approved=True)
    assert reviewed.status == DistilledStrategyLifecycle.USER_REVIEWED


def test_retrieval_integration_returns_signal_snapshot_refs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPARKLE_WS7_RETRIEVAL_ENABLED", "true")
    strategies = import_seed_library_content()
    store = InMemoryDistilledStrategyStore(initial=strategies)
    refs = build_distilled_strategy_refs(RetrievalQueryInput(text="一元二次方程 示例"), store)
    assert refs


def test_seed_bridge_imports_human_authored_reviewed_strategies() -> None:
    strategies = import_seed_library_content()
    assert strategies
    assert all(strategy.source_trajectory_type == "human_authored" for strategy in strategies)
    assert all(strategy.status == DistilledStrategyLifecycle.USER_REVIEWED for strategy in strategies)
    assert all(strategy.shareability == Shareability.PUBLIC_SEED_CANDIDATE for strategy in strategies)
    assert all(strategy.user_authorization is True for strategy in strategies)
