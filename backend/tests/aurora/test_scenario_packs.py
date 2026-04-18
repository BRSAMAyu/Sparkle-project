from __future__ import annotations

from app.scenario_packs import (
    EXAM_PREP_14D_PACK_ID,
    assemble_pack_context,
    evaluate_readiness,
    load_default_registry,
    load_exam_prep_14d_manifest,
)


def test_exam_prep_pack_loads_and_registers() -> None:
    manifest = load_exam_prep_14d_manifest()

    assert manifest.id == EXAM_PREP_14D_PACK_ID
    assert manifest.version == "v1.0"
    assert len(manifest.backbone_nodes) == 14
    assert manifest.backbone_nodes[0].node_id == "day1_orientation"
    assert "考试预言家" in manifest.backbone_nodes[0].prompt_template
    assert manifest.backbone_nodes[1].node_id == "day2_prerequisite_map"
    assert "星图向导" in manifest.backbone_nodes[1].prompt_template

    registry = load_default_registry()
    loaded = registry.get_by_id(EXAM_PREP_14D_PACK_ID)
    assert loaded is not None
    assert loaded.name == manifest.name
    assert len(registry.list()) >= 1


def test_exam_prep_terminal_node_has_no_empty_transition_target() -> None:
    manifest = load_exam_prep_14d_manifest()

    terminal_node = manifest.backbone_nodes[-1]
    assert terminal_node.node_id == "day14_final_reset"
    assert terminal_node.transition_triggers
    assert all(target != "" for target in terminal_node.transition_triggers.values())


def test_readiness_evaluator_reports_missing_signals_and_context_overlay() -> None:
    manifest = load_exam_prep_14d_manifest()
    user_signals = {
        "exam_goal_defined": {"confidence": 0.93},
        "prerequisite_mastery": 0.8,
        "study_schedule_reserved": True,
        "extra_signal": "keep me around",
    }

    evaluation = evaluate_readiness(user_signals, manifest)
    assert not evaluation.ready
    assert evaluation.total_required == 5
    assert evaluation.total_satisfied == 3
    assert evaluation.missing_signals == ("practice_loop_active", "exam_date_confirmed")

    assembly = assemble_pack_context(user_signals, manifest)
    assert not assembly.ready
    assert "exam_goal_defined" in assembly.core_signals
    assert "prerequisite_mastery" in assembly.core_signals
    assert "study_schedule_reserved" in assembly.core_signals
    assert "practice_loop_active" not in assembly.core_signals
    assert "extra_signal" in assembly.optional_signals
