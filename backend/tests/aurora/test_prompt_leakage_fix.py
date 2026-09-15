"""WS-RP1: Verify compiled UserInsightState is consumed by prompt render pipeline."""

from __future__ import annotations

from app.core.user_insight_state import InsightSignalEvidence, UserInsightState
from app.orchestration.prompts import (
    _normalize_user_context,
    build_system_prompt,
    format_user_context,
)


def _make_insight_state() -> UserInsightState:
    """Build a canonical insight state with representative signal evidence."""
    return UserInsightState(
        goals=[
            {"id": "goal:primary", "type": "exam_window", "label": "期末冲刺"},
        ],
        constraints=[
            {"id": "cognitive:perfectionism", "label": "完美主义回避", "type": "behavioral"},
        ],
        recent_pain_points=[
            {
                "id": "pain:error_summary",
                "type": "error_pressure",
                "label": "错题压力持续偏高",
                "details": {"total_errors": 8, "need_review_count": 3},
            },
        ],
        recent_wins=[
            {
                "id": "win:mastery:thermo-1",
                "type": "mastery_gain",
                "label": "热机效率",
                "old_mastery": 31.0,
                "new_mastery": 46.0,
            },
            {
                "id": "win:mastery:thermo-2",
                "type": "mastery_gain",
                "label": "卡诺循环",
                "old_mastery": 40.0,
                "new_mastery": 55.0,
            },
        ],
        stable_preferences={"depth_preference": 0.7, "curiosity_preference": 0.6},
        current_state={"overall_mastery": 0.52, "active_subjects": ["热力学"]},
        inferred_work_style={"preferred_tools": ["flashcard", "quiz"]},
        active_bottlenecks=[
            {"id": "knowledge:thermo-entropy", "label": "熵增方向", "type": "knowledge_gap", "mastery": 0.35},
        ],
        temporal_patterns={
            "calendar": {"exam_urgency": {"days_left": 12, "urgent": True}},
        },
        confidence_metadata={"error_summary": 0.92, "recent_errors": 0.85},
        freshness_metadata={"error_summary": "high", "recent_errors": "high"},
        signal_evidence=[
            InsightSignalEvidence(
                signal_id="error_summary",
                family="error",
                label="Error summary",
                source="error_book",
                value={"total_errors": 8, "need_review_count": 3, "subject_distribution": {"thermo": 5, "math": 3}},
                confidence=0.92,
                freshness="high",
            ),
            InsightSignalEvidence(
                signal_id="recent_errors",
                family="error",
                label="Recent errors",
                source="error_book",
                value=[
                    {"question_preview": "熵增方向判断", "subject": "thermo", "error_type": "概念混淆", "mastery": 0.35},
                    {"question_preview": "可逆过程条件", "subject": "thermo", "error_type": "推理跳步", "mastery": 0.42},
                ],
                confidence=0.85,
                freshness="high",
            ),
        ],
    )


def test_normalize_prefers_canonical_error_summary_over_raw_dict() -> None:
    """Canonical insight state error_summary takes priority over raw dict."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
        # Raw dict with DIFFERENT values — should be ignored when canonical has the field
        "cognitive_context": {
            "error_summary": {"total_errors": 1, "need_review_count": 0},
        },
    }
    normalized = _normalize_user_context(context)

    # Canonical source wins
    assert normalized["error_summary"]["total_errors"] == 8
    assert normalized["error_summary"]["need_review_count"] == 3


def test_normalize_prefers_canonical_recent_errors() -> None:
    """Canonical insight state recent_errors takes priority."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
    }
    normalized = _normalize_user_context(context)

    assert isinstance(normalized["recent_errors"], list)
    assert normalized["recent_errors"][0]["question_preview"] == "熵增方向判断"
    assert len(normalized["recent_errors"]) == 2


