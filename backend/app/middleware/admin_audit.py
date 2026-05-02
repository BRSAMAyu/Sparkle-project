"""Admin operation audit middleware and endpoint decorator."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import wraps
from typing import Any
from uuid import UUID

from fastapi import Request, Response
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AdminAuditLog

logger = logging.getLogger(__name__)

ADMIN_AUDIT_METADATA_ATTR = "__sparkle_admin_audit__"
ADMIN_AUDIT_RETENTION_DAYS = 90
ADMIN_AUDIT_ARCHIVE_PREFIX = "admin-audit-log"


@dataclass(frozen=True)
class AdminAuditMetadata:
    """Explicit audit metadata attached to high-risk admin endpoint functions."""

    category: str
    risk: str = "medium"
    action: str | None = None


def audit_admin_action(
    *,
    category: str,
    risk: str = "medium",
    action: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark an admin endpoint with explicit audit category/risk metadata.

    Example for other FV agents:

        @router.post("/promote/{report_id}")
        @audit_admin_action(category="policy_publish", risk="high")
        async def promote_report(...):
            ...
    """

    metadata = AdminAuditMetadata(category=category, risk=risk, action=action)

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, ADMIN_AUDIT_METADATA_ATTR, metadata)
        if not hasattr(func, "__call__"):
            return func

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)
            if isinstance(result, Awaitable):
                return await result
            return result

        setattr(async_wrapper, ADMIN_AUDIT_METADATA_ATTR, metadata)
        return async_wrapper

    return decorator


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _is_admin_audit_path(path: str) -> bool:
    normalized = path.lower()
    return (
        normalized.startswith("/api/v1/admin")
        or normalized.startswith("/api/v1/audit")
        or normalized.startswith("/api/v1/dlq")
        or "_admin" in normalized
    )


def _hash_value(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _extract_admin_user_id(request: Request) -> UUID | None:
    payload = getattr(request.state, "token_payload", None)
    if isinstance(payload, dict):
        user_id = _safe_uuid(payload.get("sub"))
        if user_id:
            return user_id
    return _safe_uuid(request.headers.get("x-admin-user-id"))


def _extract_actor_claims(request: Request) -> dict[str, Any] | None:
    payload = getattr(request.state, "token_payload", None)
    if not isinstance(payload, dict):
        return None
    safe_keys = ("sub", "type", "session_id", "jti", "roles", "scope", "scopes")
    claims = {key: payload.get(key) for key in safe_keys if payload.get(key) is not None}
    return claims or None


def _metadata_for_request(request: Request) -> AdminAuditMetadata | None:
    endpoint = request.scope.get("endpoint")
    if endpoint is None:
        return None
    return getattr(endpoint, ADMIN_AUDIT_METADATA_ATTR, None)


def _infer_category(path: str, method: str) -> str:
    lower = path.lower()
    if "kill-switch" in lower or "killswitch" in lower:
        return "kill_switch"
    if "dlq" in lower:
        return "dlq_replay" if method != "GET" else "dlq_inspection"
    if "memory" in lower:
        return "memory_governance"
    if "feedback" in lower or "bandit" in lower:
        return "feedback_governance"
    if "execution" in lower:
        return "execution_governance"
    if "audit" in lower:
        return "audit_log_access"
    return "admin_write" if method in {"POST", "PUT", "PATCH", "DELETE"} else "admin_read"


def _infer_risk(method: str, category: str) -> str:
    if method in {"POST", "PUT", "PATCH", "DELETE"}:
        return "high" if category in {"kill_switch", "dlq_replay", "memory_governance"} else "medium"
    return "low" if category in {"admin_read", "audit_log_access"} else "medium"


async def record_admin_audit_log(
    *,
    request: Request,
    status_code: int,
    duration_ms: float,
    error: BaseException | None = None,
) -> None:
    """Persist one admin audit log row without mutating the business transaction."""

    metadata = _metadata_for_request(request)
    method = request.method.upper()
    path = request.url.path
    category = metadata.category if metadata else _infer_category(path, method)
    risk = metadata.risk if metadata else _infer_risk(method, category)
    endpoint = request.scope.get("endpoint")
    action = metadata.action if metadata and metadata.action else getattr(endpoint, "__name__", None)
    action = action or f"{method} {path}"
    now = _utcnow()

    log = AdminAuditLog(
        admin_user_id=_extract_admin_user_id(request),
        action=action,
        category=category,
        risk=risk,
        method=method,
        path=path,
        query_hash=_hash_value(request.url.query),
        status_code=status_code,
        outcome="success" if status_code < 400 and error is None else "failure",
        duration_ms=round(duration_ms, 3),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None) or request.headers.get("x-request-id"),
        trace_id=getattr(request.state, "trace_id", None) or request.headers.get("x-trace-id"),
        actor_claims=_extract_actor_claims(request),
        error_message=str(error)[:1000] if error else None,
        details={
            "route_name": getattr(endpoint, "__name__", None),
            "decorated": metadata is not None,
        },
        occurred_at=now,
        retention_until=now + timedelta(days=ADMIN_AUDIT_RETENTION_DAYS),
    )

    try:
        async with AsyncSessionLocal() as session:
            session.add(log)
            await session.commit()
    except Exception:
        logger.exception("failed_to_persist_admin_audit_log", extra={"path": path, "action": action})


class AdminAuditMiddleware(BaseHTTPMiddleware):
    """Capture admin requests and persist immutable audit metadata."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start = time.perf_counter()
        response: Response | None = None
        error: BaseException | None = None
        try:
            response = await call_next(request)
            return response
        except BaseException as exc:
            error = exc
            raise
        finally:
            metadata = _metadata_for_request(request)
            if _is_admin_audit_path(request.url.path) or metadata:
                duration_ms = (time.perf_counter() - start) * 1000
                await record_admin_audit_log(
                    request=request,
                    status_code=response.status_code if response is not None else 500,
                    duration_ms=duration_ms,
                    error=error,
                )


async def archive_due_admin_audit_logs(*, limit: int = 1000) -> dict[str, Any]:
    """Copy due admin audit rows to object storage as JSONL.

    The source table remains append-only; archival is a durable copy for retention
    workflows and legal review, not a destructive purge.
    """

    now = _utcnow()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdminAuditLog)
            .where(AdminAuditLog.retention_until <= now)
            .order_by(AdminAuditLog.occurred_at.asc())
            .limit(limit)
        )
        rows = list(result.scalars().all())

    if not rows:
        return {"archived": 0, "object_key": None}

    payload = "\n".join(json.dumps(row.to_archive_dict(), default=str, sort_keys=True) for row in rows).encode("utf-8")
    object_key = f"{ADMIN_AUDIT_ARCHIVE_PREFIX}/{now:%Y/%m/%d}/{now:%H%M%S}_{len(rows)}.jsonl"

    from app.services.document_upload_storage import _internal_client, document_upload_storage

    _internal_client().put_object(
        Bucket=document_upload_storage.bucket,
        Key=object_key,
        Body=payload,
        ContentType="application/x-ndjson",
    )
    return {"archived": len(rows), "object_key": object_key}
