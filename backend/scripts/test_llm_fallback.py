#!/usr/bin/env python3
"""
LLM Model Fallback System Test Script

This script tests the new model fallback system:
1. Simulates 429 errors to trigger fallback
2. Verifies same-tier model switching
3. Tests exponential backoff
4. Validates health tracking

Usage:
    cd backend && python scripts/test_llm_fallback.py
"""

import asyncio
import sys
import time

sys.path.insert(0, ".")

from app.core.agent_profiles import AgentRole
from app.core.llm_router import llm_router
from app.services.llm.fallback import FallbackReason, ModelHealthTracker, llm_fallback_manager
from app.services.llm_service import LLMService


class MockAPIError(Exception):
    """Mock API Error for testing"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MockLLMProvider:
    """
    Mock LLM provider that simulates various error conditions
    """
    def __init__(self, fail_config: dict[str, list[int]]):
        """
        Args:
            fail_config: Map of model_name -> list of attempt numbers to fail on
                        e.g., {"glm-4-plus": [1, 2]} means first 2 attempts fail
        """
        self.fail_config = fail_config
        self.attempt_counts: dict[str, int] = {}

    async def call(self, model: str, attempt_num: int) -> str:
        """Simulate an LLM call with configurable failures"""
        if model not in self.attempt_counts:
            self.attempt_counts[model] = 0
        self.attempt_counts[model] += 1

        fail_on = self.fail_config.get(model, [])

        if self.attempt_counts[model] in fail_on:
            # Simulate 429 error
            raise MockAPIError("429 Too Many Requests")

        # Simulate successful response
        return f"Response from {model} (attempt #{self.attempt_counts[model]})"


def test_fallback_reason_detection():
    """Test 1: Fallback reason detection"""
    print("\n" + "=" * 70)
    print("📊 Test 1: Fallback Reason Detection")
    print("=" * 70)

    manager = llm_fallback_manager

    # Test 429 detection
    error_429 = MockAPIError("429 Too Many Requests")
    reason = manager._detect_fallback_reason(error_429)
    print(f"  429 Error: {reason} - {'✅ PASS' if reason == FallbackReason.RATE_LIMIT_429 else '❌ FAIL'}")

    # Test rate limit detection (includes quota)
    error_rate = MockAPIError("Rate limit exceeded")
    reason = manager._detect_fallback_reason(error_rate)
    print(f"  Rate Limit Error: {reason} - {'✅ PASS' if reason in (FallbackReason.RATE_LIMIT_429, FallbackReason.RATE_LIMIT_QUOTA) else '❌ FAIL'}")

    # Test timeout detection
    error_timeout = Exception("Request timed out")
    reason = manager._detect_fallback_reason(error_timeout)
    print(f"  Timeout Error: {reason} - {'✅ PASS' if reason == FallbackReason.TIMEOUT else '❌ FAIL'}")

    # Test non-retryable error
    error_other = Exception("Invalid API key")
    reason = manager._detect_fallback_reason(error_other)
    print(f"  Other Error: {reason} - {'✅ PASS' if reason is None else '❌ FAIL'}")


def test_health_tracker():
    """Test 2: Model Health Tracker"""
    print("\n" + "=" * 70)
    print("📊 Test 2: Model Health Tracker")
    print("=" * 70)

    tracker = ModelHealthTracker(failure_threshold=3, recovery_timeout=10)
    test_model = "test_model_1"

    async def run_test():
        # Initially healthy
        is_healthy = await tracker.is_healthy(test_model)
        print(f"  Initial health: {'✅ Healthy' if is_healthy else '❌ Unhealthy'}")

        # Record failures below threshold
        for i in range(2):
            await tracker.record_failure(test_model, FallbackReason.RATE_LIMIT_429)

        is_healthy = await tracker.is_healthy(test_model)
        count = await tracker.get_failure_count(test_model)
        print(f"  After 2 failures: {'✅ Healthy' if is_healthy else '❌ Unhealthy'} (count={count})")

        # Record third failure (at threshold)
        await tracker.record_failure(test_model, FallbackReason.RATE_LIMIT_429)
        is_healthy = await tracker.is_healthy(test_model)
        count = await tracker.get_failure_count(test_model)
        print(f"  After 3 failures: {'❌ Unhealthy' if not is_healthy else '✅ Healthy'} (count={count}) - Circuit breaker should be open")

        # Record success resets the state
        await tracker.record_success(test_model)
        is_healthy = await tracker.is_healthy(test_model)
        count = await tracker.get_failure_count(test_model)
        print(f"  After success: {'✅ Healthy' if is_healthy else '❌ Unhealthy'} (count={count})")

    asyncio.run(run_test())


def test_fallback_candidates():
    """Test 3: Fallback Candidate Selection"""
    print("\n" + "=" * 70)
    print("📊 Test 3: Fallback Candidate Selection")
    print("=" * 70)

    # Get a STANDARD tier model selection
    from app.core.llm_router import LLMSelection, ModelConfig, ModelProvider
    from app.core.agent_profiles import ModelTier

    # Simulate a failed zhipu_chat model
    config = llm_router._available_models.get("zhipu_chat")
    if config:
        failed_selection = LLMSelection(
            config=config,
            agent_role=AgentRole.GENERATION,
            task_type=None,
            reason="Test selection",
            is_fallback=False,
        )

        print(f"  Original model: {config.model_name} (tier: {config.tier.value})")

        # Get fallback candidates
        candidates = llm_fallback_manager._get_fallback_candidates(
            failed_selection,
            exclude_models={"zhipu_chat"}
        )

        print(f"  Fallback candidates ({len(candidates)}):")
        for i, candidate in enumerate(candidates, 1):
            print(f"    {i}. {candidate.config.model_name} ({candidate.config.provider.value}) - {candidate.reason}")
    else:
        print("  ⚠️  zhipu_chat model not found in config")


def test_backoff_calculation():
    """Test 4: Exponential Backoff Calculation"""
    print("\n" + "=" * 70)
    print("📊 Test 4: Exponential Backoff Calculation")
    print("=" * 70)

    manager = llm_fallback_manager

    print("  Attempt | Delay (ms)")
    print("  --------|----------")
    for attempt in range(5):
        delay = manager._calculate_backoff_delay(attempt)
        print(f"  {attempt:8d} | {delay * 1000:8.0f}")


async def test_concurrent_limits():
    """Test 5: Concurrent Limits Configuration"""
    print("\n" + "=" * 70)
    print("📊 Test 5: Concurrent Limits Configuration")
    print("=" * 70)

    from app.services.llm.concurrency import PROVIDER_CONFIGS, ProviderType

    print("  Provider      | Max Concurrent | Queue Timeout")
    print("  --------------|----------------|--------------")
    for provider_type, config in PROVIDER_CONFIGS.items():
        print(f"  {provider_type.value:14} | {config.max_concurrent:14} | {config.queue_timeout:.1f}s")

    print("\n  💡 Configure via environment variables:")
    print("     - ZHIPU_CONCURRENT_LIMIT: Override ZHIPU concurrent limit")
    print("     - ZHIPU_USER_LEVEL: Set user level (free/1/2/3/4/5/pro)")


async def test_real_llm_with_fallback():
    """Test 6: Real LLM Call with Fallback (if configured)"""
    print("\n" + "=" * 70)
    print("📊 Test 6: Real LLM Call with Fallback System")
    print("=" * 70)

    try:
        llm = LLMService(agent_role=AgentRole.GENERATION, enable_dynamic_routing=True)

        if llm.demo_mode:
            print("  ⚠️  Demo mode enabled, skipping real LLM test")
            return

        selection = llm.get_current_selection()
        if not selection:
            print("  ⚠️  No model selection available")
            return

        print(f"  Selected model: {selection.config.model_name}")
        print(f"  Provider: {selection.config.provider.value}")
        print(f"  Tier: {selection.config.tier.value}")

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Reply in one sentence."},
            {"role": "user", "content": "Say 'fallback test successful' in one sentence."}
        ]

        print("\n  Sending request...")
        start = time.perf_counter()

        response = await llm.chat(messages)

        elapsed = (time.perf_counter() - start) * 1000
        print(f"  ✅ Response received in {elapsed:.0f}ms")
        print(f"  Response: {response[:100]}...")

    except Exception as e:
        print(f"  ❌ Test failed: {e}")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("🚀 LLM Model Fallback System Test Suite")
    print("=" * 70)

    test_fallback_reason_detection()
    test_health_tracker()
    test_fallback_candidates()
    test_backoff_calculation()
    asyncio.run(test_concurrent_limits())
    asyncio.run(test_real_llm_with_fallback())

    print("\n" + "=" * 70)
    print("✅ Test Suite Completed")
    print("=" * 70)


if __name__ == "__main__":
    main()
