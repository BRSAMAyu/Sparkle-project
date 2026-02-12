from __future__ import annotations

from app.services.meta_policy_composer_service import MetaPolicyComposerService


def test_meta_policy_composer_support_aware_blend():
    layers = [
        {
            "policy_id": "policy_global",
            "scope_type": "global",
            "scope_key": "all",
            "support_size": 500,
            "weights": {"semantic_weight": 0.4},
            "thresholds": {"min_selected_score": 0.34},
        },
        {
            "policy_id": "policy_cohort",
            "scope_type": "cohort",
            "scope_key": "cohort::study",
            "support_size": 120,
            "weights": {"semantic_weight": 0.5},
            "thresholds": {"min_selected_score": 0.38},
        },
    ]
    result = MetaPolicyComposerService.compose(
        strategy_pack="general_v2",
        channel="routing",
        layers=layers,
        cohort_id="cohort::study",
        user_scope="usr::111111111111",
    )
    assert result["policy_id"].startswith("meta_policy_v1:routing:general_v2:")
    assert result["meta_learning_scope"] == "composed"
    assert float(result["weights"]["semantic_weight"]) > 0.0
    assert len(result["selected_layers"]) == 2
