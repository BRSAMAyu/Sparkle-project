from __future__ import annotations

import asyncio

from app.gen.agent.v1 import agent_service_pb2

_GENERIC_INTERNAL_ERROR_MESSAGE = "系统暂时不可用，请稍后重试。"
_GENERIC_TIMEOUT_ERROR_MESSAGE = "系统处理超时，请稍后重试。"
_GENERIC_UNAVAILABLE_ERROR_MESSAGE = "服务暂时不可用，请稍后重试。"


def build_safe_chat_error(exc: Exception) -> tuple[str, int, bool]:
    """Map internal exceptions to user-safe chat error payload fields."""
    if isinstance(exc, asyncio.TimeoutError):
        return (
            _GENERIC_TIMEOUT_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_TIMEOUT,
            True,
        )

    if isinstance(exc, (ConnectionError, OSError)):
        return (
            _GENERIC_UNAVAILABLE_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_UNAVAILABLE,
            True,
        )

    return (
        _GENERIC_INTERNAL_ERROR_MESSAGE,
        agent_service_pb2.ERROR_CODE_INTERNAL,
        True,
    )
