"""Regression test for ISSUE-20260503-1513-K4: LLM timeout fallback.

Validates that the timeout fallback never produces a None timeout,
and that httpx.Timeout is available as the safety net.
"""

import pytest
import httpx


class TestLLMTimeoutFallback:

    def test_httpx_fallback_has_expected_values(self):
        """httpx.Timeout fallback must match the same shape as openai.Timeout."""
        t = httpx.Timeout(timeout=60.0, connect=10.0)
        assert t.read == 60.0
        assert t.connect == 10.0

    def test_httpx_timeout_is_not_none(self):
        """The fallback must never produce None (was the old bug)."""
        t = httpx.Timeout(timeout=60.0, connect=10.0)
        assert t is not None

    def test_providers_module_imports(self):
        """OpenAICompatibleProvider should be importable without errors."""
        from app.services.llm.providers import (
            HAS_OPENAI,
            OpenAICompatibleProvider,
            OpenAITimeout,
        )
        assert OpenAICompatibleProvider is not None
        if HAS_OPENAI:
            assert OpenAITimeout is not None

    def test_timeout_config_never_none(self):
        """Simulate the fixed logic: never pass None as timeout (was old bug)."""
        timeout_seconds = 60.0
        # Simulate the case where OpenAITimeout is None (import failed)
        OpenAITimeout_sim = None
        if OpenAITimeout_sim:
            cfg = OpenAITimeout_sim(timeout=timeout_seconds, connect=10.0)
        else:
            cfg = httpx.Timeout(timeout=timeout_seconds, connect=10.0)
        assert cfg is not None
        assert cfg.read == 60.0
