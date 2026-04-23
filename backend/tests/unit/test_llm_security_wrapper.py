from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.llm_security_wrapper import LLMSecurityWrapper, SecurityConfig
from app.core.llm_quota import QuotaCheckResult


class _FakeLLMService:
    async def chat(self, *args, **kwargs):
        return "安全回复"

    async def chat_with_tools(self, *args, **kwargs):
        return SimpleNamespace(content="工具回复")

    async def generate_embeddings(self, texts, model=None):
        return [[0.1] * 3 for _ in texts]


@pytest.mark.asyncio
async def test_wrapper_chat_uses_quota_check_only_and_records_actual_usage():
    wrapper = LLMSecurityWrapper(
        llm_service=_FakeLLMService(),
        redis_client=object(),
        config=SecurityConfig(enable_input_filter=False, enable_output_validation=False, enable_monitoring=False),
    )
    wrapper.cost_guard = SimpleNamespace(
        estimate_tokens=lambda text: 10 if "安全回复" not in text else 4,
        check_quota=AsyncMock(
            return_value=QuotaCheckResult(
                allowed=True,
                current_usage=0,
                limit=100_000,
                remaining=99_990,
                percentage=0.0,
            )
        ),
        record_usage=AsyncMock(return_value=None),
    )

    result = await wrapper.chat(
        user_id="user-1",
        messages=[{"role": "user", "content": "你好"}],
    )

    assert result == "安全回复"
    wrapper.cost_guard.check_quota.assert_awaited_once_with("user-1", 10, check_only=True)
    wrapper.cost_guard.record_usage.assert_awaited_once_with("user-1", 4, "unknown")


@pytest.mark.asyncio
async def test_wrapper_chat_with_tools_uses_quota_check_only():
    wrapper = LLMSecurityWrapper(
        llm_service=_FakeLLMService(),
        redis_client=object(),
        config=SecurityConfig(enable_input_filter=False, enable_output_validation=False, enable_monitoring=False),
    )
    wrapper.cost_guard = SimpleNamespace(
        estimate_tokens=lambda text: 12 if "工具回复" not in text else 5,
        check_quota=AsyncMock(
            return_value=QuotaCheckResult(
                allowed=True,
                current_usage=0,
                limit=100_000,
                remaining=99_988,
                percentage=0.0,
            )
        ),
        record_usage=AsyncMock(return_value=None),
    )

    response = await wrapper.chat_with_tools(
        user_id="user-2",
        system_prompt="sys",
        user_message="msg",
        tools=[],
    )

    assert response.content == "工具回复"
    wrapper.cost_guard.check_quota.assert_awaited_once_with("user-2", 12, check_only=True)
    wrapper.cost_guard.record_usage.assert_awaited_once_with("user-2", 5, "unknown")
