from __future__ import annotations

import pytest

from app.services.metacognition_guard import scan_diagnostic_labels


@pytest.mark.parametrize(
    ("text", "pattern_id"),
    [
        ("你是拖延型。", "identity_type"),
        ("你是完美主义人格。", "identity_type"),
        ("你属于内向型。", "belongs_type"),
        ("你的性格就是容易焦虑。", "personality_trait"),
        ("你很拖延。", "diagnostic_tendency"),
        ("你比较焦虑。", "diagnostic_tendency"),
        ("你总是高估自己。", "absolute_always"),
        ("你从不做现实判断。", "absolute_never"),
    ],
)
def test_rule_ao_blocks_diagnostic_and_absolute_labels(
    text: str, pattern_id: str
) -> None:
    matches = scan_diagnostic_labels(text, source="test")
    assert matches
    assert matches[0].pattern_id == pattern_id


def test_rule_ao_allows_behavioral_observation_language() -> None:
    matches = scan_diagnostic_labels(
        "你过去 10 次对完成时间估得偏乐观 2.3 小时。", source="test"
    )
    assert matches == []
