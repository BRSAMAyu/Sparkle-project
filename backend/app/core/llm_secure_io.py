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
_ASSIGNMENT_SECRET_RE = re.compile(
    r"(?i)\b(api[_ -]?key|secret|token|password|authorization)\b\s*[:=]\s*([^\s,;]+)"
)
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
    if not llm_safety_enabled():
        _record_bypass("redact")
        return value

    value = _OPENAI_KEY_RE.sub("[REDACTED_API_KEY]", value)
    value = _BEARER_RE.sub("Bearer [REDACTED]", value)
    value = _ASSIGNMENT_SECRET_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", value)
    value = _URL_CREDENTIAL_RE.sub(r"\1[REDACTED]:[REDACTED]@", value)
    return value


def sanitize_text_for_llm(text: str, user_id: str | None = None) -> str:
    if not text:
        return ""
    if not llm_safety_enabled():
        _record_bypass("input")
        return str(text)
    check = _safety_service.sanitize_input(redact_secrets(text), user_id=user_id)
    return check.sanitized_text


def sanitize_llm_output(text: str, *, context: dict[str, Any] | None = None) -> str:
    if not text:
        return ""
    if not llm_safety_enabled():
        _record_bypass("output")
        return str(text)
    result = _output_validator.validate(redact_secrets(text), context=context)
    if result.action == "block":
        return "抱歉，这部分内容无法直接返回。"
    return result.sanitized_text


def wrap_user_message(text: str) -> str:
    if not text:
        return ""
    if not llm_safety_enabled():
        _record_bypass("wrap_user")
        return str(text)
    return f"{_USER_INPUT_OPEN}\n{text}\n{_USER_INPUT_CLOSE}"


def wrap_tool_result(text: str) -> str:
    if not text:
        return ""
    if not llm_safety_enabled():
        _record_bypass("wrap_tool")
        return str(text)
    return f"{_TOOL_RESULT_OPEN}\n{text}\n{_TOOL_RESULT_CLOSE}"


def secure_messages(
    messages: list[dict[str, Any]] | None,
    *,
    user_id: str | None = None,
    wrap_user_messages: bool = False,
    wrap_tool_messages: bool = False,
) -> list[dict[str, Any]]:
    if not llm_safety_enabled():
        _record_bypass("messages")
        return [dict(message) for message in messages or []]
    secured: list[dict[str, Any]] = []
    for message in messages or []:
        current = dict(message)
        role = str(current.get("role") or "user")
        content = current.get("content")
        if isinstance(content, str):
            safe_content = sanitize_text_for_llm(content, user_id=user_id) if role in {"user", "tool"} else redact_secrets(content)
            if role == "user" and wrap_user_messages:
                safe_content = wrap_user_message(safe_content)
            elif role == "tool" and wrap_tool_messages:
                safe_content = wrap_tool_result(safe_content)
            current["content"] = safe_content
        secured.append(current)
    return secured


def sanitize_exception_message(message: str | None, *, fallback: str = "工具执行失败，请稍后重试。") -> str:
    if not llm_safety_enabled():
        _record_bypass("exception")
        return str(message or "")
    raw = redact_secrets(str(message or "")).strip()
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
        return payload
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
        return json.dumps(payload, ensure_ascii=False)
    return json.dumps(sanitize_tool_payload(payload), ensure_ascii=False)
