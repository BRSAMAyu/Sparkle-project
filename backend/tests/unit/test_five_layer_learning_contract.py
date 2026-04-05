from datetime import datetime, timedelta, timezone

from app.services.five_layer_learning_contract import (
    DEFAULT_FIVE_LAYER_CONTRACT,
    REASON_TAXONOMY,
    filter_active_learnings,
    learning_is_active,
    learning_status,
)


def test_five_layer_contract_declares_all_layers_and_reason_taxonomy() -> None:
    contract = DEFAULT_FIVE_LAYER_CONTRACT

    assert contract.version
    assert set(contract.layers.keys()) == {"constitutional", "session", "episode", "profile", "system"}
    assert contract.reason_taxonomy == REASON_TAXONOMY


def test_five_layer_contract_thresholds_match_phase_e_defaults() -> None:
    contract = DEFAULT_FIVE_LAYER_CONTRACT

    episode = contract.promotion_threshold("episode", "companion_session_to_episode")
    profile = contract.promotion_threshold("profile", "companion_session_to_profile")
    conflict_overwrite = contract.promotion_threshold("profile", "companion_conflict_overwrite")
    outcome_profile = contract.promotion_threshold("profile", "outcome_learning_to_profile")

    assert episode.min_matching_revisions == 2
    assert episode.min_confidence == 0.7
    assert episode.review_window_days == 14
    assert profile.min_matching_revisions == 3
    assert profile.min_distinct_sessions == 2
    assert profile.min_confidence == 0.8
    assert conflict_overwrite.min_matching_revisions == 4
    assert conflict_overwrite.min_distinct_sessions == 3
    assert conflict_overwrite.min_confidence == 0.9
    assert outcome_profile.sample_count_threshold == 3
    assert outcome_profile.unique_sessions_threshold == 2


def test_five_layer_contract_declares_active_only_runtime_policy() -> None:
    contract = DEFAULT_FIVE_LAYER_CONTRACT

    assert contract.effective_runtime_statuses == ("active",)
    assert set(contract.inactive_runtime_statuses) == {"blocked", "demoted", "review_due", "stale"}
    assert contract.review_due_runtime_policy == "exclude_until_revalidated"


def test_learning_status_helpers_exclude_review_due_and_stale_from_runtime_state() -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    assert learning_status({"status": "blocked"}, now=now) == "blocked"
    assert learning_status({"status": "demoted"}, now=now) == "demoted"
    assert learning_status({"review_after": (now - timedelta(days=1)).isoformat()}, now=now) == "review_due"
    assert learning_status({"expires_at": (now - timedelta(days=1)).isoformat()}, now=now) == "stale"
    assert learning_is_active({"status": "active"}, now=now) is True
    assert learning_is_active({"review_after": (now - timedelta(days=1)).isoformat()}, now=now) is False


def test_filter_active_learnings_splits_active_and_inactive_entries() -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active, inactive, summary = filter_active_learnings(
        [
            {"learning_key": "still_good", "summary": "Active"},
            {"learning_key": "needs_review", "summary": "Review due"},
            {"learning_key": "demoted_rule", "summary": "Demoted"},
        ],
        {
            "still_good": {"status": "active"},
            "needs_review": {"review_after": (now - timedelta(hours=2)).isoformat()},
            "demoted_rule": {"status": "demoted"},
        },
        now=now,
    )

    assert [item["learning_key"] for item in active] == ["still_good"]
    assert {item["learning_key"] for item in inactive} == {"needs_review", "demoted_rule"}
    assert summary["still_good"]["active"] is True
    assert summary["needs_review"]["status"] == "review_due"
