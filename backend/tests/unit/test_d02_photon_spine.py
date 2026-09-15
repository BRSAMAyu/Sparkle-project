"""
Tests for D-02: Photon consumption patterns → Spine signal pipeline.
"""
from unittest.mock import MagicMock

from app.orchestration.dual_core_router import DualCoreRouter, DualCoreRoutingInput
from app.services.spine_event_bridge import SpineEventBridge


def _base_input(**overrides) -> DualCoreRoutingInput:
    defaults = {
        "intent": "chat",
        "intent_confidence": 0.85,
        "information_sufficient": True,
        "primary_challenge_area": None,
        "recent_sentiment_distribution": {"neutral": 5},
        "has_active_plan": True,
        "plan_health_status": "on_track",
        "recent_task_feedback_distribution": {},
    }
    defaults.update(overrides)
    return DualCoreRoutingInput(**defaults)


def test_shop_purchase_signal():
    """shop.purchase_completed event produces reward_engagement signal."""
    bridge = SpineEventBridge(MagicMock())
    signal = bridge.build_signal({
        "event_type": "shop.purchase_completed",
        "user_id": "u1",
        "item_name": "Galaxy Skin",
        "amount": 50,
    })
    assert signal is not None
    assert signal.state_key == "reward_engagement"
    assert signal.claim == "photon_spent"
    assert signal.priority == "low"


def test_achievement_unlocked_signal():
    """achievement.unlocked event produces reward_engagement signal with rarity-based confidence."""
    bridge = SpineEventBridge(MagicMock())
    signal = bridge.build_signal({
        "event_type": "achievement.unlocked",
        "user_id": "u1",
        "achievement_name": "First Step",
        "rarity": "rare",
    })
    assert signal is not None
    assert signal.state_key == "reward_engagement"
    assert signal.claim == "achievement_unlocked"
    assert signal.confidence >= 0.75


def test_achievement_legendary_has_high_confidence():
    """Legendary achievements should have highest confidence."""
    bridge = SpineEventBridge(MagicMock())
    signal = bridge.build_signal({
        "event_type": "achievement.unlocked",
        "user_id": "u1",
        "achievement_name": "Champion",
        "rarity": "legendary",
    })
    assert signal.confidence >= 0.9


def test_reward_engagement_adjusts_router():
    """reward_engagement state in dual_core_router should recommend push_vs_support."""
    router = DualCoreRouter()
    inp = _base_input(
        spine_active_states=[
            {"state_key": "reward_engagement", "value": "achievement_unlocked", "confidence": 0.8, "scope": "session"},
        ],
    )
    decision = router.route(inp)
    fields = [s["field"] for s in decision.strategy_adjustments]
    assert "push_vs_support" in fields