def test_normalize_prefers_canonical_mastery_changes_from_wins() -> None:
    """Canonical insight state recent_wins map to recent_mastery_changes."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
    }
    normalized = _normalize_user_context(context)

    assert "recent_mastery_changes" in normalized
    assert isinstance(normalized["recent_mastery_changes"], list)
    assert normalized["recent_mastery_changes"][0]["node_name"] == "热机效率"
    assert normalized["recent_mastery_changes"][0]["old_mastery"] == 31.0
    assert normalized["recent_mastery_changes"][0]["new_mastery"] == 46.0


def test_normalize_falls_back_to_raw_dict_when_no_insight_state() -> None:
    """When no UserInsightState is present, raw dict cascade still works."""
    context = {
        "cognitive_context": {
            "error_summary": {"total_errors": 5, "need_review_count": 2},
            "recent_errors": [{"question_preview": "Some error", "subject": "math"}],
            "recent_mastery_changes": [{"node_name": "微积分", "old_mastery": 30, "new_mastery": 45}],
        },
    }
    normalized = _normalize_user_context(context)

    assert normalized["error_summary"]["total_errors"] == 5
    assert normalized["recent_errors"][0]["question_preview"] == "Some error"
    assert normalized["recent_mastery_changes"][0]["node_name"] == "微积分"


def test_normalize_falls_back_when_insight_state_lacks_signal() -> None:
    """When UserInsightState exists but lacks a specific signal, raw dict fills in."""
    insight = UserInsightState()  # Empty state
    context = {
        "user_insight_state": insight,
        "cognitive_context": {
            "error_summary": {"total_errors": 3},
        },
    }
    normalized = _normalize_user_context(context)

    # insight state has no error_summary signal evidence → falls back to cognitive_context
    assert normalized["error_summary"]["total_errors"] == 3


def test_format_user_context_renders_canonical_signals() -> None:
    """The full prompt render path consumes canonical insight state."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
    }
    rendered = format_user_context(context, context_level="full")

    # Pain points from canonical state
    assert "【近期痛点】" in rendered
    assert "累计错题 8" in rendered
    assert "待复习 3" in rendered

    # Wins from canonical state
    assert "【近期进展】" in rendered
    assert "热机效率" in rendered

    # Inline snapshot should be present
    assert "【画像快照】" in rendered


def test_format_user_context_does_not_dump_raw_internal_payload() -> None:
    """Internal payload (confidence_metadata, freshness_metadata, etc.) must not appear as-is."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
    }
    rendered = format_user_context(context, context_level="full")

    # Internal fields should NOT be rendered as raw JSON
    assert "confidence_metadata" not in rendered
    assert "freshness_metadata" not in rendered
    assert "signal_evidence" not in rendered
    assert "calibration_summary" not in rendered


def test_build_system_prompt_telemetry_tracks_canonical_source() -> None:
    """Telemetry records that signals came from canonical_insight_state."""
    insight = _make_insight_state()
    context = {
        "user_insight_state": insight,
    }
    build_system_prompt(user_context=context, conversation_history={"messages": []})

    telemetry = context.get("prompt_signal_telemetry")
    assert telemetry is not None

    # At least error_summary should show canonical source
    error_meta = telemetry["high_value_fields"].get("error_summary", {})
    assert "canonical_insight_state" in error_meta.get("collected_sources", [])


def test_inline_snapshot_has_budget_discipline() -> None:
    """to_inline_snapshot() respects character budget."""
    insight = _make_insight_state()
    snapshot = insight.to_inline_snapshot()

    assert snapshot["available"] is True
    assert isinstance(snapshot["body"], str)
    assert len(snapshot["body"]) <= UserInsightState.INLINE_SNAPSHOT_BUDGET_CHARS
    assert snapshot["budget_chars"] == UserInsightState.INLINE_SNAPSHOT_BUDGET_CHARS


def test_inline_snapshot_empty_state() -> None:
    """An empty insight state produces an unavailable snapshot."""
    insight = UserInsightState()
    snapshot = insight.to_inline_snapshot()

    assert snapshot["available"] is False
    assert snapshot["body"] == ""
    assert snapshot["item_count"] == 0


def test_inline_snapshot_truncation() -> None:
    """Inline snapshot truncates when content exceeds budget."""
    # Create a state with many goals to exceed budget
    goals = [{"id": f"g:{i}", "type": "goal", "label": f"目标 {i}: " + "X" * 200} for i in range(20)]
    pains = [{"id": f"p:{i}", "label": f"痛点 {i}: " + "Y" * 200} for i in range(10)]
    wins = [{"id": f"w:{i}", "label": f"进展 {i}: " + "Z" * 200} for i in range(10)]
    constraints = [{"id": f"c:{i}", "label": f"约束 {i}: " + "W" * 200} for i in range(10)]

    insight = UserInsightState(
        goals=goals,
        constraints=constraints,
        recent_pain_points=pains,
        recent_wins=wins,
    )
    snapshot = insight.to_inline_snapshot()

    assert snapshot["available"] is True
    assert len(snapshot["body"]) <= UserInsightState.INLINE_SNAPSHOT_BUDGET_CHARS
    assert snapshot["truncated"] is True


def test_profile_context_attribute_extraction() -> None:
    """UserInsightState on a ProfileContext-like object is extracted."""

    class FakeProfileContext:
        user_insight_state = _make_insight_state()

    context = {"profile_context": FakeProfileContext()}
    normalized = _normalize_user_context(context)

    assert normalized["error_summary"]["total_errors"] == 8
    assert "recent_mastery_changes" in normalized
