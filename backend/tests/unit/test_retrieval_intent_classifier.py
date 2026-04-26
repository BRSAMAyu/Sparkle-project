from __future__ import annotations

import pytest

from app.orchestration.retrieval_intent import (
    RetrievalIntentBudgets,
    RetrievalIntentClassifier,
    build_retrieval_decision,
)
from app.orchestration.session_state_mixin import SessionStateMixin
from app.orchestration.statechart_engine import WorkflowState


@pytest.mark.parametrize(
    ("message", "expected_mode"),
    [
        ("I'm really stressed about my exam", "skip"),
        ("I feel anxious and overwhelmed tonight", "skip"),
        ("hello!", "skip"),
        ("thanks, that helps", "skip"),
        ("add a task to review chapter 3", "skip"),
        ("mark my calculus homework done", "skip"),
        ("把操作系统第三章加入任务", "skip"),
        ("explain virtual memory", "aggressive"),
        ("how does TCP congestion control work?", "aggressive"),
        ("help me understand dynamic programming", "aggressive"),
        ("what is a page table?", "aggressive"),
        ("compare paging and segmentation", "aggressive"),
        ("derive the Bayes theorem formula", "aggressive"),
        ("解释一下虚拟内存的原理", "aggressive"),
        ("make me a study plan for OS finals", "selective"),
        ("can you plan my revision schedule?", "selective"),
        ("break down my database exam prep", "selective"),
        ("help me with chapter 4", "selective"),
        ("I'm stuck on this topic", "selective"),
        ("can you help with my lecture notes?", "selective"),
    ],
)
def test_retrieval_intent_classifier_diverse_messages(message: str, expected_mode: str) -> None:
    decision = RetrievalIntentClassifier().classify(message)

    assert decision.retrieval_mode == expected_mode
    assert decision.should_retrieve is (expected_mode != "skip")
    assert decision.budget_tokens == 0 if expected_mode == "skip" else decision.budget_tokens > 0


@pytest.mark.parametrize(
    "message",
    [
        "I'm really stressed about my exam",
        "I am panicking about finals",
        "今天压力好大，有点崩溃",
        "I feel anxious and overwhelmed tonight",
    ],
)
def test_emotional_messages_never_trigger_retrieval(message: str) -> None:
    classifier = RetrievalIntentClassifier()

    assert classifier.classify(message).should_retrieve is False
    assert classifier.classify(message, aurora_doc_context_mode="aggressive").should_retrieve is False


def test_session_toggle_disables_document_context() -> None:
    decision = build_retrieval_decision(
        message="explain virtual memory",
        context={"session_flags": {"use_document_context": False}},
    )

    assert decision.should_retrieve is False
    assert decision.retrieval_mode == "skip"
    assert decision.reason == "session_use_document_context_false"


def test_aurora_mode_can_skip_or_cap_positive_decisions() -> None:
    classifier = RetrievalIntentClassifier()
    budgets = RetrievalIntentBudgets(aggressive=2000, selective=800, ambiguous=400)

    skipped = classifier.classify("explain virtual memory", aurora_doc_context_mode="off", budgets=budgets)
    capped = classifier.classify("explain virtual memory", aurora_doc_context_mode="selective", budgets=budgets)

    assert skipped.should_retrieve is False
    assert skipped.retrieval_mode == "skip"
    assert capped.should_retrieve is True
    assert capped.retrieval_mode == "selective"
    assert capped.budget_tokens == 800


def test_session_state_overlay_attaches_retrieval_decision() -> None:
    state = WorkflowState()

    payload = SessionStateMixin._attach_retrieval_decision(
        user_context_payload={"user_context": {"user_id": "user-1"}},
        state=state,
        user_message="help me understand virtual memory",
        route_intent="knowledge",
    )

    assert payload is not None
    assert payload["retrieval_decision"]["retrieval_mode"] == "aggressive"
    assert payload["document_retrieval_decision"] == payload["retrieval_decision"]
    assert state.context_data["retrieval_decision"] == payload["retrieval_decision"]
