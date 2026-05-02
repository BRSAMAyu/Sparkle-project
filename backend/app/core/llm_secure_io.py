from __future__ import annotations

import json
import re
from typing import Any

from app.core.llm_output_validator import LLMOutputValidator
from app.core.llm_safety import LLMSafetyService
from app.core.metrics import LLM_SAFETY_BYPASS_TOTAL
from app.services.aurora_stage37_llm_safety_kill_switch_service import (
    aurora_stage37_llm_safety_kill_switch_service,
)

_USER_INPUT_OPEN = "<USER_INPUT>"
_USER_INPUT_CLOSE = "</USER_INPUT>"
_TOOL_RESULT_OPEN = "<TOOL_RESULT>"
_TOOL_RESULT_CLOSE = "</TOOL_RESULT>"

_safety_service = LLMSafetyService(enable_deep_analysis=True)
_output_validator = LLMOutputValidator(strict_mode=True)

_OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9][A-Za-z0-9._-]{8,}\b")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._-]{8,}")
_ASSIGNMENT_SECRET_RE = re.compile(r"(?i)\b(api[_ -]?key|secret|token|password|authorization)\b\s*[:=]\s*([^\s,;]+)")
_URL_CREDENTIAL_RE = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*://)([^/\s:@]+):([^@\s/]+)@")
_TRACEBACK_RE = re.compile(r"Traceback \(most recent call last\):", re.IGNORECASE)
_INTERNAL_ERROR_MARKERS = (
    "traceback",
    "sqlalchemy",
    "asyncpg",
    "psycopg",
    "httpx.",
    "openai.",
    "stack trace",
    "exception:",
    "authorization:",
    "bearer ",
    "select ",
    "insert ",
    "update ",
    "delete ",
    "/users/",
    "/internal/",
)


async def refresh_llm_safety_mode() -> bool:
    return await aurora_stage37_llm_safety_kill_switch_service.get_enabled()


def llm_safety_enabled() -> bool:
    return aurora_stage37_llm_safety_kill_switch_service.current_enabled()


def _record_bypass(surface: str) -> None:
    LLM_SAFETY_BYPASS_TOTAL.labels(surface=surface).inc()


def redact_secrets(text: str) -> str:
    value = str(text or "")
    if not value:
        return ""

    value = _OPENAI_KEY_RE.sub("[REDACTED_API_KEY]", value)
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    value = _ASSIGNMENT_SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    value = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED]:[REDACTED]@", value)
    return value


def _redact_string_values(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, dict):
        return {key: _redact_string_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_redact_string_values(item) for item in value]
    return value


def sanitize_text_for_llm(text: str, user_id: str | None = None) -> str:
    if not text:
        return ""
    redacted = redact_secrets(text)
    if not llm_safety_enabled():
        _record_bypass("input")
        return redacted
    check = _safety_service.sanitize_input(redacted, user_id=user_id)
    return check.sanitized_text


def sanitize_llm_output(text: str, *, context: dict[str, Any] | None = None) -> str:
    if not text:
        return ""
    redacted = redact_secrets(text)
    if not llm_safety_enabled():
        _record_bypass("output")
        # Always run output validation even when kill switch is off
        result = _output_validator.validate(redacted, context=context)
        if result.action == "block":
            return "抱歉，这部分内容无法直接返回。"
        return result.sanitized_text
    result = _output_validator.validate(redacted, context=context)
    if result.action == "block":
        return "抱歉，这部分内容无法直接返回。"
    return result.sanitized_text


def wrap_user_message(text: str) -> str:
    if not text:
        return ""
    redacted = redact_secrets(text)
    if not llm_safety_enabled():
        _record_bypass("wrap_user")
        return redacted
    return f"{_USER_INPUT_OPEN}\n{redacted}\n{_USER_INPUT_CLOSE}"


def wrap_tool_result(text: str) -> str:
    if not text:
        return ""
    redacted = redact_secrets(text)
    if not llm_safety_enabled():
        _record_bypass("wrap_tool")
        return redacted
    return f"{_TOOL_RESULT_OPEN}\n{redacted}\n{_TOOL_RESULT_CLOSE}"


def secure_messages(
    messages: list[dict[str, Any]] | None,
    *,
    user_id: str | None = None,
    wrap_user_messages: bool = False,
    wrap_tool_messages: bool = False,
) -> list[dict[str, Any]]:
    if not llm_safety_enabled():
        _record_bypass("messages")
        secured: list[dict[str, Any]] = []
        for message in messages or []:
            current = dict(message)
            content = current.get("content")
            current["content"] = _redact_string_values(content)
            secured.append(current)
        return secured
    secured: list[dict[str, Any]] = []
    for message in messages or []:
        current = dict(message)
        role = str(current.get("role") or "user")
        content = current.get("content")
        if isinstance(content, str):
            safe_content = (
                sanitize_text_for_llm(content, user_id=user_id) if role in {"user", "tool"} else redact_secrets(content)
            )
            if role == "user" and wrap_user_messages:
                safe_content = wrap_user_message(safe_content)
            elif role == "tool" and wrap_tool_messages:
                safe_content = wrap_tool_result(safe_content)
            current["content"] = safe_content
        elif content is not None:
            current["content"] = _redact_string_values(content)
        secured.append(current)
    return secured


def sanitize_exception_message(message: str | None, *, fallback: str = "工具执行失败，请稍后重试。") -> str:
    raw = redact_secrets(str(message or "")).strip()
    if not llm_safety_enabled():
        _record_bypass("exception")
        return raw
    if not raw:
        return fallback

    collapsed = re.sub(r"\s+", " ", raw).strip()
    lowered = collapsed.lower()
    if "timeout" in lowered or "timed out" in lowered or "超时" in collapsed:
        return "工具执行超时，请稍后重试。"
    if any(marker in lowered for marker in _INTERNAL_ERROR_MARKERS):
        return fallback
    if len(collapsed) > 240:
        collapsed = collapsed[:237] + "..."
    if _TRACEBACK_RE.search(raw):
        return fallback
    return collapsed


def sanitize_tool_payload(payload: Any) -> Any:
    if not llm_safety_enabled():
        _record_bypass("tool_payload")
        return _redact_string_values(payload)
    if isinstance(payload, dict):
        sanitized = {}
        for key, value in payload.items():
            if key == "error_message" and isinstance(value, str):
                sanitized[key] = sanitize_exception_message(value)
            elif key == "suggestion" and isinstance(value, str):
                sanitized[key] = sanitize_exception_message(value, fallback="请稍后重试。")
            else:
                sanitized[key] = sanitize_tool_payload(value)
        return sanitized
    if isinstance(payload, list):
        return [sanitize_tool_payload(item) for item in payload]
    if isinstance(payload, str):
        safe = redact_secrets(payload)
        if len(safe) > 2000:
            safe = safe[:1997] + "..."
        return safe
    return payload


def sanitize_tool_payload_json(payload: Any) -> str:
    if not llm_safety_enabled():
        _record_bypass("tool_payload_json")
        return json.dumps(sanitize_tool_payload(payload), ensure_ascii=False)
    return json.dumps(sanitize_tool_payload(payload), ensure_ascii=False)
