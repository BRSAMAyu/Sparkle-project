from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest

from app.core.cache import cache_service
from app.services.chat_signal_collector import ChatSignalCollector
from app.services.evidence.conversational_extractor import ConversationalEvidenceExtractor
from app.services.evidence.fusion_engine import FusionEngine

pytestmark = pytest.mark.asyncio


async def test_chat_signal_collector_writes_trace_to_real_redis() -> None:
    if os.getenv("SPARKLE_RUN_REAL_REDIS_TESTS") != "1":
        pytest.skip("Set SPARKLE_RUN_REAL_REDIS_TESTS=1 to run against docker Redis.")
    if cache_service.redis is None:
        await cache_service.init_redis()
    if cache_service.redis is None:
        pytest.skip("Redis is not configured")

    user_id = uuid4()
    conversation_id = f"real-redis-smoke-{uuid4()}"
    collector = ChatSignalCollector(
        redis=cache_service.redis,
        evidence_extractor=ConversationalEvidenceExtractor(llm_enabled=False),
    )

    await collector.collect_signals(
        user_id=user_id,
        user_message="我现在真的好累，今天感觉什么都不想做，不知道从哪里开始。",
        ai_response="我先帮你把第一步压到最小。",
        conversation_id=conversation_id,
        turn_index=1,
        actual_router_mode="execution_first",
        routing_trace_id=f"rt-{conversation_id}",
        route_history_decision_id=f"rh-{conversation_id}",
        routing_outcome_signal_id=f"sig-{conversation_id}",
    )

    key = FusionEngine.BELIEF_TRACE_KEY.format(user_id=str(user_id))
    raw = await cache_service.redis.lrange(key, 0, 0)
    assert raw
    payload = raw[0].decode("utf-8") if isinstance(raw[0], bytes) else raw[0]
    trace = json.loads(payload)

    assert trace["actual_router_mode"] == "execution_first"
    assert trace["router_shadow_projection"]["shadow_mode"] in {"execution_first", "balanced", "cognitive_first"}
    assert trace["belief_variable_evidence_counts"]
    assert trace["belief_source_breakdown"]["total"]
    assert "cognitive_load_type_counts" in trace
    assert "stage_of_change_counts" in trace
    assert trace["router_snapshot"]["routing_trace_id"] == f"rt-{conversation_id}"
