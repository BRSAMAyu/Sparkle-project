from app.services.layer_conflict_resolver import LayerConflictResolver


def test_layer_conflict_resolver_prefers_episode_when_context_specific_conflict_exists() -> None:
    resolver = LayerConflictResolver()

    report = resolver.resolve_field_conflict(
        learning_key="challenge_style",
        layer_values=[
            {"layer": "profile", "value": "gentle", "confidence": 0.85, "repeated_evidence": 4, "updated_at": "2026-04-01T09:00:00"},
            {"layer": "episode", "value": "firm", "confidence": 0.82, "repeated_evidence": 2, "updated_at": "2026-04-05T09:00:00"},
            {"layer": "session", "value": "firm", "confidence": 0.9, "repeated_evidence": 1, "updated_at": "2026-04-05T10:00:00"},
        ],
        context_preferred_layer="episode",
    )

    assert report is not None
    assert report.winner == "episode"
    assert "profile" in report.blocked_layers


def test_layer_conflict_resolver_marks_review_due_and_stale_items() -> None:
    resolver = LayerConflictResolver()

    stale = resolver.stale_items_from_governance(
        {
            "difficulty_level": {"expires_at": "2026-04-01T09:00:00", "status": "active"},
            "retrieval_emphasis": {"review_after": "2026-04-01T09:00:00", "status": "active"},
        }
    )

    statuses = {item["learning_key"]: item["status"] for item in stale}
    assert statuses["difficulty_level"] == "stale"
    assert statuses["retrieval_emphasis"] == "review_due"
