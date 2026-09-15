from __future__ import annotations

import pytest

from app.services.metacognition_registry import (
    CONFIDENCE_PROXY_REGISTRY,
    ensure_registered_proxies,
)


def test_confidence_proxy_registry_contains_expected_five_proxies() -> None:
    assert set(CONFIDENCE_PROXY_REGISTRY) == {
        "revision_frequency",
        "self_correction_rate",
        "question_to_statement_ratio",
        "time_to_first_action",
        "completion_vs_estimate_delta_sign",
    }


def test_every_confidence_proxy_has_forbidden_interpretations() -> None:
    for definition in CONFIDENCE_PROXY_REGISTRY.values():
        assert definition.forbidden_interpretations
        assert definition.known_biases


def test_ensure_registered_proxies_preserves_registered_values() -> None:
    selected = ensure_registered_proxies(["revision_frequency", "time_to_first_action"])
    assert selected == ("revision_frequency", "time_to_first_action")


def test_ensure_registered_proxies_rejects_unknown_proxy() -> None:
    with pytest.raises(ValueError):
        ensure_registered_proxies(["freeform_confidence_proxy"])
