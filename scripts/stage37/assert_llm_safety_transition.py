#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
from types import SimpleNamespace

from app.core.cache import cache_service
from app.core.llm_secure_io import refresh_llm_safety_mode
from app.services.aurora_stage37_llm_safety_kill_switch_service import (
    aurora_stage37_llm_safety_kill_switch_service,
)
from app.services.llm_service import LLMService


class _FakeCompletions:
    def __init__(self) -> None:
        self.last_kwargs = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        message = SimpleNamespace(content="ok", tool_calls=None)
        choice = SimpleNamespace(message=message, finish_reason="stop")
        return SimpleNamespace(choices=[choice], usage=None)


def _build_service(fake_completions: _FakeCompletions) -> LLMService:
    service = LLMService(enable_dynamic_routing=False)
    service.demo_mode = False
    service.chat_model = "test-model"
    service.reason_model = "test-model"
    service._provider_error = None
    service._extra_body = None
    service._current_selection = None
    service._provider = SimpleNamespace(
        client=SimpleNamespace(
            chat=SimpleNamespace(
                completions=fake_completions,
            )
        )
    )
    return service


async def _run(enabled: bool) -> None:
    cache_service.redis = None
    aurora_stage37_llm_safety_kill_switch_service.reset_local_cache()
    await aurora_stage37_llm_safety_kill_switch_service.set_enabled(enabled)
    await refresh_llm_safety_mode()

    fake = _FakeCompletions()
    service = _build_service(fake)
    fake_key = "sk-" + "transition-secret-1234567890"
    await service.chat_with_tools(
        system_prompt="You are a helpful assistant.",
        user_message=f"api_key: {fake_key}",
        tools=[],
    )

    flattened = "\n".join(
        message["content"]
        for message in fake.last_kwargs["messages"]
        if isinstance(message.get("content"), str)
    )
    if enabled:
        assert "<USER_INPUT>" in flattened
        assert fake_key not in flattened
        print("mode=on behavior=sanitized")
        return
    assert "<USER_INPUT>" not in flattened
    assert fake_key in flattened
    print("mode=off behavior=passthrough")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enabled", choices=("on", "off"), required=True)
    args = parser.parse_args()
    asyncio.run(_run(args.enabled == "on"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
