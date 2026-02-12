from __future__ import annotations

from app.services.meta_cold_start_service import MetaColdStartService


def test_meta_cold_start_detects_new_user_context():
    user_context = {
        "analytics_summary": {"flame_level": 0},
        "preferences": {},
        "inferred": {},
    }
    conversation_context = {"messages": []}
    assert MetaColdStartService.is_cold_start(
        user_context=user_context,
        conversation_context=conversation_context,
    )


def test_meta_cold_start_rejects_established_session():
    user_context = {
        "analytics_summary": {"flame_level": 4},
        "preferences": {"depth_preference": "deep"},
        "inferred": {"expert_affinity": {"deep_analyst": 0.8}},
    }
    conversation_context = {"messages": [{"role": "user", "content": "x"}] * 4, "summary": "history"}
    assert not MetaColdStartService.is_cold_start(
        user_context=user_context,
        conversation_context=conversation_context,
    )
