"""
Unified error taxonomy for Sparkle.

Every error in the system is classified by severity and category,
ensuring no failure is silently swallowed and all errors feed into
CausalTrace for observability (OBS-007).

Severity levels:
  - WARNING: Transient issues, auto-retried, no user impact
  - DEGRADED: Partial failure, system operates with reduced capability
  - CRITICAL: Full failure, requires immediate attention

Categories group errors by subsystem for dashboards and alerts.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorSeverity(StrEnum):
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"


class ErrorCategory(StrEnum):
    INFRASTRUCTURE = "infrastructure"
    LLM = "llm"
    RAG = "rag"
    DATABASE = "database"
    REDIS = "redis"
    WEBSOCKET = "websocket"
    SPINE = "spine"
    AURORA = "aurora"
    NOTIFICATION = "notification"
    MEMORY = "memory"
    COMMUNITY = "community"
    GRAPH = "graph"
    AUTH = "auth"
    EXTERNAL = "external"
    VALIDATION = "validation"


# Map common exception patterns to (severity, category) defaults.
_EXCEPTION_DEFAULTS: dict[str, tuple[ErrorSeverity, ErrorCategory]] = {
    "ConnectionError": (ErrorSeverity.CRITICAL, ErrorCategory.INFRASTRUCTURE),
    "ConnectionRefusedError": (ErrorSeverity.CRITICAL, ErrorCategory.INFRASTRUCTURE),
    "TimeoutError": (ErrorSeverity.DEGRADED, ErrorCategory.INFRASTRUCTURE),
    "asyncio.TimeoutError": (ErrorSeverity.DEGRADED, ErrorCategory.INFRASTRUCTURE),
    "redis.exceptions.ConnectionError": (ErrorSeverity.DEGRADED, ErrorCategory.REDIS),
    "redis.exceptions.TimeoutError": (ErrorSeverity.WARNING, ErrorCategory.REDIS),
    "sqlalchemy.exc.OperationalError": (ErrorSeverity.DEGRADED, ErrorCategory.DATABASE),
    "sqlalchemy.exc.InterfaceError": (ErrorSeverity.CRITICAL, ErrorCategory.DATABASE),
    "openai.APITimeoutError": (ErrorSeverity.DEGRADED, ErrorCategory.LLM),
    "openai.RateLimitError": (ErrorSeverity.WARNING, ErrorCategory.LLM),
    "openai.APIConnectionError": (ErrorSeverity.DEGRADED, ErrorCategory.LLM),
}


@dataclass
class ClassifiedError:
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    component: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "exception_type": self.exception_type,
            "component": self.component,
            "details": self.details or {},
        }


def classify_error(
    error: Exception,
    *,
    component: str = "unknown",
    severity: ErrorSeverity | None = None,
    category: ErrorCategory | None = None,
    details: dict[str, Any] | None = None,
) -> ClassifiedError:
    """Classify an exception into the unified error taxonomy.

    Callers can override severity/category for domain-specific classification.
    If not overridden, defaults are inferred from the exception type.
    """
    exc_type_name = type(error).__qualname__
    exc_module = type(error).__module__
    full_name = f"{exc_module}.{exc_type_name}" if exc_module != "builtins" else exc_type_name

    if severity is None or category is None:
        # Try full module path first, then bare class name
        default = _EXCEPTION_DEFAULTS.get(full_name) or _EXCEPTION_DEFAULTS.get(exc_type_name)
        if default:
            resolved_severity = severity or default[0]
            resolved_category = category or default[1]
        else:
            resolved_severity = severity or ErrorSeverity.WARNING
            resolved_category = category or ErrorCategory.INFRASTRUCTURE
    else:
        resolved_severity = severity
        resolved_category = category

    return ClassifiedError(
        severity=resolved_severity,
        category=resolved_category,
        message=str(error),
        exception_type=full_name,
        component=component,
        details=details,
    )


def should_alert(error: ClassifiedError) -> bool:
    """Whether this error should trigger an alert (DEGRADED or CRITICAL)."""
    return error.severity in (ErrorSeverity.DEGRADED, ErrorSeverity.CRITICAL)


def should_trace(error: ClassifiedError) -> bool:
    """Whether this error should be written to CausalTrace.

    All classified errors should be traced — this exists so callers
    can explicitly opt out for expected transient issues.
    """
    return True
