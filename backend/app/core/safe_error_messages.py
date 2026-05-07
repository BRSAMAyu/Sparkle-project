from __future__ import annotations

import asyncio
from http import HTTPStatus

from app.core.exceptions import LLMServiceError, ValidationError
from app.gen.agent.v1 import agent_service_pb2

_GENERIC_INTERNAL_ERROR_MESSAGE = "系统暂时不可用，请稍后重试。"
_GENERIC_TIMEOUT_ERROR_MESSAGE = "系统处理超时，请稍后重试。"
_GENERIC_UNAVAILABLE_ERROR_MESSAGE = "服务暂时不可用，请稍后重试。"
_GENERIC_INVALID_ARGUMENT_MESSAGE = "输入内容有误，请检查后重试。"
_GENERIC_LLM_PROVIDER_ERROR_MESSAGE = "AI 服务暂时不可用，请稍后重试。"
_ACTIONABLE_LLM_WARMUP_MESSAGE = "AI 服务正在启动中，请等待 30 秒后重试。"

_LLM_PROVIDER_MODULE_MARKERS = (
    "openai",
    "anthropic",
    "dashscope",
    "zhipu",
    "deepseek",
    "litellm",
)
_LLM_PROVIDER_NAME_MARKERS = (
    "apierror",
    "apiconnectionerror",
    "apistatuserror",
    "insufficientquotaerror",
    "llm",
    "openai",
    "provider",
    "ratelimiterror",
)


def _is_llm_provider_exception(exc: Exception) -> bool:
    exc_type = type(exc)
    module = exc_type.__module__.lower()
    name = exc_type.__name__.lower()
    if any(marker in module for marker in _LLM_PROVIDER_MODULE_MARKERS):
        return True
    return any(marker in name for marker in _LLM_PROVIDER_NAME_MARKERS)


def _http_status(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code
    status = getattr(exc, "status", None)
    if isinstance(status, int):
        return status
    return None


def build_safe_chat_error(exc: Exception) -> tuple[str, int, bool]:
    """Map internal exceptions to user-safe chat error payload fields."""
    if isinstance(exc, asyncio.TimeoutError):
        return (
            _GENERIC_TIMEOUT_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_TIMEOUT,
            True,
        )

    if isinstance(exc, (ValueError, ValidationError)):
        return (
            _GENERIC_INVALID_ARGUMENT_MESSAGE,
            agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            False,
        )

    status_code = _http_status(exc)
    if status_code == HTTPStatus.BAD_REQUEST:
        return (
            _GENERIC_INVALID_ARGUMENT_MESSAGE,
            agent_service_pb2.ERROR_CODE_INVALID_ARGUMENT,
            False,
        )

    if isinstance(exc, LLMServiceError) or _is_llm_provider_exception(exc):
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            return (
                _GENERIC_LLM_PROVIDER_ERROR_MESSAGE,
                agent_service_pb2.ERROR_CODE_RATE_LIMITED,
                True,
            )
        if status_code in {HTTPStatus.BAD_GATEWAY, HTTPStatus.SERVICE_UNAVAILABLE, HTTPStatus.GATEWAY_TIMEOUT}:
            return (
                _ACTIONABLE_LLM_WARMUP_MESSAGE,
                agent_service_pb2.ERROR_CODE_UNAVAILABLE,
                True,
            )
        return (
            _GENERIC_LLM_PROVIDER_ERROR_MESSAGE,
            agent_service_pb2.ERROR_CODE_INTERNAL,
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
