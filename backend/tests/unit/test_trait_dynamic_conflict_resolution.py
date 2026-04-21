from __future__ import annotations

from app.services.traits_guardrails import resolve_trait_vs_dynamic


def test_dynamic_state_wins_for_focus_mode() -> None:
    assert resolve_trait_vs_dynamic({"focus": "slow"}, {"focus": "sprint"}) == {"focus": "sprint"}


def test_dynamic_state_wins_for_tone_selection() -> None:
    dynamic = {"response_style": "concise"}
    assert resolve_trait_vs_dynamic({"response_style": "reflective"}, dynamic) is dynamic


def test_dynamic_state_wins_even_when_trait_is_none() -> None:
    assert resolve_trait_vs_dynamic(None, {"push_vs_support": 0.2}) == {"push_vs_support": 0.2}


def test_dynamic_state_wins_even_when_empty() -> None:
    assert resolve_trait_vs_dynamic({"extraversion": 0.3}, {}) == {}
