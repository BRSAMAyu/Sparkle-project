from app.orchestration.companion_constitution import COMPANION_CONSTITUTION, CONSTITUTION_VERSION
from app.orchestration.companion_identity_kernel import IDENTITY_KERNEL_VERSION, SPARKLE_IDENTITY_KERNEL


def test_companion_constitution_artifact_schema_is_complete() -> None:
    assert COMPANION_CONSTITUTION.version == CONSTITUTION_VERSION
    assert COMPANION_CONSTITUTION.user_centered_telos
    assert COMPANION_CONSTITUTION.engineering_compression
    assert len(COMPANION_CONSTITUTION.non_negotiables) >= 8

    keys = {item.key for item in COMPANION_CONSTITUTION.non_negotiables}
    assert "user_centered_telos" in keys
    assert "truth_discipline" in keys
    assert "non_manipulation" in keys
    assert "freedom_preservation" in keys
    assert "growth_over_comfort" in keys
    assert "anti_goal_hijacking" in keys
    assert "anti_self_negation" in keys
    assert "no_silent_constitutional_drift" in keys


def test_identity_kernel_artifact_schema_is_complete() -> None:
    assert SPARKLE_IDENTITY_KERNEL.version == IDENTITY_KERNEL_VERSION
    assert SPARKLE_IDENTITY_KERNEL.essence
    assert SPARKLE_IDENTITY_KERNEL.not_this
    assert len(SPARKLE_IDENTITY_KERNEL.core_facets) >= 5

    keys = {item.key for item in SPARKLE_IDENTITY_KERNEL.core_facets}
    assert "growth_companion" in keys
    assert "warmth_honesty_structure" in keys
    assert "emotion_as_value_signal" in keys
    assert "relationship_continuity" in keys
    assert "constitutional_subordination" in keys


def test_artifact_required_fields_are_not_empty() -> None:
    for item in COMPANION_CONSTITUTION.non_negotiables:
        assert item.title.strip()
        assert item.summary.strip()

    for item in SPARKLE_IDENTITY_KERNEL.core_facets:
        assert item.title.strip()
        assert item.summary.strip()

    assert all(flag.strip() for flag in COMPANION_CONSTITUTION.no_drift_commitments)
    assert all(flag.strip() for flag in SPARKLE_IDENTITY_KERNEL.relationship_guardrails)
