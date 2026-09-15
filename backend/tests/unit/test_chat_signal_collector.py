from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

import app.services.evidence.conversational_extractor as conversational_extractor_module
from app.api.v1.cognitive import BeliefCorrectionRequest, _belief_correction_evidence
from app.services.chat_signal_collector import ChatSignalCollector
from app.services.evidence import ConversationalEvidenceExtractor, EvidenceDirection, EvidenceSourceType, EvidenceTarget
from app.services.evidence.unified_evidence import UnifiedEvidence


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.expirations: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.expirations[key] = ttl

    async def lpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).insert(0, value)

    async def ltrim(self, key: str, start: int, end: int) -> None:
        self.lists[key] = self.lists.get(key, [])[start : end + 1]

    async def lset(self, key: str, index: int, value: str) -> None:
        self.lists[key][index] = value

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl


def test_chat_signal_collector_satisfaction_defaults_to_neutral_not_positive() -> None:
    collector = ChatSignalCollector(redis=None)
    entries = [
        {"gratitude": False, "dissatisfaction": False, "follow_up": False},
        {"gratitude": False, "dissatisfaction": False, "follow_up": False},
        {"gratitude": True, "dissatisfaction": False, "follow_up": False},
        {"gratitude": False, "dissatisfaction": True, "follow_up": False},
    ]

    rate = collector._satisfaction_rate(entries)

    assert rate == 0.5


def test_chat_signal_collector_detects_explicit_dissatisfaction() -> None:
    assert ChatSignalCollector._detect_dissatisfaction("这个答案不太对，我还是不懂")
    assert ChatSignalCollector._detect_dissatisfaction("This is wrong and still confused")
    assert not ChatSignalCollector._detect_dissatisfaction("谢谢，我明白了")


def test_belief_correction_generates_high_confidence_evidence() -> None:
    evidence = _belief_correction_evidence(
        user_id=uuid4(),
        payload=BeliefCorrectionRequest(correction_key="not_tired_stuck"),
    )

    assert evidence.source_type == EvidenceSourceType.PROBE_EXPLICIT
    assert evidence.confidence == 0.95
    assert evidence.target_latent_variable == EvidenceTarget.COGNITIVE_LOAD
    assert evidence.metadata["correction_source"] == "belief_summary_mvp"
    assert evidence.metadata["cognitive_load_type"] == "intrinsic"


def test_chat_signal_collector_weights_recent_sentiment_more_heavily() -> None:
    collector = ChatSignalCollector(redis=None)
    now = datetime.now(UTC).replace(tzinfo=None)
    entries = [
        {
            "ts": (now - timedelta(days=6)).isoformat(),
            "gratitude": True,
            "dissatisfaction": False,
            "follow_up": False,
        },
        {
            "ts": now.isoformat(),
            "gratitude": False,
            "dissatisfaction": True,
            "follow_up": False,
        },
    ]

    rate = collector._satisfaction_rate(entries)

    assert rate < 0.35


def test_chat_signal_collector_prefers_recent_active_hours() -> None:
    collector = ChatSignalCollector(redis=None)
    now = datetime.now(UTC).replace(tzinfo=None)
    entries = [
        {"ts": (now - timedelta(days=6)).isoformat(), "hour": 3},
        {"ts": now.isoformat(), "hour": 14},
        {"ts": now.isoformat(), "hour": 14},
    ]

    active_hours = collector._active_hours(entries)

    assert active_hours[0] == 14


def test_conversational_evidence_rule_fallback_extracts_task_aversion() -> None:
    extractor = ConversationalEvidenceExtractor(llm_enabled=False)

    evidence = extractor.extract_rule_based(
        user_message="这个任务看着就烦，不是不懂，就是不想开始。",
        scope={"conversation_id": "c1", "turn_index": 1},
    )

    targets = {item.target_latent_variable for item in evidence}
    assert EvidenceTarget.TASK_AVERSION in targets
    assert all(item.confidence < 0.8 for item in evidence)
    assert all(item.metadata["extractor"] == "rule_fallback" for item in evidence)


def test_conversational_evidence_rule_fallback_classifies_cognitive_load_type() -> None:
    extractor = ConversationalEvidenceExtractor(llm_enabled=False)

    evidence = extractor.extract_rule_based(
        user_message="这个解释太乱了，步骤太多，信息太多。",
        scope={"conversation_id": "c1", "turn_index": 1},
    )

    load = next(item for item in evidence if item.target_latent_variable == EvidenceTarget.COGNITIVE_LOAD)
    assert load.metadata["cognitive_load_type"] == "extraneous"
    assert load.metadata["academic_prior"] == "cognitive_load_theory.v1"
    assert load.metadata["stage_of_change"] == "unknown"


def test_conversational_evidence_rule_fallback_classifies_stage_of_change() -> None:
    extractor = ConversationalEvidenceExtractor(llm_enabled=False)

    evidence = extractor.extract_rule_based(
        user_message="我准备先试试，但信息太多了，从哪里开始比较好？",
        scope={"conversation_id": "c1", "turn_index": 1},
    )

    assert evidence
    assert {item.metadata["stage_of_change"] for item in evidence} == {"preparation"}


