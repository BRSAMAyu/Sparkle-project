"""
Unit Tests for Candidate Generation Service

Tests coverage:
- Candidate action generation from signals
- Cooldown enforcement (Constraint 1)
- Confidence threshold (Constraint 2)
- Daily budget limit (Constraint 3)
- Diversity control (Constraint 4)
- Action type mapping
- Cache integration for cooldowns and counters
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.candidate_generation_service import (
    candidate_generation_service,
    CandidateGenerationService,
    CandidateAction,
)
from app.services.signal_generation_service import Signal, Signals


@pytest.fixture
def mock_cache_service():
    """Mock cache service for cooldown and counter tracking"""
    mock = MagicMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    return mock


@pytest.mark.asyncio
async def test_generate_candidates_simple(mock_cache_service):
    """Test basic candidate generation from signals"""
    service = CandidateGenerationService()

    # Mock cache: no cooldowns, no daily limit reached
    mock_cache_service.get.return_value = None

    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(
                type="needs_break",
                confidence=0.80,
                reason="深夜学习且频繁中断",
                metadata={"hour": "22+"},
            ),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.action_type == "break"
    assert candidate.title == "休息一下"
    assert "因为" in candidate.reason
    assert candidate.confidence == 0.80
    assert candidate.timing_hint == "now"


@pytest.mark.asyncio
async def test_generate_candidates_cooldown_enforced(mock_cache_service):
    """Test Constraint 1: Cooldown enforcement"""
    service = CandidateGenerationService()

    # Mock cache: break action in cooldown
    async def mock_get(key):
        if "candidate_cooldown:test_user:break" in key:
            return "1"  # In cooldown
        if "daily_interventions" in key:
            return "2"  # Current count
        return None

    mock_cache_service.get.side_effect = mock_get

    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(
                type="needs_break",
                confidence=0.80,
                reason="测试",
                metadata={},
            ),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    # Should be filtered due to cooldown
    assert len(candidates) == 0


@pytest.mark.asyncio
async def test_generate_candidates_daily_budget_exceeded(mock_cache_service):
    """Test Constraint 3: Daily budget limit"""
    service = CandidateGenerationService()

    # Mock cache: daily budget exhausted
    async def mock_get(key):
        if "daily_interventions" in key:
            return "8"  # Max limit reached
        return None

    mock_cache_service.get.side_effect = mock_get

    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(
                type="needs_break",
                confidence=0.80,
                reason="测试",
                metadata={},
            ),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    # Should return empty due to budget
    assert len(candidates) == 0


@pytest.mark.asyncio
async def test_generate_candidates_diversity_control(mock_cache_service):
    """Test Constraint 4: Diversity control (max 3 candidates)"""
    service = CandidateGenerationService()

    # Mock cache: no cooldowns, low daily count
    mock_cache_service.get.return_value = None

    # 5 signals, but should return max 3
    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(type="needs_break", confidence=0.80, reason="测试1", metadata={}),
            Signal(type="topic_stuck", confidence=0.70, reason="测试2", metadata={}),
            Signal(type="risk_dropout_soon", confidence=0.75, reason="测试3", metadata={}),
            Signal(type="best_next_action_window", confidence=0.60, reason="测试4", metadata={}),
            Signal(type="session_too_short", confidence=0.68, reason="测试5", metadata={}),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    # Should limit to 3
    assert len(candidates) <= 3


@pytest.mark.asyncio
async def test_generate_candidates_sets_cooldowns(mock_cache_service):
    """Test that cooldowns are set for generated candidates"""
    service = CandidateGenerationService()

    mock_cache_service.get.return_value = None

    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(type="needs_break", confidence=0.80, reason="测试", metadata={}),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    # Should have called set for cooldown
    set_calls = [call for call in mock_cache_service.set.call_args_list]
    cooldown_calls = [call for call in set_calls if "cooldown" in str(call)]
    assert len(cooldown_calls) > 0

    # Verify cooldown TTL (60 minutes = 3600 seconds for break)
    cooldown_call = cooldown_calls[0]
    assert cooldown_call.kwargs["ttl"] == 3600  # 60 * 60


@pytest.mark.asyncio
async def test_generate_candidates_increments_daily_count(mock_cache_service):
    """Test that daily intervention count is incremented"""
    service = CandidateGenerationService()

    # Mock cache: current count = 5
    async def mock_get(key):
        if "daily_interventions" in key:
            return "5"
        return None

    mock_cache_service.get.side_effect = mock_get

    signals = Signals(
        version="sig_v1",
        signals=[
            Signal(type="needs_break", confidence=0.80, reason="测试", metadata={}),
        ],
    )

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_candidates(
            user_id="test_user",
            signals=signals
        )

    # Should have incremented to 6
    set_calls = [call for call in mock_cache_service.set.call_args_list]
    daily_calls = [call for call in set_calls if "daily_interventions" in str(call)]
    assert len(daily_calls) > 0

    # Verify new count is 6 (5 + 1)
    daily_call = daily_calls[0]
    assert daily_call.args[1] == "6"


def test_signal_to_action_type_mapping():
    """Test signal type to action type mapping"""
    service = CandidateGenerationService()

    assert service._signal_to_action_type("needs_break") == "break"
    assert service._signal_to_action_type("topic_stuck") == "clarify"
    assert service._signal_to_action_type("high_comprehension_friction") == "clarify"
    assert service._signal_to_action_type("risk_dropout_soon") == "plan_split"
    assert service._signal_to_action_type("consecutive_failures") == "plan_split"
    assert service._signal_to_action_type("session_too_short") == "plan_split"
    assert service._signal_to_action_type("best_next_action_window") == "review"
    assert service._signal_to_action_type("unknown_signal") == "review"  # Default


def test_create_candidate_break():
    """Test candidate creation for break action"""
    service = CandidateGenerationService()

    signal = Signal(
        type="needs_break",
        confidence=0.80,
        reason="深夜学习",
        metadata={"hour": "22+"},
    )

    candidate = service._create_candidate(signal, "break")

    assert candidate.action_type == "break"
    assert candidate.title == "休息一下"
    assert candidate.reason == "因为深夜学习"
    assert candidate.confidence == 0.80
    assert candidate.timing_hint == "now"
    assert candidate.payload_seed == "suggest_break_activity"
    assert "hour" in candidate.metadata


def test_create_candidate_clarify():
    """Test candidate creation for clarify action"""
    service = CandidateGenerationService()

    signal = Signal(
        type="topic_stuck",
        confidence=0.70,
        reason="理解遇到阻塞",
        metadata={"density": 5},
    )

    candidate = service._create_candidate(signal, "clarify")

    assert candidate.action_type == "clarify"
    assert candidate.title == "换个角度理解"
    assert candidate.timing_hint == "now"
    assert candidate.payload_seed == "suggest_alternative_explanation"


def test_create_candidate_plan_split():
    """Test candidate creation for plan_split action"""
    service = CandidateGenerationService()

    signal = Signal(
        type="risk_dropout_soon",
        confidence=0.75,
        reason="连续中断",
        metadata={},
    )

    candidate = service._create_candidate(signal, "plan_split")

    assert candidate.action_type == "plan_split"
    assert candidate.title == "拆小任务"
    assert candidate.timing_hint == "after_current_task"
    assert candidate.payload_seed == "breakdown_current_task"


def test_create_candidate_review():
    """Test candidate creation for review action"""
    service = CandidateGenerationService()

    signal = Signal(
        type="best_next_action_window",
        confidence=0.60,
        reason="适合重新规划",
        metadata={},
    )

    candidate = service._create_candidate(signal, "review")

    assert candidate.action_type == "review"
    assert candidate.title == "复习巩固"
    assert candidate.timing_hint == "in_5min"
    assert candidate.payload_seed == "suggest_review_topic"


def test_candidate_to_dict():
    """Test candidate to_dict serialization"""
    candidate = CandidateAction(
        id="ca_123456",
        action_type="break",
        title="休息一下",
        reason="因为深夜学习",
        confidence=0.80,
        timing_hint="now",
        payload_seed="suggest_break_activity",
        metadata={"test": "data"},
    )

    candidate_dict = candidate.to_dict()

    assert candidate_dict["id"] == "ca_123456"
    assert candidate_dict["action_type"] == "break"
    assert candidate_dict["title"] == "休息一下"
    assert candidate_dict["reason"] == "因为深夜学习"
    assert candidate_dict["confidence"] == 0.80
    assert candidate_dict["timing_hint"] == "now"
    assert candidate_dict["payload_seed"] == "suggest_break_activity"
    assert candidate_dict["metadata"]["test"] == "data"


def test_apply_diversity_no_consecutive():
    """Test diversity control prevents 3 consecutive same-type"""
    service = CandidateGenerationService()

    # Create 4 candidates with same type
    candidates = [
        CandidateAction(
            id=f"ca_{i}",
            action_type="break",
            title="休息",
            reason="测试",
            confidence=0.80,
            timing_hint="now",
            payload_seed="test",
            metadata={},
        )
        for i in range(4)
    ]

    result = service._apply_diversity(candidates)

    # Should not have 3 consecutive same-type
    # Check that we don't have 3 in a row
    for i in range(len(result) - 2):
        types = [result[i].action_type, result[i+1].action_type, result[i+2].action_type]
        # Should not all be the same
        assert not (types[0] == types[1] == types[2])


def test_apply_diversity_max_three():
    """Test diversity control limits to 3 candidates"""
    service = CandidateGenerationService()

    # Create 5 diverse candidates
    candidates = [
        CandidateAction(
            id=f"ca_{i}",
            action_type=["break", "clarify", "review", "plan_split", "break"][i],
            title="测试",
            reason="测试",
            confidence=0.70,
            timing_hint="now",
            payload_seed="test",
            metadata={},
        )
        for i in range(5)
    ]

    result = service._apply_diversity(candidates)

    # Should limit to 3
    assert len(result) <= 3


@pytest.mark.asyncio
async def test_generate_from_dict(mock_cache_service):
    """Test generate_from_dict convenience method"""
    service = CandidateGenerationService()

    mock_cache_service.get.return_value = None

    signals_dict = {
        "version": "sig_v1",
        "signals": [
            {
                "type": "needs_break",
                "confidence": 0.80,
                "reason": "测试",
                "metadata": {},
            },
        ],
    }

    with patch("app.services.candidate_generation_service.cache_service", mock_cache_service):
        candidates = await service.generate_from_dict(
            user_id="test_user",
            signals_dict=signals_dict
        )

    assert len(candidates) > 0


def test_cooldown_times_configuration():
    """Test cooldown time configuration"""
    service = CandidateGenerationService()

    assert service.COOLDOWN_TIMES["break"] == 60
    assert service.COOLDOWN_TIMES["review"] == 30
    assert service.COOLDOWN_TIMES["clarify"] == 45
    assert service.COOLDOWN_TIMES["plan_split"] == 60


def test_constraints_configuration():
    """Test constraint configuration values"""
    service = CandidateGenerationService()

    assert service.MIN_CONFIDENCE == 0.65
    assert service.MAX_DAILY_INTERVENTIONS == 8
    assert service.MAX_CANDIDATES_PER_REQUEST == 3


def test_singleton_instance():
    """Test singleton instance is available"""
    from app.services.candidate_generation_service import candidate_generation_service

    assert candidate_generation_service is not None
    assert isinstance(candidate_generation_service, CandidateGenerationService)
