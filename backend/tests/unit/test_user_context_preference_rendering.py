"""V3-FIX-36 regression: the render layer must serialize memory-chain
preference VALUES into the prompt face.

M-09 real-model probing showed the production ``format_user_context`` never
rendered preference values — 【学习偏好】 carried only the two numeric scalars
(深度/好奇心), so every preference M-01..M-07 kept correct was INVISIBLE to
the model answering the user. The user's correction reached the pack but
never the answer (记忆流「用户可感知闭环」阻断).

Privacy contract under test (same external stance as M-08 provenance):
- the rendered face carries user-readable value text ONLY (the ``{"value": X}``
  writer contract, scalar fields, or str/int/float/bool dict fields);
- internal parameters (scores / confidence / version / ids / epoch) and the
  raw serialized dict structure never appear;
- numeric depth/curiosity keep their dedicated scalar lines (no duplicate);
- emotional-focus mode still renders the values (a correction must stay
  visible when the turn is emotionally led);
- unknown keys fall back to the raw key (honest, no guessing);
- line count and per-line length are bounded.
"""

from __future__ import annotations

from app.orchestration.prompts import format_user_context


def _ctx(preferences: dict) -> dict:
    """Pack-shaped prompt context (same boundary as ContextPack.to_prompt_context)."""
    return {"preferences": preferences}


def test_render_contains_memory_preference_values():
    rendered = format_user_context(
        _ctx({"preferred_expansion_depth": {"value": "现在要竞赛难度的题，基础的没挑战"}})
    )
    assert "现在要竞赛难度的题，基础的没挑战" in rendered
    assert "- 拓展难度: 现在要竞赛难度的题，基础的没挑战" in rendered
    # the two scalar lines remain
    assert "深度:" in rendered and "好奇心:" in rendered


def test_render_superseded_chain_head_is_the_rendered_value():
    """End-state of FIX-35+FIX-36 composed: only the chain head value renders."""
    rendered = format_user_context(
        _ctx({"vocabulary_retention_style": {"value": "改用思维导图串联记，卡片太碎了"}})
    )
    assert "思维导图" in rendered
    assert "记忆卡片" not in rendered


def test_render_excludes_internal_parameters_and_raw_structure():
    rendered = format_user_context(
        _ctx(
            {
                "feedback_tone": {"value": "直接指出问题"},
                "unknown_open_key": {"value": "自定义偏好内容"},
            }
        )
    )
    # user-readable values DO render
    assert "直接指出问题" in rendered
    assert "自定义偏好内容" in rendered
    # unknown keys fall back to the raw key, honestly
    assert "unknown_open_key" in rendered
    # internal parameters / raw dict serialization DO NOT
    assert "'value'" not in rendered
    assert '"value"' not in rendered
    for internal in ("evidence", "confidence", "version", "epoch", "pref_value", "replaced_by"):
        assert internal not in rendered


def test_render_preference_value_shapes():
    rendered = format_user_context(
        _ctx(
            {
                "study_time_preference": {"minutes": 30},
                "enable_push": {"value": True},
                "ai_verbosity": "尽量简短",
                "motivation_type": None,
                "task_priority_bias": {"nested": {"deep": "no"}},
                "sprint_mode": {"value": "  "},
            }
        )
    )
    assert "minutes=30" in rendered
    assert "- 推送开关: True" in rendered
    assert "- 回答长度: 尽量简短" in rendered
    # unreadable / empty shapes render nothing (no crash, no noise)
    assert "nested" not in rendered
    assert "None" not in rendered


def test_numeric_depth_curiosity_not_duplicated():
    rendered = format_user_context(
        _ctx(
            {
                "depth_preference": {"value": 0.7},
                "curiosity_preference": {"value": 0.3},
            }
        )
    )
    assert "深度: 0.7" in rendered
    assert "好奇心: 0.3" in rendered
    assert "内容深度: 0.7" not in rendered
    assert "好奇心拓展: 0.3" not in rendered


def test_emotional_focus_mode_still_renders_preference_values():
    focus = {
        "focus_mode": "emotional_focus",
        "focus_reason": "probe",
        "section_weights": {"preferences": "high"},
        "section_caps": {},
        "briefing_candidates": [],
        "semantic_gating_enabled": False,
    }
    rendered = format_user_context(
        _ctx({"feedback_tone": {"value": "直接一点，不用绕弯子"}}),
        context_focus=focus,
    )
    assert "直接一点，不用绕弯子" in rendered


def test_render_bounds_line_count_and_length():
    prefs = {"long_key": {"value": "长" * 300}}
    prefs.update({f"key_{i}": {"value": f"值{i}"} for i in range(12)})
    rendered = format_user_context(_ctx(prefs))
    pref_lines = [line for line in rendered.splitlines() if line.startswith("- key_")]
    assert len(pref_lines) == 7  # long_key consumed one of the 8 slots
    long_line = next(line for line in rendered.splitlines() if line.startswith("- long_key"))
    assert len(long_line) < 140
    assert long_line.endswith("…")


def test_preferences_section_off_respects_focus_weighting():
    focus = {
        "focus_mode": "general_focus",
        "focus_reason": "probe",
        "section_weights": {"preferences": "off"},
        "section_caps": {},
        "briefing_candidates": [],
        "semantic_gating_enabled": False,
    }
    rendered = format_user_context(
        _ctx({"feedback_tone": {"value": "直接指出问题"}}),
        context_focus=focus,
    )
    assert "直接指出问题" not in rendered
    assert "【学习偏好】" not in rendered
