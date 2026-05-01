import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app" / "gen" / "agent" / "v1"))

from app.aurora.runtime_v1.correction_feedback import (
    CorrectionFeedbackProcessor,
    CorrectionResult,
    generate_calibration_receipt,
)
from app.gen.agent.v1 import agent_service_pb2
from app.orchestration.prompts import get_system_prompt
from app.services.agent_grpc_service import AgentServiceImpl


def test_generate_calibration_receipt_describes_confidence_drop() -> None:
    result = CorrectionResult(
        correction_id="corr_strategy",
        action="disconfirmed",
        affected_state_keys=["strategy_confidence"],
        new_confidence={"strategy_confidence": 0.6},
    )

    receipt = generate_calibration_receipt(
        result,
        chip_label="这个建议太激进了",
        surface="chat",
        timestamp=datetime(2026, 5, 1, 12, 0, 0),
    )

    assert receipt["correction_id"] == "corr_strategy"
    assert receipt["confidence_delta"] == -0.15
    assert "0.75" in receipt["what_changed"]
    assert "0.60" in receipt["what_changed"]
    assert "这个建议太激进了" in receipt["why_changed"]
    assert receipt["next_time"]
    assert receipt["i18n"]["en"]["what_changed"]


def test_generate_calibration_receipt_freeform_uses_user_words() -> None:
    result = CorrectionResult(
        correction_id="corr_freeform",
        action="freeform_correction",
        affected_state_keys=[],
        new_confidence={},
    )

    receipt = generate_calibration_receipt(
        result,
        freeform_text="其实我不是焦虑，是今天生病了。",
        surface="status_band",
    )

    assert receipt["affected_states"] == []
    assert receipt["confidence_delta"] == 0.0
    assert "新的校准" in receipt["what_changed"]
    assert "其实我不是焦虑" in receipt["why_changed"]
    assert "similar situation" in receipt["i18n"]["en"]["next_time"]


@pytest.mark.asyncio
async def test_processor_returns_and_persists_calibration_receipt(monkeypatch) -> None:
    class Redis:
        def __init__(self):
            self.calls = []

        async def lpush(self, key, value):
            self.calls.append(("lpush", key, json.loads(value)))

        async def ltrim(self, key, start, stop):
            self.calls.append(("ltrim", key, start, stop))

        async def expire(self, key, ttl):
            self.calls.append(("expire", key, ttl))

        async def setex(self, key, ttl, value):
            self.calls.append(("setex", key, ttl, json.loads(value)))

        async def get(self, key):
            return None

    redis = Redis()
    processor = CorrectionFeedbackProcessor(redis)

    result = await processor.process(
        user_id="user_1",
        semantic_value="freeform_correction",
        is_freeform=True,
        freeform_text="上次那不是拖延，是我在等材料。",
        telemetry_id="telemetry_1",
        correction_payload={
            "surface": "chat",
            "source": "freeform_input",
            "semantic_value": "freeform_correction",
            "freeform_text": "上次那不是拖延，是我在等材料。",
            "is_freeform": True,
            "telemetry_id": "telemetry_1",
            "conversation_id": "session_1",
        },
    )

    assert result.calibration_receipt["what_changed"]
    assert "上次那不是拖延" in result.calibration_receipt["why_changed"]
    assert any(call[0] == "lpush" and call[1] == "aurora:recent_corrections:user_1" for call in redis.calls)


def test_prompt_includes_recent_correction_without_semantic_token() -> None:
    prompt = get_system_prompt(
        {
            "recent_corrections": [
                {
                    "what_changed": "我把「你当前压力或焦虑程度」的判断置信度从 0.80 下调到 0.65。",
                    "why_changed": "因为你纠正了我：「其实不焦虑」。",
                    "next_time": "下次出现类似信号时，我会先确认再提醒。",
                    "affected_states": ["affective_pressure"],
                }
            ],
            "current_query": "继续刚才的计划",
        }
    )

    assert "近期 Aurora 校准回执" in prompt
    assert "其实不焦虑" in prompt
    assert "affective_pressure" not in prompt


def test_grpc_metadata_carries_calibration_receipt_as_json() -> None:
    response = agent_service_pb2.ChatResponse(response_id="resp_1")
    receipt = {
        "correction_id": "corr_1",
        "what_changed": "我下调了判断",
        "why_changed": "因为你纠正了我",
        "next_time": "下次先确认",
        "affected_states": ["strategy_confidence"],
        "confidence_delta": -0.15,
    }

    AgentServiceImpl._attach_calibration_receipt_metadata(response, receipt)

    decoded = json.loads(response.metadata["calibration_receipt"])
    unified = json.loads(response.metadata["aurora_receipts"])
    assert decoded["correction_id"] == "corr_1"
    assert unified[0]["receipt_type"] == "calibration_receipt"
