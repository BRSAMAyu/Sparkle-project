from app.api.v1 import profile_transparency as profile_api


def test_achievement_inferred_keys_have_transparency_labels_and_explanations() -> None:
    assert profile_api._INFERRED_KEY_LABELS["achievement_peak_hours"] == "成就高峰时段"
    assert profile_api._INFERRED_KEY_LABELS["achievement_reward_sensitivity"] == "成就奖励敏感度"
    assert profile_api._INFERRED_SOURCE_LABELS["achievement_signals"] == "成就行为"

    explanation = profile_api._localize_inferred_explanation(
        "achievement_motivation_response",
        "progress_praise",
        "",
    )
    assert "进度肯定型鼓励" in explanation