def test_chat_signal_collector_maps_evidence_severity_conservatively() -> None:
    assert ChatSignalCollector._evidence_severity(0.9, 0.9) == 4
    assert ChatSignalCollector._evidence_severity(0.7, 0.8) == 3
    assert ChatSignalCollector._evidence_severity(0.5, 0.7) == 2
    assert ChatSignalCollector._evidence_severity(0.2, 0.8) == 1


@pytest.mark.asyncio
async def test_chat_signal_collector_belief_shadow_records_actual_router_mode() -> None:
    redis = FakeRedis()
    collector = ChatSignalCollector(redis=redis)
    user_id = uuid4()
    evidence = UnifiedEvidence(
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT,
        target_latent_variable=EvidenceTarget.EMOTIONAL_BLOCK,
        direction=EvidenceDirection.INCREASE,
        strength=0.9,
        confidence=0.9,
        evidence_text="我真的有点崩溃。",
    )

    trace = await collector._persist_belief_shadow(
        user_id=user_id,
        evidence_items=[evidence],
        conversation_id="c1",
        turn_index=3,
        actual_router_mode="execution_first",
    )

    assert trace is not None
    assert trace["actual_router_mode"] == "execution_first"
    assert trace["action_taken"]["mode"] == "execution_first"
    assert trace["router_shadow_projection"]["shadow_mode"] == "cognitive_first"


@pytest.mark.asyncio
async def test_chat_signal_collector_belief_shadow_records_weak_chat_reward_and_route_ids() -> None:
    redis = FakeRedis()
    collector = ChatSignalCollector(redis=redis)
    user_id = uuid4()
    evidence = UnifiedEvidence(
        source_type=EvidenceSourceType.CONVERSATIONAL_IMPLICIT,
        target_latent_variable=EvidenceTarget.GOAL_CLARITY,
        direction=EvidenceDirection.INCREASE,
        strength=0.8,
        confidence=0.8,
        evidence_text="谢谢，我懂了。",
    )

    trace = await collector._persist_belief_shadow(
        user_id=user_id,
        evidence_items=[evidence],
        conversation_id="c1",
        turn_index=4,
        actual_router_mode="balanced",
        routing_trace_id="rt-1",
        route_history_decision_id="rh-1",
        routing_outcome_signal_id="sig-1",
        gratitude=True,
    )

    assert trace is not None
    assert trace["outcome"] == "explicit_gratitude"
    assert trace["reward"]["signal_type"] == "explicit.gratitude"
    assert trace["reward"]["reward_category"] == "chat_feedback"
    assert trace["router_snapshot"]["routing_trace_id"] == "rt-1"
    assert trace["action_taken"]["route_history_decision_id"] == "rh-1"


@pytest.mark.asyncio
async def test_conversational_extractor_retries_llm_once(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_safe_llm_json_call(*args, **kwargs):
        captured.update(kwargs)
        return [
            {
                "target_latent_variable": "emotional_block",
                "direction": "increase",
                "strength": 0.8,
                "confidence": 0.82,
                "evidence_text": "我真的好累",
                "ttl_seconds": 3600,
            }
        ]

    monkeypatch.setattr(conversational_extractor_module, "safe_llm_json_call", fake_safe_llm_json_call)
    extractor = ConversationalEvidenceExtractor(llm_enabled=True)

    evidence = await extractor.extract(
        user_id=uuid4(),
        user_message="我真的好累",
        ai_response="",
        conversation_id="c-llm",
        turn_index=1,
    )

    assert captured["retry_count"] == 1
    assert captured["timeout"] == 12.0
    assert evidence[0].source_type == EvidenceSourceType.CONVERSATIONAL_IMPLICIT


@pytest.mark.asyncio
async def test_chat_signal_collector_trace_records_evidence_metadata_summary() -> None:
    redis = FakeRedis()
    collector = ChatSignalCollector(redis=redis)
    user_id = uuid4()
    evidence = UnifiedEvidence(
        source_type=EvidenceSourceType.HEURISTIC_FALLBACK,
        target_latent_variable=EvidenceTarget.COGNITIVE_LOAD,
        direction=EvidenceDirection.INCREASE,
        strength=0.72,
        confidence=0.68,
        evidence_text="解释太乱了",
        metadata={
            "cognitive_load_type": "extraneous",
            "academic_prior": "cognitive_load_theory.v1",
            "stage_of_change": "preparation",
        },
    )

    trace = await collector._persist_belief_shadow(
        user_id=user_id,
        evidence_items=[evidence],
        conversation_id="c1",
        turn_index=5,
        actual_router_mode="balanced",
    )

    assert trace is not None
    assert trace["cognitive_load_type_counts"]["extraneous"] == 1
    assert trace["stage_of_change_counts"]["preparation"] == 1
    assert trace["extraneous_load_rate"] == 1.0
