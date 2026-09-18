"""R2-08-02 契约测试：LLMSecurityWrapper fail-closed 转发面。

修复前：`__getattr__` 对除 dunder 外的一切属性无界转发到裸 LLMService，
`chat_stream_with_tools`（REST 流式聊天主路径）等调用经包装器单例直达内层，
跳过配额/监控/记账。

修复后契约：
1. `__getattr__` 仅放行只读路由元属性（chat_model/reason_model/model_key/
   default_model），其余一律 AttributeError（fail-closed）；
2. 六个显式审计旁路方法（reason/reason_json/chat_json/
   continue_with_tool_results/chat_stream_with_tools/generate_push_content）
   为 wrapper 真实方法：身份可识别时强制配额预检（check_only）+ 用量记账；
3. 配额超限在旁路上同样阻断（QuotaExceededError）。
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.core.llm_security_wrapper import LLMSecurityWrapper, QuotaExceededError, SecurityConfig
from app.core.llm_quota import QuotaCheckResult

AUDITED_BYPASSES = (
    "reason",
    "reason_json",
    "chat_json",
    "continue_with_tool_results",
    "chat_stream_with_tools",
    "generate_push_content",
)
META_ATTRS = ("chat_model", "reason_model", "model_key", "default_model")


def _allowed_quota() -> QuotaCheckResult:
    return QuotaCheckResult(allowed=True, current_usage=0, limit=100_000, remaining=100_000, percentage=0.0)


def _denied_quota() -> QuotaCheckResult:
    return QuotaCheckResult(
        allowed=False, current_usage=100_000, limit=100_000, remaining=0, percentage=100.0, message="quota exceeded"
    )


class _FakeInner:
    """覆盖 wrapper 全部调用面的最小内层服务替身。"""

    chat_model = "fake-chat-model"
    reason_model = "fake-reason-model"
    model_key = "fake-key"
    default_model = "fake-chat-model"

    async def reason(self, *args, **kwargs):
        return "reasoned"

    async def reason_json(self, *args, **kwargs):
        return {"ok": True}

    async def chat_json(self, *args, **kwargs):
        return {"ok": True}

    async def continue_with_tool_results(self, *args, **kwargs):
        return SimpleNamespace(content="continued")

    async def generate_push_content(self, *args, **kwargs):
        return {"title": "t", "body": "b"}

    def chat_stream_with_tools(self, *args, **kwargs):
        async def _gen():
            yield SimpleNamespace(type="text", content="你好")
            yield SimpleNamespace(type="tool_call", content=None)

        return _gen()


def _make_wrapper(**config_overrides) -> LLMSecurityWrapper:
    config = SecurityConfig(
        enable_input_filter=False,
        enable_output_validation=False,
        enable_monitoring=False,
        **config_overrides,
    )
    return LLMSecurityWrapper(llm_service=_FakeInner(), redis_client=object(), config=config)


def _attach_quota_guard(wrapper: LLMSecurityWrapper, quota_result: QuotaCheckResult) -> SimpleNamespace:
    guard = SimpleNamespace(
        estimate_tokens=lambda text: 7,
        check_quota=AsyncMock(return_value=quota_result),
        record_usage=AsyncMock(return_value=None),
    )
    wrapper.cost_guard = guard
    return guard


# ---------------------------------------------------------------------------
# 1. fail-closed 转发面
# ---------------------------------------------------------------------------


def test_getattr_blocks_unknown_attribute() -> None:
    wrapper = _make_wrapper()
    with pytest.raises(AttributeError, match="R2-08-02 fail-closed"):
        _ = wrapper.some_never_defined_internal  # 任意未定义属性必须 fail-closed


def test_getattr_blocks_arbitrary_attribute() -> None:
    wrapper = _make_wrapper()
    with pytest.raises(AttributeError):
        _ = wrapper.anything_else


@pytest.mark.parametrize("name", META_ATTRS)
def test_meta_attrs_forward_to_inner(name: str) -> None:
    wrapper = _make_wrapper()
    assert getattr(wrapper, name) == getattr(_FakeInner(), name)


# ---------------------------------------------------------------------------
# 2. 审计旁路为真实方法且带配额/记账
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("method", AUDITED_BYPASSES[:5])
async def test_bypass_enforces_quota_when_user_identifiable(method: str) -> None:
    wrapper = _make_wrapper()
    guard = _attach_quota_guard(wrapper, _allowed_quota())

    call = getattr(wrapper, method)
    if method == "chat_stream_with_tools":
        async for _ in call(system_prompt="s", user_message="u", tools=[], user_context={"user_id": "user-9"}):
            pass
    else:
        await call("prompt", user_id="user-9")

    guard.check_quota.assert_awaited_once_with("user-9", 7, check_only=True)
    if method != "chat_stream_with_tools":
        guard.record_usage.assert_awaited()


@pytest.mark.asyncio
async def test_bypass_records_stream_usage_after_completion() -> None:
    """流式主路径：完整消费流之后按产出补记用量。"""
    wrapper = _make_wrapper()
    guard = _attach_quota_guard(wrapper, _allowed_quota())

    chunks = []
    async for chunk in wrapper.chat_stream_with_tools(
        system_prompt="s",
        user_message="u",
        tools=[],
        user_context={"user_id": "user-9"},
    ):
        chunks.append(chunk)

    assert len(chunks) == 2
    guard.check_quota.assert_awaited_once()  # 流开始前预检
    guard.record_usage.assert_awaited_once()  # 流结束后记账


@pytest.mark.asyncio
@pytest.mark.parametrize("method", AUDITED_BYPASSES[:5])
async def test_bypass_quota_exceeded_blocks_call(method: str) -> None:
    wrapper = _make_wrapper()
    guard = _attach_quota_guard(wrapper, _denied_quota())

    call = getattr(wrapper, method)
    with pytest.raises(QuotaExceededError):
        if method == "chat_stream_with_tools":
            async for _ in call(system_prompt="s", user_message="u", tools=[], user_context={"user_id": "user-9"}):
                pass
        else:
            await call("prompt", user_id="user-9")

    # 被阻断的调用不得产生用量记账（流式从未开始，自然无 record）
    if method != "chat_stream_with_tools":
        guard.record_usage.assert_not_awaited()


@pytest.mark.asyncio
async def test_bypass_without_identity_skips_quota_but_calls_through() -> None:
    """系统内部推理（无终端用户身份）不绑配额，但调用照常透传。"""
    wrapper = _make_wrapper()
    guard = _attach_quota_guard(wrapper, _allowed_quota())

    result = await wrapper.reason("internal prompt")

    assert result == "reasoned"
    guard.check_quota.assert_not_awaited()
