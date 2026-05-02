import json
from types import SimpleNamespace

import pytest

from app.aurora.correction_types import AuroraCorrectionPayload
from app.aurora.runtime_v1.correction_feedback import CorrectionFeedbackProcessor


def test_dashboard_payload_normalizes_legacy_freeform_shape():
    payload = AuroraCorrectionPayload.normalize(
        {
            "type": "freeform",
            "semantic_value": "freeform_correction",
            "band_status": "needs_confirm",
            "freeform_text": "I am tired, not avoiding the work.",
            "context_source": "dashboard_status_band",
            "telemetry_id": "tel-dashboard",
            "group_id": "group-dashboard",
            "session_id": "conversation-dashboard",
        }
    )

    assert payload.surface == "dashboard"
    assert payload.source == "freeform_input"
    assert payload.is_freeform is True
    assert payload.is_disconfirming is True
    assert payload.conversation_id == "conversation-dashboard"
    assert payload.telemetry_id == "tel-dashboard"


def test_chat_payload_preserves_canonical_correlation_fields():
    payload = AuroraCorrectionPayload.normalize(
        {
            "surface": "chat",
            "source": "predicted_chip",
            "semantic_value": "risk_false_positive",
            "label": "That risk judgment is off",
            "is_freeform": False,
            "is_disconfirming": True,
            "telemetry_id": "tel-chat",
            "group_id": "group-chat",
            "conversation_id": "conversation-chat",
            "message_id": "message-chat",
        }
    )

    assert payload.to_dict() == {
        "surface": "chat",
        "source": "predicted_chip",
        "semantic_value": "risk_false_positive",
        "label": "That risk judgment is off",
        "freeform_text": "",
        "is_freeform": False,
        "is_disconfirming": True,
        "band_status": "",
        "telemetry_id": "tel-chat",
        "group_id": "group-chat",
        "conversation_id": "conversation-chat",
        "message_id": "message-chat",
    }


def test_chip_vs_freeform_source_classification():
    chip_payload = AuroraCorrectionPayload.normalize(
        {"type": "chip", "semantic_value": "strategy_too_aggressive", "chip_id": "chip-1"}
    )
    freeform_payload = AuroraCorrectionPayload.normalize(
        {"type": "freeform", "semantic_value": "freeform_correction", "freeform_text": "Not quite."}
    )

    assert chip_payload.source == "predicted_chip"
    assert chip_payload.is_freeform is False
    assert freeform_payload.source == "freeform_input"
    assert freeform_payload.is_freeform is True


@pytest.mark.asyncio
async def test_processor_records_surface_source_and_conversation(monkeypatch):
    captured: dict[str, object] = {}

    class FakeSelfModel:
        def __init__(self, redis):
            captured["self_model_redis"] = redis

        async def record_user_correction(self, **kwargs):
            captured["self_model_kwargs"] = kwargs

    class FakeCorrector:
        def __init__(self, redis):
            captured["corrector_redis"] = redis

        async def apply_correction(self, **kwargs):
            captured["corrector_kwargs"] = kwargs
            return SimpleNamespace(correction_id="corr-recorded")

    monkeypatch.setattr(
        "app.aurora.runtime_v1.self_model.SparkleSelfModelService",
        FakeSelfModel,
    )
    monkeypatch.setattr(
        "app.aurora.runtime_v1.aurora_spine_confluence.AuroraSelfCorrector",
        FakeCorrector,
    )

    payload = AuroraCorrectionPayload.normalize(
        {
            "surface": "status_band",
            "source": "freeform_input",
            "semantic_value": "freeform_correction",
            "freeform_text": "The blocker was illness, not avoidance.",
            "is_freeform": True,
            "is_disconfirming": True,
            "telemetry_id": "tel-status",
            "group_id": "group-status",
            "conversation_id": "conversation-status",
            "message_id": "message-status",
        }
    )

    result = await CorrectionFeedbackProcessor(redis_client=None).process(
        user_id="user-1",
        correction_payload=payload,
    )

    correction_text = json.loads(captured["self_model_kwargs"]["correction_text"])
    user_context_payload = captured["self_model_kwargs"]["user_context_payload"]
    assert correction_text["surface"] == "status_band"
    assert correction_text["source"] == "freeform_input"
    assert correction_text["conversation_id"] == "conversation-status"
    assert correction_text["message_id"] == "message-status"
    assert user_context_payload["surface"] == "status_band"
    assert user_context_payload["source"] == "freeform_input"
    assert result.user_visible_effect["surface"] == "status_band"
    assert result.user_visible_effect["conversation_id"] == "conversation-status"
